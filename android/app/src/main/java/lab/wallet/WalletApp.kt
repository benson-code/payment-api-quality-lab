package lab.wallet

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.displayCutout
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.union
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.testTagsAsResourceId
import lab.wallet.data.ApiClient
import lab.wallet.data.ApiConfig
import lab.wallet.ui.WalletNavHost
import lab.wallet.ui.theme.WalletColors
import lab.wallet.ui.theme.WalletTheme

/**
 * The app's root. testTagsAsResourceId exposes every Compose testTag as the view's resource-id, so
 * Appium finds the app's elements under the same names as the web's data-testid (SPEC.md §7).
 * The status bar inset is applied here; each screen handles the navigation bar and the keyboard.
 */
@OptIn(ExperimentalComposeUiApi::class)
@Composable
fun WalletApp(config: ApiConfig) {
    val api = remember(config) { ApiClient(config) }
    WalletTheme {
        Box(
            Modifier
                .fillMaxSize()
                .background(WalletColors.bgPage)
                .windowInsetsPadding(WindowInsets.statusBars.union(WindowInsets.displayCutout))
                .semantics { testTagsAsResourceId = true },
        ) {
            WalletNavHost(api)
        }
    }
}
