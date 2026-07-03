import { FolderOpen, RefreshCw } from "lucide-react";

import { runNameFromId } from "./format";
import type { RunSummary } from "./runApi";
import { StatusChip } from "./ui";

export function RunHeader({
  runs,
  activeRunId,
  status,
  isLoadingRun,
  onSelectRun,
  onImport,
}: {
  runs: RunSummary[];
  activeRunId: string;
  status: string | null;
  isLoadingRun: boolean;
  onSelectRun: (runId: string) => void;
  onImport: () => void;
}) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-200 bg-white px-6 py-3">
      <div className="flex items-baseline gap-3">
        <span className="font-mono text-[11px] uppercase tracking-[0.24em] text-teal-700">
          eda·artifacts
        </span>
        <h1 className="text-sm font-semibold tracking-tight text-zinc-950">Analysis inspector</h1>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        {runs.length > 0 ? (
          <label className="flex items-center gap-2 rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm">
            <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-zinc-400">
              Run
            </span>
            <select
              value={activeRunId}
              disabled={isLoadingRun}
              onChange={(event) => onSelectRun(event.target.value)}
              className="max-w-64 bg-transparent text-sm text-zinc-900 outline-none disabled:text-zinc-400"
            >
              {activeRunId === "" ? <option value="">Select run</option> : null}
              {runs.map((summary) => (
                <option key={summary.id} value={summary.id}>
                  {runNameFromId(summary.id)}
                </option>
              ))}
            </select>
          </label>
        ) : null}

        {status ? <StatusChip status={status} /> : null}

        <button
          type="button"
          onClick={onImport}
          className="inline-flex items-center gap-2 rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium text-zinc-700 transition hover:border-zinc-400 hover:bg-zinc-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-500"
        >
          {isLoadingRun ? <RefreshCw size={15} className="animate-spin" /> : <FolderOpen size={15} />}
          Import run
        </button>
      </div>
    </header>
  );
}
