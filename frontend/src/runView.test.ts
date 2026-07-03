import { describe, expect, it } from "vitest";

import { artifactView, filesView, overviewView, pipelineView, viewKey } from "./runView";

describe("runView constructors", () => {
  it("builds an artifact view carrying the artifact id", () => {
    expect(artifactView("target_outlier_boxplot")).toEqual({
      kind: "artifact",
      artifactId: "target_outlier_boxplot",
    });
  });

  it("builds a files view carrying the selected path", () => {
    expect(filesView("lineage.json")).toEqual({ kind: "files", path: "lineage.json" });
    expect(filesView(null)).toEqual({ kind: "files", path: null });
  });
});

describe("viewKey", () => {
  it("gives stable keys per view, scoping artifact views by id", () => {
    expect(viewKey(overviewView())).toBe("overview");
    expect(viewKey(pipelineView())).toBe("pipeline");
    expect(viewKey(filesView(null))).toBe("files");
    expect(viewKey(artifactView("a"))).toBe("artifact:a");
    expect(viewKey(artifactView("b"))).toBe("artifact:b");
  });
});
