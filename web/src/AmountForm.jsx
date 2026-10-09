import { useRef, useState } from 'react';
import { ApiError, NetworkError, newKey } from './api.js';
import { messageFor } from './messages.js';

// The amount form shared by top-up, payment and refund.
//
// One attempt = one amount the user confirmed, with one Idempotency-Key (when the API supports one).
// - While a request is in flight the button is disabled and a second submit is ignored. The ref
//   guards the gap before React re-renders the disabled button: two taps in the same instant
//   would otherwise send two requests.
// - No answer (NetworkError): the outcome is unknown. For an idempotent request the attempt and its
//   key are kept, and the next submit, from Retry or from the main button, sends the same key again:
//   if the first request was processed, the API returns its original result instead of charging
//   twice. (The main button first created a new key here: a user pressing Pay again instead of Retry
//   would have been charged twice. Found reviewing the "no answer" screen before any test existed.)
// - An error answer (ApiError) is definitive and nothing was charged: the attempt ends, and the next
//   submit is a new attempt with a new key.
// - Top-ups take no Idempotency-Key in this API, so after no answer the user is asked to check the
//   balance instead of being offered a retry that could add the money twice.
export default function AmountForm({ label, submitLabel, idempotent, send, onDone, inputId }) {
  const [amount, setAmount] = useState('');
  const [state, setState] = useState({ kind: 'idle' });
  const inFlight = useRef(false);
  const attempt = useRef(null);

  async function submit() {
    if (inFlight.current) return;
    inFlight.current = true;
    // A pending attempt survives only an unknown outcome; editing the amount or a definitive answer
    // ends it. So reusing it here is exactly "same amount, outcome still unknown".
    if (!attempt.current) {
      attempt.current = { amount, key: idempotent ? newKey() : null };
    }
    setState({ kind: 'pending' });
    try {
      const result = await send(attempt.current.amount, attempt.current.key);
      attempt.current = null;
      setState({ kind: 'idle' });
      onDone(result);
    } catch (error) {
      if (error instanceof NetworkError) {
        setState({ kind: 'unknown' });
      } else {
        attempt.current = null;
        setState({ kind: 'error', message: error instanceof ApiError ? messageFor(error) : 'Something went wrong.' });
      }
    } finally {
      inFlight.current = false;
    }
  }

  function edit(value) {
    // A different amount is a different attempt: forget the previous key.
    attempt.current = null;
    setAmount(value);
    if (state.kind !== 'pending') setState({ kind: 'idle' });
  }

  const pending = state.kind === 'pending';
  return (
    <form
      className="amount-form"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <label htmlFor={inputId}>{label}</label>
      {/* Text, not type="number": a number input hands the value over as a float. The amount stays
          the string the user typed, and the API parses it into integer cents. */}
      <input
        id={inputId}
        data-testid="amount-input"
        type="text"
        inputMode="decimal"
        autoComplete="off"
        placeholder="0.00"
        value={amount}
        onChange={(e) => edit(e.target.value)}
        disabled={pending}
      />
      <button type="submit" data-testid="submit" disabled={pending}>
        {pending ? 'Processing…' : submitLabel}
      </button>

      <div aria-live="polite">
        {state.kind === 'error' && (
          <p className="message error" data-testid="error-message">{state.message}</p>
        )}
        {state.kind === 'unknown' && idempotent && (
          <div className="message warning" data-testid="no-answer">
            <p>No answer from the server: the request may or may not have gone through. Retrying is safe: it cannot charge twice.</p>
            <button type="button" data-testid="retry" onClick={() => submit()}>Retry</button>
          </div>
        )}
        {state.kind === 'unknown' && !idempotent && (
          <p className="message warning" data-testid="no-answer">
            No answer from the server: the top-up may or may not have gone through. Check the balance before trying again.
          </p>
        )}
      </div>
    </form>
  );
}
