/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// ローカル開発: /api を FastAPI（uvicorn backend.app.main:app --port 8000）へ中継する。
// SSE（/api/support/stream/*）もこのプロキシ経由で届く。
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
});
