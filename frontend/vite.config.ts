import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/resume': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/screenings': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/screen': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
