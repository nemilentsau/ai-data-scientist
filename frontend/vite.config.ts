import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

import { runApiPlugin } from "./vite/runApiPlugin";

const repoRoot = resolve(fileURLToPath(new URL(".", import.meta.url)), "..");

export default defineConfig({
  plugins: [react(), tailwindcss(), runApiPlugin(repoRoot)],
  server: {
    host: "localhost",
    port: 5180,
    strictPort: true,
  },
  preview: {
    host: "localhost",
    port: 5180,
    strictPort: true,
  },
});
