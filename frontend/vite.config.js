import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    hmr: {
      port: 5173,
      host: 'localhost'
    },
    proxy: {
      '/auth': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/users': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/files': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/tasks': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/upload': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/start_test': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true
      },
      '/system': {
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