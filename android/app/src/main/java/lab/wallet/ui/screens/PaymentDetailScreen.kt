package lab.wallet.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.material3.Text
import androidx.compose.foundation.relocation.BringIntoViewRequester
import androidx.compose.foundation.relocation.bringIntoViewRequester
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import lab.wallet.data.ApiClient
import lab.wallet.data.ApiResult
import lab.wallet.data.Payment
import lab.wallet.data.RefundResult
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
import lab.wallet.ui.components.SectionHeader
import lab.wallet.ui.components.TransactionRow
import lab.wallet.ui.components.WalletButton
import lab.wallet.ui.components.WalletCard
import lab.wallet.ui.theme.WalletColors
import lab.wallet.ui.theme.WalletSpacing
import lab.wallet.ui.theme.WalletType

/**
 * A payment, its refunds and a refund form (SPEC.md §7.6). Same behaviour as
 * web/src/screens/PaymentDetail.jsx. What is left to refund is computed in integer cents (R-03).
 *
 * Refunds are idempotent: after no answer the button becomes Retry and sends the same key again. The
 * field can be edited without dropping the pending attempt; the button reads Retry only while it holds
 * the pending amount, and submitting a different amount starts a new attempt (K-05).
 */
class PaymentDetailViewModel(private val api: ApiClient, private val paymentId: String) : ViewModel() {
    val attempt = Attempt(idempotent = true)
    private val _payment = MutableStateFlow(Loaded<Payment>())
    val payment = _payment.asStateFlow()
    private val _amount = MutableStateFlow("")
    val amount = _amount.asStateFlow()
    private val _last = MutableStateFlow<RefundResult?>(null)
    val last = _last.asStateFlow()

    init { viewModelScope.launch { reload() } }

    private suspend fun reload() {
        _payment.value = api.getPayment(paymentId).toLoaded()
    }

    fun edit(value: String) {
        attempt.clearRefusal()
        _amount.value = value
        _last.value = null
    }

    fun submit() {
        viewModelScope.launch {
            val r = attempt.submit(_amount.value) { a, key -> api.refund(paymentId, a, key!!) }
            if (r is ApiResult.Ok) {
                // Reload first, then show the message: the refund list appears above the form, and a
                // message shown before it would be pushed below the visible area (SPEC L-04). The web
                // keeps it in view through the browser's scroll anchoring; Compose has none.
                reload()
                _amount.value = ""
                _last.value = r.value
            }
        }
    }
}

@Composable
fun PaymentDetailScreen(vm: PaymentDetailViewModel, formats: Formats, onBack: () -> Unit) {
    val loaded by vm.payment.collectAsStateWithLifecycle()
    val amount by vm.amount.collectAsStateWithLifecycle()
    val last by vm.last.collectAsStateWithLifecycle()
    val state by vm.attempt.state.collectAsStateWithLifecycle()
    val pending = state == Attempt.State.Pending
    val retrying = state == Attempt.State.Unknown && Money.sameAmount(vm.attempt.pendingAmount ?: "", amount)

    Screen(title = "Payment", onBack = onBack) {
        loaded.error?.let { Message(MessageKind.Error, it, testTag = "error-message") }
        loaded.data?.let { p ->
            WalletCard(spacing = WalletSpacing.xs) {
                Text("Paid · ${formats.dateTime(p.createdAt)}", style = WalletType.caption, color = WalletColors.textSecondary)
                Row {
                    Text(Money.display(p.amount), style = WalletType.amountLarge, color = WalletColors.textPrimary,
                        modifier = Modifier.testTag("payment-amount"))
                    Text(" TWD", style = WalletType.amountLarge, color = WalletColors.textPrimary)
                }
                ReceiptRow("Refunded", Money.display(p.refunded), valueTestTag = "payment-refunded")
                RowDivider()
                ReceiptRow("Left to refund", Money.display(Money.fromCents(Money.toCents(p.amount) - Money.toCents(p.refunded))),
                    valueTestTag = "payment-refundable")
                RowDivider()
                ReceiptRow("Payment ID", p.paymentId)
            }
            if (p.refunds.isNotEmpty()) {
                Column(verticalArrangement = Arrangement.spacedBy(WalletSpacing.sm)) {
                    SectionHeader("Refunds")
                    WalletCard(spacing = 0.dp, padding = PaddingValues(horizontal = WalletSpacing.lg, vertical = WalletSpacing.xs)) {
                        p.refunds.forEachIndexed { i, r ->
                            if (i > 0) RowDivider()
                            TransactionRow("Refund", formats.dateTime(r.createdAt), r.amount, null, testTag = "refund-item")
                        }
                    }
                }
            }
            // The whole form (field, message, button) comes into view when its state changes: a message
            // alone is not enough when the action it asks for (Retry) sits below it (SPEC L-04).
            val form = remember { BringIntoViewRequester() }
            LaunchedEffect(state, last) { if (state != Attempt.State.Idle || last != null) form.bringIntoView() }
            Column(Modifier.bringIntoViewRequester(form), verticalArrangement = Arrangement.spacedBy(WalletSpacing.sm)) {
                AmountField(amount, vm::edit, label = "Refund amount", enabled = !pending,
                    error = (state as? Attempt.State.Refused)?.message)
                last?.let {
                    Message(MessageKind.Success,
                        "Refunded ${Money.display(it.amount)} TWD. New balance ${Money.display(it.balanceAfter)} TWD.", testTag = "refund-done")
                }
                if (state == Attempt.State.Unknown) Message(MessageKind.Warning, Messages.REFUND_NO_ANSWER, testTag = "no-answer")
                if (retrying) {
                    WalletButton("Retry", onClick = vm::submit, testTag = "retry", style = ButtonStyle.Secondary)
                } else {
                    WalletButton("Refund", onClick = vm::submit, testTag = "submit", style = ButtonStyle.Secondary,
                        enabled = amount.isNotBlank(), loading = pending)
                }
            }
        }
    }
}
