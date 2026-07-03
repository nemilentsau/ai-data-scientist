import { describe, expect, it } from "vitest";

import { loadedRunFromApiResponse } from "./runApi";

describe("loadedRunFromApiResponse", () => {
  it("converts API artifacts into the inspector run model", () => {
    const run = loadedRunFromApiResponse({
      rootName: "inspectable-smoke",
      lineage: {
        status: "passed_visual_gate",
        artifact_statuses: {
          distribution_histogram: "passed",
        },
        dependencies: {
          "05-visual-reviewer/distribution_histogram/attempt-1/output.json": [
            "04-render/distribution_histogram/attempt-1/chart.png",
          ],
        },
      },
      paths: [
        "lineage.json",
        "04-render/distribution_histogram/attempt-1/chart.png",
        "01-eda-framer/output.json",
      ],
      files: [
        {
          kind: "text",
          path: "lineage.json",
          size: 2,
          text: "{}",
        },
        {
          kind: "image",
          path: "04-render/distribution_histogram/attempt-1/chart.png",
          size: 10,
          url: "/api/run-file?run=multimodal%2Finspectable-smoke&path=04-render%2Fdistribution_histogram%2Fattempt-1%2Fchart.png",
        },
      ],
    });

    expect(run.rootName).toBe("inspectable-smoke");
    expect(run.paths).toEqual([
      "01-eda-framer/output.json",
      "04-render/distribution_histogram/attempt-1/chart.png",
      "lineage.json",
    ]);
    expect(run.files.get("04-render/distribution_histogram/attempt-1/chart.png")?.kind).toBe(
      "image",
    );
  });

  it("rejects malformed API responses", () => {
    expect(() => loadedRunFromApiResponse({ rootName: "bad", paths: [], files: [] })).toThrow(
      /lineage/,
    );
  });
});
