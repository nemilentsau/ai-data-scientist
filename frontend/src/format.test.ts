import { describe, expect, it } from "vitest";

import { datasetFromRunId, humanizeId, runNameFromId, statusTone } from "./format";

describe("humanizeId", () => {
  it("turns a snake_case artifact id into sentence case", () => {
    expect(humanizeId("target_distribution_histogram")).toBe("Target distribution histogram");
  });

  it("turns a kebab-case run id into sentence case", () => {
    expect(humanizeId("target-distribution-modeling")).toBe("Target distribution modeling");
  });

  it("returns an empty string unchanged", () => {
    expect(humanizeId("")).toBe("");
  });
});

describe("datasetFromRunId", () => {
  it("reads the dataset segment before the slash", () => {
    expect(datasetFromRunId("multimodal/target-distribution-modeling")).toBe("multimodal");
  });

  it("falls back to the whole id when there is no slash", () => {
    expect(datasetFromRunId("solo-run")).toBe("solo-run");
  });
});

describe("runNameFromId", () => {
  it("reads the run segment after the last slash", () => {
    expect(runNameFromId("multimodal/target-distribution-modeling")).toBe(
      "target-distribution-modeling",
    );
  });
});

describe("statusTone", () => {
  it("maps passing statuses to the pass tone", () => {
    expect(statusTone("pass")).toBe("pass");
    expect(statusTone("passed")).toBe("pass");
    expect(statusTone("passed_visual_gate")).toBe("pass");
  });

  it("maps revision statuses to the revise tone", () => {
    expect(statusTone("revise")).toBe("revise");
    expect(statusTone("revision_requested")).toBe("revise");
  });

  it("maps exhausted and failed statuses to the fail tone", () => {
    expect(statusTone("revision_budget_exhausted")).toBe("fail");
    expect(statusTone("failed")).toBe("fail");
  });

  it("maps anything else to the neutral tone", () => {
    expect(statusTone("unknown")).toBe("neutral");
  });
});
