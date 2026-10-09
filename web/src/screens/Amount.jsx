import { useState } from 'react';
import AmountForm from '../AmountForm.jsx';
import { api } from '../api.js';
import { displayAmount } from '../money.js';
import { go } from '../router.js';
import { useLoad } from './useLoad.js';

// Top-up and payment: the same screen, two modes.
const MODES = {
  topup: {
    title: 'Top up',
    submitLabel: 'Top up',
    idempotent: false,
    send: (walletId, amount) => api.topUp(walletId, amount),
  },
  pay: {
    title: 'Pay',
    submitLabel: 'Pay',
    idempotent: true,
    send: (walletId, amount, key) => api.pay(walletId, amount, key),
  },
};

export default function Amount({ walletId, mode }) {
  const m = MODES[mode];
  const { data: wallet } = useLoad(() => api.getWallet(walletId), [walletId]);
  const [result, setResult] = useState(null);

  if (result) {
    const { data, replayed } = result;
    return (
      <main className="screen">
        <h1>{mode === 'pay' ? 'Payment done' : 'Top-up done'}</h1>
        <section className="result" data-testid="result" aria-live="polite">
          <p><span data-testid="result-amount">{displayAmount(data.amount)}</span> TWD</p>
          <p>New balance <span data-testid="result-balance">{displayAmount(data.balance_after ?? data.balance)}</span> TWD</p>
          {replayed && (
            <p className="message info" data-testid="replayed">
              This payment had already gone through. You were not charged again.
            </p>
          )}
        </section>
        {mode === 'pay' && (
          <button type="button" className="secondary" data-testid="view-payment"
                  onClick={() => go(`/w/${walletId}/p/${data.payment_id}`)}>View payment</button>
        )}
        <button type="button" data-testid="done" onClick={() => go(`/w/${walletId}`)}>Back to wallet</button>
      </main>
    );
  }

  return (
    <main className="screen">
      <p className="back"><a href={`#/w/${walletId}`} data-testid="back">Back</a></p>
      <h1>{m.title}</h1>
      {wallet && (
        <p className="note">Balance <span data-testid="balance">{displayAmount(wallet.balance)}</span> {wallet.currency}</p>
      )}
      <AmountForm
        inputId="amount"
        label="Amount (TWD)"
        submitLabel={m.submitLabel}
        idempotent={m.idempotent}
        send={(amount, key) => m.send(walletId, amount, key)}
        onDone={setResult}
      />
    </main>
  );
}
