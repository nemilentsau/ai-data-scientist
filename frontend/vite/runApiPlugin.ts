import { createReadStream } from "node:fs";
import { readdir, readFile, stat } from "node:fs/promises";
import type { IncomingMessage, ServerResponse } from "node:http";
import { dirname, extname, join, relative, resolve, sep } from "node:path";
import type { Plugin } from "vite";

type NextFunction = (error?: unknown) => void;

type Middleware = (
  request: IncomingMessage,
  response: ServerResponse,
  next: NextFunction,
) => void | Promise<void>;

type MiddlewareStack = {
  use: (handler: Middleware) => void;
};

type RunSummaryDto = {
  id: string;
  path: string;
  modifiedAt: string;
  artifactCount: number;
};

type ArtifactDto =
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

type RunDto = {
  rootName: string;
  lineage: unknown;
  paths: string[];
  files: ArtifactDto[];
};

const API_ORIGIN = "http://localhost";
const RUNS_ROUTE = "/api/runs";
const RUN_ROUTE = "/api/run";
const RUN_FILE_ROUTE = "/api/run-file";

export function runApiPlugin(repoRoot: string): Plugin {
  return {
    name: "eda-artifacts-run-api",
    configureServer(server) {
      installRunApi(server.middlewares, repoRoot);
    },
    configurePreviewServer(server) {
      installRunApi(server.middlewares, repoRoot);
    },
  };
}

function installRunApi(middlewares: MiddlewareStack, repoRoot: string): void {
  const runRoot = resolve(repoRoot, "runs", "eda-artifacts");

  middlewares.use(async (request, response, next) => {
    const url = new URL(request.url ?? "/", API_ORIGIN);

    if (!url.pathname.startsWith("/api/")) {
      next();
      return;
    }

    if (request.method !== "GET") {
      sendJson(response, 405, { error: "Only GET is supported." });
      return;
    }

    try {
      if (url.pathname === RUNS_ROUTE) {
        sendJson(response, 200, { runs: await listRuns(runRoot) });
        return;
      }

      if (url.pathname === RUN_ROUTE) {
        sendJson(response, 200, await loadRun(runRoot, requiredParam(url, "run")));
        return;
      }

      if (url.pathname === RUN_FILE_ROUTE) {
        await sendRunFile(
          response,
          runRoot,
          requiredParam(url, "run"),
          requiredParam(url, "path"),
        );
        return;
      }

      next();
    } catch (error) {
      sendJson(response, statusForError(error), { error: messageForError(error) });
    }
  });
}

async function listRuns(runRoot: string): Promise<RunSummaryDto[]> {
  const lineagePaths = await findLineageFiles(runRoot);
  const runs = await Promise.all(
    lineagePaths.map(async (lineagePath) => {
      const runDir = dirname(lineagePath);
      const lineageStats = await stat(lineagePath);
      const files = await listFiles(runDir);
      const id = toPosix(relative(runRoot, runDir));

      return {
        id,
        path: `runs/eda-artifacts/${id}`,
        modifiedAt: lineageStats.mtime.toISOString(),
        artifactCount: files.length,
      };
    }),
  );

  return runs.sort((left, right) => right.modifiedAt.localeCompare(left.modifiedAt));
}

async function loadRun(runRoot: string, runId: string): Promise<RunDto> {
  const runDir = resolveUnder(runRoot, runId);
  const paths = (await listFiles(runDir)).sort();
  const files = await Promise.all(paths.map((path) => readArtifact(runDir, runId, path)));
  const lineageArtifact = files.find((file) => file.path === "lineage.json");

  if (lineageArtifact?.kind !== "text") {
    throw httpError(404, "Run does not contain lineage.json.");
  }

  return {
    rootName: runId.split("/").filter(Boolean).at(-1) ?? "selected-run",
    lineage: JSON.parse(lineageArtifact.text) as unknown,
    paths,
    files,
  };
}

async function readArtifact(runDir: string, runId: string, path: string): Promise<ArtifactDto> {
  const fullPath = resolveUnder(runDir, path);
  const artifactStats = await stat(fullPath);

  if (path.endsWith(".png")) {
    const params = new URLSearchParams({ run: runId, path });
    return {
      kind: "image",
      path,
      size: artifactStats.size,
      url: `${RUN_FILE_ROUTE}?${params.toString()}`,
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

async function sendRunFile(
  response: ServerResponse,
  runRoot: string,
  runId: string,
  artifactPath: string,
): Promise<void> {
  const runDir = resolveUnder(runRoot, runId);
  const fullPath = resolveUnder(runDir, artifactPath);
  const artifactStats = await stat(fullPath);

  if (!artifactStats.isFile()) {
    throw httpError(404, "Artifact file was not found.");
  }

  response.statusCode = 200;
  response.setHeader("Content-Type", contentTypeFor(fullPath));
  response.setHeader("Content-Length", String(artifactStats.size));
  createReadStream(fullPath).pipe(response);
}

async function findLineageFiles(root: string): Promise<string[]> {
  if (!(await exists(root))) return [];

  const found: string[] = [];
  const entries = await readdir(root, { withFileTypes: true });

  for (const entry of entries) {
    if (entry.name.startsWith(".")) continue;

    const fullPath = join(root, entry.name);
    if (entry.isFile() && entry.name === "lineage.json") {
      found.push(fullPath);
    } else if (entry.isDirectory()) {
      found.push(...(await findLineageFiles(fullPath)));
    }
  }

  return found;
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

function requiredParam(url: URL, name: string): string {
  const value = url.searchParams.get(name);
  if (!value) throw httpError(400, `Missing required parameter: ${name}.`);
  return value;
}

function resolveUnder(root: string, relativePath: string): string {
  const resolvedRoot = resolve(root);
  const resolvedPath = resolve(resolvedRoot, relativePath);
  const rootBoundary = resolvedRoot.endsWith(sep) ? resolvedRoot : `${resolvedRoot}${sep}`;

  if (resolvedPath !== resolvedRoot && !resolvedPath.startsWith(rootBoundary)) {
    throw httpError(400, "Path is outside the run root.");
  }

  return resolvedPath;
}

function sendJson(response: ServerResponse, statusCode: number, body: unknown): void {
  response.statusCode = statusCode;
  response.setHeader("Content-Type", "application/json; charset=utf-8");
  response.end(JSON.stringify(body));
}

function contentTypeFor(path: string): string {
  if (extname(path) === ".png") return "image/png";
  return "application/octet-stream";
}

async function exists(path: string): Promise<boolean> {
  try {
    await stat(path);
    return true;
  } catch {
    return false;
  }
}

function toPosix(path: string): string {
  return path.split(sep).join("/");
}

function httpError(statusCode: number, message: string): Error & { statusCode: number } {
  return Object.assign(new Error(message), { statusCode });
}

function statusForError(error: unknown): number {
  if (error instanceof Error && "statusCode" in error && typeof error.statusCode === "number") {
    return error.statusCode;
  }

  return 500;
}

function messageForError(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "Unknown run API error.";
}
