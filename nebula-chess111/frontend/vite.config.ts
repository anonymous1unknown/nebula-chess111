import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // זה הפתרון המוחלט לגרסאות Vite 5 ומטה - מכבה את בדיקת ה-Host
    hmr: {
      clientPort: 443
    },
    allowedHosts: [
      'eager-dragons-shout.loca.lt',
      '.loca.lt'
    ],
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/ws': { target: 'ws://localhost:8000', ws: true, changeOrigin: true },
    },
  },
  build: { outDir: 'dist', sourcemap: true },
})