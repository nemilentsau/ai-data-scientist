<script>
  let { configNames, configs, datasets, runMap, onSelect } = $props();

  const verdictColors = {
    solved: "var(--green)",
    partial: "var(--orange)",
    wrong: "var(--red)",
    failed: "var(--red)",
    run_error: "var(--red)",
  };

  const verdictBg = {
    solved: "var(--green-soft)",
    partial: "var(--orange-soft)",
    wrong: "var(--red-soft)",
    failed: "var(--red-soft)",
    run_error: "var(--red-soft)",
  };

  function displayVerdict(verdict) {
    return verdict === "run_error" ? "run error" : verdict;
  }

  function getAggregates(configName) {
    let total = 0;
    let solved = 0;
    let partial = 0;
    let wrong = 0;
    let runError = 0;
    let totalCost = 0;
    for (const ds of datasets) {
      const run = runMap[`${configName}/${ds}`];
      if (!run?.score) continue;
      total++;
      if (run.score.verdict === "solved") solved++;
      else if (run.score.verdict === "partial") partial++;
      else if (run.score.verdict === "run_error") runError++;
      else wrong++;
      totalCost += run.stats?.costUsd ?? 0;
    }
    return { total, solved, partial, wrong, runError, totalCost };
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
            {#if agg.total > 0}
              <div class="agg-bar-track">
                {#if agg.solved > 0}
                  <div class="agg-bar-seg agg-bar-solved" style="width: {agg.solved / agg.total * 100}%" title="{agg.solved} solved"></div>
                {/if}
                {#if agg.partial > 0}
                  <div class="agg-bar-seg agg-bar-partial" style="width: {agg.partial / agg.total * 100}%" title="{agg.partial} partial"></div>
                {/if}
                {#if agg.wrong > 0}
                  <div class="agg-bar-seg agg-bar-wrong" style="width: {agg.wrong / agg.total * 100}%" title="{agg.wrong} wrong"></div>
                {/if}
                {#if agg.runError > 0}
                  <div class="agg-bar-seg agg-bar-error" style="width: {agg.runError / agg.total * 100}%" title="{agg.runError} errors"></div>
                {/if}
              </div>
            {/if}
            <div class="config-agg">
              <span class="agg-pill agg-solved" title="Solved">{agg.solved}</span>
              <span class="agg-pill agg-partial" title="Partial">{agg.partial}</span>
              <span class="agg-pill agg-wrong" title="Wrong">{agg.wrong}</span>
              {#if agg.runError > 0}
                <span class="agg-pill agg-run-error" title="Run errors">{agg.runError}</span>
              {/if}
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
              {@const coverage = Math.round((run.score.required_coverage ?? 0) * 100)}
              <td class="run-cell">
                <button
                  class="cell-btn"
                  class:run-error-cell={run.score.verdict === "run_error"}
                  style="background: {verdictBg[run.score.verdict] ?? 'var(--bg)'}"
                  onclick={() => onSelect(run)}
                  title="{cfg} / {ds}: {displayVerdict(run.score.verdict)}"
                >
                  <div class="cell-top">
                    <span
                      class="verdict-tag"
                      style="color: {verdictColors[run.score.verdict] ?? 'var(--text-muted)'}; border-color: {verdictColors[run.score.verdict] ?? 'var(--border)'}"
                    >
                      {displayVerdict(run.score.verdict)}
                    </span>
                    {#if run.stats?.costUsd != null}
                      <span class="cost">${run.stats.costUsd.toFixed(2)}</span>
                    {/if}
                  </div>
                  {#if run.score.verdict === "run_error"}
                    <span class="coverage coverage--error">execution failed</span>
                  {:else}
                    <div class="coverage-row">
                      <div class="coverage-bar-track">
                        <div
                          class="coverage-bar-fill"
                          style="width: {coverage}%; background: {verdictColors[run.score.verdict] ?? 'var(--text-muted)'}"
                        ></div>
                      </div>
                      <span class="coverage">{coverage}%</span>
                    </div>
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
    border: 1px solid var(--border);
    border-radius: var(--radius-xl, 16px);
    box-shadow: var(--shadow-sm);
    background: var(--bg-secondary);
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
    background: var(--bg-tertiary);
    z-index: 1;
    padding: 16px 14px;
    text-align: center;
    border-bottom: 2px solid var(--border);
  }

  .dataset-col {
    text-align: left !important;
    min-width: 180px;
    font-weight: 600;
    color: var(--text-muted);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .config-col {
    min-width: 190px;
  }

  .config-name {
    font-size: 0.85rem;
    font-weight: 700;
    color: var(--accent);
  }

  .config-desc {
    font-size: 0.68rem;
    color: var(--text-muted);
    font-weight: 400;
    margin-top: 3px;
    max-width: 220px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .agg-bar-track {
    display: flex;
    height: 5px;
    border-radius: 100px;
    overflow: hidden;
    background: color-mix(in srgb, var(--border) 60%, var(--bg-tertiary));
    margin-top: 10px;
    gap: 1px;
  }

  .agg-bar-seg {
    min-width: 3px;
    border-radius: 100px;
    transition: width 400ms cubic-bezier(0.4, 0, 0.2, 1);
  }

  .agg-bar-solved  { background: var(--green); }
  .agg-bar-partial { background: var(--orange); }
  .agg-bar-wrong   { background: var(--red); }
  .agg-bar-error   { background: repeating-linear-gradient(-45deg, var(--red), var(--red) 1.5px, transparent 1.5px, transparent 3px); }

  .config-agg {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 4px;
    margin-top: 8px;
    font-size: 0.7rem;
  }

  .agg-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 22px;
    padding: 2px 7px;
    border-radius: 999px;
    font-weight: 700;
    line-height: 1.2;
    border: none;
    font-variant-numeric: tabular-nums;
  }

  .agg-solved {
    color: var(--green);
    background: color-mix(in srgb, var(--green) 12%, var(--bg-secondary));
  }

  .agg-partial {
    color: var(--orange);
    background: color-mix(in srgb, var(--orange) 12%, var(--bg-secondary));
  }

  .agg-wrong {
    color: var(--red);
    background: color-mix(in srgb, var(--red) 10%, var(--bg-secondary));
  }

  .agg-run-error {
    color: var(--red);
    background: color-mix(in srgb, var(--red) 14%, var(--bg-secondary));
  }

  .agg-cost {
    margin-left: 4px;
    color: var(--text-muted);
    font-weight: 500;
    font-size: 0.72rem;
    font-family: var(--font-mono);
  }

  tbody tr {
    transition: background var(--transition-fast, 120ms ease);
  }

  tbody tr:hover {
    background: color-mix(in srgb, var(--accent) 2.5%, var(--bg-secondary));
  }

  .dataset-cell {
    padding: 10px 14px;
    font-weight: 600;
    text-transform: capitalize;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
    color: var(--text);
    font-size: 0.88rem;
  }

  .run-cell {
    padding: 4px 5px;
    text-align: center;
    border-bottom: 1px solid var(--border);
  }

  .cell-btn {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 6px;
    width: 100%;
    padding: 8px 10px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    transition: all var(--transition-fast, 120ms ease);
    font-family: inherit;
  }

  .cell-btn:hover {
    border-color: var(--accent);
    box-shadow: var(--shadow-sm);
    transform: translateY(-1px);
  }

  .cell-top {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }

  .run-error-cell {
    border-color: color-mix(in srgb, var(--red) 30%, var(--border));
  }

  .run-error-cell:hover {
    border-color: var(--red);
  }

  .verdict-tag {
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 2px 7px;
    border: 1px solid;
    border-radius: 4px;
  }

  .coverage-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .coverage-bar-track {
    flex: 1;
    height: 4px;
    border-radius: 100px;
    background: color-mix(in srgb, var(--border) 50%, var(--bg));
    overflow: hidden;
  }

  .coverage-bar-fill {
    height: 100%;
    border-radius: 100px;
    transition: width 400ms cubic-bezier(0.4, 0, 0.2, 1);
  }

  .coverage {
    font-family: var(--font-mono);
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--text);
    min-width: 32px;
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  .coverage--error {
    color: var(--red);
    font-family: var(--font-sans, inherit);
    font-size: 0.72rem;
    text-align: center;
  }

  .cost {
    font-family: var(--font-mono);
    font-size: 0.68rem;
    color: var(--text-faint, var(--text-muted));
    font-variant-numeric: tabular-nums;
  }

  .no-score {
    font-size: 0.72rem;
    color: var(--text-muted);
    font-style: italic;
  }

  .empty-cell {
    opacity: 0.5;
  }

  .no-run {
    color: var(--text-muted);
    opacity: 0.2;
  }
</style>
