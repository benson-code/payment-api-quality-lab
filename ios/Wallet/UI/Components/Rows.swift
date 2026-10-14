import SwiftUI

/// Figma: Section header. Groups rows ("Recent activity", "Today", "9 Oct").
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

/// Figma: Transaction row (Direction = Credit | Debit; Show chevron). Credit amounts in green with "+",
/// debit amounts in the text colour with "−" (SPEC D-02). The row carries `testTag`; the title, amount
/// and balance keep their own hooks ("item-title", "item-amount", "item-balance").
///
/// With `onOpen` (payments, D-05) the whole row is one button, hook "open-payment", with a chevron. As on
/// the web and Android the row and its button are two levels; the button's texts stay elements of their
/// own, with their hooks. The chevron is named "Open payment" for VoiceOver.
struct TransactionRow: View {
    let title: String
    let time: String
    let amount: String
    let balanceAfter: String?
    let testTag: String
    var onOpen: (() -> Void)?

    var body: some View {
        // A stack of its own around the button: two views, so two elements, each with its hook
        VStack(spacing: 0) {
            if let onOpen {
                Button(action: onOpen) {
                    content.contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                // No accessibilityElement(children: .contain) here: on a button it replaced this hook
                // with one made of the children's ("item-title-item-amount-item-balance")
                .accessibilityIdentifier("open-payment")
            } else {
                content
            }
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier(testTag)
    }

    private var content: some View {
        let credit = !amount.hasPrefix("-")
        return HStack(spacing: WalletSpacing.md) {
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
            if onOpen != nil {
                Image(systemName: "chevron.right")
                    .font(.system(size: 16, weight: .medium))
                    .foregroundStyle(WalletColors.iconMuted)
                    .frame(width: 24, height: 24)
                    .accessibilityLabel("Open payment")
                    .accessibilityAddTraits(.isButton)
            }
        }
        .padding(.vertical, WalletSpacing.md)
    }
}

/// Ledger entries in a list card, newest first, separated by hairlines. Payment rows open their
/// detail (D-05). Home shows the latest three, History every entry of a day.
struct EntryList: View {
    let entries: [Entry]
    let rowTag: String
    let onOpenPayment: (_ paymentId: String) -> Void

    var body: some View {
        WalletCard(spacing: 0, padding: EdgeInsets(top: WalletSpacing.xs, leading: WalletSpacing.lg,
                                                   bottom: WalletSpacing.xs, trailing: WalletSpacing.lg)) {
            ForEach(Array(entries.enumerated()), id: \.element.entryId) { i, e in
                if i > 0 { RowDivider() }
                let open: (() -> Void)? = if e.type == "PAYMENT", let id = e.refId { { onOpenPayment(id) } } else { nil }
                TransactionRow(title: Formats.typeLabel(e.type), time: Formats.time(e.createdAt),
                               amount: e.amount, balanceAfter: e.balanceAfter, testTag: rowTag, onOpen: open)
            }
        }
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
