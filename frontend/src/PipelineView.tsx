import type { AgentInvocation } from "./agentInvocations";
import { humanizeId } from "./format";
import { labelForPath } from "./runFolder";
import { Eyebrow, SectionTitle } from "./ui";

export function PipelineView({
  invocations,
  selectedPath,
  onSelectPath,
}: {
  invocations: AgentInvocation[];
  selectedPath: string | null;
  onSelectPath: (path: string) => void;
}) {
  return (
    <div className="mx-auto max-w-4xl space-y-6 px-8 py-10">
      <header className="space-y-2">
        <Eyebrow>pipeline</Eyebrow>
        <SectionTitle>Ordered agent runs</SectionTitle>
        <p className="max-w-2xl text-sm leading-6 text-zinc-500">
          The framer, every builder attempt, and every reviewer attempt, in execution order. Full
          step-level traces will move to Opik / Langfuse.
        </p>
      </header>

      <ol>
        {invocations.map((invocation, index) => {
          const isLast = index === invocations.length - 1;
          return (
            <li key={invocation.id} className="flex gap-4">
              <div className="flex flex-col items-center">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-zinc-300 bg-white font-mono text-xs text-zinc-500">
                  {String(index + 1).padStart(2, "0")}
                </span>
                {isLast ? null : <span className="my-1 w-px flex-1 bg-zinc-200" />}
              </div>

              <div className="min-w-0 flex-1 pb-8">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <span className="text-sm font-semibold text-zinc-950">{invocation.label}</span>
                  {invocation.artifactId ? (
                    <span className="font-mono text-xs text-zinc-500">
                      {humanizeId(invocation.artifactId)}
                    </span>
                  ) : null}
                  {invocation.attempt ? (
                    <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-zinc-400">
                      attempt {invocation.attempt}
                    </span>
                  ) : null}
                </div>

                <div className="mt-3 grid gap-4 sm:grid-cols-2">
                  <PathList
                    label="Inputs"
                    paths={invocation.inputPaths}
                    selectedPath={selectedPath}
                    onSelectPath={onSelectPath}
                  />
                  <PathList
                    label="Outputs"
                    paths={invocation.outputPaths}
                    selectedPath={selectedPath}
                    onSelectPath={onSelectPath}
                  />
                </div>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function PathList({
  label,
  paths,
  selectedPath,
  onSelectPath,
}: {
  label: string;
  paths: string[];
  selectedPath: string | null;
  onSelectPath: (path: string) => void;
}) {
  return (
    <div className="space-y-1.5">
      <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-zinc-400">{label}</p>
      {paths.length > 0 ? (
        <ul className="space-y-1">
          {paths.map((path) => (
            <li key={path}>
              <button
                type="button"
                onClick={() => onSelectPath(path)}
                title={path}
                className={`block w-full truncate border-l-2 pl-2 text-left font-mono text-xs transition ${
                  path === selectedPath
                    ? "border-teal-500 text-teal-800"
                    : "border-transparent text-zinc-600 hover:border-zinc-300 hover:text-zinc-900"
                }`}
              >
                {labelForPath(path)}
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-zinc-400">None</p>
      )}
    </div>
  );
}
