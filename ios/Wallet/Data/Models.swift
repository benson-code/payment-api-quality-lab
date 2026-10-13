import Foundation

/// The three ways a request can end (SPEC.md §6.2).
enum ApiResult<T> {
    /// The API answered with success. `replayed`: Idempotent-Replayed: true, the original result of an earlier request.
    case ok(T, replayed: Bool = false)
    /// The API answered with an error: definitive, nothing was charged.
    case refused(status: Int, code: String, message: String)
    /// No usable answer (network error, or a body that is not JSON): the outcome is unknown.
    case noAnswer
}

/// A field missing from an answer: the answer is not usable.
nonisolated struct MissingField: Error {
    let name: String
}

typealias JSON = [String: Any]

nonisolated private extension Dictionary where Key == String, Value == Any {
    func string(_ key: String) throws -> String {
        guard let v = self[key] as? String else { throw MissingField(name: key) }
        return v
    }
}

// What the API returns, with amounts kept as the API's strings (SPEC D-01). Parsed by hand, as the
// Android app does (Models.kt), so both clients read exactly the same fields.

nonisolated struct Wallet: Equatable {
    let walletId: String
    let owner: String
    let currency: String
    let balance: String

    static func from(_ j: JSON) throws -> Wallet {
        Wallet(walletId: try j.string("wallet_id"), owner: try j.string("owner"),
               currency: try j.string("currency"), balance: try j.string("balance"))
    }
}

/// One ledger entry. `amount` is signed: "-30.00" for a payment.
nonisolated struct Entry: Equatable {
    let entryId: Int
    let type: String
    let amount: String
    let balanceAfter: String
    let refId: String?
    let createdAt: String

    static func from(_ j: JSON) throws -> Entry {
        guard let id = j["entry_id"] as? Int else { throw MissingField(name: "entry_id") }
        return Entry(entryId: id, type: try j.string("type"), amount: try j.string("amount"),
                     balanceAfter: try j.string("balance_after"), refId: j["ref_id"] as? String,
                     createdAt: try j.string("created_at"))
    }
}

/// A payment. `balanceAfter` is only in the answer to the payment itself.
nonisolated struct Payment: Equatable {
    let paymentId: String
    let walletId: String
    let amount: String
    let createdAt: String
    let balanceAfter: String?

    static func from(_ j: JSON) throws -> Payment {
        Payment(paymentId: try j.string("payment_id"), walletId: try j.string("wallet_id"),
                amount: try j.string("amount"), createdAt: try j.string("created_at"),
                balanceAfter: j["balance_after"] as? String)
    }
}
