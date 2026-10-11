package lab.wallet.domain

/**
 * Amounts as the API sends them: strings with two decimals ("12345.60"). They are formatted as text
 * and computed in integer cents (Long), never through Double or Float (SPEC.md D-01, §5).
 * Same behaviour as web/src/money.js.
 */
object Money {
    private const val MINUS = '−'      // the typographic minus sign, read as "minus" (SPEC D-02)
    /** 0-9 only: on Android, \d would also match "１００" and other scripts' digits (MoneyTest). */
    internal val PLAIN = Regex("""^[0-9]+(\.[0-9]{1,2})?$""")

    /** "12345.60" -> "12,345.60"; "-7.00" -> "-7.00". */
    fun display(value: String): String {
        val negative = value.startsWith("-")
        val parts = (if (negative) value.drop(1) else value).split(".")
        val grouped = parts[0].reversed().chunked(3).joinToString(",").reversed()
        val cents = parts.getOrElse(1) { "00" }
        return (if (negative) "-" else "") + grouped + "." + cents
    }

    /** For ledger rows: "+100.00" for money in, "−30.00" for money out. */
    fun signed(value: String): String =
        if (value.startsWith("-")) MINUS + display(value.drop(1)) else "+" + display(value)

    /**
     * The Figma text style for a balance as shown: one step smaller for long amounts, two for the
     * longest, so that the largest balance the API allows (999,999,999,999.99) fits a 360 dp screen
     * (SPEC L-01). Same rule as balanceStyle in web/src/money.js.
     */
    fun balanceStyle(shown: String): String = when {
        shown.length <= 10 -> "Display/Balance"     // up to 999,999.99
        shown.length <= 14 -> "Amount/Large"        // up to 999,999,999.99
        else -> "Title/Large"
    }

    /** "100.50" -> 10050. Accepts what the API sends (two decimals) and plain amounts with one or none. */
    fun toCents(value: String): Long {
        val negative = value.startsWith("-")
        val parts = (if (negative) value.drop(1) else value).split(".")
        val cents = parts[0].toLong() * 100 + parts.getOrElse(1) { "00" }.padEnd(2, '0').toLong()
        return if (negative) -cents else cents
    }

    /** 10050 -> "100.50"; -5 -> "-0.05". */
    fun fromCents(cents: Long): String {
        val abs = Math.abs(cents)
        return (if (cents < 0) "-" else "") + (abs / 100) + "." + (abs % 100).toString().padStart(2, '0')
    }

    /**
     * What the user typed, as a two-decimal amount ("30" -> "30.00"), or null if it is not a plain
     * amount. Display only: the client never decides whether an amount is valid, the API does (R-02).
     * "Plain" is the API's own grammar, so spaces are not trimmed: " 5 " shown as 5.00 on Confirm was
     * then refused (found in the QA pass).
     */
    fun normalize(typed: String): String? = if (PLAIN.matches(typed)) fromCents(toCents(typed)) else null

    /** Amounts compared as money: "30" and "30.00" are the same payment (K-05); anything else as typed. */
    fun sameAmount(a: String, b: String): Boolean = (normalize(a) ?: a) == (normalize(b) ?: b)
}
