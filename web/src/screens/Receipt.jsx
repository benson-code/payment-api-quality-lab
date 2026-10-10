import Icon from '../components/Icon.jsx';
import Message from '../components/Message.jsx';
import TopBar from '../components/TopBar.jsx';
import { displayAmount } from '../money.js';

// The screen after a top-up or payment went through. No back button: the money has moved, and the
// way on is Done. `replayed`: the API answered Idempotent-Replayed: true, so this is the original
// result of an earlier request, and nothing was charged again.
export default function Receipt({ title, heading, amount, replayed = false, children, actions }) {
  return (
    <div className="screen">
      <TopBar title={title} />
      <main className="content" data-testid="result" aria-live="polite">
        <p className="status">
          <Icon name="check-circle" />
          <span className="t-title-lg">{heading}</span>
        </p>
        <p className="balance-row">
          <span className="t-display" data-testid="result-amount">{displayAmount(amount)}</span>
          <span className="t-body-strong c-secondary">TWD</span>
        </p>
        {replayed && (
          <Message kind="success" testId="replayed">
            This payment had already gone through. You were not charged again.
          </Message>
        )}
        <dl className="card card-receipt receipt">{children}</dl>
        <div className="push" />
        <div className="actions">{actions}</div>
      </main>
    </div>
  );
}
