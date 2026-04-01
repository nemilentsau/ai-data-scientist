import fs from "fs";
import path from "path";
import { parse as parseYaml } from "yaml";

/**
 * Vite plugin that serves benchmark data as a live API endpoint
 * instead of baking it into the bundle.
 *
 * Dev mode:  GET /api/manifest — live-reads results/ on every request
 * Build:    Generates a static manifest.json in dist/
 *
 * Plot images served at /plots/{config}/{dataset}/{file}
 */
export default function benchmarkManifest() {
  const resultsDir = path.resolve(import.meta.dirname, "../results");
  const configsDir = path.join(resultsDir, "configs");
  const runsDir = path.join(resultsDir, "runs");

  function readJsonIfValid(filePath) {
    try {
      return JSON.parse(fs.readFileSync(filePath, "utf-8"));
    } catch {
      return null;
    }
  }

  function buildManifest() {
    const configs = {};
    const runs = [];

    if (fs.existsSync(configsDir)) {
      for (const file of fs.readdirSync(configsDir)) {
        if (!file.endsWith(".yaml") && !file.endsWith(".yml")) continue;
        const name = file.replace(/\.ya?ml$/, "");
        configs[name] = parseYaml(fs.readFileSync(path.join(configsDir, file), "utf-8"));
      }
    }

    if (fs.existsSync(runsDir)) {
      for (const configName of fs.readdirSync(runsDir)) {
        const configDir = path.join(runsDir, configName);
        if (!fs.statSync(configDir).isDirectory()) continue;

        for (const dataset of fs.readdirSync(configDir)) {
          const runDir = path.join(configDir, dataset);
          if (!fs.statSync(runDir).isDirectory()) continue;

          const run = { config: configName, dataset, id: `${configName}/${dataset}` };

          const scorePath = path.join(runDir, "score.json");
          if (fs.existsSync(scorePath)) run.score = readJsonIfValid(scorePath);

          const sessionPath = path.join(runDir, "session.json");
          if (fs.existsSync(sessionPath)) run.session = readJsonIfValid(sessionPath);

          const reportPath = path.join(runDir, "analysis_report.md");
          if (fs.existsSync(reportPath)) run.report = fs.readFileSync(reportPath, "utf-8");

          const tracePath = path.join(runDir, "trace.jsonl");
          if (fs.existsSync(tracePath)) run.trace = fs.readFileSync(tracePath, "utf-8");

          const plotsDir = path.join(runDir, "plots");
          if (fs.existsSync(plotsDir)) {
            run.plots = fs.readdirSync(plotsDir)
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

    configureServer(server) {
      // Live API — reads from disk on every request
      server.middlewares.use("/api/manifest", (_req, res) => {
        res.setHeader("Content-Type", "application/json");
        res.end(JSON.stringify(buildManifest()));
      });

      // Serve plot images
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

    // At build time, write manifest.json into dist/ so the built app can fetch it
    writeBundle(options) {
      const outDir = options.dir || path.resolve(import.meta.dirname, "dist");
      const apiDir = path.join(outDir, "api");
      fs.mkdirSync(apiDir, { recursive: true });
      fs.writeFileSync(
        path.join(apiDir, "manifest"),
        JSON.stringify(buildManifest()),
      );

      // Copy plot images
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
  };
}
