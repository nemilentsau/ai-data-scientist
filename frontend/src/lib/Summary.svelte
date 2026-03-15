<script>
  let { stats } = $props();
</script>

<div class="summary">
  <div class="stat">
    <span class="label">Events</span>
    <span class="value">{stats.totalEvents}</span>
  </div>
  <div class="stat">
    <span class="label">Tool Calls</span>
    <span class="value">{stats.toolCalls}</span>
  </div>
  <div class="stat" class:has-errors={stats.errors > 0}>
    <span class="label">Errors</span>
    <span class="value">{stats.errors}</span>
  </div>
  <div class="stat">
    <span class="label">Duration</span>
    <span class="value">{stats.durationFormatted}</span>
  </div>
  {#if stats.costUsd !== null}
    <div class="stat">
      <span class="label">Cost</span>
      <span class="value">${stats.costUsd.toFixed(2)}</span>
    </div>
  {/if}
  {#if stats.numTurns !== null}
    <div class="stat">
      <span class="label">Turns</span>
      <span class="value">{stats.numTurns}</span>
    </div>
  {/if}
</div>

<style>
  .summary {
    display: flex;
    gap: 2px;
    margin-bottom: 16px;
    border-radius: var(--radius-lg);
    overflow: hidden;
  }

  .stat {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 10px 12px;
    background: var(--bg-secondary);
  }

  .stat:first-child {
    border-radius: var(--radius-lg) 0 0 var(--radius-lg);
  }

  .stat:last-child {
    border-radius: 0 var(--radius-lg) var(--radius-lg) 0;
  }

  .label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
  }

  .value {
    font-size: 1.2rem;
    font-weight: 600;
    font-family: var(--font-mono);
  }

  .has-errors .value {
    color: var(--red);
  }
</style>
