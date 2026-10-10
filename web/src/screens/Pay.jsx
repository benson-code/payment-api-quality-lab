import { useState } from 'react';
import { api } from '../api.js';
import { AmountField } from '../components/Fields.jsx';
import Message from '../components/Message.jsx';
import { ReceiptRow } from '../components/Rows.jsx';
import TopBar from '../components/TopBar.jsx';
import { dateTime, maskId } from '../format.js';
import { displayAmount, fromCents, normalizeAmount, toCents } from '../money.js';
import { go } from '../router.js';
import { useAttempt } from '../useAttempt.js';
import Receipt from './Receipt.jsx';
import { useLoad } from './useLoad.js';

// Pay: enter the amount, review it on Confirm, then the receipt.
//
// The Idempotency-Key is created when Confirm payment is tapped (useAttempt). Confirm shows four
// states: ready, processing (a second tap sends nothing), refused (an error answer: nothing was
// charged, the next confirm is a new attempt) and no answer (Retry sends the same key again).
// The page does not check the amount itself: an amount the API refuses comes back as "refused".
export default function Pay({ walletId }) {
  const { data: wallet } = useLoad(() => api.getWallet(walletId), [walletId]);
  const [amount, setAmount] = useState('');
  const [step, setStep] = useState('amount');
  const [result, setResult] = useState(null);
  const attempt = useAttempt({ idempotent: true, send: (a, key) => api.pay(walletId, a, key), onDone: setResult });
  const { state, pending } = attempt;

  function changeAmount() {
    attempt.reset();
    setStep('amount');
  }

  if (result) {
    const { data, replayed } = result;
    return (
      <Receipt title="Payment" heading="Payment completed" amount={data.amount} replayed={replayed}
               actions={<>
                 <button type="button" className="btn btn-primary" data-testid="done"
                         onClick={() => go(`/w/${walletId}`)}>Done</button>
                 <button type="button" className="btn btn-ghost" data-testid="view-payment"
                         onClick={() => go(`/w/${walletId}/p/${data.payment_id}`)}>View payment</button>
               </>}>
        <ReceiptRow label="Status">Completed</ReceiptRow>
        <ReceiptRow label="Time">{dateTime(data.created_at)}</ReceiptRow>
        <ReceiptRow label="Payment ID" testId="result-payment-id">{data.payment_id}</ReceiptRow>
        {data.balance_after && (
          <ReceiptRow label="Balance after"><span data-testid="result-balance">{displayAmount(data.balance_after)}</span> TWD</ReceiptRow>
        )}
      </Receipt>
    );
  }

  if (step === 'amount') {
    return (
      <div className="screen">
        <TopBar title="Pay" back={`#/w/${walletId}`} />
        <form className="content" onSubmit={(e) => { e.preventDefault(); attempt.reset(); setStep('confirm'); }}>
          {wallet && (
            <p className="t-body c-secondary">
              Available <span data-testid="balance">{displayAmount(wallet.balance)}</span> {wallet.currency}
            </p>
          )}
          <AmountField id="amount" value={amount} onChange={setAmount} />
          <div className="push" />
          <button type="submit" className="btn btn-primary" data-testid="submit" disabled={!amount.trim()}>Continue</button>
        </form>
      </div>
    );
  }

  // Confirm. The amount is shown as the API will read it when it is a plain amount, else as typed.
  const normalized = normalizeAmount(amount);
  const after = normalized && wallet ? toCents(wallet.balance) - toCents(normalized) : null;
  let primary = (
    <button type="button" className="btn btn-primary" data-testid="confirm-pay" disabled={pending}
            onClick={() => attempt.submit(amount)}>
      {pending ? 'Processing…' : 'Confirm payment'}
    </button>
  );
  let secondary = (
    <button type="button" className="btn btn-ghost" data-testid="cancel" disabled={pending} onClick={changeAmount}>
      Cancel
    </button>
  );
  if (state.kind === 'error') {
    secondary = (
      <button type="button" className="btn btn-ghost" data-testid="change-amount" onClick={changeAmount}>Change amount</button>
    );
  }
  if (state.kind === 'unknown') {
    primary = (
      <button type="button" className="btn btn-primary" data-testid="retry" onClick={() => attempt.submit(amount)}>Retry</button>
    );
    secondary = (
      <button type="button" className="btn btn-ghost" data-testid="back-to-wallet" onClick={() => go(`/w/${walletId}`)}>
        Back to wallet
      </button>
    );
  }

  return (
    <div className="screen">
      <TopBar title="Confirm payment" onBack={changeAmount} backDisabled={pending} />
      <main className="content">
        <section className="card card-tight" aria-label="Payment summary">
          <p className="t-label c-secondary">You pay</p>
          <p className="t-amount"><span data-testid="confirm-amount">{normalized ? displayAmount(normalized) : amount}</span> TWD</p>
          <dl className="receipt">
            {wallet && <ReceiptRow label="From">{wallet.owner} · {maskId(wallet.wallet_id)}</ReceiptRow>}
            {after !== null && after >= 0 && (
              <ReceiptRow label="Balance after"><span data-testid="confirm-balance-after">{displayAmount(fromCents(after))}</span> TWD</ReceiptRow>
            )}
          </dl>
        </section>
        <div aria-live="polite">
          {state.kind === 'error' && <Message kind="error" testId="error-message">{state.message}</Message>}
          {state.kind === 'unknown' && (
            <Message kind="warning" testId="no-answer">
              No answer from the server. The payment may or may not have gone through. Retrying is safe: it cannot charge twice.
            </Message>
          )}
        </div>
        <div className="push" />
        <div className="actions">{primary}{secondary}</div>
      </main>
    </div>
  );
}
