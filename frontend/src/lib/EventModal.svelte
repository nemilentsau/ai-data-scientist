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
    background: rgba(10, 12, 20, 0.35);
    backdrop-filter: blur(6px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 24px;
    animation: fadeIn 150ms ease;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .modal {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius-xl, 16px);
    max-width: 900px;
    width: 100%;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    box-shadow: var(--shadow-lg, var(--shadow-md));
    animation: slideUp 180ms cubic-bezier(0.16, 1, 0.3, 1);
  }

  @keyframes slideUp {
    from { opacity: 0; transform: translateY(12px) scale(0.98); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
    background: var(--bg);
  }

  .modal-header h3 {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text);
  }

  .close-btn {
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text-muted);
    font-size: 0.85rem;
    transition: all var(--transition-fast, 120ms ease);
  }

  .close-btn:hover {
    color: var(--red);
    border-color: var(--red);
    background: var(--red-soft, color-mix(in srgb, var(--red) 5%, var(--bg-secondary)));
  }

  .modal-body {
    overflow: auto;
    padding: 20px;
    background: var(--bg);
  }

  pre {
    font-size: 0.82rem;
    line-height: 1.55;
    white-space: pre-wrap;
    word-break: break-all;
    color: var(--text);
  }
</style>
