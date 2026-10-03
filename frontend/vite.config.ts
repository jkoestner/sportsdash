/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// During `npm run dev`, Vite serves the React app on :5173 and forwards /api
// calls to the FastAPI backend on :8000, so both feel like one site.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  test: {
    environment: "node",
  },
});
