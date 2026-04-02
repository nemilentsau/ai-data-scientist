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

<div class="gallery">
  <div class="gallery-controls">
    <input
      class="gallery-search"
      type="text"
      placeholder="Filter by filename, dataset, or config..."
      bind:value={search}
    />
    <div class="gallery-filters">
      <label class="filter-group">
        <span>Dataset</span>
        <select bind:value={filterDataset}>
          <option value="all">All datasets</option>
          {#each datasets as ds}
            <option value={ds}>{ds.replace(/_/g, " ")}</option>
          {/each}
        </select>
      </label>
      <label class="filter-group">
        <span>Config</span>
        <select bind:value={filterConfig}>
          <option value="all">All configs</option>
          {#each configs as cfg}
            <option value={cfg}>{cfg}</option>
          {/each}
        </select>
      </label>
      <span class="section-count">{totalCount} plots</span>
    </div>
  </div>

  {#if groups.length === 0}
    <div class="gallery-empty">No plots match the current filters.</div>
  {:else}
    {#each groups as [dataset, items]}
      <div class="gallery-group">
        <div class="gallery-group-header">
          <h3>{dataset.replace(/_/g, " ")}</h3>
          <span class="gallery-group-count">{items.length}</span>
        </div>
        <div class="gallery-grid">
          {#each items as plot}
            <button
              class="gallery-thumb"
              type="button"
              onclick={() => openLightbox(plot)}
              title="{plot.filename} — {plot.configLabels.join(', ')}"
            >
              <img
                src={plot.content_url}
                alt={plot.filename}
                loading="lazy"
              />
              <div class="thumb-footer">
                <span class="thumb-name">{plot.filename}</span>
                {#if plot.configLabels.length > 0}
                  <span class="thumb-config">{plot.configLabels[0]}</span>
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

<style>
  .gallery {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .gallery-controls {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .gallery-search {
    width: 100%;
    padding: 10px 14px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    font-size: 0.9rem;
    font-family: inherit;
    outline: none;
    transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
  }

  .gallery-search::placeholder { color: var(--text-faint); }

  .gallery-search:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 10%, transparent);
  }

  .gallery-filters {
    display: flex;
    gap: 12px;
    align-items: flex-end;
    flex-wrap: wrap;
  }


  .gallery-empty {
    padding: 48px 24px;
    text-align: center;
    color: var(--text-muted);
  }

  /* ── Group ── */
  .gallery-group-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 12px;
  }

  .gallery-group-header h3 {
    font-size: 0.92rem;
    font-weight: 700;
    text-transform: capitalize;
    color: var(--text);
    margin: 0;
  }

  .gallery-group-count {
    font-size: 0.72rem;
    font-weight: 700;
    padding: 2px 9px;
    border-radius: 999px;
    background: var(--accent-soft);
    color: var(--accent);
  }

  /* ── Thumbnail Grid ── */
  .gallery-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 10px;
  }

  .gallery-thumb {
    display: flex;
    flex-direction: column;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    cursor: zoom-in;
    transition: all var(--transition-normal);
    text-align: left;
  }

  .gallery-thumb:hover {
    border-color: color-mix(in srgb, var(--accent) 40%, var(--border));
    box-shadow: var(--shadow-md);
    transform: translateY(-2px);
  }

  .gallery-thumb img {
    width: 100%;
    aspect-ratio: 4 / 3;
    object-fit: contain;
    background: var(--bg);
    display: block;
  }

  .thumb-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    border-top: 1px solid var(--border);
    min-height: 30px;
  }

  .thumb-name {
    font-size: 0.7rem;
    font-family: var(--font-mono);
    color: var(--text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .thumb-config {
    font-size: 0.65rem;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 999px;
    background: color-mix(in srgb, var(--cyan) 10%, var(--bg));
    color: var(--cyan);
    white-space: nowrap;
    flex-shrink: 0;
  }

</style>
