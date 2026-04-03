import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import tailwindcss from "@tailwindcss/vite";
import benchmarkManifest from "./vite-plugin-manifest.js";

export default defineConfig({
  plugins: [tailwindcss(), benchmarkManifest(), svelte()],
  server: { port: 5173, open: true },
});
