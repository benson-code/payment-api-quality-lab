// Display only. Amounts arrive from the API as strings with two decimals ("12345.60") and are
// formatted as text, never converted to numbers: 12345.60 -> "12,345.60".
export function displayAmount(value) {
  const negative = value.startsWith('-');
  const [whole, cents] = (negative ? value.slice(1) : value).split('.');
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return `${negative ? '-' : ''}${grouped}.${cents}`;
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
