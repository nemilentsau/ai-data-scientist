export type RunView =
  | { kind: "overview" }
  | { kind: "artifact"; artifactId: string }
  | { kind: "pipeline" }
  | { kind: "files"; path: string | null };

export function overviewView(): RunView {
  return { kind: "overview" };
}

export function artifactView(artifactId: string): RunView {
  return { kind: "artifact", artifactId };
}

export function pipelineView(): RunView {
  return { kind: "pipeline" };
}

export function filesView(path: string | null): RunView {
  return { kind: "files", path };
}

export function viewKey(view: RunView): string {
  return view.kind === "artifact" ? `artifact:${view.artifactId}` : view.kind;
}
