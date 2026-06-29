import type { AgentInvocation } from "./agentInvocations";

export function AgentInvocationList({
  invocations,
  selectedPath,
  onSelectPath,
}: {
  invocations: AgentInvocation[];
  selectedPath: string | null;
  onSelectPath: (path: string) => void;
}) {
  return (
    <section className="border-b-2 border-zinc-950">
      <div className="px-4 py-3">
        <h2 className="text-sm font-semibold uppercase tracking-[0.16em]">Agent runs</h2>
      </div>
      {invocations.length === 0 ? (
        <p className="border-t border-zinc-200 px-4 py-3 text-sm text-zinc-500">
          No agent invocations found.
        </p>
      ) : (
        <ol>
          {invocations.map((invocation, index) => (
            <li key={invocation.id} className="border-t border-zinc-200 px-4 py-3">
              <div className="mb-2 flex items-start gap-3">
                <span className="mt-1 font-mono text-xs text-zinc-500">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    <p className="font-mono text-sm font-semibold">{invocation.label}</p>
                    <span className={`border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.12em] ${roleClass(invocation.role)}`}>
                      {invocation.role}
                    </span>
                  </div>
                  <p className="mt-1 break-all font-mono text-[11px] uppercase tracking-[0.12em] text-zinc-500">
                    {invocation.artifactId ? invocation.artifactId : "run scope"}
                    {invocation.attempt ? ` / attempt ${invocation.attempt}` : ""}
                  </p>
                </div>
              </div>
              <PathGroup
                title="Inputs"
                paths={invocation.inputPaths}
                selectedPath={selectedPath}
                onSelectPath={onSelectPath}
                collapsed
              />
              <PathGroup
                title="Outputs"
                paths={invocation.outputPaths}
                selectedPath={selectedPath}
                onSelectPath={onSelectPath}
              />
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function PathGroup({
  title,
  paths,
  selectedPath,
  onSelectPath,
  collapsed = false,
}: {
  title: string;
  paths: string[];
  selectedPath: string | null;
  onSelectPath: (path: string) => void;
  collapsed?: boolean;
}) {
  if (paths.length === 0) return null;

  return (
    <details className="mb-2 last:mb-0" open={!collapsed}>
      <summary className="mb-1 cursor-pointer font-mono text-[11px] uppercase tracking-[0.14em] text-zinc-500">
        {title} ({paths.length})
      </summary>
      <div className="space-y-1">
        {paths.map((path) => (
          <button
            key={path}
            type="button"
            onClick={() => onSelectPath(path)}
            className={`block w-full truncate border-l-2 py-1 pl-2 pr-1 text-left font-mono text-xs transition ${
              path === selectedPath
                ? "border-teal-700 bg-teal-50 text-teal-950"
                : "border-transparent text-zinc-600 hover:border-zinc-400 hover:bg-zinc-100"
            }`}
            title={path}
          >
            {path}
          </button>
        ))}
      </div>
    </details>
  );
}

function roleClass(role: AgentInvocation["role"]): string {
  if (role === "eda_framer") return "border-teal-700 bg-teal-50 text-teal-950";
  if (role === "artifact_builder") return "border-sky-700 bg-sky-50 text-sky-950";
  return "border-amber-700 bg-amber-50 text-amber-950";
}
