package lab.wallet.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.platform.testTag
import lab.wallet.R
import lab.wallet.domain.Money
import lab.wallet.ui.components.Message
import lab.wallet.ui.components.MessageKind
import lab.wallet.ui.components.Screen
import lab.wallet.ui.components.WalletCard
import lab.wallet.ui.components.WalletIcon
import lab.wallet.ui.theme.WalletColors
import lab.wallet.ui.theme.WalletSpacing
import lab.wallet.ui.theme.WalletType

/**
 * The screen after a top-up or payment went through (hook "result"). No back button: the money has
 * moved, and the way on is Done. [replayed]: the API answered Idempotent-Replayed: true (SPEC K-06).
 */
@Composable
fun Receipt(
    title: String,
    heading: String,
    amount: String,
    replayed: Boolean = false,
    actions: @Composable ColumnScope.() -> Unit,
    rows: @Composable ColumnScope.() -> Unit,
) {
    Screen(title = title, bottom = actions) {
        Column(Modifier.testTag("result"), verticalArrangement = Arrangement.spacedBy(WalletSpacing.lg)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(WalletSpacing.sm)) {
                WalletIcon(R.drawable.ic_check_circle, WalletColors.amountCredit)
                Text(heading, style = WalletType.titleLarge, color = WalletColors.textPrimary)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(WalletSpacing.sm)) {
                Text(Money.display(amount), style = WalletType.displayBalance, color = WalletColors.textPrimary,
                    modifier = Modifier.alignByBaseline().testTag("result-amount"))
                Text("TWD", style = WalletType.bodyStrong, color = WalletColors.textSecondary, modifier = Modifier.alignByBaseline())
            }
            if (replayed) {
                Message(MessageKind.Success, "This payment had already gone through. You were not charged again.", testTag = "replayed")
            }
            WalletCard(spacing = 0.dp, padding = PaddingValues(horizontal = WalletSpacing.xl, vertical = WalletSpacing.xs), content = rows)
        }
    }
}
