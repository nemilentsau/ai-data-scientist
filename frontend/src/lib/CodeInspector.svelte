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

<div class="flex flex-col gap-6">
  <div class="flex gap-3 items-end flex-wrap">
    <label>
      <span>Dataset</span>
      <select bind:value={filterDataset}>
        <option value="all">All datasets</option>
        {#each datasets as ds}
          <option value={ds}>{ds.replace(/_/g, " ")}</option>
        {/each}
      </select>
    </label>
    <label>
      <span>Config</span>
      <select bind:value={filterConfig}>
        <option value="all">All configs</option>
        {#each configs as cfg}
          <option value={cfg}>{cfg}</option>
        {/each}
      </select>
    </label>
    <span class="text-text-muted text-[0.85rem]">{filtered.length} files</span>
  </div>

  {#if groups.length === 0}
    <div class="py-12 px-6 text-center text-text-muted">No generated code files match the current filters.</div>
  {:else}
    {#each groups as [dataset, items]}
      <div>
        <div class="flex items-center gap-2.5 pb-2.5 border-b border-border mb-2">
          <h3 class="text-[0.92rem] font-bold capitalize text-text m-0">{dataset.replace(/_/g, " ")}</h3>
          <span class="text-[0.72rem] font-bold py-0.5 px-[9px] rounded-full bg-[color-mix(in_srgb,var(--color-purple)_10%,var(--color-bg))] text-purple">{items.length}</span>
        </div>

        <div class="flex flex-col gap-1.5">
          {#each items as artifact}
            <div
              class="code-item border border-border border-l-[3px] border-l-purple rounded-lg bg-bg-secondary overflow-hidden transition-all duration-100 ease-out"
              class:expanded={expandedId === artifact.artifact_id}
            >
              <button
                class="code-item-header flex items-center gap-3 w-full py-3 px-4 bg-none border-none text-left font-[inherit] transition-[background] duration-100 ease-out"
                type="button"
                onclick={() => toggleExpand(artifact)}
              >
                <span class="flex items-center justify-center w-[30px] h-[30px] rounded-md bg-[color-mix(in_srgb,var(--color-purple)_12%,var(--color-bg))] text-purple font-mono text-[0.72rem] font-bold shrink-0">py</span>
                <div class="flex-1 flex flex-col gap-0.5 min-w-0">
                  <span class="font-mono text-[0.88rem] font-semibold text-text">{artifact.filename}</span>
                  <span class="font-mono text-[0.72rem] text-text-faint overflow-hidden text-ellipsis whitespace-nowrap">{artifact.path}</span>
                </div>
                {#if artifact.configLabels.length > 0}
                  <span class="text-[0.68rem] font-semibold py-0.5 px-2 rounded-full bg-[color-mix(in_srgb,var(--color-cyan)_10%,var(--color-bg))] text-cyan whitespace-nowrap shrink-0">{artifact.configLabels[0]}</span>
                {/if}
                <span class="w-6 h-6 flex items-center justify-center text-[1.1rem] font-light text-text-faint shrink-0">{expandedId === artifact.artifact_id ? "\u2212" : "+"}</span>
              </button>

              {#if expandedId === artifact.artifact_id}
                <div class="border-t border-border">
                  {#if loadedContent[artifact.artifact_id]}
                    <CodeBlock
                      code={loadedContent[artifact.artifact_id]}
                      language="python"
                      maxLines={80}
                    />
                  {:else}
                    <div class="py-5 text-center text-text-muted text-[0.85rem]">Loading...</div>
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
  .code-item:hover {
    border-color: color-mix(in srgb, var(--color-purple) 30%, var(--color-border));
    border-left-color: var(--color-purple);
  }

  .code-item.expanded {
    border-color: var(--color-purple);
    border-left-color: var(--color-purple);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-purple) 6%, transparent);
  }

  .code-item-header:hover {
    background: color-mix(in srgb, var(--color-purple) 3%, var(--color-bg-secondary));
  }
</style>
