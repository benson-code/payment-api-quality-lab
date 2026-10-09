import { api } from '../api.js';
import Header from '../Header.jsx';
import Icon from '../Icon.jsx';
import { displayAmount } from '../money.js';
import { go } from '../router.js';
import { useLoad } from './useLoad.js';

export default function Wallet({ walletId }) {
  const { data: wallet, error } = useLoad(() => api.getWallet(walletId), [walletId]);

  return (
    <>
      <Header title="Wallet" back="#/" backTestId="switch-wallet" backLabel="Use another wallet" />
      <main className="screen">
        {error && <p className="message error" data-testid="error-message">{error}</p>}
        {wallet && (
          <>
            <section className="balance-card">
              <p className="owner" data-testid="owner">{wallet.owner}</p>
              <p className="label">Balance</p>
              <p className="balance">
                <span data-testid="balance">{displayAmount(wallet.balance)}</span>
                <span className="currency">{wallet.currency}</span>
              </p>
              <p className="wallet-id">ID <code data-testid="wallet-id">{wallet.wallet_id}</code></p>
            </section>

            <nav className="actions" aria-label="Wallet actions">
              <button type="button" className="tile" data-testid="go-topup" onClick={() => go(`/w/${walletId}/topup`)}>
                <span className="tile-icon credit"><Icon name="plus" /></span>Top up
              </button>
              <button type="button" className="tile" data-testid="go-pay" onClick={() => go(`/w/${walletId}/pay`)}>
                <span className="tile-icon accent"><Icon name="send" /></span>Pay
              </button>
              <button type="button" className="tile" data-testid="go-history" onClick={() => go(`/w/${walletId}/history`)}>
                <span className="tile-icon muted"><Icon name="list" /></span>History
              </button>
            </nav>
          </>
        )}
      </main>
    </>
  );
}
