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
    padding: 5px 11px;
    font-size: 0.75rem;
    font-weight: 600;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text-faint, var(--text-muted));
    transition: all var(--transition-fast, 120ms ease);
  }

  .meta-btn:hover {
    color: var(--text);
    border-color: var(--accent);
    background: var(--accent-soft, color-mix(in srgb, var(--accent) 5%, var(--bg-secondary)));
  }

  .tool-btn {
    padding: 5px 12px;
    font-size: 0.78rem;
    font-weight: 600;
    background: color-mix(in srgb, var(--tool-color) 8%, var(--bg-secondary));
    border: 1px solid color-mix(in srgb, var(--tool-color) 25%, var(--border));
    border-radius: 6px;
    color: var(--tool-color);
    transition: all var(--transition-fast, 120ms ease);
  }

  .tool-btn:hover {
    background: color-mix(in srgb, var(--tool-color) 14%, var(--bg-secondary));
    border-color: var(--tool-color);
    transform: translateY(-1px);
  }

  .tool-btn.inactive {
    opacity: 0.3;
    background: var(--bg);
    border-color: var(--border);
    color: var(--text-muted);
    transform: none;
  }
</style>
