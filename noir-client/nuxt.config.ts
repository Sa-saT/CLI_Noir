// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  // SPA — game state comes from WS/HTTP at runtime (設計指示書 § 2)
  ssr: false,
  modules: ['@pinia/nuxt'],
  css: ['~/assets/css/main.css'],
  app: {
    head: {
      title: 'CLI_Noir',
      htmlAttrs: { lang: 'ja' },
      meta: [{ name: 'viewport', content: 'width=device-width, initial-scale=1' }],
    },
  },
  runtimeConfig: {
    public: {
      // noir-api（FastAPI, uvicorn 既定ポート）への接続先。本番は .env で上書き。
      apiBase: 'http://localhost:8000',
      wsBase: 'ws://localhost:8000',
    },
  },
})
