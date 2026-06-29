import {
  AlertCircle,
  CheckCircle2,
  ClipboardList,
  Code2,
  Database,
  Eye,
  FileJson,
  FileText,
  FolderOpen,
  GitBranch,
  Image,
  ListTree,
  RefreshCw,
  Table,
  type LucideIcon,
} from "lucide-react";
import { type ChangeEvent, useEffect, useMemo, useRef, useState } from "react";

import { AgentInvocationList } from "./AgentInvocationList";
import { RunOverview } from "./RunOverview";
import {
  deriveAgentInvocations,
  type AgentInvocation,
} from "./agentInvocations";
import {
  artifactIdForPath,
  deriveArtifactSummaries,
  importantPathsForRun,
  latestAttempt,
  readFramerOutput,
  readJsonArtifact,
  textArtifact,
  type ArtifactAttemptSummary,
  type ArtifactSummary,
} from "./artifactLoop";
import { listLocalRuns, loadLocalRun, type RunSummary } from "./runApi";
import {
  isArtifactSelectedView,
  resolveSelectedView,
  type SelectedView,
} from "./selectedView";
import {
  STAGES,
  formatBytes,
  labelForPath,
  loadRunFolder,
  pickInitialPath,
  safeParseJson,
  type StageId,
} from "./runFolder";
import type { LoadedRun, RunArtifact, RunLineage } from "./types";

const STAGE_ICONS: Record<StageId, LucideIcon> = {
  "00-dataset": Database,
  "01-eda-framer": FileJson,
  "02-artifact-builder": Code2,
  "03-execution": Table,
  "04-render": Image,
  "05-visual-reviewer": Eye,
  "06-synthesis": FileText,
};

type StageRow = (typeof STAGES)[number] & {
  artifacts: string[];
};

type ViewResolution =
  | {
      ok: true;
      artifactSummaries: ArtifactSummary[];
      agentInvocations: AgentInvocation[];
      selectedView: SelectedView | null;
    }
  | {
      ok: false;
      artifactSummaries: ArtifactSummary[];
      agentInvocations: AgentInvocation[];
      error: string;
    };

export function App() {
  const pickerRef = useRef<HTMLInputElement>(null);
  const [run, setRun] = useState<LoadedRun | null>(null);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [loadError, setLoadError] = useState("");
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [activeRunId, setActiveRunId] = useState("");
  const [isLoadingRun, setIsLoadingRun] = useState(false);

  const selected = selectedPath && run ? run.files.get(selectedPath) : undefined;

  const viewResolution = useMemo<ViewResolution>(() => {
    if (!run) {
      return { ok: true, artifactSummaries: [], agentInvocations: [], selectedView: null };
    }

    try {
      const summaries = deriveArtifactSummaries(run);
      return {
        ok: true,
        artifactSummaries: summaries,
        agentInvocations: deriveAgentInvocations(run),
        selectedView: selectedPath ? resolveSelectedView(run, selectedPath) : null,
      };
    } catch (error) {
      return {
        ok: false,
        artifactSummaries: [],
        agentInvocations: [],
        error: error instanceof Error ? error.message : String(error),
      };
    }
  }, [run, selectedPath]);

  const artifactSummaries = viewResolution.artifactSummaries;
  const agentInvocations = viewResolution.agentInvocations;
  const selectedView = viewResolution.ok ? viewResolution.selectedView : null;
  const activeArtifact =
    selectedView && isArtifactSelectedView(selectedView) ? selectedView.artifact : undefined;

  const stageRows = useMemo<StageRow[]>(() => {
    if (!run) return [];
    return STAGES.map((stage) => ({
      ...stage,
      artifacts: run.paths.filter((path) => path.startsWith(stage.prefix)),
    }));
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
          setRun(null);
          setSelectedPath(null);
          setActiveRunId("");
          setLoadError("");
          return;
        }

        const parsed = await loadLocalRun(firstRun.id);
        if (cancelled) return;

        setRun(parsed);
        setSelectedPath(pickInitialPath(parsed));
        setActiveRunId(firstRun.id);
        setLoadError("");
      } catch (error) {
        if (cancelled) return;
        setLoadError(error instanceof Error ? error.message : String(error));
        setRun(null);
        setSelectedPath(null);
        setActiveRunId("");
      } finally {
        if (!cancelled) setIsLoadingRun(false);
      }
    }

    void loadInitialRun();

    return () => {
      cancelled = true;
    };
  }, []);

  async function selectLocalRun(runId: string): Promise<void> {
    if (!runId) return;

    setIsLoadingRun(true);
    try {
      const parsed = await loadLocalRun(runId);
      setRun(parsed);
      setSelectedPath(pickInitialPath(parsed));
      setActiveRunId(runId);
      setLoadError("");
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
      setRun(parsed);
      setSelectedPath(pickInitialPath(parsed));
      setActiveRunId("");
      setLoadError("");
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : String(error));
      setRun(null);
      setSelectedPath(null);
    } finally {
      event.target.value = "";
    }
  }

  function openPicker(): void {
    pickerRef.current?.click();
  }

  return (
    <main className="min-h-screen bg-zinc-50 text-zinc-950">
      <header className="border-b-2 border-zinc-950 bg-zinc-50">
        <div className="flex min-h-20 flex-col justify-between gap-4 px-5 py-4 lg:flex-row lg:items-end">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.22em] text-teal-700">
              eda-artifacts
            </p>
            <h1 className="text-3xl font-semibold tracking-tight">Run Inspector</h1>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {runs.length > 0 ? (
              <RunSelector
                runs={runs}
                activeRunId={activeRunId}
                disabled={isLoadingRun}
                onSelect={(runId) => {
                  void selectLocalRun(runId);
                }}
              />
            ) : null}
            {run ? <RunStatus lineage={run.lineage} rootName={run.rootName} /> : null}
            <button
              type="button"
              onClick={openPicker}
              className="inline-flex h-11 items-center gap-2 border-2 border-zinc-950 px-4 text-sm font-semibold transition hover:bg-zinc-950 hover:text-white focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2"
            >
              <FolderOpen size={18} />
              Import external run
            </button>
            <input
              ref={pickerRef}
              type="file"
              multiple
              webkitdirectory=""
              directory=""
              className="hidden"
              onChange={handleFiles}
            />
          </div>
        </div>
      </header>

      {loadError ? (
        <section className="border-b-2 border-red-700 bg-red-50 px-5 py-3 text-sm text-red-900">
          <div className="flex items-center gap-2">
            <AlertCircle size={18} />
            {loadError}
          </div>
        </section>
      ) : null}

      {!run ? (
        <EmptyState isLoadingRun={isLoadingRun} runs={runs} onOpen={openPicker} />
      ) : (
        <>
          {viewResolution.ok ? (
            <RunOverview
              runName={run.rootName}
              status={run.lineage.status ?? "unknown"}
              userQuestion={readFramerOutput(run).user_question}
              analysisGoal={readFramerOutput(run).analysis_goal}
              artifactCount={artifactSummaries.length}
              agentRunCount={agentInvocations.length}
            />
          ) : null}
          <section className="grid min-h-[calc(100vh-187px)] grid-cols-1 lg:h-[calc(100vh-187px)] lg:grid-cols-[390px_minmax(0,1fr)_350px]">
            <ArtifactRail
              agentInvocations={agentInvocations}
              artifacts={artifactSummaries}
              files={run.files}
              selectedPath={selectedPath}
              stageRows={stageRows}
              onSelect={setSelectedPath}
            />
            <ArtifactWorkspace
              run={run}
              artifact={selected}
              activeArtifact={activeArtifact}
              artifactSummaries={artifactSummaries}
              path={selectedPath}
              schemaError={viewResolution.ok ? "" : viewResolution.error}
              selectedView={selectedView}
              onSelect={setSelectedPath}
            />
            <EvidencePane
              run={run}
              activeArtifact={activeArtifact}
              selectedPath={selectedPath}
              onSelect={setSelectedPath}
            />
          </section>
        </>
      )}
    </main>
  );
}

function RunSelector({
  runs,
  activeRunId,
  disabled,
  onSelect,
}: {
  runs: RunSummary[];
  activeRunId: string;
  disabled: boolean;
  onSelect: (runId: string) => void;
}) {
  return (
    <label className="flex h-11 items-center gap-2 border-2 border-zinc-950 bg-white px-3 text-sm">
      <span className="font-mono text-xs uppercase tracking-[0.16em] text-zinc-500">Run</span>
      <select
        value={activeRunId}
        disabled={disabled}
        onChange={(event) => onSelect(event.target.value)}
        className="max-w-72 bg-transparent font-mono text-sm outline-none disabled:text-zinc-500"
      >
        {activeRunId === "" ? <option value="">Select run</option> : null}
        {runs.map((summary) => (
          <option key={summary.id} value={summary.id}>
            {summary.id}
          </option>
        ))}
      </select>
    </label>
  );
}

function EmptyState({
  isLoadingRun,
  runs,
  onOpen,
}: {
  isLoadingRun: boolean;
  runs: RunSummary[];
  onOpen: () => void;
}) {
  return (
    <section className="grid min-h-[calc(100vh-82px)] place-items-center px-6">
      <div className="max-w-3xl border-l-4 border-zinc-950 pl-6">
        <p className="mb-3 font-mono text-xs uppercase tracking-[0.22em] text-teal-700">
          Repo-local run inspector
        </p>
        <h2 className="mb-4 text-4xl font-semibold tracking-tight">
          {isLoadingRun ? "Loading local runs." : "No local run is selected."}
        </h2>
        <p className="mb-6 max-w-2xl text-lg leading-7 text-zinc-700">
          {runs.length > 0
            ? "Choose a run from the selector in the header."
            : "No runs were found under "}
          {runs.length === 0 ? (
            <>
              <code className="font-mono text-sm text-zinc-950">runs/eda-artifacts</code>.
            </>
          ) : null}
        </p>
        <p className="mb-6 max-w-2xl text-sm leading-6 text-zinc-600">
          The folder picker is only for a run outside this repository. The normal
          path is generated runs served by Vite from the repo.
        </p>
        <button
          type="button"
          onClick={onOpen}
          className="inline-flex h-11 items-center gap-2 border-2 border-zinc-950 px-4 text-sm font-semibold transition hover:bg-zinc-950 hover:text-white focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2"
        >
          {isLoadingRun ? (
            <RefreshCw size={18} className="animate-spin" />
          ) : (
            <FolderOpen size={18} />
          )}
          Import external run
        </button>
      </div>
    </section>
  );
}

function RunStatus({ lineage, rootName }: { lineage: RunLineage; rootName: string }) {
  const status = lineage.status ?? "unknown";
  const passed = status === "passed_visual_gate";

  return (
    <div className="flex items-center gap-3 border-2 border-zinc-950 px-3 py-2 text-sm">
      {passed ? (
        <CheckCircle2 className="text-teal-700" size={18} />
      ) : (
        <AlertCircle className="text-amber-700" size={18} />
      )}
      <span className="font-mono">{rootName}</span>
      <span className="h-5 border-l border-zinc-400" />
      <span>{status}</span>
    </div>
  );
}

function ArtifactRail({
  agentInvocations,
  artifacts,
  files,
  selectedPath,
  stageRows,
  onSelect,
}: {
  agentInvocations: AgentInvocation[];
  artifacts: ArtifactSummary[];
  files: Map<string, RunArtifact>;
  selectedPath: string | null;
  stageRows: StageRow[];
  onSelect: (path: string) => void;
}) {
  return (
    <aside className="border-b-2 border-zinc-950 bg-white lg:min-h-0 lg:overflow-auto lg:border-b-0 lg:border-r-2">
      <AgentInvocationList
        invocations={agentInvocations}
        selectedPath={selectedPath}
        onSelectPath={onSelect}
      />

      <div className="border-b-2 border-zinc-950 px-4 py-3">
        <div className="flex items-center gap-2">
          <ClipboardList size={17} className="text-teal-700" />
          <h2 className="text-sm font-semibold uppercase tracking-[0.16em]">
            Artifact plan
          </h2>
        </div>
      </div>

      <div className="border-b border-zinc-200 px-4 py-3">
        <div className="space-y-1">
          {["01-eda-framer/output.json", "06-synthesis/report.md", "lineage.json"]
            .filter((path) => files.has(path))
            .map((path) => (
              <FileButton
                key={path}
                path={path}
                label={labelForPath(path)}
                active={path === selectedPath}
                onSelect={onSelect}
              />
            ))}
        </div>
      </div>

      {artifacts.length === 0 ? (
        <p className="px-4 py-4 text-sm text-zinc-500">No planned artifacts found.</p>
      ) : (
        <ol>
          {artifacts.map((artifact, index) => (
            <ArtifactPlanRow
              key={artifact.id}
              index={index}
              artifact={artifact}
              files={files}
              selectedPath={selectedPath}
              onSelect={onSelect}
            />
          ))}
        </ol>
      )}

      <RawStageList rows={stageRows} selectedPath={selectedPath} onSelect={onSelect} />
    </aside>
  );
}

function ArtifactPlanRow({
  artifact,
  index,
  files,
  selectedPath,
  onSelect,
}: {
  artifact: ArtifactSummary;
  index: number;
  files: Map<string, RunArtifact>;
  selectedPath: string | null;
  onSelect: (path: string) => void;
}) {
  const attempt = latestAttempt(artifact);
  const entryPath = firstReviewPath(artifact);
  const pathButtons = [
    ["chart", attempt?.paths.renderImage],
    ["review", attempt?.paths.reviewOutput],
    ["context", attempt?.paths.reviewContext],
    ["report", attempt?.paths.report],
    ["query", attempt?.paths.query],
  ] as const;

  return (
    <li className="border-b border-zinc-200 px-4 py-4">
      <div className="mb-2 flex items-start gap-3">
        <span className="mt-1 font-mono text-xs text-zinc-500">
          {String(index + 1).padStart(2, "0")}
        </span>
        <div className="min-w-0 flex-1">
          <button
            type="button"
            disabled={!entryPath}
            onClick={() => {
              if (entryPath) onSelect(entryPath);
            }}
            className="block max-w-full truncate text-left font-mono text-sm font-semibold hover:text-teal-800 disabled:text-zinc-950 disabled:hover:text-zinc-950"
            title={artifact.id}
          >
            {artifact.id}
          </button>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className={`border px-2 py-0.5 font-mono text-[11px] ${statusClass(artifact.status)}`}>
              {artifact.status}
            </span>
            {attempt ? (
              <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-zinc-500">
                attempt {attempt.number}
              </span>
            ) : null}
          </div>
        </div>
      </div>

      {artifact.plan?.purpose ? (
        <p className="mb-3 text-sm leading-5 text-zinc-700">{artifact.plan.purpose}</p>
      ) : null}

      <div className="grid grid-cols-2 gap-x-3 gap-y-1">
        {pathButtons.map(([label, path]) =>
          path ? (
            <FileButton
              key={label}
              path={path}
              label={label}
              active={path === selectedPath}
              disabled={!files.has(path)}
              onSelect={onSelect}
            />
          ) : null,
        )}
      </div>
    </li>
  );
}

function RawStageList({
  rows,
  selectedPath,
  onSelect,
}: {
  rows: StageRow[];
  selectedPath: string | null;
  onSelect: (path: string) => void;
}) {
  return (
    <details className="border-t-2 border-zinc-950">
      <summary className="cursor-pointer px-4 py-3 font-mono text-xs uppercase tracking-[0.18em] text-zinc-500">
        All files by stage
      </summary>
      <ol>
        {rows.map((stage, index) => {
          const Icon = STAGE_ICONS[stage.id];

          return (
            <li key={stage.id} className="border-t border-zinc-200">
              <div className="flex gap-3 px-4 py-4">
                <span className="font-mono text-xs text-zinc-500">
                  {String(index).padStart(2, "0")}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex items-center gap-2">
                    <Icon size={16} className="text-teal-700" />
                    <p className="truncate text-sm font-semibold">{stage.label}</p>
                  </div>
                  <p className="mb-3 font-mono text-[11px] uppercase tracking-[0.14em] text-zinc-500">
                    {stage.owner}
                  </p>
                  <div className="space-y-1">
                    {stage.artifacts.map((path) => (
                      <FileButton
                        key={path}
                        path={path}
                        active={path === selectedPath}
                        onSelect={onSelect}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </details>
  );
}

function FileButton({
  path,
  label,
  active = false,
  disabled = false,
  onSelect,
}: {
  path: string;
  label?: string;
  active?: boolean;
  disabled?: boolean;
  onSelect: (path: string) => void;
}) {
  const displayLabel = label ?? path.split("/").slice(-2).join("/");

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={() => onSelect(path)}
      className={`block w-full truncate border-l-2 py-1 pl-2 pr-1 text-left font-mono text-xs transition ${
        active
          ? "border-teal-700 bg-teal-50 text-teal-950"
          : "border-transparent text-zinc-600 hover:border-zinc-400 hover:bg-zinc-100 disabled:text-zinc-400 disabled:hover:border-transparent disabled:hover:bg-transparent"
      }`}
      title={path}
    >
      {displayLabel}
    </button>
  );
}

export function ArtifactWorkspace({
  run,
  artifact,
  activeArtifact,
  artifactSummaries,
  path,
  schemaError,
  selectedView,
  onSelect,
}: {
  run: LoadedRun;
  artifact: RunArtifact | undefined;
  activeArtifact: ArtifactSummary | undefined;
  artifactSummaries: ArtifactSummary[];
  path: string | null;
  schemaError: string;
  selectedView: SelectedView | null;
  onSelect: (path: string) => void;
}) {
  const attempt = activeArtifact ? latestAttempt(activeArtifact) : undefined;
  const selectedIsRenderedChart = path === attempt?.paths.renderImage;
  const shouldShowSelectedFile = Boolean(artifact && path && !selectedIsRenderedChart);

  if (schemaError) {
    return (
      <section className="flex min-w-0 flex-col border-b-2 border-zinc-950 bg-zinc-50 lg:min-h-0 lg:border-b-0 lg:border-r-2">
        <SchemaErrorPanel message={schemaError} path={path} />
      </section>
    );
  }

  if (!selectedView || (!artifact && !activeArtifact)) {
    return (
      <section className="grid place-items-center border-b-2 border-zinc-950 bg-zinc-50 lg:min-h-0 lg:border-b-0 lg:border-r-2">
        <p className="text-zinc-500">Select an artifact.</p>
      </section>
    );
  }

  if (selectedView.kind === "run-framer") {
    return (
      <section className="flex min-w-0 flex-col border-b-2 border-zinc-950 bg-zinc-50 lg:min-h-0 lg:border-b-0 lg:border-r-2">
        <RunViewHeader eyebrow="Run plan" title="EDA framer output" />
        <div className="min-h-0 flex-1 overflow-auto p-5">
          <FramerView run={run} artifacts={artifactSummaries} onSelect={onSelect} />
          {artifact && path ? (
            <section className="mt-6 border-t-2 border-zinc-950 pt-5">
              <p className="mb-1 font-mono text-xs uppercase tracking-[0.18em] text-zinc-500">
                Raw framer output
              </p>
              <ArtifactContent artifact={artifact} path={path} />
            </section>
          ) : null}
        </div>
      </section>
    );
  }

  if (
    selectedView.kind === "run-synthesis" ||
    selectedView.kind === "run-lineage" ||
    selectedView.kind === "run-file"
  ) {
    return (
      <section className="flex min-w-0 flex-col border-b-2 border-zinc-950 bg-zinc-50 lg:min-h-0 lg:border-b-0 lg:border-r-2">
        <RunViewHeader eyebrow="Selected run file" title={path ?? selectedView.kind} />
        <div className="min-h-0 flex-1 overflow-auto p-5">
          {artifact && path ? <ArtifactContent artifact={artifact} path={path} /> : null}
        </div>
      </section>
    );
  }

  return (
    <section className="flex min-w-0 flex-col border-b-2 border-zinc-950 bg-zinc-50 lg:min-h-0 lg:border-b-0 lg:border-r-2">
      <div className="border-b-2 border-zinc-950 bg-white px-5 py-4">
        <p className="mb-1 font-mono text-xs uppercase tracking-[0.18em] text-zinc-500">
          Review target
        </p>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <h2 className="break-all font-mono text-lg font-semibold">
            {activeArtifact?.id ?? path}
          </h2>
          {activeArtifact ? (
            <span className={`border px-2 py-1 font-mono text-xs ${statusClass(activeArtifact.status)}`}>
              {activeArtifact.status}
            </span>
          ) : null}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto p-5">
        {shouldShowSelectedFile && artifact && path ? (
          <section className="mb-6 border-b-2 border-zinc-950 pb-5">
            <p className="mb-1 font-mono text-xs uppercase tracking-[0.18em] text-zinc-500">
              Selected artifact file
            </p>
            <h3 className="mb-4 break-all font-mono text-base font-semibold">{path}</h3>
            <ArtifactContent artifact={artifact} path={path} />
          </section>
        ) : null}

        {activeArtifact ? (
          <section>
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-[0.16em]">
              Artifact dossier
            </h3>
            <ArtifactEvidence run={run} summary={activeArtifact} attempt={attempt} />
          </section>
        ) : null}
      </div>
    </section>
  );
}

function RunViewHeader({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <div className="border-b-2 border-zinc-950 bg-white px-5 py-4">
      <p className="mb-1 font-mono text-xs uppercase tracking-[0.18em] text-zinc-500">
        {eyebrow}
      </p>
      <h2 className="break-all font-mono text-lg font-semibold">{title}</h2>
    </div>
  );
}

function SchemaErrorPanel({ message, path }: { message: string; path: string | null }) {
  return (
    <div className="p-5">
      <div className="border-l-4 border-red-700 bg-red-50 p-4 text-red-950">
        <p className="mb-2 font-mono text-xs uppercase tracking-[0.18em]">
          Frontend contract failure
        </p>
        <h2 className="mb-3 text-xl font-semibold">Run artifact cannot be rendered.</h2>
        {path ? <p className="mb-3 break-all font-mono text-sm">{path}</p> : null}
        <p className="text-sm leading-6">{message}</p>
      </div>
    </div>
  );
}

function FramerView({
  run,
  artifacts,
  onSelect,
}: {
  run: LoadedRun;
  artifacts: ArtifactSummary[];
  onSelect: (path: string) => void;
}) {
  const framer = readFramerOutput(run);

  return (
    <div className="space-y-6">
      <section>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em]">
          Framing
        </h3>
        <dl className="grid gap-x-4 gap-y-3 border-y-2 border-zinc-950 py-3 text-sm md:grid-cols-[180px_minmax(0,1fr)]">
          <dt className="font-mono text-xs uppercase tracking-[0.14em] text-zinc-500">
            User question
          </dt>
          <dd>{framer.user_question}</dd>
          <dt className="font-mono text-xs uppercase tracking-[0.14em] text-zinc-500">
            Analysis goal
          </dt>
          <dd>{framer.analysis_goal}</dd>
          <dt className="font-mono text-xs uppercase tracking-[0.14em] text-zinc-500">
            Artifact count
          </dt>
          <dd>{framer.artifact_plan.length}</dd>
        </dl>
      </section>

      <section>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em]">
          Artifact plan
        </h3>
        <div className="overflow-x-auto border-y-2 border-zinc-950">
          <table className="min-w-full border-collapse text-left text-sm">
            <thead className="border-b border-zinc-300">
              <tr>
                <th className="px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] text-zinc-500">
                  Artifact
                </th>
                <th className="px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] text-zinc-500">
                  Purpose
                </th>
                <th className="px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] text-zinc-500">
                  Statistical check
                </th>
                <th className="px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] text-zinc-500">
                  Chart
                </th>
              </tr>
            </thead>
            <tbody>
              {framer.artifact_plan.map((item) => {
                const summary = artifacts.find((artifact) => artifact.id === item.id);
                const path = summary ? firstReviewPath(summary) : undefined;
                return (
                  <tr key={item.id} className="border-b border-zinc-200 last:border-b-0">
                    <td className="px-3 py-3 align-top font-mono text-xs">
                      {path ? (
                        <button
                          type="button"
                          onClick={() => onSelect(path)}
                          className="max-w-56 truncate text-left font-mono text-xs font-semibold text-teal-800 underline decoration-teal-700/40 underline-offset-2 hover:text-teal-950"
                          title={item.id}
                        >
                          {item.id}
                        </button>
                      ) : (
                        item.id
                      )}
                    </td>
                    <td className="px-3 py-3 align-top">{item.purpose}</td>
                    <td className="px-3 py-3 align-top">{item.statistical_check}</td>
                    <td className="px-3 py-3 align-top">{item.expected_chart_family}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em]">
          Stop conditions
        </h3>
        <ul className="space-y-2 text-sm leading-6 text-zinc-700">
          {framer.stop_conditions.map((condition) => (
            <li key={condition} className="border-l-2 border-zinc-300 pl-3">
              {condition}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function ArtifactEvidence({
  run,
  summary,
  attempt,
}: {
  run: LoadedRun;
  summary: ArtifactSummary;
  attempt: ArtifactAttemptSummary | undefined;
}) {
  const image =
    attempt?.paths.renderImage !== undefined
      ? run.files.get(attempt.paths.renderImage)
      : undefined;
  const review = readJsonArtifact(run, attempt?.paths.reviewOutput);
  const reviewContext = readJsonArtifact(run, attempt?.paths.reviewContext);
  const resultSummary = readJsonArtifact(run, attempt?.paths.resultSummary);
  const builderOutput = readJsonArtifact(run, attempt?.paths.builderOutput);
  const report = textArtifact(run, attempt?.paths.report);
  const query = textArtifact(run, attempt?.paths.query);

  return (
    <div className="space-y-6">
      <PlanSummary summary={summary} builderOutput={builderOutput} />

      <section>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold uppercase tracking-[0.16em]">
            Rendered evidence
          </h3>
          {attempt ? (
            <span className="font-mono text-xs text-zinc-500">attempt {attempt.number}</span>
          ) : null}
        </div>
        {image?.kind === "image" ? (
          <figure>
            <img
              src={image.url}
              alt={attempt?.paths.renderImage ?? summary.id}
              className="max-h-[56vh] max-w-full border-2 border-zinc-950 bg-white object-contain"
            />
            <figcaption className="mt-2 break-all font-mono text-xs text-zinc-500">
              {attempt?.paths.renderImage} - {formatBytes(image.size)}
            </figcaption>
          </figure>
        ) : (
          <p className="border-l-4 border-amber-700 pl-3 text-sm text-amber-900">
            No rendered chart image was found for this artifact attempt.
          </p>
        )}
      </section>

      {query ? (
        <section>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold uppercase tracking-[0.16em]">
              Builder query
            </h3>
            <span className="break-all font-mono text-xs text-zinc-500">{query.path}</span>
          </div>
          <CodeBlock text={query.text} language="sql" />
        </section>
      ) : null}

      <ResultSummary value={resultSummary} />
      <ReviewDecision value={review} />

      {report ? (
        <section>
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em]">
            Reviewer report
          </h3>
          <CodeBlock text={report.text} language="markdown" />
        </section>
      ) : null}

      <ReviewContextSummary value={reviewContext} />
    </div>
  );
}

function PlanSummary({
  summary,
  builderOutput,
}: {
  summary: ArtifactSummary;
  builderOutput: unknown;
}) {
  const plan = summary.plan;
  const builder = isRecord(builderOutput) ? builderOutput : undefined;

  return (
    <section>
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em]">
        Artifact request
      </h3>
      <dl className="grid gap-x-4 gap-y-3 border-y-2 border-zinc-950 py-3 text-sm md:grid-cols-[180px_minmax(0,1fr)]">
        <dt className="font-mono text-xs uppercase tracking-[0.14em] text-zinc-500">
          Purpose
        </dt>
        <dd>{plan?.purpose ?? "Not recorded."}</dd>
        <dt className="font-mono text-xs uppercase tracking-[0.14em] text-zinc-500">
          Statistical check
        </dt>
        <dd>{plan?.statistical_check ?? "Not recorded."}</dd>
        <dt className="font-mono text-xs uppercase tracking-[0.14em] text-zinc-500">
          Expected chart
        </dt>
        <dd>{plan?.expected_chart_family ?? plan?.artifact_type ?? "Not recorded."}</dd>
        <dt className="font-mono text-xs uppercase tracking-[0.14em] text-zinc-500">
          Required fields
        </dt>
        <dd>{formatList(plan?.required_fields)}</dd>
        <dt className="font-mono text-xs uppercase tracking-[0.14em] text-zinc-500">
          Builder artifact
        </dt>
        <dd>{stringField(builder, "artifact_id") ?? "Not recorded."}</dd>
      </dl>
    </section>
  );
}

function ReviewDecision({ value }: { value: unknown }) {
  const review = isRecord(value) ? value : undefined;
  const verdict = stringField(review, "verdict") ?? "missing";
  const visualAdequacy = stringArrayField(review, "visual_adequacy");
  const statisticalFindings = stringArrayField(review, "statistical_findings");
  const carryForward = stringArrayField(review, "carry_forward_notes");
  const requiredRevision = stringField(review, "required_revision");

  return (
    <section>
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <h3 className="text-sm font-semibold uppercase tracking-[0.16em]">
          Reviewer decision
        </h3>
        <span className={`border px-2 py-1 font-mono text-xs ${statusClass(verdict)}`}>
          {verdict}
        </span>
      </div>

      {!review ? (
        <p className="border-l-4 border-amber-700 pl-3 text-sm text-amber-900">
          No reviewer output JSON was found for this artifact attempt.
        </p>
      ) : (
        <div className="grid gap-5 xl:grid-cols-2">
          <FindingsList title="Visual adequacy" items={visualAdequacy} />
          <FindingsList title="Statistical findings" items={statisticalFindings} />
          <FindingsList title="Carry-forward limits" items={carryForward} />
          <section>
            <h4 className="mb-2 font-mono text-xs uppercase tracking-[0.14em] text-zinc-500">
              Required revision
            </h4>
            <p className="text-sm leading-6 text-zinc-700">
              {requiredRevision && requiredRevision.length > 0 ? requiredRevision : "None."}
            </p>
          </section>
        </div>
      )}
    </section>
  );
}

function FindingsList({ title, items }: { title: string; items: string[] }) {
  return (
    <section>
      <h4 className="mb-2 font-mono text-xs uppercase tracking-[0.14em] text-zinc-500">
        {title}
      </h4>
      {items.length > 0 ? (
        <ul className="space-y-2 text-sm leading-6 text-zinc-700">
          {items.map((item) => (
            <li key={item} className="border-l-2 border-zinc-300 pl-3">
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-zinc-500">None recorded.</p>
      )}
    </section>
  );
}

function ResultSummary({ value }: { value: unknown }) {
  if (!isRecord(value)) return null;

  const rowCount = value.row_count;
  const columns = Array.isArray(value.columns)
    ? value.columns.filter((column): column is string => typeof column === "string")
    : [];

  return (
    <section>
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em]">
        Query result summary
      </h3>
      <dl className="grid gap-x-4 gap-y-2 border-y border-zinc-300 py-3 text-sm md:grid-cols-[160px_minmax(0,1fr)]">
        <dt className="font-mono text-xs uppercase tracking-[0.14em] text-zinc-500">
          Rows
        </dt>
        <dd>{typeof rowCount === "number" ? rowCount : "Not recorded."}</dd>
        <dt className="font-mono text-xs uppercase tracking-[0.14em] text-zinc-500">
          Columns
        </dt>
        <dd>{columns.length > 0 ? columns.join(", ") : "Not recorded."}</dd>
      </dl>
    </section>
  );
}

function ReviewContextSummary({ value }: { value: unknown }) {
  const context = isRecord(value) ? value : undefined;
  if (!context) return null;

  const previousReviews = arrayField(context, "previous_reviews");
  const remainingArtifacts = arrayField(context, "remaining_artifacts");
  const revisionRequest = stringField(context, "revision_request");
  const analysisGoal = stringField(context, "analysis_goal");

  return (
    <section>
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em]">
        Review context
      </h3>
      <dl className="grid gap-x-4 gap-y-2 border-y border-zinc-300 py-3 text-sm md:grid-cols-[180px_minmax(0,1fr)]">
        <dt className="font-mono text-xs uppercase tracking-[0.14em] text-zinc-500">
          Analysis goal
        </dt>
        <dd>{analysisGoal ?? "Not recorded."}</dd>
        <dt className="font-mono text-xs uppercase tracking-[0.14em] text-zinc-500">
          Previous reviews
        </dt>
        <dd>{previousReviews.length}</dd>
        <dt className="font-mono text-xs uppercase tracking-[0.14em] text-zinc-500">
          Remaining artifacts
        </dt>
        <dd>{remainingArtifacts.length}</dd>
        <dt className="font-mono text-xs uppercase tracking-[0.14em] text-zinc-500">
          Revision request
        </dt>
        <dd>{revisionRequest && revisionRequest.length > 0 ? revisionRequest : "None."}</dd>
      </dl>
    </section>
  );
}

function ArtifactContent({ artifact, path }: { artifact: RunArtifact; path: string }) {
  if (artifact.kind === "image") {
    return (
      <figure>
        <img
          src={artifact.url}
          alt={path}
          className="max-h-[72vh] max-w-full border-2 border-zinc-950 bg-white object-contain"
        />
        <figcaption className="mt-3 font-mono text-xs text-zinc-500">
          {formatBytes(artifact.size)}
        </figcaption>
      </figure>
    );
  }

  if (artifact.kind === "binary") {
    return (
      <div className="border-l-4 border-zinc-950 pl-4">
        <p className="mb-2 text-lg font-semibold">Binary artifact</p>
        <p className="font-mono text-sm text-zinc-600">{formatBytes(artifact.size)}</p>
        <p className="mt-4 max-w-xl text-sm leading-6 text-zinc-700">
          Browser-only inspection intentionally does not parse this binary file.
          Use the adjacent summary JSON for table shape and preview rows.
        </p>
      </div>
    );
  }

  if (path.endsWith(".json")) return <JsonView text={artifact.text} />;
  if (path.endsWith(".csv")) return <CsvPreview text={artifact.text} />;
  if (path.endsWith(".sql")) return <CodeBlock text={artifact.text} language="sql" />;
  if (path.endsWith(".md")) return <CodeBlock text={artifact.text} language="markdown" />;

  return <CodeBlock text={artifact.text} language="text" />;
}

function JsonView({ text }: { text: string }) {
  const parsed = safeParseJson(text);
  if (!parsed.ok) return <CodeBlock text={text} language="json" />;
  return <CodeBlock text={JSON.stringify(parsed.value, null, 2)} language="json" />;
}

function CsvPreview({ text }: { text: string }) {
  const rows = text.trim().split(/\r?\n/).slice(0, 12);

  return (
    <div>
      <p className="mb-3 font-mono text-xs uppercase tracking-[0.18em] text-zinc-500">
        First {rows.length} rows
      </p>
      <div className="overflow-x-auto border-2 border-zinc-950 bg-white">
        <table className="min-w-full border-collapse font-mono text-xs">
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={`${row}-${rowIndex}`} className="border-b border-zinc-200 last:border-b-0">
                {row.split(",").map((cell, cellIndex) => (
                  <td
                    key={`${cell}-${cellIndex}`}
                    className={`px-3 py-2 ${
                      rowIndex === 0 ? "bg-zinc-950 font-semibold text-white" : ""
                    }`}
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function CodeBlock({ text, language }: { text: string; language: string }) {
  return (
    <pre className="overflow-auto border-2 border-zinc-950 bg-zinc-950 p-4 font-mono text-xs leading-5 text-zinc-50">
      <code data-language={language}>{text}</code>
    </pre>
  );
}

function EvidencePane({
  run,
  activeArtifact,
  selectedPath,
  onSelect,
}: {
  run: LoadedRun;
  activeArtifact: ArtifactSummary | undefined;
  selectedPath: string | null;
  onSelect: (path: string) => void;
}) {
  const { lineage, files, paths } = run;
  const dependencies =
    selectedPath && lineage.dependencies ? (lineage.dependencies[selectedPath] ?? []) : [];
  const dependents = selectedPath
    ? Object.entries(lineage.dependencies ?? {})
        .filter(([, inputs]) => inputs.includes(selectedPath))
        .map(([path]) => path)
    : [];
  const statuses = artifactStatusEntries(lineage);
  const activeAttempt = activeArtifact ? latestAttempt(activeArtifact) : undefined;
  const activeContext = readJsonArtifact(run, activeAttempt?.paths.reviewContext);

  return (
    <aside className="bg-white lg:min-h-0 lg:overflow-auto">
      <div className="border-b-2 border-zinc-950 px-4 py-4">
        <div className="mb-3 flex items-center gap-2">
          <GitBranch size={17} className="text-teal-700" />
          <h2 className="text-sm font-semibold uppercase tracking-[0.16em]">Lineage</h2>
        </div>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <dt className="text-zinc-500">Files</dt>
          <dd className="font-mono">{paths.length}</dd>
          <dt className="text-zinc-500">Artifacts</dt>
          <dd className="font-mono">{statuses.length}</dd>
          <dt className="text-zinc-500">Status</dt>
          <dd className="font-mono">{lineage.status ?? "unknown"}</dd>
        </dl>
      </div>

      <ArtifactStatusSection
        statuses={statuses}
        activeArtifact={activeArtifact}
        files={files}
        paths={paths}
        onSelect={onSelect}
      />
      <ActiveContextSection value={activeContext} />
      <LinkSection title="Inputs" paths={dependencies} files={files} onSelect={onSelect} />
      <LinkSection title="Used by" paths={dependents} files={files} onSelect={onSelect} />

      <div className="border-t-2 border-zinc-950 px-4 py-4">
        <div className="mb-3 flex items-center gap-2">
          <ListTree size={17} className="text-teal-700" />
          <h3 className="text-sm font-semibold uppercase tracking-[0.16em]">Quick jumps</h3>
        </div>
        <div className="space-y-1">
          {importantPathsForRun(run).map((path) => (
            <FileButton
              key={path}
              path={path}
              label={labelForPath(path)}
              active={path === selectedPath}
              onSelect={onSelect}
            />
          ))}
        </div>
      </div>
    </aside>
  );
}

function ArtifactStatusSection({
  statuses,
  activeArtifact,
  files,
  paths,
  onSelect,
}: {
  statuses: Array<[string, string]>;
  activeArtifact: ArtifactSummary | undefined;
  files: Map<string, RunArtifact>;
  paths: string[];
  onSelect: (path: string) => void;
}) {
  return (
    <section className="border-t border-zinc-200 px-4 py-4">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em]">
        Artifact status
      </h3>
      {statuses.length > 0 ? (
        <div className="space-y-2">
          {statuses.map(([artifactId, status]) => {
            const path = firstPathForArtifactId(artifactId, paths);
            const active = artifactId === activeArtifact?.id;
            return (
              <button
                key={artifactId}
                type="button"
                disabled={!path || !files.has(path)}
                onClick={() => {
                  if (path) onSelect(path);
                }}
                className={`block w-full border-l-2 py-1 pl-2 text-left transition ${
                  active
                    ? "border-teal-700 bg-teal-50"
                    : "border-transparent hover:border-zinc-400 hover:bg-zinc-100"
                } disabled:text-zinc-400 disabled:hover:border-transparent disabled:hover:bg-transparent`}
              >
                <span className="block truncate font-mono text-xs">{artifactId}</span>
                <span className="font-mono text-[11px] text-zinc-500">{status}</span>
              </button>
            );
          })}
        </div>
      ) : (
        <p className="text-sm text-zinc-500">None recorded.</p>
      )}
    </section>
  );
}

function ActiveContextSection({ value }: { value: unknown }) {
  const context = isRecord(value) ? value : undefined;
  const currentArtifact = context?.current_artifact;
  const currentArtifactId = isRecord(currentArtifact)
    ? stringField(currentArtifact, "id")
    : undefined;
  const previousReviews = context ? arrayField(context, "previous_reviews") : [];
  const remainingArtifacts = context ? arrayField(context, "remaining_artifacts") : [];
  const revisionRequest = stringField(context, "revision_request");

  return (
    <section className="border-t border-zinc-200 px-4 py-4">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em]">
        Review context
      </h3>
      {context ? (
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <dt className="text-zinc-500">Current</dt>
          <dd className="min-w-0 truncate font-mono" title={currentArtifactId}>
            {currentArtifactId ?? "n/a"}
          </dd>
          <dt className="text-zinc-500">Previous</dt>
          <dd className="font-mono">{previousReviews.length}</dd>
          <dt className="text-zinc-500">Remaining</dt>
          <dd className="font-mono">{remainingArtifacts.length}</dd>
          <dt className="text-zinc-500">Revision</dt>
          <dd className="min-w-0 truncate" title={revisionRequest}>
            {revisionRequest && revisionRequest.length > 0 ? revisionRequest : "None"}
          </dd>
        </dl>
      ) : (
        <p className="text-sm text-zinc-500">No context selected.</p>
      )}
    </section>
  );
}

function LinkSection({
  title,
  paths,
  files,
  onSelect,
}: {
  title: string;
  paths: string[];
  files: Map<string, RunArtifact>;
  onSelect: (path: string) => void;
}) {
  return (
    <section className="border-t border-zinc-200 px-4 py-4">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-[0.16em]">{title}</h3>
      {paths.length ? (
        <div className="space-y-1">
          {paths.map((path) => (
            <FileButton
              key={path}
              path={path}
              active={false}
              disabled={!files.has(path)}
              onSelect={onSelect}
            />
          ))}
        </div>
      ) : (
        <p className="text-sm text-zinc-500">None recorded.</p>
      )}
    </section>
  );
}

function firstReviewPath(summary: ArtifactSummary): string | undefined {
  const attempt = latestAttempt(summary);
  return (
    attempt?.paths.renderImage ??
    attempt?.paths.reviewOutput ??
    attempt?.paths.reviewContext ??
    attempt?.paths.report ??
    attempt?.paths.query
  );
}

function firstPathForArtifactId(artifactId: string, paths: string[]): string | undefined {
  return (
    paths.find((path) => path === `04-render/${artifactId}/attempt-1/chart.png`) ??
    paths.find(
      (path) =>
        artifactIdForPath(path) === artifactId &&
        path.startsWith("05-visual-reviewer/") &&
        path.endsWith("/output.json"),
    ) ??
    paths.find((path) => artifactIdForPath(path) === artifactId)
  );
}

function artifactStatusEntries(lineage: RunLineage): Array<[string, string]> {
  const statuses = lineage.artifact_statuses;
  if (!isRecord(statuses)) return [];

  return Object.entries(statuses)
    .flatMap(([artifactId, status]) =>
      typeof status === "string" ? ([[artifactId, status]] as Array<[string, string]>) : [],
    )
    .sort(([left], [right]) => left.localeCompare(right));
}

function statusClass(status: string): string {
  if (status === "pass" || status === "passed" || status === "passed_visual_gate") {
    return "border-teal-700 bg-teal-50 text-teal-950";
  }
  if (status === "revise" || status === "revision_requested") {
    return "border-amber-700 bg-amber-50 text-amber-950";
  }
  if (status === "revision_budget_exhausted" || status === "failed") {
    return "border-red-700 bg-red-50 text-red-950";
  }
  return "border-zinc-400 bg-white text-zinc-700";
}

function formatList(value: readonly string[] | undefined): string {
  if (!value || value.length === 0) return "Not recorded.";
  return value.join(", ");
}

function stringField(record: Record<string, unknown> | undefined, key: string): string | undefined {
  const value = record?.[key];
  return typeof value === "string" ? value : undefined;
}

function stringArrayField(record: Record<string, unknown> | undefined, key: string): string[] {
  const value = record?.[key];
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

function arrayField(record: Record<string, unknown>, key: string): unknown[] {
  const value = record[key];
  return Array.isArray(value) ? value : [];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
