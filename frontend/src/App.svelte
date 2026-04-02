<script>
  import { onMount } from "svelte";
  import ComparisonMatrix from "./lib/ComparisonMatrix.svelte";
  import ArtifactDetail from "./lib/ArtifactDetail.svelte";
  import RunDetail from "./lib/RunDetail.svelte";
  import {
    buildExperimentView,
    filterArtifacts,
    hydrateArtifactDetail,
    hydrateCaseDetail,
  } from "./lib/experiments.js";

  let experimentsPayload = $state({ experiments: [] });
  let selectedExperimentId = $state("");
  let experimentManifest = $state(null);
  let selectedRun = $state(null);
  let selectedArtifact = $state(null);
  let activeSection = $state("overview");
  let search = $state("");
  let artifactQuery = $state("");
  let artifactCategory = $state("analysis");
  let artifactDataset = $state("all");
  let artifactConfig = $state("all");
  let artifactVisibleCount = $state(12);
  let loading = $state(true);
  let experimentLoading = $state(false);
  let detailLoading = $state(false);
  let error = $state("");

  onMount(() => {
    void refreshExperiments();
  });

  async function refreshExperiments() {
    loading = true;
    error = "";
    try {
      const res = await fetch("/api/experiments.json");
      if (!res.ok) {
        throw new Error(`Failed to load experiments (${res.status})`);
      }
      experimentsPayload = await res.json();

      const availableExperiments = experimentsPayload.experiments ?? [];
      if (availableExperiments.length === 0) {
        selectedExperimentId = "";
        experimentManifest = null;
        selectedRun = null;
        selectedArtifact = null;
        activeSection = "overview";
        resetArtifactFilters();
        return;
      }

      const nextExperimentId = availableExperiments.some(
        (experiment) => experiment.experiment_id === selectedExperimentId,
      )
        ? selectedExperimentId
        : availableExperiments[0].experiment_id;

      if (nextExperimentId !== selectedExperimentId || experimentManifest == null) {
        selectedExperimentId = nextExperimentId;
        await loadExperiment(nextExperimentId);
      }
    } catch (err) {
      error = err instanceof Error ? err.message : "Failed to load experiments";
    } finally {
      loading = false;
    }
  }

  async function loadExperiment(experimentId) {
    experimentLoading = true;
    error = "";
    selectedRun = null;
    selectedArtifact = null;
    try {
      const res = await fetch(`/api/experiments/${encodeURIComponent(experimentId)}.json`);
      if (!res.ok) {
        throw new Error(`Failed to load experiment ${experimentId} (${res.status})`);
      }
      experimentManifest = await res.json();
    } catch (err) {
      experimentManifest = null;
      error = err instanceof Error ? err.message : "Failed to load experiment";
    } finally {
      experimentLoading = false;
    }
  }

  async function handleExperimentChange(event) {
    const experimentId = event.currentTarget.value;
    if (!experimentId || experimentId === selectedExperimentId) {
      return;
    }
    selectedExperimentId = experimentId;
    search = "";
    activeSection = "overview";
    resetArtifactFilters();
    await loadExperiment(experimentId);
  }

  async function selectRun(runSummary) {
    if (experimentManifest == null) {
      return;
    }
    detailLoading = true;
    error = "";
    selectedArtifact = null;
    try {
      selectedRun = await hydrateCaseDetail(experimentManifest, runSummary);
    } catch (err) {
      error = err instanceof Error ? err.message : "Failed to load case detail";
    } finally {
      detailLoading = false;
    }
  }

  async function selectArtifact(artifactSummary) {
    if (experimentManifest == null) {
      return;
    }
    detailLoading = true;
    error = "";
    selectedRun = null;
    try {
      selectedArtifact = await hydrateArtifactDetail(experimentManifest, artifactSummary);
    } catch (err) {
      error = err instanceof Error ? err.message : "Failed to load artifact";
    } finally {
      detailLoading = false;
    }
  }

  function goBack() {
    selectedRun = null;
    selectedArtifact = null;
  }

  function resetArtifactFilters() {
    artifactQuery = "";
    artifactCategory = "analysis";
    artifactDataset = "all";
    artifactConfig = "all";
    artifactVisibleCount = 12;
  }

  function showMoreArtifacts() {
    artifactVisibleCount += 12;
  }

  let experimentView = $derived.by(() =>
    experimentManifest
      ? buildExperimentView(experimentManifest)
      : {
          configs: {},
          configNames: [],
          datasets: [],
          artifactCatalog: [],
          artifactCategories: ["all"],
          artifactDatasets: ["all"],
          artifactConfigs: ["all"],
          artifactScopes: ["all"],
          experimentArtifacts: [],
          runs: [],
          runMap: {},
        },
  );

  let selectedExperiment = $derived.by(() =>
    (experimentsPayload.experiments ?? []).find(
      (experiment) => experiment.experiment_id === selectedExperimentId,
    ) ?? null,
  );

  let filteredDatasets = $derived.by(() => {
    if (!search.trim()) {
      return experimentView.datasets;
    }
    const query = search.toLowerCase();
    return experimentView.datasets.filter((dataset) => {
      if (dataset.toLowerCase().includes(query)) {
        return true;
      }
      for (const configName of experimentView.configNames) {
        const run = experimentView.runMap[`${configName}/${dataset}`];
        if (!run) {
          continue;
        }
        const haystack = [
          run.score?.verdict,
          run.score?.summary,
          run.config,
          run.dataset,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        if (haystack.includes(query)) {
          return true;
        }
      }
      return false;
    });
  });

  let filteredArtifacts = $derived.by(() =>
    filterArtifacts(experimentView.artifactCatalog, {
      query: artifactQuery,
      category: artifactCategory,
      dataset: artifactDataset,
      config: artifactConfig,
    }),
  );

  let visibleArtifacts = $derived.by(() =>
    filteredArtifacts.slice(0, artifactVisibleCount),
  );

  let verdictCounts = $derived.by(() => {
    const counts = { solved: 0, partial: 0, wrong: 0, failed: 0, run_error: 0 };
    let scored = 0;
    for (const run of experimentView.runs) {
      const v = run.score?.verdict;
      if (v && v in counts) {
        counts[v]++;
        scored++;
      }
    }
    return { ...counts, scored };
  });

  let totalCost = $derived.by(() => {
    let cost = 0;
    for (const run of experimentView.runs) {
      cost += run.stats?.costUsd ?? 0;
    }
    return cost;
  });
</script>

<div class="app">
  <header>
    <div class="header-left">
      {#if selectedRun || selectedArtifact}
        <button class="back-btn" onclick={goBack} aria-label="Go back">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M10 12L6 8l4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
      {/if}
      <div>
        <div class="title-row">
          <h1>Benchmark Dashboard</h1>
          {#if selectedExperiment && !selectedRun && !selectedArtifact}
            <span class="title-divider"></span>
            <span class="title-experiment">{selectedExperiment.title}</span>
          {/if}
        </div>
        {#if selectedRun}
          <nav class="breadcrumb">
            <button class="breadcrumb-link" onclick={goBack}>Results</button>
            <span class="breadcrumb-sep">/</span>
            <span class="breadcrumb-current">{selectedRun.config} / {selectedRun.dataset.replace(/_/g, " ")}</span>
          </nav>
        {:else if selectedArtifact}
          <nav class="breadcrumb">
            <button class="breadcrumb-link" onclick={goBack}>Results</button>
            <span class="breadcrumb-sep">/</span>
            <span class="breadcrumb-current">{selectedArtifact.title ?? "Artifact"}</span>
          </nav>
        {/if}
      </div>
    </div>

    <div class="header-actions">
      {#if !selectedRun && !selectedArtifact && experimentsPayload.experiments.length > 0}
        <label class="selector">
          <span>Experiment</span>
          <select value={selectedExperimentId} onchange={handleExperimentChange}>
            {#each experimentsPayload.experiments as experiment}
              <option value={experiment.experiment_id}>
                {experiment.title} ({experiment.experiment_id})
              </option>
            {/each}
          </select>
        </label>
      {/if}
      <button class="refresh-btn" onclick={refreshExperiments}>
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M14 8A6 6 0 1 1 8 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M14 2v4h-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        Refresh
      </button>
    </div>
  </header>

  {#if error}
    <div class="error-banner">{error}</div>
  {/if}

  {#if loading}
    <div class="empty">
      <p>Loading experiments...</p>
    </div>
  {:else if experimentsPayload.experiments.length === 0}
    <div class="empty">
      <div class="empty-icon">&#128202;</div>
      <p>No imported experiments found</p>
      <p class="hint">
        Import legacy results with
        <code>uv run python experiment_import.py --title "Imported benchmark"</code>
      </p>
    </div>
  {:else if experimentLoading}
    <div class="empty">
      <p>Loading experiment...</p>
    </div>
  {:else if selectedRun || selectedArtifact}
    {#if detailLoading}
      <div class="empty">
        <p>Loading detail...</p>
      </div>
    {:else}
      {#if selectedRun}
        <RunDetail
          run={selectedRun}
          config={experimentView.configs[selectedRun.config]}
          onSelectArtifact={selectArtifact}
        />
      {:else if selectedArtifact}
        <ArtifactDetail artifact={selectedArtifact} />
      {/if}
    {/if}
  {:else}
    <section class="dashboard-hero">
      <div class="stats-row">
        <div class="stat-card stat-card--accent">
          <span class="stat-label">Configs</span>
          <span class="stat-value">{experimentView.configNames.length}</span>
        </div>
        <div class="stat-card stat-card--purple">
          <span class="stat-label">Datasets</span>
          <span class="stat-value">{experimentView.datasets.length}</span>
        </div>
        <div class="stat-card stat-card--cyan">
          <span class="stat-label">Cases</span>
          <span class="stat-value">{experimentView.runs.length}</span>
        </div>
        <div class="stat-card stat-card--muted">
          <span class="stat-label">Total Cost</span>
          <span class="stat-value">{totalCost > 0 ? `$${totalCost.toFixed(2)}` : "—"}</span>
        </div>
      </div>

      {#if verdictCounts.scored > 0}
        <div class="verdict-summary">
          <div class="verdict-bar-container">
            <div class="verdict-bar">
              {#if verdictCounts.solved > 0}
                <div
                  class="verdict-segment verdict-solved"
                  style="width: {(verdictCounts.solved / verdictCounts.scored * 100)}%"
                  title="{verdictCounts.solved} solved"
                ></div>
              {/if}
              {#if verdictCounts.partial > 0}
                <div
                  class="verdict-segment verdict-partial"
                  style="width: {(verdictCounts.partial / verdictCounts.scored * 100)}%"
                  title="{verdictCounts.partial} partial"
                ></div>
              {/if}
              {#if verdictCounts.wrong + verdictCounts.failed > 0}
                <div
                  class="verdict-segment verdict-wrong"
                  style="width: {((verdictCounts.wrong + verdictCounts.failed) / verdictCounts.scored * 100)}%"
                  title="{verdictCounts.wrong + verdictCounts.failed} wrong"
                ></div>
              {/if}
              {#if verdictCounts.run_error > 0}
                <div
                  class="verdict-segment verdict-error"
                  style="width: {(verdictCounts.run_error / verdictCounts.scored * 100)}%"
                  title="{verdictCounts.run_error} run errors"
                ></div>
              {/if}
            </div>
          </div>
          <div class="verdict-legend">
            <span class="verdict-item">
              <span class="verdict-dot" style="background: var(--green)"></span>
              <span class="verdict-count">{verdictCounts.solved}</span> solved
            </span>
            <span class="verdict-item">
              <span class="verdict-dot" style="background: var(--orange)"></span>
              <span class="verdict-count">{verdictCounts.partial}</span> partial
            </span>
            <span class="verdict-item">
              <span class="verdict-dot" style="background: var(--red)"></span>
              <span class="verdict-count">{verdictCounts.wrong + verdictCounts.failed}</span> wrong
            </span>
            {#if verdictCounts.run_error > 0}
              <span class="verdict-item">
                <span class="verdict-dot verdict-dot--striped"></span>
                <span class="verdict-count">{verdictCounts.run_error}</span> errors
              </span>
            {/if}
          </div>
        </div>
      {/if}
    </section>

    <div class="workspace-switch">
      <button
        class="workspace-pill"
        class:active={activeSection === "overview"}
        onclick={() => (activeSection = "overview")}
      >
        Results
      </button>
      <button
        class="workspace-pill"
        class:active={activeSection === "artifacts"}
        onclick={() => (activeSection = "artifacts")}
      >
        Artifacts
      </button>
    </div>

    {#if activeSection === "overview"}
      <div class="controls">
        <input
          class="search"
          type="text"
          placeholder="Search datasets and verdict summaries..."
          bind:value={search}
        />
      </div>

      {#if experimentView.experimentArtifacts.length > 0}
        <section class="notes">
          <div class="section-heading">
            <h2>Experiment Notes</h2>
            <span>{experimentView.experimentArtifacts.length}</span>
          </div>
          <div class="notes-grid">
            {#each experimentView.experimentArtifacts as artifact}
              <button class="note-card" onclick={() => selectArtifact(artifact)}>
                <div class="note-type">{artifact.type?.replace(/_/g, " ") ?? "note"}</div>
                <div class="note-title">{artifact.title ?? artifact.artifact_id}</div>
                {#if artifact.summary}
                  <div class="note-summary">{artifact.summary}</div>
                {/if}
              </button>
            {/each}
          </div>
        </section>
      {/if}

      <ComparisonMatrix
        configNames={experimentView.configNames}
        configs={experimentView.configs}
        datasets={filteredDatasets}
        runMap={experimentView.runMap}
        onSelect={selectRun}
      />

      {#if filteredDatasets.length === 0 && search}
        <div class="empty compact-empty">
          <p>No datasets match "{search}"</p>
        </div>
      {/if}
    {:else}
      <section class="artifact-browser">
        <div class="section-heading">
          <div>
            <h2>Artifact Explorer</h2>
            <p class="artifact-browser-copy">
              Use this for raw reports, plots, traces, generated code, and notes. Analysis
              artifacts are shown by default; switch categories when you need lower-level harness
              outputs.
            </p>
          </div>
          <span>{filteredArtifacts.length}</span>
        </div>

        <div class="artifact-controls">
          <input
            class="search artifact-search"
            type="text"
            placeholder="Search artifact titles, summaries, datasets, and configs..."
            bind:value={artifactQuery}
          />

          <div class="artifact-filters">
            <label class="artifact-filter">
              <span>Category</span>
              <select bind:value={artifactCategory}>
                {#each experimentView.artifactCategories as option}
                  <option value={option}>{option.replace(/_/g, " ")}</option>
                {/each}
              </select>
            </label>

            <label class="artifact-filter">
              <span>Dataset</span>
              <select bind:value={artifactDataset}>
                {#each experimentView.artifactDatasets as option}
                  <option value={option}>{option}</option>
                {/each}
              </select>
            </label>

            <label class="artifact-filter">
              <span>Config</span>
              <select bind:value={artifactConfig}>
                {#each experimentView.artifactConfigs as option}
                  <option value={option}>{option}</option>
                {/each}
              </select>
            </label>
          </div>
        </div>

        {#if visibleArtifacts.length > 0}
          <div class="artifact-grid">
            {#each visibleArtifacts as artifact}
              <button class="artifact-card" onclick={() => selectArtifact(artifact)}>
                <div class="artifact-card-top">
                  <span class="artifact-category">{artifact.category.replace(/_/g, " ")}</span>
                  <span class="artifact-scope">{artifact.type.replace(/_/g, " ")}</span>
                </div>
                <div class="artifact-card-title">{artifact.title}</div>
                <div class="artifact-card-summary">{artifact.previewText}</div>
                <div class="artifact-meta-row">
                  {#if artifact.datasetLabels.length > 0}
                    <span class="artifact-chip">{artifact.datasetLabels.join(", ")}</span>
                  {/if}
                  {#if artifact.configLabels.length > 0}
                    <span class="artifact-chip artifact-chip--config">
                      {artifact.configLabels.join(", ")}
                    </span>
                  {/if}
                </div>
              </button>
            {/each}
          </div>
          {#if filteredArtifacts.length > visibleArtifacts.length}
            <div class="artifact-browser-footer">
              <button class="show-more-btn" onclick={showMoreArtifacts}>
                Show {Math.min(12, filteredArtifacts.length - visibleArtifacts.length)} more
              </button>
            </div>
          {/if}
        {:else}
          <div class="empty compact-empty">
            <p>No artifacts match the current filters.</p>
            <p class="hint">Analysis is the default category. Switch to plots, diagnostics, or generated code for raw harness outputs.</p>
          </div>
        {/if}
      </section>
    {/if}
  {/if}
</div>

<style>
  .app {
    max-width: 1440px;
    margin: 0 auto;
    padding: 24px 32px;
  }

  /* ── Header ── */
  header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 28px;
    padding-bottom: 20px;
    border-bottom: 1px solid var(--border);
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .title-row {
    display: flex;
    align-items: baseline;
    gap: 12px;
  }

  h1 {
    font-size: 1.4rem;
    font-weight: 800;
    color: var(--text);
    letter-spacing: -0.02em;
  }

  .title-divider {
    width: 1px;
    height: 16px;
    background: var(--border);
    align-self: center;
  }

  .title-experiment {
    font-size: 0.92rem;
    font-weight: 500;
    color: var(--text-muted);
  }

  .breadcrumb {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 6px;
    font-size: 0.82rem;
  }

  .breadcrumb-link {
    background: none;
    border: none;
    padding: 0;
    color: var(--accent);
    font-weight: 500;
    font-size: inherit;
    font-family: inherit;
    transition: color var(--transition-fast);
  }

  .breadcrumb-link:hover {
    color: var(--accent-hover);
  }

  .breadcrumb-sep {
    color: var(--text-faint);
  }

  .breadcrumb-current {
    color: var(--text-muted);
    font-weight: 500;
    text-transform: capitalize;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .selector {
    display: flex;
    flex-direction: column;
    gap: 5px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
  }

  .selector select {
    min-width: 320px;
    padding: 9px 12px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    font-size: 0.88rem;
    box-shadow: var(--shadow-xs);
    transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
  }

  .selector select:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 10%, transparent);
    outline: none;
  }

  .refresh-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 9px 16px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text-muted);
    font-size: 0.85rem;
    font-weight: 500;
    box-shadow: var(--shadow-xs);
    transition: all var(--transition-fast);
  }

  .refresh-btn:hover {
    color: var(--text);
    border-color: var(--accent);
    background: var(--bg-secondary);
  }

  .back-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    padding: 0;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text-muted);
    box-shadow: var(--shadow-xs);
    transition: all var(--transition-fast);
  }

  .back-btn:hover {
    color: var(--accent);
    border-color: var(--accent);
  }

  .error-banner {
    margin-bottom: 16px;
    padding: 12px 16px;
    border: 1px solid color-mix(in srgb, var(--red) 30%, var(--border));
    border-radius: var(--radius);
    background: var(--red-soft);
    color: var(--red);
    font-weight: 500;
  }

  /* ── Dashboard Hero ── */
  .dashboard-hero {
    display: flex;
    flex-direction: column;
    gap: 16px;
    margin-bottom: 24px;
  }

  .stats-row {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
  }

  .stat-card {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 18px 20px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    border-top: 3px solid var(--border);
    transition: transform var(--transition-fast), box-shadow var(--transition-fast);
  }

  .stat-card:hover {
    transform: translateY(-1px);
    box-shadow: var(--shadow);
  }

  .stat-card--accent { border-top-color: var(--accent); }
  .stat-card--purple { border-top-color: var(--purple); }
  .stat-card--cyan   { border-top-color: var(--cyan); }
  .stat-card--muted  { border-top-color: var(--text-faint); }

  .stat-label {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
  }

  .stat-value {
    font-size: 1.65rem;
    font-weight: 800;
    color: var(--text);
    letter-spacing: -0.03em;
    font-variant-numeric: tabular-nums;
  }

  /* ── Verdict Distribution ── */
  .verdict-summary {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 18px 22px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
  }

  .verdict-bar-container {
    width: 100%;
  }

  .verdict-bar {
    display: flex;
    height: 10px;
    border-radius: 100px;
    overflow: hidden;
    background: var(--bg-tertiary);
    gap: 2px;
  }

  .verdict-segment {
    min-width: 4px;
    border-radius: 100px;
    transition: width 400ms cubic-bezier(0.4, 0, 0.2, 1);
  }

  .verdict-solved  { background: var(--green); }
  .verdict-partial { background: var(--orange); }
  .verdict-wrong   { background: var(--red); }
  .verdict-error   { background: repeating-linear-gradient(-45deg, var(--red), var(--red) 2px, transparent 2px, transparent 5px); }

  .verdict-legend {
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
  }

  .verdict-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.82rem;
    color: var(--text-muted);
    font-weight: 500;
  }

  .verdict-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .verdict-dot--striped {
    background: repeating-linear-gradient(-45deg, var(--red), var(--red) 1.5px, transparent 1.5px, transparent 3px);
  }

  .verdict-count {
    font-weight: 700;
    color: var(--text);
    font-variant-numeric: tabular-nums;
  }

  /* ── Controls ── */
  .controls {
    margin-bottom: 18px;
  }

  .workspace-switch {
    display: inline-flex;
    gap: 2px;
    margin: 0 0 22px;
    padding: 3px;
    border-radius: var(--radius-lg);
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
  }

  .workspace-pill {
    padding: 9px 20px;
    border-radius: var(--radius);
    border: 1px solid transparent;
    background: transparent;
    color: var(--text-muted);
    font-size: 0.82rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    transition: all var(--transition-normal);
  }

  .workspace-pill:hover {
    color: var(--text);
  }

  .workspace-pill.active {
    color: var(--text);
    background: var(--bg-secondary);
    box-shadow: var(--shadow-sm);
    border-color: var(--border-subtle);
  }

  /* ── Notes ── */
  .notes {
    margin: 0 0 28px;
  }

  /* ── Artifact Browser ── */
  .artifact-browser {
    margin: 0 0 28px;
    padding: 24px;
    border: 1px solid var(--border);
    border-radius: var(--radius-xl);
    background: var(--bg-secondary);
    box-shadow: var(--shadow-sm);
  }

  .artifact-controls {
    display: flex;
    flex-direction: column;
    gap: 14px;
    margin-bottom: 20px;
  }

  .artifact-search {
    max-width: none;
  }

  .artifact-filters {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }

  .artifact-browser-copy {
    margin: 8px 0 0;
    max-width: 72ch;
    color: var(--text-muted);
    line-height: 1.55;
    font-size: 0.92rem;
    text-transform: none;
    letter-spacing: normal;
  }

  .artifact-filter {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .artifact-filter span {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
  }

  .artifact-filter select {
    min-width: 0;
    padding: 9px 12px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    font-size: 0.88rem;
    transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
  }

  .artifact-filter select:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 10%, transparent);
    outline: none;
  }

  .artifact-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 14px;
  }

  .artifact-card {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-height: 180px;
    padding: 20px;
    text-align: left;
    border-radius: var(--radius-lg);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    background: var(--bg-secondary);
    box-shadow: var(--shadow-xs);
    transition: all var(--transition-normal);
  }

  .artifact-card:hover {
    transform: translateY(-2px);
    border-color: color-mix(in srgb, var(--accent) 40%, var(--border));
    border-left-color: var(--accent);
    box-shadow: var(--shadow-md);
  }

  .artifact-card-top {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    align-items: center;
    color: var(--text-muted);
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .artifact-category {
    color: var(--accent);
  }

  .artifact-card-title {
    font-size: 0.98rem;
    font-weight: 700;
    line-height: 1.3;
    color: var(--text);
  }

  .artifact-card-summary {
    color: var(--text-muted);
    line-height: 1.55;
    font-size: 0.85rem;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .artifact-meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: auto;
  }

  .artifact-chip {
    padding: 3px 9px;
    border-radius: 999px;
    background: var(--accent-soft);
    color: var(--accent);
    font-size: 0.7rem;
    font-weight: 600;
    line-height: 1.2;
  }

  .artifact-chip--config {
    background: color-mix(in srgb, var(--cyan) 10%, var(--bg));
    color: var(--cyan);
  }

  .artifact-browser-footer {
    display: flex;
    justify-content: center;
    margin-top: 20px;
  }

  .show-more-btn {
    padding: 10px 24px;
    border: 1px solid var(--border);
    border-radius: 999px;
    background: var(--bg-secondary);
    color: var(--accent);
    font-weight: 600;
    font-size: 0.85rem;
    box-shadow: var(--shadow-xs);
    transition: all var(--transition-fast);
  }

  .show-more-btn:hover {
    border-color: var(--accent);
    background: var(--accent-soft);
    box-shadow: var(--shadow-sm);
  }

  /* ── Section Heading ── */
  .section-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;
  }

  .section-heading h2 {
    margin: 0;
    font-size: 0.82rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-muted);
  }

  .section-heading span {
    min-width: 30px;
    padding: 3px 10px;
    border-radius: 999px;
    background: var(--accent-soft);
    color: var(--accent);
    font-size: 0.78rem;
    font-weight: 700;
    text-align: center;
  }

  .notes-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 14px;
  }

  .note-card {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-height: 150px;
    padding: 20px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: var(--radius-lg);
    text-align: left;
    cursor: pointer;
    box-shadow: var(--shadow-xs);
    transition: all var(--transition-normal);
  }

  .note-card:hover {
    transform: translateY(-2px);
    border-color: color-mix(in srgb, var(--accent) 40%, var(--border));
    border-left-color: var(--accent);
    box-shadow: var(--shadow-md);
  }

  .note-type {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--accent);
  }

  .note-title {
    font-size: 1.02rem;
    font-weight: 700;
    line-height: 1.25;
    color: var(--text);
  }

  .note-summary {
    color: var(--text-muted);
    line-height: 1.55;
    font-size: 0.88rem;
  }

  /* ── Search ── */
  .search {
    width: 100%;
    max-width: 440px;
    padding: 10px 14px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    font-size: 0.9rem;
    font-family: inherit;
    outline: none;
    box-shadow: var(--shadow-xs);
    transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
  }

  .search::placeholder {
    color: var(--text-faint);
  }

  .search:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 10%, transparent);
  }

  /* ── Empty States ── */
  .empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 40vh;
    color: var(--text-muted);
    text-align: center;
    gap: 12px;
  }

  .compact-empty {
    min-height: 16vh;
  }

  .empty-icon {
    font-size: 3rem;
    opacity: 0.25;
  }

  .empty code {
    color: var(--accent);
    background: var(--bg-tertiary);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.85rem;
  }

  .hint {
    font-size: 0.82rem;
    color: var(--text-faint);
  }

  @media (max-width: 900px) {
    .app {
      padding: 16px 18px;
    }

    header {
      flex-direction: column;
      align-items: stretch;
    }

    .title-row {
      flex-direction: column;
      gap: 4px;
    }

    .title-divider {
      display: none;
    }

    .header-actions {
      flex-direction: column;
      align-items: stretch;
    }

    .selector select {
      min-width: 0;
      width: 100%;
    }

    .stats-row {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .artifact-filters {
      grid-template-columns: 1fr;
    }
  }
</style>
