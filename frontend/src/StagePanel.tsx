import { X } from "lucide-react";

import type { StageId } from "./pipelineGraph";
import { fileChipLabel } from "./runFolder";
import { stageInstances } from "./stageInstances";
import type { LoadedRun } from "./types";
import { EmptyNote, Eyebrow, StatusChip } from "./ui";

export function StagePanel({
  stage,
  label,
  run,
  onSelectArtifact,
  onSelectPath,
  onClose,
}: {
  stage: StageId;
  label: string;
  run: LoadedRun;
  onSelectArtifact: (artifactId: string) => void;
  onSelectPath: (path: string) => void;
  onClose: () => void;
}) {
  const instances = stageInstances(run, stage);

  return (
    <aside className="flex w-80 shrink-0 flex-col overflow-auto border-l border-zinc-200 bg-white">
      <header className="flex items-start justify-between gap-3 border-b border-zinc-200 px-4 py-3">
        <div className="space-y-1">
          <Eyebrow>Stage</Eyebrow>
          <h3 className="text-sm font-semibold text-zinc-950">{label}</h3>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close stage panel"
          className="rounded p-1 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700"
        >
          <X size={16} />
        </button>
      </header>

      {instances.length === 0 ? (
        <div className="px-4 py-4">
          <EmptyNote>No artifacts at this stage.</EmptyNote>
        </div>
      ) : (
        <ul className="divide-y divide-zinc-100">
          {instances.map((instance) => (
            <li key={instance.key} className="space-y-2 px-4 py-3">
              <div className="flex items-center justify-between gap-2">
                {instance.artifactId ? (
                  <button
                    type="button"
                    onClick={() => onSelectArtifact(instance.artifactId as string)}
                    className="text-left text-sm font-medium text-zinc-900 hover:text-teal-800"
                  >
                    {instance.label}
                  </button>
                ) : (
                  <span className="text-sm font-medium text-zinc-900">{instance.label}</span>
                )}
                {instance.verdict ? (
                  <StatusChip status={instance.verdict} />
                ) : instance.status && stage === "select" ? (
                  <StatusChip status={instance.status} />
                ) : null}
              </div>

              {instance.paths.length > 0 ? (
                <ul className="flex flex-wrap gap-1.5">
                  {instance.paths.map((path) => (
                    <li key={path}>
                      <button
                        type="button"
                        onClick={() => onSelectPath(path)}
                        title={path}
                        className="rounded border border-zinc-200 px-2 py-0.5 font-mono text-[11px] text-zinc-600 transition hover:border-teal-300 hover:text-teal-800"
                      >
                        {fileChipLabel(path)}
                      </button>
                    </li>
                  ))}
                </ul>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
