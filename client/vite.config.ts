import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 5173,
    strictPort: true,
    // Inside Docker on Windows, file-change events do not cross the mounted
    // folder, so edits would never show up. Polling fixes that; it is only
    // switched on by docker-compose (VITE_USE_POLLING=true).
    watch: process.env.VITE_USE_POLLING ? { usePolling: true, interval: 300 } : undefined,
  }
})
