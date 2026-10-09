import { useState } from 'react';
import AmountForm from '../AmountForm.jsx';
import { api } from '../api.js';
import { displayAmount, fromCents, toCents } from '../money.js';
import { useLoad } from './useLoad.js';

// A payment, its refunds, and a refund form. What is left to refund is computed in integer cents.
export default function PaymentDetail({ walletId, paymentId }) {
  const { data: payment, error, reload } = useLoad(() => api.getPayment(paymentId), [paymentId]);
  const [last, setLast] = useState(null);

  return (
    <main className="screen">
      <p className="back"><a href={`#/w/${walletId}/history`} data-testid="back">Back to history</a></p>
      <h1>Payment</h1>
      {error && <p className="message error" data-testid="error-message">{error}</p>}
      {payment && (
        <>
          <dl className="details">
            <dt>Amount</dt><dd data-testid="payment-amount">{displayAmount(payment.amount)}</dd>
            <dt>Refunded</dt><dd data-testid="payment-refunded">{displayAmount(payment.refunded)}</dd>
            <dt>Left to refund</dt>
            <dd data-testid="payment-refundable">{displayAmount(fromCents(toCents(payment.amount) - toCents(payment.refunded)))}</dd>
            <dt>Payment ID</dt><dd><code>{payment.payment_id}</code></dd>
          </dl>
          {payment.refunds.length > 0 && (
            <ul className="history">
              {payment.refunds.map((r) => (
                <li key={r.refund_id} data-testid="refund-item">
                  <span className="type">Refund</span>
                  <span className="amount credit">+{displayAmount(r.amount)}</span>
                </li>
              ))}
            </ul>
          )}
          {last && (
            <p className="message info" data-testid="refund-done" aria-live="polite">
              Refunded {displayAmount(last.amount)} TWD. New balance {displayAmount(last.balance_after)} TWD.
            </p>
          )}
          <AmountForm
            inputId="refund-amount"
            label="Refund amount (TWD)"
            submitLabel="Refund"
            idempotent
            send={(amount, key) => api.refund(paymentId, amount, key)}
            onDone={({ data }) => {
              setLast(data);
              reload();
            }}
          />
        </>
      )}
    </main>
  );
}
