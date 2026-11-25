import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// In development, requests to /api go to the FastAPI server. On a volunteer's computer, FastAPI serves frontend/dist
// itself. Mode "hosted" is the public website's copy, which has no StoryBridge server (see src/services/hosted.js).
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  server: { port: 5173, proxy: mode === "hosted" ? {} : { "/api": "http://127.0.0.1:8000" } },
  test: { environment: "node" },
}));
