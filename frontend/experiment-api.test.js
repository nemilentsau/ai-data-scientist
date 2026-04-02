import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import {
  artifactContentUrl,
  listExperiments,
  readExperimentArtifact,
  readExperimentManifest,
  writeExperimentApiFiles,
} from "./experiment-api.js";

function makeTempDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "experiment-api-"));
}

function writeJson(filePath, payload) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, JSON.stringify(payload, null, 2));
}

test("listExperiments reads the experiment index when present", () => {
  const root = makeTempDir();
  const experimentsDir = path.join(root, "results", "experiments");
  writeJson(path.join(experimentsDir, "index.json"), [
    {
      experiment_id: "exp_b",
      title: "Experiment B",
      created_at: "2026-04-01T10:00:00Z",
    },
    {
      experiment_id: "exp_a",
      title: "Experiment A",
      created_at: "2026-04-01T08:00:00Z",
    },
  ]);

  const experiments = listExperiments(experimentsDir);

  assert.deepEqual(
    experiments.map((experiment) => experiment.experiment_id),
    ["exp_b", "exp_a"],
  );
});

test("listExperiments falls back to experiment metadata when the index is missing", () => {
  const root = makeTempDir();
  const experimentsDir = path.join(root, "results", "experiments");
  writeJson(path.join(experimentsDir, "exp_alpha", "experiment.json"), {
    experiment_id: "exp_alpha",
    title: "Alpha",
    created_at: "2026-04-01T08:00:00Z",
    summary: { num_cases: 2 },
  });
  writeJson(path.join(experimentsDir, "exp_beta", "manifest.json"), {
    experiment: {
      experiment_id: "exp_beta",
      title: "Beta",
      created_at: "2026-04-01T09:00:00Z",
      summary: { num_cases: 3 },
    },
  });

  const experiments = listExperiments(experimentsDir);

  assert.deepEqual(
    experiments.map((experiment) => experiment.experiment_id),
    ["exp_beta", "exp_alpha"],
  );
  assert.equal(experiments[0].summary.num_cases, 3);
});

test("readExperimentManifest returns the stored manifest and null for missing ids", () => {
  const root = makeTempDir();
  const experimentsDir = path.join(root, "results", "experiments");
  writeJson(path.join(experimentsDir, "exp_one", "manifest.json"), {
    experiment: { experiment_id: "exp_one" },
    cases: [{ case_id: "case_one" }],
    artifacts: [
      {
        artifact_id: "artifact_report",
        path: "results/runs/solo-codex/multimodal/analysis_report.md",
        media_type: "text/markdown",
      },
    ],
  });

  assert.deepEqual(readExperimentManifest(experimentsDir, "exp_one"), {
    experiment: { experiment_id: "exp_one" },
    cases: [{ case_id: "case_one" }],
    artifacts: [
      {
        artifact_id: "artifact_report",
        path: "results/runs/solo-codex/multimodal/analysis_report.md",
        media_type: "text/markdown",
        content_url: "/api/artifacts/exp_one/artifact_report/content.md",
      },
    ],
  });
  assert.equal(readExperimentManifest(experimentsDir, "missing"), null);
});

test("readExperimentArtifact resolves artifact metadata to the original file path", () => {
  const root = makeTempDir();
  const experimentsDir = path.join(root, "results", "experiments");
  const artifactPath = path.join(
    root,
    "results",
    "runs",
    "solo-codex",
    "multimodal",
    "analysis_report.md",
  );
  fs.mkdirSync(path.dirname(artifactPath), { recursive: true });
  fs.writeFileSync(artifactPath, "# Report\n");
  writeJson(path.join(experimentsDir, "exp_one", "manifest.json"), {
    experiment: { experiment_id: "exp_one" },
    artifacts: [
      {
        artifact_id: "artifact_report",
        path: "results/runs/solo-codex/multimodal/analysis_report.md",
        media_type: "text/markdown",
      },
    ],
  });

  const resolved = readExperimentArtifact(experimentsDir, "exp_one", "artifact_report");

  assert.equal(resolved.artifact.artifact_id, "artifact_report");
  assert.equal(resolved.filePath, artifactPath);
});

test("writeExperimentApiFiles emits experiment list and per-experiment manifests", () => {
  const root = makeTempDir();
  const resultsDir = path.join(root, "results");
  const experimentsDir = path.join(resultsDir, "experiments");
  const outDir = path.join(root, "dist");
  const reportPath = path.join(
    resultsDir,
    "runs",
    "solo-codex",
    "multimodal",
    "analysis_report.md",
  );
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, "# Imported report\n");
  writeJson(path.join(experimentsDir, "exp_one", "experiment.json"), {
    experiment_id: "exp_one",
    title: "First",
    created_at: "2026-04-01T08:00:00Z",
  });
  writeJson(path.join(experimentsDir, "exp_one", "manifest.json"), {
    experiment: { experiment_id: "exp_one", title: "First" },
    cases: [{ case_id: "case_one" }],
    artifacts: [
      {
        artifact_id: "artifact_report",
        path: "results/runs/solo-codex/multimodal/analysis_report.md",
        media_type: "text/markdown",
      },
    ],
  });
  writeJson(path.join(experimentsDir, "exp_two", "experiment.json"), {
    experiment_id: "exp_two",
    title: "Second",
    created_at: "2026-04-01T09:00:00Z",
  });
  writeJson(path.join(experimentsDir, "exp_two", "manifest.json"), {
    experiment: { experiment_id: "exp_two", title: "Second" },
    cases: [{ case_id: "case_two" }],
  });

  writeExperimentApiFiles({ resultsDir, outDir });

  const listPayload = JSON.parse(
    fs.readFileSync(path.join(outDir, "api", "experiments.json"), "utf-8"),
  );
  const detailPayload = JSON.parse(
    fs.readFileSync(
      path.join(outDir, "api", "experiments", "exp_two.json"),
      "utf-8",
    ),
  );

  assert.deepEqual(
    listPayload.experiments.map((experiment) => experiment.experiment_id),
    ["exp_two", "exp_one"],
  );
  assert.equal(detailPayload.experiment.experiment_id, "exp_two");
  assert.equal(detailPayload.cases[0].case_id, "case_two");
  assert.equal(
    JSON.parse(
      fs.readFileSync(path.join(outDir, "api", "experiments", "exp_one.json"), "utf-8"),
    ).artifacts[0].content_url,
    artifactContentUrl("exp_one", {
      artifact_id: "artifact_report",
      path: "results/runs/solo-codex/multimodal/analysis_report.md",
    }),
  );
  assert.equal(
    fs.readFileSync(
      path.join(outDir, "api", "artifacts", "exp_one", "artifact_report", "content.md"),
      "utf-8",
    ),
    "# Imported report\n",
  );
});
