package lab.wallet.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.style.TextAlign
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.LifecycleResumeEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import lab.wallet.R
import lab.wallet.data.ApiClient
import lab.wallet.data.Entry
import lab.wallet.data.Wallet
import lab.wallet.domain.Formats
import lab.wallet.ui.components.ButtonStyle
import lab.wallet.ui.components.Message
import lab.wallet.ui.components.MessageKind
import lab.wallet.ui.components.QuickAction
import lab.wallet.ui.components.RowDivider
import lab.wallet.ui.components.Screen
import lab.wallet.ui.components.SectionHeader
import lab.wallet.ui.components.Tab
import lab.wallet.ui.components.TabBar
import lab.wallet.ui.components.TransactionRow
import lab.wallet.ui.components.WalletButton
import lab.wallet.ui.components.WalletCard
import lab.wallet.ui.components.BalanceCard
import lab.wallet.ui.theme.WalletColors
import lab.wallet.ui.theme.WalletSpacing
import lab.wallet.ui.theme.WalletType

private const val RECENT = 3

data class HomeState(val wallet: Loaded<Wallet> = Loaded(), val recent: List<Entry>? = null)

/** Home tab: balance, the three actions and the latest ledger entries (SPEC.md §7.2). */
class HomeViewModel(private val api: ApiClient, private val walletId: String) : ViewModel() {
    private val _state = MutableStateFlow(HomeState())
    val state = _state.asStateFlow()

    /** Called each time the screen is shown, so a top-up just made appears on return. */
    fun load() {
        viewModelScope.launch {
            val wallet = async { api.getWallet(walletId).toLoaded() }
            val ledger = async { api.transactions(walletId).toLoaded() }
            _state.value = HomeState(wallet.await(), ledger.await().data?.reversed()?.take(RECENT))
        }
    }
}

@Composable
fun HomeScreen(
    vm: HomeViewModel,
    formats: Formats,
    onTopUp: () -> Unit,
    onHistory: () -> Unit,
    onSwitchWallet: () -> Unit,
) {
    val state by vm.state.collectAsStateWithLifecycle()
    LifecycleResumeEffect(Unit) {
        vm.load()
        onPauseOrDispose { }
    }
    Screen(
        title = "Wallet",
        tabBar = {
            TabBar(Tab.Home) { tab ->
                when (tab) {
                    Tab.Home -> null
                    Tab.History -> onHistory
                    Tab.Pay -> null              // the pay flow arrives with the payment screens
                }
            }
        },
    ) {
        state.wallet.error?.let { Message(MessageKind.Error, it, testTag = "error-message") }
        state.wallet.data?.let { wallet ->
            BalanceCard(wallet)
            WalletCard(spacing = WalletSpacing.sm, padding = PaddingValues(WalletSpacing.sm)) {
                Row(Modifier.fillMaxWidth()) {
                    QuickAction("Top up", R.drawable.ic_plus, "go-topup", Modifier.weight(1f), onTopUp)
                    QuickAction("Pay", R.drawable.ic_send, "go-pay", Modifier.weight(1f), null)
                    QuickAction("History", R.drawable.ic_history, "go-history", Modifier.weight(1f), onHistory)
                }
            }
            state.recent?.let { recent ->
                Column(verticalArrangement = Arrangement.spacedBy(WalletSpacing.sm)) {
                    SectionHeader("Recent activity")
                    if (recent.isEmpty()) {
                        WalletCard {
                            Text("No transactions yet.", style = WalletType.body, color = WalletColors.textSecondary,
                                textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth().testTag("recent-empty"))
                        }
                    } else {
                        EntryList(recent, formats, rowTag = "recent-item")
                    }
                }
            }
            WalletButton("Use another wallet", onClick = onSwitchWallet, testTag = "switch-wallet", style = ButtonStyle.Ghost)
        }
    }
}

/** Ledger entries in a list card, newest first, separated by hairlines. */
@Composable
fun EntryList(entries: List<Entry>, formats: Formats, rowTag: String) {
    WalletCard(spacing = 0.dp, padding = PaddingValues(horizontal = WalletSpacing.lg, vertical = WalletSpacing.xs)) {
        entries.forEachIndexed { i, e ->
            if (i > 0) RowDivider()
            TransactionRow(Formats.typeLabel(e.type), formats.time(e.createdAt), e.amount, e.balanceAfter, rowTag)
        }
    }
}
