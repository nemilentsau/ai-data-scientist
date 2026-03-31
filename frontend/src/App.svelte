<script>
  import manifest from "virtual:manifest";
  import { parseTrace, computeStats } from "./lib/parse.js";
  import ComparisonMatrix from "./lib/ComparisonMatrix.svelte";
  import RunDetail from "./lib/RunDetail.svelte";

  let selectedRun = $state(null);
  let search = $state("");

  // Pre-process runs: parse traces, attach computed stats
  let runs = $derived.by(() => {
    return manifest.runs.map((run) => {
      const parsed = run.trace ? parseTrace(run.trace) : { events: [], meta: null };
      const stats = computeStats(parsed.events, parsed.meta, run.session);
      return { ...run, parsedTrace: parsed, stats };
    });
  });

  let configs = $derived(manifest.configs);
  let configNames = $derived(Object.keys(configs).sort());
  let datasets = $derived([...new Set(runs.map((r) => r.dataset))].sort());

  // Build lookup: { "config/dataset": run }
  let runMap = $derived.by(() => {
    const map = {};
    for (const run of runs) {
      map[run.id] = run;
    }
    return map;
  });

  let filteredDatasets = $derived.by(() => {
    if (!search.trim()) return datasets;
    const q = search.toLowerCase();
    return datasets.filter((ds) => {
      // Search dataset name
      if (ds.toLowerCase().includes(q)) return true;
      // Search across all config runs for this dataset
      for (const cfg of configNames) {
        const run = runMap[`${cfg}/${ds}`];
        if (!run) continue;
        const haystack = [
          run.score?.verdict,
          run.score?.summary,
          run.report,
          ...(run.score?.criterion_results?.map(
            (c) => `${c.criterion_id} ${c.justification} ${c.evidence}`
          ) ?? []),
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        if (haystack.includes(q)) return true;
      }
      return false;
    });
  });

  function selectRun(run) {
    selectedRun = run;
  }

  function goBack() {
    selectedRun = null;
  }
</script>

<div class="app">
  <header>
    <div class="header-left">
      {#if selectedRun}
        <button class="back-btn" onclick={goBack}>&larr;</button>
      {/if}
      <h1>Benchmark Dashboard</h1>
    </div>
    {#if runs.length > 0 && !selectedRun}
      <div class="header-stats">
        <span class="stat-chip">{configNames.length} config{configNames.length !== 1 ? "s" : ""}</span>
        <span class="stat-chip">{datasets.length} dataset{datasets.length !== 1 ? "s" : ""}</span>
        <span class="stat-chip">{runs.length} run{runs.length !== 1 ? "s" : ""}</span>
      </div>
    {/if}
  </header>

  {#if selectedRun}
    <RunDetail run={selectedRun} config={configs[selectedRun.config]} />
  {:else if runs.length === 0}
    <div class="empty">
      <div class="empty-icon">&#128202;</div>
      <p>No benchmark results found</p>
      <p class="hint">Run benchmarks with <code>--config solo-baseline</code> to populate results</p>
    </div>
  {:else}
    <div class="controls">
      <input
        class="search"
        type="text"
        placeholder="Search datasets, criteria, reports..."
        bind:value={search}
      />
    </div>

    <ComparisonMatrix
      {configNames}
      {configs}
      datasets={filteredDatasets}
      {runMap}
      onSelect={selectRun}
    />

    {#if filteredDatasets.length === 0 && search}
      <div class="empty">
        <p>No datasets match "{search}"</p>
      </div>
    {/if}
  {/if}
</div>

<style>
  .app {
    max-width: 1400px;
    margin: 0 auto;
    padding: 16px 24px;
  }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border);
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  h1 {
    font-size: 1.3rem;
    font-weight: 600;
    color: var(--text);
  }

  .back-btn {
    padding: 4px 10px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text-muted);
    font-size: 1rem;
    transition: all 0.15s;
  }

  .back-btn:hover {
    color: var(--text);
    border-color: var(--text-muted);
  }

  .header-stats {
    display: flex;
    gap: 8px;
  }

  .stat-chip {
    font-size: 0.75rem;
    padding: 3px 10px;
    background: var(--bg-tertiary);
    border-radius: 12px;
    color: var(--text-muted);
  }

  .controls {
    margin-bottom: 16px;
  }

  .search {
    width: 100%;
    max-width: 400px;
    padding: 8px 14px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    font-size: 0.9rem;
    font-family: inherit;
    outline: none;
    transition: border-color 0.15s;
  }

  .search::placeholder {
    color: var(--text-muted);
  }

  .search:focus {
    border-color: var(--accent);
  }

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

  .empty-icon {
    font-size: 3rem;
    opacity: 0.3;
  }

  .empty code {
    color: var(--accent);
    background: var(--bg-tertiary);
    padding: 2px 6px;
    border-radius: 4px;
  }

  .hint {
    font-size: 0.8rem;
    opacity: 0.6;
  }
</style>
