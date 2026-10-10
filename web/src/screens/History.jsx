import { api } from '../api.js';
import Message from '../components/Message.jsx';
import { SectionHeader, TransactionRow } from '../components/Rows.jsx';
import TabBar from '../components/TabBar.jsx';
import TopBar from '../components/TopBar.jsx';
import { groupByDay, timeOf, typeLabel } from '../format.js';
import { go } from '../router.js';
import { useLoad } from './useLoad.js';

// History tab: the wallet's ledger, newest first, grouped by day. Each entry shows the signed
// amount and the balance after it; payments open their detail.
export default function History({ walletId }) {
  const { data, error } = useLoad(() => api.transactions(walletId), [walletId]);
  const entries = data ? [...data.transactions].reverse() : [];

  return (
    <div className="screen">
      <TopBar title="History" />
      <main className="content">
        {error && <Message kind="error" testId="error-message">{error}</Message>}
        {data && entries.length === 0 && <p className="card t-body empty" data-testid="empty">No transactions yet.</p>}
        {groupByDay(entries).map(({ label, items }) => (
          <section key={label} aria-label={label} className="content-section">
            <SectionHeader>{label}</SectionHeader>
            <ul className="card card-list">
              {items.map((t) => (
                <TransactionRow key={t.entry_id} testId="history-item" data-entry-id={t.entry_id} data-type={t.type}
                                title={typeLabel(t.type)} time={timeOf(t.created_at)}
                                amount={t.amount} balanceAfter={t.balance_after}
                                onOpen={t.type === 'PAYMENT' ? () => go(`/w/${walletId}/p/${t.ref_id}`) : undefined} />
              ))}
            </ul>
          </section>
        ))}
      </main>
      <TabBar walletId={walletId} active="history" />
    </div>
  );
}
