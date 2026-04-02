<script>
  import { onMount } from "svelte";
  import ComparisonMatrix from "./lib/ComparisonMatrix.svelte";
  import ArtifactDetail from "./lib/ArtifactDetail.svelte";
  import RunDetail from "./lib/RunDetail.svelte";
  import PlotGallery from "./lib/PlotGallery.svelte";
  import CaseCompare from "./lib/CaseCompare.svelte";
  import CodeInspector from "./lib/CodeInspector.svelte";
  import {
    buildExperimentView,
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
  let artifactSubView = $state("gallery");
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

  let plotArtifacts = $derived.by(() =>
    experimentView.artifactCatalog.filter((a) => a.category === "plots"),
  );

  let codeArtifacts = $derived.by(() =>
    experimentView.artifactCatalog.filter((a) => a.category === "generated_code"),
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

<div class="mx-auto max-w-[1440px] px-8 py-6 max-[900px]:px-[18px] max-[900px]:py-4">
  <header class="flex items-start justify-between gap-4 mb-7 pb-5 border-b border-border max-[900px]:flex-col max-[900px]:items-stretch">
    <div class="flex items-center gap-3.5">
      {#if selectedRun || selectedArtifact}
        <button
          class="inline-flex items-center justify-center w-9 h-9 p-0 bg-bg-secondary border border-border rounded-lg text-text-muted shadow-xs transition-all duration-100 ease-out hover:text-accent hover:border-accent"
          onclick={goBack}
          aria-label="Go back"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M10 12L6 8l4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
      {/if}
      <div>
        <div class="flex items-baseline gap-3 max-[900px]:flex-col max-[900px]:gap-1">
          <h1 class="text-[1.4rem] font-extrabold text-text tracking-[-0.02em]">Benchmark Dashboard</h1>
          {#if selectedExperiment && !selectedRun && !selectedArtifact}
            <span class="w-px h-4 bg-border self-center max-[900px]:hidden"></span>
            <span class="text-[0.92rem] font-medium text-text-muted">{selectedExperiment.title}</span>
          {/if}
        </div>
        {#if selectedRun}
          <nav class="flex items-center gap-1.5 mt-1.5 text-[0.82rem]">
            <button class="bg-transparent border-none p-0 text-accent font-medium text-[inherit] font-[inherit] transition-colors duration-100 ease-out hover:text-accent-hover" onclick={goBack}>Results</button>
            <span class="text-text-faint">/</span>
            <span class="text-text-muted font-medium capitalize">{selectedRun.config} / {selectedRun.dataset.replace(/_/g, " ")}</span>
          </nav>
        {:else if selectedArtifact}
          <nav class="flex items-center gap-1.5 mt-1.5 text-[0.82rem]">
            <button class="bg-transparent border-none p-0 text-accent font-medium text-[inherit] font-[inherit] transition-colors duration-100 ease-out hover:text-accent-hover" onclick={goBack}>Results</button>
            <span class="text-text-faint">/</span>
            <span class="text-text-muted font-medium capitalize">{selectedArtifact.title ?? "Artifact"}</span>
          </nav>
        {/if}
      </div>
    </div>

    <div class="flex items-center gap-3 max-[900px]:flex-col max-[900px]:items-stretch">
      {#if !selectedRun && !selectedArtifact && experimentsPayload.experiments.length > 0}
        <label class="flex flex-col gap-[5px] text-[0.7rem] font-semibold uppercase tracking-[0.05em] text-text-muted">
          <span>Experiment</span>
          <select
            class="min-w-[320px] px-3 py-[9px] bg-bg-secondary border border-border rounded-lg text-text text-[0.88rem] shadow-xs transition-[border-color,box-shadow] duration-100 ease-out focus:border-accent focus:shadow-[0_0_0_3px_var(--color-accent)/10] focus:outline-none max-[900px]:min-w-0 max-[900px]:w-full"
            value={selectedExperimentId}
            onchange={handleExperimentChange}
          >
            {#each experimentsPayload.experiments as experiment}
              <option value={experiment.experiment_id}>
                {experiment.title} ({experiment.experiment_id})
              </option>
            {/each}
          </select>
        </label>
      {/if}
      <button
        class="inline-flex items-center gap-1.5 px-4 py-[9px] bg-bg-secondary border border-border rounded-lg text-text-muted text-[0.85rem] font-medium shadow-xs transition-all duration-100 ease-out hover:text-text hover:border-accent"
        onclick={refreshExperiments}
      >
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M14 8A6 6 0 1 1 8 2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M14 2v4h-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        Refresh
      </button>
    </div>
  </header>

  {#if error}
    <div class="mb-4 px-4 py-3 border border-[color-mix(in_srgb,var(--color-red)_30%,var(--color-border))] rounded-lg bg-red-soft text-red font-medium">{error}</div>
  {/if}

  {#if loading}
    <div class="flex flex-col items-center justify-center min-h-[40vh] text-text-muted text-center gap-3">
      <p>Loading experiments...</p>
    </div>
  {:else if experimentsPayload.experiments.length === 0}
    <div class="flex flex-col items-center justify-center min-h-[40vh] text-text-muted text-center gap-3">
      <div class="text-[3rem] opacity-25">&#128202;</div>
      <p>No imported experiments found</p>
      <p class="text-[0.82rem] text-text-faint">
        Import legacy results with
        <code class="text-accent bg-bg-tertiary px-2 py-[2px] rounded font-mono text-[0.85rem]">uv run python experiment_import.py --title "Imported benchmark"</code>
      </p>
    </div>
  {:else if experimentLoading}
    <div class="flex flex-col items-center justify-center min-h-[40vh] text-text-muted text-center gap-3">
      <p>Loading experiment...</p>
    </div>
  {:else if selectedRun || selectedArtifact}
    {#if detailLoading}
      <div class="flex flex-col items-center justify-center min-h-[40vh] text-text-muted text-center gap-3">
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
    <section class="flex flex-col gap-4 mb-6">
      <div class="grid grid-cols-4 gap-3 max-[900px]:grid-cols-2">
        <div class="flex flex-col gap-1.5 px-5 py-[18px] bg-bg-secondary border border-border rounded-xl shadow-sm border-t-[3px] border-t-accent transition-[transform,box-shadow] duration-100 ease-out hover:-translate-y-px hover:shadow">
          <span class="text-[0.72rem] font-semibold uppercase tracking-[0.06em] text-text-muted">Configs</span>
          <span class="text-[1.65rem] font-extrabold text-text tracking-[-0.03em] tabular-nums">{experimentView.configNames.length}</span>
        </div>
        <div class="flex flex-col gap-1.5 px-5 py-[18px] bg-bg-secondary border border-border rounded-xl shadow-sm border-t-[3px] border-t-purple transition-[transform,box-shadow] duration-100 ease-out hover:-translate-y-px hover:shadow">
          <span class="text-[0.72rem] font-semibold uppercase tracking-[0.06em] text-text-muted">Datasets</span>
          <span class="text-[1.65rem] font-extrabold text-text tracking-[-0.03em] tabular-nums">{experimentView.datasets.length}</span>
        </div>
        <div class="flex flex-col gap-1.5 px-5 py-[18px] bg-bg-secondary border border-border rounded-xl shadow-sm border-t-[3px] border-t-cyan transition-[transform,box-shadow] duration-100 ease-out hover:-translate-y-px hover:shadow">
          <span class="text-[0.72rem] font-semibold uppercase tracking-[0.06em] text-text-muted">Cases</span>
          <span class="text-[1.65rem] font-extrabold text-text tracking-[-0.03em] tabular-nums">{experimentView.runs.length}</span>
        </div>
        <div class="flex flex-col gap-1.5 px-5 py-[18px] bg-bg-secondary border border-border rounded-xl shadow-sm border-t-[3px] border-t-text-faint transition-[transform,box-shadow] duration-100 ease-out hover:-translate-y-px hover:shadow">
          <span class="text-[0.72rem] font-semibold uppercase tracking-[0.06em] text-text-muted">Total Cost</span>
          <span class="text-[1.65rem] font-extrabold text-text tracking-[-0.03em] tabular-nums">{totalCost > 0 ? `$${totalCost.toFixed(2)}` : "—"}</span>
        </div>
      </div>

      {#if verdictCounts.scored > 0}
        <div class="flex flex-col gap-3 px-[22px] py-[18px] bg-bg-secondary border border-border rounded-xl shadow-sm">
          <div class="w-full">
            <div class="flex h-2.5 rounded-full overflow-hidden bg-bg-tertiary gap-0.5">
              {#if verdictCounts.solved > 0}
                <div
                  class="min-w-1 rounded-full bg-green transition-[width] duration-[400ms] ease-[cubic-bezier(0.4,0,0.2,1)]"
                  style="width: {(verdictCounts.solved / verdictCounts.scored * 100)}%"
                  title="{verdictCounts.solved} solved"
                ></div>
              {/if}
              {#if verdictCounts.partial > 0}
                <div
                  class="min-w-1 rounded-full bg-orange transition-[width] duration-[400ms] ease-[cubic-bezier(0.4,0,0.2,1)]"
                  style="width: {(verdictCounts.partial / verdictCounts.scored * 100)}%"
                  title="{verdictCounts.partial} partial"
                ></div>
              {/if}
              {#if verdictCounts.wrong + verdictCounts.failed > 0}
                <div
                  class="min-w-1 rounded-full bg-red transition-[width] duration-[400ms] ease-[cubic-bezier(0.4,0,0.2,1)]"
                  style="width: {((verdictCounts.wrong + verdictCounts.failed) / verdictCounts.scored * 100)}%"
                  title="{verdictCounts.wrong + verdictCounts.failed} wrong"
                ></div>
              {/if}
              {#if verdictCounts.run_error > 0}
                <div
                  class="verdict-error-segment min-w-1 rounded-full transition-[width] duration-[400ms] ease-[cubic-bezier(0.4,0,0.2,1)]"
                  style="width: {(verdictCounts.run_error / verdictCounts.scored * 100)}%"
                  title="{verdictCounts.run_error} run errors"
                ></div>
              {/if}
            </div>
          </div>
          <div class="flex gap-5 flex-wrap">
            <span class="flex items-center gap-1.5 text-[0.82rem] text-text-muted font-medium">
              <span class="w-2 h-2 rounded-full shrink-0 bg-green"></span>
              <span class="font-bold text-text tabular-nums">{verdictCounts.solved}</span> solved
            </span>
            <span class="flex items-center gap-1.5 text-[0.82rem] text-text-muted font-medium">
              <span class="w-2 h-2 rounded-full shrink-0 bg-orange"></span>
              <span class="font-bold text-text tabular-nums">{verdictCounts.partial}</span> partial
            </span>
            <span class="flex items-center gap-1.5 text-[0.82rem] text-text-muted font-medium">
              <span class="w-2 h-2 rounded-full shrink-0 bg-red"></span>
              <span class="font-bold text-text tabular-nums">{verdictCounts.wrong + verdictCounts.failed}</span> wrong
            </span>
            {#if verdictCounts.run_error > 0}
              <span class="flex items-center gap-1.5 text-[0.82rem] text-text-muted font-medium">
                <span class="verdict-dot-striped w-2 h-2 rounded-full shrink-0"></span>
                <span class="font-bold text-text tabular-nums">{verdictCounts.run_error}</span> errors
              </span>
            {/if}
          </div>
        </div>
      {/if}
    </section>

    <div class="inline-flex gap-0.5 mb-[22px] p-[3px] rounded-xl bg-bg-tertiary border border-border">
      <button
        class="px-5 py-[9px] rounded-lg border border-transparent bg-transparent text-text-muted text-[0.82rem] font-semibold uppercase tracking-[0.06em] transition-all duration-200 ease-out hover:text-text {activeSection === 'overview' ? '!text-text !bg-bg-secondary !shadow-sm !border-border-subtle' : ''}"
        onclick={() => (activeSection = "overview")}
      >
        Results
      </button>
      <button
        class="px-5 py-[9px] rounded-lg border border-transparent bg-transparent text-text-muted text-[0.82rem] font-semibold uppercase tracking-[0.06em] transition-all duration-200 ease-out hover:text-text {activeSection === 'artifacts' ? '!text-text !bg-bg-secondary !shadow-sm !border-border-subtle' : ''}"
        onclick={() => (activeSection = "artifacts")}
      >
        Artifacts
      </button>
    </div>

    {#if activeSection === "overview"}
      <div class="mb-[18px]">
        <input
          class="w-full max-w-[440px] px-3.5 py-2.5 bg-bg-secondary border border-border rounded-lg text-text text-[0.9rem] font-[inherit] outline-none shadow-xs transition-[border-color,box-shadow] duration-100 ease-out placeholder:text-text-faint focus:border-accent focus:shadow-[0_0_0_3px_var(--color-accent)/10]"
          type="text"
          placeholder="Search datasets and verdict summaries..."
          bind:value={search}
        />
      </div>

      {#if experimentView.experimentArtifacts.length > 0}
        <section class="mb-7">
          <div class="flex items-center justify-between gap-3 mb-4">
            <h2 class="m-0 text-[0.82rem] font-bold uppercase tracking-[0.1em] text-text-muted">Experiment Notes</h2>
            <span class="min-w-[30px] px-2.5 py-[3px] rounded-full bg-accent-soft text-accent text-[0.78rem] font-bold text-center">{experimentView.experimentArtifacts.length}</span>
          </div>
          <div class="grid grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-3.5">
            {#each experimentView.experimentArtifacts as artifact}
              <button class="flex flex-col gap-2.5 min-h-[150px] p-5 bg-bg-secondary border border-border border-l-[3px] border-l-accent rounded-xl text-left cursor-pointer shadow-xs transition-all duration-200 ease-out hover:-translate-y-0.5 hover:border-[color-mix(in_srgb,var(--color-accent)_40%,var(--color-border))] hover:border-l-accent hover:shadow-md" onclick={() => selectArtifact(artifact)}>
                <div class="text-[0.7rem] font-bold uppercase tracking-[0.1em] text-accent">{artifact.type?.replace(/_/g, " ") ?? "note"}</div>
                <div class="text-[1.02rem] font-bold leading-[1.25] text-text">{artifact.title ?? artifact.artifact_id}</div>
                {#if artifact.summary}
                  <div class="text-text-muted leading-[1.55] text-[0.88rem]">{artifact.summary}</div>
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
        <div class="flex flex-col items-center justify-center min-h-[16vh] text-text-muted text-center gap-3">
          <p>No datasets match "{search}"</p>
        </div>
      {/if}
    {:else}
      <section class="mb-7 p-6 border border-border rounded-2xl bg-bg-secondary shadow-sm">
        <div class="flex items-center justify-between gap-4 mb-[22px] flex-wrap">
          <h2 class="text-[0.82rem] font-bold uppercase tracking-[0.1em] text-text-muted m-0">Artifact Explorer</h2>
          <div class="inline-flex gap-0.5 p-[3px] rounded-xl bg-bg-tertiary border border-border">
            <button
              class="inline-flex items-center gap-1.5 px-4 py-[7px] rounded-lg border border-transparent bg-transparent text-text-muted text-[0.8rem] font-semibold transition-all duration-100 ease-out hover:text-text {artifactSubView === 'gallery' ? '!text-text !bg-bg-secondary !shadow-sm !border-border-subtle' : ''}"
              onclick={() => (artifactSubView = "gallery")}
            >
              Gallery
              <span class="text-[0.68rem] font-bold px-1.5 py-px rounded-full bg-[color-mix(in_srgb,var(--color-accent)_8%,var(--color-bg-tertiary))] text-accent tabular-nums {artifactSubView === 'gallery' ? '!bg-accent-soft' : ''}">{plotArtifacts.length}</span>
            </button>
            <button
              class="inline-flex items-center gap-1.5 px-4 py-[7px] rounded-lg border border-transparent bg-transparent text-text-muted text-[0.8rem] font-semibold transition-all duration-100 ease-out hover:text-text {artifactSubView === 'compare' ? '!text-text !bg-bg-secondary !shadow-sm !border-border-subtle' : ''}"
              onclick={() => (artifactSubView = "compare")}
            >
              Compare
            </button>
            <button
              class="inline-flex items-center gap-1.5 px-4 py-[7px] rounded-lg border border-transparent bg-transparent text-text-muted text-[0.8rem] font-semibold transition-all duration-100 ease-out hover:text-text {artifactSubView === 'code' ? '!text-text !bg-bg-secondary !shadow-sm !border-border-subtle' : ''}"
              onclick={() => (artifactSubView = "code")}
            >
              Code
              <span class="text-[0.68rem] font-bold px-1.5 py-px rounded-full bg-[color-mix(in_srgb,var(--color-accent)_8%,var(--color-bg-tertiary))] text-accent tabular-nums {artifactSubView === 'code' ? '!bg-accent-soft' : ''}">{codeArtifacts.length}</span>
            </button>
          </div>
        </div>

        {#if artifactSubView === "gallery"}
          <PlotGallery
            plots={plotArtifacts}
            datasets={experimentView.datasets}
            configs={experimentView.configNames}
          />
        {:else if artifactSubView === "compare"}
          <CaseCompare
            artifactCatalog={experimentView.artifactCatalog}
            datasets={experimentView.datasets}
            configNames={experimentView.configNames}
            runMap={experimentView.runMap}
            onSelectRun={selectRun}
          />
        {:else if artifactSubView === "code"}
          <CodeInspector
            {codeArtifacts}
            datasets={experimentView.datasets}
            configs={experimentView.configNames}
          />
        {/if}
      </section>
    {/if}
  {/if}
</div>

<style>
  /* Repeating gradient patterns that can't be expressed as Tailwind utilities */
  .verdict-error-segment {
    background: repeating-linear-gradient(-45deg, var(--color-red), var(--color-red) 2px, transparent 2px, transparent 5px);
  }
  .verdict-dot-striped {
    background: repeating-linear-gradient(-45deg, var(--color-red), var(--color-red) 1.5px, transparent 1.5px, transparent 3px);
  }
</style>
