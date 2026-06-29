import { useMemo } from "react";
import {
  BaseEdge,
  Controls,
  EdgeLabelRenderer,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  type Edge,
  type EdgeProps,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type { PipelineGraph as PipelineGraphModel, StageId, StageOwner } from "./pipelineGraph";
import { layoutPipeline, type Point } from "./pipelineLayout";

type StageNodeData = {
  label: string;
  owner: StageOwner;
  runs: number;
  detail?: string;
  dim: boolean;
};

type StageFlowNode = Node<StageNodeData, "stage">;

type RoutedEdgeData = {
  points: Point[];
  color: string;
  traversed: boolean;
  label?: string;
};

const UNLABELED_EDGES = new Set(["select->build"]);

const OWNER_LABEL: Record<StageOwner, string> = {
  agent: "agent",
  harness: "harness",
  control: "router",
};

const OWNER_ACCENT: Record<StageOwner, string> = {
  agent: "border-l-teal-500",
  harness: "border-l-zinc-300",
  control: "border-l-violet-400",
};

const TRAVERSED = "#0f766e";
const IDLE = "#cbd5e1";

const nodeTypes = { stage: StageNode };
const edgeTypes = { routed: RoutedEdge };

export function PipelineCanvas({
  graph,
  selectedStage,
  onSelectStage,
}: {
  graph: PipelineGraphModel;
  selectedStage: StageId | null;
  onSelectStage: (stage: StageId) => void;
}) {
  const layout = useMemo(() => layoutPipeline(graph), [graph]);

  const nodes = useMemo<StageFlowNode[]>(
    () =>
      graph.nodes.map((stage) => ({
        id: stage.id,
        type: "stage",
        position: layout.nodes[stage.id] ?? { x: 0, y: 0 },
        selected: stage.id === selectedStage,
        data: {
          label: stage.label,
          owner: stage.owner,
          runs: stage.runs,
          dim: stage.runs === 0,
          ...(stage.detail ? { detail: stage.detail } : {}),
        },
      })),
    [graph.nodes, layout, selectedStage],
  );

  const edges = useMemo<Edge[]>(
    () =>
      graph.edges.map((edge) => {
        const color = edge.traversed ? TRAVERSED : IDLE;
        const showLabel = edge.label && !UNLABELED_EDGES.has(edge.id);
        const data: RoutedEdgeData = {
          points: layout.edges[edge.id] ?? [],
          color,
          traversed: edge.traversed,
          ...(showLabel ? { label: edgeLabel(edge.label as string, edge.count, edge.traversed) } : {}),
        };
        return {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          type: "routed",
          data,
          markerEnd: { type: MarkerType.ArrowClosed, color, width: 18, height: 18 },
        } satisfies Edge;
      }),
    [graph.edges, layout],
  );

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.08, maxZoom: 1.0 }}
        nodesDraggable={false}
        nodesConnectable={false}
        edgesFocusable={false}
        zoomOnScroll
        zoomOnDoubleClick
        panOnDrag
        panOnScroll={false}
        proOptions={{ hideAttribution: true }}
        minZoom={0.5}
        maxZoom={1.8}
        onNodeClick={(_, node) => onSelectStage(node.id as StageId)}
      >
        <Controls showInteractive={false} position="bottom-left" />
      </ReactFlow>
    </div>
  );
}

function StageNode({ data, selected }: NodeProps<StageFlowNode>) {
  return (
    <div
      className={`w-[200px] rounded-xl border border-l-4 bg-white px-4 py-3.5 shadow-sm transition ${
        OWNER_ACCENT[data.owner]
      } ${selected ? "border-teal-500 ring-2 ring-teal-400" : "border-zinc-200"} ${
        data.dim ? "opacity-55" : ""
      }`}
    >
      <Handle id="t" type="target" position={Position.Top} style={HIDDEN_HANDLE} />
      <Handle id="b" type="source" position={Position.Bottom} style={HIDDEN_HANDLE} />
      <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-zinc-400">
        {OWNER_LABEL[data.owner]}
      </p>
      <p className="text-[17px] font-semibold leading-tight text-zinc-950">{data.label}</p>
      <p className="mt-1 font-mono text-[13px] text-zinc-500">
        {data.detail ?? (data.runs === 1 ? "ran once" : `ran ×${data.runs}`)}
      </p>
    </div>
  );
}

function RoutedEdge({ id, markerEnd, data }: EdgeProps) {
  const routed = data as RoutedEdgeData | undefined;
  const points = routed?.points ?? [];
  if (points.length < 2) return null;

  const path = smoothPath(points);
  const mid = labelAnchor(points);

  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        {...(markerEnd ? { markerEnd } : {})}
        style={{
          stroke: routed?.color ?? IDLE,
          strokeWidth: routed?.traversed ? 2.5 : 1.75,
          strokeDasharray: routed?.traversed ? undefined : "6 5",
          fill: "none",
        }}
      />
      {routed?.label && mid ? (
        <EdgeLabelRenderer>
          <div
            className="nodrag nopan pointer-events-none rounded bg-white/90 px-1.5 py-0.5 font-mono text-[13px] font-semibold"
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${mid.x}px, ${mid.y}px)`,
              color: routed.traversed ? TRAVERSED : "#94a3b8",
            }}
          >
            {routed.label}
          </div>
        </EdgeLabelRenderer>
      ) : null}
    </>
  );
}

const HIDDEN_HANDLE = {
  opacity: 0,
  width: 1,
  height: 1,
  minWidth: 0,
  minHeight: 0,
  border: "none",
} as const;

// Anchor the label at the midpoint of the longest segment so it lands on a
// clear, straight stretch of the edge instead of a corner.
function labelAnchor(points: Point[]): Point | undefined {
  let anchor: Point | undefined;
  let longest = -1;
  for (let i = 0; i < points.length - 1; i += 1) {
    const a = points[i];
    const b = points[i + 1];
    if (!a || !b) continue;
    const length = Math.hypot(b.x - a.x, b.y - a.y);
    if (length > longest) {
      longest = length;
      anchor = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
    }
  }
  return anchor;
}

function smoothPath(points: Point[]): string {
  const first = points[0];
  if (!first) return "";

  let d = `M ${first.x},${first.y}`;
  for (let i = 1; i < points.length - 1; i += 1) {
    const current = points[i];
    const next = points[i + 1];
    if (!current || !next) continue;
    const midX = (current.x + next.x) / 2;
    const midY = (current.y + next.y) / 2;
    d += ` Q ${current.x},${current.y} ${midX},${midY}`;
  }
  const last = points[points.length - 1];
  if (last) d += ` L ${last.x},${last.y}`;
  return d;
}

function edgeLabel(label: string, count: number, traversed: boolean): string {
  return traversed && count > 0 ? `${label} ×${count}` : label;
}
