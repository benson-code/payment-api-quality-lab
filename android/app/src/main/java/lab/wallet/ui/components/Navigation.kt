package lab.wallet.ui.components

import androidx.annotation.DrawableRes
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import lab.wallet.R
import lab.wallet.ui.theme.WalletColors
import lab.wallet.ui.theme.WalletSpacing
import lab.wallet.ui.theme.WalletType

enum class Tab(val label: String, @DrawableRes val icon: Int, val testTag: String) {
    Home("Home", R.drawable.ic_home, "tab-home"),
    Pay("Pay", R.drawable.ic_send, "tab-pay"),
    History("History", R.drawable.ic_history, "tab-history"),
}

/**
 * Figma: Tab bar (Active = Home | Pay | History). 64 dp on a surface that runs on under the system
 * navigation bar. The active tab is marked selected for assistive technology. A tab with no action
 * in [onSelect] is shown but inactive.
 */
@Composable
fun TabBar(active: Tab, onSelect: (Tab) -> (() -> Unit)?) {
    Column(Modifier.fillMaxWidth().background(WalletColors.bgSurface).navigationBarsPadding()) {
        HorizontalDivider(thickness = 1.dp, color = WalletColors.borderDefault)
        Row(Modifier.fillMaxWidth().height(63.dp)) {
            for (tab in Tab.entries) {
                val on = tab == active
                val action = onSelect(tab)
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(2.dp, Alignment.CenterVertically),
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxHeight()
                        .testTag(tab.testTag)
                        .semantics { selected = on }
                        .alpha(if (action == null && !on) 0.4f else 1f)
                        .clickable(enabled = action != null, role = Role.Tab) { action?.invoke() },
                ) {
                    WalletIcon(tab.icon, if (on) WalletColors.actionPrimary else WalletColors.iconMuted)
                    Text(tab.label, style = if (on) WalletType.label else WalletType.caption,
                        color = if (on) WalletColors.textPrimary else WalletColors.textSecondary)
                }
            }
        }
    }
}

/** Figma: Quick action. Line icon in the primary colour over a label; the whole cell is the touch target. */
@Composable
fun QuickAction(label: String, @DrawableRes icon: Int, testTag: String, modifier: Modifier = Modifier, onClick: (() -> Unit)?) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(WalletSpacing.sm, Alignment.CenterVertically),
        modifier = modifier
            .height(76.dp)
            .testTag(testTag)
            .alpha(if (onClick == null) 0.4f else 1f)
            .clickable(enabled = onClick != null, role = Role.Button) { onClick?.invoke() }
            .padding(horizontal = WalletSpacing.xs),
    ) {
        WalletIcon(icon, WalletColors.actionPrimary)
        Text(label, style = WalletType.label, color = WalletColors.textPrimary)
    }
}
