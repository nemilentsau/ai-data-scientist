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
</script>

<!-- svelte-ignore a11y_click_events_have_key_events a11y_interactive_supports_focus -->
<div
  class="lb-backdrop"
  role="dialog"
  aria-modal="true"
  tabindex="-1"
  onclick={(e) => e.target === e.currentTarget && onClose()}
  onkeydown={handleKeydown}
>
  <div class="lb-content">
    <div class="lb-header">
      <div class="lb-title">
        {#if sublabel}
          <span class="lb-sublabel">{sublabel}</span>
          <span class="lb-sep">/</span>
        {/if}
        <span class="lb-label">{label}</span>
      </div>
      <div class="lb-actions">
        {#if onPrev}
          <button class="lb-nav" onclick={onPrev} aria-label="Previous" disabled={!hasPrev}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M10 12L6 8l4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
        {/if}
        {#if onNext}
          <button class="lb-nav" onclick={onNext} aria-label="Next" disabled={!hasNext}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M6 4l4 4-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
        {/if}
        <button class="lb-close" onclick={onClose} aria-label="Close">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none"><path d="M13 5L5 13M5 5l8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
        </button>
      </div>
    </div>
    <div class="lb-body">
      <img {src} alt={label} />
    </div>
  </div>
</div>

<style>
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
    box-shadow: var(--shadow-lg, var(--shadow-md));
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
    gap: 16px;
  }

  .lb-title {
    display: flex;
    align-items: center;
    gap: 6px;
    overflow: hidden;
  }

  .lb-sublabel {
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: capitalize;
  }

  .lb-sep { color: var(--text-faint, var(--text-muted)); }

  .lb-label {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    color: var(--text-muted);
  }

  .lb-actions {
    display: flex;
    gap: 6px;
    flex-shrink: 0;
  }

  .lb-nav,
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
    transition: all var(--transition-fast, 120ms ease);
  }

  .lb-nav:disabled {
    opacity: 0.3;
    cursor: default;
  }

  .lb-nav:not(:disabled):hover {
    color: var(--accent);
    border-color: var(--accent);
  }

  .lb-close:hover {
    color: var(--red);
    border-color: var(--red);
    background: var(--red-soft, color-mix(in srgb, var(--red) 5%, var(--bg-secondary)));
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
    border-radius: var(--radius, 8px);
  }
</style>
