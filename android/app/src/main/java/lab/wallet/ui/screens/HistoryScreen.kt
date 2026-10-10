package lab.wallet.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.style.TextAlign
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.LifecycleResumeEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import lab.wallet.data.ApiClient
import lab.wallet.data.Entry
import lab.wallet.domain.Formats
import lab.wallet.ui.components.Message
import lab.wallet.ui.components.MessageKind
import lab.wallet.ui.components.Screen
import lab.wallet.ui.components.SectionHeader
import lab.wallet.ui.components.Tab
import lab.wallet.ui.components.TabBar
import lab.wallet.ui.components.WalletCard
import lab.wallet.ui.theme.WalletColors
import lab.wallet.ui.theme.WalletSpacing
import lab.wallet.ui.theme.WalletType

/** History tab: the ledger, newest first, grouped by day (SPEC.md §7.3, D-03, D-05). */
class HistoryViewModel(private val api: ApiClient, private val walletId: String) : ViewModel() {
    private val _state = MutableStateFlow(Loaded<List<Entry>>())
    val state = _state.asStateFlow()

    fun load() {
        viewModelScope.launch {
            val loaded = api.transactions(walletId).toLoaded()
            _state.value = Loaded(loaded.data?.reversed(), loaded.error)
        }
    }
}

@Composable
fun HistoryScreen(vm: HistoryViewModel, formats: Formats, onHome: () -> Unit, onPay: () -> Unit, onOpenPayment: (String) -> Unit) {
    val state by vm.state.collectAsStateWithLifecycle()
    LifecycleResumeEffect(Unit) {
        vm.load()
        onPauseOrDispose { }
    }
    Screen(
        title = "History",
        tabBar = {
            TabBar(Tab.History) { tab ->
                when (tab) {
                    Tab.Home -> onHome
                    Tab.History -> null
                    Tab.Pay -> onPay
                }
            }
        },
    ) {
        state.error?.let { Message(MessageKind.Error, it, testTag = "error-message") }
        state.data?.let { entries ->
            if (entries.isEmpty()) {
                WalletCard {
                    Text("No transactions yet.", style = WalletType.body, color = WalletColors.textSecondary,
                        textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth().testTag("empty"))
                }
            }
            for ((label, items) in formats.groupByDay(entries) { it.createdAt }) {
                Column(verticalArrangement = Arrangement.spacedBy(WalletSpacing.sm)) {
                    SectionHeader(label)
                    EntryList(items, formats, rowTag = "history-item", onOpenPayment)
                }
            }
        }
    }
}
