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
});
