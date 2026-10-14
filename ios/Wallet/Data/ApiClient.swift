import Foundation

/// Every call to the payment API that the iOS screens make. Same behaviour as web/src/api.js and the
/// Android ApiClient.kt: amounts are sent as the strings the user typed (the API parses them into
/// integer cents), an error answer is `.refused`, and no answer or a non-JSON answer is `.noAnswer`.
final class ApiClient {
    private let config: ApiConfig
    private let session: URLSession

    init(config: ApiConfig) {
        self.config = config
        // No cache of any kind: a balance must always come from the server, never from a stored answer
        let c = URLSessionConfiguration.ephemeral
        c.urlCache = nil
        c.requestCachePolicy = .reloadIgnoringLocalCacheData
        c.timeoutIntervalForRequest = 15        // Android: readTimeout 15 s
        c.waitsForConnectivity = false          // offline is "no answer" at once, not a wait
        session = URLSession(configuration: c)
    }

    func createWallet(_ owner: String) async -> ApiResult<Wallet> {
        await request("POST", "/wallets", body: ["owner": owner], parse: Wallet.from)
    }

    func getWallet(_ walletId: String) async -> ApiResult<Wallet> {
        await request("GET", "/wallets/\(seg(walletId))", parse: Wallet.from)
    }

    func topUp(_ walletId: String, _ amount: String) async -> ApiResult<TopUp> {
        await request("POST", "/wallets/\(seg(walletId))/topups", body: ["amount": amount], parse: TopUp.from)
    }

    /// The ledger, oldest first, as the API returns it.
    func transactions(_ walletId: String) async -> ApiResult<[Entry]> {
        await request("GET", "/wallets/\(seg(walletId))/transactions") { j in
            guard let rows = j["transactions"] as? [JSON] else { throw MissingField(name: "transactions") }
            return try rows.map(Entry.from)
        }
    }

    /// Pays `amount` from the wallet. `key` is the attempt's Idempotency-Key (SPEC.md §6.2).
    func pay(_ walletId: String, _ amount: String, key: String) async -> ApiResult<Payment> {
        await request("POST", "/payments", body: ["wallet_id": walletId, "amount": amount], key: key, parse: Payment.from)
    }

    func getPayment(_ paymentId: String) async -> ApiResult<Payment> {
        await request("GET", "/payments/\(seg(paymentId))", parse: Payment.from)
    }

    /// Refunds `amount` of the payment. `key` is the attempt's Idempotency-Key (SPEC.md §6.2).
    func refund(_ paymentId: String, _ amount: String, key: String) async -> ApiResult<RefundResult> {
        await request("POST", "/payments/\(seg(paymentId))/refunds", body: ["amount": amount], key: key, parse: RefundResult.from)
    }

    private func seg(_ value: String) -> String {
        var allowed = CharacterSet.alphanumerics
        allowed.insert(charactersIn: "-._~")
        return value.addingPercentEncoding(withAllowedCharacters: allowed) ?? value
    }

    private func request<T>(
        _ method: String,
        _ path: String,
        body: [String: String]? = nil,
        key: String? = nil,
        parse: (JSON) throws -> T
    ) async -> ApiResult<T> {
        guard let url = URL(string: config.baseUrl + path) else { return .noAnswer }
        var req = URLRequest(url: url)
        req.httpMethod = method
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        if let key { req.setValue(key, forHTTPHeaderField: "Idempotency-Key") }
        if let body {
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = try? JSONSerialization.data(withJSONObject: body)
        }
        let data: Data
        let http: HTTPURLResponse
        do {
            let (d, response) = try await session.data(for: req)
            guard let h = response as? HTTPURLResponse else { return .noAnswer }
            (data, http) = (d, h)
        } catch {
            return .noAnswer
        }
        // An answer without a JSON body is not a usable answer
        guard let json = (try? JSONSerialization.jsonObject(with: data)) as? JSON else { return .noAnswer }
        guard (200..<300).contains(http.statusCode) else {
            return .refused(status: http.statusCode, code: json["error_code"] as? String ?? "UNKNOWN",
                            message: json["message"] as? String ?? "")
        }
        guard let value = try? parse(json) else { return .noAnswer }
        return .ok(value, replayed: http.value(forHTTPHeaderField: "Idempotent-Replayed") == "true")
    }
}
