import { signedAmount, displayAmount } from '../money.js';
import Icon from './Icon.jsx';

// Figma: Section header. Groups rows by date ("Today", "9 Oct").
export function SectionHeader({ children }) {
  return <h2 className="section-header t-label">{children}</h2>;
}

// Figma: Receipt row. Label left, value right; used inside <dl className="receipt">.
export function ReceiptRow({ label, testId, children }) {
  return (
    <div className="receipt-row">
      <dt className="t-body">{label}</dt>
      <dd className="t-body-strong" data-testid={testId}>{children}</dd>
    </div>
  );
}

// Figma: Transaction row (Direction=Credit | Debit). Credit amounts in green with "+", debit amounts
// in the text colour with a minus sign (red is kept for errors). With `onOpen` the whole row is one
// button and shows a chevron (payments open their detail).
export function TransactionRow({ title, time, amount, balanceAfter, onOpen, testId, ...attrs }) {
  const credit = !amount.startsWith('-');
  const inner = (
    <>
      <span className="tx-left">
        <span className="t-body-strong">{title}</span>
        <span className="t-caption c-secondary">{time}</span>
      </span>
      <span className="tx-right">
        <span className={`t-body-strong${credit ? ' tx-amount-credit' : ''}`} data-testid="item-amount">
          {signedAmount(amount)}
        </span>
        {balanceAfter && (
          <span className="t-caption c-secondary">
            Balance <span data-testid="item-balance">{displayAmount(balanceAfter)}</span>
          </span>
        )}
      </span>
    </>
  );
  return (
    <li className="tx-row" data-testid={testId} {...attrs}>
      {onOpen ? (
        <button type="button" className="row-button" data-testid="open-payment" onClick={onOpen}>
          {inner}
          <span className="tx-chevron"><Icon name="chevron-right" /></span>
        </button>
      ) : (
        <div className="tx-inner">{inner}</div>
      )}
    </li>
  );
}
