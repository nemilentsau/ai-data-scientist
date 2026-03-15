<script>
  import { formatTime, toolColor, toolIcon, summarizeInput, extractCode } from "./parse.js";
  import CodeBlock from "./CodeBlock.svelte";

  let { event, delta, index, showResponses, onSelect } = $props();
  let expanded = $state(false);

  let isError = $derived(!!event.error || event.event === "PostToolUseFailure");
  let color = $derived(toolColor(event.tool));
  let icon = $derived(toolIcon(event.tool));
  let summary = $derived(summarizeInput(event.tool, event.tool_input));
  let codeInfo = $derived(extractCode(event));

  let responseText = $derived.by(() => {
    if (!event.tool_response_parsed) return null;
    const r = event.tool_response_parsed;
    if (typeof r === "string") return r;
    // Read tool: extract file content
    if (r?.file?.content) return r.file.content;
    if (r?.type === "text" && r?.file?.content) return r.file.content;
    // Generic: stringify
    return JSON.stringify(r, null, 2);
  });
</script>

<div
  class="event"
  class:error={isError}
  style="--event-color: {color}"
  role="button"
  tabindex="0"
  onclick={() => (expanded = !expanded)}
  onkeydown={(e) => e.key === "Enter" && (expanded = !expanded)}
>
  <div class="event-header">
    <span class="time">{formatTime(event.timestamp)}</span>
    {#if delta !== null}
      <span class="delta">+{delta}s</span>
    {/if}
    <span class="icon" style="background: color-mix(in srgb, {color} 20%, transparent); color: {color}">
      {icon}
    </span>
    <span class="tool-name" style="color: {color}">{event.tool}</span>
    {#if isError}
      <span class="badge error-badge">FAIL</span>
    {:else}
      <span class="badge ok-badge">OK</span>
    {/if}
    <span class="summary-text">{summary}</span>
    <button
      class="json-btn"
      title="View raw JSON"
      onclick={(e) => { e.stopPropagation(); onSelect(); }}
    >
      {"{ }"}
    </button>
  </div>

  {#if expanded}
    <div class="event-body">
      {#if codeInfo}
        <div class="section">
          <div class="section-label">Input</div>
          <CodeBlock code={codeInfo.code} language={codeInfo.language} />
        </div>
      {:else if event.tool_input}
        <div class="section">
          <div class="section-label">Input</div>
          <CodeBlock code={JSON.stringify(event.tool_input, null, 2)} language="json" />
        </div>
      {/if}

      {#if showResponses && isError && event.error}
        <div class="section">
          <div class="section-label error-label">Error</div>
          <CodeBlock
            code={typeof event.error === "string" ? event.error : JSON.stringify(event.error, null, 2)}
            language="text"
          />
        </div>
      {/if}

      {#if showResponses && responseText}
        <div class="section">
          <div class="section-label">Response</div>
          <CodeBlock code={responseText} language="text" maxLines={50} />
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .event {
    background: var(--bg-secondary);
    border-radius: var(--radius);
    border-left: 3px solid transparent;
    transition: all 0.1s;
    cursor: pointer;
  }

  .event:hover {
    background: var(--bg-tertiary);
  }

  .event.error {
    border-left-color: var(--red);
  }

  .event:not(.error) {
    border-left-color: var(--event-color);
  }

  .event-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    min-height: 40px;
  }

  .time {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--text-muted);
    min-width: 65px;
  }

  .delta {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    color: var(--text-muted);
    opacity: 0.5;
    min-width: 45px;
  }

  .icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-radius: var(--radius);
    font-family: var(--font-mono);
    font-size: 0.8rem;
    font-weight: 700;
    flex-shrink: 0;
  }

  .tool-name {
    font-weight: 600;
    font-size: 0.85rem;
    min-width: 50px;
  }

  .badge {
    font-size: 0.6rem;
    font-weight: 700;
    padding: 1px 6px;
    border-radius: 3px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    flex-shrink: 0;
  }

  .ok-badge {
    background: color-mix(in srgb, var(--green) 15%, transparent);
    color: var(--green);
  }

  .error-badge {
    background: color-mix(in srgb, var(--red) 15%, transparent);
    color: var(--red);
  }

  .summary-text {
    flex: 1;
    font-family: var(--font-mono);
    font-size: 0.8rem;
    color: var(--text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .json-btn {
    padding: 4px 8px;
    font-family: var(--font-mono);
    font-size: 0.75rem;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text-muted);
    flex-shrink: 0;
    transition: all 0.1s;
  }

  .json-btn:hover {
    color: var(--accent);
    border-color: var(--accent);
  }

  .event-body {
    padding: 0 12px 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .section {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .section-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    font-weight: 600;
  }

  .error-label {
    color: var(--red);
  }
</style>
