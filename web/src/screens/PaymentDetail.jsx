import { useState } from 'react';
import AmountForm from '../AmountForm.jsx';
import { api } from '../api.js';
import Header from '../Header.jsx';
import Icon from '../Icon.jsx';
import { displayAmount, fromCents, toCents } from '../money.js';
import { useLoad } from './useLoad.js';

// A payment, its refunds, and a refund form. What is left to refund is computed in integer cents.
export default function PaymentDetail({ walletId, paymentId }) {
  const { data: payment, error, reload } = useLoad(() => api.getPayment(paymentId), [paymentId]);
  const [last, setLast] = useState(null);

  return (
    <>
      <Header title="Payment" back={`#/w/${walletId}/history`} backLabel="Back to history" />
      <main className="screen">
        {error && <p className="message error" data-testid="error-message">{error}</p>}
        {payment && (
          <>
            <section className="card">
              <p className="label">Paid</p>
              <p className="big-amount"><span data-testid="payment-amount">{displayAmount(payment.amount)}</span> TWD</p>
              <dl className="details">
                <dt>Refunded</dt><dd data-testid="payment-refunded">{displayAmount(payment.refunded)}</dd>
                <dt>Left to refund</dt>
                <dd data-testid="payment-refundable">{displayAmount(fromCents(toCents(payment.amount) - toCents(payment.refunded)))}</dd>
                <dt>Payment ID</dt><dd><code>{payment.payment_id}</code></dd>
              </dl>
            </section>

            {payment.refunds.length > 0 && (
              <ul className="card list">
                {payment.refunds.map((r) => (
                  <li key={r.refund_id} data-testid="refund-item">
                    <span className="row-icon credit"><Icon name="down" size={20} /></span>
                    <div className="row-main"><span className="type">Refund</span>
                      <span className="time">{r.created_at.slice(0, 16).replace('T', ' ')} UTC</span></div>
                    <div className="row-figures"><span className="amount credit">+{displayAmount(r.amount)}</span></div>
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
              label="Refund amount"
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
    </>
  );
}
