package lab.wallet.ui.screens

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import lab.wallet.data.ApiClient
import lab.wallet.data.ApiResult
import lab.wallet.data.Payment
import lab.wallet.data.Wallet
import lab.wallet.domain.Attempt
import lab.wallet.domain.Formats
import lab.wallet.domain.Messages
import lab.wallet.domain.Money
import lab.wallet.ui.components.AmountField
import lab.wallet.ui.components.ButtonStyle
import lab.wallet.ui.components.Message
import lab.wallet.ui.components.MessageKind
import lab.wallet.ui.components.ReceiptRow
import lab.wallet.ui.components.RowDivider
import lab.wallet.ui.components.Screen
import lab.wallet.ui.components.WalletButton
import lab.wallet.ui.components.WalletCard
import lab.wallet.ui.theme.WalletColors
import lab.wallet.ui.theme.WalletSpacing
import lab.wallet.ui.theme.WalletType

/**
 * Pay: enter the amount, review it on Confirm, then the receipt (SPEC.md §7.5). Same behaviour as
 * web/src/screens/Pay.jsx.
 *
 * The Idempotency-Key is created when Confirm payment is tapped (Attempt). Confirm has four states:
 * ready, processing (a second tap sends nothing, Cancel and Back are disabled), refused (nothing was
 * charged; the next confirm is a new attempt) and no answer (Retry sends the same key again). After
 * no answer the attempt survives Back: continuing with the same amount shows "no answer" again, and
 * only a different amount starts a new attempt (K-05).
 *
 * K-08: the step, the amount and a pending attempt (amount and key) are kept in the SavedStateHandle,
 * so they survive the app's process being killed in the background. Reopened, the app shows Confirm
 * with "no answer" and Retry resends the saved key: the web cannot do this (SPEC.md §10).
 *
 * N-01: the receipt is kept there too. Without it, a process killed on the receipt reopened on Confirm,
 * ready to send the same amount again with a new key: a second payment (found in the QA pass, APP-017).
 */
class PayViewModel(private val api: ApiClient, private val walletId: String, private val saved: SavedStateHandle) : ViewModel() {
    val attempt = Attempt(idempotent = true)
    val amount = saved.getStateFlow(AMOUNT, "")
    val step = saved.getStateFlow(STEP, STEP_AMOUNT)
    private val _wallet = MutableStateFlow<Wallet?>(null)
    val wallet = _wallet.asStateFlow()
    private val _result = MutableStateFlow<ApiResult.Ok<Payment>?>(null)
    val result = _result.asStateFlow()

    init {
        val pendingAmount = saved.get<String>(PENDING_AMOUNT)
        if (pendingAmount != null) attempt.restore(pendingAmount, saved.get<String>(PENDING_KEY))
        if (step.value == STEP_RECEIPT) {
            val receipt = restoreReceipt()
            if (receipt != null) {
                _result.value = receipt
            } else {
                // Never fall back to Confirm from a receipt: without its fields, start again from the amount step
                saved[STEP] = STEP_AMOUNT
                saved[AMOUNT] = ""
            }
        }
        viewModelScope.launch {
            attempt.state.collect { state ->
                // A request in flight or without an answer may have been charged: keep its key until the outcome is known
                if (state == Attempt.State.Pending || state == Attempt.State.Unknown) {
                    saved[PENDING_AMOUNT] = attempt.pendingAmount
                    saved[PENDING_KEY] = attempt.pendingKey
                } else {
                    saved.remove<String>(PENDING_AMOUNT)
                    saved.remove<String>(PENDING_KEY)
                }
            }
        }
        viewModelScope.launch { (api.getWallet(walletId) as? ApiResult.Ok)?.let { _wallet.value = it.value } }
    }

    fun setAmount(value: String) { saved[AMOUNT] = value }

    /** Continue: a different amount from a pending attempt's is a new payment. */
    fun toConfirm() {
        val pending = attempt.pendingAmount
        if (pending != null && !Money.sameAmount(pending, amount.value)) attempt.reset()
        saved[STEP] = STEP_CONFIRM
    }

    /** Back, Cancel or Change amount. A pending attempt is kept (K-05); a refusal's message is cleared. */
    fun changeAmount() {
        if (attempt.state.value != Attempt.State.Unknown) attempt.reset()
        saved[STEP] = STEP_AMOUNT
    }

    fun confirm() {
        viewModelScope.launch {
            val r = attempt.submit(amount.value) { a, key -> api.pay(walletId, a, key!!) }
            if (r is ApiResult.Ok) {
                saveReceipt(r)
                _result.value = r
            }
        }
    }

    /** What the receipt shows, saved before it is shown: a payment that went through is never offered again. */
    private fun saveReceipt(ok: ApiResult.Ok<Payment>) {
        val p = ok.value
        saved[RECEIPT_ID] = p.paymentId
        saved[RECEIPT_AMOUNT] = p.amount
        saved[RECEIPT_CREATED] = p.createdAt
        saved[RECEIPT_BALANCE] = p.balanceAfter
        saved[RECEIPT_REPLAYED] = ok.replayed
        saved[STEP] = STEP_RECEIPT
    }

    private fun restoreReceipt(): ApiResult.Ok<Payment>? {
        val id = saved.get<String>(RECEIPT_ID) ?: return null
        val payment = Payment(id, walletId, saved.get<String>(RECEIPT_AMOUNT) ?: return null, refunded = "0.00",
            createdAt = saved.get<String>(RECEIPT_CREATED) ?: return null, balanceAfter = saved.get<String>(RECEIPT_BALANCE),
            refunds = emptyList())
        return ApiResult.Ok(payment, replayed = saved.get<Boolean>(RECEIPT_REPLAYED) ?: false)
    }

    companion object {
        private const val AMOUNT = "amount"
        private const val STEP = "step"
        private const val PENDING_AMOUNT = "pendingAmount"
        private const val PENDING_KEY = "pendingKey"
        private const val RECEIPT_ID = "receiptPaymentId"
        private const val RECEIPT_AMOUNT = "receiptAmount"
        private const val RECEIPT_CREATED = "receiptCreatedAt"
        private const val RECEIPT_BALANCE = "receiptBalanceAfter"
        private const val RECEIPT_REPLAYED = "receiptReplayed"
        const val STEP_AMOUNT = "amount"
        const val STEP_CONFIRM = "confirm"
        const val STEP_RECEIPT = "receipt"
    }
}

@Composable
fun PayScreen(vm: PayViewModel, formats: Formats, onBack: () -> Unit, onDone: () -> Unit, onViewPayment: (String) -> Unit) {
    val amount by vm.amount.collectAsStateWithLifecycle()
    val step by vm.step.collectAsStateWithLifecycle()
    val wallet by vm.wallet.collectAsStateWithLifecycle()
    val result by vm.result.collectAsStateWithLifecycle()
    val state by vm.attempt.state.collectAsStateWithLifecycle()

    result?.let { ok ->
        val p = ok.value
        // N-01: Back on the receipt goes Home, never back to Confirm
        BackHandler { onDone() }
        Receipt(
            title = "Payment",
            heading = "Payment completed",
            amount = p.amount,
            replayed = ok.replayed,
            actions = {
                WalletButton("Done", onClick = onDone, testTag = "done")
                WalletButton("View payment", onClick = { onViewPayment(p.paymentId) }, testTag = "view-payment", style = ButtonStyle.Ghost)
            },
        ) {
            ReceiptRow("Status", "Completed")
            RowDivider()
            ReceiptRow("Time", formats.dateTime(p.createdAt))
            RowDivider()
            ReceiptRow("Payment ID", p.paymentId, valueTestTag = "result-payment-id")
            p.balanceAfter?.let {
                RowDivider()
                ReceiptRow("Balance after", Money.display(it), valueTestTag = "result-balance", suffix = "TWD")
            }
        }
        return
    }

    if (step == PayViewModel.STEP_AMOUNT) {
        Screen(
            title = "Pay",
            onBack = onBack,
            bottom = { WalletButton("Continue", onClick = vm::toConfirm, testTag = "submit", enabled = amount.isNotBlank()) },
        ) {
            wallet?.let { Available(it) }
            AmountField(amount, vm::setAmount)
        }
        return
    }

    // Confirm. The amount is shown as the API will read it when it is a plain amount, else as typed.
    val pending = state == Attempt.State.Pending
    val normalized = Money.normalize(amount)
    val after = if (normalized != null && wallet != null) Money.toCents(wallet!!.balance) - Money.toCents(normalized) else null
    // N-01: system Back does what the top bar's back does; while processing it does nothing
    BackHandler { if (!pending) vm.changeAmount() }
    Screen(
        title = "Confirm payment",
        onBack = vm::changeAmount,
        backEnabled = !pending,
        bottom = {
            when (state) {
                Attempt.State.Unknown -> {
                    WalletButton("Retry", onClick = vm::confirm, testTag = "retry")
                    WalletButton("Back to wallet", onClick = onDone, testTag = "back-to-wallet", style = ButtonStyle.Ghost)
                }
                is Attempt.State.Refused -> {
                    WalletButton("Confirm payment", onClick = vm::confirm, testTag = "confirm-pay")
                    WalletButton("Change amount", onClick = vm::changeAmount, testTag = "change-amount", style = ButtonStyle.Ghost)
                }
                else -> {
                    WalletButton("Confirm payment", onClick = vm::confirm, testTag = "confirm-pay", loading = pending)
                    WalletButton("Cancel", onClick = vm::changeAmount, testTag = "cancel", style = ButtonStyle.Ghost, enabled = !pending)
                }
            }
        },
    ) {
        WalletCard(spacing = WalletSpacing.xs) {
            Text("You pay", style = WalletType.label, color = WalletColors.textSecondary)
            Row {
                Text(normalized?.let { Money.display(it) } ?: amount, style = WalletType.amountLarge,
                    color = WalletColors.textPrimary, modifier = Modifier.testTag("confirm-amount"))
                Text(" TWD", style = WalletType.amountLarge, color = WalletColors.textPrimary)
            }
            wallet?.let { ReceiptRow("From", "${it.owner} · ${Formats.maskId(it.walletId)}") }
            if (after != null && after >= 0) {
                RowDivider()
                ReceiptRow("Balance after", Money.display(Money.fromCents(after)), valueTestTag = "confirm-balance-after", suffix = "TWD")
            }
        }
        when (val s = state) {
            is Attempt.State.Refused -> Message(MessageKind.Error, s.message, testTag = "error-message")
            Attempt.State.Unknown -> Message(MessageKind.Warning, Messages.PAY_NO_ANSWER, testTag = "no-answer")
            else -> {}
        }
    }
}

/** "Available 68.00 TWD"; the hook "balance" holds the number only. */
@Composable
fun Available(wallet: Wallet) {
    Row {
        Text("Available ", style = WalletType.body, color = WalletColors.textSecondary)
        Text(Money.display(wallet.balance), style = WalletType.body, color = WalletColors.textSecondary, modifier = Modifier.testTag("balance"))
        Text(" ${wallet.currency}", style = WalletType.body, color = WalletColors.textSecondary)
    }
}
