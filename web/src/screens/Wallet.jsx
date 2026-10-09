import { api } from '../api.js';
import { displayAmount } from '../money.js';
import { go } from '../router.js';
import { useLoad } from './useLoad.js';

export default function Wallet({ walletId }) {
  const { data: wallet, error } = useLoad(() => api.getWallet(walletId), [walletId]);

  return (
    <main className="screen">
      <p className="back"><a href="#/" data-testid="switch-wallet">Use another wallet</a></p>
      {error && <p className="message error" data-testid="error-message">{error}</p>}
      {wallet && (
        <>
          <h1 data-testid="owner">{wallet.owner}</h1>
          <p className="note">Wallet ID <code data-testid="wallet-id">{wallet.wallet_id}</code></p>
          <section className="balance-card">
            <p className="label">Balance</p>
            <p className="balance"><span data-testid="balance">{displayAmount(wallet.balance)}</span> {wallet.currency}</p>
          </section>
          <nav className="actions">
            <button type="button" data-testid="go-topup" onClick={() => go(`/w/${walletId}/topup`)}>Top up</button>
            <button type="button" data-testid="go-pay" onClick={() => go(`/w/${walletId}/pay`)}>Pay</button>
            <button type="button" className="secondary" data-testid="go-history" onClick={() => go(`/w/${walletId}/history`)}>History</button>
          </nav>
        </>
      )}
    </main>
  );
}
