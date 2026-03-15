<script>
  import TraceEvent from "./TraceEvent.svelte";
  import { deltaSeconds } from "./parse.js";

  let { events, allEvents, showResponses, onSelect } = $props();
</script>

<div class="timeline">
  {#each events as event, i (i)}
    {@const prevTs = i > 0 ? events[i - 1].timestamp : null}
    {@const delta = deltaSeconds(prevTs, event.timestamp)}
    {#if delta !== null && Number(delta) > 5}
      <div class="time-gap">
        <span>{delta}s gap</span>
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
    <div class="no-events">No matching events</div>
  {/if}
</div>

<style>
  .timeline {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .time-gap {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 4px 0;
  }

  .time-gap span {
    font-size: 0.7rem;
    color: var(--text-muted);
    background: var(--bg-tertiary);
    padding: 2px 10px;
    border-radius: 10px;
    opacity: 0.7;
  }

  .no-events {
    text-align: center;
    padding: 40px;
    color: var(--text-muted);
  }
</style>
