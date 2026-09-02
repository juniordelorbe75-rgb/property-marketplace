import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/users": "http://127.0.0.1:8000",
      "/auth": {
        target: "http://127.0.0.1:8000",
        bypass(request) {
          if (request.method === "GET" && request.url?.startsWith("/auth/callback") && request.headers.accept?.includes("text/html")) {
            return "/index.html"
          }
          return undefined
        },
      },
      "/properties": {
        target: "http://127.0.0.1:8000",
        bypass(request) {
          const path = request.url?.split("?")[0]
          const acceptsHtml = request.headers.accept?.includes("text/html")
          const isFrontendPropertyPage = /^\/properties\/(new|\d+)$/.test(path)

          if (
            request.method === "GET"
            && acceptsHtml
            && isFrontendPropertyPage
          ) {
            return "/index.html"
          }

          return undefined
        },
      },
      "/favorites": {
        target: "http://127.0.0.1:8000",
        bypass(request) {
          const acceptsHtml = request.headers.accept?.includes("text/html")

          if (
            request.method === "GET"
            && request.url === "/favorites"
            && acceptsHtml
          ) {
            return "/index.html"
          }

          return undefined
        },
      },
      "/inquiries": {
        target: "http://127.0.0.1:8000",
        bypass(request) {
          const acceptsHtml = request.headers.accept?.includes("text/html")

          if (
            request.method === "GET"
            && request.url === "/inquiries"
            && acceptsHtml
          ) {
            return "/index.html"
          }

          return undefined
        },
      },
      "/reports": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
      "/ready": "http://127.0.0.1:8000",
      "/uploads": "http://127.0.0.1:8000",
    },
  },
})
