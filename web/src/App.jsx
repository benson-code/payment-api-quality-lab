import { useHashPath } from './router.js';
import History from './screens/History.jsx';
import Pay from './screens/Pay.jsx';
import PaymentDetail from './screens/PaymentDetail.jsx';
import Start from './screens/Start.jsx';
import TopUp from './screens/TopUp.jsx';
import Wallet from './screens/Wallet.jsx';

// #/                      start: create or open a wallet
// #/w/<wallet>            Home tab: balance, actions, recent activity
// #/w/<wallet>/topup      top up
// #/w/<wallet>/pay        pay: amount, confirm, receipt
// #/w/<wallet>/history    History tab: ledger, newest first
// #/w/<wallet>/p/<pay>    payment detail and refund
export default function App() {
  const path = useHashPath();
  const m = path.match(/^\/w\/([^/]+)(?:\/(topup|pay|history|p)(?:\/([^/]+))?)?$/);
  if (!m) return <Start />;

  const [, walletId, section, paymentId] = m;
  // A remount per screen (key) resets each screen's state when the path changes.
  if (!section) return <Wallet key={path} walletId={walletId} />;
  if (section === 'topup') return <TopUp key={path} walletId={walletId} />;
  if (section === 'pay') return <Pay key={path} walletId={walletId} />;
  if (section === 'history') return <History key={path} walletId={walletId} />;
  if (section === 'p' && paymentId) return <PaymentDetail key={path} walletId={walletId} paymentId={paymentId} />;
  return <Start />;
}
