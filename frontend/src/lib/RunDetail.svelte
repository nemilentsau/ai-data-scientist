<script>
  import { extractTools } from "./parse.js";
  import CriteriaTable from "./CriteriaTable.svelte";
  import ReportView from "./ReportView.svelte";
  import Timeline from "./Timeline.svelte";
  import ToolFilter from "./ToolFilter.svelte";
  import EventModal from "./EventModal.svelte";

  let { run, config = null, onSelectArtifact = null } = $props();

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
    <div class="header-left">
      <div class="run-title">
        <span class="config-name">{run.config}</span>
        <span class="separator">/</span>
        <span class="dataset-name">{run.dataset.replace(/_/g, " ")}</span>
      </div>
    </div>
    {#if score}
      <span
        class="verdict-badge"
        style="--verdict-color: {verdictColors[score.verdict] ?? 'var(--text-muted)'}"
      >
        <span class="verdict-dot" style="background: {verdictColors[score.verdict] ?? 'var(--text-muted)'}"></span>
        {displayVerdict(score.verdict)}
        {#if score.verdict !== "run_error" && score.core_insight_pass !== undefined}
          <span class="verdict-sep"></span>
          core insight {score.core_insight_pass ? "pass" : "fail"}
        {/if}
      </span>
    {/if}
  </div>

  {#if score}
    <div class="summary-bar">
      {#if score.verdict === "run_error"}
        <div class="summary-stat summary-stat--wide">
          <span class="summary-label">Run Status</span>
          <span class="summary-value summary-value--error">run error</span>
        </div>
        <div class="summary-stat">
          <span class="summary-label">Rerun Recommended</span>
          <span class="summary-value">{score.rerun_recommended ? "yes" : "no"}</span>
        </div>
      {:else}
        {@const reqCov = Math.round((score.required_coverage ?? 0) * 100)}
        {@const supCov = Math.round((score.supporting_coverage ?? 0) * 100)}
        <div class="summary-stat">
          <span class="summary-label">Required Coverage</span>
          <div class="summary-gauge">
            <div class="gauge-track">
              <div class="gauge-fill" style="width: {reqCov}%; background: {reqCov >= 80 ? 'var(--green)' : reqCov >= 50 ? 'var(--orange)' : 'var(--red)'}"></div>
            </div>
            <span class="summary-value">{reqCov}%</span>
          </div>
        </div>
        <div class="summary-stat">
          <span class="summary-label">Supporting Coverage</span>
          <div class="summary-gauge">
            <div class="gauge-track">
              <div class="gauge-fill" style="width: {supCov}%; background: {supCov >= 80 ? 'var(--green)' : supCov >= 50 ? 'var(--orange)' : 'var(--red)'}"></div>
            </div>
            <span class="summary-value">{supCov}%</span>
          </div>
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
    {#if run.relatedArtifacts?.length}
      <button class="tab" class:active={activeTab === "notes"} onclick={() => (activeTab = "notes")}>
        Notes ({run.relatedArtifacts.length})
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
  {:else if activeTab === "notes"}
    <div class="notes-grid">
      {#each run.relatedArtifacts as artifact}
        <button
          class="note-card"
          type="button"
          disabled={onSelectArtifact == null}
          onclick={() => onSelectArtifact?.(artifact)}
        >
          <div class="note-type">{artifact.type?.replace(/_/g, " ") ?? "note"}</div>
          <div class="note-title">{artifact.title ?? artifact.artifact_id}</div>
          {#if artifact.summary}
            <div class="note-summary">{artifact.summary}</div>
          {/if}
        </button>
      {/each}
    </div>
  {/if}
</div>

{#if selectedEvent}
  <EventModal event={selectedEvent} onClose={() => (selectedEvent = null)} />
{/if}

<style>
  .detail {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  /* ── Header ── */
  .detail-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 20px 24px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-xl, 16px);
    box-shadow: var(--shadow-sm);
  }

  .run-title {
    display: flex;
    align-items: baseline;
    gap: 8px;
  }

  .config-name {
    font-size: 0.82rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--accent);
  }

  .separator {
    color: var(--text-muted);
    opacity: 0.25;
  }

  .dataset-name {
    font-size: 1.3rem;
    font-weight: 800;
    text-transform: capitalize;
    letter-spacing: -0.02em;
  }

  .verdict-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 7px 16px;
    border: 1px solid color-mix(in srgb, var(--verdict-color) 30%, var(--border));
    border-radius: 999px;
    white-space: nowrap;
    color: var(--verdict-color);
    background: color-mix(in srgb, var(--verdict-color) 6%, var(--bg-secondary));
  }

  .verdict-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .verdict-sep {
    width: 1px;
    height: 12px;
    background: var(--border);
  }

  /* ── Summary Bar ── */
  .summary-bar {
    display: flex;
    gap: 1px;
    border-radius: var(--radius-lg);
    overflow: hidden;
    border: 1px solid var(--border);
    box-shadow: var(--shadow-sm);
  }

  .summary-stat {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    padding: 16px 12px;
    background: var(--bg-secondary);
  }

  .summary-stat--wide {
    flex: 1.5;
  }

  .summary-stat:first-child {
    border-radius: var(--radius-lg) 0 0 var(--radius-lg);
  }

  .summary-stat:last-child {
    border-radius: 0 var(--radius-lg) var(--radius-lg) 0;
  }

  .summary-label {
    font-size: 0.66rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-faint, var(--text-muted));
  }

  .summary-value {
    font-size: 1.15rem;
    font-weight: 700;
    font-family: var(--font-mono);
    color: var(--text);
    font-variant-numeric: tabular-nums;
  }

  .summary-value--error {
    color: var(--red);
  }

  .summary-gauge {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    max-width: 140px;
  }

  .gauge-track {
    flex: 1;
    height: 6px;
    border-radius: 100px;
    background: var(--bg-tertiary);
    overflow: hidden;
  }

  .gauge-fill {
    height: 100%;
    border-radius: 100px;
    transition: width 400ms cubic-bezier(0.4, 0, 0.2, 1);
  }

  /* ── Tabs ── */
  .tabs {
    display: flex;
    gap: 0;
    border-bottom: 2px solid var(--border);
  }

  .tab {
    padding: 11px 20px;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
    color: var(--text-muted);
    font-size: 0.88rem;
    font-weight: 500;
    transition: all var(--transition-fast, 120ms ease);
    position: relative;
  }

  .tab:hover {
    color: var(--text);
    background: color-mix(in srgb, var(--accent) 3%, transparent);
  }

  .tab.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
    font-weight: 600;
  }

  /* ── Score ── */
  .score-summary {
    padding: 20px 22px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    font-size: 0.92rem;
    line-height: 1.7;
    color: var(--text-muted);
    box-shadow: var(--shadow-xs);
  }

  .run-errors {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 14px 16px;
    background: var(--red-soft, color-mix(in srgb, var(--red) 5%, var(--bg-secondary)));
    border: 1px solid color-mix(in srgb, var(--red) 25%, var(--border));
    border-radius: var(--radius-lg);
    color: var(--red);
    font-family: var(--font-mono);
    font-size: 0.85rem;
  }

  .run-error-summary {
    background: var(--red-soft, color-mix(in srgb, var(--red) 5%, var(--bg-secondary)));
    border: 1px solid color-mix(in srgb, var(--red) 25%, var(--border));
    color: var(--text);
  }

  /* ── Plots ── */
  .plots-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 14px;
  }

  .plot-item {
    display: flex;
    flex-direction: column;
    gap: 0;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    overflow: hidden;
    box-shadow: var(--shadow-xs);
    transition: box-shadow var(--transition-fast, 120ms ease);
  }

  .plot-item:hover {
    box-shadow: var(--shadow);
  }

  .plot-item img {
    width: 100%;
    height: auto;
    display: block;
  }

  .plot-label {
    padding: 8px 14px;
    font-size: 0.75rem;
    font-family: var(--font-mono);
    color: var(--text-faint, var(--text-muted));
    border-top: 1px solid var(--border);
    background: var(--bg);
  }

  /* ── Trace ── */
  .trace-controls {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  /* ── Notes ── */
  .notes-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 14px;
  }

  .note-card {
    display: flex;
    flex-direction: column;
    gap: 10px;
    min-height: 150px;
    padding: 20px;
    text-align: left;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-xs);
    transition: all var(--transition-normal, 180ms ease);
  }

  .note-card:not(:disabled):hover {
    transform: translateY(-2px);
    border-color: color-mix(in srgb, var(--accent) 40%, var(--border));
    border-left-color: var(--accent);
    box-shadow: var(--shadow-md);
  }

  .note-card:disabled {
    cursor: default;
    opacity: 0.7;
  }

  .note-type {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--accent);
  }

  .note-title {
    font-size: 1rem;
    font-weight: 700;
    line-height: 1.25;
  }

  .note-summary {
    color: var(--text-muted);
    line-height: 1.55;
    font-size: 0.88rem;
  }

  .toggle-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.85rem;
    color: var(--text-muted);
    cursor: pointer;
    white-space: nowrap;
  }

  .toggle-label input {
    accent-color: var(--accent);
  }
</style>
