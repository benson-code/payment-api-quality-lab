package lab.wallet.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import lab.wallet.ui.theme.WalletSpacing

/**
 * A screen: top bar, scrollable content, then either a tab bar or the screen's own bottom actions
 * (kept above the keyboard). The same padding as the web's `.content`: 16 top, 20 sides, 16 between
 * blocks. The status bar inset is applied once at the root (WalletApp).
 */
@Composable
fun Screen(
    title: String,
    onBack: (() -> Unit)? = null,
    backEnabled: Boolean = true,
    tabBar: (@Composable () -> Unit)? = null,
    bottom: (@Composable ColumnScope.() -> Unit)? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    val outer = if (tabBar == null) Modifier.fillMaxSize().navigationBarsPadding().imePadding() else Modifier.fillMaxSize()
    Column(outer) {
        TopBar(title, onBack, backEnabled)
        Column(
            verticalArrangement = Arrangement.spacedBy(WalletSpacing.lg),
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(start = WalletSpacing.xl, end = WalletSpacing.xl, top = WalletSpacing.lg, bottom = WalletSpacing.xxl),
            content = content,
        )
        if (bottom != null) {
            Column(
                verticalArrangement = Arrangement.spacedBy(WalletSpacing.sm),
                modifier = Modifier.fillMaxWidth().padding(start = WalletSpacing.xl, end = WalletSpacing.xl, bottom = WalletSpacing.lg),
                content = bottom,
            )
        }
        tabBar?.invoke()
    }
}
