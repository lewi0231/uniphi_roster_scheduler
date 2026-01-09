// vitest.config.ts
import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: "./vitest.setup.ts",
    pool: "forks",
    globals: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname),
    },
  },
});
