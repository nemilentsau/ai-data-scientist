import {
  deriveArtifactSummaries,
  latestAttempt,
  readJsonArtifact,
  type ArtifactAttemptSummary,
  type ArtifactSummary,
} from "./artifactLoop";
import type { LoadedRun, RunLineage } from "./types";

export type RunSelectedView =
  | { kind: "run-framer"; path: string }
  | { kind: "run-synthesis"; path: string }
  | { kind: "run-lineage"; path: string }
  | { kind: "run-file"; path: string };

export type ArtifactSelectedView = {
  kind: ArtifactViewKind;
  path: string;
  artifact: ArtifactSummary;
  attempt: ArtifactAttemptSummary;
};

export type SelectedView = RunSelectedView | ArtifactSelectedView;

export type ArtifactViewKind =
  | "artifact-build-context"
  | "artifact-builder-output"
  | "artifact-builder-prompt"
  | "artifact-builder-schema"
  | "artifact-query"
  | "artifact-chart-spec"
  | "artifact-result"
  | "artifact-result-summary"
  | "artifact-render"
  | "artifact-review-context"
  | "artifact-review-output"
  | "artifact-review-prompt"
  | "artifact-review-image-inputs"
  | "artifact-review-schema"
  | "artifact-review-report";

const ARTIFACT_PATH_PATTERN =
  /^(02-artifact-builder|03-execution|04-render|05-visual-reviewer)\/([^/]+)\/attempt-(\d+)\/(.+)$/;

const RUN_FILE_PATHS = new Set([
  "00-dataset/dataset.csv",
  "00-dataset/profile.json",
  "01-eda-framer/prompt.md",
  "01-eda-framer/user-question.txt",
  "01-eda-framer/output.schema.json",
]);

export function resolveSelectedView(run: LoadedRun, selectedPath: string): SelectedView {
  if (!run.files.has(selectedPath)) {
    throw new Error(`Selected artifact path does not exist in run: ${selectedPath}`);
  }

  const artifacts = deriveArtifactSummaries(run);
  return resolveKnownPath(selectedPath, artifacts);
}

export function isArtifactSelectedView(view: SelectedView): view is ArtifactSelectedView {
  return view.kind.startsWith("artifact-");
}

export function validateInspectableRun(run: LoadedRun): void {
  validateLineage(run.lineage);
  const artifacts = deriveArtifactSummaries(run);

  for (const path of run.paths) {
    resolveKnownPath(path, artifacts);
  }

  for (const artifact of artifacts) {
    validateArtifactSummary(run, artifact);
  }
}

function resolveKnownPath(
  selectedPath: string,
  artifacts: ArtifactSummary[],
): SelectedView {
  if (selectedPath === "01-eda-framer/output.json") {
    return { kind: "run-framer", path: selectedPath };
  }
  if (selectedPath === "06-synthesis/report.md") {
    return { kind: "run-synthesis", path: selectedPath };
  }
  if (selectedPath === "lineage.json") {
    return { kind: "run-lineage", path: selectedPath };
  }
  if (RUN_FILE_PATHS.has(selectedPath)) {
    return { kind: "run-file", path: selectedPath };
  }

  const match = ARTIFACT_PATH_PATTERN.exec(selectedPath);
  if (!match) {
    throw new Error(
      `Unsupported selected artifact path: ${selectedPath}. Frontend schema resolver does not know how to render this run artifact.`,
    );
  }

  const [, stage, artifactId, attemptText, filename] = match;
  if (!stage || !artifactId || !attemptText || !filename) {
    throw new Error(`Unsupported selected artifact path: ${selectedPath}.`);
  }

  const artifact = artifacts.find((item) => item.id === artifactId);
  if (!artifact) {
    throw new Error(`Selected path belongs to artifact not present in artifact_plan: ${artifactId}.`);
  }

  const attemptNumber = Number(attemptText);
  const attempt = artifact.attempts.find((item) => item.number === attemptNumber);
  if (!attempt) {
    throw new Error(`Selected path belongs to unknown artifact attempt: ${selectedPath}.`);
  }

  return {
    kind: viewKindForArtifactPath(stage, filename, selectedPath),
    path: selectedPath,
    artifact,
    attempt,
  };
}

function viewKindForArtifactPath(
  stage: string,
  filename: string,
  selectedPath: string,
): ArtifactViewKind {
  if (stage === "02-artifact-builder") {
    if (filename === "build-context.json") return "artifact-build-context";
    if (filename === "output.json") return "artifact-builder-output";
    if (filename === "prompt.md") return "artifact-builder-prompt";
    if (filename === "output.schema.json") return "artifact-builder-schema";
    if (filename === "query.sql") return "artifact-query";
    if (filename === "chart.vegalite.json") return "artifact-chart-spec";
  }

  if (stage === "03-execution") {
    if (filename === "result.parquet") return "artifact-result";
    if (filename === "result.summary.json") return "artifact-result-summary";
  }

  if (stage === "04-render" && filename === "chart.png") return "artifact-render";

  if (stage === "05-visual-reviewer") {
    if (filename === "review-context.json") return "artifact-review-context";
    if (filename === "output.json") return "artifact-review-output";
    if (filename === "prompt.md") return "artifact-review-prompt";
    if (filename === "image-inputs.json") return "artifact-review-image-inputs";
    if (filename === "output.schema.json") return "artifact-review-schema";
    if (filename === "report.md") return "artifact-review-report";
  }

  throw new Error(
    `Unsupported selected artifact path: ${selectedPath}. Frontend schema resolver does not know how to render this run artifact.`,
  );
}

function validateLineage(lineage: RunLineage): void {
  if (typeof lineage.status !== "string") {
    throw new Error("lineage.json must contain string field: status.");
  }
  if (!isRecord(lineage.artifact_statuses)) {
    throw new Error("lineage.json must contain artifact_statuses.");
  }
  if (!isRecord(lineage.dependencies)) {
    throw new Error("lineage.json must contain dependencies.");
  }
}

function validateArtifactSummary(run: LoadedRun, artifact: ArtifactSummary): void {
  for (const attempt of artifact.attempts) {
    validateBuilderOutput(run, artifact, attempt);
    validateReviewerOutput(run, artifact, attempt);
  }

  if (artifact.status === "passed") {
    const attempt = latestAttempt(artifact);
    if (!attempt) {
      throw new Error(`Passed artifact has no attempts: ${artifact.id}.`);
    }
    const requiredPaths = [
      attempt.paths.builderOutput,
      attempt.paths.query,
      attempt.paths.chartSpec,
      attempt.paths.result,
      attempt.paths.resultSummary,
      attempt.paths.renderImage,
      attempt.paths.reviewContext,
      attempt.paths.reviewOutput,
      attempt.paths.report,
    ];
    if (requiredPaths.some((path) => path === undefined)) {
      throw new Error(`Passed artifact is missing required renderable outputs: ${artifact.id}.`);
    }
  }
}

function validateBuilderOutput(
  run: LoadedRun,
  artifact: ArtifactSummary,
  attempt: ArtifactAttemptSummary,
): void {
  if (!attempt.paths.builderOutput) return;

  const output = readJsonArtifact(run, attempt.paths.builderOutput);
  if (!isRecord(output)) {
    throw new Error(`${attempt.paths.builderOutput} must contain a JSON object.`);
  }

  const artifactId = requiredString(output, "artifact_id", attempt.paths.builderOutput);
  if (artifactId !== artifact.id) {
    throw new Error(`${attempt.paths.builderOutput} artifact_id does not match artifact_plan.`);
  }
  requiredString(output, "sql", attempt.paths.builderOutput);
  const chartSpec = output.chart_spec;
  if (typeof chartSpec !== "string" && !isRecord(chartSpec)) {
    throw new Error(`${attempt.paths.builderOutput} is missing required chart_spec.`);
  }
}

function validateReviewerOutput(
  run: LoadedRun,
  artifact: ArtifactSummary,
  attempt: ArtifactAttemptSummary,
): void {
  if (!attempt.paths.reviewOutput) return;

  const output = readJsonArtifact(run, attempt.paths.reviewOutput);
  if (!isRecord(output)) {
    throw new Error(`${attempt.paths.reviewOutput} must contain a JSON object.`);
  }

  const artifactId = requiredString(output, "artifact_id", attempt.paths.reviewOutput);
  if (artifactId !== artifact.id) {
    throw new Error(`${attempt.paths.reviewOutput} artifact_id does not match artifact_plan.`);
  }

  const verdict = requiredString(output, "verdict", attempt.paths.reviewOutput);
  if (verdict !== "pass" && verdict !== "revise") {
    throw new Error(`${attempt.paths.reviewOutput} verdict must be pass or revise.`);
  }

  requiredStringArray(output, "visual_adequacy", attempt.paths.reviewOutput);
  requiredStringArray(output, "statistical_findings", attempt.paths.reviewOutput);
  requiredStringArray(output, "limitations", attempt.paths.reviewOutput);
  requiredStringArray(output, "carry_forward_notes", attempt.paths.reviewOutput);
  requiredString(output, "required_revision", attempt.paths.reviewOutput);
  requiredString(output, "report_markdown", attempt.paths.reviewOutput);
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

function requiredStringArray(
  record: Record<string, unknown>,
  key: string,
  source: string,
): string[] {
  const value = record[key];
  if (!Array.isArray(value)) {
    throw new Error(`${source} is missing required array field: ${key}.`);
  }
  return value.map((item, index) => {
    if (typeof item !== "string") {
      throw new Error(`${source}.${key}[${index}] must be a string.`);
    }
    return item;
  });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
