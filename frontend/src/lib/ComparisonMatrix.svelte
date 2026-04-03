<script>
  import { VERDICT_COLORS as verdictColors, VERDICT_BG as verdictBg, displayVerdict } from "./parse.js";

  let { configNames, configs, datasets, runMap, onSelect } = $props();

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

<div class="overflow-x-auto border border-border rounded-2xl shadow-sm bg-bg-secondary">
  <table class="w-full border-separate border-spacing-0 text-[0.85rem]">
    <thead>
      <tr>
        <th class="sticky top-0 bg-bg-tertiary z-1 px-3.5 py-4 border-b-2 border-border text-left! min-w-[180px] font-semibold text-text-muted text-[0.78rem] uppercase tracking-[0.05em]">Dataset</th>
        {#each configNames as cfg}
          {@const agg = getAggregates(cfg)}
          <th class="sticky top-0 bg-bg-tertiary z-1 px-3.5 py-4 border-b-2 border-border text-center min-w-[190px]">
            <div class="text-[0.85rem] font-bold text-accent">{cfg}</div>
            <div class="text-[0.68rem] text-text-muted font-normal mt-[3px] max-w-[220px] overflow-hidden text-ellipsis whitespace-nowrap">{configs[cfg]?.description ?? ""}</div>
            {#if agg.total > 0}
              <div class="flex h-[5px] rounded-full overflow-hidden bg-[color-mix(in_srgb,var(--color-border)_60%,var(--color-bg-tertiary))] mt-2.5 gap-px">
                {#if agg.solved > 0}
                  <div class="min-w-[3px] rounded-full bg-green transition-[width] duration-[400ms] ease-[cubic-bezier(0.4,0,0.2,1)]" style="width: {agg.solved / agg.total * 100}%" title="{agg.solved} solved"></div>
                {/if}
                {#if agg.partial > 0}
                  <div class="min-w-[3px] rounded-full bg-orange transition-[width] duration-[400ms] ease-[cubic-bezier(0.4,0,0.2,1)]" style="width: {agg.partial / agg.total * 100}%" title="{agg.partial} partial"></div>
                {/if}
                {#if agg.wrong > 0}
                  <div class="min-w-[3px] rounded-full bg-red transition-[width] duration-[400ms] ease-[cubic-bezier(0.4,0,0.2,1)]" style="width: {agg.wrong / agg.total * 100}%" title="{agg.wrong} wrong"></div>
                {/if}
                {#if agg.runError > 0}
                  <div class="min-w-[3px] rounded-full transition-[width] duration-[400ms] ease-[cubic-bezier(0.4,0,0.2,1)]" style="width: {agg.runError / agg.total * 100}%; background: repeating-linear-gradient(-45deg, var(--color-red), var(--color-red) 1.5px, transparent 1.5px, transparent 3px)" title="{agg.runError} errors"></div>
                {/if}
              </div>
            {/if}
            <div class="flex flex-wrap items-center justify-center gap-1 mt-2 text-[0.7rem]">
              <span class="inline-flex items-center justify-center min-w-[22px] px-[7px] py-[2px] rounded-full font-bold leading-[1.2] tabular-nums text-green bg-[color-mix(in_srgb,var(--color-green)_12%,var(--color-bg-secondary))]" title="Solved">{agg.solved}</span>
              <span class="inline-flex items-center justify-center min-w-[22px] px-[7px] py-[2px] rounded-full font-bold leading-[1.2] tabular-nums text-orange bg-[color-mix(in_srgb,var(--color-orange)_12%,var(--color-bg-secondary))]" title="Partial">{agg.partial}</span>
              <span class="inline-flex items-center justify-center min-w-[22px] px-[7px] py-[2px] rounded-full font-bold leading-[1.2] tabular-nums text-red bg-[color-mix(in_srgb,var(--color-red)_10%,var(--color-bg-secondary))]" title="Wrong">{agg.wrong}</span>
              {#if agg.runError > 0}
                <span class="inline-flex items-center justify-center min-w-[22px] px-[7px] py-[2px] rounded-full font-bold leading-[1.2] tabular-nums text-red bg-[color-mix(in_srgb,var(--color-red)_14%,var(--color-bg-secondary))]" title="Run errors">{agg.runError}</span>
              {/if}
              {#if agg.totalCost > 0}
                <span class="ml-1 text-text-muted font-medium text-[0.72rem] font-mono">${agg.totalCost.toFixed(2)}</span>
              {/if}
            </div>
          </th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each datasets as ds}
        <tr class="transition-all duration-100 ease-out hover:bg-[color-mix(in_srgb,var(--color-accent)_2.5%,var(--color-bg-secondary))]">
          <td class="px-3.5 py-2.5 font-semibold capitalize border-b border-border whitespace-nowrap text-text text-[0.88rem]">{ds.replace(/_/g, " ")}</td>
          {#each configNames as cfg}
            {@const run = runMap[`${cfg}/${ds}`]}
            {#if run?.score}
              {@const coverage = Math.round((run.score.required_coverage ?? 0) * 100)}
              <td class="px-[5px] py-1 text-center border-b border-border">
                <button
                  class="flex flex-col items-stretch gap-1.5 w-full px-2.5 py-2 bg-bg border border-border rounded-lg transition-all duration-100 ease-out hover:border-accent hover:shadow-sm hover:-translate-y-px"
                  class:border-[color-mix(in_srgb,var(--color-red)_30%,var(--color-border))]={run.score.verdict === "run_error"}
                  class:hover:!border-red={run.score.verdict === "run_error"}
                  style="background: {verdictBg[run.score.verdict] ?? 'var(--color-bg)'}"
                  onclick={() => onSelect(run)}
                  title="{cfg} / {ds}: {displayVerdict(run.score.verdict)}"
                >
                  <div class="flex items-center justify-center gap-2">
                    <span
                      class="text-[0.68rem] font-bold uppercase tracking-[0.04em] px-[7px] py-[2px] border rounded-[4px]"
                      style="color: {verdictColors[run.score.verdict] ?? 'var(--color-text-muted)'}; border-color: {verdictColors[run.score.verdict] ?? 'var(--color-border)'}"
                    >
                      {displayVerdict(run.score.verdict)}
                    </span>
                    {#if run.stats?.costUsd != null}
                      <span class="font-mono text-[0.68rem] text-text-faint tabular-nums">${run.stats.costUsd.toFixed(2)}</span>
                    {/if}
                  </div>
                  {#if run.score.verdict === "run_error"}
                    <span class="font-mono text-[0.78rem] font-semibold text-red min-w-[32px] text-center font-sans">execution failed</span>
                  {:else}
                    <div class="flex items-center gap-2">
                      <div class="flex-1 h-1 rounded-full bg-[color-mix(in_srgb,var(--color-border)_50%,var(--color-bg))] overflow-hidden">
                        <div
                          class="h-full rounded-full transition-[width] duration-[400ms] ease-[cubic-bezier(0.4,0,0.2,1)]"
                          style="width: {coverage}%; background: {verdictColors[run.score.verdict] ?? 'var(--color-text-muted)'}"
                        ></div>
                      </div>
                      <span class="font-mono text-[0.78rem] font-semibold text-text min-w-[32px] text-right tabular-nums">{coverage}%</span>
                    </div>
                  {/if}
                </button>
              </td>
            {:else if run}
              <td class="px-[5px] py-1 text-center border-b border-border">
                <button class="flex flex-col items-stretch gap-1.5 w-full px-2.5 py-2 bg-bg border border-border rounded-lg transition-all duration-100 ease-out hover:border-accent hover:shadow-sm hover:-translate-y-px opacity-50" onclick={() => onSelect(run)}>
                  <span class="text-[0.72rem] text-text-muted italic">unscored</span>
                </button>
              </td>
            {:else}
              <td class="px-[5px] py-1 text-center border-b border-border">
                <span class="text-text-muted opacity-20">&mdash;</span>
              </td>
            {/if}
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>
