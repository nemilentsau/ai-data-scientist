<script>
  let { plots, resultsDir } = $props();
  let selectedPlot = $state(null);

  function shortName(path) {
    return path.split("/").pop();
  }
</script>

<div class="gallery">
  {#if plots.length === 0}
    <p class="empty">No plot files detected in trace</p>
  {:else}
    <p class="hint">
      Plot paths extracted from trace. To view, serve the results directory or
      drop PNG files here.
    </p>
    <div class="grid">
      {#each plots as plot}
        <button class="plot-card" onclick={() => (selectedPlot = plot)}>
          <div class="plot-placeholder">
            <span class="plot-icon">&#128202;</span>
          </div>
          <div class="plot-name">{shortName(plot)}</div>
          <div class="plot-path">{plot}</div>
        </button>
      {/each}
    </div>
  {/if}
</div>

{#if selectedPlot}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="lightbox"
    role="dialog"
    aria-modal="true"
    tabindex="-1"
    onclick={() => (selectedPlot = null)}
    onkeydown={(e) => e.key === "Escape" && (selectedPlot = null)}
  >
    <div class="lightbox-content" role="presentation" onclick={(e) => e.stopPropagation()}>
      <div class="lightbox-header">
        <span>{shortName(selectedPlot)}</span>
        <button onclick={() => (selectedPlot = null)}>x</button>
      </div>
      <div class="lightbox-body">
        <div class="plot-full-placeholder">
          <span class="plot-icon-lg">&#128202;</span>
          <p class="path-display">{selectedPlot}</p>
          <p class="serve-hint">
            Serve with: <code>python -m http.server -d results/</code>
          </p>
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  .gallery {
    padding: 16px 0;
  }

  .hint {
    color: var(--text-muted);
    font-size: 0.85rem;
    margin-bottom: 16px;
  }

  .empty {
    text-align: center;
    color: var(--text-muted);
    padding: 40px;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 12px;
  }

  .plot-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    overflow: hidden;
    cursor: pointer;
    transition: all 0.15s;
  }

  .plot-card:hover {
    border-color: var(--accent);
    transform: translateY(-2px);
  }

  .plot-placeholder {
    height: 140px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-tertiary);
  }

  .plot-icon {
    font-size: 2.5rem;
    opacity: 0.3;
  }

  .plot-name {
    padding: 8px 12px 2px;
    font-weight: 600;
    font-size: 0.85rem;
  }

  .plot-path {
    padding: 0 12px 8px;
    font-size: 0.7rem;
    color: var(--text-muted);
    font-family: var(--font-mono);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .lightbox {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.8);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 24px;
  }

  .lightbox-content {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    max-width: 900px;
    width: 100%;
    overflow: hidden;
  }

  .lightbox-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 16px;
    border-bottom: 1px solid var(--border);
    font-weight: 600;
    font-size: 0.9rem;
  }

  .lightbox-header button {
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text-muted);
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .lightbox-body {
    padding: 24px;
  }

  .plot-full-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 40px;
    color: var(--text-muted);
  }

  .plot-icon-lg {
    font-size: 4rem;
    opacity: 0.2;
  }

  .path-display {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    background: var(--bg);
    padding: 6px 12px;
    border-radius: var(--radius);
  }

  .serve-hint {
    font-size: 0.75rem;
    opacity: 0.6;
  }

  .serve-hint code {
    background: var(--bg);
    padding: 2px 6px;
    border-radius: 3px;
  }
</style>
