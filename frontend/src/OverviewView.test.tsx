import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ChartGallery } from "./ChartGallery";
import { OverviewView } from "./OverviewView";
import { toGalleryItems } from "./overview";
import type { ArtifactSummary } from "./artifactLoop";
import type { GalleryItem } from "./overview";
import type { LoadedRun, RunArtifact } from "./types";

const items: GalleryItem[] = [
  {
    artifactId: "target_distribution_histogram",
    title: "Target distribution histogram",
    status: "passed",
    purpose: "Show the overall frequency distribution.",
    chartFamily: "histogram",
    imageUrl: "/hist.png",
  },
  {
    artifactId: "target_outlier_boxplot",
    title: "Target outlier boxplot",
    status: "revise",
    purpose: "Summarize quartiles and outliers.",
    chartFamily: "boxplot",
  },
];

describe("toGalleryItems", () => {
  it("humanizes ids and resolves the rendered chart image url", () => {
    const renderPath = "04-render/target_distribution_histogram/attempt-1/chart.png";
    const image: RunArtifact = { kind: "image", path: renderPath, size: 1, url: "/hist.png" };
    const run = {
      rootName: "r",
      paths: [renderPath],
      lineage: {},
      files: new Map([[renderPath, image]]),
    } satisfies LoadedRun;

    const summaries: ArtifactSummary[] = [
      {
        id: "target_distribution_histogram",
        status: "passed",
        plan: {
          id: "target_distribution_histogram",
          purpose: "Show the overall frequency distribution.",
          statistical_check: "histogram",
          artifact_type: "chart",
          expected_chart_family: "histogram",
          required_fields: ["monthly_rent_usd"],
          interpretation_limits: [],
        },
        attempts: [{ number: 1, paths: { renderImage: renderPath } }],
      },
    ];

    expect(toGalleryItems(run, summaries)).toEqual([
      {
        artifactId: "target_distribution_histogram",
        title: "Target distribution histogram",
        status: "passed",
        purpose: "Show the overall frequency distribution.",
        chartFamily: "histogram",
        imageUrl: "/hist.png",
      },
    ]);
  });
});

describe("ChartGallery", () => {
  it("renders one figure per artifact with title, purpose, and chart image", () => {
    const html = renderToStaticMarkup(<ChartGallery items={items} onSelect={() => {}} />);

    expect(html.match(/<figure/g)?.length).toBe(2);
    expect(html).toContain("Target distribution histogram");
    expect(html).toContain("Show the overall frequency distribution.");
    expect(html).toContain('src="/hist.png"');
    expect(html).toContain("No rendered chart");
  });
});

describe("OverviewView", () => {
  it("leads with the question, goal, status, and renders the summary report", () => {
    const html = renderToStaticMarkup(
      <OverviewView
        question="Analyze the monthly_rent_usd target distribution."
        goal="Determine whether the target is well-behaved for modeling."
        status="passed_visual_gate"
        datasetName="multimodal"
        artifactCount={4}
        agentRunCount={9}
        items={items}
        synthesisMarkdown={"# EDA Artifact Review Summary\n\nThe target is right-skewed."}
        onSelectArtifact={() => {}}
      />,
    );

    expect(html).toContain("Analyze the monthly_rent_usd target distribution.");
    expect(html).toContain("Determine whether the target is well-behaved");
    expect(html).toContain("passed_visual_gate");
    expect(html).toContain("EDA Artifact Review Summary");
    expect(html).toContain("Target distribution histogram");
    expect(html).toContain("multimodal");
  });
});
