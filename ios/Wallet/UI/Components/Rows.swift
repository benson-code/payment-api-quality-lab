import SwiftUI

/// Figma: Section header. Groups rows ("Recent activity").
struct SectionHeader: View {
    let text: String

    var body: some View {
        Text(text)
            .walletText(WalletType.label)
            .foregroundStyle(WalletColors.textSecondary)
            .padding(.top, WalletSpacing.xs)
            .accessibilityAddTraits(.isHeader)
    }
}

/// A hairline between rows of a list card, as the web's `.tx-row + .tx-row`.
struct RowDivider: View {
    var body: some View {
        Rectangle().fill(WalletColors.borderDefault).frame(height: 1)
    }
}

/// Figma: Transaction row (Direction = Credit | Debit). Credit amounts in green with "+", debit
/// amounts in the text colour with "−" (SPEC D-02). The row carries `testTag`; the title, amount and
/// balance keep their own hooks ("item-title", "item-amount", "item-balance").
/// No chevron yet: this app has no payment detail screen.
struct TransactionRow: View {
    let title: String
    let time: String
    let amount: String
    let balanceAfter: String?
    let testTag: String

    var body: some View {
        let credit = !amount.hasPrefix("-")
        HStack(spacing: WalletSpacing.md) {
            VStack(alignment: .leading, spacing: 2) {
                Text(title).walletText(WalletType.bodyStrong).foregroundStyle(WalletColors.textPrimary)
                    .accessibilityIdentifier("item-title")
                Text(time).walletText(WalletType.caption).foregroundStyle(WalletColors.textSecondary)
            }
            Spacer(minLength: 0)
            VStack(alignment: .trailing, spacing: 2) {
                Text(Money.signed(amount))
                    .walletText(WalletType.bodyStrongTabular)
                    .foregroundStyle(credit ? WalletColors.amountCredit : WalletColors.textPrimary)
                    .accessibilityIdentifier("item-amount")
                if let balanceAfter {
                    HStack(spacing: 0) {
                        Text("Balance ")
                        Text(Money.display(balanceAfter)).monospacedDigit().accessibilityIdentifier("item-balance")
                    }
                    .walletText(WalletType.caption)
                    .foregroundStyle(WalletColors.textSecondary)
                }
            }
        }
        .padding(.vertical, WalletSpacing.md)
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier(testTag)
    }
}

/// Figma: Receipt row. Label left, value right. A hook on an amount wraps the number only, never the
/// currency (SPEC §7): pass the number as `value` and the currency as `suffix`. Hook "receipt-row" on
/// the whole row, as on the web and Android. The value is Body/Strong in tabular figures (D-07), as on
/// the web and Android; until 2.13 it was Body/Regular in proportional figures.
/// `last`: the last row of a summary card (Confirm) has no padding under it; the card's own padding
/// ends it, as on the web (SPEC §7.7).
struct ReceiptRow: View {
    let label: String
    let value: String
    var valueTestTag: String?
    var suffix: String?
    var last = false

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: WalletSpacing.lg) {
            Text(label).walletText(WalletType.body).foregroundStyle(WalletColors.textSecondary)
            Spacer(minLength: 0)
            HStack(alignment: .firstTextBaseline, spacing: 4) {
                Text(value)
                    .walletText(WalletType.bodyStrongTabular)
                    .foregroundStyle(WalletColors.textPrimary)
                    .multilineTextAlignment(.trailing)
                    .accessibilityIdentifier(valueTestTag ?? "")
                if let suffix {
                    Text(suffix).walletText(WalletType.bodyStrong).foregroundStyle(WalletColors.textPrimary)
                }
            }
        }
        .padding(.top, WalletSpacing.md)
        .padding(.bottom, last ? 0 : WalletSpacing.md)
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("receipt-row")
    }
}
