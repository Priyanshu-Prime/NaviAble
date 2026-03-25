import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * Vite configuration for the NaviAble web demo.
 *
 * Proxy
 * -----
 * All requests to /api/* and /health are proxied to the FastAPI backend
 * running on http://localhost:8000.  This avoids CORS issues during
 * development and matches the production configuration where the frontend
 * is served from the same origin as the API.
 */
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
