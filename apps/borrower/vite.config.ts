import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Served by the API under /app/ (backend/app/web.py). `npm run dev` proxies API calls to :8000.
const API = process.env.VITE_DEV_API ?? "http://localhost:8000";
const apiPaths = ["/demo", "/auth", "/consent", "/me", "/apply", "/documents", "/bhorsha", "/explain", "/loans", "/upload", "/health"];

export default defineConfig({
  base: "/app/",
  plugins: [react()],
  server: {
    port: 5174,
    proxy: Object.fromEntries(apiPaths.map((p) => [p, { target: API, changeOrigin: true }])),
  },
});
