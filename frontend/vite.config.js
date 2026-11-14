import { defineConfig } from 'vite';

export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/app/' : '/',
  server: {
    proxy: { '/api': 'http://127.0.0.1:5000' },
  },
  esbuild: { jsx: 'automatic' },
}));
