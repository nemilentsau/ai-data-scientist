<script>
  import { parseTrace, extractTools, computeStats, extractPlots } from "./lib/parse.js";
  import Summary from "./lib/Summary.svelte";
  import ToolFilter from "./lib/ToolFilter.svelte";
  import Timeline from "./lib/Timeline.svelte";
  import EventModal from "./lib/EventModal.svelte";
  import PlotGallery from "./lib/PlotGallery.svelte";
  import ReportView from "./lib/ReportView.svelte";
  import FileLoader from "./lib/FileLoader.svelte";

  let events = $state([]);
  let meta = $state(null);
  let tools = $state([]);
  let stats = $state(null);
  let plots = $state([]);
  let activeTools = $state(new Set());
  let showResponses = $state(true);
  let errorsOnly = $state(false);
  let selectedEvent = $state(null);
  let reportText = $state("");
  let activeTab = $state("timeline");
  let resultsDir = $state("");

  function handleTraceLoaded(text, dirPath) {
    const parsed = parseTrace(text);
    events = parsed.events;
    meta = parsed.meta;
    tools = extractTools(events);
    stats = computeStats(events, meta);
    plots = extractPlots(events);
    activeTools = new Set(tools);
    resultsDir = dirPath || "";
    reportText = "";
    activeTab = "timeline";
  }

  function handleReportLoaded(text) {
    reportText = text;
  }

  let filteredEvents = $derived.by(() => {
    let filtered = events;
    if (activeTools.size < tools.length) {
      filtered = filtered.filter((e) => activeTools.has(e.tool));
    }
    if (errorsOnly) {
      filtered = filtered.filter(
        (e) => e.error || e.event === "PostToolUseFailure"
      );
    }
    return filtered;
  });

  function toggleTool(tool) {
    const next = new Set(activeTools);
    if (next.has(tool)) next.delete(tool);
    else next.add(tool);
    activeTools = next;
  }

  function selectAll() {
    activeTools = new Set(tools);
  }

  function selectNone() {
    activeTools = new Set();
  }
</script>

<div class="app">
  <header>
    <h1>Trace Viewer</h1>
    <FileLoader onTraceLoaded={handleTraceLoaded} onReportLoaded={handleReportLoaded} />
  </header>

  {#if stats}
    <Summary {stats} />

    <nav class="tabs">
      <button
        class="tab"
        class:active={activeTab === "timeline"}
        onclick={() => (activeTab = "timeline")}
      >
        Timeline ({events.length})
      </button>
      {#if reportText}
        <button
          class="tab"
          class:active={activeTab === "report"}
          onclick={() => (activeTab = "report")}
        >
          Report
        </button>
      {/if}
      {#if plots.length > 0}
        <button
          class="tab"
          class:active={activeTab === "plots"}
          onclick={() => (activeTab = "plots")}
        >
          Plots ({plots.length})
        </button>
      {/if}
    </nav>

    {#if activeTab === "timeline"}
      <div class="controls">
        <ToolFilter
          {tools}
          {activeTools}
          onToggle={toggleTool}
          onSelectAll={selectAll}
          onSelectNone={selectNone}
        />
        <div class="toggles">
          <label>
            <input type="checkbox" bind:checked={showResponses} />
            Responses
          </label>
          <label>
            <input type="checkbox" bind:checked={errorsOnly} />
            Errors only
          </label>
        </div>
      </div>

      <Timeline
        events={filteredEvents}
        allEvents={events}
        {showResponses}
        onSelect={(e) => (selectedEvent = e)}
      />
    {:else if activeTab === "report"}
      <ReportView text={reportText} />
    {:else if activeTab === "plots"}
      <PlotGallery {plots} {resultsDir} />
    {/if}
  {:else}
    <div class="empty">
      <div class="empty-icon">&#9776;</div>
      <p>Drop a <code>trace.jsonl</code> file or use the loader above</p>
      <p class="hint">
        You can also load an entire results directory (trace.jsonl +
        analysis_report.md + plots/)
      </p>
    </div>
  {/if}

  {#if selectedEvent}
    <EventModal event={selectedEvent} onClose={() => (selectedEvent = null)} />
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
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border);
  }

  h1 {
    font-size: 1.3rem;
    font-weight: 600;
    color: var(--text);
  }

  .tabs {
    display: flex;
    gap: 2px;
    margin-bottom: 12px;
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

  .controls {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 12px;
  }

  .toggles {
    display: flex;
    gap: 16px;
    font-size: 0.85rem;
    color: var(--text-muted);
  }

  .toggles label {
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
  }

  .toggles input[type="checkbox"] {
    accent-color: var(--accent);
  }

  .empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 50vh;
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
