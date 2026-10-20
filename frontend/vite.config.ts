import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Securities lending model takes the fourth port pair (8000-8002 / 5173-5175 belong to the siblings).
const port = Number(process.env.VITE_PORT ?? 5176);
const backendPort = Number(process.env.VITE_BACKEND_PORT ?? 8003);

export default defineConfig({
  plugins: [react()],
  server: {
    port,
    proxy: {
      "/api": { target: `http://localhost:${backendPort}`, changeOrigin: true },
    },
  },
});
