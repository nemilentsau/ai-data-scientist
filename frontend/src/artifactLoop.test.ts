import { describe, expect, it } from "vitest";

import {
  deriveArtifactSummaries,
  importantPathsForRun,
  latestAttempt,
} from "./artifactLoop";
import type { LoadedRun, RunArtifact, RunLineage } from "./types";

describe("deriveArtifactSummaries", () => {
  it("groups artifact-loop files by framer plan order and attempt", () => {
    const run = loadedRun({
      lineage: {
        status: "passed_visual_gate",
        artifact_statuses: {
          bin_sensitivity: "passed",
          distribution_histogram: "passed",
        },
      },
      files: [
        textArtifact(
          "01-eda-framer/output.json",
          JSON.stringify({
            user_question: "Assess distribution.",
            analysis_goal: "Inspect the target distribution.",
            artifact_plan: [
              {
                id: "distribution_histogram",
                purpose: "Inspect modality.",
                statistical_check: "Is the distribution simple?",
                artifact_type: "chart",
                expected_chart_family: "histogram",
                required_fields: ["monthly_rent_usd"],
                interpretation_limits: ["A single bin width may not establish modality."],
              },
              {
                id: "bin_sensitivity",
                purpose: "Check bin-width stability.",
                statistical_check: "Does modality depend on bin width?",
                artifact_type: "chart",
                expected_chart_family: "small_multiple_histograms",
                required_fields: ["monthly_rent_usd"],
                interpretation_limits: ["This is a visual stability check."],
              },
            ],
            stop_conditions: ["No modeling claims."],
          }),
        ),
        textArtifact(
          "02-artifact-builder/distribution_histogram/attempt-1/query.sql",
          "select 1",
        ),
        imageArtifact("04-render/distribution_histogram/attempt-1/chart.png"),
        textArtifact(
          "05-visual-reviewer/distribution_histogram/attempt-1/output.json",
          JSON.stringify({ artifact_id: "distribution_histogram", verdict: "pass" }),
        ),
        textArtifact("05-visual-reviewer/bin_sensitivity/attempt-2/report.md", "# Report"),
      ],
    });

    const summaries = deriveArtifactSummaries(run);

    expect(summaries.map((summary) => summary.id)).toEqual([
      "distribution_histogram",
      "bin_sensitivity",
    ]);
    expect(summaries[0]?.status).toBe("passed");
    expect(summaries[0]?.plan?.purpose).toBe("Inspect modality.");
    expect(summaries[0]?.attempts[0]?.number).toBe(1);
    expect(summaries[0]?.attempts[0]?.paths.renderImage).toBe(
      "04-render/distribution_histogram/attempt-1/chart.png",
    );
    expect(summaries[1]?.attempts[0]?.number).toBe(2);
  });

  it("rejects artifact ids that are not present in the framer plan", () => {
    const run = loadedRun({
      lineage: {
        artifact_statuses: {
          fallback_artifact: "revision_budget_exhausted",
        },
      },
      files: [
        textArtifact("01-eda-framer/output.json", fullFramerOutput(["planned_artifact"])),
        imageArtifact("04-render/fallback_artifact/attempt-1/chart.png"),
        textArtifact("lineage.json", "{}"),
      ],
    });

    expect(() => deriveArtifactSummaries(run)).toThrow(/unknown artifact/);
  });
});

describe("importantPathsForRun", () => {
  it("prioritizes framer output, rendered evidence, review context, reports, and lineage", () => {
    const run = loadedRun({
      lineage: {
        artifact_statuses: {
          distribution_histogram: "passed",
        },
      },
      files: [
        textArtifact("lineage.json", "{}"),
        textArtifact("06-synthesis/report.md", "# Summary"),
        textArtifact("01-eda-framer/output.json", fullFramerOutput(["distribution_histogram"])),
        imageArtifact("04-render/distribution_histogram/attempt-1/chart.png"),
        textArtifact(
          "05-visual-reviewer/distribution_histogram/attempt-1/review-context.json",
          "{}",
        ),
        textArtifact(
          "05-visual-reviewer/distribution_histogram/attempt-1/output.json",
          "{}",
        ),
        textArtifact(
          "05-visual-reviewer/distribution_histogram/attempt-1/report.md",
          "# Report",
        ),
      ],
    });

    expect(importantPathsForRun(run)).toEqual([
      "01-eda-framer/output.json",
      "04-render/distribution_histogram/attempt-1/chart.png",
      "05-visual-reviewer/distribution_histogram/attempt-1/review-context.json",
      "05-visual-reviewer/distribution_histogram/attempt-1/output.json",
      "05-visual-reviewer/distribution_histogram/attempt-1/report.md",
      "06-synthesis/report.md",
      "lineage.json",
    ]);
  });
});

describe("latestAttempt", () => {
  it("returns the highest numbered attempt", () => {
    const summary = deriveArtifactSummaries(
      loadedRun({
        lineage: {
          artifact_statuses: {
            distribution_histogram: "passed",
          },
        },
        files: [
          textArtifact("01-eda-framer/output.json", fullFramerOutput(["distribution_histogram"])),
          imageArtifact("04-render/distribution_histogram/attempt-1/chart.png"),
          imageArtifact("04-render/distribution_histogram/attempt-2/chart.png"),
        ],
      }),
    )[0];

    expect(summary ? latestAttempt(summary)?.number : undefined).toBe(2);
  });
});

function loadedRun({
  lineage,
  files,
}: {
  lineage: RunLineage;
  files: RunArtifact[];
}): LoadedRun {
  const map = new Map(files.map((artifact) => [artifact.path, artifact]));
  return {
    rootName: "run",
    lineage,
    files: map,
    paths: Array.from(map.keys()).sort(),
  };
}

function fullFramerOutput(artifactIds: string[]): string {
  return JSON.stringify({
    user_question: "Assess distribution.",
    analysis_goal: "Inspect target distribution.",
    artifact_plan: artifactIds.map((id) => ({
      id,
      purpose: "Inspect shape.",
      statistical_check: "Check skew and modality.",
      artifact_type: "chart",
      expected_chart_family: "histogram",
      required_fields: ["monthly_rent_usd"],
      interpretation_limits: ["Visual check only."],
    })),
    stop_conditions: ["No modeling claims."],
  });
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
