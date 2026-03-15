<script>
  let { code = "", language = "text", maxLines = 0 } = $props();
  let showAll = $state(false);

  let lines = $derived(code.split("\n"));
  let isTruncated = $derived(maxLines > 0 && lines.length > maxLines && !showAll);
  let displayCode = $derived(
    isTruncated ? lines.slice(0, maxLines).join("\n") : code
  );

  let lineNumbers = $derived(
    displayCode.split("\n").map((_, i) => i + 1)
  );

  let isDiff = $derived(language === "diff");
</script>

<div class="code-block">
  <div class="code-header">
    <span class="lang">{language}</span>
    <span class="line-count">{lines.length} lines</span>
  </div>
  <div class="code-content">
    <div class="line-nums" aria-hidden="true">
      {#each lineNumbers as n}
        <span>{n}</span>
      {/each}
    </div>
    <pre class="code-pre"><code>{#each displayCode.split("\n") as line, i}{#if isDiff}<span
      class={line.startsWith("+") ? "diff-add" : line.startsWith("-") ? "diff-del" : ""}
    >{line}</span>{:else}<span>{line}</span>{/if}{#if i < displayCode.split("\n").length - 1}{"\n"}{/if}{/each}</code></pre>
  </div>
  {#if isTruncated}
    <button class="show-more" onclick={() => (showAll = true)}>
      Show all {lines.length} lines
    </button>
  {/if}
</div>

<style>
  .code-block {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    background: var(--bg);
  }

  .code-header {
    display: flex;
    justify-content: space-between;
    padding: 4px 10px;
    background: var(--bg-tertiary);
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
  }

  .code-content {
    display: flex;
    overflow-x: auto;
  }

  .line-nums {
    display: flex;
    flex-direction: column;
    padding: 8px 0;
    min-width: 40px;
    text-align: right;
    user-select: none;
    color: var(--text-muted);
    opacity: 0.4;
    font-family: var(--font-mono);
    font-size: 0.8rem;
    line-height: 1.5;
    border-right: 1px solid var(--border);
  }

  .line-nums span {
    padding: 0 8px;
  }

  .code-pre {
    flex: 1;
    padding: 8px 12px;
    margin: 0;
    overflow-x: auto;
    font-size: 0.8rem;
    line-height: 1.5;
    white-space: pre;
    tab-size: 4;
  }

  .diff-add {
    background: color-mix(in srgb, var(--green) 12%, transparent);
    color: var(--green);
  }

  .diff-del {
    background: color-mix(in srgb, var(--red) 12%, transparent);
    color: var(--red);
  }

  .show-more {
    display: block;
    width: 100%;
    padding: 6px;
    background: var(--bg-tertiary);
    border: none;
    border-top: 1px solid var(--border);
    color: var(--accent);
    font-size: 0.75rem;
    transition: background 0.1s;
  }

  .show-more:hover {
    background: var(--bg-secondary);
  }
</style>
