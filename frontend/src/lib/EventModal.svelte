<script>
  let { event, onClose } = $props();

  let json = $derived(JSON.stringify(event, null, 2));

  function handleKeydown(e) {
    if (e.key === "Escape") onClose();
  }

  function handleBackdropClick(e) {
    if (e.target === e.currentTarget) onClose();
  }
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- svelte-ignore a11y_click_events_have_key_events a11y_interactive_supports_focus -->
<div
  class="backdrop"
  role="dialog"
  aria-modal="true"
  tabindex="-1"
  onclick={handleBackdropClick}
>
  <div class="modal">
    <div class="modal-header">
      <h3>Event Detail — {event.tool}</h3>
      <button class="close-btn" onclick={onClose}>x</button>
    </div>
    <div class="modal-body">
      <pre><code>{json}</code></pre>
    </div>
  </div>
</div>

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 24px;
  }

  .modal {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    max-width: 900px;
    width: 100%;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
  }

  .modal-header h3 {
    font-size: 0.95rem;
    font-weight: 600;
  }

  .close-btn {
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text-muted);
    font-size: 0.85rem;
    transition: all 0.1s;
  }

  .close-btn:hover {
    color: var(--text);
    border-color: var(--text-muted);
  }

  .modal-body {
    overflow: auto;
    padding: 16px;
  }

  pre {
    font-size: 0.8rem;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-all;
  }
</style>
