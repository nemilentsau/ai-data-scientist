import { useMemo, useState } from "react";

import { PipelineCanvas } from "./PipelineCanvas";
import { StagePanel } from "./StagePanel";
import { derivePipelineGraph, type StageId } from "./pipelineGraph";
import type { LoadedRun } from "./types";
import { Eyebrow, StatusChip } from "./ui";

export function PipelineView({
  run,
  onSelectPath,
  onSelectArtifact,
}: {
  run: LoadedRun;
  onSelectPath: (path: string) => void;
  onSelectArtifact: (artifactId: string) => void;
}) {
  const graph = useMemo(() => derivePipelineGraph(run), [run]);
  const [selectedStage, setSelectedStage] = useState<StageId | null>(null);

  const selectedLabel = selectedStage
    ? (graph.nodes.find((node) => node.id === selectedStage)?.label ?? selectedStage)
    : "";

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col">
      <header className="space-y-2 border-b border-zinc-200 px-8 py-5">
        <Eyebrow>pipeline · control flow</Eyebrow>
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-base font-semibold tracking-tight text-zinc-950">
            How the harness ran this analysis
          </h2>
          <StatusChip status={graph.status} />
        </div>
        <p className="max-w-3xl text-sm leading-6 text-zinc-500">
          The LangGraph loop: each planned chart goes through build → execute → render → review, and a
          reviewer <span className="font-mono text-zinc-600">revise</span> sends it back to the builder
          (up to two attempts). Solid teal edges were taken this run; dashed edges were not. Click a
          stage to see its artifacts. Step-level traces will move to Opik / Langfuse.
        </p>
      </header>

      <div className="relative flex min-h-0 flex-1 bg-zinc-50">
        <div className="min-w-0 flex-1">
          <PipelineCanvas
            graph={graph}
            selectedStage={selectedStage}
            onSelectStage={setSelectedStage}
          />
        </div>
        {selectedStage ? (
          <div className="absolute bottom-0 right-0 top-0 flex shadow-xl">
            <StagePanel
              stage={selectedStage}
              label={selectedLabel}
              run={run}
              onSelectArtifact={onSelectArtifact}
              onSelectPath={onSelectPath}
              onClose={() => setSelectedStage(null)}
            />
          </div>
        ) : null}
      </div>
    </div>
  );
}
