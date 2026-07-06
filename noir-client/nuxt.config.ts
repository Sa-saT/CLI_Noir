// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  // SPA — game state comes from WS/HTTP at runtime (設計指示書 § 2)
  ssr: false,
  css: ['~/assets/css/main.css'],
  app: {
    head: {
      title: 'CLI_Noir',
      htmlAttrs: { lang: 'ja' },
      meta: [{ name: 'viewport', content: 'width=device-width, initial-scale=1' }],
    },
  },
})
