<script>
  let { text } = $props();

  // Simple markdown renderer for analysis reports
  function renderMarkdown(md) {
    let html = md
      // Code blocks
      .replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
        return `<div class="md-code-block"><div class="md-code-lang">${lang || "text"}</div><pre><code>${escapeHtml(code.trim())}</code></pre></div>`;
      })
      // Tables
      .replace(/^(\|.+\|)\n(\|[-:| ]+\|)\n((?:\|.+\|\n?)*)/gm, (_, header, sep, body) => {
        const ths = header.split("|").filter(c => c.trim()).map(c => `<th>${c.trim()}</th>`).join("");
        const rows = body.trim().split("\n").map(row => {
          const tds = row.split("|").filter(c => c.trim()).map(c => `<td>${c.trim()}</td>`).join("");
          return `<tr>${tds}</tr>`;
        }).join("");
        return `<table><thead><tr>${ths}</tr></thead><tbody>${rows}</tbody></table>`;
      })
      // Headers
      .replace(/^#### (.+)$/gm, "<h4>$1</h4>")
      .replace(/^### (.+)$/gm, "<h3>$1</h3>")
      .replace(/^## (.+)$/gm, "<h2>$1</h2>")
      .replace(/^# (.+)$/gm, "<h1>$1</h1>")
      // Bold and italic
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      // Inline code
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      // Lists
      .replace(/^- (.+)$/gm, "<li>$1</li>")
      .replace(/^(\d+)\. (.+)$/gm, "<li>$2</li>")
      // Paragraphs (lines not already wrapped)
      .replace(/^(?!<[hltud]|<\/)(.*\S.*)$/gm, "<p>$1</p>")
      // Clean up consecutive <li> into <ul>
      .replace(/(<li>.*<\/li>\n?)+/g, (match) => `<ul>${match}</ul>`);

    return html;
  }

  function escapeHtml(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }
</script>

<div class="report p-8 bg-bg-secondary border border-border rounded-2xl leading-[1.7] max-w-[900px] shadow-xs">
  {@html renderMarkdown(text)}
</div>

<style>
  .report :global(h1) {
    font-size: 1.5rem;
    font-weight: 800;
    margin: 0 0 18px;
    padding-bottom: 12px;
    border-bottom: 2px solid var(--color-border);
    color: var(--color-text);
    letter-spacing: -0.01em;
  }

  .report :global(h2) {
    font-size: 1.2rem;
    font-weight: 700;
    margin: 32px 0 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--color-border);
    color: var(--color-accent);
  }

  .report :global(h3) {
    font-size: 1.02rem;
    font-weight: 600;
    margin: 24px 0 8px;
    color: var(--color-text);
  }

  .report :global(h4) {
    font-size: 0.92rem;
    font-weight: 600;
    margin: 18px 0 6px;
    color: var(--color-text-muted);
  }

  .report :global(p) {
    margin: 8px 0;
    color: var(--color-text);
  }

  .report :global(strong) {
    color: var(--color-text);
    font-weight: 600;
  }

  .report :global(code) {
    font-family: var(--font-mono);
    font-size: 0.85em;
    background: var(--color-bg-tertiary);
    padding: 2px 6px;
    border-radius: 4px;
    color: var(--color-accent);
  }

  .report :global(table) {
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0;
    font-size: 0.85rem;
    border: 1px solid var(--color-border);
    border-radius: 8px;
    overflow: hidden;
  }

  .report :global(th) {
    background: var(--color-bg-tertiary);
    padding: 10px 14px;
    text-align: left;
    border: 1px solid var(--color-border);
    font-weight: 600;
    color: var(--color-text);
  }

  .report :global(td) {
    padding: 8px 14px;
    border: 1px solid var(--color-border);
    color: var(--color-text);
  }

  .report :global(tr:hover td) {
    background: var(--color-bg);
  }

  .report :global(ul) {
    margin: 10px 0;
    padding-left: 24px;
  }

  .report :global(li) {
    margin: 5px 0;
    color: var(--color-text);
  }

  .report :global(.md-code-block) {
    border: 1px solid var(--color-border);
    border-radius: 8px;
    overflow: hidden;
    margin: 14px 0;
  }

  .report :global(.md-code-lang) {
    padding: 5px 12px;
    background: var(--color-bg-tertiary);
    font-size: 0.67rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--color-text-muted);
    border-bottom: 1px solid var(--color-border);
  }

  .report :global(.md-code-block pre) {
    padding: 14px;
    overflow-x: auto;
    font-size: 0.82rem;
    line-height: 1.55;
    background: var(--color-bg);
  }
</style>
