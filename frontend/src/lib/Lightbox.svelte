<script>
  let {
    src,
    label = "",
    sublabel = "",
    onClose,
    onPrev = null,
    onNext = null,
    hasPrev = false,
    hasNext = false,
  } = $props();

  function handleKeydown(e) {
    if (e.key === "Escape") onClose();
    else if (e.key === "ArrowLeft" && onPrev && hasPrev) onPrev();
    else if (e.key === "ArrowRight" && onNext && hasNext) onNext();
  }

  function autoFocus(node) {
    node.focus();
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_interactive_supports_focus -->
<div
  class="fixed inset-0 z-[1000] bg-[rgba(10,12,20,0.75)] backdrop-blur-[8px] flex items-center justify-center p-6 animate-fade-in"
  role="dialog"
  aria-modal="true"
  tabindex="-1"
  use:autoFocus
  onclick={(e) => e.target === e.currentTarget && onClose()}
  onkeydown={handleKeydown}
>
  <div class="flex flex-col max-w-[95vw] max-h-[92vh] bg-bg-secondary border border-border rounded-2xl overflow-hidden shadow-lg animate-scale-in">
    <div class="flex items-center justify-between px-[18px] py-3 border-b border-border bg-bg shrink-0 gap-4">
      <div class="flex items-center gap-1.5 overflow-hidden">
        {#if sublabel}
          <span class="text-[0.82rem] font-semibold text-text-muted capitalize">{sublabel}</span>
          <span class="text-text-faint">/</span>
        {/if}
        <span class="font-mono text-[0.8rem] text-text-muted">{label}</span>
      </div>
      <div class="flex gap-1.5 shrink-0">
        {#if onPrev}
          <button
            class="flex items-center justify-center w-8 h-8 border border-border rounded-lg bg-bg-secondary text-text-muted transition-all duration-100 ease-out disabled:opacity-30 disabled:cursor-default hover:enabled:text-accent hover:enabled:border-accent"
            onclick={onPrev}
            aria-label="Previous"
            disabled={!hasPrev}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M10 12L6 8l4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
        {/if}
        {#if onNext}
          <button
            class="flex items-center justify-center w-8 h-8 border border-border rounded-lg bg-bg-secondary text-text-muted transition-all duration-100 ease-out disabled:opacity-30 disabled:cursor-default hover:enabled:text-accent hover:enabled:border-accent"
            onclick={onNext}
            aria-label="Next"
            disabled={!hasNext}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M6 4l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
        {/if}
        <button
          class="flex items-center justify-center w-8 h-8 border border-border rounded-lg bg-bg-secondary text-text-muted transition-all duration-100 ease-out hover:text-red hover:border-red hover:bg-red-soft"
          onclick={onClose}
          aria-label="Close"
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M13 5L5 13M5 5l8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
        </button>
      </div>
    </div>
    <div class="overflow-auto p-4 flex items-center justify-center bg-bg">
      <img class="max-w-full max-h-[82vh] object-contain rounded-lg" {src} alt={label} />
    </div>
  </div>
</div>
