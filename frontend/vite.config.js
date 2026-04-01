import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import benchmarkManifest from "./vite-plugin-manifest.js";

export default defineConfig({
  plugins: [benchmarkManifest(), svelte()],
  server: { port: 5173, open: true },
});
