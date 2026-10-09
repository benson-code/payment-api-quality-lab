import { api } from '../api.js';
import Header from '../Header.jsx';
import Icon from '../Icon.jsx';
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
    <>
      <Header title="History" back={`#/w/${walletId}`} />
      <main className="screen">
        {error && <p className="message error" data-testid="error-message">{error}</p>}
        {data && entries.length === 0 && <p className="card note empty" data-testid="empty">No transactions yet.</p>}
        {entries.length > 0 && (
          <ul className="card list">
            {entries.map((t) => {
              const debit = t.amount.startsWith('-');
              return (
                <li key={t.entry_id} data-testid="history-item" data-entry-id={t.entry_id} data-type={t.type}>
                  <span className={`row-icon ${debit ? 'debit' : 'credit'}`}><Icon name={debit ? 'up' : 'down'} size={20} /></span>
                  <div className="row-main">
                    <span className="type">{LABELS[t.type] ?? t.type}</span>
                    <span className="time">{t.created_at.slice(0, 16).replace('T', ' ')} UTC</span>
                    {t.type === 'PAYMENT' && (
                      <button type="button" className="link" data-testid="open-payment"
                              onClick={() => go(`/w/${walletId}/p/${t.ref_id}`)}>Details and refund</button>
                    )}
                  </div>
                  <div className="row-figures">
                    <span className={`amount ${debit ? 'debit' : 'credit'}`} data-testid="item-amount">
                      {debit ? '' : '+'}{displayAmount(t.amount)}
                    </span>
                    <span className="after">Balance <span data-testid="item-balance">{displayAmount(t.balance_after)}</span></span>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </main>
    </>
  );
}
