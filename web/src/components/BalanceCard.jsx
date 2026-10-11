import { useState } from 'react';
import { maskId } from '../format.js';
import { balanceStyle, displayAmount } from '../money.js';
import Icon from './Icon.jsx';

// Figma: Balance card (Hidden=False | True). The eye button hides the balance, as a banking app
// does in a public place; the wallet ID is shown partly masked.
export default function BalanceCard({ wallet }) {
  const [hidden, setHidden] = useState(false);
  const shown = hidden ? '••••••' : displayAmount(wallet.balance);
  return (
    <section className="card card-tight" aria-label="Balance">
      <div className="balance-head">
        <span className="t-body-strong" data-testid="owner">{wallet.owner}</span>
        <button type="button" className="icon-button" data-testid="balance-toggle"
                aria-label={hidden ? 'Show balance' : 'Hide balance'} aria-pressed={hidden}
                onClick={() => setHidden(!hidden)}>
          <Icon name={hidden ? 'eye-off' : 'eye'} />
        </button>
      </div>
      <p className="balance-row">
        <span className={balanceStyle(shown)} data-testid="balance">{shown}</span>
        <span className="t-body-strong c-secondary">{wallet.currency}</span>
      </p>
      <p className="t-caption c-secondary">
        Available balance · <span data-testid="wallet-id" title={wallet.wallet_id}>{maskId(wallet.wallet_id)}</span>
      </p>
    </section>
  );
}
