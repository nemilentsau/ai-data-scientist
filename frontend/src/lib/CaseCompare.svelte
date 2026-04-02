<script>
  import Lightbox from "./Lightbox.svelte";
  import { VERDICT_COLORS as verdictColors, displayVerdict } from "./parse.js";

  let { artifactCatalog = [], datasets = [], configNames = [], runMap = {}, onSelectRun = null } = $props();

  let selectedDataset = $state("");
  let compareType = $state("plots");

  let columns = $derived.by(() => {
    if (!selectedDataset) return [];
    return configNames.map((cfg) => {
      const run = runMap[`${cfg}/${selectedDataset}`];
      const caseId = run?.caseId;

      // Get artifacts for this case
      const caseArtifacts = caseId
        ? artifactCatalog.filter(
            (a) =>
              a.datasetLabels.includes(selectedDataset) &&
              a.configLabels.includes(cfg),
          )
        : [];

      const plots = caseArtifacts.filter((a) => a.category === "plots");
      const reports = caseArtifacts.filter((a) => a.category === "reports");
      const code = caseArtifacts.filter((a) => a.category === "generated_code");

      return {
        config: cfg,
        run,
        verdict: run?.score?.verdict ?? null,
        requiredCoverage: run?.score?.required_coverage ?? null,
        plots,
        reports,
        code,
      };
    });
  });

  // Lightbox
  let lightboxSrc = $state(null);
  let lightboxLabel = $state("");

  function openLightbox(plot) {
    lightboxSrc = plot.content_url;
    lightboxLabel = plot.filename ?? "plot";
  }
</script>

<div class="flex flex-col gap-5">
  <div class="flex items-end gap-4 flex-wrap">
    <label class="flex flex-col gap-1.5 text-[0.78rem] font-semibold text-text-muted">
      <span>Dataset</span>
      <select class="min-w-[240px]" bind:value={selectedDataset}>
        {#each datasets as ds}
          <option value={ds}>{ds.replace(/_/g, " ")}</option>
        {/each}
      </select>
    </label>

    <div class="inline-flex gap-0.5 p-[3px] rounded-xl bg-bg-tertiary border border-border">
      <button
        class="py-[7px] px-4 rounded-lg border border-transparent bg-transparent text-text-muted text-[0.8rem] font-semibold transition-all duration-100 ease-out hover:text-text {compareType === 'plots' ? 'text-text bg-bg-secondary shadow-sm !border-border-subtle' : ''}"
        onclick={() => (compareType = "plots")}
      >Plots</button>
      <button
        class="py-[7px] px-4 rounded-lg border border-transparent bg-transparent text-text-muted text-[0.8rem] font-semibold transition-all duration-100 ease-out hover:text-text {compareType === 'reports' ? 'text-text bg-bg-secondary shadow-sm !border-border-subtle' : ''}"
        onclick={() => (compareType = "reports")}
      >Reports</button>
      <button
        class="py-[7px] px-4 rounded-lg border border-transparent bg-transparent text-text-muted text-[0.8rem] font-semibold transition-all duration-100 ease-out hover:text-text {compareType === 'code' ? 'text-text bg-bg-secondary shadow-sm !border-border-subtle' : ''}"
        onclick={() => (compareType = "code")}
      >Code</button>
    </div>
  </div>

  {#if columns.length === 0}
    <div class="py-12 px-6 text-center text-text-muted">Select a dataset to compare configs.</div>
  {:else}
    <div class="grid gap-3.5 items-start" style="grid-template-columns: repeat({columns.length}, minmax(0, 1fr))">
      {#each columns as col}
        <div class="flex flex-col border border-border rounded-xl bg-bg-secondary overflow-hidden shadow-sm">
          <div class="flex flex-col gap-2 p-4 border-b border-border bg-bg">
            <span class="text-[0.88rem] font-bold text-accent">{col.config}</span>
            {#if col.verdict}
              <span
                class="flex items-center gap-1.5 text-xs font-bold uppercase tracking-[0.04em]"
                style="color: {verdictColors[col.verdict] ?? 'var(--color-text-muted)'}"
              >
                <span class="w-[7px] h-[7px] rounded-full shrink-0" style="background: {verdictColors[col.verdict]}"></span>
                {displayVerdict(col.verdict)}
                {#if col.requiredCoverage != null && col.verdict !== "run_error"}
                  <span class="font-mono font-semibold text-[0.78rem] text-text ml-1">{Math.round(col.requiredCoverage * 100)}%</span>
                {/if}
              </span>
            {:else}
              <span class="flex items-center gap-1.5 text-xs font-bold uppercase tracking-[0.04em] text-text-faint">no data</span>
            {/if}
            {#if col.run && onSelectRun}
              <button class="self-start py-[5px] px-3 text-xs font-semibold text-accent bg-accent-soft border border-[color-mix(in_srgb,var(--color-accent)_20%,var(--color-border))] rounded-full transition-all duration-100 ease-out hover:bg-[color-mix(in_srgb,var(--color-accent)_12%,var(--color-bg-secondary))] hover:border-accent" onclick={() => onSelectRun(col.run)}>
                View detail
              </button>
            {/if}
          </div>

          <div class="p-3 flex flex-col gap-2 min-h-[120px]">
            {#if compareType === "plots"}
              {#if col.plots.length === 0}
                <div class="flex items-center justify-center min-h-[100px] text-text-faint text-[0.82rem]">No plots</div>
              {:else}
                <div class="flex flex-col gap-2">
                  {#each col.plots as plot}
                    <button
                      class="flex flex-col bg-bg border border-border rounded-lg overflow-hidden text-left cursor-zoom-in transition-all duration-100 ease-out hover:border-[color-mix(in_srgb,var(--color-accent)_40%,var(--color-border))] hover:shadow-sm"
                      type="button"
                      onclick={() => openLightbox(plot)}
                      title={plot.filename}
                    >
                      <img class="w-full h-auto block" src={plot.content_url} alt={plot.filename} loading="lazy" />
                      <span class="px-2 py-[5px] text-[0.68rem] font-mono text-text-faint border-t border-border">{plot.filename}</span>
                    </button>
                  {/each}
                </div>
              {/if}
            {:else if compareType === "reports"}
              {#if col.reports.length === 0}
                <div class="flex items-center justify-center min-h-[100px] text-text-faint text-[0.82rem]">No reports</div>
              {:else}
                {#each col.reports as report}
                  <div class="flex flex-col gap-1.5 p-3 bg-bg border border-border rounded-lg">
                    <span class="text-[0.85rem] font-semibold text-text">{report.title}</span>
                    <span class="text-[0.8rem] text-text-muted leading-normal line-clamp-4">{report.previewText}</span>
                  </div>
                {/each}
              {/if}
            {:else if compareType === "code"}
              {#if col.code.length === 0}
                <div class="flex items-center justify-center min-h-[100px] text-text-faint text-[0.82rem]">No generated code</div>
              {:else}
                {#each col.code as file}
                  <div class="flex flex-col gap-1 py-2.5 px-3 bg-bg border border-border rounded-lg">
                    <span class="font-mono text-[0.82rem] font-semibold text-text">{file.filename}</span>
                    <span class="font-mono text-[0.7rem] text-text-faint break-all">{file.path}</span>
                  </div>
                {/each}
              {/if}
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

{#if lightboxSrc}
  <Lightbox
    src={lightboxSrc}
    label={lightboxLabel}
    onClose={() => (lightboxSrc = null)}
  />
{/if}
