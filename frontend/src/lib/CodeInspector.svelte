<script>
  import CodeBlock from "./CodeBlock.svelte";

  let { codeArtifacts = [], datasets = [], configs = [] } = $props();

  let filterDataset = $state("all");
  let filterConfig = $state("all");
  let expandedId = $state(null);
  let loadedContent = $state({});

  let filtered = $derived.by(() => {
    let items = codeArtifacts;
    if (filterDataset !== "all") {
      items = items.filter((a) => a.datasetLabels.includes(filterDataset));
    }
    if (filterConfig !== "all") {
      items = items.filter((a) => a.configLabels.includes(filterConfig));
    }
    return items;
  });

  let groups = $derived.by(() => {
    const map = {};
    for (const item of filtered) {
      const ds = item.datasetLabels[0] ?? "ungrouped";
      (map[ds] ??= []).push(item);
    }
    return Object.entries(map).sort(([a], [b]) => a.localeCompare(b));
  });

  async function toggleExpand(artifact) {
    if (expandedId === artifact.artifact_id) {
      expandedId = null;
      return;
    }
    expandedId = artifact.artifact_id;
    if (!loadedContent[artifact.artifact_id] && artifact.content_url) {
      try {
        const res = await fetch(artifact.content_url);
        const text = await res.text();
        loadedContent = { ...loadedContent, [artifact.artifact_id]: text };
      } catch {
        loadedContent = {
          ...loadedContent,
          [artifact.artifact_id]: "// Failed to load content",
        };
      }
    }
  }
</script>

<div class="inspector">
  <div class="inspector-controls">
    <label class="inspector-filter">
      <span>Dataset</span>
      <select bind:value={filterDataset}>
        <option value="all">All datasets</option>
        {#each datasets as ds}
          <option value={ds}>{ds.replace(/_/g, " ")}</option>
        {/each}
      </select>
    </label>
    <label class="inspector-filter">
      <span>Config</span>
      <select bind:value={filterConfig}>
        <option value="all">All configs</option>
        {#each configs as cfg}
          <option value={cfg}>{cfg}</option>
        {/each}
      </select>
    </label>
    <span class="inspector-count">{filtered.length} files</span>
  </div>

  {#if groups.length === 0}
    <div class="inspector-empty">No generated code files match the current filters.</div>
  {:else}
    {#each groups as [dataset, items]}
      <div class="inspector-group">
        <div class="inspector-group-header">
          <h3>{dataset.replace(/_/g, " ")}</h3>
          <span class="inspector-group-count">{items.length}</span>
        </div>

        <div class="inspector-list">
          {#each items as artifact}
            <div class="code-item" class:expanded={expandedId === artifact.artifact_id}>
              <button
                class="code-item-header"
                type="button"
                onclick={() => toggleExpand(artifact)}
              >
                <span class="code-icon">py</span>
                <div class="code-info">
                  <span class="code-filename">{artifact.filename}</span>
                  <span class="code-path">{artifact.path}</span>
                </div>
                {#if artifact.configLabels.length > 0}
                  <span class="code-config">{artifact.configLabels[0]}</span>
                {/if}
                <span class="code-expand-icon">{expandedId === artifact.artifact_id ? "−" : "+"}</span>
              </button>

              {#if expandedId === artifact.artifact_id}
                <div class="code-item-body">
                  {#if loadedContent[artifact.artifact_id]}
                    <CodeBlock
                      code={loadedContent[artifact.artifact_id]}
                      language="python"
                      maxLines={80}
                    />
                  {:else}
                    <div class="code-loading">Loading...</div>
                  {/if}
                </div>
              {/if}
            </div>
          {/each}
        </div>
      </div>
    {/each}
  {/if}
</div>

<style>
  .inspector {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .inspector-controls {
    display: flex;
    gap: 12px;
    align-items: flex-end;
    flex-wrap: wrap;
  }

  .inspector-filter {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }

  .inspector-filter span {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
  }

  .inspector-filter select {
    min-width: 180px;
    padding: 8px 12px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text);
    font-size: 0.85rem;
    transition: border-color var(--transition-fast);
  }

  .inspector-filter select:focus {
    border-color: var(--accent);
    outline: none;
  }

  .inspector-count {
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--text-muted);
    padding: 8px 0;
    margin-left: auto;
    font-variant-numeric: tabular-nums;
  }

  .inspector-empty {
    padding: 48px 24px;
    text-align: center;
    color: var(--text-muted);
  }

  /* ── Group ── */
  .inspector-group-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding-bottom: 10px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 8px;
  }

  .inspector-group-header h3 {
    font-size: 0.92rem;
    font-weight: 700;
    text-transform: capitalize;
    color: var(--text);
    margin: 0;
  }

  .inspector-group-count {
    font-size: 0.72rem;
    font-weight: 700;
    padding: 2px 9px;
    border-radius: 999px;
    background: color-mix(in srgb, var(--purple) 10%, var(--bg));
    color: var(--purple);
  }

  /* ── List ── */
  .inspector-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .code-item {
    border: 1px solid var(--border);
    border-left: 3px solid var(--purple);
    border-radius: var(--radius);
    background: var(--bg-secondary);
    overflow: hidden;
    transition: all var(--transition-fast);
  }

  .code-item:hover {
    border-color: color-mix(in srgb, var(--purple) 30%, var(--border));
    border-left-color: var(--purple);
  }

  .code-item.expanded {
    border-color: var(--purple);
    border-left-color: var(--purple);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--purple) 6%, transparent);
  }

  .code-item-header {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    padding: 12px 16px;
    background: none;
    border: none;
    text-align: left;
    font-family: inherit;
    transition: background var(--transition-fast);
  }

  .code-item-header:hover {
    background: color-mix(in srgb, var(--purple) 3%, var(--bg-secondary));
  }

  .code-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 30px;
    height: 30px;
    border-radius: 6px;
    background: color-mix(in srgb, var(--purple) 12%, var(--bg));
    color: var(--purple);
    font-family: var(--font-mono);
    font-size: 0.72rem;
    font-weight: 700;
    flex-shrink: 0;
  }

  .code-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  .code-filename {
    font-family: var(--font-mono);
    font-size: 0.88rem;
    font-weight: 600;
    color: var(--text);
  }

  .code-path {
    font-family: var(--font-mono);
    font-size: 0.72rem;
    color: var(--text-faint);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .code-config {
    font-size: 0.68rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 999px;
    background: color-mix(in srgb, var(--cyan) 10%, var(--bg));
    color: var(--cyan);
    white-space: nowrap;
    flex-shrink: 0;
  }

  .code-expand-icon {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.1rem;
    font-weight: 300;
    color: var(--text-faint);
    flex-shrink: 0;
  }

  .code-item-body {
    border-top: 1px solid var(--border);
  }

  .code-loading {
    padding: 20px;
    text-align: center;
    color: var(--text-muted);
    font-size: 0.85rem;
  }
</style>
