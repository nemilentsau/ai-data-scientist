import type { LoadedRun, RunArtifact, RunLineage } from "./types";

// Shared test fixture builder for runs. Not imported by app code.
export type FixtureAttempt = { verdict?: "pass" | "revise"; partial?: boolean };

export type FixtureArtifact = {
  id: string;
  status: string;
  purpose?: string;
  chartFamily?: string;
  attempts: FixtureAttempt[];
};

export function makeRun(opts: {
  artifacts: FixtureArtifact[];
  status?: string;
  synthesis?: boolean;
}): LoadedRun {
  const files = new Map<string, RunArtifact>();
  const text = (path: string, body: string): void => {
    files.set(path, { kind: "text", path, size: body.length, text: body });
  };
  const image = (path: string): void => {
    files.set(path, { kind: "image", path, size: 1, url: `/${path}` });
  };
  const binary = (path: string): void => {
    files.set(path, { kind: "binary", path, size: 1 });
  };

  text("00-dataset/dataset.csv", "a,b\n1,2\n");
  text("00-dataset/profile.json", "{}");

  const plan = opts.artifacts.map((artifact) => ({
    artifact_type: "chart",
    id: artifact.id,
    purpose: artifact.purpose ?? `Purpose for ${artifact.id}`,
    statistical_check: "check",
    expected_chart_family: artifact.chartFamily ?? "histogram",
    required_fields: ["x"],
    interpretation_limits: [],
  }));
  text("01-eda-framer/prompt.md", "p");
  text("01-eda-framer/user-question.txt", "q");
  text("01-eda-framer/output.schema.json", "{}");
  text(
    "01-eda-framer/output.json",
    JSON.stringify({
      user_question: "Analyze the target.",
      analysis_goal: "Characterize the target.",
      artifact_plan: plan,
      stop_conditions: [],
    }),
  );

  for (const artifact of opts.artifacts) {
    artifact.attempts.forEach((attempt, index) => {
      const n = index + 1;
      const builder = `02-artifact-builder/${artifact.id}/attempt-${n}`;
      const execution = `03-execution/${artifact.id}/attempt-${n}`;
      const render = `04-render/${artifact.id}/attempt-${n}`;
      const reviewer = `05-visual-reviewer/${artifact.id}/attempt-${n}`;

      text(`${builder}/build-context.json`, "{}");
      text(`${builder}/prompt.md`, "p");
      text(`${builder}/output.schema.json`, "{}");
      text(
        `${builder}/output.json`,
        JSON.stringify({ artifact_id: artifact.id, sql: "SELECT 1", chart_spec: {} }),
      );
      text(`${builder}/query.sql`, "SELECT 1");
      text(`${builder}/chart.vegalite.json`, "{}");

      if (attempt.partial) return;

      binary(`${execution}/result.parquet`);
      text(
        `${execution}/result.summary.json`,
        JSON.stringify({ row_count: 1, columns: ["x"], preview_rows: [{ x: 1 }] }),
      );
      image(`${render}/chart.png`);
      text(`${reviewer}/review-context.json`, "{}");
      text(`${reviewer}/prompt.md`, "p");
      text(`${reviewer}/image-inputs.json`, "{}");
      text(`${reviewer}/output.schema.json`, "{}");
      text(
        `${reviewer}/output.json`,
        JSON.stringify({
          artifact_id: artifact.id,
          verdict: attempt.verdict ?? "pass",
          visual_adequacy: [],
          statistical_findings: [],
          limitations: [],
          carry_forward_notes: [],
          required_revision: attempt.verdict === "revise" ? "fix it" : "",
          report_markdown: "report body",
        }),
      );
      text(`${reviewer}/report.md`, "report body");
    });
  }

  if (opts.synthesis ?? true) {
    text("06-synthesis/report.md", "# Summary\n\nThe target is right-skewed.");
  }

  const artifactStatuses: Record<string, string> = {};
  for (const artifact of opts.artifacts) artifactStatuses[artifact.id] = artifact.status;

  const lineage: RunLineage = {
    status: opts.status ?? "passed_visual_gate",
    artifact_statuses: artifactStatuses,
    dependencies: {},
  };

  return { rootName: "fixture", files, lineage, paths: Array.from(files.keys()) };
}
