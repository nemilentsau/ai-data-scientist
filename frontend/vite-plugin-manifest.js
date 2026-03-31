import fs from "fs";
import path from "path";

/**
 * Vite plugin that scans ../results/ at build time and exposes a virtual module
 * `virtual:manifest` containing all benchmark run data (scores, reports, traces).
 * Plot images are served via middleware in dev and copied at build time.
 */
export default function benchmarkManifest() {
  const resultsDir = path.resolve(import.meta.dirname, "../results");

  function buildManifest() {
    const runs = [];
    let benchmarkReport = "";

    const reportPath = path.join(resultsDir, "benchmark_report.md");
    if (fs.existsSync(reportPath)) {
      benchmarkReport = fs.readFileSync(reportPath, "utf-8");
    }

    if (!fs.existsSync(resultsDir)) return { runs, benchmarkReport };

    for (const agent of fs.readdirSync(resultsDir)) {
      const agentDir = path.join(resultsDir, agent);
      if (!fs.statSync(agentDir).isDirectory()) continue;

      for (const dataset of fs.readdirSync(agentDir)) {
        const runDir = path.join(agentDir, dataset);
        if (!fs.statSync(runDir).isDirectory()) continue;

        const run = { agent, dataset, id: `${agent}/${dataset}` };

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
        const reportMdPath = path.join(runDir, "analysis_report.md");
        if (fs.existsSync(reportMdPath)) {
          run.report = fs.readFileSync(reportMdPath, "utf-8");
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
            .map((f) => `/plots/${agent}/${dataset}/${f}`);
        }

        runs.push(run);
      }
    }

    return { runs, benchmarkReport };
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

    // Serve plot images from results/ in dev mode
    // URL: /plots/{agent}/{dataset}/{file} → results/{agent}/{dataset}/plots/{file}
    configureServer(server) {
      server.middlewares.use("/plots", (req, res, next) => {
        // req.url has /plots prefix stripped, e.g. /claude/simpsons_paradox/01_foo.png
        const parts = req.url.replace(/^\//, "").split("/");
        if (parts.length < 3) return next();
        const [agent, dataset, ...rest] = parts;
        const filePath = path.join(resultsDir, agent, dataset, "plots", ...rest);
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
      if (!fs.existsSync(resultsDir)) return;

      for (const agent of fs.readdirSync(resultsDir)) {
        const agentDir = path.join(resultsDir, agent);
        if (!fs.statSync(agentDir).isDirectory()) continue;

        for (const dataset of fs.readdirSync(agentDir)) {
          const plotsDir = path.join(agentDir, dataset, "plots");
          if (!fs.existsSync(plotsDir)) continue;

          const destDir = path.join(outDir, "plots", agent, dataset);
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
