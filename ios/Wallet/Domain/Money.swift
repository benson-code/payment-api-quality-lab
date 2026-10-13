import Foundation

/// Amounts as the API sends them: strings with two decimals ("12345.60"). They are formatted as text
/// and computed in integer cents (Int64), never through Double, Float or Decimal (SPEC.md D-01, §5).
/// Same behaviour as web/src/money.js and the Android Money.kt.
nonisolated enum Money {
    /// The typographic minus sign, read as "minus" (SPEC D-02).
    static let minus = "\u{2212}"

    /// "12345.60" -> "12,345.60"; "-7.00" -> "-7.00".
    static func display(_ value: String) -> String {
        let negative = value.hasPrefix("-")
        let parts = (negative ? String(value.dropFirst()) : value).split(separator: ".", omittingEmptySubsequences: false)
        var grouped = ""
        for (i, digit) in parts[0].reversed().enumerated() {
            if i > 0 && i % 3 == 0 { grouped.append(",") }
            grouped.append(digit)
        }
        let cents = parts.count > 1 ? String(parts[1]) : "00"
        return (negative ? "-" : "") + String(grouped.reversed()) + "." + cents
    }

    /// For ledger rows: "+100.00" for money in, "−30.00" for money out.
    static func signed(_ value: String) -> String {
        value.hasPrefix("-") ? minus + display(String(value.dropFirst())) : "+" + display(value)
    }

    /// The Figma text style for a balance as shown, one step smaller for long amounts (SPEC L-01).
    /// Same rule as balanceStyle in web/src/money.js.
    static func balanceStyle(_ shown: String) -> String {
        switch shown.count {
        case ...10: return "Display/Balance"     // up to 999,999.99
        case ...14: return "Amount/Large"        // up to 999,999,999.99
        default: return "Title/Large"
        }
    }

    /// Digits 0-9 only, at most two decimals, nothing else: the API's own grammar (R-04). `\A` and `\z`,
    /// not `^` and `$`: in ICU, `$` also matches before a final line break, so "30\n" would pass.
    static func isPlain(_ typed: String) -> Bool {
        typed.range(of: #"\A[0-9]+(\.[0-9]{1,2})?\z"#, options: .regularExpression) != nil
    }

    /// "100.50" -> 10050. Accepts what the API sends (two decimals) and plain amounts with one or none.
    /// nil when the number does not fit in 64 bits: such an amount is shown as typed, and the API refuses it.
    static func toCents(_ value: String) -> Int64? {
        let negative = value.hasPrefix("-")
        let parts = (negative ? String(value.dropFirst()) : value).split(separator: ".", omittingEmptySubsequences: false)
        let decimals = parts.count > 1 ? String(parts[1]).padding(toLength: 2, withPad: "0", startingAt: 0) : "00"
        guard let whole = Int64(parts[0]), let cents = Int64(decimals) else { return nil }
        let (scaled, o1) = whole.multipliedReportingOverflow(by: 100)
        let (total, o2) = scaled.addingReportingOverflow(cents)
        if o1 || o2 { return nil }
        return negative ? -total : total
    }

    /// 10050 -> "100.50"; -5 -> "-0.05".
    static func fromCents(_ cents: Int64) -> String {
        let abs = cents.magnitude
        let fraction = String(abs % 100)
        return (cents < 0 ? "-" : "") + String(abs / 100) + "." + (fraction.count < 2 ? "0" + fraction : fraction)
    }

    /// What the user typed, as a two-decimal amount ("30" -> "30.00"), or nil if it is not a plain amount.
    /// Display only: the client never decides whether an amount is valid, the API does (R-02).
    static func normalize(_ typed: String) -> String? {
        guard isPlain(typed), let cents = toCents(typed) else { return nil }
        return fromCents(cents)
    }

    /// Amounts compared as money: "30" and "30.00" are the same payment (K-05); anything else as typed.
    static func sameAmount(_ a: String, _ b: String) -> Bool {
        (normalize(a) ?? a) == (normalize(b) ?? b)
    }
}
