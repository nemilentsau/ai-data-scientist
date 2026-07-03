import { describe, expect, it } from "vitest";

import { derivePipelineGraph, type StageEdge, type StageNode } from "./pipelineGraph";
import { makeRun } from "./runFixture";

function node(nodes: StageNode[], id: string): StageNode {
  const found = nodes.find((n) => n.id === id);
  if (!found) throw new Error(`missing node ${id}`);
  return found;
}

function edge(edges: StageEdge[], id: string): StageEdge {
  const found = edges.find((e) => e.id === id);
  if (!found) throw new Error(`missing edge ${id}`);
  return found;
}

describe("derivePipelineGraph", () => {
  it("models the eight harness stages and the loop/branch edges", () => {
    const graph = derivePipelineGraph(
      makeRun({ artifacts: [{ id: "hist", status: "passed", attempts: [{ verdict: "pass" }] }] }),
    );

    expect(graph.nodes.map((n) => n.id)).toEqual([
      "dataset",
      "framer",
      "select",
      "build",
      "execute",
      "render",
      "review",
      "finalize",
    ]);

    expect(edge(graph.edges, "review->build").kind).toBe("loop");
    expect(edge(graph.edges, "review->build").label).toBe("revise");
    expect(edge(graph.edges, "review->select").label).toBe("pass");
    expect(edge(graph.edges, "select->finalize").label).toBe("all passed");
  });

  it("overlays run counts and verdicts for an all-pass run", () => {
    const graph = derivePipelineGraph(
      makeRun({
        artifacts: [
          { id: "a", status: "passed", attempts: [{ verdict: "pass" }] },
          { id: "b", status: "passed", attempts: [{ verdict: "pass" }] },
          { id: "c", status: "passed", attempts: [{ verdict: "pass" }] },
          { id: "d", status: "passed", attempts: [{ verdict: "pass" }] },
        ],
        status: "passed_visual_gate",
      }),
    );

    expect(node(graph.nodes, "build").runs).toBe(4);
    expect(node(graph.nodes, "review").runs).toBe(4);
    expect(node(graph.nodes, "review").detail).toBe("4 pass · 0 revise");

    // The revise back-edge never fired; the pass edge fired once per artifact.
    expect(edge(graph.edges, "review->build").traversed).toBe(false);
    expect(edge(graph.edges, "review->build").count).toBe(0);
    expect(edge(graph.edges, "review->select").traversed).toBe(true);
    expect(edge(graph.edges, "review->select").count).toBe(4);
    expect(edge(graph.edges, "select->finalize").traversed).toBe(true);
  });

  it("marks the revise loop as traversed when an artifact needed a second attempt", () => {
    const graph = derivePipelineGraph(
      makeRun({
        artifacts: [
          {
            id: "looped",
            status: "passed",
            attempts: [{ verdict: "revise" }, { verdict: "pass" }],
          },
        ],
        status: "passed_visual_gate",
      }),
    );

    expect(node(graph.nodes, "build").runs).toBe(2);
    expect(node(graph.nodes, "review").detail).toBe("1 pass · 1 revise");
    expect(edge(graph.edges, "review->build").traversed).toBe(true);
    expect(edge(graph.edges, "review->build").count).toBe(1);
  });

  it("routes an exhausted artifact straight to finalize", () => {
    const graph = derivePipelineGraph(
      makeRun({
        artifacts: [
          {
            id: "stuck",
            status: "revision_budget_exhausted",
            attempts: [{ verdict: "revise" }, { verdict: "revise" }],
          },
        ],
        status: "revision_budget_exhausted",
      }),
    );

    expect(edge(graph.edges, "review->finalize").traversed).toBe(true);
    expect(edge(graph.edges, "review->finalize").count).toBe(1);
    expect(edge(graph.edges, "select->finalize").traversed).toBe(false);
    expect(node(graph.nodes, "review").detail).toBe("0 pass · 2 revise · 1 exhausted");
  });
});
