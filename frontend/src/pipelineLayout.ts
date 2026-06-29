import type { PipelineGraph, StageId } from "./pipelineGraph";

export const NODE_WIDTH = 200;
export const NODE_HEIGHT = 82;

export type Point = { x: number; y: number };

export type PipelineLayout = {
  nodes: Record<string, Point>;
  edges: Record<string, Point[]>;
  width: number;
  height: number;
};

// Authored 2D fold: the setup chain runs vertically down the left, the chart
// pipeline runs horizontally, and the loop-backs arc through the freed space.
const POSITIONS: Record<StageId, Point> = {
  dataset: { x: 60, y: 40 },
  framer: { x: 60, y: 178 },
  select: { x: 60, y: 316 },
  build: { x: 350, y: 316 },
  execute: { x: 640, y: 316 },
  render: { x: 930, y: 316 },
  review: { x: 1220, y: 316 },
  finalize: { x: 640, y: 506 },
};

const ROW_Y = POSITIONS.select.y;
const REVISE_Y = ROW_Y - 66;
const PASS_Y = ROW_Y - 150;
const FAR_LEFT_X = 14;
const BOTTOM_Y = POSITIONS.finalize.y + NODE_HEIGHT / 2;

const topC = (p: Point): Point => ({ x: p.x + NODE_WIDTH / 2, y: p.y });
const bottomC = (p: Point): Point => ({ x: p.x + NODE_WIDTH / 2, y: p.y + NODE_HEIGHT });
const leftC = (p: Point): Point => ({ x: p.x, y: p.y + NODE_HEIGHT / 2 });
const rightC = (p: Point): Point => ({ x: p.x + NODE_WIDTH, y: p.y + NODE_HEIGHT / 2 });
const centerC = (p: Point): Point => ({ x: p.x + NODE_WIDTH / 2, y: p.y + NODE_HEIGHT / 2 });

function routeFor(id: string): Point[] | undefined {
  const p = POSITIONS;
  switch (id) {
    case "dataset->framer":
      return [bottomC(p.dataset), topC(p.framer)];
    case "framer->select":
      return [bottomC(p.framer), topC(p.select)];
    case "select->build":
      return [rightC(p.select), leftC(p.build)];
    case "build->execute":
      return [rightC(p.build), leftC(p.execute)];
    case "execute->render":
      return [rightC(p.execute), leftC(p.render)];
    case "render->review":
      return [rightC(p.render), leftC(p.review)];
    case "review->build":
      return [
        topC(p.review),
        { x: topC(p.review).x, y: REVISE_Y },
        { x: topC(p.build).x, y: REVISE_Y },
        topC(p.build),
      ];
    case "review->select":
      return [
        topC(p.review),
        { x: topC(p.review).x, y: PASS_Y },
        { x: FAR_LEFT_X, y: PASS_Y },
        { x: FAR_LEFT_X, y: leftC(p.select).y },
        leftC(p.select),
      ];
    case "select->finalize":
      return [
        bottomC(p.select),
        { x: bottomC(p.select).x, y: BOTTOM_Y },
        { x: leftC(p.finalize).x, y: BOTTOM_Y },
        leftC(p.finalize),
      ];
    case "review->finalize":
      return [
        bottomC(p.review),
        { x: bottomC(p.review).x, y: BOTTOM_Y },
        { x: rightC(p.finalize).x, y: BOTTOM_Y },
        rightC(p.finalize),
      ];
    default:
      return undefined;
  }
}

export function layoutPipeline(graph: PipelineGraph): PipelineLayout {
  const nodes: Record<string, Point> = {};
  for (const node of graph.nodes) nodes[node.id] = POSITIONS[node.id];

  const edges: Record<string, Point[]> = {};
  for (const edge of graph.edges) {
    edges[edge.id] =
      routeFor(edge.id) ?? [centerC(POSITIONS[edge.source]), centerC(POSITIONS[edge.target])];
  }

  return {
    nodes,
    edges,
    width: POSITIONS.review.x + NODE_WIDTH + FAR_LEFT_X,
    height: POSITIONS.finalize.y + NODE_HEIGHT + 40,
  };
}
