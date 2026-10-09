// All calls to the payment API. The page is served by the API itself (under /app), so paths are
// relative and there are no cross-origin requests.

export class ApiError extends Error {
  // The server answered with an error: the outcome is known (nothing was charged).
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export class NetworkError extends Error {
  // No answer arrived. The request may or may not have been processed by the server.
  constructor() {
    super('no response from the server');
  }
}

// A new Idempotency-Key, one per payment or refund attempt (UUID v4).
// crypto.randomUUID() exists only on secure origins (HTTPS or localhost); an Android WebView loading
// the page from the host at http://10.0.2.2 is not one, so the UUID is built from getRandomValues().
export function newKey() {
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const hex = [...b].map((x) => x.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

async function request(method, path, { body, key } = {}) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (key) headers['Idempotency-Key'] = key;

  let response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new NetworkError();
  }
  let data = null;
  try {
    data = await response.json();
  } catch {
    // An answer without a JSON body: treat as no usable answer.
    throw new NetworkError();
  }
  if (!response.ok) {
    throw new ApiError(response.status, data?.error_code ?? 'UNKNOWN', data?.message ?? '');
  }
  return { data, replayed: response.headers.get('Idempotent-Replayed') === 'true' };
}

// Amounts are sent as the strings the user typed: the API parses them into integer cents, so no
// floating-point value is ever involved.
export const api = {
  createWallet: (owner) => request('POST', '/wallets', { body: { owner } }),
  getWallet: (walletId) => request('GET', `/wallets/${encodeURIComponent(walletId)}`),
  topUp: (walletId, amount) =>
    request('POST', `/wallets/${encodeURIComponent(walletId)}/topups`, { body: { amount } }),
  transactions: (walletId) => request('GET', `/wallets/${encodeURIComponent(walletId)}/transactions`),
  pay: (walletId, amount, key) =>
    request('POST', '/payments', { body: { wallet_id: walletId, amount }, key }),
  getPayment: (paymentId) => request('GET', `/payments/${encodeURIComponent(paymentId)}`),
  refund: (paymentId, amount, key) =>
    request('POST', `/payments/${encodeURIComponent(paymentId)}/refunds`, { body: { amount }, key }),
};
