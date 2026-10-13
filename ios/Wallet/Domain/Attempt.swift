import Foundation
import Observation

/// Sending an amount that the API takes an Idempotency-Key for. Same rules as web/src/useAttempt.js
/// and the Android Attempt.kt (SPEC.md §6.2).
///
/// One attempt = one amount the user confirmed, with one Idempotency-Key.
/// - K-01 The key is created when the attempt is first sent, not before.
/// - K-02 While a request is in flight, another submit sends nothing. Everything here runs on the main
///   actor and the flag is set before the first `await`, so a second tap that arrives before the
///   screen redraws is ignored too.
/// - K-03 No answer: the outcome is unknown. The attempt and its key are kept; the next submit of the
///   same amount resends the same key, so a request the server already processed is not charged again.
/// - K-04 An error answer is definitive and nothing was charged: the attempt ends.
/// - K-05 Only a different amount (compared as money: "30" is "30.00") ends a pending attempt.
@Observable
final class Attempt {
    enum State: Equatable {
        case idle
        case pending
        case refused(code: String, message: String)
        case unknown
    }

    private struct Sent {
        let amount: String
        let key: String
    }

    private(set) var state: State = .idle
    @ObservationIgnored private var inFlight = false
    @ObservationIgnored private var pending: Sent?
    private let newKey: () -> String

    /// UUID v4, lower case as on the web and Android (`UUID()` is random, version 4).
    init(newKey: @escaping () -> String = { UUID().uuidString.lowercased() }) {
        self.newKey = newKey
    }

    /// The amount of the attempt still waiting for an answer, or nil.
    var pendingAmount: String? { pending?.amount }

    /// Sends `amount` with `send`, unless a request is already in flight (then returns nil at once).
    /// Returns the API's result; `state` tells the screen what to show.
    func submit<T>(_ amount: String, send: (_ amount: String, _ key: String) async -> ApiResult<T>) async -> ApiResult<T>? {
        if inFlight { return nil }
        inFlight = true
        defer { inFlight = false }
        if let p = pending, !Money.sameAmount(p.amount, amount) { pending = nil }
        let attempt = pending ?? Sent(amount: amount, key: newKey())
        pending = attempt
        state = .pending
        let result = await send(attempt.amount, attempt.key)
        switch result {
        case .ok:
            pending = nil
            state = .idle
        case .refused(_, let code, _):
            pending = nil
            state = .refused(code: code, message: Messages.forCode(code))
        case .noAnswer:
            state = .unknown
        }
        return result
    }

    /// Ends the attempt without sending (the user changed the amount, or left a refusal). Ignored while in flight.
    func reset() {
        if inFlight { return }
        pending = nil
        state = .idle
    }
}
