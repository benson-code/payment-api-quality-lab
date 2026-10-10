import { useRef, useState } from 'react';
import { ApiError, NetworkError, newKey } from './api.js';
import { messageFor } from './messages.js';
import { normalizeAmount } from './money.js';

// Sending an amount: top-up, payment and refund. state.kind is idle | pending | error | unknown.
//
// One attempt = one amount the user confirmed, with one Idempotency-Key (when the API takes one).
// - While a request is in flight a second submit is ignored. The ref guards the gap before React
//   re-renders the disabled button: two taps in the same instant would otherwise send two requests.
// - No answer (NetworkError): the outcome is unknown. For an idempotent request the attempt and its
//   key are kept, and the next submit sends the same key again: if the first request was
//   processed, the API returns its original result instead of charging twice. (An earlier version
//   created a new key when the user pressed Pay again instead of Retry, which would have charged
//   twice. Found reviewing the "no answer" screen before any test existed.)
// - An error answer (ApiError) is definitive and nothing was charged: the attempt ends, and the
//   next submit is a new attempt with a new key.
// - A different amount is a different attempt, so it gets a new key. Amounts are compared as money
//   ("30" and "30.00" are the same payment), and only the amount ends a pending attempt: going
//   back from Confirm and continuing with the same amount resends the same key. (The first
//   two-step version created a new key there, which would have charged twice when the first
//   request had gone through. Found writing WEB-013.)
// - reset() ends the attempt without sending: the user edited the amount.
// - Top-ups take no Idempotency-Key in this API, so after no answer the screen asks the user to
//   check the balance instead of offering a retry that could add the money twice.
export function useAttempt({ idempotent, send, onDone }) {
  const [state, setState] = useState({ kind: 'idle' });
  const inFlight = useRef(false);
  const attempt = useRef(null);

  async function submit(amount) {
    if (inFlight.current) return;
    inFlight.current = true;
    // A pending attempt survives only an unknown outcome, so reusing it here is exactly
    // "same amount, outcome still unknown".
    if (attempt.current && !sameAmount(attempt.current.amount, amount)) attempt.current = null;
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

  function reset() {
    if (inFlight.current) return;
    attempt.current = null;
    setState({ kind: 'idle' });
  }

  return {
    state,
    submit,
    reset,
    pending: state.kind === 'pending',
    // The amount of the attempt still waiting for an answer, or null.
    pendingAmount: attempt.current ? attempt.current.amount : null,
  };
}

export function sameAmount(a, b) {
  return (normalizeAmount(a) ?? a.trim()) === (normalizeAmount(b) ?? b.trim());
}
