<script>
  import { toolColor } from "./parse.js";

  let { tools, activeTools, onToggle, onSelectAll, onSelectNone } = $props();
</script>

<div class="filters">
  <button class="meta-btn" onclick={onSelectAll}>All</button>
  <button class="meta-btn" onclick={onSelectNone}>None</button>
  {#each tools as tool}
    <button
      class="tool-btn"
      class:inactive={!activeTools.has(tool)}
      style="--tool-color: {toolColor(tool)}"
      onclick={() => onToggle(tool)}
    >
      {tool}
    </button>
  {/each}
</div>

<style>
  .filters {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    align-items: center;
  }

  .meta-btn {
    padding: 4px 10px;
    font-size: 0.75rem;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text-muted);
    transition: all 0.15s;
  }

  .meta-btn:hover {
    color: var(--text);
    border-color: var(--text-muted);
  }

  .tool-btn {
    padding: 4px 12px;
    font-size: 0.8rem;
    font-weight: 500;
    background: color-mix(in srgb, var(--tool-color) 15%, transparent);
    border: 1px solid color-mix(in srgb, var(--tool-color) 40%, transparent);
    border-radius: var(--radius);
    color: var(--tool-color);
    transition: all 0.15s;
  }

  .tool-btn:hover {
    background: color-mix(in srgb, var(--tool-color) 25%, transparent);
  }

  .tool-btn.inactive {
    opacity: 0.3;
    background: var(--bg-tertiary);
    border-color: var(--border);
    color: var(--text-muted);
  }
</style>
