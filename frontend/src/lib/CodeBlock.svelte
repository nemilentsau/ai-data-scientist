<script>
  let { code = "", language = "text", maxLines = 0 } = $props();
  let showAll = $state(false);

  let lines = $derived(code.split("\n"));
  let isTruncated = $derived(maxLines > 0 && lines.length > maxLines && !showAll);
  let displayCode = $derived(
    isTruncated ? lines.slice(0, maxLines).join("\n") : code
  );

  let displayLines = $derived(displayCode.split("\n"));
  let lineNumbers = $derived(displayLines.map((_, i) => i + 1));
  let isDiff = $derived(language === "diff");
</script>

<div class="border border-border rounded-lg overflow-hidden bg-bg">
  <div class="flex justify-between px-3 py-1.5 bg-bg-tertiary text-[0.67rem] font-semibold uppercase tracking-[0.06em] text-text-faint border-b border-border">
    <span>{language}</span>
    <span>{lines.length} lines</span>
  </div>
  <div class="flex overflow-x-auto">
    <div class="flex flex-col py-2.5 min-w-[42px] text-right select-none text-text-muted opacity-40 font-mono text-[0.8rem] leading-[1.5] border-r border-border bg-bg-tertiary" aria-hidden="true">
      {#each lineNumbers as n}
        <span class="px-2">{n}</span>
      {/each}
    </div>
    <pre class="flex-1 px-3.5 py-2.5 m-0 overflow-x-auto text-[0.8rem] leading-[1.5] whitespace-pre tab-[4] text-text"><code>{#each displayLines as line, i}{#if isDiff}<span
      class={line.startsWith("+") ? "bg-green/10 text-green" : line.startsWith("-") ? "bg-red/10 text-red" : ""}
    >{line}</span>{:else}<span>{line}</span>{/if}{#if i < displayLines.length - 1}{"\n"}{/if}{/each}</code></pre>
  </div>
  {#if isTruncated}
    <button
      class="block w-full py-[7px] bg-bg-tertiary border-0 border-t border-solid border-border text-accent text-[0.78rem] font-semibold transition-[background] duration-100 hover:bg-[color-mix(in_srgb,var(--color-accent)_5%,var(--color-bg-secondary))]"
      onclick={() => (showAll = true)}
    >
      Show all {lines.length} lines
    </button>
  {/if}
</div>
