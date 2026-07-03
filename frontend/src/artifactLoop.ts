import type { LoadedRun, TextArtifact } from "./types";

export type ArtifactPlanItem = {
  id: string;
  purpose: string;
  statistical_check: string;
  artifact_type: "chart";
  expected_chart_family: string;
  required_fields: string[];
  interpretation_limits: string[];
};

export type FramerOutput = {
  user_question: string;
  analysis_goal: string;
  artifact_plan: ArtifactPlanItem[];
  stop_conditions: string[];
};

export type ArtifactAttemptPaths = {
  buildContext?: string;
  builderPrompt?: string;
  builderOutput?: string;
  query?: string;
  chartSpec?: string;
  result?: string;
  resultSummary?: string;
  renderImage?: string;
  reviewContext?: string;
  reviewPrompt?: string;
  imageInputs?: string;
  reviewOutput?: string;
  report?: string;
};

export type ArtifactAttemptSummary = {
  number: number;
  paths: ArtifactAttemptPaths;
};

export type ArtifactSummary = {
  id: string;
  status: string;
  plan?: ArtifactPlanItem;
  attempts: ArtifactAttemptSummary[];
};

const ARTIFACT_STAGE_PATTERN =
  /^(02-artifact-builder|03-execution|04-render|05-visual-reviewer)\/([^/]+)\/attempt-(\d+)\/(.+)$/;

export function deriveArtifactSummaries(run: LoadedRun): ArtifactSummary[] {
  const plan = readFramerOutput(run).artifact_plan;
  const statuses = artifactStatuses(run);
  validateArtifactIdSets(run, plan, statuses);

  return plan.map((planItem) => {
    const status = statuses[planItem.id];
    if (typeof status !== "string") {
      throw new Error(`lineage.json artifact_statuses is missing planned artifact: ${planItem.id}.`);
    }
    return {
      id: planItem.id,
      status,
      plan: planItem,
      attempts: deriveAttemptsForArtifact(run, planItem.id),
    };
  });
}

export function latestAttempt(
  summary: ArtifactSummary,
): ArtifactAttemptSummary | undefined {
  return summary.attempts.at(-1);
}

export function importantPathsForRun(run: LoadedRun): string[] {
  const preferred = [
    "01-eda-framer/output.json",
    ...deriveArtifactSummaries(run).flatMap((summary) => {
      const attempt = latestAttempt(summary);
      if (!attempt) return [];
      return [
        attempt.paths.renderImage,
        attempt.paths.reviewContext,
        attempt.paths.reviewOutput,
        attempt.paths.report,
      ];
    }),
    "06-synthesis/report.md",
    "lineage.json",
  ];

  return uniqueStrings(preferred.filter((path): path is string => Boolean(path))).filter(
    (path) => run.files.has(path),
  );
}

export function artifactIdForPath(path: string): string | null {
  return ARTIFACT_STAGE_PATTERN.exec(path)?.[2] ?? null;
}

export function readJsonArtifact(run: LoadedRun, path: string | undefined): unknown {
  if (!path) return undefined;
  const artifact = run.files.get(path);
  if (artifact?.kind !== "text") return undefined;

  try {
    return JSON.parse(artifact.text) as unknown;
  } catch {
    return undefined;
  }
}

export function textArtifact(run: LoadedRun, path: string | undefined): TextArtifact | undefined {
  if (!path) return undefined;
  const artifact = run.files.get(path);
  return artifact?.kind === "text" ? artifact : undefined;
}

export function readFramerOutput(run: LoadedRun): FramerOutput {
  const value = readJsonArtifact(run, "01-eda-framer/output.json");
  if (!isRecord(value)) {
    throw new Error("01-eda-framer/output.json must contain a JSON object.");
  }

  return {
    user_question: requiredString(value, "user_question", "01-eda-framer/output.json"),
    analysis_goal: requiredString(value, "analysis_goal", "01-eda-framer/output.json"),
    artifact_plan: requiredArray(value, "artifact_plan", "01-eda-framer/output.json").map(
      parseArtifactPlanItem,
    ),
    stop_conditions: requiredStringArray(
      value,
      "stop_conditions",
      "01-eda-framer/output.json",
    ),
  };
}

function artifactStatuses(run: LoadedRun): Record<string, string> {
  const statuses = run.lineage.artifact_statuses;
  if (!isRecord(statuses)) {
    throw new Error("lineage.json must contain artifact_statuses.");
  }

  return Object.fromEntries(
    Object.entries(statuses).flatMap(([id, status]) =>
      typeof status === "string" ? [[id, status]] : [],
    ),
  );
}

function validateArtifactIdSets(
  run: LoadedRun,
  plan: ArtifactPlanItem[],
  statuses: Record<string, string>,
): void {
  const planIds = new Set(plan.map((item) => item.id));
  const statusIds = Object.keys(statuses);
  const pathIds = uniqueStrings(
    run.paths.flatMap((path) => {
      const artifactId = artifactIdForPath(path);
      return artifactId ? [artifactId] : [];
    }),
  );

  for (const artifactId of statusIds) {
    if (!planIds.has(artifactId)) {
      throw new Error(`lineage.json contains artifact_statuses for unknown artifact: ${artifactId}.`);
    }
  }

  for (const artifactId of pathIds) {
    if (!planIds.has(artifactId)) {
      throw new Error(`Run contains files for artifact not present in artifact_plan: ${artifactId}.`);
    }
  }

  for (const artifactId of planIds) {
    if (!(artifactId in statuses)) {
      throw new Error(`lineage.json artifact_statuses is missing planned artifact: ${artifactId}.`);
    }
  }
}

function deriveAttemptsForArtifact(
  run: LoadedRun,
  artifactId: string,
): ArtifactAttemptSummary[] {
  const attempts = new Map<number, ArtifactAttemptPaths>();

  for (const path of run.paths) {
    const match = ARTIFACT_STAGE_PATTERN.exec(path);
    if (!match) continue;

    const [, stage, matchedArtifactId, attemptText, filename] = match;
    if (!stage || !matchedArtifactId || !attemptText || !filename) continue;
    if (matchedArtifactId !== artifactId) continue;

    const attempt = Number(attemptText);
    const paths = attempts.get(attempt) ?? {};
    assignAttemptPath(paths, stage, filename, path);
    attempts.set(attempt, paths);
  }

  return Array.from(attempts.entries())
    .sort(([left], [right]) => left - right)
    .map(([number, paths]) => ({ number, paths }));
}

function assignAttemptPath(
  paths: ArtifactAttemptPaths,
  stage: string,
  filename: string,
  path: string,
): void {
  if (stage === "02-artifact-builder") {
    if (filename === "build-context.json") paths.buildContext = path;
    if (filename === "prompt.md") paths.builderPrompt = path;
    if (filename === "output.json") paths.builderOutput = path;
    if (filename === "query.sql") paths.query = path;
    if (filename === "chart.vegalite.json") paths.chartSpec = path;
    return;
  }

  if (stage === "03-execution") {
    if (filename === "result.parquet") paths.result = path;
    if (filename === "result.summary.json") paths.resultSummary = path;
    return;
  }

  if (stage === "04-render") {
    if (filename === "chart.png") paths.renderImage = path;
    return;
  }

  if (stage === "05-visual-reviewer") {
    if (filename === "review-context.json") paths.reviewContext = path;
    if (filename === "prompt.md") paths.reviewPrompt = path;
    if (filename === "image-inputs.json") paths.imageInputs = path;
    if (filename === "output.json") paths.reviewOutput = path;
    if (filename === "report.md") paths.report = path;
  }
}

function uniqueStrings(values: string[]): string[] {
  return Array.from(new Set(values));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseArtifactPlanItem(value: unknown, index: number): ArtifactPlanItem {
  const source = `01-eda-framer/output.json artifact_plan[${index}]`;
  if (!isRecord(value)) {
    throw new Error(`${source} must be a JSON object.`);
  }

  const artifactType = requiredString(value, "artifact_type", source);
  if (artifactType !== "chart") {
    throw new Error(`${source}.artifact_type must be "chart".`);
  }

  return {
    id: requiredString(value, "id", source),
    purpose: requiredString(value, "purpose", source),
    statistical_check: requiredString(value, "statistical_check", source),
    artifact_type: artifactType,
    expected_chart_family: requiredString(value, "expected_chart_family", source),
    required_fields: requiredStringArray(value, "required_fields", source),
    interpretation_limits: requiredStringArray(value, "interpretation_limits", source),
  };
}

function requiredString(
  record: Record<string, unknown>,
  key: string,
  source: string,
): string {
  const value = record[key];
  if (typeof value !== "string") {
    throw new Error(`${source} is missing required string field: ${key}.`);
  }
  return value;
}

function requiredArray(
  record: Record<string, unknown>,
  key: string,
  source: string,
): unknown[] {
  const value = record[key];
  if (!Array.isArray(value)) {
    throw new Error(`${source} is missing required array field: ${key}.`);
  }
  return value;
}

function requiredStringArray(
  record: Record<string, unknown>,
  key: string,
  source: string,
): string[] {
  return requiredArray(record, key, source).map((item, index) => {
    if (typeof item !== "string") {
      throw new Error(`${source}.${key}[${index}] must be a string.`);
    }
    return item;
  });
}
