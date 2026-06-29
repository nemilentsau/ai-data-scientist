import { AlertCircle, FolderOpen, RefreshCw } from "lucide-react";
import { type ChangeEvent, useEffect, useMemo, useRef, useState } from "react";

import { ArtifactDetailView } from "./ArtifactDetailView";
import { FilesView } from "./FilesView";
import { OverviewView } from "./OverviewView";
import { PipelineView } from "./PipelineView";
import { RunHeader } from "./RunHeader";
import { RunSidebar } from "./RunSidebar";
import { deriveAgentInvocations, type AgentInvocation } from "./agentInvocations";
import {
  deriveArtifactSummaries,
  readFramerOutput,
  textArtifact,
  type ArtifactSummary,
} from "./artifactLoop";
import { datasetFromRunId } from "./format";
import { toGalleryItems, type GalleryItem } from "./overview";
import { listLocalRuns, loadLocalRun, type RunSummary } from "./runApi";
import { loadRunFolder } from "./runFolder";
import { filesView, overviewView, viewKey, type RunView } from "./runView";
import type { LoadedRun } from "./types";
import { EmptyNote } from "./ui";

const SYNTHESIS_PATH = "06-synthesis/report.md";

type Derived =
  | {
      ok: true;
      summaries: ArtifactSummary[];
      invocations: AgentInvocation[];
      items: GalleryItem[];
      question: string;
      goal: string;
      synthesis: string | null;
    }
  | { ok: false; error: string };

export function App() {
  const pickerRef = useRef<HTMLInputElement>(null);
  const [run, setRun] = useState<LoadedRun | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [activeRunId, setActiveRunId] = useState("");
  const [loadError, setLoadError] = useState("");
  const [isLoadingRun, setIsLoadingRun] = useState(false);
  const [view, setView] = useState<RunView>(overviewView());

  const derived = useMemo<Derived | null>(() => {
    if (!run) return null;
    try {
      const summaries = deriveArtifactSummaries(run);
      const framer = readFramerOutput(run);
      return {
        ok: true,
        summaries,
        invocations: deriveAgentInvocations(run),
        items: toGalleryItems(run, summaries),
        question: framer.user_question,
        goal: framer.analysis_goal,
        synthesis: textArtifact(run, SYNTHESIS_PATH)?.text ?? null,
      };
    } catch (error) {
      return { ok: false, error: error instanceof Error ? error.message : String(error) };
    }
  }, [run]);

  useEffect(() => {
    let cancelled = false;

    async function loadInitialRun(): Promise<void> {
      setIsLoadingRun(true);
      try {
        const summaries = await listLocalRuns();
        if (cancelled) return;
        setRuns(summaries);

        const firstRun = summaries[0];
        if (!firstRun) {
          resetRun(null, "");
          return;
        }

        const parsed = await loadLocalRun(firstRun.id);
        if (cancelled) return;
        resetRun(parsed, firstRun.id);
      } catch (error) {
        if (cancelled) return;
        setLoadError(error instanceof Error ? error.message : String(error));
        resetRun(null, "");
      } finally {
        if (!cancelled) setIsLoadingRun(false);
      }
    }

    void loadInitialRun();
    return () => {
      cancelled = true;
    };
  }, []);

  function resetRun(parsed: LoadedRun | null, runId: string): void {
    setRun(parsed);
    setActiveRunId(runId);
    setView(overviewView());
    setLoadError("");
  }

  async function selectLocalRun(runId: string): Promise<void> {
    if (!runId) return;
    setIsLoadingRun(true);
    try {
      const parsed = await loadLocalRun(runId);
      resetRun(parsed, runId);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : String(error));
    } finally {
      setIsLoadingRun(false);
    }
  }

  async function handleFiles(event: ChangeEvent<HTMLInputElement>): Promise<void> {
    const files = Array.from(event.target.files ?? []);
    if (files.length === 0) return;
    try {
      const parsed = await loadRunFolder(files);
      resetRun(parsed, "");
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : String(error));
      setRun(null);
    } finally {
      event.target.value = "";
    }
  }

  function openPicker(): void {
    pickerRef.current?.click();
  }

  const datasetName = activeRunId ? datasetFromRunId(activeRunId) : "external";
  const status = run ? (run.lineage.status ?? "unknown") : null;

  return (
    <div className="flex h-screen flex-col bg-zinc-50 text-zinc-900">
      <RunHeader
        runs={runs}
        activeRunId={activeRunId}
        status={status}
        isLoadingRun={isLoadingRun}
        onSelectRun={(runId) => void selectLocalRun(runId)}
        onImport={openPicker}
      />

      <input
        ref={pickerRef}
        type="file"
        multiple
        webkitdirectory=""
        directory=""
        className="hidden"
        onChange={handleFiles}
      />

      {loadError ? (
        <div className="flex items-center gap-2 border-b border-red-200 bg-red-50 px-6 py-2.5 text-sm text-red-800">
          <AlertCircle size={16} />
          {loadError}
        </div>
      ) : null}

      {!run ? (
        <EmptyState isLoadingRun={isLoadingRun} hasRuns={runs.length > 0} onOpen={openPicker} />
      ) : derived?.ok ? (
        <div className="flex min-h-0 flex-1">
          <RunSidebar current={view} summaries={derived.summaries} onNavigate={setView} />
          <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
            <ActiveView
              run={run}
              view={view}
              derived={derived}
              datasetName={datasetName}
              status={status ?? "unknown"}
              onNavigate={setView}
            />
          </main>
        </div>
      ) : (
        <SchemaFailure message={derived?.ok === false ? derived.error : "Run could not be parsed."} />
      )}
    </div>
  );
}

function ActiveView({
  run,
  view,
  derived,
  datasetName,
  status,
  onNavigate,
}: {
  run: LoadedRun;
  view: RunView;
  derived: Extract<Derived, { ok: true }>;
  datasetName: string;
  status: string;
  onNavigate: (view: RunView) => void;
}) {
  if (view.kind === "files") {
    return (
      <FilesView
        run={run}
        selectedPath={view.path}
        onSelectPath={(path) => onNavigate(filesView(path))}
      />
    );
  }

  return (
    <div key={viewKey(view)} className="min-h-0 flex-1 overflow-auto">
      {view.kind === "overview" ? (
        <OverviewView
          question={derived.question}
          goal={derived.goal}
          status={status}
          datasetName={datasetName}
          artifactCount={derived.summaries.length}
          agentRunCount={derived.invocations.length}
          items={derived.items}
          synthesisMarkdown={derived.synthesis}
          onSelectArtifact={(artifactId) => onNavigate({ kind: "artifact", artifactId })}
        />
      ) : null}

      {view.kind === "artifact" ? (
        <ArtifactDetail
          run={run}
          summaries={derived.summaries}
          artifactId={view.artifactId}
          onNavigate={onNavigate}
        />
      ) : null}

      {view.kind === "pipeline" ? (
        <PipelineView
          invocations={derived.invocations}
          selectedPath={null}
          onSelectPath={(path) => onNavigate(filesView(path))}
        />
      ) : null}
    </div>
  );
}

function ArtifactDetail({
  run,
  summaries,
  artifactId,
  onNavigate,
}: {
  run: LoadedRun;
  summaries: ArtifactSummary[];
  artifactId: string;
  onNavigate: (view: RunView) => void;
}) {
  const summary = summaries.find((item) => item.id === artifactId);
  if (!summary) {
    return (
      <div className="px-8 py-10">
        <EmptyNote>This artifact is not part of the current run.</EmptyNote>
      </div>
    );
  }

  return (
    <ArtifactDetailView
      run={run}
      summary={summary}
      onSelectFile={(path) => onNavigate(filesView(path))}
    />
  );
}

function EmptyState({
  isLoadingRun,
  hasRuns,
  onOpen,
}: {
  isLoadingRun: boolean;
  hasRuns: boolean;
  onOpen: () => void;
}) {
  return (
    <div className="grid flex-1 place-items-center px-6">
      <div className="max-w-xl space-y-4 text-center">
        <h2 className="text-2xl font-semibold tracking-tight text-zinc-950">
          {isLoadingRun ? "Loading local runs…" : "No run selected"}
        </h2>
        <p className="text-sm leading-6 text-zinc-600">
          {hasRuns
            ? "Choose a run from the selector in the header."
            : "No runs were found under runs/eda-artifacts. The importer is only for runs outside this repository."}
        </p>
        <button
          type="button"
          onClick={onOpen}
          className="inline-flex items-center gap-2 rounded-md border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 transition hover:border-zinc-400 hover:bg-zinc-50"
        >
          {isLoadingRun ? <RefreshCw size={15} className="animate-spin" /> : <FolderOpen size={15} />}
          Import external run
        </button>
      </div>
    </div>
  );
}

function SchemaFailure({ message }: { message: string }) {
  return (
    <div className="grid flex-1 place-items-center px-6">
      <div className="max-w-2xl space-y-3 border-l-2 border-red-400 bg-red-50/60 p-5">
        <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-red-800">
          Frontend contract failure
        </p>
        <h2 className="text-xl font-semibold text-zinc-950">This run cannot be rendered.</h2>
        <p className="text-sm leading-6 text-red-900">{message}</p>
      </div>
    </div>
  );
}
