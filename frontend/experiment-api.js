import fs from "node:fs";
import path from "node:path";

export function listExperiments(experimentsDir) {
  if (!fs.existsSync(experimentsDir)) {
    return [];
  }

  const indexedExperiments = readJsonIfValid(path.join(experimentsDir, "index.json"));
  if (Array.isArray(indexedExperiments)) {
    return sortExperiments(indexedExperiments);
  }

  const experiments = [];
  for (const entry of fs.readdirSync(experimentsDir)) {
    const experimentDir = path.join(experimentsDir, entry);
    if (!fs.existsSync(experimentDir) || !fs.statSync(experimentDir).isDirectory()) {
      continue;
    }
    const experimentRecord =
      readJsonIfValid(path.join(experimentDir, "experiment.json")) ??
      readJsonIfValid(path.join(experimentDir, "manifest.json"))?.experiment;
    if (experimentRecord?.experiment_id) {
      experiments.push(experimentRecord);
    }
  }
  return sortExperiments(experiments);
}

export function readExperimentManifest(experimentsDir, experimentId) {
  if (!experimentId) {
    return null;
  }
  const manifest = readJsonIfValid(path.join(experimentsDir, experimentId, "manifest.json"));
  if (manifest == null) {
    return null;
  }
  return decorateManifest(manifest);
}

export function readExperimentArtifact(experimentsDir, experimentId, artifactId) {
  const manifest = readJsonIfValid(path.join(experimentsDir, experimentId, "manifest.json"));
  if (manifest == null) {
    return null;
  }
  const artifact = manifest.artifacts?.find(
    (candidate) => candidate.artifact_id === artifactId,
  );
  if (artifact == null) {
    return null;
  }

  const repoRoot = path.resolve(experimentsDir, "..", "..");
  return {
    artifact: {
      ...artifact,
      content_url: artifactContentUrl(experimentId, artifact),
    },
    filePath: path.join(repoRoot, artifact.path),
  };
}

export function artifactContentUrl(experimentId, artifact) {
  const ext = path.extname(artifact.path ?? "");
  return `/api/artifacts/${encodeURIComponent(experimentId)}/${encodeURIComponent(artifact.artifact_id)}/content${ext}`;
}

export function writeExperimentApiFiles({ resultsDir, outDir }) {
  const experimentsDir = path.join(resultsDir, "experiments");
  const apiDir = path.join(outDir, "api");
  const detailDir = path.join(apiDir, "experiments");
  const experiments = listExperiments(experimentsDir);

  fs.mkdirSync(detailDir, { recursive: true });
  fs.writeFileSync(
    path.join(apiDir, "experiments.json"),
    JSON.stringify({ experiments }),
  );

  for (const experiment of experiments) {
    const manifest = readExperimentManifest(experimentsDir, experiment.experiment_id);
    if (manifest == null) {
      continue;
    }
    fs.writeFileSync(
      path.join(detailDir, `${experiment.experiment_id}.json`),
      JSON.stringify(manifest),
    );
    writeArtifactFiles(experimentsDir, outDir, experiment.experiment_id, manifest.artifacts ?? []);
  }
}

function readJsonIfValid(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf-8"));
  } catch {
    return null;
  }
}

function sortExperiments(experiments) {
  return [...experiments].sort((left, right) => {
    const leftTime = Date.parse(left.created_at ?? "");
    const rightTime = Date.parse(right.created_at ?? "");
    const safeLeft = Number.isFinite(leftTime) ? leftTime : 0;
    const safeRight = Number.isFinite(rightTime) ? rightTime : 0;
    if (safeLeft !== safeRight) {
      return safeRight - safeLeft;
    }
    return String(left.experiment_id ?? "").localeCompare(
      String(right.experiment_id ?? ""),
    );
  });
}

function decorateManifest(manifest) {
  return {
    ...manifest,
    artifacts: (manifest.artifacts ?? []).map((artifact) => ({
      ...artifact,
      content_url: artifactContentUrl(manifest.experiment.experiment_id, artifact),
    })),
  };
}

function writeArtifactFiles(experimentsDir, outDir, experimentId, artifacts) {
  for (const artifact of artifacts) {
    const resolved = readExperimentArtifact(experimentsDir, experimentId, artifact.artifact_id);
    if (resolved == null || !fs.existsSync(resolved.filePath)) {
      continue;
    }
    const outputPath = path.join(outDir, resolved.artifact.content_url.replace(/^\//, ""));
    fs.mkdirSync(path.dirname(outputPath), { recursive: true });
    fs.copyFileSync(resolved.filePath, outputPath);
  }
}
