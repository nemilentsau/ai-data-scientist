<script>
  import { toolColor } from "./parse.js";

  let { tools, activeTools, onToggle, onSelectAll, onSelectNone } = $props();
</script>

<div class="flex gap-1.5 flex-wrap items-center">
  <button
    class="px-[11px] py-[5px] text-xs font-semibold bg-bg-secondary border border-border rounded-md text-text-faint transition-all duration-100 ease-out hover:text-text hover:border-accent hover:bg-accent-soft"
    onclick={onSelectAll}
  >All</button>
  <button
    class="px-[11px] py-[5px] text-xs font-semibold bg-bg-secondary border border-border rounded-md text-text-faint transition-all duration-100 ease-out hover:text-text hover:border-accent hover:bg-accent-soft"
    onclick={onSelectNone}
  >None</button>
  {#each tools as tool}
    <button
      class="tool-btn px-3 py-[5px] text-[0.78rem] font-semibold rounded-md transition-all duration-100 ease-out {activeTools.has(tool) ? 'hover:-translate-y-px' : 'opacity-30 bg-bg border-border text-text-muted'}"
      style="--tool-color: {toolColor(tool)}"
      onclick={() => onToggle(tool)}
    >
      {tool}
    </button>
  {/each}
</div>

<style>
  .tool-btn:not(.opacity-30) {
    background: color-mix(in srgb, var(--tool-color) 8%, var(--color-bg-secondary));
    border: 1px solid color-mix(in srgb, var(--tool-color) 25%, var(--color-border));
    color: var(--tool-color);
  }

  .tool-btn:not(.opacity-30):hover {
    background: color-mix(in srgb, var(--tool-color) 14%, var(--color-bg-secondary));
    border-color: var(--tool-color);
  }

  .tool-btn.opacity-30 {
    border: 1px solid var(--color-border);
    transform: none;
  }
</style>
