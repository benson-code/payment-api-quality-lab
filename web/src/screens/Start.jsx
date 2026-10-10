import { useState } from 'react';
import { ApiError, api } from '../api.js';
import { TextField } from '../components/Fields.jsx';
import Message from '../components/Message.jsx';
import TopBar from '../components/TopBar.jsx';
import { messageFor } from '../messages.js';
import { go } from '../router.js';

// Create a wallet, or open one by its ID. There is no login: the wallet ID in the URL is the only
// key, as in the API itself (a known limitation of this practice project).
export default function Start() {
  const [owner, setOwner] = useState('');
  const [walletId, setWalletId] = useState('');
  // The message is shown in the form that was submitted, under its button (SPEC L-04)
  const [error, setError] = useState({ form: null, text: '' });
  const [busy, setBusy] = useState(false);

  async function run(form, action) {
    setBusy(true);
    setError({ form: null, text: '' });
    try {
      const { data } = await action();
      go(`/w/${data.wallet_id}`);
    } catch (e) {
      setError({ form, text: e instanceof ApiError ? messageFor(e) : 'No answer from the server. Try again.' });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="screen">
      <TopBar title="Wallet" />
      <main className="content">
        <div>
          <h2 className="t-title-lg">Open your wallet</h2>
          <p className="t-body c-secondary">A practice wallet: no real money, no login.</p>
        </div>

        <form className="card" onSubmit={(e) => { e.preventDefault(); run('new', () => api.createWallet(owner)); }}>
          <h3 className="t-title-md">New wallet</h3>
          <TextField id="owner" label="Your name" testId="owner-input" value={owner} onChange={setOwner}
                     placeholder="e.g. Alex" />
          <button type="submit" className="btn btn-primary" data-testid="create-wallet" disabled={busy}>Create wallet</button>
          <div aria-live="polite">
            {error.form === 'new' && <Message kind="error" testId="error-message">{error.text}</Message>}
          </div>
        </form>

        <p className="t-caption c-secondary center">or</p>

        <form className="card" onSubmit={(e) => { e.preventDefault(); run('existing', () => api.getWallet(walletId.trim())); }}>
          <h3 className="t-title-md">Existing wallet</h3>
          <TextField id="wallet-id" label="Wallet ID" testId="wallet-id-input" value={walletId} onChange={setWalletId}
                     placeholder="w_…" />
          <button type="submit" className="btn btn-secondary" data-testid="open-wallet" disabled={busy}>Open wallet</button>
          <div aria-live="polite">
            {error.form === 'existing' && <Message kind="error" testId="error-message">{error.text}</Message>}
          </div>
        </form>
      </main>
    </div>
  );
}
