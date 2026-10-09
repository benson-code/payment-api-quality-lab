import { useState } from 'react';
import AmountForm from '../AmountForm.jsx';
import { api } from '../api.js';
import Header from '../Header.jsx';
import Icon from '../Icon.jsx';
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
      <>
        <Header title={m.title} />
        <main className="screen">
          <section className="result" data-testid="result" aria-live="polite">
            <span className="result-icon"><Icon name="check" size={36} /></span>
            <h1>{mode === 'pay' ? 'Payment done' : 'Top-up done'}</h1>
            <p className="result-amount"><span data-testid="result-amount">{displayAmount(data.amount)}</span> TWD</p>
            <p className="note">New balance <span data-testid="result-balance">{displayAmount(data.balance_after ?? data.balance)}</span> TWD</p>
            {replayed && (
              <p className="message info" data-testid="replayed">
                This payment had already gone through. You were not charged again.
              </p>
            )}
          </section>
          <button type="button" data-testid="done" onClick={() => go(`/w/${walletId}`)}>Back to wallet</button>
          {mode === 'pay' && (
            <button type="button" className="secondary" data-testid="view-payment"
                    onClick={() => go(`/w/${walletId}/p/${data.payment_id}`)}>View payment</button>
          )}
        </main>
      </>
    );
  }

  return (
    <>
      <Header title={m.title} back={`#/w/${walletId}`} />
      <main className="screen">
        {wallet && (
          <p className="available">
            Available <span data-testid="balance">{displayAmount(wallet.balance)}</span> {wallet.currency}
          </p>
        )}
        <AmountForm
          inputId="amount"
          label="Amount"
          submitLabel={m.submitLabel}
          idempotent={m.idempotent}
          send={(amount, key) => m.send(walletId, amount, key)}
          onDone={setResult}
        />
      </main>
    </>
  );
}
