<script>
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
      <label class="gallery-filter">
        <span>Dataset</span>
        <select bind:value={filterDataset}>
          <option value="all">All datasets</option>
          {#each datasets as ds}
            <option value={ds}>{ds.replace(/_/g, " ")}</option>
          {/each}
        </select>
      </label>
      <label class="gallery-filter">
        <span>Config</span>
        <select bind:value={filterConfig}>
          <option value="all">All configs</option>
          {#each configs as cfg}
            <option value={cfg}>{cfg}</option>
          {/each}
        </select>
      </label>
      <span class="gallery-count">{totalCount} plots</span>
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
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_interactive_supports_focus -->
  <div
    class="lb-backdrop"
    role="dialog"
    aria-modal="true"
    tabindex="-1"
    onclick={(e) => e.target === e.currentTarget && (lightboxSrc = null)}
    onkeydown={(e) => {
      if (e.key === "Escape") lightboxSrc = null;
      else if (e.key === "ArrowLeft") navigateLightbox(-1);
      else if (e.key === "ArrowRight") navigateLightbox(1);
    }}
  >
    <div class="lb-content">
      <div class="lb-header">
        <div class="lb-title">
          {#if lightboxDataset}
            <span class="lb-dataset">{lightboxDataset.replace(/_/g, " ")}</span>
            <span class="lb-sep">/</span>
          {/if}
          <span class="lb-filename">{lightboxLabel}</span>
        </div>
        <div class="lb-actions">
          <button class="lb-nav" onclick={() => navigateLightbox(-1)} aria-label="Previous" disabled={filtered.findIndex(p => p.content_url === lightboxSrc) <= 0}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M10 12L6 8l4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
          <button class="lb-nav" onclick={() => navigateLightbox(1)} aria-label="Next" disabled={filtered.findIndex(p => p.content_url === lightboxSrc) >= filtered.length - 1}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M6 4l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
          <button class="lb-close" onclick={() => (lightboxSrc = null)} aria-label="Close">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M13 5L5 13M5 5l8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </button>
        </div>
      </div>
      <div class="lb-body">
        <img src={lightboxSrc} alt={lightboxLabel} />
      </div>
    </div>
  </div>
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

  .gallery-filter {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .gallery-filter span {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
  }

  .gallery-filter select {
    min-width: 180px;
    padding: 8px 12px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    font-size: 0.85rem;
    transition: border-color var(--transition-fast);
  }

  .gallery-filter select:focus {
    border-color: var(--accent);
    outline: none;
  }

  .gallery-count {
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--text-muted);
    padding: 8px 0;
    margin-left: auto;
    font-variant-numeric: tabular-nums;
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

  /* ── Lightbox ── */
  .lb-backdrop {
    position: fixed;
    inset: 0;
    z-index: 1000;
    background: rgba(10, 12, 20, 0.75);
    backdrop-filter: blur(8px);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    animation: lbFade 150ms ease;
  }

  @keyframes lbFade {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .lb-content {
    display: flex;
    flex-direction: column;
    max-width: 95vw;
    max-height: 92vh;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 16px;
    overflow: hidden;
    box-shadow: var(--shadow-lg);
    animation: lbScale 200ms cubic-bezier(0.16, 1, 0.3, 1);
  }

  @keyframes lbScale {
    from { opacity: 0; transform: scale(0.95); }
    to { opacity: 1; transform: scale(1); }
  }

  .lb-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 18px;
    border-bottom: 1px solid var(--border);
    background: var(--bg);
    flex-shrink: 0;
    gap: 16px;
  }

  .lb-title {
    display: flex;
    align-items: center;
    gap: 6px;
    overflow: hidden;
  }

  .lb-dataset {
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: capitalize;
  }

  .lb-sep { color: var(--text-faint); }

  .lb-filename {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    color: var(--text-muted);
  }

  .lb-actions {
    display: flex;
    gap: 6px;
    flex-shrink: 0;
  }

  .lb-nav,
  .lb-close {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--bg-secondary);
    color: var(--text-muted);
    transition: all var(--transition-fast);
  }

  .lb-nav:disabled {
    opacity: 0.3;
    cursor: default;
  }

  .lb-nav:not(:disabled):hover {
    color: var(--accent);
    border-color: var(--accent);
  }

  .lb-close:hover {
    color: var(--red);
    border-color: var(--red);
    background: var(--red-soft);
  }

  .lb-body {
    overflow: auto;
    padding: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg);
  }

  .lb-body img {
    max-width: 100%;
    max-height: 82vh;
    object-fit: contain;
    border-radius: var(--radius);
  }
</style>
