import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { AgentInvocationList } from "./AgentInvocationList";
import type { AgentInvocation } from "./agentInvocations";

describe("AgentInvocationList", () => {
  it("renders visible agent roles, artifacts, attempts, inputs, and outputs", () => {
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
        outputPaths: ["02-artifact-builder/distribution_histogram/attempt-1/output.json"],
      },
      {
        id: "visual_reviewer/distribution_histogram/attempt-1",
        role: "visual_reviewer",
        label: "Visual reviewer",
        artifactId: "distribution_histogram",
        attempt: 1,
        inputPaths: ["05-visual-reviewer/distribution_histogram/attempt-1/review-context.json"],
        outputPaths: ["05-visual-reviewer/distribution_histogram/attempt-1/output.json"],
      },
    ];

    const html = renderToStaticMarkup(
      <AgentInvocationList
        invocations={invocations}
        selectedPath={null}
        onSelectPath={() => undefined}
      />,
    );

    expect(html).toContain("Agent runs");
    expect(html).toContain("EDA framer");
    expect(html).toContain("Artifact builder");
    expect(html).toContain("Visual reviewer");
    expect(html).toContain("distribution_histogram");
    expect(html).toContain("attempt 1");
    expect(html).toContain("Inputs");
    expect(html).toContain("Outputs");
    expect(html).toContain("01-eda-framer/output.json");
    expect(html).toContain("05-visual-reviewer/distribution_histogram/attempt-1/output.json");
  });
});
