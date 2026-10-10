// Figma: Text field (Default | Filled) and Amount field (Empty | Filled | Focus | Error).
// Both always show a visible label; a placeholder alone is not a label.

export function TextField({ id, label, testId, value, onChange, placeholder }) {
  return (
    <div className="field">
      <label className="field-label t-label" htmlFor={id}>{label}</label>
      <div className="field-box">
        <input id={id} data-testid={testId} value={value} placeholder={placeholder} autoComplete="off"
               onChange={(e) => onChange(e.target.value)} />
      </div>
    </div>
  );
}

// Text with inputmode=decimal, never type="number": a number input hands the value over as a
// float. The amount stays the string the user typed, and the API parses it into integer cents.
// `error` is the server's answer, shown under the field (data-testid="error-message").
export function AmountField({ id, label = 'Amount', value, onChange, disabled = false, error = '' }) {
  return (
    <div className={`field${error ? ' field-error' : ''}`}>
      <label className="field-label t-label" htmlFor={id}>{label}</label>
      <div className="field-box amount-box">
        <input id={id} data-testid="amount-input" type="text" inputMode="decimal" autoComplete="off"
               placeholder="0.00" value={value} disabled={disabled}
               aria-invalid={error ? 'true' : undefined} aria-describedby={error ? `${id}-help` : undefined}
               onChange={(e) => onChange(e.target.value)} />
        <span className="t-body-strong c-secondary">TWD</span>
      </div>
      <div aria-live="polite">
        {error && <p id={`${id}-help`} className="field-help t-caption" data-testid="error-message">{error}</p>}
      </div>
    </div>
  );
}
