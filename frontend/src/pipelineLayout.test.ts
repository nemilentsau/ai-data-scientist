import { describe, expect, it } from "vitest";

import { derivePipelineGraph } from "./pipelineGraph";
import { layoutPipeline } from "./pipelineLayout";
import { makeRun } from "./runFixture";

describe("layoutPipeline", () => {
  it("positions every stage node and routes every edge", () => {
    const graph = derivePipelineGraph(
      makeRun({
        artifacts: [
          { id: "a", status: "passed", attempts: [{ verdict: "revise" }, { verdict: "pass" }] },
          { id: "b", status: "passed", attempts: [{ verdict: "pass" }] },
        ],
        status: "passed_visual_gate",
      }),
    );

    const layout = layoutPipeline(graph);

    for (const node of graph.nodes) {
      const point = layout.nodes[node.id];
      expect(point).toBeDefined();
      expect(Number.isFinite(point?.x)).toBe(true);
      expect(Number.isFinite(point?.y)).toBe(true);
    }
    for (const edge of graph.edges) {
      expect(layout.edges[edge.id]?.length ?? 0).toBeGreaterThanOrEqual(2);
    }
    expect(layout.width).toBeGreaterThan(0);
    expect(layout.height).toBeGreaterThan(0);
  });

  it("stacks the setup chain vertically and runs the pipeline horizontally", () => {
    const graph = derivePipelineGraph(
      makeRun({ artifacts: [{ id: "a", status: "passed", attempts: [{ verdict: "pass" }] }] }),
    );
    const layout = layoutPipeline(graph);

    // Setup chain is a vertical left column.
    expect(layout.nodes.dataset?.y ?? 0).toBeLessThan(layout.nodes.framer?.y ?? 0);
    expect(layout.nodes.framer?.y ?? 0).toBeLessThan(layout.nodes.select?.y ?? 0);
    expect(layout.nodes.dataset?.x).toBe(layout.nodes.select?.x);

    // Pipeline is a horizontal row at one height.
    expect(layout.nodes.select?.x ?? 0).toBeLessThan(layout.nodes.build?.x ?? 0);
    expect(layout.nodes.build?.x ?? 0).toBeLessThan(layout.nodes.review?.x ?? 0);
    expect(layout.nodes.build?.y).toBe(layout.nodes.review?.y);
  });
});
