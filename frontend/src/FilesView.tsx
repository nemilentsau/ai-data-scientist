import { AlertTriangle } from "lucide-react";

import { FileContent } from "./FileContent";
import { STAGES } from "./runFolder";
import { resolveSelectedView } from "./selectedView";
import type { LoadedRun } from "./types";
import { EmptyNote } from "./ui";

type FileGroup = { id: string; label: string; paths: string[] };

export function FilesView({
  run,
  selectedPath,
  onSelectPath,
}: {
  run: LoadedRun;
  selectedPath: string | null;
  onSelectPath: (path: string) => void;
}) {
  const groups = groupPaths(run.paths);
  const selected = selectedPath ? run.files.get(selectedPath) : undefined;

  return (
    <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[300px_minmax(0,1fr)]">
      <nav className="overflow-auto border-b border-zinc-200 lg:border-b-0 lg:border-r">
        {groups.map((group) => (
          <details key={group.id} open className="border-b border-zinc-100">
            <summary className="cursor-pointer px-4 py-2.5 font-mono text-[11px] uppercase tracking-[0.14em] text-zinc-500">
              {group.label}
            </summary>
            <ul className="pb-2">
              {group.paths.map((path) => (
                <li key={path}>
                  <button
                    type="button"
                    onClick={() => onSelectPath(path)}
                    title={path}
                    className={`block w-full truncate border-l-2 py-1 pl-4 pr-2 text-left font-mono text-xs transition ${
                      path === selectedPath
                        ? "border-teal-500 bg-teal-50 text-teal-900"
                        : "border-transparent text-zinc-600 hover:border-zinc-300 hover:bg-zinc-50"
                    }`}
                  >
                    {path.slice(group.prefixLength)}
                  </button>
                </li>
              ))}
            </ul>
          </details>
        ))}
      </nav>

      <div className="min-w-0 overflow-auto px-8 py-8">
        {selectedPath && selected ? (
          <StrictFile run={run} path={selectedPath} />
        ) : (
          <EmptyNote>Select a file to inspect it.</EmptyNote>
        )}
      </div>
    </div>
  );
}

function StrictFile({ run, path }: { run: LoadedRun; path: string }) {
  const artifact = run.files.get(path);
  if (!artifact) {
    return <ContractFailure path={path} message={`File not present in run: ${path}`} />;
  }

  try {
    // Enforce the backend contract: unknown artifact paths must fail, never fall back.
    resolveSelectedView(run, path);
  } catch (error) {
    return (
      <ContractFailure path={path} message={error instanceof Error ? error.message : String(error)} />
    );
  }

  return (
    <div className="space-y-4">
      <p className="break-all font-mono text-xs text-zinc-400">{path}</p>
      <FileContent artifact={artifact} path={path} />
    </div>
  );
}

function ContractFailure({ path, message }: { path: string; message: string }) {
  return (
    <div className="max-w-2xl space-y-3 border-l-2 border-red-400 bg-red-50/60 p-4">
      <div className="flex items-center gap-2 text-red-800">
        <AlertTriangle size={16} />
        <p className="font-mono text-[11px] uppercase tracking-[0.16em]">Frontend contract failure</p>
      </div>
      <p className="break-all font-mono text-xs text-red-900">{path}</p>
      <p className="text-sm leading-6 text-red-900">{message}</p>
    </div>
  );
}

type GroupWithPrefix = FileGroup & { prefixLength: number };

function groupPaths(paths: string[]): GroupWithPrefix[] {
  const groups: GroupWithPrefix[] = STAGES.map((stage) => ({
    id: stage.id,
    label: stage.label,
    prefixLength: stage.prefix.length,
    paths: paths.filter((path) => path.startsWith(stage.prefix)),
  }));

  const rootPaths = paths.filter((path) => !STAGES.some((stage) => path.startsWith(stage.prefix)));
  if (rootPaths.length > 0) {
    groups.push({ id: "run-root", label: "Run root", prefixLength: 0, paths: rootPaths });
  }

  return groups.filter((group) => group.paths.length > 0);
}
