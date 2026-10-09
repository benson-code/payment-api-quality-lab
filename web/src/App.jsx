import { useEffect, useState } from 'react';

// Step 1 of the front end: a page served under /app that reaches the API on the same origin.
// The screens (start, wallet, top-up and payment, history, payment detail) come next.
export default function App() {
  const [api, setApi] = useState('checking');

  useEffect(() => {
    fetch('/health')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((body) => setApi(body.status === 'ok' ? 'ok' : 'unexpected response'))
      .catch(() => setApi('unreachable'));
  }, []);

  return (
    <main className="screen">
      <h1>Wallet</h1>
      <p className="note">Practice project: no real money, no login.</p>
      <p data-testid="api-status">API: {api}</p>
    </main>
  );
}
