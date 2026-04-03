import fs from "node:fs";
import path from "node:path";
import {
  listExperiments,
  readExperimentArtifact,
  readExperimentManifest,
  writeExperimentApiFiles,
} from "./experiment-api.js";

export default function benchmarkManifest() {
  const resultsDir = path.resolve(import.meta.dirname, "../results");
  const experimentsDir = path.join(resultsDir, "experiments");

  return {
    name: "benchmark-manifest",

    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.url === "/api/experiments.json") {
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify({ experiments: listExperiments(experimentsDir) }));
          return;
        }

        const experimentMatch = req.url?.match(/^\/api\/experiments\/([^/]+)\.json$/);
        if (experimentMatch) {
          const experimentId = decodeURIComponent(experimentMatch[1]);
          const manifest = readExperimentManifest(experimentsDir, experimentId);
          if (manifest == null) {
            respondNotFound(res, "Experiment not found");
            return;
          }
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify(manifest));
          return;
        }

        const artifactMatch = req.url?.match(
          /^\/api\/artifacts\/([^/]+)\/([^/]+)\/content(?:\.[^/]+)?$/,
        );
        if (!artifactMatch) {
          next();
          return;
        }

        const experimentId = decodeURIComponent(artifactMatch[1]);
        const artifactId = decodeURIComponent(artifactMatch[2]);
        const resolved = readExperimentArtifact(experimentsDir, experimentId, artifactId);
        if (resolved == null || !fs.existsSync(resolved.filePath)) {
          respondNotFound(res, "Artifact not found");
          return;
        }

        res.setHeader(
          "Content-Type",
          resolved.artifact.media_type ?? "application/octet-stream",
        );
        fs.createReadStream(resolved.filePath).pipe(res);
      });
    },

    writeBundle(options) {
      const outDir = options.dir || path.resolve(import.meta.dirname, "dist");
      writeExperimentApiFiles({ resultsDir, outDir });
    },
  };
}

function respondNotFound(res, message) {
  res.statusCode = 404;
  res.setHeader("Content-Type", "application/json");
  res.end(JSON.stringify({ error: message }));
}
