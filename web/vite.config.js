import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The built files are served by the FastAPI app under /app, on the same origin as the API, so the
// page calls the API with relative URLs and no cross-origin requests are involved.
// `npm run dev` (port 5173) forwards API calls to a locally running API on port 8400.
const API = 'http://127.0.0.1:8400';

export default defineConfig({
  base: '/app/',
  plugins: [react()],
  build: { outDir: 'dist', emptyOutDir: true },
  server: {
    host: '127.0.0.1',
    proxy: Object.fromEntries(['/health', '/wallets', '/payments'].map((p) => [p, API])),
  },
});
