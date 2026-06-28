import {
  AlertCircle,
  CheckCircle2,
  Code2,
  Database,
  Eye,
  FileJson,
  FolderOpen,
  GitBranch,
  Image,
  ListTree,
  Table,
  type LucideIcon,
} from "lucide-react";
import { type ChangeEvent, useMemo, useRef, useState } from "react";

import {
  IMPORTANT_ORDER,
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
};

type StageRow = (typeof STAGES)[number] & {
  artifacts: string[];
};

export function App() {
  const pickerRef = useRef<HTMLInputElement>(null);
  const [run, setRun] = useState<LoadedRun | null>(null);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [loadError, setLoadError] = useState("");

  const selected = selectedPath && run ? run.files.get(selectedPath) : undefined;

  const stageRows = useMemo<StageRow[]>(() => {
    if (!run) return [];
    return STAGES.map((stage) => ({
      ...stage,
      artifacts: run.paths.filter((path) => path.startsWith(stage.prefix)),
    }));
  }, [run]);

  async function handleFiles(event: ChangeEvent<HTMLInputElement>): Promise<void> {
    const files = Array.from(event.target.files ?? []);
    if (files.length === 0) return;

    try {
      const parsed = await loadRunFolder(files);
      setRun(parsed);
      setSelectedPath(pickInitialPath(parsed));
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
            {run ? <RunStatus lineage={run.lineage} rootName={run.rootName} /> : null}
            <button
              type="button"
              onClick={openPicker}
              className="inline-flex h-11 items-center gap-2 border-2 border-zinc-950 bg-zinc-950 px-4 text-sm font-semibold text-white transition hover:bg-teal-700 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2"
            >
              <FolderOpen size={18} />
              Open run folder
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
        <EmptyState onOpen={openPicker} />
      ) : (
        <section className="grid min-h-[calc(100vh-82px)] grid-cols-1 lg:grid-cols-[300px_minmax(0,1fr)_360px]">
          <StageRail rows={stageRows} selectedPath={selectedPath} onSelect={setSelectedPath} />
          <ArtifactWorkspace artifact={selected} path={selectedPath} />
          <EvidencePane
            lineage={run.lineage}
            selectedPath={selectedPath}
            files={run.files}
            paths={run.paths}
            onSelect={setSelectedPath}
          />
        </section>
      )}
    </main>
  );
}

function EmptyState({ onOpen }: { onOpen: () => void }) {
  return (
    <section className="grid min-h-[calc(100vh-82px)] place-items-center px-6">
      <div className="max-w-3xl border-l-4 border-zinc-950 pl-6">
        <p className="mb-3 font-mono text-xs uppercase tracking-[0.22em] text-teal-700">
          Select one run directory
        </p>
        <h2 className="mb-4 text-4xl font-semibold tracking-tight">
          Inspect what each role saw and produced.
        </h2>
        <p className="mb-6 max-w-2xl text-lg leading-7 text-zinc-700">
          Open a folder like{" "}
          <code className="font-mono text-sm text-zinc-950">
            runs/eda-artifacts/multimodal/inspectable-smoke
          </code>
          . The app reads the files locally and maps them into execution order,
          role outputs, deterministic harness artifacts, rendered chart, and lineage.
        </p>
        <button
          type="button"
          onClick={onOpen}
          className="inline-flex h-11 items-center gap-2 border-2 border-zinc-950 px-4 text-sm font-semibold transition hover:bg-zinc-950 hover:text-white focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2"
        >
          <FolderOpen size={18} />
          Choose folder
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

function StageRail({
  rows,
  selectedPath,
  onSelect,
}: {
  rows: StageRow[];
  selectedPath: string | null;
  onSelect: (path: string) => void;
}) {
  return (
    <aside className="border-b-2 border-zinc-950 bg-white lg:border-b-0 lg:border-r-2">
      <div className="border-b border-zinc-300 px-4 py-3">
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-zinc-500">
          Execution order
        </p>
      </div>
      <ol>
        {rows.map((stage, index) => {
          const Icon = STAGE_ICONS[stage.id];

          return (
            <li key={stage.id} className="border-b border-zinc-200">
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
                      <ArtifactButton
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
    </aside>
  );
}

function ArtifactButton({
  path,
  active,
  onSelect,
}: {
  path: string;
  active: boolean;
  onSelect: (path: string) => void;
}) {
  const label = path.split("/").slice(-2).join("/");

  return (
    <button
      type="button"
      onClick={() => onSelect(path)}
      className={`block w-full truncate border-l-2 py-1 pl-2 pr-1 text-left font-mono text-xs transition ${
        active
          ? "border-teal-700 bg-teal-50 text-teal-950"
          : "border-transparent text-zinc-600 hover:border-zinc-400 hover:bg-zinc-100"
      }`}
      title={path}
    >
      {label}
    </button>
  );
}

function ArtifactWorkspace({
  artifact,
  path,
}: {
  artifact: RunArtifact | undefined;
  path: string | null;
}) {
  if (!artifact || !path) {
    return (
      <section className="grid place-items-center border-b-2 border-zinc-950 bg-zinc-50 lg:border-b-0 lg:border-r-2">
        <p className="text-zinc-500">Select an artifact.</p>
      </section>
    );
  }

  return (
    <section className="min-w-0 border-b-2 border-zinc-950 bg-zinc-50 lg:border-b-0 lg:border-r-2">
      <div className="border-b-2 border-zinc-950 bg-white px-5 py-4">
        <p className="mb-1 font-mono text-xs uppercase tracking-[0.18em] text-zinc-500">
          Selected artifact
        </p>
        <h2 className="break-all font-mono text-lg font-semibold">{path}</h2>
      </div>
      <div className="h-[calc(100vh-181px)] overflow-auto p-5">
        <ArtifactContent artifact={artifact} path={path} />
      </div>
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
  lineage,
  selectedPath,
  files,
  paths,
  onSelect,
}: {
  lineage: RunLineage;
  selectedPath: string | null;
  files: Map<string, RunArtifact>;
  paths: string[];
  onSelect: (path: string) => void;
}) {
  const dependencies =
    selectedPath && lineage.dependencies ? (lineage.dependencies[selectedPath] ?? []) : [];
  const dependents = selectedPath
    ? Object.entries(lineage.dependencies ?? {})
        .filter(([, inputs]) => inputs.includes(selectedPath))
        .map(([path]) => path)
    : [];

  return (
    <aside className="bg-white">
      <div className="border-b-2 border-zinc-950 px-4 py-4">
        <div className="mb-3 flex items-center gap-2">
          <GitBranch size={17} className="text-teal-700" />
          <h2 className="text-sm font-semibold uppercase tracking-[0.16em]">Lineage</h2>
        </div>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <dt className="text-zinc-500">Artifacts</dt>
          <dd className="font-mono">{paths.length}</dd>
          <dt className="text-zinc-500">Revisions</dt>
          <dd className="font-mono">{lineage.revision_count ?? "n/a"}</dd>
        </dl>
      </div>

      <LinkSection title="Inputs" paths={dependencies} files={files} onSelect={onSelect} />
      <LinkSection title="Used by" paths={dependents} files={files} onSelect={onSelect} />

      <div className="border-t-2 border-zinc-950 px-4 py-4">
        <div className="mb-3 flex items-center gap-2">
          <ListTree size={17} className="text-teal-700" />
          <h3 className="text-sm font-semibold uppercase tracking-[0.16em]">Quick jumps</h3>
        </div>
        <div className="space-y-1">
          {IMPORTANT_ORDER.filter((path) => files.has(path)).map((path) => (
            <button
              key={path}
              type="button"
              onClick={() => onSelect(path)}
              className="block w-full truncate border-l-2 border-transparent py-1 pl-2 text-left font-mono text-xs text-zinc-700 hover:border-teal-700 hover:bg-teal-50"
              title={path}
            >
              {labelForPath(path)}
            </button>
          ))}
        </div>
      </div>
    </aside>
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
            <button
              key={path}
              type="button"
              disabled={!files.has(path)}
              onClick={() => onSelect(path)}
              className="block w-full truncate border-l-2 border-transparent py-1 pl-2 text-left font-mono text-xs text-zinc-700 hover:border-teal-700 hover:bg-teal-50 disabled:text-zinc-400 disabled:hover:border-transparent disabled:hover:bg-transparent"
              title={path}
            >
              {path}
            </button>
          ))}
        </div>
      ) : (
        <p className="text-sm text-zinc-500">None recorded.</p>
      )}
    </section>
  );
}
