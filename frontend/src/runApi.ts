import { stageSort } from "./runFolder";
import type { LoadedRun, RunArtifact, RunLineage } from "./types";

export type RunSummary = {
  id: string;
  path: string;
  modifiedAt: string;
  artifactCount: number;
};

type RunsResponse = {
  runs: RunSummary[];
};

type ApiArtifact =
  | {
      kind: "text";
      path: string;
      size: number;
      text: string;
    }
  | {
      kind: "image";
      path: string;
      size: number;
      url: string;
    }
  | {
      kind: "binary";
      path: string;
      size: number;
    };

type ApiRunResponse = {
  rootName: string;
  lineage: RunLineage;
  paths: string[];
  files: ApiArtifact[];
};

export async function listLocalRuns(): Promise<RunSummary[]> {
  const response = await fetchJson<unknown>("/api/runs");
  const parsed = parseRunsResponse(response);
  return parsed.runs;
}

export async function loadLocalRun(runId: string): Promise<LoadedRun> {
  const params = new URLSearchParams({ run: runId });
  const response = await fetchJson<unknown>(`/api/run?${params.toString()}`);
  return loadedRunFromApiResponse(response);
}

export function loadedRunFromApiResponse(response: unknown): LoadedRun {
  const parsed = parseRunResponse(response);
  return {
    rootName: parsed.rootName,
    lineage: parsed.lineage,
    paths: [...parsed.paths].sort(stageSort),
    files: new Map(parsed.files.map((artifact) => [artifact.path, artifact] satisfies [string, RunArtifact])),
  };
}

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  const body = (await response.json()) as unknown;

  if (!response.ok) {
    throw new Error(errorMessageFromBody(body));
  }

  return body as T;
}

function parseRunsResponse(value: unknown): RunsResponse {
  if (!isRecord(value) || !Array.isArray(value.runs)) {
    throw new Error("Run list response was not valid.");
  }

  const runs = value.runs.map(parseRunSummary);
  return { runs };
}

function parseRunSummary(value: unknown): RunSummary {
  if (!isRecord(value)) throw new Error("Run summary response was not valid.");

  const id = requiredString(value, "id");
  return {
    id,
    path: requiredString(value, "path"),
    modifiedAt: requiredString(value, "modifiedAt"),
    artifactCount: requiredNumber(value, "artifactCount"),
  };
}

function parseRunResponse(value: unknown): ApiRunResponse {
  if (!isRecord(value) || !Array.isArray(value.paths) || !Array.isArray(value.files)) {
    throw new Error("Run response was not valid.");
  }

  const lineage = value.lineage;
  if (!isRecord(lineage)) {
    throw new Error("Run response lineage was not valid.");
  }

  return {
    rootName: requiredString(value, "rootName"),
    lineage: lineage as RunLineage,
    paths: value.paths.map((path) => {
      if (typeof path !== "string") throw new Error("Run response paths were not valid.");
      return path;
    }),
    files: value.files.map(parseArtifact),
  };
}

function parseArtifact(value: unknown): ApiArtifact {
  if (!isRecord(value)) throw new Error("Run artifact response was not valid.");

  const kind = requiredString(value, "kind");
  const path = requiredString(value, "path");
  const size = requiredNumber(value, "size");

  if (kind === "text") {
    return {
      kind,
      path,
      size,
      text: requiredString(value, "text"),
    };
  }

  if (kind === "image") {
    return {
      kind,
      path,
      size,
      url: requiredString(value, "url"),
    };
  }

  if (kind === "binary") {
    return {
      kind,
      path,
      size,
    };
  }

  throw new Error(`Unsupported artifact kind: ${kind}.`);
}

function errorMessageFromBody(body: unknown): string {
  if (isRecord(body) && typeof body.error === "string") return body.error;
  return "Run API request failed.";
}

function requiredString(record: Record<string, unknown>, key: string): string {
  const value = record[key];
  if (typeof value !== "string") throw new Error(`Expected string field: ${key}.`);
  return value;
}

function requiredNumber(record: Record<string, unknown>, key: string): number {
  const value = record[key];
  if (typeof value !== "number") throw new Error(`Expected number field: ${key}.`);
  return value;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
