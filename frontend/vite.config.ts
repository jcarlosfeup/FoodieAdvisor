import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// The dev server proxies API calls to FastAPI, so the browser only talks to one origin.
// In Phase 6 nginx does the same job in the frontend container.
const apiTarget = process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": apiTarget,
      "/health": apiTarget,
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    restoreMocks: true,
    unstubGlobals: true,
  },
});
