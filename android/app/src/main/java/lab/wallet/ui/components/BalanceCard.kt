package lab.wallet.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.offset
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.unit.dp
import lab.wallet.R
import lab.wallet.data.Wallet
import lab.wallet.domain.Formats
import lab.wallet.domain.Money
import lab.wallet.ui.theme.WalletColors
import lab.wallet.ui.theme.WalletSpacing
import lab.wallet.ui.theme.WalletType

/** The balance's text style, stepped down for long amounts (SPEC L-01, Money.balanceStyle). */
private fun balanceStyle(shown: String) = when (Money.balanceStyle(shown)) {
    "Display/Balance" -> WalletType.displayBalance
    "Amount/Large" -> WalletType.amountLarge
    else -> WalletType.titleLarge.copy(fontFeatureSettings = "tnum")
}

/**
 * Figma: Balance card (Hidden = False | True). The eye button hides the balance (SPEC D-06); the choice
 * is not kept across screens. The wallet ID is shown masked (D-04).
 */
@Composable
fun BalanceCard(wallet: Wallet) {
    var hidden by remember { mutableStateOf(false) }
    WalletCard(spacing = WalletSpacing.xs) {
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.fillMaxWidth()) {
            Text(wallet.owner, style = WalletType.bodyStrong, color = WalletColors.textPrimary,
                modifier = Modifier.weight(1f).testTag("owner"))
            // Pulled right so the icon lines up with the card's content edge, as on the web
            Row(Modifier.offset(x = 12.dp).semantics { stateDescription = if (hidden) "Hidden" else "Shown" }) {
                IconButton(
                    icon = if (hidden) R.drawable.ic_eye_off else R.drawable.ic_eye,
                    label = if (hidden) "Show balance" else "Hide balance",
                    testTag = "balance-toggle",
                    tint = WalletColors.iconMuted,
                    onClick = { hidden = !hidden },
                )
            }
        }
        // The currency moves to the next line rather than being squeezed into a column (SPEC L-01)
        val shown = if (hidden) "••••••" else Money.display(wallet.balance)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(WalletSpacing.sm)) {
            Text(shown, style = balanceStyle(shown), color = WalletColors.textPrimary,
                modifier = Modifier.alignByBaseline().testTag("balance"))
            Text(wallet.currency, style = WalletType.bodyStrong, color = WalletColors.textSecondary, softWrap = false,
                modifier = Modifier.alignByBaseline())
        }
        Row {
            Text("Available balance · ", style = WalletType.caption, color = WalletColors.textSecondary)
            Text(Formats.maskId(wallet.walletId), style = WalletType.caption, color = WalletColors.textSecondary,
                modifier = Modifier.testTag("wallet-id"))
        }
    }
}
