import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Keep browser rehearsals isolated from another developer's backend on :8000.
const backendTarget = process.env.CARTMATE_DEV_API_TARGET || 'http://127.0.0.1:8000'
const websocketTarget = backendTarget.replace(/^http/, 'ws')

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 5280,
    strictPort: true,
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
      },
      '/ws': {
        target: websocketTarget,
        ws: true,
      },
    },
  },
})
