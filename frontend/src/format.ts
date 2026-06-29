export type StatusTone = "pass" | "revise" | "fail" | "neutral";

export function humanizeId(id: string): string {
  const spaced = id.replace(/[_-]+/g, " ").trim();
  if (spaced.length === 0) return "";
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

export function datasetFromRunId(runId: string): string {
  const slash = runId.indexOf("/");
  return slash === -1 ? runId : runId.slice(0, slash);
}

export function runNameFromId(runId: string): string {
  return runId.split("/").filter(Boolean).at(-1) ?? runId;
}

export function statusTone(status: string): StatusTone {
  if (status === "pass" || status === "passed" || status === "passed_visual_gate") {
    return "pass";
  }
  if (status === "revise" || status === "revision_requested") {
    return "revise";
  }
  if (status === "revision_budget_exhausted" || status === "failed") {
    return "fail";
  }
  return "neutral";
}
