// Dates and IDs as the screens show them.
//
// The API returns UTC timestamps (2026-10-10T06:31:12.345+00:00); they are shown in the device's
// time zone, as a phone app does. Tests that check a time pin the browser's time zone.

const TIME = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
const DAY = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' });
const DAY_YEAR = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

const dayKey = (d) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;

// "14:31"
export function timeOf(iso) {
  return TIME.format(new Date(iso));
}

// "10 Oct 2026, 14:31"
export function dateTime(iso) {
  const d = new Date(iso);
  return `${DAY_YEAR.format(d)}, ${TIME.format(d)}`;
}

// The heading a row is grouped under: "Today", "Yesterday", "9 Oct", or "9 Oct 2025" in another year.
export function dayLabel(iso, now = new Date()) {
  const d = new Date(iso);
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (dayKey(d) === dayKey(now)) return 'Today';
  if (dayKey(d) === dayKey(yesterday)) return 'Yesterday';
  return d.getFullYear() === now.getFullYear() ? DAY.format(d) : DAY_YEAR.format(d);
}

// Rows grouped by day, keeping their order: [{ label, items }].
export function groupByDay(items, now = new Date()) {
  const groups = [];
  for (const item of items) {
    const label = dayLabel(item.created_at, now);
    if (groups.length && groups[groups.length - 1].label === label) groups[groups.length - 1].items.push(item);
    else groups.push({ label, items: [item] });
  }
  return groups;
}

// "w_beeb1c2d3e4f4385" -> "w_beeb •••• 4385", as banking apps show account numbers.
export function maskId(id) {
  return id.length > 12 ? `${id.slice(0, 6)} •••• ${id.slice(-4)}` : id;
}

// The ledger's entry types, as the user reads them.
const TYPES = {
  TOPUP: 'Top-up',
  PAYMENT: 'Payment',
  REFUND: 'Refund',
  TRANSFER_IN: 'Transfer in',
  TRANSFER_OUT: 'Transfer out',
};

export function typeLabel(type) {
  return TYPES[type] ?? type;
}
