import { useState } from 'react';
import { api } from '../api.js';
import { AmountField } from '../components/Fields.jsx';
import Message from '../components/Message.jsx';
import { ReceiptRow } from '../components/Rows.jsx';
import TopBar from '../components/TopBar.jsx';
import { displayAmount } from '../money.js';
import { go } from '../router.js';
import { useAttempt } from '../useAttempt.js';
import Receipt from './Receipt.jsx';
import { useLoad } from './useLoad.js';

// Top up: one step. Top-ups take no Idempotency-Key in this API, so there is no safe retry: after
// no answer the user is asked to check the balance first.
export default function TopUp({ walletId }) {
  const { data: wallet } = useLoad(() => api.getWallet(walletId), [walletId]);
  const [amount, setAmount] = useState('');
  const [result, setResult] = useState(null);
  const attempt = useAttempt({ idempotent: false, send: (a) => api.topUp(walletId, a), onDone: setResult });
  const { state, pending } = attempt;

  if (result) {
    return (
      <Receipt title="Top up" heading="Top-up completed" amount={result.data.amount}
               actions={<button type="button" className="btn btn-primary" data-testid="done"
                                onClick={() => go(`/w/${walletId}`)}>Done</button>}>
        <ReceiptRow label="Status">Completed</ReceiptRow>
        <ReceiptRow label="Balance after"><span data-testid="result-balance">{displayAmount(result.data.balance)}</span> TWD</ReceiptRow>
      </Receipt>
    );
  }

  return (
    <div className="screen">
      <TopBar title="Top up" back={`#/w/${walletId}`} />
      <form className="content" onSubmit={(e) => { e.preventDefault(); attempt.submit(amount); }}>
        {wallet && (
          <p className="t-body c-secondary">
            Available <span data-testid="balance">{displayAmount(wallet.balance)}</span> {wallet.currency}
          </p>
        )}
        <AmountField id="amount" value={amount} disabled={pending}
                     error={state.kind === 'error' ? state.message : ''}
                     onChange={(value) => { attempt.reset(); setAmount(value); }} />
        {state.kind === 'unknown' && (
          <Message kind="warning" testId="no-answer">
            No answer from the server: the top-up may or may not have gone through. Check the balance before trying again.
          </Message>
        )}
        <div className="push" />
        <button type="submit" className="btn btn-primary" data-testid="submit" disabled={pending || !amount.trim()}>
          {pending ? 'Processing…' : 'Top up'}
        </button>
      </form>
    </div>
  );
}
