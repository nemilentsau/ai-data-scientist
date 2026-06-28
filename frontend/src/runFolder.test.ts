import { describe, expect, it } from "vitest";

import { loadRunFolder, pickInitialPath } from "./runFolder";

describe("loadRunFolder", () => {
  it("loads a run folder and normalizes artifact paths under its lineage root", async () => {
    const run = await loadRunFolder([
      fileAt(
        "inspectable-smoke/lineage.json",
        JSON.stringify({
          status: "passed_visual_gate",
          revision_count: 1,
          dependencies: {
            "05-visual-reviewer/attempt-1/output.json": ["04-render/attempt-1/chart.png"],
          },
        }),
      ),
      fileAt("inspectable-smoke/01-eda-framer/output.json", "{\"goal\":\"inspect\"}"),
      fileAt("inspectable-smoke/03-execution/attempt-1/result.parquet", new Uint8Array([1, 2])),
    ]);

    expect(run.rootName).toBe("inspectable-smoke");
    expect(run.lineage.status).toBe("passed_visual_gate");
    expect(run.files.get("03-execution/attempt-1/result.parquet")?.kind).toBe("binary");
    expect(run.paths).toEqual([
      "01-eda-framer/output.json",
      "03-execution/attempt-1/result.parquet",
      "lineage.json",
    ]);
  });

  it("chooses the first role output before secondary artifacts", async () => {
    const run = await loadRunFolder([
      fileAt("run/lineage.json", "{\"dependencies\":{}}"),
      fileAt("run/05-visual-reviewer/attempt-1/report.md", "# Report"),
      fileAt("run/01-eda-framer/output.json", "{}"),
    ]);

    expect(pickInitialPath(run)).toBe("01-eda-framer/output.json");
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
