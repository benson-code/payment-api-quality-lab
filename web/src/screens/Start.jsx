import { useState } from 'react';
import { ApiError, api } from '../api.js';
import { messageFor } from '../messages.js';
import { go } from '../router.js';

// Create a wallet, or open one by its ID. There is no login: the wallet ID in the URL is the only
// key, as in the API itself (a known limitation of this practice project).
export default function Start() {
  const [owner, setOwner] = useState('');
  const [walletId, setWalletId] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function run(action) {
    setBusy(true);
    setError('');
    try {
      const { data } = await action();
      go(`/w/${data.wallet_id}`);
    } catch (e) {
      setError(e instanceof ApiError ? messageFor(e) : 'No answer from the server. Try again.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="screen">
      <h1>Wallet</h1>
      <p className="note">Practice project: no real money, no login.</p>

      <form onSubmit={(e) => { e.preventDefault(); run(() => api.createWallet(owner)); }}>
        <h2>New wallet</h2>
        <label htmlFor="owner">Your name</label>
        <input id="owner" data-testid="owner-input" value={owner} autoComplete="off"
               onChange={(e) => setOwner(e.target.value)} />
        <button type="submit" data-testid="create-wallet" disabled={busy}>Create wallet</button>
      </form>

      <form onSubmit={(e) => { e.preventDefault(); run(() => api.getWallet(walletId.trim())); }}>
        <h2>Existing wallet</h2>
        <label htmlFor="wallet-id">Wallet ID</label>
        <input id="wallet-id" data-testid="wallet-id-input" value={walletId} autoComplete="off"
               onChange={(e) => setWalletId(e.target.value)} />
        <button type="submit" className="secondary" data-testid="open-wallet" disabled={busy}>Open wallet</button>
      </form>

      <div aria-live="polite">
        {error && <p className="message error" data-testid="error-message">{error}</p>}
      </div>
    </main>
  );
}
