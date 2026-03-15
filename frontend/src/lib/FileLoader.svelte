<script>
  let { onTraceLoaded, onReportLoaded } = $props();
  let dragActive = $state(false);
  let fileInput;

  function handleFiles(files) {
    let dirPath = "";
    for (const f of files) {
      // Try to extract directory path from webkitRelativePath or name
      if (f.webkitRelativePath) {
        const parts = f.webkitRelativePath.split("/");
        dirPath = parts.slice(0, -1).join("/");
      }

      if (f.name === "trace.jsonl" || f.name.endsWith(".jsonl")) {
        f.text().then((text) => onTraceLoaded(text, dirPath));
      } else if (f.name === "analysis_report.md" || f.name.endsWith(".md")) {
        f.text().then((text) => onReportLoaded(text));
      }
    }
  }

  function onDrop(e) {
    e.preventDefault();
    dragActive = false;

    if (e.dataTransfer.items) {
      const files = [];
      for (const item of e.dataTransfer.items) {
        if (item.kind === "file") {
          files.push(item.getAsFile());
        }
      }
      handleFiles(files);
    } else {
      handleFiles(e.dataTransfer.files);
    }
  }

  function onDragOver(e) {
    e.preventDefault();
    dragActive = true;
  }

  function onDragLeave() {
    dragActive = false;
  }

  function onInputChange(e) {
    handleFiles(e.target.files);
  }
</script>

<div
  class="loader"
  class:drag-active={dragActive}
  role="button"
  tabindex="0"
  ondrop={onDrop}
  ondragover={onDragOver}
  ondragleave={onDragLeave}
  onclick={() => fileInput.click()}
  onkeydown={(e) => e.key === "Enter" && fileInput.click()}
>
  <span>Drop files or click to load</span>
  <span class="formats">trace.jsonl, analysis_report.md</span>
  <input
    bind:this={fileInput}
    type="file"
    accept=".jsonl,.json,.md"
    multiple
    onchange={onInputChange}
    hidden
  />
</div>

<style>
  .loader {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 16px;
    border: 1px dashed var(--border);
    border-radius: var(--radius);
    cursor: pointer;
    transition: all 0.15s;
    font-size: 0.85rem;
    color: var(--text-muted);
  }

  .loader:hover,
  .drag-active {
    border-color: var(--accent);
    background: rgba(88, 166, 255, 0.05);
    color: var(--text);
  }

  .formats {
    font-size: 0.75rem;
    opacity: 0.6;
  }
</style>
