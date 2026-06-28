import type {
  JsonParseResult,
  LoadedRun,
  RunArtifact,
  RunLineage,
  StageDefinition,
} from "./types";

export const STAGES = [
  {
    id: "00-dataset",
    label: "Dataset",
    owner: "Harness",
    prefix: "00-dataset/",
  },
  {
    id: "01-eda-framer",
    label: "EDA framer",
    owner: "Codex role",
    prefix: "01-eda-framer/",
  },
  {
    id: "02-artifact-builder",
    label: "Artifact builder",
    owner: "Codex role",
    prefix: "02-artifact-builder/",
  },
  {
    id: "03-execution",
    label: "Execution",
    owner: "Harness",
    prefix: "03-execution/",
  },
  {
    id: "04-render",
    label: "Render",
    owner: "Harness",
    prefix: "04-render/",
  },
  {
    id: "05-visual-reviewer",
    label: "Visual reviewer",
    owner: "Codex role",
    prefix: "05-visual-reviewer/",
  },
] as const satisfies readonly StageDefinition[];

export type StageId = (typeof STAGES)[number]["id"];

export const IMPORTANT_ORDER = [
  "01-eda-framer/output.json",
  "02-artifact-builder/attempt-1/query.sql",
  "02-artifact-builder/attempt-1/chart.vegalite.json",
  "04-render/attempt-1/chart.png",
  "05-visual-reviewer/attempt-1/output.json",
  "05-visual-reviewer/attempt-1/report.md",
  "lineage.json",
] as const;

const LINEAGE_FILENAME = "lineage.json";

export async function loadRunFolder(files: readonly File[]): Promise<LoadedRun> {
  const rootPrefix = findRootPrefix(files);
  const entries = await Promise.all(files.map((file) => readArtifact(file, rootPrefix)));
  const artifactFiles = entries.filter((entry): entry is RunArtifact => entry !== null);
  const map = new Map(artifactFiles.map((entry) => [entry.path, entry]));
  const lineageEntry = map.get(LINEAGE_FILENAME);

  if (lineageEntry?.kind !== "text") {
    throw new Error("Selected folder does not contain lineage.json at a run root.");
  }

  const lineage = parseLineage(lineageEntry.text);
  const paths = Array.from(map.keys()).sort(stageSort);

  return {
    rootName: rootNameFromPrefix(rootPrefix),
    files: map,
    lineage,
    paths,
  };
}

export function pickInitialPath(run: LoadedRun): string | null {
  return (
    IMPORTANT_ORDER.find((path) => run.files.has(path)) ??
    run.paths.find((path) => path.endsWith(".png")) ??
    run.paths[0] ??
    null
  );
}

export function stageSort(left: string, right: string): number {
  const leftStage = stageIndex(left);
  const rightStage = stageIndex(right);
  if (leftStage !== rightStage) return leftStage - rightStage;
  return left.localeCompare(right);
}

export function labelForPath(path: string): string {
  if (path.endsWith("output.json")) return path.split("/").slice(0, -1).join("/");
  if (path.endsWith("chart.png")) return "rendered chart";
  if (path.endsWith("query.sql")) return "builder query";
  if (path.endsWith("report.md")) return "visual report";
  if (path.endsWith(LINEAGE_FILENAME)) return "lineage";
  return path;
}

export function safeParseJson(text: string): JsonParseResult {
  try {
    return { ok: true, value: JSON.parse(text) as unknown };
  } catch {
    return { ok: false };
  }
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

async function readArtifact(file: File, rootPrefix: string): Promise<RunArtifact | null> {
  const rawPath = browserRelativePath(file);
  if (!rawPath.startsWith(rootPrefix)) return null;

  const path = rawPath.slice(rootPrefix.length);
  if (!path || path.includes("/.") || path.endsWith(".DS_Store")) return null;

  if (path.endsWith(".png")) {
    return {
      path,
      kind: "image",
      size: file.size,
      url: URL.createObjectURL(file),
    };
  }

  if (path.endsWith(".parquet")) {
    return {
      path,
      kind: "binary",
      size: file.size,
    };
  }

  return {
    path,
    kind: "text",
    size: file.size,
    text: await file.text(),
  };
}

function findRootPrefix(files: readonly File[]): string {
  const lineage = files.find((file) => browserRelativePath(file).endsWith(LINEAGE_FILENAME));
  if (!lineage) {
    throw new Error("Choose a run folder that contains lineage.json.");
  }

  const path = browserRelativePath(lineage);
  return path.slice(0, path.length - LINEAGE_FILENAME.length);
}

function parseLineage(text: string): RunLineage {
  const value = JSON.parse(text) as unknown;
  if (!isRecord(value)) {
    throw new Error("lineage.json must contain a JSON object.");
  }

  const dependencies = value.dependencies;
  if (dependencies !== undefined && !isDependencyMap(dependencies)) {
    throw new Error("lineage.json dependencies must map artifact paths to path arrays.");
  }

  return value as RunLineage;
}

function isDependencyMap(value: unknown): value is Record<string, string[]> {
  if (!isRecord(value)) return false;
  return Object.values(value).every(
    (entry) => Array.isArray(entry) && entry.every((item) => typeof item === "string"),
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stageIndex(path: string): number {
  const index = STAGES.findIndex((stage) => path.startsWith(stage.prefix));
  return index === -1 ? 99 : index;
}

function rootNameFromPrefix(rootPrefix: string): string {
  return rootPrefix.replace(/\/$/, "").split("/").filter(Boolean).at(-1) ?? "selected-run";
}

function browserRelativePath(file: File): string {
  return file.webkitRelativePath || file.name;
}
