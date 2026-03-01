import { defineConfig } from "vite";

export default defineConfig({
  root: ".",
  publicDir: "public",
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/agent": {
        target: "http://127.0.0.1:5051",
        changeOrigin: true,
      },
    },
  },
});
