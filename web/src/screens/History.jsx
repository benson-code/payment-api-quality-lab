import { api } from '../api.js';
import { displayAmount } from '../money.js';
import { go } from '../router.js';
import { useLoad } from './useLoad.js';

const LABELS = {
  TOPUP: 'Top-up',
  PAYMENT: 'Payment',
  REFUND: 'Refund',
  TRANSFER_IN: 'Transfer in',
  TRANSFER_OUT: 'Transfer out',
};

// The wallet's ledger, newest first. Each entry shows the signed amount and the balance after it.
export default function History({ walletId }) {
  const { data, error } = useLoad(() => api.transactions(walletId), [walletId]);
  const entries = data ? [...data.transactions].reverse() : [];

  return (
    <main className="screen">
      <p className="back"><a href={`#/w/${walletId}`} data-testid="back">Back</a></p>
      <h1>History</h1>
      {error && <p className="message error" data-testid="error-message">{error}</p>}
      {data && entries.length === 0 && <p className="note" data-testid="empty">No transactions yet.</p>}
      <ul className="history">
        {entries.map((t) => (
          <li key={t.entry_id} data-testid="history-item" data-entry-id={t.entry_id} data-type={t.type}>
            <div>
              <span className="type">{LABELS[t.type] ?? t.type}</span>
              <span className="time">{t.created_at.slice(0, 16).replace('T', ' ')} UTC</span>
            </div>
            <div className="figures">
              <span className={t.amount.startsWith('-') ? 'amount debit' : 'amount credit'} data-testid="item-amount">
                {t.amount.startsWith('-') ? '' : '+'}{displayAmount(t.amount)}
              </span>
              <span className="after">Balance <span data-testid="item-balance">{displayAmount(t.balance_after)}</span></span>
            </div>
            {t.type === 'PAYMENT' && (
              <button type="button" className="link" data-testid="open-payment"
                      onClick={() => go(`/w/${walletId}/p/${t.ref_id}`)}>Details and refund</button>
            )}
          </li>
        ))}
      </ul>
    </main>
  );
}
