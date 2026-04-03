<script>
  import { extractTools, VERDICT_COLORS as verdictColors, displayVerdict } from "./parse.js";
  import CriteriaTable from "./CriteriaTable.svelte";
  import ReportView from "./ReportView.svelte";
  import Timeline from "./Timeline.svelte";
  import ToolFilter from "./ToolFilter.svelte";
  import EventModal from "./EventModal.svelte";
  import Lightbox from "./Lightbox.svelte";

  let { run, config = null, onSelectArtifact = null } = $props();

  let activeTab = $state("score");
  let selectedEvent = $state(null);
  let activeTools = $state(new Set());
  let showResponses = $state(true);
  let lightboxSrc = $state(null);
  let lightboxLabel = $state("");

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

</script>

<div class="flex flex-col gap-5">
  <div class="flex items-center justify-between gap-4 px-6 py-5 bg-bg-secondary border border-border rounded-2xl shadow-sm">
    <div>
      <div class="flex items-baseline gap-2">
        <span class="text-[0.82rem] font-bold uppercase tracking-[0.05em] text-accent">{run.config}</span>
        <span class="text-text-muted opacity-25">/</span>
        <span class="text-[1.3rem] font-[800] capitalize tracking-[-0.02em]">{run.dataset.replace(/_/g, " ")}</span>
      </div>
    </div>
    {#if score}
      <span
        class="verdict-badge"
        style="--verdict-color: {verdictColors[score.verdict] ?? 'var(--color-text-muted)'}"
      >
        <span class="h-2 w-2 rounded-full shrink-0" style="background: {verdictColors[score.verdict] ?? 'var(--color-text-muted)'}"></span>
        {displayVerdict(score.verdict)}
        {#if score.verdict !== "run_error" && score.core_insight_pass !== undefined}
          <span class="w-px h-3 bg-border"></span>
          core insight {score.core_insight_pass ? "pass" : "fail"}
        {/if}
      </span>
    {/if}
  </div>

  {#if score}
    <div class="flex gap-px rounded-xl overflow-hidden border border-border shadow-sm">
      {#if score.verdict === "run_error"}
        <div class="flex-[1.5] flex flex-col items-center gap-1.5 px-3 py-4 bg-bg-secondary first:rounded-l-xl last:rounded-r-xl">
          <span class="text-[0.66rem] font-semibold uppercase tracking-[0.06em] text-text-faint">Run Status</span>
          <span class="text-[1.15rem] font-bold font-mono text-red tabular-nums">run error</span>
        </div>
        <div class="flex-1 flex flex-col items-center gap-1.5 px-3 py-4 bg-bg-secondary first:rounded-l-xl last:rounded-r-xl">
          <span class="text-[0.66rem] font-semibold uppercase tracking-[0.06em] text-text-faint">Rerun Recommended</span>
          <span class="text-[1.15rem] font-bold font-mono text-text tabular-nums">{score.rerun_recommended ? "yes" : "no"}</span>
        </div>
      {:else}
        {@const reqCov = Math.round((score.required_coverage ?? 0) * 100)}
        {@const supCov = Math.round((score.supporting_coverage ?? 0) * 100)}
        <div class="flex-1 flex flex-col items-center gap-1.5 px-3 py-4 bg-bg-secondary first:rounded-l-xl last:rounded-r-xl">
          <span class="text-[0.66rem] font-semibold uppercase tracking-[0.06em] text-text-faint">Required Coverage</span>
          <div class="flex items-center gap-2.5 w-full max-w-[140px]">
            <div class="flex-1 h-1.5 rounded-full bg-bg-tertiary overflow-hidden">
              <div class="h-full rounded-full transition-[width] duration-[400ms] ease-[cubic-bezier(0.4,0,0.2,1)]" style="width: {reqCov}%; background: {reqCov >= 80 ? 'var(--color-green)' : reqCov >= 50 ? 'var(--color-orange)' : 'var(--color-red)'}"></div>
            </div>
            <span class="text-[1.15rem] font-bold font-mono text-text tabular-nums">{reqCov}%</span>
          </div>
        </div>
        <div class="flex-1 flex flex-col items-center gap-1.5 px-3 py-4 bg-bg-secondary first:rounded-l-xl last:rounded-r-xl">
          <span class="text-[0.66rem] font-semibold uppercase tracking-[0.06em] text-text-faint">Supporting Coverage</span>
          <div class="flex items-center gap-2.5 w-full max-w-[140px]">
            <div class="flex-1 h-1.5 rounded-full bg-bg-tertiary overflow-hidden">
              <div class="h-full rounded-full transition-[width] duration-[400ms] ease-[cubic-bezier(0.4,0,0.2,1)]" style="width: {supCov}%; background: {supCov >= 80 ? 'var(--color-green)' : supCov >= 50 ? 'var(--color-orange)' : 'var(--color-red)'}"></div>
            </div>
            <span class="text-[1.15rem] font-bold font-mono text-text tabular-nums">{supCov}%</span>
          </div>
        </div>
      {/if}
      {#if run.stats?.costUsd !== null}
        <div class="flex-1 flex flex-col items-center gap-1.5 px-3 py-4 bg-bg-secondary first:rounded-l-xl last:rounded-r-xl">
          <span class="text-[0.66rem] font-semibold uppercase tracking-[0.06em] text-text-faint">Cost</span>
          <span class="text-[1.15rem] font-bold font-mono text-text tabular-nums">${run.stats.costUsd.toFixed(2)}</span>
        </div>
      {/if}
      <div class="flex-1 flex flex-col items-center gap-1.5 px-3 py-4 bg-bg-secondary first:rounded-l-xl last:rounded-r-xl">
        <span class="text-[0.66rem] font-semibold uppercase tracking-[0.06em] text-text-faint">Duration</span>
        <span class="text-[1.15rem] font-bold font-mono text-text tabular-nums">{run.stats?.durationFormatted ?? "\u2014"}</span>
      </div>
      <div class="flex-1 flex flex-col items-center gap-1.5 px-3 py-4 bg-bg-secondary first:rounded-l-xl last:rounded-r-xl">
        <span class="text-[0.66rem] font-semibold uppercase tracking-[0.06em] text-text-faint">Turns</span>
        <span class="text-[1.15rem] font-bold font-mono text-text tabular-nums">{run.stats?.numTurns ?? events.length}</span>
      </div>
      {#if score.efficiency}
        <div class="flex-1 flex flex-col items-center gap-1.5 px-3 py-4 bg-bg-secondary first:rounded-l-xl last:rounded-r-xl">
          <span class="text-[0.66rem] font-semibold uppercase tracking-[0.06em] text-text-faint">Trace Events</span>
          <span class="text-[1.15rem] font-bold font-mono text-text tabular-nums">{score.efficiency.trace_events}</span>
        </div>
      {/if}
    </div>
  {/if}

  <nav class="flex border-b-2 border-border">
    <button class="tab-btn" class:tab-active={activeTab === "score"} onclick={() => (activeTab = "score")}>
      Score
    </button>
    {#if run.report}
      <button class="tab-btn" class:tab-active={activeTab === "report"} onclick={() => (activeTab = "report")}>
        Report
      </button>
    {/if}
    {#if run.plots?.length}
      <button class="tab-btn" class:tab-active={activeTab === "plots"} onclick={() => (activeTab = "plots")}>
        Plots ({run.plots.length})
      </button>
    {/if}
    {#if events.length > 0}
      <button class="tab-btn" class:tab-active={activeTab === "trace"} onclick={() => (activeTab = "trace")}>
        Trace ({events.length})
      </button>
    {/if}
    {#if run.relatedArtifacts?.length}
      <button class="tab-btn" class:tab-active={activeTab === "notes"} onclick={() => (activeTab = "notes")}>
        Notes ({run.relatedArtifacts.length})
      </button>
    {/if}
  </nav>

  {#if activeTab === "score" && score}
    {#if score.summary}
      <div class="px-[22px] py-5 bg-bg-secondary border border-border rounded-xl text-[0.92rem] leading-[1.7] text-text-muted shadow-xs {score.verdict === 'run_error' ? 'bg-red-soft border-[color-mix(in_srgb,var(--color-red)_25%,var(--color-border))] !text-text' : ''}">
        {score.summary}
      </div>
    {/if}
    {#if score.run_error_reasons?.length}
      <div class="flex flex-col gap-2 px-4 py-3.5 bg-red-soft border border-[color-mix(in_srgb,var(--color-red)_25%,var(--color-border))] rounded-xl text-red font-mono text-[0.85rem]">
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
    <div class="grid grid-cols-[repeat(auto-fill,minmax(320px,1fr))] gap-3.5">
      {#each run.plots as src}
        <button
          class="flex flex-col bg-bg-secondary border border-border rounded-xl overflow-hidden shadow-xs text-left transition-all duration-200 ease-out cursor-zoom-in hover:shadow-md hover:-translate-y-0.5 hover:border-[color-mix(in_srgb,var(--color-accent)_35%,var(--color-border))]"
          type="button"
          onclick={() => { lightboxSrc = src; lightboxLabel = src.split("/").pop(); }}
        >
          <img {src} alt={src.split("/").pop()} loading="lazy" class="w-full h-auto block" />
          <span class="px-3.5 py-2 text-[0.75rem] font-mono text-text-faint border-t border-border bg-bg">{src.split("/").pop()}</span>
        </button>
      {/each}
    </div>
  {:else if activeTab === "trace"}
    <div class="flex items-center justify-between gap-4">
      <ToolFilter
        {tools}
        {activeTools}
        onToggle={toggleTool}
        onSelectAll={() => (activeTools = new Set(tools))}
        onSelectNone={() => (activeTools = new Set())}
      />
      <label class="flex items-center gap-1.5 text-[0.85rem] text-text-muted cursor-pointer whitespace-nowrap">
        <input type="checkbox" bind:checked={showResponses} class="accent-accent" />
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
    <div class="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-3.5">
      {#each run.relatedArtifacts as artifact}
        <button
          class="note-card flex flex-col gap-2.5 min-h-[150px] p-5 text-left bg-bg-secondary border border-border border-l-[3px] border-l-accent rounded-xl shadow-xs transition-all duration-200 ease-out disabled:cursor-default disabled:opacity-70"
          type="button"
          disabled={onSelectArtifact == null}
          onclick={() => onSelectArtifact?.(artifact)}
        >
          <div class="text-[0.7rem] font-bold uppercase tracking-[0.1em] text-accent">{artifact.type?.replace(/_/g, " ") ?? "note"}</div>
          <div class="text-base font-bold leading-[1.25]">{artifact.title ?? artifact.artifact_id}</div>
          {#if artifact.summary}
            <div class="text-text-muted leading-[1.55] text-[0.88rem]">{artifact.summary}</div>
          {/if}
        </button>
      {/each}
    </div>
  {/if}
</div>

{#if selectedEvent}
  <EventModal event={selectedEvent} onClose={() => (selectedEvent = null)} />
{/if}

{#if lightboxSrc}
  <Lightbox
    src={lightboxSrc}
    label={lightboxLabel}
    onClose={() => (lightboxSrc = null)}
  />
{/if}

<style>
  /* Verdict badge uses dynamic --verdict-color CSS variable */
  .verdict-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 7px 16px;
    border: 1px solid color-mix(in srgb, var(--verdict-color) 30%, var(--color-border));
    border-radius: 999px;
    white-space: nowrap;
    color: var(--verdict-color);
    background: color-mix(in srgb, var(--verdict-color) 6%, var(--color-bg-secondary));
  }

  /* Tab buttons */
  .tab-btn {
    padding: 11px 20px;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
    color: var(--color-text-muted);
    font-size: 0.88rem;
    font-weight: 500;
    transition: all 120ms ease-out;
    position: relative;
  }

  .tab-btn:hover {
    color: var(--color-text);
    background: color-mix(in srgb, var(--color-accent) 3%, transparent);
  }

  .tab-active {
    color: var(--color-accent) !important;
    border-bottom-color: var(--color-accent) !important;
    font-weight: 600 !important;
  }

  /* Note card hover (not disabled) */
  .note-card:not(:disabled):hover {
    transform: translateY(-2px);
    border-color: color-mix(in srgb, var(--color-accent) 40%, var(--color-border));
    border-left-color: var(--color-accent);
    box-shadow: var(--shadow-md);
  }
</style>
