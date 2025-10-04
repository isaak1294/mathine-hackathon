export default defineNuxtConfig({
  devtools: { enabled: true },
  //devServer: {
  //  https: {
  //    key: "./key.pem",
  //    cert: "./cert.pem",
  //  },
  //},

  // ----------------------------------------------------------------------------------------------
  //                           (FIX IN PROD, JUST FOR GETTING IT WORKING)
  // ----------------------------------------------------------------------------------------------

  runtimeConfig: {
    backend_url: "http://localhost:3002",
  },

  // CSS - try absolute path instead
  css: ['@/assets/css/main.css'],

  // Modules
  modules: ["@pinia/nuxt", "@nuxtjs/tailwindcss"],

  compatibilityDate: "2025-04-29",
});