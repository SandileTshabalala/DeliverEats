import { defineConfig, loadEnv, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

/**
 * Uploaded photos (menu items, logos, categories) are served by the API. In
 * production that is the same https site, which the Content-Security-Policy in
 * index.html already allows. In development the API is plain
 * http://localhost:8000, which the policy blocks, so every uploaded photo
 * showed as empty. While developing only, allow images from the API's address.
 */
const allowApiImagesInDev = (apiUrl: string): Plugin => ({
  name: 'allow-api-images-in-dev',
  apply: 'serve',
  transformIndexHtml(html) {
    const origin = new URL(apiUrl).origin
    return html.replace("img-src 'self'", `img-src 'self' ${origin}`)
  },
})

export default defineConfig(({ mode }) => {
  const env = { ...loadEnv(mode, process.cwd()), ...process.env }
  return {
    plugins: [
      react(),
      tailwindcss(),
      allowApiImagesInDev(env.VITE_API_URL || 'http://localhost:8000/api/v1'),
    ],
    server: {
      port: 5173,
      strictPort: true,
      // Inside Docker on Windows, file-change events do not cross the mounted
      // folder, so edits would never show up. Polling fixes that; it is only
      // switched on by docker-compose (VITE_USE_POLLING=true).
      watch: process.env.VITE_USE_POLLING ? { usePolling: true, interval: 300 } : undefined,
    },
  }
})
