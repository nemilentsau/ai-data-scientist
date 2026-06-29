import type { ReactNode } from "react";

import {
  latestAttempt,
  readJsonArtifact,
  textArtifact,
  type ArtifactSummary,
} from "./artifactLoop";
import { FileContent } from "./FileContent";
import { humanizeId } from "./format";
import { fileChipLabel, formatBytes } from "./runFolder";
import type { LoadedRun, RunArtifact } from "./types";
import {
  CodeBlock,
  Collapsible,
  DefinitionList,
  EmptyNote,
  Eyebrow,
  SectionTitle,
  StatusChip,
} from "./ui";
import { Markdown } from "./Markdown";

const RAW_FILE_KEYS = [
  "buildContext",
  "builderPrompt",
  "builderOutput",
  "query",
  "chartSpec",
  "result",
  "resultSummary",
  "renderImage",
  "reviewContext",
  "reviewPrompt",
  "imageInputs",
  "reviewOutput",
  "report",
] as const;

export function ArtifactDetailView({
  run,
  summary,
  onSelectFile,
}: {
  run: LoadedRun;
  summary: ArtifactSummary;
  onSelectFile: (path: string) => void;
}) {
  const attempt = latestAttempt(summary);
  const plan = summary.plan;
  const chart = imageArtifact(run, attempt?.paths.renderImage);
  const review = readReviewerDecision(run, attempt?.paths.reviewOutput);
  const query = textArtifact(run, attempt?.paths.query);
  const resultSummaryPath = attempt?.paths.resultSummary;
  const resultSummary = resultSummaryPath ? run.files.get(resultSummaryPath) : undefined;
  const attemptCount = summary.attempts.length;

  return (
    <div className="mx-auto max-w-4xl space-y-10 px-8 py-10">
      <header className="space-y-3">
        <Eyebrow>
          {plan?.expected_chart_family ?? "chart"}
          {attempt ? ` · attempt ${attempt.number}${attemptCount > 1 ? ` of ${attemptCount}` : ""}` : ""}
        </Eyebrow>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-950">
            {humanizeId(summary.id)}
          </h1>
          <StatusChip status={summary.status} />
        </div>
        {plan?.purpose ? (
          <p className="max-w-3xl text-base leading-7 text-zinc-600">{plan.purpose}</p>
        ) : null}
      </header>

      {chart ? (
        <figure className="space-y-2">
          <img
            src={chart.url}
            alt={summary.id}
            className="max-h-[58vh] w-full rounded-lg border border-zinc-200 bg-white object-contain p-3"
          />
          <figcaption className="font-mono text-xs text-zinc-400">
            {attempt?.paths.renderImage} · {formatBytes(chart.size)}
          </figcaption>
        </figure>
      ) : (
        <EmptyNote>No rendered chart image was found for this artifact attempt.</EmptyNote>
      )}

      <section className="space-y-5">
        <div className="flex flex-wrap items-center gap-3">
          <SectionTitle>Reviewer decision</SectionTitle>
          {review ? <StatusChip status={review.verdict} /> : null}
        </div>

        {review ? (
          <>
            {review.reportMarkdown ? <Markdown text={review.reportMarkdown} /> : null}
            <div className="grid gap-x-10 gap-y-6 sm:grid-cols-2">
              <FindingList title="Visual adequacy" items={review.visualAdequacy} />
              <FindingList title="Statistical findings" items={review.statisticalFindings} />
              <FindingList title="Carry-forward limits" items={review.carryForward} />
              <FindingList title="Limitations" items={review.limitations} />
            </div>
            <div className="space-y-1.5">
              <FindingTitle>Required revision</FindingTitle>
              <p className="text-sm leading-6 text-zinc-700">
                {review.requiredRevision.length > 0 ? review.requiredRevision : "None."}
              </p>
            </div>
          </>
        ) : (
          <EmptyNote>No reviewer output was recorded for this attempt.</EmptyNote>
        )}
      </section>

      <section className="space-y-4">
        <SectionTitle>Artifact request</SectionTitle>
        <DefinitionList
          items={[
            { term: "Statistical check", value: plan?.statistical_check ?? "Not recorded." },
            { term: "Expected chart", value: plan?.expected_chart_family ?? "Not recorded." },
            {
              term: "Required fields",
              value: plan && plan.required_fields.length > 0 ? plan.required_fields.join(", ") : "Not recorded.",
            },
            {
              term: "Interpretation limits",
              value:
                plan && plan.interpretation_limits.length > 0 ? (
                  <ul className="list-disc space-y-1 pl-5 marker:text-zinc-400">
                    {plan.interpretation_limits.map((limit) => (
                      <li key={limit}>{limit}</li>
                    ))}
                  </ul>
                ) : (
                  "Not recorded."
                ),
            },
          ]}
        />
      </section>

      <Collapsible summary="Evidence — query, result, and raw files">
        {query ? (
          <div className="space-y-2">
            <FindingTitle>Builder query</FindingTitle>
            <CodeBlock text={query.text} language="sql" />
          </div>
        ) : null}

        {resultSummary && resultSummaryPath ? (
          <div className="space-y-2">
            <FindingTitle>Query result</FindingTitle>
            <FileContent artifact={resultSummary} path={resultSummaryPath} />
          </div>
        ) : null}

        <div className="space-y-2">
          <FindingTitle>Raw files</FindingTitle>
          <ul className="flex flex-wrap gap-2">
            {rawFilePaths(run, summary).map((path) => (
              <li key={path}>
                <button
                  type="button"
                  onClick={() => onSelectFile(path)}
                  className="rounded border border-zinc-200 px-2.5 py-1 font-mono text-xs text-zinc-600 transition hover:border-teal-300 hover:text-teal-800"
                  title={path}
                >
                  {fileChipLabel(path)}
                </button>
              </li>
            ))}
          </ul>
        </div>
      </Collapsible>
    </div>
  );
}

type ReviewerDecision = {
  verdict: string;
  visualAdequacy: string[];
  statisticalFindings: string[];
  carryForward: string[];
  limitations: string[];
  requiredRevision: string;
  reportMarkdown: string;
};

function readReviewerDecision(
  run: LoadedRun,
  reviewOutputPath: string | undefined,
): ReviewerDecision | undefined {
  const value = readJsonArtifact(run, reviewOutputPath);
  if (!isRecord(value)) return undefined;

  return {
    verdict: stringField(value, "verdict") ?? "unknown",
    visualAdequacy: stringArrayField(value, "visual_adequacy"),
    statisticalFindings: stringArrayField(value, "statistical_findings"),
    carryForward: stringArrayField(value, "carry_forward_notes"),
    limitations: stringArrayField(value, "limitations"),
    requiredRevision: stringField(value, "required_revision") ?? "",
    reportMarkdown: stringField(value, "report_markdown") ?? "",
  };
}

function rawFilePaths(run: LoadedRun, summary: ArtifactSummary): string[] {
  const paths: string[] = [];
  for (const attempt of summary.attempts) {
    for (const key of RAW_FILE_KEYS) {
      const path = attempt.paths[key];
      if (path && run.files.has(path)) paths.push(path);
    }
  }
  return paths;
}

function imageArtifact(run: LoadedRun, path: string | undefined): Extract<RunArtifact, { kind: "image" }> | undefined {
  if (!path) return undefined;
  const artifact = run.files.get(path);
  return artifact?.kind === "image" ? artifact : undefined;
}

function FindingTitle({ children }: { children: ReactNode }) {
  return (
    <h4 className="font-mono text-[11px] uppercase tracking-[0.14em] text-zinc-400">{children}</h4>
  );
}

function FindingList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="space-y-2">
      <FindingTitle>{title}</FindingTitle>
      {items.length > 0 ? (
        <ul className="space-y-2 text-sm leading-6 text-zinc-700">
          {items.map((item) => (
            <li key={item} className="border-l-2 border-zinc-200 pl-3">
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-zinc-400">None recorded.</p>
      )}
    </div>
  );
}

function stringField(record: Record<string, unknown>, key: string): string | undefined {
  const value = record[key];
  return typeof value === "string" ? value : undefined;
}

function stringArrayField(record: Record<string, unknown>, key: string): string[] {
  const value = record[key];
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
