import type { ReactNode } from "react";
import { GitBranch, LayoutDashboard, ListTree } from "lucide-react";

import type { ArtifactSummary } from "./artifactLoop";
import { humanizeId } from "./format";
import { artifactView, filesView, overviewView, pipelineView, type RunView } from "./runView";
import { StatusDot } from "./ui";

export function RunSidebar({
  current,
  summaries,
  onNavigate,
}: {
  current: RunView;
  summaries: ArtifactSummary[];
  onNavigate: (view: RunView) => void;
}) {
  return (
    <aside className="w-60 shrink-0 overflow-auto border-r border-zinc-200 bg-white">
      <nav className="space-y-1 p-3 text-sm">
        <NavItem
          active={current.kind === "overview"}
          icon={<LayoutDashboard size={15} />}
          onClick={() => onNavigate(overviewView())}
        >
          Overview
        </NavItem>

        <div className="pt-4">
          <p className="px-3 pb-1.5 font-mono text-[11px] uppercase tracking-[0.16em] text-zinc-400">
            Charts
          </p>
          {summaries.length > 0 ? (
            <ul>
              {summaries.map((summary) => {
                const active = current.kind === "artifact" && current.artifactId === summary.id;
                return (
                  <li key={summary.id}>
                    <button
                      type="button"
                      onClick={() => onNavigate(artifactView(summary.id))}
                      className={`flex w-full items-center gap-2 rounded-md px-3 py-1.5 text-left transition ${
                        active
                          ? "bg-zinc-100 font-medium text-zinc-950"
                          : "text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900"
                      }`}
                    >
                      <StatusDot status={summary.status} />
                      <span className="truncate">{humanizeId(summary.id)}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="px-3 text-xs text-zinc-400">None</p>
          )}
        </div>

        <div className="mt-4 space-y-1 border-t border-zinc-200 pt-4">
          <NavItem
            active={current.kind === "pipeline"}
            icon={<GitBranch size={15} />}
            onClick={() => onNavigate(pipelineView())}
          >
            Pipeline
          </NavItem>
          <NavItem
            active={current.kind === "files"}
            icon={<ListTree size={15} />}
            onClick={() => onNavigate(filesView(current.kind === "files" ? current.path : null))}
          >
            Files
          </NavItem>
        </div>
      </nav>
    </aside>
  );
}

function NavItem({
  active,
  icon,
  onClick,
  children,
}: {
  active: boolean;
  icon: ReactNode;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-center gap-2.5 rounded-md px-3 py-1.5 text-left transition ${
        active ? "bg-zinc-100 font-medium text-zinc-950" : "text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900"
      }`}
    >
      <span className={active ? "text-teal-700" : "text-zinc-400"}>{icon}</span>
      {children}
    </button>
  );
}
