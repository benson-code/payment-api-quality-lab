import SwiftUI

/// Figma: Balance card (Hidden = False | True). The eye button hides the balance (SPEC D-06); the choice
/// is not kept across screens. The wallet ID is shown masked (D-04).
struct BalanceCard: View {
    let wallet: Wallet
    @State private var hidden = false

    var body: some View {
        WalletCard(spacing: WalletSpacing.xs) {
            HStack(spacing: 0) {
                Text(wallet.owner)
                    .walletText(WalletType.bodyStrong)
                    .foregroundStyle(WalletColors.textPrimary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .accessibilityIdentifier("owner")
                IconButton(systemName: hidden ? "eye.slash" : "eye", label: hidden ? "Show balance" : "Hide balance",
                           testTag: "balance-toggle", tint: WalletColors.iconMuted) { hidden.toggle() }
                    .accessibilityValue(hidden ? "Hidden" : "Shown")
                    .offset(x: 12)          // the icon lines up with the card's content edge, as on the web
            }
            let shown = hidden ? "••••••" : Money.display(wallet.balance)
            // The currency moves to the next line rather than being squeezed (SPEC L-01)
            ViewThatFits(in: .horizontal) {
                HStack(alignment: .firstTextBaseline, spacing: WalletSpacing.sm) { balance(shown); currency }
                VStack(alignment: .leading, spacing: 0) { balance(shown); currency }
            }
            .accessibilityElement(children: .contain)
            .accessibilityIdentifier("balance-row")
            HStack(spacing: 0) {
                Text("Available balance · ")
                Text(Formats.maskId(wallet.walletId)).accessibilityIdentifier("wallet-id")
            }
            .walletText(WalletType.caption)
            .foregroundStyle(WalletColors.textSecondary)
        }
    }

    private func balance(_ shown: String) -> some View {
        let style = switch Money.balanceStyle(shown) {
        case "Display/Balance": WalletType.displayBalance
        case "Amount/Large": WalletType.amountLarge
        default: WalletType.titleLargeTabular
        }
        return Text(shown)
            .walletText(style)
            .foregroundStyle(WalletColors.textPrimary)
            .fixedSize()
            .accessibilityIdentifier("balance")
    }

    private var currency: some View {
        Text(wallet.currency).walletText(WalletType.bodyStrong).foregroundStyle(WalletColors.textSecondary).fixedSize()
    }
}
