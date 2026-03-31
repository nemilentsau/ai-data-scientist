<script>
  import manifest from "virtual:manifest";
  import { parseTrace, computeStats } from "./lib/parse.js";
  import RunCard from "./lib/RunCard.svelte";
  import RunDetail from "./lib/RunDetail.svelte";

  let search = $state("");
  let selectedRun = $state(null);
  let filterVerdict = $state("all");

  // Pre-process runs: parse traces, attach computed stats
  let runs = $derived.by(() => {
    return manifest.runs.map((run) => {
      const parsed = run.trace ? parseTrace(run.trace) : { events: [], meta: null };
      const stats = computeStats(parsed.events, parsed.meta);
      return { ...run, parsedTrace: parsed, stats };
    });
  });

  let verdicts = $derived([...new Set(runs.map((r) => r.score?.verdict).filter(Boolean))]);

  let filteredRuns = $derived.by(() => {
    let result = runs;
    if (filterVerdict !== "all") {
      result = result.filter((r) => r.score?.verdict === filterVerdict);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter((r) => {
        const haystack = [
          r.agent,
          r.dataset,
          r.score?.verdict,
          r.score?.summary,
          r.report,
          ...(r.score?.criterion_results?.map((c) => `${c.criterion_id} ${c.justification} ${c.evidence}`) ?? []),
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return haystack.includes(q);
      });
    }
    return result;
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
    {#if runs.length > 0}
      <div class="header-stats">
        <span class="stat-chip">{runs.length} run{runs.length !== 1 ? "s" : ""}</span>
        <span class="stat-chip">{new Set(runs.map((r) => r.agent)).size} agent{new Set(runs.map((r) => r.agent)).size !== 1 ? "s" : ""}</span>
        <span class="stat-chip">{new Set(runs.map((r) => r.dataset)).size} dataset{new Set(runs.map((r) => r.dataset)).size !== 1 ? "s" : ""}</span>
      </div>
    {/if}
  </header>

  {#if selectedRun}
    <RunDetail run={selectedRun} />
  {:else if runs.length === 0}
    <div class="empty">
      <div class="empty-icon">&#128202;</div>
      <p>No benchmark results found</p>
      <p class="hint">Run benchmarks to populate <code>results/</code></p>
    </div>
  {:else}
    <div class="controls">
      <input
        class="search"
        type="text"
        placeholder="Search runs, criteria, reports..."
        bind:value={search}
      />
      <div class="filters">
        <button
          class="filter-btn"
          class:active={filterVerdict === "all"}
          onclick={() => (filterVerdict = "all")}
        >
          All
        </button>
        {#each verdicts as v}
          <button
            class="filter-btn"
            class:active={filterVerdict === v}
            onclick={() => (filterVerdict = v)}
          >
            {v}
          </button>
        {/each}
      </div>
    </div>

    <div class="run-grid">
      {#each filteredRuns as run (run.id)}
        <RunCard {run} onSelect={() => selectRun(run)} />
      {/each}
    </div>

    {#if filteredRuns.length === 0 && search}
      <div class="empty">
        <p>No runs match "{search}"</p>
      </div>
    {/if}
  {/if}
</div>

<style>
  .app {
    max-width: 1200px;
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
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
    align-items: center;
  }

  .search {
    flex: 1;
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

  .filters {
    display: flex;
    gap: 4px;
  }

  .filter-btn {
    padding: 6px 14px;
    font-size: 0.8rem;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text-muted);
    text-transform: capitalize;
    transition: all 0.15s;
  }

  .filter-btn.active {
    background: color-mix(in srgb, var(--accent) 15%, transparent);
    border-color: var(--accent);
    color: var(--accent);
  }

  .run-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 12px;
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
