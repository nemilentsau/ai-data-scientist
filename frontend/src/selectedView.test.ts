import { describe, expect, it } from "vitest";

import { resolveSelectedView, validateInspectableRun } from "./selectedView";
import type { LoadedRun, RunArtifact, RunLineage } from "./types";

describe("resolveSelectedView", () => {
  it("resolves the EDA framer output as a run-level framer view", () => {
    const run = renderableRun();

    const view = resolveSelectedView(run, "01-eda-framer/output.json");

    expect(view.kind).toBe("run-framer");
    expect("artifact" in view).toBe(false);
  });

  it("rejects unknown artifact paths instead of falling back to an artifact", () => {
    const run = renderableRun([
      textArtifact("07-new-backend-stage/new-contract.json", "{}"),
    ]);

    expect(() =>
      resolveSelectedView(run, "07-new-backend-stage/new-contract.json"),
    ).toThrow(/Unsupported selected artifact path/);
  });
});

describe("validateInspectableRun", () => {
  it("rejects framer output that is missing artifact_plan", () => {
    const run = renderableRun();
    run.files.set(
      "01-eda-framer/output.json",
      textArtifact(
        "01-eda-framer/output.json",
        JSON.stringify({
          user_question: "Assess distribution.",
          analysis_goal: "Inspect the target distribution.",
          stop_conditions: ["No modeling claims."],
        }),
      ),
    );

    expect(() => validateInspectableRun(run)).toThrow(/artifact_plan/);
  });

  it("rejects reviewer output that is missing required critique fields", () => {
    const run = renderableRun();
    run.files.set(
      "05-visual-reviewer/distribution_histogram/attempt-1/output.json",
      textArtifact(
        "05-visual-reviewer/distribution_histogram/attempt-1/output.json",
        JSON.stringify({
          artifact_id: "distribution_histogram",
          verdict: "pass",
          visual_adequacy: ["Readable."],
        }),
      ),
    );

    expect(() => validateInspectableRun(run)).toThrow(/statistical_findings/);
  });
});

function renderableRun(extraFiles: RunArtifact[] = []): LoadedRun {
  const lineage: RunLineage = {
    status: "passed_visual_gate",
    artifact_statuses: {
      distribution_histogram: "passed",
    },
    dependencies: {},
  };
  const files: RunArtifact[] = [
    textArtifact("lineage.json", JSON.stringify(lineage)),
    textArtifact("00-dataset/profile.json", "{}"),
    textArtifact("01-eda-framer/prompt.md", "# prompt"),
    textArtifact("01-eda-framer/user-question.txt", "Assess distribution."),
    textArtifact("01-eda-framer/output.schema.json", "{}"),
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
    textArtifact(
      "02-artifact-builder/distribution_histogram/attempt-1/build-context.json",
      "{}",
    ),
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
    textArtifact(
      "02-artifact-builder/distribution_histogram/attempt-1/chart.vegalite.json",
      "{}",
    ),
    binaryArtifact("03-execution/distribution_histogram/attempt-1/result.parquet"),
    textArtifact(
      "03-execution/distribution_histogram/attempt-1/result.summary.json",
      JSON.stringify({ row_count: 1, columns: ["rent_bin", "listing_count"] }),
    ),
    imageArtifact("04-render/distribution_histogram/attempt-1/chart.png"),
    textArtifact(
      "05-visual-reviewer/distribution_histogram/attempt-1/review-context.json",
      "{}",
    ),
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
    textArtifact("06-synthesis/report.md", "Summary."),
    ...extraFiles,
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
