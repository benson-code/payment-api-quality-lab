package lab.wallet

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.runtime.Composable
import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.testTagsAsResourceId
import lab.wallet.data.ApiConfig
import lab.wallet.ui.screens.StartScreen
import lab.wallet.ui.theme.WalletColors
import lab.wallet.ui.theme.WalletTheme

/**
 * The app's root. testTagsAsResourceId exposes every Compose testTag as the view's resource-id, so
 * Appium finds the app's elements under the same names as the web's data-testid (SPEC.md §7).
 */
@OptIn(ExperimentalComposeUiApi::class)
@Composable
fun WalletApp(config: ApiConfig) {
    WalletTheme {
        Box(
            Modifier
                .fillMaxSize()
                .background(WalletColors.bgPage)
                .windowInsetsPadding(WindowInsets.safeDrawing)
                .semantics { testTagsAsResourceId = true },
        ) {
            StartScreen()
        }
    }
}
