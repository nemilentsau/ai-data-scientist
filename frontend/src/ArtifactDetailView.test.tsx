import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ArtifactDetailView } from "./ArtifactDetailView";
import type { ArtifactSummary } from "./artifactLoop";
import type { LoadedRun, RunArtifact } from "./types";

const base = "target_distribution_histogram";
const renderPath = `04-render/${base}/attempt-1/chart.png`;
const reviewPath = `05-visual-reviewer/${base}/attempt-1/output.json`;
const queryPath = `02-artifact-builder/${base}/attempt-1/query.sql`;
const summaryPath = `03-execution/${base}/attempt-1/result.summary.json`;

const reviewOutput = JSON.stringify({
  artifact_id: base,
  verdict: "pass",
  visual_adequacy: ["The x-axis is labeled Monthly rent."],
  statistical_findings: ["The distribution is right-skewed."],
  carry_forward_notes: ["Use the planned boxplot for outliers."],
  limitations: ["Modality is not definitive from this histogram."],
  required_revision: "",
  report_markdown: "Supported observations: the chart is readable.",
});

const resultSummary = JSON.stringify({
  row_count: 19,
  columns: ["rent_bin", "listing_count"],
  preview_rows: [{ rent_bin: "$750-$1000", listing_count: 262 }],
});

function file(path: string, body: string): [string, RunArtifact] {
  return [path, { kind: "text", path, size: body.length, text: body }];
}

const run: LoadedRun = {
  rootName: "target-distribution-modeling",
  lineage: {},
  paths: [renderPath, reviewPath, queryPath, summaryPath],
  files: new Map<string, RunArtifact>([
    [renderPath, { kind: "image", path: renderPath, size: 2048, url: "/chart.png" }],
    file(reviewPath, reviewOutput),
    file(queryPath, "SELECT monthly_rent_usd FROM dataset"),
    file(summaryPath, resultSummary),
  ]),
};

const summary: ArtifactSummary = {
  id: base,
  status: "passed",
  plan: {
    id: base,
    purpose: "Show the overall frequency distribution.",
    statistical_check: "Compact fixed-bin histogram.",
    artifact_type: "chart",
    expected_chart_family: "histogram",
    required_fields: ["monthly_rent_usd"],
    interpretation_limits: ["Bin-level conclusions depend on bin width."],
  },
  attempts: [
    {
      number: 1,
      paths: {
        renderImage: renderPath,
        reviewOutput: reviewPath,
        query: queryPath,
        resultSummary: summaryPath,
      },
    },
  ],
};

describe("ArtifactDetailView", () => {
  it("shows the chart, reviewer verdict and findings, the plan, and evidence", () => {
    const html = renderToStaticMarkup(
      <ArtifactDetailView run={run} summary={summary} onSelectFile={() => {}} />,
    );

    expect(html).toContain("Target distribution histogram");
    expect(html).toContain('src="/chart.png"');
    expect(html).toContain("Supported observations: the chart is readable.");
    expect(html).toContain("The distribution is right-skewed.");
    expect(html).toContain("Use the planned boxplot for outliers.");
    expect(html).toContain("Compact fixed-bin histogram.");
    expect(html).toContain("SELECT monthly_rent_usd FROM dataset");
    expect(html).toContain("262");
  });
});
