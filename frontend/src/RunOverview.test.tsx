import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { RunOverview } from "./RunOverview";

describe("RunOverview", () => {
  it("summarizes the run question, status, artifact count, and agent count", () => {
    const html = renderToStaticMarkup(
      <RunOverview
        runName="target-distribution"
        status="passed_visual_gate"
        userQuestion="Analyze the target distribution for subsequent model building."
        analysisGoal="Inspect distribution shape before modeling claims."
        artifactCount={4}
        agentRunCount={9}
      />,
    );

    expect(html).toContain("target-distribution");
    expect(html).toContain("passed_visual_gate");
    expect(html).toContain("Analyze the target distribution");
    expect(html).toContain("Inspect distribution shape");
    expect(html).toContain("4");
    expect(html).toContain("9");
  });
});
