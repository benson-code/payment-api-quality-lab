import { useState } from 'react';
import { api } from '../api.js';
import { AmountField } from '../components/Fields.jsx';
import Message from '../components/Message.jsx';
import { ReceiptRow, SectionHeader, TransactionRow } from '../components/Rows.jsx';
import TopBar from '../components/TopBar.jsx';
import { dateTime } from '../format.js';
import { displayAmount, fromCents, toCents } from '../money.js';
import { sameAmount, useAttempt } from '../useAttempt.js';
import { useLoad } from './useLoad.js';

// A payment, its refunds, and a refund form. What is left to refund is computed in integer cents.
// Refunds are idempotent: after no answer the button becomes Retry and sends the same key again.
// The pending attempt is kept while the amount is edited; submitting a different amount starts a
// new attempt (useAttempt compares the amounts as money).
export default function PaymentDetail({ walletId, paymentId }) {
  const { data: payment, error, reload } = useLoad(() => api.getPayment(paymentId), [paymentId]);
  const [amount, setAmount] = useState('');
  const [last, setLast] = useState(null);
  const attempt = useAttempt({
    idempotent: true,
    send: (a, key) => api.refund(paymentId, a, key),
    onDone: ({ data }) => {
      setLast(data);
      setAmount('');
      reload();
    },
  });
  const { state, pending } = attempt;
  const retrying = state.kind === 'unknown' && sameAmount(attempt.pendingAmount ?? '', amount);

  return (
    <div className="screen">
      <TopBar title="Payment" back={`#/w/${walletId}/history`} backLabel="Back to history" />
      <main className="content">
        {error && <Message kind="error" testId="error-message">{error}</Message>}
        {payment && (
          <>
            <section className="card card-tight" aria-label="Payment summary">
              <p className="t-caption c-secondary">Paid · {dateTime(payment.created_at)}</p>
              <p className="t-amount"><span data-testid="payment-amount">{displayAmount(payment.amount)}</span> TWD</p>
              <dl className="receipt">
                <ReceiptRow label="Refunded" testId="payment-refunded">{displayAmount(payment.refunded)}</ReceiptRow>
                <ReceiptRow label="Left to refund" testId="payment-refundable">
                  {displayAmount(fromCents(toCents(payment.amount) - toCents(payment.refunded)))}
                </ReceiptRow>
                <ReceiptRow label="Payment ID">{payment.payment_id}</ReceiptRow>
              </dl>
            </section>

            {payment.refunds.length > 0 && (
              <section aria-label="Refunds" className="content-section">
                <SectionHeader>Refunds</SectionHeader>
                <ul className="card card-list">
                  {payment.refunds.map((r) => (
                    <TransactionRow key={r.refund_id} testId="refund-item" title="Refund"
                                    time={dateTime(r.created_at)} amount={r.amount} />
                  ))}
                </ul>
              </section>
            )}

            <form className="content-section" onSubmit={(e) => { e.preventDefault(); attempt.submit(amount); }}>
              <AmountField id="refund-amount" label="Refund amount" value={amount} disabled={pending}
                           error={state.kind === 'error' ? state.message : ''}
                           onChange={(value) => { if (state.kind === 'error') attempt.reset(); setAmount(value); setLast(null); }} />
              <div aria-live="polite">
                {last && (
                  <Message kind="success" testId="refund-done">
                    Refunded {displayAmount(last.amount)} TWD. New balance {displayAmount(last.balance_after)} TWD.
                  </Message>
                )}
                {state.kind === 'unknown' && (
                  <Message kind="warning" testId="no-answer">
                    No answer from the server. The refund may or may not have gone through. Retrying is safe: it cannot refund twice.
                  </Message>
                )}
              </div>
              {retrying ? (
                <button type="submit" className="btn btn-secondary" data-testid="retry">Retry</button>
              ) : (
                <button type="submit" className="btn btn-secondary" data-testid="submit" disabled={pending || !amount.trim()}>
                  {pending ? 'Processing…' : 'Refund'}
                </button>
              )}
            </form>
          </>
        )}
      </main>
    </div>
  );
}
