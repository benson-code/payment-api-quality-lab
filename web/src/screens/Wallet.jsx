import { api } from '../api.js';
import BalanceCard from '../components/BalanceCard.jsx';
import Icon from '../components/Icon.jsx';
import Message from '../components/Message.jsx';
import { SectionHeader, TransactionRow } from '../components/Rows.jsx';
import TabBar from '../components/TabBar.jsx';
import TopBar from '../components/TopBar.jsx';
import { timeOf, typeLabel } from '../format.js';
import { go } from '../router.js';
import { useLoad } from './useLoad.js';

const RECENT = 3;

// Home tab: balance, the three actions, and the latest ledger entries.
export default function Wallet({ walletId }) {
  const { data: wallet, error } = useLoad(() => api.getWallet(walletId), [walletId]);
  const { data: ledger } = useLoad(() => api.transactions(walletId), [walletId]);
  const recent = ledger ? [...ledger.transactions].reverse().slice(0, RECENT) : [];

  return (
    <div className="screen">
      <TopBar title="Wallet" />
      <main className="content">
        {error && <Message kind="error" testId="error-message">{error}</Message>}
        {wallet && (
          <>
            <BalanceCard wallet={wallet} />

            <nav className="card quick-actions" aria-label="Wallet actions">
              <button type="button" className="quick-action" data-testid="go-topup" onClick={() => go(`/w/${walletId}/topup`)}>
                <Icon name="plus" /><span className="t-label">Top up</span>
              </button>
              <button type="button" className="quick-action" data-testid="go-pay" onClick={() => go(`/w/${walletId}/pay`)}>
                <Icon name="send" /><span className="t-label">Pay</span>
              </button>
              <button type="button" className="quick-action" data-testid="go-history" onClick={() => go(`/w/${walletId}/history`)}>
                <Icon name="history" /><span className="t-label">History</span>
              </button>
            </nav>

            {ledger && (
              <section aria-label="Recent activity" className="content-section">
                <SectionHeader>Recent activity</SectionHeader>
                {recent.length === 0 ? (
                  <p className="card t-body empty" data-testid="recent-empty">No transactions yet.</p>
                ) : (
                  <ul className="card card-list">
                    {recent.map((t) => (
                      <TransactionRow key={t.entry_id} testId="recent-item" data-type={t.type}
                                      title={typeLabel(t.type)} time={timeOf(t.created_at)}
                                      amount={t.amount} balanceAfter={t.balance_after}
                                      onOpen={t.type === 'PAYMENT' ? () => go(`/w/${walletId}/p/${t.ref_id}`) : undefined} />
                    ))}
                  </ul>
                )}
              </section>
            )}

            <div className="push" />
            <a className="btn btn-ghost" href="#/" data-testid="switch-wallet">Use another wallet</a>
          </>
        )}
      </main>
      <TabBar walletId={walletId} active="home" />
    </div>
  );
}
