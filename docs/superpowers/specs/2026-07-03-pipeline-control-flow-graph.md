# Pipeline Control-Flow Graph — Design

Date: 2026-07-03
Status: Implemented

Supersedes the **Pipeline** view described in
[`2026-06-29-run-inspector-reframe-design.md`](2026-06-29-run-inspector-reframe-design.md)
(originally an ordered "agent runs" timeline).

## Problem

The inspector's Pipeline view drew the run as a straight directional line
(`framer → builder → reviewer → …`). That misrepresents the harness: it is a
**loop**, not a line. In `eda_artifacts/graph.py` the LangGraph flow has two
cycles — an inner revise retry (`build → execute → render → review →(revise)
build`, bounded to two attempts) and an outer per-artifact loop (`select →
… → review →(pass) select`) — plus conditional branches. A timeline hides all
of that.

## Decisions

- Render the run's **control flow as a node-link graph** of the real harness
  topology, with the loops and branches drawn, not a linear list.
- **Overlay this run** onto the fixed topology rather than drawing a per-run
  trace: per-stage run counts, the reviewer pass/revise/exhausted tally, and
  traversed edges (solid teal) vs untraversed edges (dashed grey).
- **Author the layout.** The topology is a fixed eight-stage graph that is
  mostly a chain; a general graph-layout engine lays a chain out as a thin strip
  and cannot "fold" it. So node positions and edge routes are authored: the
  setup chain (`dataset → framer → select`) runs vertically, the chart pipeline
  (`build → execute → render → review`) runs horizontally, and the loop-backs
  (revise / pass / all-passed / exhausted) are orthogonally routed through the
  freed space. This uses both dimensions and keeps edges crossing-free.
- Render with **React Flow** (`@xyflow/react`): custom nodes, a custom edge that
  draws the authored routed polyline, pan/zoom + fit controls.
- **Click a stage → drill in.** A stage panel lists that stage's actual
  artifact × attempt instances (verdict chips + file links); the router node
  lists the ordered artifact plan. The panel **overlays** the graph so it never
  shrinks it.

## Topology (from `graph.py`)

Nodes: `dataset` (harness), `framer` (agent), `select` (router), `build`
(agent), `execute` (harness), `render` (harness), `review` (agent), `finalize`
(harness / synthesis).

Edges: the forward chain, plus conditional edges `select→build` (next artifact)
/ `select→finalize` (all passed) and `review→build` (revise) / `review→select`
(pass) / `review→finalize` (exhausted).

## Modules

- `pipelineGraph.ts` — pure. `derivePipelineGraph(run)` → stage nodes (label,
  owner, run count, detail) + edges (kind, label, traversed flag + count) +
  status, from `deriveArtifactSummaries` + reviewer verdicts + lineage. Tested.
- `pipelineLayout.ts` — pure. `layoutPipeline(graph)` → authored node positions
  + orthogonal edge point-lists. Tested.
- `stageInstances.ts` — pure. `stageInstances(run, stage)` → the drill-in list
  (artifact/attempt/verdict/files) for a stage; the router returns the ordered
  plan. Tested.
- `PipelineCanvas.tsx` — React Flow render: custom `StageNode`, custom
  `RoutedEdge` (draws the routed polyline with an arrow + a label anchored on
  its longest segment), pan/zoom + fit Controls.
- `StagePanel.tsx` — the overlay drill-in panel (plain DOM, tested).
- `PipelineView.tsx` — composes the header, canvas, and overlay panel; wires
  node clicks and file/artifact navigation.

## Constraints honored

- `agentInvocations.ts` is unchanged and still derived, so the Python contract
  guard and `backendContract.test.ts` stay green; every agent invocation is
  reachable via the stage drill-in.
- `selectedView.ts` strictness (no fallback rendering) is untouched.
- TS-only, strict, no `.js`. Port stays `localhost:5180`.
- The React Flow canvas is DOM-measured, so it is verified in the browser; all
  layout/graph/instances logic is pure and unit-tested via `runFixture.ts`.

## Future

Step-level traces (prompts, tokens, timings) move to Opik / Langfuse; this graph
is the seam they plug into.
