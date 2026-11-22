import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// In development, requests to /api go to the FastAPI server. In production, FastAPI serves frontend/dist itself.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8000" } },
  test: { environment: "node" },
});
