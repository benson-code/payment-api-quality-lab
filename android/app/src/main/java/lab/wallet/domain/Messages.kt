package lab.wallet.domain

/**
 * What the user reads for each API error code (SPEC.md §6.6). The server decides; the client only
 * explains the decision. Same texts as web/src/messages.js; MessagesSpecParityTest compares them with
 * the specification.
 */
object Messages {
    private val BY_CODE = mapOf(
        "INVALID_AMOUNT" to "Enter an amount like 100 or 100.50: more than 0, at most two decimals.",
        "INSUFFICIENT_BALANCE" to "Not enough balance for this payment.",
        "LIMIT_EXCEEDED" to "This is above the single-payment limit of 50,000.00.",
        "REFUND_EXCEEDS_PAYMENT" to "This refund would exceed what is left to refund on this payment.",
        "WALLET_NOT_FOUND" to "No wallet with this ID.",
        "PAYMENT_NOT_FOUND" to "No payment with this ID.",
        "INVALID_OWNER" to "Enter a name of 1 to 50 characters.",
        "IDEMPOTENCY_KEY_REUSED" to "This request conflicts with an earlier one. Start again.",
    )

    fun forCode(code: String): String = BY_CODE[code] ?: "Something went wrong ($code)."

    /** Every code with its own text, for the parity test. */
    val codes: Set<String> get() = BY_CODE.keys

    const val NO_ANSWER_TRY_AGAIN = "No answer from the server. Try again."
    const val NO_ANSWER = "No answer from the server."
    const val TOP_UP_NO_ANSWER =
        "No answer from the server: the top-up may or may not have gone through. Check the balance before trying again."
}
