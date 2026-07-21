import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'icon-192.png', 'icon-512.png', 'icon-maskable-512.png'],
      manifest: {
        name: 'Atlas — Narrative Intelligence',
        short_name: 'Atlas',
        description: 'The global narrative weather — what is happening, who is saying what, where it is heading.',
        start_url: '/brief',
        display: 'standalone',
        background_color: '#0b0e13',
        theme_color: '#0b0e13',
        icons: [
          // Resolution-independent constellation mark (same geometry as
          // LoadingMoment.constellationFor). Browsers that support SVG icons
          // render this crisp at any size; the PNGs below remain the fallback.
          { src: 'favicon.svg', sizes: 'any', type: 'image/svg+xml' },
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'icon-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        // SVGs are NOT precached: the bundled flag-icons set (~500 SVGs, several
        // >100KB) would balloon the precache to ~8MB and force every install to
        // download all flags. They (and app icon SVGs) are runtime-cached on
        // demand instead — see the /assets .svg CacheFirst rule below.
        globPatterns: ['**/*.{js,css,html,woff2,png}'],
        navigateFallbackDenylist: [/^\/api\//],
        // The brief/threads read offline (network-first → last good response);
        // theme detail likewise. Never precache the live API.
        runtimeCaching: [
          {
            urlPattern: ({ url }) =>
              url.pathname.startsWith('/api/v2/briefing') || url.pathname.startsWith('/api/v2/threads'),
            handler: 'NetworkFirst',
            options: {
              cacheName: 'atlas-brief',
              networkTimeoutSeconds: 5,
              expiration: { maxEntries: 30, maxAgeSeconds: 60 * 60 * 24 },
            },
          },
          {
            urlPattern: ({ url }) => url.pathname.startsWith('/api/v2/theme/'),
            handler: 'NetworkFirst',
            options: {
              cacheName: 'atlas-theme',
              networkTimeoutSeconds: 5,
              expiration: { maxEntries: 60, maxAgeSeconds: 60 * 60 * 12 },
            },
          },
          {
            // Bundled SVG assets (country flags + app icons): fetched on first
            // render, then served from cache. Keeps them out of the precache.
            urlPattern: ({ url }) => url.pathname.startsWith('/assets/') && url.pathname.endsWith('.svg'),
            handler: 'CacheFirst',
            options: {
              cacheName: 'atlas-svg',
              expiration: { maxEntries: 600, maxAgeSeconds: 60 * 60 * 24 * 30 },
            },
          },
        ],
      },
    }),
  ],
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
