<script>
  let { configNames, configs, datasets, runMap, onSelect } = $props();

  const verdictColors = {
    solved: "var(--green)",
    partial: "var(--orange)",
    wrong: "var(--red)",
    fail: "var(--red)",
  };

  function getAggregates(configName) {
    let total = 0;
    let solved = 0;
    let partial = 0;
    let wrong = 0;
    let totalCost = 0;
    for (const ds of datasets) {
      const run = runMap[`${configName}/${ds}`];
      if (!run?.score) continue;
      total++;
      if (run.score.verdict === "solved") solved++;
      else if (run.score.verdict === "partial") partial++;
      else wrong++;
      totalCost += run.stats?.costUsd ?? 0;
    }
    return { total, solved, partial, wrong, totalCost };
  }
</script>

<div class="matrix-wrapper">
  <table class="matrix">
    <thead>
      <tr>
        <th class="dataset-col">Dataset</th>
        {#each configNames as cfg}
          {@const agg = getAggregates(cfg)}
          <th class="config-col">
            <div class="config-name">{cfg}</div>
            <div class="config-desc">{configs[cfg]?.description ?? ""}</div>
            <div class="config-agg">
              <span class="agg-item" style="color: var(--green)">{agg.solved}</span>
              <span class="agg-sep">/</span>
              <span class="agg-item" style="color: var(--orange)">{agg.partial}</span>
              <span class="agg-sep">/</span>
              <span class="agg-item" style="color: var(--red)">{agg.wrong}</span>
              {#if agg.totalCost > 0}
                <span class="agg-cost">${agg.totalCost.toFixed(2)}</span>
              {/if}
            </div>
          </th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each datasets as ds}
        <tr>
          <td class="dataset-cell">{ds.replace(/_/g, " ")}</td>
          {#each configNames as cfg}
            {@const run = runMap[`${cfg}/${ds}`]}
            {#if run?.score}
              <td class="run-cell">
                <button
                  class="cell-btn"
                  onclick={() => onSelect(run)}
                  title="{cfg} / {ds}: {run.score.verdict}"
                >
                  <span
                    class="verdict-tag"
                    style="color: {verdictColors[run.score.verdict] ?? 'var(--text-muted)'}; border-color: {verdictColors[run.score.verdict] ?? 'var(--border)'}"
                  >
                    {run.score.verdict}
                  </span>
                  <span class="coverage">
                    {Math.round((run.score.required_coverage ?? 0) * 100)}%
                  </span>
                  {#if run.stats?.costUsd != null}
                    <span class="cost">${run.stats.costUsd.toFixed(2)}</span>
                  {/if}
                </button>
              </td>
            {:else if run}
              <td class="run-cell">
                <button class="cell-btn empty-cell" onclick={() => onSelect(run)}>
                  <span class="no-score">unscored</span>
                </button>
              </td>
            {:else}
              <td class="run-cell">
                <span class="no-run">&mdash;</span>
              </td>
            {/if}
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .matrix-wrapper {
    overflow-x: auto;
  }

  .matrix {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 0.85rem;
  }

  thead th {
    position: sticky;
    top: 0;
    background: var(--bg);
    z-index: 1;
    padding: 10px 12px;
    text-align: center;
    border-bottom: 2px solid var(--border);
  }

  .dataset-col {
    text-align: left !important;
    min-width: 180px;
  }

  .config-col {
    min-width: 160px;
  }

  .config-name {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--accent);
  }

  .config-desc {
    font-size: 0.65rem;
    color: var(--text-muted);
    font-weight: 400;
    margin-top: 2px;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .config-agg {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 3px;
    margin-top: 6px;
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 600;
  }

  .agg-sep {
    color: var(--text-muted);
    opacity: 0.4;
  }

  .agg-cost {
    margin-left: 8px;
    color: var(--text-muted);
    font-weight: 400;
    font-size: 0.7rem;
  }

  tbody tr {
    transition: background 0.1s;
  }

  tbody tr:hover {
    background: var(--bg-secondary);
  }

  .dataset-cell {
    padding: 8px 12px;
    font-weight: 500;
    text-transform: capitalize;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }

  .run-cell {
    padding: 4px 6px;
    text-align: center;
    border-bottom: 1px solid var(--border);
  }

  .cell-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 100%;
    padding: 6px 10px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    transition: all 0.1s;
    font-family: inherit;
  }

  .cell-btn:hover {
    border-color: var(--accent);
    background: var(--bg-tertiary);
  }

  .verdict-tag {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 1px 6px;
    border: 1px solid;
    border-radius: 3px;
  }

  .coverage {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--text);
  }

  .cost {
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: var(--text-muted);
  }

  .no-score {
    font-size: 0.7rem;
    color: var(--text-muted);
    font-style: italic;
  }

  .empty-cell {
    opacity: 0.5;
  }

  .no-run {
    color: var(--text-muted);
    opacity: 0.3;
  }
</style>
