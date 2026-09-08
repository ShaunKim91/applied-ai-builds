import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Local `npm run dev` proxies API calls to a backend running on 8000,
    // so the frontend can be iterated on without a full Docker rebuild.
    // In production, FastAPI serves this app's build output directly from
    // the same origin (see backend/app/main.py), so no proxy is needed there.
    proxy: {
      "/api": "http://localhost:8000",
      "/media": "http://localhost:8000",
    },
  },
  build: {
    outDir: "dist",
  },
});
