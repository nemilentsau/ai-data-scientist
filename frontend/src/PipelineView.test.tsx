import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { StagePanel } from "./StagePanel";
import { makeRun } from "./runFixture";

const run = makeRun({
  artifacts: [
    { id: "hist", status: "passed", attempts: [{ verdict: "revise" }, { verdict: "pass" }] },
    { id: "ecdf", status: "passed", attempts: [{ verdict: "pass" }] },
  ],
  status: "passed_visual_gate",
});

describe("StagePanel", () => {
  it("lists review attempts with verdicts and file links", () => {
    const html = renderToStaticMarkup(
      <StagePanel
        stage="review"
        label="Visual reviewer"
        run={run}
        onSelectArtifact={() => {}}
        onSelectPath={() => {}}
        onClose={() => {}}
      />,
    );

    expect(html).toContain("Visual reviewer");
    expect(html).toContain("Hist · attempt 1");
    expect(html).toContain("Hist · attempt 2");
    expect(html).toContain("revise");
    expect(html).toContain("pass");
    expect(html).toContain("review context");
  });

  it("lists the ordered artifact plan for the select router", () => {
    const html = renderToStaticMarkup(
      <StagePanel
        stage="select"
        label="Select artifact"
        run={run}
        onSelectArtifact={() => {}}
        onSelectPath={() => {}}
        onClose={() => {}}
      />,
    );

    expect(html).toContain("Hist");
    expect(html).toContain("Ecdf");
    expect(html).toContain("passed");
  });
});
