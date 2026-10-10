package lab.wallet.data

import org.json.JSONObject

/** What the API returns, with amounts kept as the API's strings (SPEC D-01). */
data class Wallet(val walletId: String, val owner: String, val currency: String, val balance: String) {
    companion object {
        fun from(j: JSONObject) = Wallet(j.getString("wallet_id"), j.getString("owner"), j.getString("currency"), j.getString("balance"))
    }
}

/** One ledger entry. [amount] is signed: "-30.00" for a payment. */
data class Entry(
    val entryId: Long,
    val type: String,
    val amount: String,
    val balanceAfter: String,
    val refId: String?,
    val createdAt: String,
) {
    companion object {
        fun from(j: JSONObject) = Entry(
            j.getLong("entry_id"), j.getString("type"), j.getString("amount"), j.getString("balance_after"),
            if (j.isNull("ref_id")) null else j.getString("ref_id"), j.getString("created_at"),
        )
    }
}

data class TopUp(val amount: String, val balance: String) {
    companion object {
        fun from(j: JSONObject) = TopUp(j.getString("amount"), j.getString("balance"))
    }
}

/** A payment and its refunds. [balanceAfter] is only in the answer to the payment itself. */
data class Payment(
    val paymentId: String,
    val walletId: String,
    val amount: String,
    val refunded: String,
    val createdAt: String,
    val balanceAfter: String?,
    val refunds: List<Refund>,
) {
    companion object {
        fun from(j: JSONObject) = Payment(
            j.getString("payment_id"), j.getString("wallet_id"), j.getString("amount"), j.getString("refunded"),
            j.getString("created_at"), if (j.has("balance_after")) j.getString("balance_after") else null,
            j.optJSONArray("refunds")?.let { a -> List(a.length()) { Refund.from(a.getJSONObject(it)) } } ?: emptyList(),
        )
    }
}

data class Refund(val refundId: String, val amount: String, val createdAt: String) {
    companion object {
        fun from(j: JSONObject) = Refund(j.getString("refund_id"), j.getString("amount"), j.getString("created_at"))
    }
}

/** The answer to a refund. */
data class RefundResult(val amount: String, val balanceAfter: String) {
    companion object {
        fun from(j: JSONObject) = RefundResult(j.getString("amount"), j.getString("balance_after"))
    }
}
