package lab.wallet.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import lab.wallet.ui.components.ButtonStyle
import lab.wallet.ui.components.TopBar
import lab.wallet.ui.components.WalletButton
import lab.wallet.ui.components.WalletCard
import lab.wallet.ui.components.WalletTextField
import lab.wallet.ui.theme.WalletColors
import lab.wallet.ui.theme.WalletSpacing
import lab.wallet.ui.theme.WalletType

/**
 * Start: create a wallet, or open one by its ID (SPEC.md §7.1). Layout only for now: the buttons are
 * wired to the API in the next step.
 */
@Composable
fun StartScreen() {
    var owner by rememberSaveable { mutableStateOf("") }
    var walletId by rememberSaveable { mutableStateOf("") }
    Column(Modifier.fillMaxSize()) {
        TopBar(title = "Wallet")
        Column(
            verticalArrangement = Arrangement.spacedBy(WalletSpacing.lg),
            modifier = Modifier
                .verticalScroll(rememberScrollState())
                .padding(start = WalletSpacing.xl, end = WalletSpacing.xl, top = WalletSpacing.lg, bottom = WalletSpacing.xxl),
        ) {
            Column {
                Text("Open your wallet", style = WalletType.titleLarge, color = WalletColors.textPrimary)
                Text("A practice wallet: no real money, no login.", style = WalletType.body, color = WalletColors.textSecondary)
            }
            WalletCard {
                Text("New wallet", style = WalletType.titleMedium, color = WalletColors.textPrimary)
                WalletTextField("Your name", owner, { owner = it }, testTag = "owner-input", placeholder = "e.g. Alex")
                WalletButton("Create wallet", onClick = {}, testTag = "create-wallet")
            }
            Text(
                "or",
                style = WalletType.caption,
                color = WalletColors.textSecondary,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth(),
            )
            WalletCard {
                Text("Existing wallet", style = WalletType.titleMedium, color = WalletColors.textPrimary)
                WalletTextField("Wallet ID", walletId, { walletId = it }, testTag = "wallet-id-input", placeholder = "w_…")
                WalletButton("Open wallet", onClick = {}, testTag = "open-wallet", style = ButtonStyle.Secondary)
            }
        }
    }
}
