import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    allowedHosts: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    },
    watch: {
      usePolling: true,
      interval: 1000,  // 增加到 1 秒
      ignored: ['**/node_modules/**', '**/dist/**', '**/.git/**', '**/data/**', '**/logs/**', '**/*.log']
    }
  }
})