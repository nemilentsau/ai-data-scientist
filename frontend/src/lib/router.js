/** Minimal hash-based router for the benchmark dashboard. */

/**
 * Parse location.hash into a route descriptor.
 *
 * Supported patterns:
 *   #/{experimentId}
 *   #/{experimentId}/artifacts/{subView}
 *   #/{experimentId}/run/{config}/{dataset}
 *   #/{experimentId}/artifact/{artifactId}
 */
export function parseHash(hash) {
  const raw = (hash || "").replace(/^#\/?/, "");
  if (!raw) return {};

  const parts = raw.split("/").map(decodeURIComponent);
  const experimentId = parts[0];

  if (parts[1] === "run" && parts[2] && parts[3]) {
    return { experimentId, view: "run", config: parts[2], dataset: parts[3] };
  }
  if (parts[1] === "artifact" && parts[2]) {
    return { experimentId, view: "artifact", artifactId: parts[2] };
  }
  if (parts[1] === "artifacts") {
    const subView = parts[2] || "gallery";
    return { experimentId, view: "artifacts", subView };
  }
  return { experimentId, view: "overview" };
}

/**
 * Build a hash string from the current app state.
 * Returns the string without the leading `#`.
 */
export function buildHash({ experimentId, selectedRun, selectedArtifact, activeSection, artifactSubView }) {
  if (!experimentId) return "";

  const eid = encodeURIComponent(experimentId);

  if (selectedRun) {
    return `${eid}/run/${encodeURIComponent(selectedRun.config)}/${encodeURIComponent(selectedRun.dataset)}`;
  }
  if (selectedArtifact) {
    return `${eid}/artifact/${encodeURIComponent(selectedArtifact.artifact_id)}`;
  }
  if (activeSection === "artifacts") {
    return `${eid}/artifacts/${artifactSubView}`;
  }
  return eid;
}
