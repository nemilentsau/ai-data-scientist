import {
  deriveArtifactSummaries,
  readJsonArtifact,
  type ArtifactAttemptSummary,
  type ArtifactSummary,
} from "./artifactLoop";
import type { LoadedRun } from "./types";

export type StageId =
  | "dataset"
  | "framer"
  | "select"
  | "build"
  | "execute"
  | "render"
  | "review"
  | "finalize";

export type StageOwner = "agent" | "harness" | "control";

export type StageNode = {
  id: StageId;
  label: string;
  owner: StageOwner;
  runs: number;
  detail?: string;
};

export type EdgeKind = "normal" | "branch" | "loop";

export type StageEdge = {
  id: string;
  source: StageId;
  target: StageId;
  kind: EdgeKind;
  traversed: boolean;
  count: number;
  label?: string;
};

export type PipelineGraph = {
  nodes: StageNode[];
  edges: StageEdge[];
  status: string;
};

const STAGE_META: Record<StageId, { label: string; owner: StageOwner }> = {
  dataset: { label: "Dataset", owner: "harness" },
  framer: { label: "EDA framer", owner: "agent" },
  select: { label: "Select artifact", owner: "control" },
  build: { label: "Artifact builder", owner: "agent" },
  execute: { label: "Execute query", owner: "harness" },
  render: { label: "Render chart", owner: "harness" },
  review: { label: "Visual reviewer", owner: "agent" },
  finalize: { label: "Synthesis", owner: "harness" },
};

export function reviewerVerdict(
  run: LoadedRun,
  attempt: ArtifactAttemptSummary,
): "pass" | "revise" | undefined {
  const output = readJsonArtifact(run, attempt.paths.reviewOutput);
  if (!isRecord(output)) return undefined;
  const verdict = output.verdict;
  return verdict === "pass" || verdict === "revise" ? verdict : undefined;
}

export function derivePipelineGraph(run: LoadedRun): PipelineGraph {
  const summaries = deriveArtifactSummaries(run);
  const status = run.lineage.status ?? "unknown";
  const finishedNormally = status === "passed_visual_gate";

  const datasetRuns = run.files.has("00-dataset/profile.json") ? 1 : 0;
  const framerRuns = run.files.has("01-eda-framer/output.json") ? 1 : 0;

  const buildRuns = countAttempts(summaries, (a) => has(run, a.paths.builderOutput));
  const executeRuns = countAttempts(summaries, (a) => has(run, a.paths.result));
  const renderRuns = countAttempts(summaries, (a) => has(run, a.paths.renderImage));
  const reviewRuns = countAttempts(summaries, (a) => has(run, a.paths.reviewOutput));

  let passVerdicts = 0;
  let reviseVerdicts = 0;
  for (const summary of summaries) {
    for (const attempt of summary.attempts) {
      const verdict = reviewerVerdict(run, attempt);
      if (verdict === "pass") passVerdicts += 1;
      else if (verdict === "revise") reviseVerdicts += 1;
    }
  }

  const startedArtifacts = summaries.filter((s) => s.attempts.length > 0).length;
  const passedArtifacts = summaries.filter((s) => s.status === "passed").length;
  const exhaustedArtifacts = summaries.filter(
    (s) => s.status === "revision_budget_exhausted",
  ).length;
  // Each extra attempt on an artifact was triggered by a "revise" verdict looping back to build.
  const reviseLoops = summaries.reduce((n, s) => n + Math.max(0, s.attempts.length - 1), 0);
  const selectRuns = startedArtifacts + (finishedNormally ? 1 : 0);

  const nodes: StageNode[] = [
    node("dataset", datasetRuns),
    node("framer", framerRuns),
    node("select", selectRuns),
    node("build", buildRuns),
    node("execute", executeRuns),
    node("render", renderRuns),
    node("review", reviewRuns, reviewDetail(passVerdicts, reviseVerdicts, exhaustedArtifacts)),
    node("finalize", 1, status),
  ];

  const edges: StageEdge[] = [
    edge("dataset", "framer", "normal", framerRuns > 0, framerRuns),
    edge("framer", "select", "normal", framerRuns > 0, framerRuns),
    edge("select", "build", "branch", startedArtifacts > 0, startedArtifacts, "next artifact"),
    edge("select", "finalize", "branch", finishedNormally, finishedNormally ? 1 : 0, "all passed"),
    edge("build", "execute", "normal", executeRuns > 0, executeRuns),
    edge("execute", "render", "normal", renderRuns > 0, renderRuns),
    edge("render", "review", "normal", reviewRuns > 0, reviewRuns),
    edge("review", "build", "loop", reviseLoops > 0, reviseLoops, "revise"),
    edge("review", "select", "loop", passedArtifacts > 0, passedArtifacts, "pass"),
    edge("review", "finalize", "branch", exhaustedArtifacts > 0, exhaustedArtifacts, "exhausted"),
  ];

  return { nodes, edges, status };
}

function node(id: StageId, runs: number, detail?: string): StageNode {
  const meta = STAGE_META[id];
  return {
    id,
    label: meta.label,
    owner: meta.owner,
    runs,
    ...(detail ? { detail } : {}),
  };
}

function edge(
  source: StageId,
  target: StageId,
  kind: EdgeKind,
  traversed: boolean,
  count: number,
  label?: string,
): StageEdge {
  return {
    id: `${source}->${target}`,
    source,
    target,
    kind,
    traversed,
    count,
    ...(label ? { label } : {}),
  };
}

function reviewDetail(pass: number, revise: number, exhausted: number): string {
  const parts = [`${pass} pass`, `${revise} revise`];
  if (exhausted > 0) parts.push(`${exhausted} exhausted`);
  return parts.join(" · ");
}

function countAttempts(
  summaries: ArtifactSummary[],
  predicate: (attempt: ArtifactAttemptSummary) => boolean,
): number {
  let count = 0;
  for (const summary of summaries) {
    for (const attempt of summary.attempts) {
      if (predicate(attempt)) count += 1;
    }
  }
  return count;
}

function has(run: LoadedRun, path: string | undefined): boolean {
  return path !== undefined && run.files.has(path);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
