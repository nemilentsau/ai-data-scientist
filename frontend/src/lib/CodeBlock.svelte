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
    padding: 6px 12px;
    background: var(--bg-tertiary);
    font-size: 0.67rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-faint, var(--text-muted));
    border-bottom: 1px solid var(--border);
  }

  .code-content {
    display: flex;
    overflow-x: auto;
  }

  .line-nums {
    display: flex;
    flex-direction: column;
    padding: 10px 0;
    min-width: 42px;
    text-align: right;
    user-select: none;
    color: var(--text-muted);
    opacity: 0.4;
    font-family: var(--font-mono);
    font-size: 0.8rem;
    line-height: 1.5;
    border-right: 1px solid var(--border);
    background: var(--bg-tertiary);
  }

  .line-nums span {
    padding: 0 8px;
  }

  .code-pre {
    flex: 1;
    padding: 10px 14px;
    margin: 0;
    overflow-x: auto;
    font-size: 0.8rem;
    line-height: 1.5;
    white-space: pre;
    tab-size: 4;
    color: var(--text);
  }

  .diff-add {
    background: color-mix(in srgb, var(--green) 10%, transparent);
    color: var(--green);
  }

  .diff-del {
    background: color-mix(in srgb, var(--red) 10%, transparent);
    color: var(--red);
  }

  .show-more {
    display: block;
    width: 100%;
    padding: 7px;
    background: var(--bg-tertiary);
    border: none;
    border-top: 1px solid var(--border);
    color: var(--accent);
    font-size: 0.78rem;
    font-weight: 600;
    transition: background 0.1s;
  }

  .show-more:hover {
    background: color-mix(in srgb, var(--accent) 5%, var(--bg-secondary));
  }
</style>
