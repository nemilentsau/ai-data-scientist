<script>
  import TraceEvent from "./TraceEvent.svelte";
  import { deltaSeconds } from "./parse.js";

  let { events, allEvents, showResponses, onSelect } = $props();
</script>

<div class="flex flex-col gap-1">
  {#each events as event, i (i)}
    {@const prevTs = i > 0 ? events[i - 1].timestamp : null}
    {@const delta = deltaSeconds(prevTs, event.timestamp)}
    {#if delta !== null && Number(delta) > 5}
      <div class="flex items-center justify-center py-1.5">
        <span class="text-[0.72rem] font-medium text-text-muted bg-bg-tertiary px-3 py-[3px] rounded-[10px]">{delta}s gap</span>
      </div>
    {/if}
    <TraceEvent
      {event}
      {delta}
      index={allEvents.indexOf(event)}
      {showResponses}
      onSelect={() => onSelect(event)}
    />
  {/each}
  {#if events.length === 0}
    <div class="text-center p-10 text-text-muted">No matching events</div>
  {/if}
</div>
