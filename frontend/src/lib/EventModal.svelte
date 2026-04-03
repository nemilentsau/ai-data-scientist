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
  class="fixed inset-0 bg-[rgba(10,12,20,0.35)] backdrop-blur-[6px] flex items-center justify-center z-[1000] p-6 animate-fade-in"
  role="dialog"
  aria-modal="true"
  tabindex="-1"
  onclick={handleBackdropClick}
>
  <div class="bg-bg-secondary border border-border rounded-2xl max-w-[900px] w-full max-h-[80vh] flex flex-col overflow-hidden shadow-lg animate-slide-up">
    <div class="flex items-center justify-between px-5 py-4 border-b border-border bg-bg">
      <h3 class="text-[0.95rem] font-semibold text-text">Event Detail — {event.tool}</h3>
      <button
        class="w-[30px] h-[30px] flex items-center justify-center bg-bg-secondary border border-border rounded-md text-text-muted text-[0.85rem] transition-all duration-100 ease-out hover:text-red hover:border-red hover:bg-red-soft"
        onclick={onClose}
      >x</button>
    </div>
    <div class="overflow-auto p-5 bg-bg">
      <pre class="text-[0.82rem] leading-[1.55] whitespace-pre-wrap break-all text-text"><code>{json}</code></pre>
    </div>
  </div>
</div>
