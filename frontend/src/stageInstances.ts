import { deriveArtifactSummaries, type ArtifactAttemptPaths } from "./artifactLoop";
import { humanizeId } from "./format";
import { reviewerVerdict, type StageId } from "./pipelineGraph";
import type { LoadedRun } from "./types";

export type StageInstance = {
  key: string;
  label: string;
  paths: string[];
  artifactId?: string;
  attempt?: number;
  status?: string;
  verdict?: string;
};

const ATTEMPT_STAGE_KEYS: Partial<Record<StageId, Array<keyof ArtifactAttemptPaths>>> = {
  build: ["buildContext", "builderPrompt", "builderOutput", "query", "chartSpec"],
  execute: ["result", "resultSummary"],
  render: ["renderImage"],
  review: ["reviewContext", "reviewPrompt", "imageInputs", "reviewOutput", "report"],
};

export function stageInstances(run: LoadedRun, stage: StageId): StageInstance[] {
  if (stage === "dataset") {
    return [
      {
        key: "dataset",
        label: "Dataset & profile",
        paths: present(run, ["00-dataset/dataset.csv", "00-dataset/profile.json"]),
      },
    ];
  }

  if (stage === "framer") {
    return [
      {
        key: "framer",
        label: "EDA framer",
        paths: present(run, [
          "01-eda-framer/output.json",
          "01-eda-framer/prompt.md",
          "01-eda-framer/user-question.txt",
          "01-eda-framer/output.schema.json",
        ]),
      },
    ];
  }

  if (stage === "finalize") {
    return [
      {
        key: "finalize",
        label: "Synthesis & lineage",
        paths: present(run, ["06-synthesis/report.md", "lineage.json"]),
      },
    ];
  }

  const summaries = deriveArtifactSummaries(run);

  if (stage === "select") {
    return summaries.map((summary) => ({
      key: summary.id,
      label: humanizeId(summary.id),
      paths: [],
      artifactId: summary.id,
      status: summary.status,
    }));
  }

  const keys = ATTEMPT_STAGE_KEYS[stage] ?? [];
  return summaries.flatMap((summary) =>
    summary.attempts.map((attempt) => {
      const paths = present(
        run,
        keys.map((key) => attempt.paths[key]).filter((path): path is string => Boolean(path)),
      );
      const verdict = stage === "review" ? reviewerVerdict(run, attempt) : undefined;
      return {
        key: `${summary.id}#${attempt.number}`,
        label: `${humanizeId(summary.id)} · attempt ${attempt.number}`,
        paths,
        artifactId: summary.id,
        attempt: attempt.number,
        status: summary.status,
        ...(verdict ? { verdict } : {}),
      } satisfies StageInstance;
    }),
  );
}

function present(run: LoadedRun, paths: string[]): string[] {
  return paths.filter((path) => run.files.has(path));
}
