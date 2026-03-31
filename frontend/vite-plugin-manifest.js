import fs from "fs";
import path from "path";
import { parse as parseYaml } from "yaml";

/**
 * Vite plugin that scans ../results/ at build time and exposes a virtual module
 * `virtual:manifest` containing all benchmark configs and run data.
 *
 * Directory structure:
 *   results/configs/{config}.yaml
 *   results/runs/{config}/{dataset}/score.json, trace.jsonl, ...
 */
export default function benchmarkManifest() {
  const resultsDir = path.resolve(import.meta.dirname, "../results");
  const configsDir = path.join(resultsDir, "configs");
  const runsDir = path.join(resultsDir, "runs");

  function buildManifest() {
    const configs = {};
    const runs = [];

    // Load configs
    if (fs.existsSync(configsDir)) {
      for (const file of fs.readdirSync(configsDir)) {
        if (!file.endsWith(".yaml") && !file.endsWith(".yml")) continue;
        const name = file.replace(/\.ya?ml$/, "");
        const content = fs.readFileSync(path.join(configsDir, file), "utf-8");
        configs[name] = parseYaml(content);
      }
    }

    // Load runs
    if (fs.existsSync(runsDir)) {
      for (const configName of fs.readdirSync(runsDir)) {
        const configDir = path.join(runsDir, configName);
        if (!fs.statSync(configDir).isDirectory()) continue;

        for (const dataset of fs.readdirSync(configDir)) {
          const runDir = path.join(configDir, dataset);
          if (!fs.statSync(runDir).isDirectory()) continue;

          const run = { config: configName, dataset, id: `${configName}/${dataset}` };

          // score.json
          const scorePath = path.join(runDir, "score.json");
          if (fs.existsSync(scorePath)) {
            run.score = JSON.parse(fs.readFileSync(scorePath, "utf-8"));
          }

          // session.json
          const sessionPath = path.join(runDir, "session.json");
          if (fs.existsSync(sessionPath)) {
            run.session = JSON.parse(fs.readFileSync(sessionPath, "utf-8"));
          }

          // analysis_report.md
          const reportPath = path.join(runDir, "analysis_report.md");
          if (fs.existsSync(reportPath)) {
            run.report = fs.readFileSync(reportPath, "utf-8");
          }

          // trace.jsonl
          const tracePath = path.join(runDir, "trace.jsonl");
          if (fs.existsSync(tracePath)) {
            run.trace = fs.readFileSync(tracePath, "utf-8");
          }

          // plots
          const plotsDir = path.join(runDir, "plots");
          if (fs.existsSync(plotsDir)) {
            run.plots = fs
              .readdirSync(plotsDir)
              .filter((f) => /\.(png|jpg|jpeg|svg|gif)$/i.test(f))
              .sort()
              .map((f) => `/plots/${configName}/${dataset}/${f}`);
          }

          runs.push(run);
        }
      }
    }

    return { configs, runs };
  }

  return {
    name: "benchmark-manifest",

    resolveId(id) {
      if (id === "virtual:manifest") return "\0virtual:manifest";
    },

    load(id) {
      if (id === "\0virtual:manifest") {
        return `export default ${JSON.stringify(buildManifest())};`;
      }
    },

    // Serve plot images from results/runs/ in dev mode
    // URL: /plots/{config}/{dataset}/{file} → results/runs/{config}/{dataset}/plots/{file}
    configureServer(server) {
      server.middlewares.use("/plots", (req, res, next) => {
        const parts = req.url.replace(/^\//, "").split("/");
        if (parts.length < 3) return next();
        const [configName, dataset, ...rest] = parts;
        const filePath = path.join(runsDir, configName, dataset, "plots", ...rest);
        if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
          const ext = path.extname(filePath).toLowerCase();
          const mimeTypes = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".gif": "image/gif",
          };
          res.setHeader("Content-Type", mimeTypes[ext] || "application/octet-stream");
          fs.createReadStream(filePath).pipe(res);
        } else {
          next();
        }
      });
    },

    // Copy plot images to dist at build time
    writeBundle(options) {
      const outDir = options.dir || path.resolve(import.meta.dirname, "dist");
      if (!fs.existsSync(runsDir)) return;

      for (const configName of fs.readdirSync(runsDir)) {
        const configDir = path.join(runsDir, configName);
        if (!fs.statSync(configDir).isDirectory()) continue;

        for (const dataset of fs.readdirSync(configDir)) {
          const plotsDir = path.join(configDir, dataset, "plots");
          if (!fs.existsSync(plotsDir)) continue;

          const destDir = path.join(outDir, "plots", configName, dataset);
          fs.mkdirSync(destDir, { recursive: true });

          for (const file of fs.readdirSync(plotsDir)) {
            if (/\.(png|jpg|jpeg|svg|gif)$/i.test(file)) {
              fs.copyFileSync(path.join(plotsDir, file), path.join(destDir, file));
            }
          }
        }
      }
    },

    // Hot-reload when results change in dev
    handleHotUpdate({ file, server }) {
      if (file.startsWith(resultsDir)) {
        const mod = server.moduleGraph.getModuleById("\0virtual:manifest");
        if (mod) {
          server.moduleGraph.invalidateModule(mod);
          server.ws.send({ type: "full-reload" });
        }
      }
    },
  };
}
