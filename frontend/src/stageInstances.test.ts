import { describe, expect, it } from "vitest";

import { makeRun } from "./runFixture";
import { stageInstances } from "./stageInstances";

const run = makeRun({
  artifacts: [
    { id: "hist", status: "passed", attempts: [{ verdict: "revise" }, { verdict: "pass" }] },
    { id: "ecdf", status: "passed", attempts: [{ verdict: "pass" }] },
  ],
  status: "passed_visual_gate",
});

describe("stageInstances", () => {
  it("returns one instance per artifact attempt for the build stage with its files", () => {
    const instances = stageInstances(run, "build");
    expect(instances.map((i) => i.key)).toEqual(["hist#1", "hist#2", "ecdf#1"]);
    expect(instances[0]?.artifactId).toBe("hist");
    expect(instances[0]?.attempt).toBe(1);
    expect(instances[0]?.paths).toContain("02-artifact-builder/hist/attempt-1/query.sql");
  });

  it("carries reviewer verdicts on review-stage instances", () => {
    const review = stageInstances(run, "review");
    expect(review.find((i) => i.key === "hist#1")?.verdict).toBe("revise");
    expect(review.find((i) => i.key === "hist#2")?.verdict).toBe("pass");
    expect(review[0]?.paths).toContain("05-visual-reviewer/hist/attempt-1/output.json");
  });

  it("lists the ordered artifact plan for the select node without files", () => {
    const select = stageInstances(run, "select");
    expect(select.map((i) => i.artifactId)).toEqual(["hist", "ecdf"]);
    expect(select[0]?.label).toBe("Hist");
    expect(select[0]?.paths).toEqual([]);
  });

  it("collapses framer, dataset, and finalize into a single instance each", () => {
    expect(stageInstances(run, "framer")).toHaveLength(1);
    expect(stageInstances(run, "dataset")[0]?.paths).toContain("00-dataset/profile.json");
    expect(stageInstances(run, "finalize")[0]?.paths).toContain("06-synthesis/report.md");
  });
});
