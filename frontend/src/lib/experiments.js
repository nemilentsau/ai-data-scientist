import { computeStats, parseTrace } from "./parse.js";

const ANALYSIS_BROWSER_CATEGORIES = new Set(["notes", "reports"]);
const ARTIFACT_CATEGORY_ORDER = [
  "notes",
  "reports",
  "plots",
  "generated_code",
  "diagnostics",
  "other",
];

export function buildExperimentView(manifest) {
  const casesById = Object.fromEntries(
    (manifest.cases ?? []).map((caseSummary) => [caseSummary.case_id, caseSummary]),
  );
  const configs = Object.fromEntries(
    (manifest.config_snapshots ?? []).map((snapshot) => [
      snapshot.config_name,
      snapshot.config ?? snapshot,
    ]),
  );
  const evaluationsById = Object.fromEntries(
    (manifest.evaluations ?? []).map((evaluation) => [
      evaluation.evaluation_id,
      evaluation,
    ]),
  );
  const artifactsByCase = groupByCase(manifest.artifacts ?? []);
  const artifactCatalog = buildArtifactCatalog(
    manifest.artifacts ?? [],
    casesById,
    manifest.config_snapshots ?? [],
  );
  const experimentArtifacts = artifactCatalog.filter(
    (artifact) => artifact.role === "synthesis_output" && artifact.scope === "experiment",
  );

  const runs = (manifest.cases ?? [])
    .map((caseSummary) => ({
      id: caseSummary.case_id,
      caseId: caseSummary.case_id,
      workflowRunId: caseSummary.workflow_run_id,
      config: caseSummary.config_name,
      dataset: caseSummary.dataset,
      score: caseSummary.evaluation_id
        ? evaluationsById[caseSummary.evaluation_id] ?? null
        : null,
      artifactCount: artifactsByCase[caseSummary.case_id]?.length ?? 0,
    }))
    .sort((left, right) => {
      const datasetCompare = left.dataset.localeCompare(right.dataset);
      if (datasetCompare !== 0) {
        return datasetCompare;
      }
      return left.config.localeCompare(right.config);
    });

  return {
    configs,
    configNames: Object.keys(configs).sort(),
    datasets: [...new Set(runs.map((run) => run.dataset))].sort(),
    artifactCatalog,
    artifactCategories: artifactBrowserCategories(artifactCatalog),
    artifactDatasets: artifactFilterOptions(
      artifactCatalog.flatMap((artifact) => artifact.datasetLabels),
      "all",
    ),
    artifactConfigs: artifactFilterOptions(
      artifactCatalog.flatMap((artifact) => artifact.configLabels),
      "all",
    ),
    artifactScopes: artifactFilterOptions(
      artifactCatalog.map((artifact) => artifact.scope),
      "all",
    ),
    experimentArtifacts,
    runs,
    runMap: Object.fromEntries(runs.map((run) => [`${run.config}/${run.dataset}`, run])),
  };
}

export async function hydrateCaseDetail(manifest, run, fetcher = fetch) {
  const artifacts = (manifest.artifacts ?? []).filter(
    (artifact) => artifact.case_id === run.caseId,
  );
  const relatedArtifacts = (manifest.artifacts ?? [])
    .filter(
      (artifact) =>
        artifact.role === "synthesis_output" &&
        Array.isArray(artifact.related_case_ids) &&
        artifact.related_case_ids.includes(run.caseId),
    )
    .sort((left, right) =>
      String(left.title ?? left.artifact_id).localeCompare(
        String(right.title ?? right.artifact_id),
      ),
    );
  const scoreArtifact = artifacts.find((artifact) => artifact.type === "score");
  const reportArtifact = artifacts.find((artifact) => artifact.type === "analysis_report");
  const traceArtifact = artifacts.find((artifact) => artifact.type === "trace");
  const sessionArtifact = artifacts.find((artifact) => artifact.type === "session");
  const plotArtifacts = artifacts.filter((artifact) => artifact.type === "plot");

  const [score, report, trace, session] = await Promise.all([
    fetchJson(fetcher, scoreArtifact?.content_url),
    fetchText(fetcher, reportArtifact?.content_url),
    fetchText(fetcher, traceArtifact?.content_url),
    sessionArtifact?.media_type === "application/json"
      ? fetchJson(fetcher, sessionArtifact.content_url)
      : Promise.resolve(null),
  ]);

  const parsedTrace = trace ? parseTrace(trace) : { events: [], meta: null };
  const stats = computeStats(parsedTrace.events, parsedTrace.meta, session);

  return {
    ...run,
    score: score ?? run.score,
    report,
    trace,
    session,
    plots: plotArtifacts.map((artifact) => artifact.content_url),
    parsedTrace,
    stats,
    artifacts,
    relatedArtifacts,
  };
}

export async function hydrateExperimentArtifact(manifest, artifact, fetcher = fetch) {
  return hydrateArtifactDetail(manifest, artifact, fetcher);
}

export async function hydrateArtifactDetail(manifest, artifact, fetcher = fetch) {
  const casesById = Object.fromEntries(
    (manifest.cases ?? []).map((caseSummary) => [caseSummary.case_id, caseSummary]),
  );
  const configSnapshots = manifest.config_snapshots ?? [];
  const normalizedArtifact = enrichArtifact(
    artifact,
    casesById,
    Object.fromEntries(
      configSnapshots.map((snapshot) => [snapshot.config_snapshot_id, snapshot.config_name]),
    ),
  );
  const detailKind = artifactDetailKind(normalizedArtifact);
  let content = null;

  if (detailKind === "json") {
    const payload = await fetchJson(fetcher, normalizedArtifact.content_url);
    content = payload == null ? null : `${JSON.stringify(payload, null, 2)}\n`;
  } else if (detailKind === "markdown") {
    content = stripFrontMatter(await fetchText(fetcher, normalizedArtifact.content_url));
  } else if (detailKind === "text" || detailKind === "code") {
    content = await fetchText(fetcher, normalizedArtifact.content_url);
  }

  return {
    ...normalizedArtifact,
    experimentId: manifest.experiment?.experiment_id ?? null,
    detailKind,
    content,
  };
}

export function filterArtifacts(artifacts, filters = {}) {
  const normalizedQuery = String(filters.query ?? "")
    .trim()
    .toLowerCase();

  return artifacts.filter((artifact) => {
    if (filters.category && filters.category !== "all") {
      if (filters.category === "analysis") {
        if (!ANALYSIS_BROWSER_CATEGORIES.has(artifact.category)) {
          return false;
        }
      } else if (artifact.category !== filters.category) {
        return false;
      }
    }
    if (
      filters.dataset &&
      filters.dataset !== "all" &&
      !artifact.datasetLabels.includes(filters.dataset)
    ) {
      return false;
    }
    if (
      filters.config &&
      filters.config !== "all" &&
      !artifact.configLabels.includes(filters.config)
    ) {
      return false;
    }
    if (filters.scope && filters.scope !== "all" && artifact.scope !== filters.scope) {
      return false;
    }
    if (!normalizedQuery) {
      return true;
    }

    const haystack = [
      artifact.title,
      artifact.summary,
      artifact.path,
      artifact.type,
      artifact.category,
      artifact.scope,
      ...artifact.datasetLabels,
      ...artifact.configLabels,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(normalizedQuery);
  });
}

function buildArtifactCatalog(artifacts, casesById, configSnapshots) {
  const configNameBySnapshotId = Object.fromEntries(
    configSnapshots.map((snapshot) => [snapshot.config_snapshot_id, snapshot.config_name]),
  );

  return [...artifacts]
    .map((artifact) => enrichArtifact(artifact, casesById, configNameBySnapshotId))
    .sort((left, right) => {
      const leftRank = artifactSortRank(left);
      const rightRank = artifactSortRank(right);
      if (leftRank !== rightRank) {
        return leftRank - rightRank;
      }
      const leftTime = Date.parse(left.created_at ?? "");
      const rightTime = Date.parse(right.created_at ?? "");
      const safeLeft = Number.isFinite(leftTime) ? leftTime : 0;
      const safeRight = Number.isFinite(rightTime) ? rightTime : 0;
      if (safeLeft !== safeRight) {
        return safeRight - safeLeft;
      }
      return String(left.title ?? left.artifact_id).localeCompare(
        String(right.title ?? right.artifact_id),
      );
    });
}

function enrichArtifact(artifact, casesById, configNameBySnapshotId) {
  const caseSummary = artifact.case_id ? casesById[artifact.case_id] ?? null : null;
  const relatedCases = (artifact.related_case_ids ?? [])
    .map((caseId) => casesById[caseId])
    .filter(Boolean);
  const datasetLabels = uniqueStrings([
    caseSummary?.dataset,
    ...(artifact.datasets ?? []),
    ...relatedCases.map((relatedCase) => relatedCase.dataset),
  ]);
  const configLabels = uniqueStrings([
    caseSummary?.config_name,
    artifact.config_name,
    ...(artifact.config_names ?? []),
    configNameBySnapshotId[artifact.config_snapshot_id],
    ...relatedCases.map((relatedCase) => relatedCase.config_name),
  ]);
  const scope =
    artifact.scope ??
    (artifact.case_id
      ? "case"
      : artifact.type === "benchmark_report"
        ? "config"
        : "experiment");

  return {
    ...artifact,
    title: artifact.title ?? defaultArtifactTitle(artifact),
    summary: artifact.summary ?? null,
    filename: artifact.path?.split("/").pop() ?? artifact.artifact_id,
    previewText: artifactPreviewText(artifact, datasetLabels, configLabels),
    datasetLabels,
    configLabels,
    scope,
    category: artifactCategory(artifact),
  };
}

function artifactCategory(artifact) {
  if (artifact.role === "synthesis_output") {
    return "notes";
  }
  if (artifact.type === "plot") {
    return "plots";
  }
  if (artifact.type === "generated_code") {
    return "generated_code";
  }
  if (artifact.type === "analysis_report" || artifact.type === "benchmark_report") {
    return "reports";
  }
  if (
    artifact.type === "score" ||
    artifact.type === "trace" ||
    artifact.type === "session"
  ) {
    return "diagnostics";
  }
  return "other";
}

function defaultArtifactTitle(artifact) {
  if (artifact.type === "analysis_report") {
    return "Analysis Report";
  }
  if (artifact.type === "benchmark_report") {
    return "Benchmark Report";
  }
  if (artifact.type === "score") {
    return "Score";
  }
  if (artifact.type === "trace") {
    return "Trace";
  }
  if (artifact.type === "session") {
    return "Session";
  }
  if (artifact.type === "final_message") {
    return "Final Message";
  }
  return artifact.path?.split("/").pop() ?? artifact.artifact_id;
}

function artifactDetailKind(artifact) {
  if (artifact.media_type?.startsWith("image/")) {
    return "image";
  }
  if (artifact.media_type === "application/json") {
    return "json";
  }
  if (artifact.media_type === "text/markdown") {
    return "markdown";
  }
  if (
    artifact.media_type === "text/x-python" ||
    artifact.path?.endsWith(".py")
  ) {
    return "code";
  }
  if (
    artifact.media_type?.startsWith("text/") ||
    artifact.media_type === "application/x-ndjson"
  ) {
    return "text";
  }
  return "binary";
}

function artifactBrowserCategories(artifacts) {
  const present = uniqueStrings(artifacts.map((artifact) => artifact.category));
  const ordered = [];

  if (present.some((category) => ANALYSIS_BROWSER_CATEGORIES.has(category))) {
    ordered.push("analysis");
  }

  for (const category of ARTIFACT_CATEGORY_ORDER) {
    if (present.includes(category)) {
      ordered.push(category);
    }
  }

  return ["all", ...ordered];
}

function artifactFilterOptions(values, fallback) {
  return [fallback, ...uniqueStrings(values).sort()];
}

function artifactSortRank(artifact) {
  const index = ARTIFACT_CATEGORY_ORDER.indexOf(artifact.category);
  return index === -1 ? ARTIFACT_CATEGORY_ORDER.length : index;
}

function artifactPreviewText(artifact, datasetLabels, configLabels) {
  const context = artifactContext(datasetLabels, configLabels);

  if (artifact.summary) {
    return artifact.summary;
  }
  if (artifact.type === "plot") {
    return context ? `Plot output for ${context}.` : "Plot output.";
  }
  if (artifact.type === "generated_code") {
    return context ? `Generated Python artifact for ${context}.` : "Generated Python artifact.";
  }
  if (artifact.type === "analysis_report") {
    return context ? `Analysis report for ${context}.` : "Analysis report.";
  }
  if (artifact.type === "benchmark_report") {
    return context ? `Benchmark report for ${context}.` : "Benchmark report.";
  }
  if (artifact.type === "score") {
    return context ? `Structured score output for ${context}.` : "Structured score output.";
  }
  if (artifact.type === "trace") {
    return context ? `Execution trace for ${context}.` : "Execution trace.";
  }
  if (artifact.type === "session") {
    return context ? `Session metadata for ${context}.` : "Session metadata.";
  }
  if (artifact.type === "final_message") {
    return context ? `Final model message for ${context}.` : "Final model message.";
  }

  return artifact.filename ?? artifact.path?.split("/").pop() ?? artifact.artifact_id;
}

function artifactContext(datasetLabels, configLabels) {
  const datasets = datasetLabels.join(", ");
  const configs = configLabels.join(", ");

  if (datasets && configs) {
    return `${datasets} / ${configs}`;
  }
  return datasets || configs || "";
}

function uniqueStrings(values) {
  return [...new Set(values.filter(Boolean).map((value) => String(value)))];
}

async function fetchJson(fetcher, url) {
  if (!url) {
    return null;
  }
  const response = await fetcher(url);
  return response.json();
}

async function fetchText(fetcher, url) {
  if (!url) {
    return null;
  }
  const response = await fetcher(url);
  return response.text();
}

function groupByCase(artifacts) {
  const grouped = {};
  for (const artifact of artifacts) {
    if (!artifact.case_id) {
      continue;
    }
    grouped[artifact.case_id] ??= [];
    grouped[artifact.case_id].push(artifact);
  }
  return grouped;
}

function stripFrontMatter(text) {
  if (!text?.startsWith("---\n")) {
    return text;
  }
  const closingIndex = text.indexOf("\n---\n", 4);
  if (closingIndex === -1) {
    return text;
  }
  return text.slice(closingIndex + 5);
}
