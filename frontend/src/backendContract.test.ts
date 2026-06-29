import { readdir, readFile, stat } from "node:fs/promises";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { deriveAgentInvocations } from "./agentInvocations";
import { stageSort } from "./runFolder";
import { resolveSelectedView, validateInspectableRun } from "./selectedView";
import type { LoadedRun, RunArtifact } from "./types";

const runDirectory = process.env.EDA_RUN_DIR;
const contractDescribe = runDirectory ? describe : describe.skip;

contractDescribe("backend run contract", () => {
  it("classifies every artifact path produced by the backend fake smoke", async () => {
    const run = await loadRunFromDirectory(runDirectory as string);

    validateInspectableRun(run);

    expect(run.files.has("01-eda-framer/output.json")).toBe(true);
    expect(resolveSelectedView(run, "01-eda-framer/output.json").kind).toBe("run-framer");

    for (const path of run.paths) {
      expect(() => resolveSelectedView(run, path), path).not.toThrow();
    }
  });

  it("exposes every Codex agent invocation produced by the backend fake smoke", async () => {
    const run = await loadRunFromDirectory(runDirectory as string);

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
});

async function loadRunFromDirectory(runDir: string): Promise<LoadedRun> {
  const paths = (await listFiles(runDir)).sort(stageSort);
  const files = await Promise.all(paths.map((path) => readArtifact(runDir, path)));
  const lineage = files.find((artifact) => artifact.path === "lineage.json");

  if (lineage?.kind !== "text") {
    throw new Error("Backend contract fixture does not contain lineage.json.");
  }

  return {
    rootName: runDir.split("/").filter(Boolean).at(-1) ?? "contract-run",
    lineage: JSON.parse(lineage.text) as LoadedRun["lineage"],
    paths,
    files: new Map(files.map((artifact) => [artifact.path, artifact])),
  };
}

async function listFiles(root: string): Promise<string[]> {
  const results: string[] = [];
  const entries = await readdir(root, { withFileTypes: true });

  for (const entry of entries) {
    if (entry.name.startsWith(".") || entry.name === ".DS_Store") continue;

    const fullPath = join(root, entry.name);
    if (entry.isDirectory()) {
      const nested = await listFiles(fullPath);
      results.push(...nested.map((path) => toPosix(join(entry.name, path))));
    } else if (entry.isFile()) {
      results.push(entry.name);
    }
  }

  return results;
}

async function readArtifact(runDir: string, path: string): Promise<RunArtifact> {
  const fullPath = join(runDir, path);
  const artifactStats = await stat(fullPath);

  if (path.endsWith(".png")) {
    return {
      kind: "image",
      path,
      size: artifactStats.size,
      url: `/api/run-file?path=${encodeURIComponent(path)}`,
    };
  }

  if (path.endsWith(".parquet")) {
    return {
      kind: "binary",
      path,
      size: artifactStats.size,
    };
  }

  return {
    kind: "text",
    path,
    size: artifactStats.size,
    text: await readFile(fullPath, "utf8"),
  };
}

function toPosix(path: string): string {
  return path.split("\\").join("/");
}
