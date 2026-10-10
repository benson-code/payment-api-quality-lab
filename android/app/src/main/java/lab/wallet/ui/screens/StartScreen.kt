package lab.wallet.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import lab.wallet.data.ApiClient
import lab.wallet.data.ApiResult
import lab.wallet.data.Wallet
import lab.wallet.domain.Messages
import lab.wallet.ui.components.ButtonStyle
import lab.wallet.ui.components.Message
import lab.wallet.ui.components.MessageKind
import lab.wallet.ui.components.Screen
import lab.wallet.ui.components.WalletButton
import lab.wallet.ui.components.WalletCard
import lab.wallet.ui.components.WalletTextField
import lab.wallet.ui.theme.WalletColors
import lab.wallet.ui.theme.WalletType

enum class StartForm { New, Existing }

/** [errorForm]: the form whose request failed; its message is shown under that form's button (SPEC L-04). */
data class StartState(val busy: Boolean = false, val error: String? = null, val errorForm: StartForm? = null, val opened: String? = null)

/**
 * Create a wallet, or open one by its ID. There is no login: the wallet ID is the only key, as in the
 * API (a known limitation of this practice project, SPEC.md §10).
 */
class StartViewModel(private val api: ApiClient) : ViewModel() {
    private val _state = MutableStateFlow(StartState())
    val state = _state.asStateFlow()

    fun create(owner: String) = run(StartForm.New) { api.createWallet(owner) }
    fun open(walletId: String) = run(StartForm.Existing) { api.getWallet(walletId.trim()) }

    private fun run(form: StartForm, call: suspend () -> ApiResult<Wallet>) {
        if (_state.value.busy) return
        _state.value = StartState(busy = true)
        viewModelScope.launch {
            _state.value = when (val r = call()) {
                is ApiResult.Ok -> StartState(opened = r.value.walletId)
                is ApiResult.Refused -> StartState(error = Messages.forCode(r.code), errorForm = form)
                ApiResult.NoAnswer -> StartState(error = Messages.NO_ANSWER_TRY_AGAIN, errorForm = form)
            }
        }
    }

    fun navigated() { _state.value = StartState() }
}

@Composable
fun StartScreen(vm: StartViewModel, onOpened: (walletId: String) -> Unit) {
    val state by vm.state.collectAsStateWithLifecycle()
    var owner by rememberSaveable { mutableStateOf("") }
    var walletId by rememberSaveable { mutableStateOf("") }
    LaunchedEffect(state.opened) {
        state.opened?.let { vm.navigated(); onOpened(it) }
    }
    Screen(title = "Wallet") {
        Column {
            Text("Open your wallet", style = WalletType.titleLarge, color = WalletColors.textPrimary)
            Text("A practice wallet: no real money, no login.", style = WalletType.body, color = WalletColors.textSecondary)
        }
        WalletCard {
            Text("New wallet", style = WalletType.titleMedium, color = WalletColors.textPrimary)
            WalletTextField("Your name", owner, { owner = it }, testTag = "owner-input", placeholder = "e.g. Alex")
            WalletButton("Create wallet", onClick = { vm.create(owner) }, testTag = "create-wallet", enabled = !state.busy)
            if (state.errorForm == StartForm.New) state.error?.let { Message(MessageKind.Error, it, testTag = "error-message") }
        }
        Text("or", style = WalletType.caption, color = WalletColors.textSecondary, textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth())
        WalletCard {
            Text("Existing wallet", style = WalletType.titleMedium, color = WalletColors.textPrimary)
            WalletTextField("Wallet ID", walletId, { walletId = it }, testTag = "wallet-id-input", placeholder = "w_…")
            WalletButton("Open wallet", onClick = { vm.open(walletId) }, testTag = "open-wallet",
                style = ButtonStyle.Secondary, enabled = !state.busy)
            if (state.errorForm == StartForm.Existing) state.error?.let { Message(MessageKind.Error, it, testTag = "error-message") }
        }
    }
}
