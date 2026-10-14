import Observation
import SwiftUI

/// Top up: one step (SPEC.md §7.4). Same behaviour as web/src/screens/TopUp.jsx and the Android
/// TopUpScreen.kt. Top-ups take no Idempotency-Key in this API, so there is no safe retry: after no
/// answer the user is asked to check the balance first, and no Retry is offered (K-07).
@Observable
final class TopUpModel {
    let attempt = Attempt(idempotent: false)
    private(set) var amount = ""
    private(set) var wallet: Wallet?
    private(set) var result: TopUp?
    private let api: ApiClient
    private let walletId: String

    init(api: ApiClient, walletId: String) {
        self.api = api
        self.walletId = walletId
    }

    func load() async {
        if case .ok(let w, _) = await api.getWallet(walletId) { wallet = w }
    }

    /// A different amount, and any message about the last one goes away.
    func edit(_ value: String) {
        attempt.reset()
        amount = value
    }

    func submit() async {
        let r = await attempt.submit(amount) { amount, _ in await api.topUp(walletId, amount) }
        if case .ok(let topUp, _) = r { result = topUp }
    }
}

struct TopUpView: View {
    let onBack: () -> Void
    let onDone: () -> Void
    @State private var model: TopUpModel

    init(api: ApiClient, walletId: String, onBack: @escaping () -> Void, onDone: @escaping () -> Void) {
        self.onBack = onBack
        self.onDone = onDone
        _model = State(initialValue: TopUpModel(api: api, walletId: walletId))
    }

    var body: some View {
        Group {
            if let done = model.result {
                Receipt(title: "Top up", heading: "Top-up completed", amount: done.amount) {
                    WalletButton(text: "Done", testTag: "done", action: onDone)
                } rows: {
                    ReceiptRow(label: "Status", value: "Completed")
                    RowDivider()
                    ReceiptRow(label: "Balance after", value: Money.display(done.balance), valueTestTag: "result-balance", suffix: "TWD")
                }
            } else {
                form
            }
        }
        .task { await model.load() }
    }

    private var form: some View {
        let state = model.attempt.state
        let pending = state == .pending
        let error: String? = if case .refused(_, let message) = state { message } else { nil }
        return Screen(title: "Top up", onBack: onBack) {
            WalletButton(text: "Top up", testTag: "submit",
                         enabled: !model.amount.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
                         loading: pending) { Task { await model.submit() } }
        } content: {
            if let wallet = model.wallet { Available(wallet: wallet) }
            AmountField(value: Binding(get: { model.amount }, set: { model.edit($0) }), enabled: !pending, error: error)
            if state == .unknown {
                Message(kind: .warning, text: Messages.topUpNoAnswer, testTag: "no-answer")
            }
        }
    }
}
