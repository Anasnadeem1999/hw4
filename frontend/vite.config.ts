import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The FastAPI backend serves both the catalogue API and the product images.
// Proxying them through the dev server keeps the frontend on same-origin URLs.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/images': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})
