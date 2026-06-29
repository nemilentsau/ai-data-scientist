import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PipelineView } from "./PipelineView";
import type { AgentInvocation } from "./agentInvocations";

const invocations: AgentInvocation[] = [
  {
    id: "eda_framer",
    role: "eda_framer",
    label: "EDA framer",
    inputPaths: ["01-eda-framer/prompt.md"],
    outputPaths: ["01-eda-framer/output.json"],
  },
  {
    id: "artifact_builder/distribution_histogram/attempt-1",
    role: "artifact_builder",
    label: "Artifact builder",
    artifactId: "distribution_histogram",
    attempt: 1,
    inputPaths: ["02-artifact-builder/distribution_histogram/attempt-1/build-context.json"],
    outputPaths: ["02-artifact-builder/distribution_histogram/attempt-1/query.sql"],
  },
  {
    id: "visual_reviewer/distribution_histogram/attempt-1",
    role: "visual_reviewer",
    label: "Visual reviewer",
    artifactId: "distribution_histogram",
    attempt: 1,
    inputPaths: ["05-visual-reviewer/distribution_histogram/attempt-1/review-context.json"],
    outputPaths: ["05-visual-reviewer/distribution_histogram/attempt-1/report.md"],
  },
];

describe("PipelineView", () => {
  it("renders the ordered agent runs with roles, attempts, and file links", () => {
    const html = renderToStaticMarkup(
      <PipelineView invocations={invocations} selectedPath={null} onSelectPath={() => {}} />,
    );

    expect(html).toContain("EDA framer");
    expect(html).toContain("Artifact builder");
    expect(html).toContain("Visual reviewer");
    expect(html).toContain("Distribution histogram");
    expect(html).toContain("attempt 1");
    expect(html).toContain("01-eda-framer/prompt.md");
    expect(html).toContain("builder context");
    expect(html.match(/<li/g)?.length).toBeGreaterThanOrEqual(3);
  });
});
