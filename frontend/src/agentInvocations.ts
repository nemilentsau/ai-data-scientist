import { deriveArtifactSummaries, type ArtifactAttemptSummary } from "./artifactLoop";
import type { LoadedRun } from "./types";

export type AgentRole = "eda_framer" | "artifact_builder" | "visual_reviewer";

export type AgentInvocation = {
  id: string;
  role: AgentRole;
  label: string;
  artifactId?: string;
  attempt?: number;
  inputPaths: string[];
  outputPaths: string[];
};

export function deriveAgentInvocations(run: LoadedRun): AgentInvocation[] {
  return [
    {
      id: "eda_framer",
      role: "eda_framer",
      label: "EDA framer",
      inputPaths: existingPaths(run, [
        "01-eda-framer/prompt.md",
        "01-eda-framer/user-question.txt",
        "01-eda-framer/output.schema.json",
        "00-dataset/profile.json",
      ]),
      outputPaths: existingPaths(run, ["01-eda-framer/output.json"]),
    },
    ...deriveArtifactSummaries(run).flatMap((artifact) =>
      artifact.attempts.flatMap((attempt) => [
        builderInvocation(run, artifact.id, attempt),
        reviewerInvocation(run, artifact.id, attempt),
      ]),
    ),
  ];
}

function builderInvocation(
  run: LoadedRun,
  artifactId: string,
  attempt: ArtifactAttemptSummary,
): AgentInvocation {
  return {
    id: `artifact_builder/${artifactId}/attempt-${attempt.number}`,
    role: "artifact_builder",
    label: "Artifact builder",
    artifactId,
    attempt: attempt.number,
    inputPaths: existingPaths(run, [
      attempt.paths.builderPrompt,
      attempt.paths.buildContext,
      attempt.paths.builderOutput ? outputSchemaPath(attempt.paths.builderOutput) : undefined,
    ]),
    outputPaths: existingPaths(run, [
      attempt.paths.builderOutput,
      attempt.paths.query,
      attempt.paths.chartSpec,
    ]),
  };
}

function reviewerInvocation(
  run: LoadedRun,
  artifactId: string,
  attempt: ArtifactAttemptSummary,
): AgentInvocation {
  return {
    id: `visual_reviewer/${artifactId}/attempt-${attempt.number}`,
    role: "visual_reviewer",
    label: "Visual reviewer",
    artifactId,
    attempt: attempt.number,
    inputPaths: existingPaths(run, [
      attempt.paths.reviewPrompt,
      attempt.paths.reviewContext,
      attempt.paths.imageInputs,
      attempt.paths.reviewOutput ? outputSchemaPath(attempt.paths.reviewOutput) : undefined,
      attempt.paths.renderImage,
    ]),
    outputPaths: existingPaths(run, [attempt.paths.reviewOutput, attempt.paths.report]),
  };
}

function outputSchemaPath(outputPath: string): string {
  return outputPath.replace(/output\.json$/, "output.schema.json");
}

function existingPaths(run: LoadedRun, paths: Array<string | undefined>): string[] {
  return paths.filter((path): path is string => {
    if (!path) return false;
    return run.files.has(path);
  });
}
