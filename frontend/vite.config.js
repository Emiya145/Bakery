import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Production builds use /static/ so collectstatic + PythonAnywhere /static/ mapping serve assets.
// Dev server keeps base / with proxy to Django API.
export default defineConfig(({ mode }) => ({
  base: mode === 'production' ? '/static/' : '/',
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
}))
