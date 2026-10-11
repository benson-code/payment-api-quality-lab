// Display only. Amounts arrive from the API as strings with two decimals ("12345.60") and are
// formatted as text, never converted to numbers: 12345.60 -> "12,345.60".
export function displayAmount(value) {
  const negative = value.startsWith('-');
  const [whole, cents] = (negative ? value.slice(1) : value).split('.');
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return `${negative ? '-' : ''}${grouped}.${cents}`;
}

// The balance's text style: one step smaller for long amounts, two for the longest, so that the
// largest balance the API allows (999,999,999,999.99) fits a 360 px phone (SPEC L-01). Counted on
// the shown text, the same rule as the app's Money.balanceStyle.
export function balanceStyle(shown) {
  if (shown.length <= 10) return 't-display';     // Display/Balance, up to 999,999.99
  if (shown.length <= 14) return 't-amount';      // Amount/Large, up to 999,999,999.99
  return 't-title-lg';                             // Title/Large
}

// "100.50" -> 10050 and back, for arithmetic on amounts without floating point.
export function toCents(value) {
  const negative = value.startsWith('-');
  const [whole, cents = '00'] = (negative ? value.slice(1) : value).split('.');
  const n = Number(whole) * 100 + Number(cents.padEnd(2, '0'));
  return negative ? -n : n;
}

export function fromCents(n) {
  const sign = n < 0 ? '-' : '';
  const abs = Math.abs(n);
  return `${sign}${Math.floor(abs / 100)}.${String(abs % 100).padStart(2, '0')}`;
}

// Signed, for ledger rows: "+100.00" for money in, "−30.00" for money out. The minus is U+2212, the
// typographic minus sign (as in the design), not the hyphen: screen readers read it as "minus".
export function signedAmount(value) {
  return value.startsWith('-') ? `−${displayAmount(value.slice(1))}` : `+${displayAmount(value)}`;
}

// What the user typed, as a two-decimal amount ("30" -> "30.00"), or null if it is not a plain
// amount. Display only: the page never decides whether an amount is valid, the API does. "Plain" is
// the API's own grammar, so spaces are not trimmed: " 5 " shown as 5.00 on Confirm was then refused.
export function normalizeAmount(typed) {
  return /^[0-9]+(\.[0-9]{1,2})?$/.test(typed) ? fromCents(toCents(typed)) : null;
}
