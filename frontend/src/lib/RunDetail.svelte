<script>
  import { extractTools } from "./parse.js";
  import CriteriaTable from "./CriteriaTable.svelte";
  import ReportView from "./ReportView.svelte";
  import Timeline from "./Timeline.svelte";
  import ToolFilter from "./ToolFilter.svelte";
  import EventModal from "./EventModal.svelte";

  let { run, config = null } = $props();

  let activeTab = $state("score");
  let selectedEvent = $state(null);
  let activeTools = $state(new Set());
  let showResponses = $state(true);

  let score = $derived(run.score);
  let events = $derived(run.parsedTrace?.events ?? []);
  let tools = $derived(extractTools(events));

  // Reset tool filters when run changes
  $effect(() => {
    activeTools = new Set(tools);
  });

  let filteredEvents = $derived.by(() => {
    if (activeTools.size === tools.length) return events;
    return events.filter((e) => activeTools.has(e.tool));
  });

  function toggleTool(tool) {
    const next = new Set(activeTools);
    if (next.has(tool)) next.delete(tool);
    else next.add(tool);
    activeTools = next;
  }

  const verdictColors = {
    solved: "var(--green)",
    pass: "var(--green)",
    partial: "var(--orange)",
    wrong: "var(--red)",
    failed: "var(--red)",
    run_error: "var(--red)",
  };

  function displayVerdict(verdict) {
    return verdict === "run_error" ? "run error" : verdict;
  }
</script>

<div class="detail">
  <div class="detail-header">
    <div class="run-title">
      <span class="config-name">{run.config}</span>
      <span class="separator">/</span>
      <span class="dataset-name">{run.dataset.replace(/_/g, " ")}</span>
    </div>
    {#if score}
      <span
        class="verdict-badge"
        style="color: {verdictColors[score.verdict] ?? 'var(--text-muted)'}; border-color: {verdictColors[score.verdict] ?? 'var(--border)'}"
      >
        {displayVerdict(score.verdict)}
        {#if score.verdict !== "run_error" && score.core_insight_pass !== undefined}
          &mdash; core insight {score.core_insight_pass ? "pass" : "fail"}
        {/if}
      </span>
    {/if}
  </div>

  {#if score}
    <div class="summary-bar">
      {#if score.verdict === "run_error"}
        <div class="summary-stat">
          <span class="summary-label">Run Status</span>
          <span class="summary-value">run error</span>
        </div>
        <div class="summary-stat">
          <span class="summary-label">Rerun Recommended</span>
          <span class="summary-value">{score.rerun_recommended ? "yes" : "no"}</span>
        </div>
      {:else}
        <div class="summary-stat">
          <span class="summary-label">Required Coverage</span>
          <span class="summary-value">{Math.round((score.required_coverage ?? 0) * 100)}%</span>
        </div>
        <div class="summary-stat">
          <span class="summary-label">Supporting Coverage</span>
          <span class="summary-value">{Math.round((score.supporting_coverage ?? 0) * 100)}%</span>
        </div>
      {/if}
      {#if run.stats?.costUsd !== null}
        <div class="summary-stat">
          <span class="summary-label">Cost</span>
          <span class="summary-value">${run.stats.costUsd.toFixed(2)}</span>
        </div>
      {/if}
      <div class="summary-stat">
        <span class="summary-label">Duration</span>
        <span class="summary-value">{run.stats?.durationFormatted ?? "—"}</span>
      </div>
      <div class="summary-stat">
        <span class="summary-label">Turns</span>
        <span class="summary-value">{run.stats?.numTurns ?? events.length}</span>
      </div>
      {#if score.efficiency}
        <div class="summary-stat">
          <span class="summary-label">Trace Events</span>
          <span class="summary-value">{score.efficiency.trace_events}</span>
        </div>
      {/if}
    </div>
  {/if}

  <nav class="tabs">
    <button class="tab" class:active={activeTab === "score"} onclick={() => (activeTab = "score")}>
      Score
    </button>
    {#if run.report}
      <button class="tab" class:active={activeTab === "report"} onclick={() => (activeTab = "report")}>
        Report
      </button>
    {/if}
    {#if run.plots?.length}
      <button class="tab" class:active={activeTab === "plots"} onclick={() => (activeTab = "plots")}>
        Plots ({run.plots.length})
      </button>
    {/if}
    {#if events.length > 0}
      <button class="tab" class:active={activeTab === "trace"} onclick={() => (activeTab = "trace")}>
        Trace ({events.length})
      </button>
    {/if}
  </nav>

  {#if activeTab === "score" && score}
    {#if score.summary}
      <div class="score-summary" class:run-error-summary={score.verdict === "run_error"}>
        {score.summary}
      </div>
    {/if}
    {#if score.run_error_reasons?.length}
      <div class="run-errors">
        {#each score.run_error_reasons as reason}
          <div>{reason}</div>
        {/each}
      </div>
    {/if}
    {#if score.criterion_results?.length}
      <CriteriaTable criteria={score.criterion_results ?? []} />
    {/if}
  {:else if activeTab === "report" && run.report}
    <ReportView text={run.report} />
  {:else if activeTab === "plots"}
    <div class="plots-grid">
      {#each run.plots as src}
        <div class="plot-item">
          <img {src} alt={src.split("/").pop()} loading="lazy" />
          <span class="plot-label">{src.split("/").pop()}</span>
        </div>
      {/each}
    </div>
  {:else if activeTab === "trace"}
    <div class="trace-controls">
      <ToolFilter
        {tools}
        {activeTools}
        onToggle={toggleTool}
        onSelectAll={() => (activeTools = new Set(tools))}
        onSelectNone={() => (activeTools = new Set())}
      />
      <label class="toggle-label">
        <input type="checkbox" bind:checked={showResponses} />
        Responses
      </label>
    </div>
    <Timeline
      events={filteredEvents}
      allEvents={events}
      {showResponses}
      onSelect={(e) => (selectedEvent = e)}
    />
  {/if}
</div>

{#if selectedEvent}
  <EventModal event={selectedEvent} onClose={() => (selectedEvent = null)} />
{/if}

<style>
  .detail {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .detail-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .run-title {
    display: flex;
    align-items: baseline;
    gap: 8px;
  }

  .config-name {
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--accent);
  }

  .separator {
    color: var(--text-muted);
    opacity: 0.4;
  }

  .dataset-name {
    font-size: 1.2rem;
    font-weight: 600;
    text-transform: capitalize;
  }

  .verdict-badge {
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 4px 12px;
    border: 1px solid;
    border-radius: var(--radius);
  }

  .summary-bar {
    display: flex;
    gap: 2px;
    border-radius: var(--radius-lg);
    overflow: hidden;
  }

  .summary-stat {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 10px 12px;
    background: var(--bg-secondary);
  }

  .summary-stat:first-child {
    border-radius: var(--radius-lg) 0 0 var(--radius-lg);
  }

  .summary-stat:last-child {
    border-radius: 0 var(--radius-lg) var(--radius-lg) 0;
  }

  .summary-label {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
  }

  .summary-value {
    font-size: 1.1rem;
    font-weight: 600;
    font-family: var(--font-mono);
  }

  .tabs {
    display: flex;
    gap: 2px;
    border-bottom: 1px solid var(--border);
  }

  .tab {
    padding: 8px 16px;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--text-muted);
    font-size: 0.9rem;
    transition: all 0.15s;
  }

  .tab:hover {
    color: var(--text);
  }

  .tab.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
  }

  .score-summary {
    padding: 16px;
    background: var(--bg-secondary);
    border-radius: var(--radius-lg);
    font-size: 0.9rem;
    line-height: 1.7;
    color: var(--text-muted);
  }

  .run-errors {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 14px 16px;
    background: color-mix(in srgb, var(--red) 8%, var(--bg-secondary));
    border: 1px solid color-mix(in srgb, var(--red) 40%, var(--border));
    border-radius: var(--radius-lg);
    color: var(--red);
    font-family: var(--font-mono);
    font-size: 0.85rem;
  }

  .run-error-summary {
    background: color-mix(in srgb, var(--red) 8%, var(--bg-secondary));
    border: 1px solid color-mix(in srgb, var(--red) 35%, var(--border));
    color: var(--text);
  }

  .plots-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 12px;
  }

  .plot-item {
    display: flex;
    flex-direction: column;
    gap: 6px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    overflow: hidden;
  }

  .plot-item img {
    width: 100%;
    height: auto;
    display: block;
  }

  .plot-label {
    padding: 6px 12px;
    font-size: 0.75rem;
    font-family: var(--font-mono);
    color: var(--text-muted);
  }

  .trace-controls {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .toggle-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.85rem;
    color: var(--text-muted);
    cursor: pointer;
  }

  .toggle-label input {
    accent-color: var(--accent);
  }
</style>
