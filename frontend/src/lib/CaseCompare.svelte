<script>
  let { artifactCatalog = [], datasets = [], configNames = [], runMap = {}, onSelectRun = null } = $props();

  let selectedDataset = $state("");
  let compareType = $state("plots");

  // Auto-select first dataset
  $effect(() => {
    if (datasets.length > 0 && (!selectedDataset || !datasets.includes(selectedDataset))) {
      selectedDataset = datasets[0];
    }
  });

  const verdictColors = {
    solved: "var(--green)",
    partial: "var(--orange)",
    wrong: "var(--red)",
    failed: "var(--red)",
    run_error: "var(--red)",
  };

  function displayVerdict(verdict) {
    return verdict === "run_error" ? "run error" : verdict;
  }

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

<div class="compare">
  <div class="compare-controls">
    <label class="compare-select">
      <span>Dataset</span>
      <select bind:value={selectedDataset}>
        {#each datasets as ds}
          <option value={ds}>{ds.replace(/_/g, " ")}</option>
        {/each}
      </select>
    </label>

    <div class="compare-type-switch">
      <button
        class="type-pill"
        class:active={compareType === "plots"}
        onclick={() => (compareType = "plots")}
      >Plots</button>
      <button
        class="type-pill"
        class:active={compareType === "reports"}
        onclick={() => (compareType = "reports")}
      >Reports</button>
      <button
        class="type-pill"
        class:active={compareType === "code"}
        onclick={() => (compareType = "code")}
      >Code</button>
    </div>
  </div>

  {#if columns.length === 0}
    <div class="compare-empty">Select a dataset to compare configs.</div>
  {:else}
    <div class="compare-grid" style="grid-template-columns: repeat({columns.length}, minmax(0, 1fr))">
      {#each columns as col}
        <div class="compare-col">
          <div class="col-header">
            <span class="col-config">{col.config}</span>
            {#if col.verdict}
              <span
                class="col-verdict"
                style="color: {verdictColors[col.verdict] ?? 'var(--text-muted)'}"
              >
                <span class="col-verdict-dot" style="background: {verdictColors[col.verdict]}"></span>
                {displayVerdict(col.verdict)}
                {#if col.requiredCoverage != null && col.verdict !== "run_error"}
                  <span class="col-coverage">{Math.round(col.requiredCoverage * 100)}%</span>
                {/if}
              </span>
            {:else}
              <span class="col-verdict" style="color: var(--text-faint)">no data</span>
            {/if}
            {#if col.run && onSelectRun}
              <button class="col-detail-btn" onclick={() => onSelectRun(col.run)}>
                View detail
              </button>
            {/if}
          </div>

          <div class="col-body">
            {#if compareType === "plots"}
              {#if col.plots.length === 0}
                <div class="col-empty">No plots</div>
              {:else}
                <div class="col-plots">
                  {#each col.plots as plot}
                    <button
                      class="col-plot-thumb"
                      type="button"
                      onclick={() => openLightbox(plot)}
                      title={plot.filename}
                    >
                      <img src={plot.content_url} alt={plot.filename} loading="lazy" />
                      <span class="col-plot-name">{plot.filename}</span>
                    </button>
                  {/each}
                </div>
              {/if}
            {:else if compareType === "reports"}
              {#if col.reports.length === 0}
                <div class="col-empty">No reports</div>
              {:else}
                {#each col.reports as report}
                  <div class="col-report-card">
                    <span class="col-report-title">{report.title}</span>
                    <span class="col-report-preview">{report.previewText}</span>
                  </div>
                {/each}
              {/if}
            {:else if compareType === "code"}
              {#if col.code.length === 0}
                <div class="col-empty">No generated code</div>
              {:else}
                {#each col.code as file}
                  <div class="col-code-card">
                    <span class="col-code-name">{file.filename}</span>
                    <span class="col-code-path">{file.path}</span>
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
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_interactive_supports_focus -->
  <div
    class="lb-backdrop"
    role="dialog"
    aria-modal="true"
    tabindex="-1"
    onclick={(e) => e.target === e.currentTarget && (lightboxSrc = null)}
    onkeydown={(e) => e.key === "Escape" && (lightboxSrc = null)}
  >
    <div class="lb-content">
      <div class="lb-header">
        <span class="lb-filename">{lightboxLabel}</span>
        <button class="lb-close" onclick={() => (lightboxSrc = null)} aria-label="Close">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M13 5L5 13M5 5l8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
        </button>
      </div>
      <div class="lb-body">
        <img src={lightboxSrc} alt={lightboxLabel} />
      </div>
    </div>
  </div>
{/if}

<style>
  .compare {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .compare-controls {
    display: flex;
    align-items: flex-end;
    gap: 16px;
    flex-wrap: wrap;
  }

  .compare-select {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .compare-select span {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
  }

  .compare-select select {
    min-width: 240px;
    padding: 9px 12px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    font-size: 0.88rem;
    transition: border-color var(--transition-fast);
  }

  .compare-select select:focus {
    border-color: var(--accent);
    outline: none;
  }

  .compare-type-switch {
    display: inline-flex;
    gap: 2px;
    padding: 3px;
    border-radius: var(--radius-lg);
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
  }

  .type-pill {
    padding: 7px 16px;
    border-radius: var(--radius);
    border: 1px solid transparent;
    background: transparent;
    color: var(--text-muted);
    font-size: 0.8rem;
    font-weight: 600;
    transition: all var(--transition-fast);
  }

  .type-pill:hover { color: var(--text); }

  .type-pill.active {
    color: var(--text);
    background: var(--bg-secondary);
    box-shadow: var(--shadow-sm);
    border-color: var(--border-subtle);
  }

  .compare-empty {
    padding: 48px 24px;
    text-align: center;
    color: var(--text-muted);
  }

  /* ── Grid ── */
  .compare-grid {
    display: grid;
    gap: 14px;
    align-items: start;
  }

  .compare-col {
    display: flex;
    flex-direction: column;
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    background: var(--bg-secondary);
    overflow: hidden;
    box-shadow: var(--shadow-sm);
  }

  .col-header {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 16px;
    border-bottom: 1px solid var(--border);
    background: var(--bg);
  }

  .col-config {
    font-size: 0.88rem;
    font-weight: 700;
    color: var(--accent);
  }

  .col-verdict {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .col-verdict-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .col-coverage {
    font-family: var(--font-mono);
    font-weight: 600;
    font-size: 0.78rem;
    color: var(--text);
    margin-left: 4px;
  }

  .col-detail-btn {
    align-self: flex-start;
    padding: 5px 12px;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--accent);
    background: var(--accent-soft);
    border: 1px solid color-mix(in srgb, var(--accent) 20%, var(--border));
    border-radius: 999px;
    transition: all var(--transition-fast);
  }

  .col-detail-btn:hover {
    background: color-mix(in srgb, var(--accent) 12%, var(--bg-secondary));
    border-color: var(--accent);
  }

  .col-body {
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-height: 120px;
  }

  .col-empty {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100px;
    color: var(--text-faint);
    font-size: 0.82rem;
  }

  /* Plots in compare */
  .col-plots {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .col-plot-thumb {
    display: flex;
    flex-direction: column;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    text-align: left;
    cursor: zoom-in;
    transition: all var(--transition-fast);
  }

  .col-plot-thumb:hover {
    border-color: color-mix(in srgb, var(--accent) 40%, var(--border));
    box-shadow: var(--shadow-sm);
  }

  .col-plot-thumb img {
    width: 100%;
    height: auto;
    display: block;
  }

  .col-plot-name {
    padding: 5px 8px;
    font-size: 0.68rem;
    font-family: var(--font-mono);
    color: var(--text-faint);
    border-top: 1px solid var(--border);
  }

  /* Reports in compare */
  .col-report-card {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 12px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }

  .col-report-title {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text);
  }

  .col-report-preview {
    font-size: 0.8rem;
    color: var(--text-muted);
    line-height: 1.5;
    display: -webkit-box;
    -webkit-line-clamp: 4;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  /* Code in compare */
  .col-code-card {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 10px 12px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }

  .col-code-name {
    font-family: var(--font-mono);
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--text);
  }

  .col-code-path {
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: var(--text-faint);
    overflow-wrap: anywhere;
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
  }

  .lb-filename {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    color: var(--text-muted);
  }

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
