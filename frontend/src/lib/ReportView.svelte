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

<div class="report">
  {@html renderMarkdown(text)}
</div>

<style>
  .report {
    padding: 24px;
    background: var(--bg-secondary);
    border-radius: var(--radius-lg);
    line-height: 1.7;
    max-width: 900px;
  }

  .report :global(h1) {
    font-size: 1.5rem;
    margin: 0 0 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
  }

  .report :global(h2) {
    font-size: 1.2rem;
    margin: 24px 0 12px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border);
    color: var(--accent);
  }

  .report :global(h3) {
    font-size: 1rem;
    margin: 20px 0 8px;
    color: var(--text);
  }

  .report :global(h4) {
    font-size: 0.9rem;
    margin: 16px 0 6px;
    color: var(--text-muted);
  }

  .report :global(p) {
    margin: 6px 0;
  }

  .report :global(strong) {
    color: var(--text);
  }

  .report :global(code) {
    font-family: var(--font-mono);
    font-size: 0.85em;
    background: var(--bg-tertiary);
    padding: 1px 5px;
    border-radius: 3px;
  }

  .report :global(table) {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 0.85rem;
  }

  .report :global(th) {
    background: var(--bg-tertiary);
    padding: 8px 12px;
    text-align: left;
    border: 1px solid var(--border);
    font-weight: 600;
    color: var(--text);
  }

  .report :global(td) {
    padding: 6px 12px;
    border: 1px solid var(--border);
    color: var(--text-muted);
  }

  .report :global(tr:hover td) {
    background: var(--bg-tertiary);
  }

  .report :global(ul) {
    margin: 8px 0;
    padding-left: 24px;
  }

  .report :global(li) {
    margin: 4px 0;
  }

  .report :global(.md-code-block) {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    margin: 12px 0;
  }

  .report :global(.md-code-lang) {
    padding: 4px 10px;
    background: var(--bg-tertiary);
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
  }

  .report :global(.md-code-block pre) {
    padding: 12px;
    overflow-x: auto;
    font-size: 0.8rem;
    line-height: 1.5;
  }
</style>
