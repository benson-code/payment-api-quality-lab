// What the user reads for each API error code. The server decides whether an amount is valid;
// the page only explains the decision.
const MESSAGES = {
  INVALID_AMOUNT: 'Enter an amount like 100 or 100.50: more than 0, at most two decimals.',
  INSUFFICIENT_BALANCE: 'Not enough balance for this payment.',
  LIMIT_EXCEEDED: 'This is above the single-payment limit of 50,000.00.',
  REFUND_EXCEEDS_PAYMENT: 'This refund would exceed what is left to refund on this payment.',
  WALLET_NOT_FOUND: 'No wallet with this ID.',
  PAYMENT_NOT_FOUND: 'No payment with this ID.',
  INVALID_OWNER: 'Enter a name of 1 to 50 characters.',
  IDEMPOTENCY_KEY_REUSED: 'This request conflicts with an earlier one. Start again.',
};

export function messageFor(error) {
  return MESSAGES[error.code] ?? `Something went wrong (${error.code}).`;
}
