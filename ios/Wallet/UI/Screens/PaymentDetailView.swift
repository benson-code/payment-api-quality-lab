import Observation
import SwiftUI

/// A payment, its refunds and a refund form (SPEC.md §7.6). Same behaviour as
/// web/src/screens/PaymentDetail.jsx and the Android PaymentDetailScreen.kt. What is left to refund is
/// computed in integer cents (R-03).
///
/// Refunds are idempotent: after no answer the button becomes Retry and sends the same key again. The
/// field can be edited without dropping the pending attempt; the button reads Retry only while it holds
/// the pending amount, and submitting a different amount starts a new attempt (K-05).
@Observable
final class PaymentDetailModel {
    let attempt = Attempt(idempotent: true)
    private(set) var payment: Payment?
    private(set) var error: String?
    private(set) var amount = ""
    /// The refund that just went through, for the message under the field.
    private(set) var last: RefundResult?
    private let api: ApiClient
    private let paymentId: String

    init(api: ApiClient, paymentId: String) {
        self.api = api
        self.paymentId = paymentId
    }

    func load() async {
        switch await api.getPayment(paymentId) {
        case .ok(let p, _): payment = p; error = nil
        case .refused(_, let code, _): error = Messages.forCode(code)
        case .noAnswer: error = Messages.noAnswer
        }
    }

    func edit(_ value: String) {
        attempt.clearRefusal()
        amount = value
        last = nil
    }

    func submit() async {
        let r = await attempt.submit(amount) { amount, key in await api.refund(paymentId, amount, key: key!) }
        if case .ok(let refund, _) = r {
            // Reload first, then show the message: the refund list grows above the form, and the form
            // is brought into view once the message is there (SPEC L-04)
            await load()
            amount = ""
            last = refund
        }
    }
}

struct PaymentDetailView: View {
    let onBack: () -> Void
    @State private var model: PaymentDetailModel

    init(api: ApiClient, paymentId: String, onBack: @escaping () -> Void) {
        self.onBack = onBack
        _model = State(initialValue: PaymentDetailModel(api: api, paymentId: paymentId))
    }

    var body: some View {
        Screen(title: "Payment", onBack: onBack) {
            if let error = model.error {
                Message(kind: .error, text: error, testTag: "error-message")
            }
            if let p = model.payment {
                summary(p)
                if !p.refunds.isEmpty {
                    VStack(alignment: .leading, spacing: WalletSpacing.sm) {
                        SectionHeader(text: "Refunds")
                        WalletCard(spacing: 0, padding: EdgeInsets(top: WalletSpacing.xs, leading: WalletSpacing.lg,
                                                                   bottom: WalletSpacing.xs, trailing: WalletSpacing.lg)) {
                            ForEach(Array(p.refunds.enumerated()), id: \.element.refundId) { i, r in
                                if i > 0 { RowDivider() }
                                TransactionRow(title: "Refund", time: Formats.dateTime(r.createdAt), amount: r.amount,
                                               balanceAfter: nil, testTag: "refund-item")
                            }
                        }
                    }
                }
                RefundForm(model: model)
            }
        }
        .task { await model.load() }
    }

    private func summary(_ p: Payment) -> some View {
        let left = Money.fromCents((Money.toCents(p.amount) ?? 0) - (Money.toCents(p.refunded) ?? 0))
        return WalletCard(spacing: WalletSpacing.xs) {
            Text("Paid · \(Formats.dateTime(p.createdAt))").walletText(WalletType.caption).foregroundStyle(WalletColors.textSecondary)
            HStack(alignment: .firstTextBaseline, spacing: 0) {
                Text(Money.display(p.amount)).accessibilityIdentifier("payment-amount")
                Text(" TWD")
            }
            .walletText(WalletType.amountLarge)
            .foregroundStyle(WalletColors.textPrimary)
            // The rows touch, with a hairline between them, and the last one ends the card (SPEC §7.7)
            VStack(spacing: 0) {
                ReceiptRow(label: "Refunded", value: Money.display(p.refunded), valueTestTag: "payment-refunded")
                RowDivider()
                ReceiptRow(label: "Left to refund", value: Money.display(left), valueTestTag: "payment-refundable")
                RowDivider()
                ReceiptRow(label: "Payment ID", value: p.paymentId, last: true)
            }
        }
    }
}

/// The refund field, its messages and its button. The whole form comes into view when its state
/// changes: a message alone is not enough when the action it asks for (Retry) sits below it (L-04).
private struct RefundForm: View {
    let model: PaymentDetailModel
    @Environment(\.scrollProxy) private var scroll

    var body: some View {
        let state = model.attempt.state
        let pending = state == .pending
        let retrying = state == .unknown && Money.sameAmount(model.attempt.pendingAmount ?? "", model.amount)
        let error: String? = if case .refused(_, let message) = state { message } else { nil }
        VStack(alignment: .leading, spacing: WalletSpacing.sm) {
            AmountField(value: Binding(get: { model.amount }, set: { model.edit($0) }), label: "Refund amount",
                        enabled: !pending, error: error)
            if let last = model.last {
                Message(kind: .success,
                        text: "Refunded \(Money.display(last.amount)) TWD. New balance \(Money.display(last.balanceAfter)) TWD.",
                        testTag: "refund-done")
            }
            if state == .unknown {
                Message(kind: .warning, text: Messages.refundNoAnswer, testTag: "no-answer")
            }
            if retrying {
                WalletButton(text: "Retry", testTag: "retry", kind: .secondary) { Task { await model.submit() } }
            } else {
                WalletButton(text: "Refund", testTag: "submit", kind: .secondary,
                             enabled: !model.amount.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
                             loading: pending) { Task { await model.submit() } }
            }
        }
        .id(RefundForm.anchor)
        .onChange(of: state) { reveal() }
        .onChange(of: model.last) { reveal() }
    }

    private static let anchor = "refund-form"

    private func reveal() {
        if model.attempt.state != .idle || model.last != nil {
            withAnimation { scroll?.scrollTo(RefundForm.anchor, anchor: .bottom) }
        }
    }
}
