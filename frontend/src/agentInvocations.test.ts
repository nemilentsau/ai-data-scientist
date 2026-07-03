import { describe, expect, it } from "vitest";

import { deriveAgentInvocations } from "./agentInvocations";
import type { LoadedRun, RunArtifact, RunLineage } from "./types";

describe("deriveAgentInvocations", () => {
  it("exposes every Codex role call in graph order", () => {
    const run = loadedRun({
      lineage: {
        status: "passed_visual_gate",
        artifact_statuses: {
          distribution_histogram: "passed",
          bin_sensitivity: "passed",
        },
        dependencies: {},
      },
      files: [
        textArtifact("00-dataset/profile.json", "{}"),
        textArtifact("01-eda-framer/prompt.md", "# framer prompt"),
        textArtifact("01-eda-framer/user-question.txt", "Assess distribution."),
        textArtifact("01-eda-framer/output.schema.json", "{}"),
        textArtifact(
          "01-eda-framer/output.json",
          fullFramerOutput(["distribution_histogram", "bin_sensitivity"]),
        ),
        ...artifactAttemptFiles("distribution_histogram", 1),
        ...artifactAttemptFiles("bin_sensitivity", 1),
      ],
    });

    expect(
      deriveAgentInvocations(run).map(({ role, artifactId, attempt }) => ({
        role,
        artifactId,
        attempt,
      })),
    ).toEqual([
      { role: "eda_framer", artifactId: undefined, attempt: undefined },
      { role: "artifact_builder", artifactId: "distribution_histogram", attempt: 1 },
      { role: "visual_reviewer", artifactId: "distribution_histogram", attempt: 1 },
      { role: "artifact_builder", artifactId: "bin_sensitivity", attempt: 1 },
      { role: "visual_reviewer", artifactId: "bin_sensitivity", attempt: 1 },
    ]);
  });

  it("keeps revision attempts as separate agent invocations", () => {
    const run = loadedRun({
      lineage: {
        status: "passed_visual_gate",
        artifact_statuses: {
          distribution_histogram: "passed",
          bin_sensitivity: "passed",
        },
        dependencies: {},
      },
      files: [
        textArtifact("00-dataset/profile.json", "{}"),
        textArtifact("01-eda-framer/prompt.md", "# framer prompt"),
        textArtifact("01-eda-framer/user-question.txt", "Assess distribution."),
        textArtifact("01-eda-framer/output.schema.json", "{}"),
        textArtifact(
          "01-eda-framer/output.json",
          fullFramerOutput(["distribution_histogram", "bin_sensitivity"]),
        ),
        ...artifactAttemptFiles("distribution_histogram", 1),
        ...artifactAttemptFiles("distribution_histogram", 2),
        ...artifactAttemptFiles("bin_sensitivity", 1),
      ],
    });

    expect(deriveAgentInvocations(run).map((invocation) => invocation.id)).toEqual([
      "eda_framer",
      "artifact_builder/distribution_histogram/attempt-1",
      "visual_reviewer/distribution_histogram/attempt-1",
      "artifact_builder/distribution_histogram/attempt-2",
      "visual_reviewer/distribution_histogram/attempt-2",
      "artifact_builder/bin_sensitivity/attempt-1",
      "visual_reviewer/bin_sensitivity/attempt-1",
    ]);
  });

  it("records visible inputs and outputs for each agent invocation", () => {
    const run = loadedRun({
      lineage: {
        status: "passed_visual_gate",
        artifact_statuses: {
          distribution_histogram: "passed",
        },
        dependencies: {},
      },
      files: [
        textArtifact("00-dataset/profile.json", "{}"),
        textArtifact("01-eda-framer/prompt.md", "# framer prompt"),
        textArtifact("01-eda-framer/user-question.txt", "Assess distribution."),
        textArtifact("01-eda-framer/output.schema.json", "{}"),
        textArtifact("01-eda-framer/output.json", fullFramerOutput(["distribution_histogram"])),
        ...artifactAttemptFiles("distribution_histogram", 1),
      ],
    });

    const invocations = deriveAgentInvocations(run);

    expect(invocations[0]).toMatchObject({
      role: "eda_framer",
      label: "EDA framer",
      inputPaths: [
        "01-eda-framer/prompt.md",
        "01-eda-framer/user-question.txt",
        "01-eda-framer/output.schema.json",
        "00-dataset/profile.json",
      ],
      outputPaths: ["01-eda-framer/output.json"],
    });
    expect(invocations[1]).toMatchObject({
      role: "artifact_builder",
      label: "Artifact builder",
      artifactId: "distribution_histogram",
      attempt: 1,
      inputPaths: [
        "02-artifact-builder/distribution_histogram/attempt-1/prompt.md",
        "02-artifact-builder/distribution_histogram/attempt-1/build-context.json",
        "02-artifact-builder/distribution_histogram/attempt-1/output.schema.json",
      ],
      outputPaths: [
        "02-artifact-builder/distribution_histogram/attempt-1/output.json",
        "02-artifact-builder/distribution_histogram/attempt-1/query.sql",
        "02-artifact-builder/distribution_histogram/attempt-1/chart.vegalite.json",
      ],
    });
    expect(invocations[2]).toMatchObject({
      role: "visual_reviewer",
      label: "Visual reviewer",
      artifactId: "distribution_histogram",
      attempt: 1,
      inputPaths: [
        "05-visual-reviewer/distribution_histogram/attempt-1/prompt.md",
        "05-visual-reviewer/distribution_histogram/attempt-1/review-context.json",
        "05-visual-reviewer/distribution_histogram/attempt-1/image-inputs.json",
        "05-visual-reviewer/distribution_histogram/attempt-1/output.schema.json",
        "04-render/distribution_histogram/attempt-1/chart.png",
      ],
      outputPaths: [
        "05-visual-reviewer/distribution_histogram/attempt-1/output.json",
        "05-visual-reviewer/distribution_histogram/attempt-1/report.md",
      ],
    });
  });
});

function loadedRun({
  lineage,
  files,
}: {
  lineage: RunLineage;
  files: RunArtifact[];
}): LoadedRun {
  const allFiles = [textArtifact("lineage.json", JSON.stringify(lineage)), ...files];
  const map = new Map(allFiles.map((artifact) => [artifact.path, artifact]));
  return {
    rootName: "run",
    lineage,
    files: map,
    paths: Array.from(map.keys()).sort(),
  };
}

function artifactAttemptFiles(artifactId: string, attempt: number): RunArtifact[] {
  const builderBase = `02-artifact-builder/${artifactId}/attempt-${attempt}`;
  const executionBase = `03-execution/${artifactId}/attempt-${attempt}`;
  const renderBase = `04-render/${artifactId}/attempt-${attempt}`;
  const reviewerBase = `05-visual-reviewer/${artifactId}/attempt-${attempt}`;

  return [
    textArtifact(`${builderBase}/build-context.json`, "{}"),
    textArtifact(`${builderBase}/prompt.md`, "# builder prompt"),
    textArtifact(`${builderBase}/output.schema.json`, "{}"),
    textArtifact(
      `${builderBase}/output.json`,
      JSON.stringify({
        artifact_id: artifactId,
        sql: "select 1",
        chart_spec: "{}",
      }),
    ),
    textArtifact(`${builderBase}/query.sql`, "select 1"),
    textArtifact(`${builderBase}/chart.vegalite.json`, "{}"),
    binaryArtifact(`${executionBase}/result.parquet`),
    textArtifact(`${executionBase}/result.summary.json`, "{}"),
    imageArtifact(`${renderBase}/chart.png`),
    textArtifact(`${reviewerBase}/review-context.json`, "{}"),
    textArtifact(`${reviewerBase}/prompt.md`, "# reviewer prompt"),
    textArtifact(`${reviewerBase}/image-inputs.json`, "{}"),
    textArtifact(`${reviewerBase}/output.schema.json`, "{}"),
    textArtifact(
      `${reviewerBase}/output.json`,
      JSON.stringify({
        artifact_id: artifactId,
        verdict: "pass",
        visual_adequacy: ["Readable."],
        statistical_findings: ["Distribution is inspectable."],
        limitations: [],
        carry_forward_notes: [],
        required_revision: "",
        report_markdown: "Report.",
      }),
    ),
    textArtifact(`${reviewerBase}/report.md`, "Report."),
  ];
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

function binaryArtifact(path: string): RunArtifact {
  return {
    kind: "binary",
    path,
    size: 10,
  };
}
