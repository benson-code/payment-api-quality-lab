import Observation
import SwiftUI

/// Pay: enter the amount, review it on Confirm, then the receipt (SPEC.md §7.5). Same behaviour as
/// web/src/screens/Pay.jsx and the Android PayScreen.kt.
///
/// The Idempotency-Key is created when Confirm payment is tapped (Attempt). Confirm has four states:
/// ready, processing (a second tap sends nothing, Cancel and Back are disabled), refused (nothing was
/// charged; the next confirm is a new attempt) and no answer (Retry sends the same key again). After
/// no answer the attempt survives Back: continuing with the same amount shows "no answer" again, and
/// only a different amount starts a new attempt (K-05).
///
/// Not yet on iOS: keeping the attempt and the receipt when the system ends the app in the background
/// (K-08, N-01; Android keeps them in its SavedStateHandle).
@Observable
final class PayModel {
    enum Step { case amount, confirm }

    struct Receipt {
        let payment: Payment
        let replayed: Bool
    }

    let attempt = Attempt()
    var amount = ""
    private(set) var step = Step.amount
    private(set) var wallet: Wallet?
    private(set) var receipt: Receipt?
    private let api: ApiClient
    private let walletId: String

    init(api: ApiClient, walletId: String) {
        self.api = api
        self.walletId = walletId
    }

    func load() async {
        if case .ok(let w, _) = await api.getWallet(walletId) { wallet = w }
    }

    /// Continue: a different amount from a pending attempt's is a new payment.
    func toConfirm() {
        if let pending = attempt.pendingAmount, !Money.sameAmount(pending, amount) { attempt.reset() }
        step = .confirm
    }

    /// Back, Cancel or Change amount. A pending attempt is kept (K-05); a refusal's message is cleared.
    func changeAmount() {
        if attempt.state != .unknown { attempt.reset() }
        step = .amount
    }

    func confirm() async {
        let result = await attempt.submit(amount) { amount, key in await api.pay(walletId, amount, key: key) }
        if case .ok(let payment, let replayed) = result {
            receipt = Receipt(payment: payment, replayed: replayed)
        }
    }
}

struct PayView: View {
    let onBack: () -> Void
    let onDone: () -> Void
    @State private var model: PayModel

    init(api: ApiClient, walletId: String, onBack: @escaping () -> Void, onDone: @escaping () -> Void) {
        self.onBack = onBack
        self.onDone = onDone
        _model = State(initialValue: PayModel(api: api, walletId: walletId))
    }

    var body: some View {
        Group {
            if let receipt = model.receipt {
                receiptScreen(receipt)
            } else if model.step == .amount {
                amountScreen
            } else {
                confirmScreen
            }
        }
        .task { await model.load() }
    }

    private var amountScreen: some View {
        Screen(title: "Pay", onBack: onBack) {
            WalletButton(text: "Continue", testTag: "submit",
                         enabled: !model.amount.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty) { model.toConfirm() }
        } content: {
            if let wallet = model.wallet { Available(wallet: wallet) }
            AmountField(value: $model.amount)
        }
    }

    /// The amount is shown as the API will read it when it is a plain amount, else as typed (R-04).
    private var confirmScreen: some View {
        let state = model.attempt.state
        let pending = state == .pending
        let normalized = Money.normalize(model.amount)
        let after: Int64? = if let normalized, let wallet = model.wallet,
                               let balance = Money.toCents(wallet.balance), let cents = Money.toCents(normalized) {
            balance - cents
        } else {
            nil
        }
        return Screen(title: "Confirm payment", onBack: { model.changeAmount() }, backEnabled: !pending) {
            switch state {
            case .unknown:
                WalletButton(text: "Retry", testTag: "retry") { Task { await model.confirm() } }
                WalletButton(text: "Back to wallet", testTag: "back-to-wallet", kind: .ghost, action: onDone)
            case .refused:
                WalletButton(text: "Confirm payment", testTag: "confirm-pay") { Task { await model.confirm() } }
                WalletButton(text: "Change amount", testTag: "change-amount", kind: .ghost) { model.changeAmount() }
            default:
                WalletButton(text: "Confirm payment", testTag: "confirm-pay", loading: pending) { Task { await model.confirm() } }
                WalletButton(text: "Cancel", testTag: "cancel", kind: .ghost, enabled: !pending) { model.changeAmount() }
            }
        } content: {
            WalletCard(spacing: WalletSpacing.xs) {
                Text("You pay").walletText(WalletType.label).foregroundStyle(WalletColors.textSecondary)
                HStack(alignment: .firstTextBaseline, spacing: 0) {
                    Text(normalized.map(Money.display) ?? model.amount).accessibilityIdentifier("confirm-amount")
                    Text(" TWD")
                }
                .walletText(WalletType.amountLarge)
                .foregroundStyle(WalletColors.textPrimary)
                // The rows touch, with a hairline between them, and the last one ends the card (SPEC §7.7)
                let showAfter = after.map { $0 >= 0 } ?? false
                VStack(spacing: 0) {
                    if let wallet = model.wallet {
                        ReceiptRow(label: "From", value: "\(wallet.owner) · \(Formats.maskId(wallet.walletId))", last: !showAfter)
                    }
                    if let after, showAfter {
                        RowDivider()
                        ReceiptRow(label: "Balance after", value: Money.display(Money.fromCents(after)),
                                   valueTestTag: "confirm-balance-after", suffix: "TWD", last: true)
                    }
                }
            }
            switch state {
            case .refused(_, let message): Message(kind: .error, text: message, testTag: "error-message")
            case .unknown: Message(kind: .warning, text: Messages.payNoAnswer, testTag: "no-answer")
            default: EmptyView()
            }
        }
    }

    /// The screen after the payment went through (hook "result"). No back button: the money has moved,
    /// and the way on is Done. `replayed`: the API answered Idempotent-Replayed: true (SPEC K-06).
    private func receiptScreen(_ receipt: PayModel.Receipt) -> some View {
        let p = receipt.payment
        return Screen(title: "Payment") {
            WalletButton(text: "Done", testTag: "done", action: onDone)
        } content: {
            VStack(alignment: .leading, spacing: WalletSpacing.lg) {
                HStack(spacing: WalletSpacing.sm) {
                    Image(systemName: "checkmark.circle").foregroundStyle(WalletColors.amountCredit).accessibilityHidden(true)
                    Text("Payment completed").walletText(WalletType.titleLarge).foregroundStyle(WalletColors.textPrimary)
                }
                HStack(alignment: .firstTextBaseline, spacing: WalletSpacing.sm) {
                    Text(Money.display(p.amount)).walletText(WalletType.displayBalance).foregroundStyle(WalletColors.textPrimary)
                        .accessibilityIdentifier("result-amount")
                    Text("TWD").walletText(WalletType.bodyStrong).foregroundStyle(WalletColors.textSecondary)
                }
                if receipt.replayed {
                    Message(kind: .success, text: Messages.replayed, testTag: "replayed")
                }
                WalletCard(spacing: 0, padding: EdgeInsets(top: WalletSpacing.xs, leading: WalletSpacing.xl,
                                                           bottom: WalletSpacing.xs, trailing: WalletSpacing.xl)) {
                    ReceiptRow(label: "Status", value: "Completed")
                    RowDivider()
                    ReceiptRow(label: "Time", value: Formats.dateTime(p.createdAt))
                    RowDivider()
                    ReceiptRow(label: "Payment ID", value: p.paymentId, valueTestTag: "result-payment-id")
                    if let balance = p.balanceAfter {
                        RowDivider()
                        ReceiptRow(label: "Balance after", value: Money.display(balance), valueTestTag: "result-balance", suffix: "TWD")
                    }
                }
            }
            .accessibilityElement(children: .contain)
            .accessibilityIdentifier("result")
        }
    }
}

/// "Available 68.00 TWD"; the hook "balance" holds the number only.
struct Available: View {
    let wallet: Wallet

    var body: some View {
        HStack(spacing: 0) {
            Text("Available ")
            Text(Money.display(wallet.balance)).accessibilityIdentifier("balance")
            Text(" \(wallet.currency)")
        }
        .walletText(WalletType.body)
        .foregroundStyle(WalletColors.textSecondary)
    }
}
