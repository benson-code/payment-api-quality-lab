package lab.wallet.ui.screens

import androidx.compose.foundation.layout.Row
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import lab.wallet.data.ApiClient
import lab.wallet.data.ApiResult
import lab.wallet.data.TopUp
import lab.wallet.data.Wallet
import lab.wallet.domain.Attempt
import lab.wallet.domain.Messages
import lab.wallet.domain.Money
import lab.wallet.ui.components.AmountField
import lab.wallet.ui.components.Message
import lab.wallet.ui.components.MessageKind
import lab.wallet.ui.components.RowDivider
import lab.wallet.ui.components.ReceiptRow
import lab.wallet.ui.components.Screen
import lab.wallet.ui.components.WalletButton
import lab.wallet.ui.theme.WalletColors
import lab.wallet.ui.theme.WalletType

/**
 * Top up: one step (SPEC.md §7.4). Top-ups take no Idempotency-Key in this API, so there is no safe
 * retry: after no answer the user is asked to check the balance first (K-07).
 */
class TopUpViewModel(private val api: ApiClient, private val walletId: String) : ViewModel() {
    val attempt = Attempt(idempotent = false)
    private val _amount = MutableStateFlow("")
    val amount = _amount.asStateFlow()
    private val _wallet = MutableStateFlow<Wallet?>(null)
    val wallet = _wallet.asStateFlow()
    private val _result = MutableStateFlow<TopUp?>(null)
    val result = _result.asStateFlow()

    init {
        viewModelScope.launch { (api.getWallet(walletId) as? ApiResult.Ok)?.let { _wallet.value = it.value } }
    }

    fun edit(value: String) {
        attempt.reset()          // a different amount, and any message about the last one goes away
        _amount.value = value
    }

    fun submit() {
        viewModelScope.launch {
            val r = attempt.submit(_amount.value) { amount, _ -> api.topUp(walletId, amount) }
            if (r is ApiResult.Ok) _result.value = r.value
        }
    }
}

@Composable
fun TopUpScreen(vm: TopUpViewModel, onBack: () -> Unit, onDone: () -> Unit) {
    val amount by vm.amount.collectAsStateWithLifecycle()
    val wallet by vm.wallet.collectAsStateWithLifecycle()
    val result by vm.result.collectAsStateWithLifecycle()
    val state by vm.attempt.state.collectAsStateWithLifecycle()

    result?.let { done ->
        Receipt(
            title = "Top up",
            heading = "Top-up completed",
            amount = done.amount,
            actions = { WalletButton("Done", onClick = onDone, testTag = "done") },
        ) {
            ReceiptRow("Status", "Completed")
            RowDivider()
            ReceiptRow("Balance after", Money.display(done.balance), valueTestTag = "result-balance", suffix = "TWD")
        }
        return
    }

    val pending = state == Attempt.State.Pending
    Screen(
        title = "Top up",
        onBack = onBack,
        bottom = {
            WalletButton("Top up", onClick = vm::submit, testTag = "submit", enabled = amount.isNotBlank(), loading = pending)
        },
    ) {
        wallet?.let {
            Row {
                Text("Available ", style = WalletType.body, color = WalletColors.textSecondary)
                Text(Money.display(it.balance), style = WalletType.body, color = WalletColors.textSecondary, modifier = Modifier.testTag("balance"))
                Text(" ${it.currency}", style = WalletType.body, color = WalletColors.textSecondary)
            }
        }
        AmountField(amount, vm::edit, enabled = !pending, error = (state as? Attempt.State.Refused)?.message)
        if (state == Attempt.State.Unknown) {
            Message(MessageKind.Warning, Messages.TOP_UP_NO_ANSWER, testTag = "no-answer")
        }
    }
}
