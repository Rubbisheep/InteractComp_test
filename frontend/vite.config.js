import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    hmr: {
      host: '103.234.62.210', 
      port: 5173,
      protocol: 'ws'
    },
    proxy: {
      '/upload': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/test': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/config': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      }
    }
  }
})