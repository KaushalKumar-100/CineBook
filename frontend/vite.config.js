import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Keep framework code separate from the icon library so browser caches can
// reuse these chunks when application code changes.
export default defineConfig({
  plugins: [react()],
  build: {
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          "react-vendor": ["react", "react-dom"],
          "icon-vendor": ["lucide-react"],
        },
      },
    },
  },
});
