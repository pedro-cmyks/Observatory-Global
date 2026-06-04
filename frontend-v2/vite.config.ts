import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    strictPort: true,  // Fail if port 3000 is taken
    proxy: {
      // Local frontend dev runs against the PRODUCTION backend/data so localhost
      // shows the same live signals as production; only the frontend code is
      // local. Set VITE_LOCAL_API=http://localhost:8000 to target a local
      // backend instead.
      '/api': {
        target: process.env.VITE_LOCAL_API || 'https://atlas-api-pedro.fly.dev',
        changeOrigin: true,
      },
      '/health': {
        target: process.env.VITE_LOCAL_API || 'https://atlas-api-pedro.fly.dev',
        changeOrigin: true,
      }
    }
  },
  preview: {
    port: 3000
  }
})
