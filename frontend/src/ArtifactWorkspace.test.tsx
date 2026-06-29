import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { deriveArtifactSummaries } from "./artifactLoop";
import { ArtifactWorkspace } from "./App";
import { resolveSelectedView } from "./selectedView";
import type { LoadedRun, RunArtifact, RunLineage } from "./types";

describe("ArtifactWorkspace", () => {
  it("renders a selected artifact file before the artifact dossier", () => {
    const run = renderableRun();
    const path = "02-artifact-builder/distribution_histogram/attempt-1/output.json";
    const artifactSummaries = deriveArtifactSummaries(run);
    const selectedView = resolveSelectedView(run, path);
    const html = renderToStaticMarkup(
      <ArtifactWorkspace
        run={run}
        artifact={run.files.get(path)}
        activeArtifact={artifactSummaries[0]}
        artifactSummaries={artifactSummaries}
        path={path}
        schemaError=""
        selectedView={selectedView}
        onSelect={() => undefined}
      />,
    );

    const selectedIndex = html.indexOf("Selected artifact file");
    const dossierIndex = html.indexOf("Artifact dossier");

    expect(selectedIndex).toBeGreaterThanOrEqual(0);
    expect(dossierIndex).toBeGreaterThanOrEqual(0);
    expect(selectedIndex).toBeLessThan(dossierIndex);
    expect(html).toContain("02-artifact-builder/distribution_histogram/attempt-1/output.json");
    expect(html).toContain("chart_spec");
  });
});

function renderableRun(): LoadedRun {
  const lineage: RunLineage = {
    status: "passed_visual_gate",
    artifact_statuses: {
      distribution_histogram: "passed",
    },
    dependencies: {},
  };
  const files: RunArtifact[] = [
    textArtifact("lineage.json", JSON.stringify(lineage)),
    textArtifact(
      "01-eda-framer/output.json",
      JSON.stringify({
        user_question: "Assess distribution.",
        analysis_goal: "Inspect the target distribution.",
        artifact_plan: [
          {
            id: "distribution_histogram",
            purpose: "Inspect shape.",
            statistical_check: "Check skew and modality.",
            artifact_type: "chart",
            expected_chart_family: "histogram",
            required_fields: ["monthly_rent_usd"],
            interpretation_limits: ["Binning can change modality."],
          },
        ],
        stop_conditions: ["No modeling claims."],
      }),
    ),
    textArtifact("02-artifact-builder/distribution_histogram/attempt-1/build-context.json", "{}"),
    textArtifact("02-artifact-builder/distribution_histogram/attempt-1/prompt.md", "# prompt"),
    textArtifact("02-artifact-builder/distribution_histogram/attempt-1/output.schema.json", "{}"),
    textArtifact(
      "02-artifact-builder/distribution_histogram/attempt-1/output.json",
      JSON.stringify({
        artifact_id: "distribution_histogram",
        sql: "select 1",
        chart_spec: "{}",
      }),
    ),
    textArtifact("02-artifact-builder/distribution_histogram/attempt-1/query.sql", "select 1"),
    textArtifact("02-artifact-builder/distribution_histogram/attempt-1/chart.vegalite.json", "{}"),
    binaryArtifact("03-execution/distribution_histogram/attempt-1/result.parquet"),
    textArtifact("03-execution/distribution_histogram/attempt-1/result.summary.json", "{}"),
    imageArtifact("04-render/distribution_histogram/attempt-1/chart.png"),
    textArtifact("05-visual-reviewer/distribution_histogram/attempt-1/review-context.json", "{}"),
    textArtifact("05-visual-reviewer/distribution_histogram/attempt-1/prompt.md", "# prompt"),
    textArtifact("05-visual-reviewer/distribution_histogram/attempt-1/image-inputs.json", "{}"),
    textArtifact("05-visual-reviewer/distribution_histogram/attempt-1/output.schema.json", "{}"),
    textArtifact(
      "05-visual-reviewer/distribution_histogram/attempt-1/output.json",
      JSON.stringify({
        artifact_id: "distribution_histogram",
        verdict: "pass",
        visual_adequacy: ["Readable."],
        statistical_findings: ["Right skew."],
        limitations: ["Binning sensitive."],
        carry_forward_notes: [],
        required_revision: "",
        report_markdown: "Report.",
      }),
    ),
    textArtifact("05-visual-reviewer/distribution_histogram/attempt-1/report.md", "Report."),
  ];
  const map = new Map(files.map((artifact) => [artifact.path, artifact]));
  return {
    rootName: "run",
    lineage,
    files: map,
    paths: Array.from(map.keys()).sort(),
  };
}

function textArtifact(path: string, text: string): RunArtifact {
  return {
    kind: "text",
    path,
    size: text.length,
    text,
  };
}

function imageArtifact(path: string): RunArtifact {
  return {
    kind: "image",
    path,
    size: 10,
    url: `/api/run-file?path=${encodeURIComponent(path)}`,
  };
}

function binaryArtifact(path: string): RunArtifact {
  return {
    kind: "binary",
    path,
    size: 10,
  };
}
