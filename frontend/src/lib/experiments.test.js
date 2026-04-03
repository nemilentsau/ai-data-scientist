import assert from "node:assert/strict";
import test from "node:test";

import {
  buildExperimentView,
  filterArtifacts,
  hydrateArtifactDetail,
  hydrateCaseDetail,
} from "./experiments.js";

test("buildExperimentView indexes configs, datasets, and case summaries", () => {
  const manifest = {
    experiment: { experiment_id: "exp_one", title: "Imported" },
    config_snapshots: [
      { config_name: "solo-codex", config: { description: "Codex config" } },
      { config_name: "solo-baseline", config: { description: "Claude config" } },
    ],
    cases: [
      {
        case_id: "case_two",
        dataset: "mnar",
        config_name: "solo-baseline",
        evaluation_id: "eval_two",
        workflow_run_id: "workflow_case_two_01",
      },
      {
        case_id: "case_one",
        dataset: "multimodal",
        config_name: "solo-codex",
        evaluation_id: "eval_one",
        workflow_run_id: "workflow_case_one_01",
      },
    ],
    evaluations: [
      { evaluation_id: "eval_one", verdict: "partial", summary: "Missed multimodality" },
      { evaluation_id: "eval_two", verdict: "solved", summary: "Correctly identified MNAR" },
    ],
    artifacts: [
      { artifact_id: "artifact_one", case_id: "case_one", type: "analysis_report" },
      { artifact_id: "artifact_two", case_id: "case_two", type: "analysis_report" },
      {
        artifact_id: "artifact_note",
        type: "synthesis_note",
        role: "synthesis_output",
        scope: "experiment",
        media_type: "text/markdown",
        title: "General Overview",
        summary: "Cross-case review",
      },
      {
        artifact_id: "artifact_scoped_note",
        type: "dataset_note",
        role: "synthesis_output",
        scope: "dataset",
        title: "Multimodal note",
        related_case_ids: ["case_one"],
      },
    ],
  };

  const view = buildExperimentView(manifest);

  assert.deepEqual(view.configNames, ["solo-baseline", "solo-codex"]);
  assert.deepEqual(view.datasets, ["mnar", "multimodal"]);
  assert.equal(view.runMap["solo-codex/multimodal"].score.verdict, "partial");
  assert.equal(view.runMap["solo-baseline/mnar"].artifactCount, 1);
  assert.equal(view.runs[0].caseId, "case_two");
  assert.equal(view.experimentArtifacts.length, 1);
  assert.equal(view.experimentArtifacts[0].title, "General Overview");
  assert.equal(view.artifactCatalog.length, 4);
  assert.deepEqual(view.artifactCategories.slice(0, 4), ["all", "analysis", "notes", "reports"]);
  assert.equal(view.artifactCatalog[0].title, "General Overview");
  assert.equal(view.artifactCatalog[0].category, "notes");
  assert.equal(view.artifactCatalog[1].datasetLabels.includes("multimodal"), true);
  assert.equal(view.artifactCatalog[0].previewText, "Cross-case review");
});

test("filterArtifacts supports analysis-first filtering and raw artifact drill-down", () => {
  const artifacts = [
    {
      artifact_id: "artifact_note",
      title: "General Overview",
      summary: "Cross-case note",
      path: "docs/artifacts/general.md",
      category: "notes",
      scope: "experiment",
      datasetLabels: [],
      configLabels: [],
      type: "synthesis_note",
    },
    {
      artifact_id: "artifact_plot",
      title: "distribution.png",
      summary: null,
      path: "results/runs/solo-codex/multimodal/plots/distribution.png",
      category: "plots",
      scope: "case",
      datasetLabels: ["multimodal"],
      configLabels: ["solo-codex"],
      type: "plot",
    },
    {
      artifact_id: "artifact_code",
      title: "analyze_dataset.py",
      summary: null,
      path: "results/runs/solo-baseline/mnar/analyze_dataset.py",
      category: "generated_code",
      scope: "case",
      datasetLabels: ["mnar"],
      configLabels: ["solo-baseline"],
      type: "generated_code",
    },
  ];

  assert.equal(filterArtifacts(artifacts, {}).length, 3);
  assert.deepEqual(
    filterArtifacts(artifacts, { category: "analysis" }).map((artifact) => artifact.artifact_id),
    ["artifact_note"],
  );
  assert.deepEqual(
    filterArtifacts(artifacts, { category: "plots" }).map((artifact) => artifact.artifact_id),
    ["artifact_plot"],
  );
  assert.deepEqual(
    filterArtifacts(artifacts, {
      dataset: "multimodal",
      config: "solo-codex",
    }).map((artifact) => artifact.artifact_id),
    ["artifact_plot"],
  );
  assert.deepEqual(
    filterArtifacts(artifacts, { query: "general", category: "notes" }).map(
      (artifact) => artifact.artifact_id,
    ),
    ["artifact_note"],
  );
});

test("hydrateCaseDetail loads score, trace, report, and plots for a selected case", async () => {
  const manifest = {
    experiment: { experiment_id: "exp_one" },
    artifacts: [
      {
        artifact_id: "artifact_score",
        case_id: "case_one",
        type: "score",
        content_url: "/api/artifacts/exp_one/artifact_score/content.json",
      },
      {
        artifact_id: "artifact_report",
        case_id: "case_one",
        type: "analysis_report",
        content_url: "/api/artifacts/exp_one/artifact_report/content.md",
      },
      {
        artifact_id: "artifact_trace",
        case_id: "case_one",
        type: "trace",
        content_url: "/api/artifacts/exp_one/artifact_trace/content.jsonl",
      },
      {
        artifact_id: "artifact_session",
        case_id: "case_one",
        type: "session",
        media_type: "application/json",
        content_url: "/api/artifacts/exp_one/artifact_session/content.json",
      },
      {
        artifact_id: "artifact_plot",
        case_id: "case_one",
        type: "plot",
        content_url: "/api/artifacts/exp_one/artifact_plot/content.png",
      },
      {
        artifact_id: "artifact_related_note",
        type: "dataset_note",
        role: "synthesis_output",
        title: "Multimodal note",
        summary: "Only for this case",
        related_case_ids: ["case_one"],
        content_url: "/api/artifacts/exp_one/artifact_related_note/content.md",
      },
      {
        artifact_id: "artifact_other_note",
        type: "dataset_note",
        role: "synthesis_output",
        title: "Other note",
        related_case_ids: ["case_other"],
        content_url: "/api/artifacts/exp_one/artifact_other_note/content.md",
      },
    ],
  };
  const run = {
    id: "case_one",
    caseId: "case_one",
    config: "solo-codex",
    dataset: "multimodal",
    score: { verdict: "partial" },
  };
  const fetcher = async (url) => ({
    async json() {
      if (url.endsWith("artifact_score/content.json")) {
        return {
          verdict: "partial",
          summary: "Missed multimodality",
          required_coverage: 0.5,
        };
      }
      if (url.endsWith("artifact_session/content.json")) {
        return { total_cost_usd: 1.25 };
      }
      throw new Error(`unexpected json fetch ${url}`);
    },
    async text() {
      if (url.endsWith("artifact_report/content.md")) {
        return "# Report\n";
      }
      if (url.endsWith("artifact_trace/content.jsonl")) {
        return '{"tool":"Bash","timestamp":"2026-04-01T08:00:00Z","tool_input":{"command":"echo hi"}}\n';
      }
      throw new Error(`unexpected text fetch ${url}`);
    },
  });

  const detail = await hydrateCaseDetail(manifest, run, fetcher);

  assert.equal(detail.report, "# Report\n");
  assert.equal(detail.trace.includes('"tool":"Bash"'), true);
  assert.equal(detail.score.summary, "Missed multimodality");
  assert.equal(detail.plots[0], "/api/artifacts/exp_one/artifact_plot/content.png");
  assert.equal(detail.stats.costUsd, 1.25);
  assert.equal(detail.parsedTrace.events.length, 1);
  assert.equal(detail.relatedArtifacts.length, 1);
  assert.equal(detail.relatedArtifacts[0].title, "Multimodal note");
});

test("hydrateArtifactDetail loads markdown content for experiment-scoped notes", async () => {
  const manifest = {
    experiment: { experiment_id: "exp_one" },
    artifacts: [
      {
        artifact_id: "artifact_note",
        type: "synthesis_note",
        role: "synthesis_output",
        media_type: "text/markdown",
        title: "General Overview",
        summary: "Cross-case review",
        content_url: "/api/artifacts/exp_one/artifact_note/content.md",
      },
    ],
  };
  const fetcher = async (url) => ({
    async text() {
      if (url.endsWith("artifact_note/content.md")) {
        return "# Overview\n";
      }
      throw new Error(`unexpected text fetch ${url}`);
    },
  });

  const detail = await hydrateArtifactDetail(
    manifest,
    manifest.artifacts[0],
    fetcher,
  );

  assert.equal(detail.title, "General Overview");
  assert.equal(detail.content, "# Overview\n");
});

test("hydrateArtifactDetail formats json artifacts for the detail view", async () => {
  const manifest = {
    experiment: { experiment_id: "exp_one" },
  };
  const artifact = {
    artifact_id: "artifact_score",
    type: "score",
    media_type: "application/json",
    title: "Score",
    content_url: "/api/artifacts/exp_one/artifact_score/content.json",
  };
  const fetcher = async () => ({
    async json() {
      return { verdict: "partial", required_coverage: 0.5 };
    },
  });

  const detail = await hydrateArtifactDetail(manifest, artifact, fetcher);

  assert.equal(detail.detailKind, "json");
  assert.equal(detail.content.includes('"verdict": "partial"'), true);
});
