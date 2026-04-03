<script>
  import Lightbox from "./Lightbox.svelte";

  let { plots = [], datasets = [], configs = [] } = $props();

  let filterDataset = $state("all");
  let filterConfig = $state("all");
  let search = $state("");
  let lightboxSrc = $state(null);
  let lightboxLabel = $state("");
  let lightboxDataset = $state("");

  let filtered = $derived.by(() => {
    let items = plots;
    if (filterDataset !== "all") {
      items = items.filter((p) => p.datasetLabels.includes(filterDataset));
    }
    if (filterConfig !== "all") {
      items = items.filter((p) => p.configLabels.includes(filterConfig));
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      items = items.filter(
        (p) =>
          (p.filename ?? "").toLowerCase().includes(q) ||
          p.datasetLabels.some((d) => d.toLowerCase().includes(q)) ||
          p.configLabels.some((c) => c.toLowerCase().includes(q)),
      );
    }
    return items;
  });

  let groups = $derived.by(() => {
    const map = {};
    for (const plot of filtered) {
      const ds = plot.datasetLabels[0] ?? "ungrouped";
      (map[ds] ??= []).push(plot);
    }
    return Object.entries(map).sort(([a], [b]) => a.localeCompare(b));
  });

  let totalCount = $derived(filtered.length);

  function openLightbox(plot) {
    lightboxSrc = plot.content_url;
    lightboxLabel = plot.filename ?? "plot";
    lightboxDataset = plot.datasetLabels[0] ?? "";
  }

  // Navigate between plots in lightbox
  function navigateLightbox(delta) {
    if (!lightboxSrc) return;
    const idx = filtered.findIndex((p) => p.content_url === lightboxSrc);
    if (idx === -1) return;
    const next = idx + delta;
    if (next >= 0 && next < filtered.length) {
      openLightbox(filtered[next]);
    }
  }
</script>

<div class="flex flex-col gap-6">
  <div class="flex flex-col gap-3">
    <input
      class="w-full px-3.5 py-2.5 bg-bg border border-border rounded-lg text-text text-[0.9rem] font-[inherit] outline-none transition-all duration-100 ease-out placeholder:text-text-faint focus:border-accent focus:shadow-[0_0_0_3px_color-mix(in_srgb,var(--color-accent)_10%,transparent)]"
      type="text"
      placeholder="Filter by filename, dataset, or config..."
      bind:value={search}
    />
    <div class="flex gap-3 items-end flex-wrap">
      <label class="flex flex-col gap-1.5">
        <span class="text-[0.7rem] font-semibold uppercase tracking-[0.06em] text-text-muted">Dataset</span>
        <select class="min-w-[180px] px-3 py-2 bg-bg border border-border rounded-lg text-text text-[0.85rem] transition-[border-color] duration-100 ease-out focus:border-accent focus:outline-none" bind:value={filterDataset}>
          <option value="all">All datasets</option>
          {#each datasets as ds}
            <option value={ds}>{ds.replace(/_/g, " ")}</option>
          {/each}
        </select>
      </label>
      <label class="flex flex-col gap-1.5">
        <span class="text-[0.7rem] font-semibold uppercase tracking-[0.06em] text-text-muted">Config</span>
        <select class="min-w-[180px] px-3 py-2 bg-bg border border-border rounded-lg text-text text-[0.85rem] transition-[border-color] duration-100 ease-out focus:border-accent focus:outline-none" bind:value={filterConfig}>
          <option value="all">All configs</option>
          {#each configs as cfg}
            <option value={cfg}>{cfg}</option>
          {/each}
        </select>
      </label>
      <span class="text-[0.82rem] font-semibold text-text-muted py-2 ml-auto tabular-nums">{totalCount} plots</span>
    </div>
  </div>

  {#if groups.length === 0}
    <div class="py-12 px-6 text-center text-text-muted">No plots match the current filters.</div>
  {:else}
    {#each groups as [dataset, items]}
      <div>
        <div class="flex items-center gap-2.5 pb-2.5 border-b border-border mb-3">
          <h3 class="text-[0.92rem] font-bold capitalize text-text m-0">{dataset.replace(/_/g, " ")}</h3>
          <span class="text-[0.72rem] font-bold px-[9px] py-0.5 rounded-full bg-accent-soft text-accent">{items.length}</span>
        </div>
        <div class="grid grid-cols-[repeat(auto-fill,minmax(200px,1fr))] gap-2.5">
          {#each items as plot}
            <button
              class="flex flex-col bg-bg-secondary border border-border rounded-lg overflow-hidden cursor-zoom-in transition-all duration-200 ease-out text-left hover:border-[color-mix(in_srgb,var(--color-accent)_40%,var(--color-border))] hover:shadow-md hover:-translate-y-0.5"
              type="button"
              onclick={() => openLightbox(plot)}
              title="{plot.filename} — {plot.configLabels.join(', ')}"
            >
              <img
                class="w-full aspect-[4/3] object-contain bg-bg block"
                src={plot.content_url}
                alt={plot.filename}
                loading="lazy"
              />
              <div class="flex justify-between items-center gap-1.5 px-2.5 py-1.5 border-t border-border min-h-[30px]">
                <span class="text-[0.7rem] font-mono text-text-muted overflow-hidden text-ellipsis whitespace-nowrap">{plot.filename}</span>
                {#if plot.configLabels.length > 0}
                  <span class="text-[0.65rem] font-semibold px-1.5 py-px rounded-full bg-cyan/10 text-cyan whitespace-nowrap shrink-0">{plot.configLabels[0]}</span>
                {/if}
              </div>
            </button>
          {/each}
        </div>
      </div>
    {/each}
  {/if}
</div>

{#if lightboxSrc}
  {@const idx = filtered.findIndex((p) => p.content_url === lightboxSrc)}
  <Lightbox
    src={lightboxSrc}
    label={lightboxLabel}
    sublabel={lightboxDataset ? lightboxDataset.replace(/_/g, " ") : ""}
    onClose={() => (lightboxSrc = null)}
    onPrev={() => navigateLightbox(-1)}
    onNext={() => navigateLightbox(1)}
    hasPrev={idx > 0}
    hasNext={idx < filtered.length - 1}
  />
{/if}
