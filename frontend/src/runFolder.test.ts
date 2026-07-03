import { describe, expect, it } from "vitest";

import { importantPathsForRun } from "./artifactLoop";
import { fileChipLabel, labelForPath, loadRunFolder, pickInitialPath } from "./runFolder";
import type { LoadedRun, RunArtifact } from "./types";

describe("loadRunFolder", () => {
  it("loads a run folder and normalizes artifact paths under its lineage root", async () => {
    const run = await loadRunFolder([
      fileAt(
        "inspectable-smoke/lineage.json",
        JSON.stringify({
          status: "passed_visual_gate",
          artifact_statuses: {
            distribution_histogram: "passed",
          },
          dependencies: {
            "05-visual-reviewer/distribution_histogram/attempt-1/output.json": [
              "04-render/distribution_histogram/attempt-1/chart.png",
            ],
          },
        }),
      ),
      fileAt(
        "inspectable-smoke/01-eda-framer/output.json",
        fullFramerOutput(["distribution_histogram"]),
      ),
      fileAt(
        "inspectable-smoke/03-execution/distribution_histogram/attempt-1/result.parquet",
        new Uint8Array([1, 2]),
      ),
    ]);

    expect(run.rootName).toBe("inspectable-smoke");
    expect(run.lineage.status).toBe("passed_visual_gate");
    expect(
      run.files.get("03-execution/distribution_histogram/attempt-1/result.parquet")?.kind,
    ).toBe("binary");
    expect(run.paths).toEqual([
      "01-eda-framer/output.json",
      "03-execution/distribution_histogram/attempt-1/result.parquet",
      "lineage.json",
    ]);
  });

  it("chooses the first role output before secondary artifacts", async () => {
    const run = await loadRunFolder([
      fileAt(
        "run/lineage.json",
        JSON.stringify({
          status: "passed_visual_gate",
          artifact_statuses: {
            distribution_histogram: "passed",
          },
          dependencies: {},
        }),
      ),
      fileAt("run/05-visual-reviewer/distribution_histogram/attempt-1/report.md", "# Report"),
      fileAt("run/01-eda-framer/output.json", fullFramerOutput(["distribution_histogram"])),
    ]);

    expect(pickInitialPath(run)).toBe("01-eda-framer/output.json");
  });

  it("surfaces current visual-review contract artifacts as inspectable jumps", () => {
    const artifacts: RunArtifact[] = [
      {
        kind: "text",
        path: "lineage.json",
        size: 2,
        text: JSON.stringify({
          status: "passed_visual_gate",
          artifact_statuses: {
            distribution_histogram: "passed",
          },
          dependencies: {},
        }),
      },
      {
        kind: "text",
        path: "01-eda-framer/output.json",
        size: 2,
        text: fullFramerOutput(["distribution_histogram"]),
      },
      {
        kind: "image",
        path: "04-render/distribution_histogram/attempt-1/chart.png",
        size: 10,
        url: "/chart.png",
      },
      {
        kind: "text",
        path: "05-visual-reviewer/distribution_histogram/attempt-1/review-context.json",
        size: 2,
        text: "{}",
      },
      {
        kind: "text",
        path: "05-visual-reviewer/distribution_histogram/attempt-1/output.json",
        size: 2,
        text: JSON.stringify({
          artifact_id: "distribution_histogram",
          verdict: "pass",
          visual_adequacy: ["The chart is readable."],
          statistical_findings: ["The plotted distribution can be inspected visually."],
          limitations: ["Visual evidence alone does not prove modality."],
          carry_forward_notes: ["Compare against alternative binnings."],
          required_revision: "",
          report_markdown: "# Review",
        }),
      },
    ];
    const run: LoadedRun = {
      rootName: "run",
      lineage: {
        status: "passed_visual_gate",
        artifact_statuses: {
          distribution_histogram: "passed",
        },
        dependencies: {},
      },
      paths: artifacts.map((artifact) => artifact.path),
      files: new Map(artifacts.map((artifact) => [artifact.path, artifact])),
    };

    expect(importantPathsForRun(run)).toContain(
      "05-visual-reviewer/distribution_histogram/attempt-1/review-context.json",
    );
    expect(labelForPath("05-visual-reviewer/distribution_histogram/attempt-1/image-inputs.json")).toBe(
      "visual reviewer image inputs",
    );
    expect(labelForPath("05-visual-reviewer/distribution_histogram/attempt-1/output.schema.json")).toBe(
      "visual reviewer schema",
    );
    expect(labelForPath("05-visual-reviewer/distribution_histogram/attempt-2/output.schema.json")).toBe(
      "visual reviewer schema",
    );
  });

  it("rejects folders without lineage", async () => {
    await expect(loadRunFolder([fileAt("run/01-eda-framer/output.json", "{}")])).rejects.toThrow(
      /lineage\.json/,
    );
  });
});

function fileAt(path: string, contents: BlobPart): File {
  const name = path.split("/").at(-1) ?? "artifact.txt";
  const file = new File([contents], name);
  Object.defineProperty(file, "webkitRelativePath", {
    value: path,
  });
  return file;
}

describe("fileChipLabel", () => {
  it("keeps friendly labels but falls back to the filename for path-shaped labels", () => {
    expect(fileChipLabel("05-visual-reviewer/hist/attempt-1/review-context.json")).toBe(
      "review context",
    );
    expect(fileChipLabel("05-visual-reviewer/hist/attempt-1/output.json")).toBe("output.json");
  });
});

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
