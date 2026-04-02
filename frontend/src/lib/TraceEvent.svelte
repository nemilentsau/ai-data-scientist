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
  class="event bg-bg-secondary rounded-lg border border-border transition-all duration-100 ease-out cursor-pointer shadow-xs hover:shadow-sm"
  class:error={isError}
  style="--event-color: {color}"
  role="button"
  tabindex="0"
  onclick={() => (expanded = !expanded)}
  onkeydown={(e) => e.key === "Enter" && (expanded = !expanded)}
>
  <div class="flex items-center gap-2 px-3.5 py-2.5 min-h-[42px]">
    <span class="font-mono text-[0.75rem] text-text-faint min-w-[65px] tabular-nums">{formatTime(event.timestamp)}</span>
    {#if delta !== null}
      <span class="font-mono text-[0.65rem] text-text-faint opacity-50 min-w-[45px] tabular-nums">+{delta}s</span>
    {/if}
    <span
      class="flex items-center justify-center w-7 h-7 rounded-[6px] font-mono text-[0.8rem] font-bold shrink-0"
      style="background: color-mix(in srgb, {color} 20%, transparent); color: {color}"
    >
      {icon}
    </span>
    <span class="font-semibold text-[0.85rem] min-w-[50px]" style="color: {color}">{event.tool}</span>
    {#if isError}
      <span class="text-[0.6rem] font-bold px-[7px] py-0.5 rounded-full uppercase tracking-wide shrink-0 bg-red/10 text-red">FAIL</span>
    {:else}
      <span class="text-[0.6rem] font-bold px-[7px] py-0.5 rounded-full uppercase tracking-wide shrink-0 bg-green/10 text-green">OK</span>
    {/if}
    <span class="flex-1 font-mono text-[0.78rem] text-text-muted overflow-hidden text-ellipsis whitespace-nowrap">{summary}</span>
    <button
      class="px-2.5 py-1 font-mono text-[0.72rem] bg-bg-tertiary border border-border rounded-[6px] text-text-faint shrink-0 transition-all duration-100 ease-out hover:text-accent hover:border-accent hover:bg-accent-soft"
      title="View raw JSON"
      onclick={(e) => { e.stopPropagation(); onSelect(); }}
    >
      {"{ }"}
    </button>
  </div>

  {#if expanded}
    <div class="px-3.5 pb-3.5 flex flex-col gap-2.5">
      {#if codeInfo}
        <div class="flex flex-col gap-1">
          <div class="text-[0.7rem] uppercase tracking-[0.06em] text-text-faint font-semibold">Input</div>
          <CodeBlock code={codeInfo.code} language={codeInfo.language} />
        </div>
      {:else if event.tool_input}
        <div class="flex flex-col gap-1">
          <div class="text-[0.7rem] uppercase tracking-[0.06em] text-text-faint font-semibold">Input</div>
          <CodeBlock code={JSON.stringify(event.tool_input, null, 2)} language="json" />
        </div>
      {/if}

      {#if showResponses && isError && event.error}
        <div class="flex flex-col gap-1">
          <div class="text-[0.7rem] uppercase tracking-[0.06em] text-red font-semibold">Error</div>
          <CodeBlock
            code={typeof event.error === "string" ? event.error : JSON.stringify(event.error, null, 2)}
            language="text"
          />
        </div>
      {/if}

      {#if showResponses && responseText}
        <div class="flex flex-col gap-1">
          <div class="text-[0.7rem] uppercase tracking-[0.06em] text-text-faint font-semibold">Response</div>
          <CodeBlock code={responseText} language="text" maxLines={50} />
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .event {
    border-left: 3px solid var(--event-color);
  }

  .event:hover {
    border-color: color-mix(in srgb, var(--event-color) 35%, var(--color-border));
    border-left-color: var(--event-color);
  }

  .event.error {
    border-left-color: var(--color-red);
    background: color-mix(in srgb, var(--color-red) 2%, var(--color-bg-secondary));
  }
</style>
