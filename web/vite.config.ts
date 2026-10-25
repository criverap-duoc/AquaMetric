import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    // shadcn/ui generates imports as "@/components/...", so the alias must exist in both
    // Vite (resolution) and TypeScript (types).
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    // 5174 keeps AquaMetric next to TerraPlan (5173) and matches the API's CORS allowlist.
    port: 5174,
    strictPort: true,
  },
});
