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
