import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    sourcemap: false,
    chunkSizeWarningLimit: 1000,
    minify: false,
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:9202',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
