import Icon from './Icon.jsx';

const ICON = { error: 'alert-circle', warning: 'alert-circle', success: 'check-circle' };

// Figma: Message (Kind=Error | Warning | Success).
// Error: the request was refused, nothing was charged. Warning: no answer, the outcome is unknown.
// Success: a confirmation, such as a payment that had already gone through.
export default function Message({ kind, testId, children }) {
  return (
    <div className={`message message-${kind}`} data-testid={testId} role={kind === 'error' ? 'alert' : 'status'}>
      <Icon name={ICON[kind]} />
      <p className="t-body">{children}</p>
    </div>
  );
}
