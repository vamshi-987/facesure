
// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    mkcert(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'FaceSure',
        short_name: 'FaceSure',
        start_url: '/',
        display: 'standalone',
        background_color: '#111827',
        theme_color: '#6366f1',
        icons: [
          {
            src: '/icon-192x192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: '/icon-512x512.png',
            sizes: '512x512',
            type: 'image/png',
          },
        ],
      },
    })
  ],
});
