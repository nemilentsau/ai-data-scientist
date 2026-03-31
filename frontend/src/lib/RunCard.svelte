<script>
  let { run, onSelect } = $props();

  let score = $derived(run.score);

  const verdictColors = {
    pass: "var(--green)",
    partial: "var(--orange)",
    fail: "var(--red)",
  };

  let color = $derived(verdictColors[score?.verdict] ?? "var(--text-muted)");

  let mustHaveStats = $derived.by(() => {
    if (!score?.criterion_results) return null;
    const must = score.criterion_results.filter((c) => c.group === "must_have");
    const hits = must.filter((c) => c.status === "hit").length;
    return { hits, total: must.length };
  });
</script>

<button class="card" onclick={onSelect}>
  <div class="card-header">
    <span class="agent">{run.agent}</span>
    <span class="verdict" style="color: {color}; border-color: {color}">
      {score?.verdict ?? "unknown"}
    </span>
  </div>

  <div class="dataset">{run.dataset.replace(/_/g, " ")}</div>

  {#if score}
    <div class="metrics">
      <div class="metric">
        <span class="metric-label">Required</span>
        <span class="metric-value">{Math.round((score.required_coverage ?? 0) * 100)}%</span>
      </div>
      <div class="metric">
        <span class="metric-label">Supporting</span>
        <span class="metric-value">{Math.round((score.supporting_coverage ?? 0) * 100)}%</span>
      </div>
      {#if mustHaveStats}
        <div class="metric">
          <span class="metric-label">Must-have</span>
          <span class="metric-value">{mustHaveStats.hits}/{mustHaveStats.total}</span>
        </div>
      {/if}
    </div>

    <div class="bar-track">
      <div
        class="bar-fill"
        style="width: {(score.required_coverage ?? 0) * 100}%; background: {color}"
      ></div>
    </div>
  {/if}

  <div class="card-footer">
    {#if run.stats}
      <span class="foot-stat">{run.stats.durationFormatted}</span>
      {#if run.stats.costUsd !== null}
        <span class="foot-stat">${run.stats.costUsd.toFixed(2)}</span>
      {/if}
      <span class="foot-stat">{run.stats.numTurns ?? run.stats.totalEvents} turns</span>
    {/if}
    {#if run.plots?.length}
      <span class="foot-stat">{run.plots.length} plots</span>
    {/if}
  </div>
</button>

<style>
  .card {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 16px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    text-align: left;
    transition: all 0.15s;
  }

  .card:hover {
    border-color: var(--accent);
    transform: translateY(-2px);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .agent {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--accent);
  }

  .verdict {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 2px 8px;
    border: 1px solid;
    border-radius: 4px;
  }

  .dataset {
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--text);
    text-transform: capitalize;
  }

  .metrics {
    display: flex;
    gap: 16px;
  }

  .metric {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .metric-label {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
  }

  .metric-value {
    font-size: 1rem;
    font-weight: 600;
    font-family: var(--font-mono);
  }

  .bar-track {
    height: 4px;
    background: var(--bg-tertiary);
    border-radius: 2px;
    overflow: hidden;
  }

  .bar-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.3s;
  }

  .card-footer {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }

  .foot-stat {
    font-size: 0.7rem;
    color: var(--text-muted);
    font-family: var(--font-mono);
  }
</style>
