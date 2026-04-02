<script>
  import ReportView from "./ReportView.svelte";

  let { artifact } = $props();
</script>

<div class="artifact-detail">
  <div class="artifact-header">
    <div>
      <div class="artifact-kicker">{artifact.category?.replace(/_/g, " ") ?? "Artifact"}</div>
      <h2>{artifact.title ?? artifact.artifact_id}</h2>
      {#if artifact.summary}
        <p class="artifact-summary">{artifact.summary}</p>
      {/if}
    </div>
    <div class="artifact-meta">
      <span>{artifact.type?.replace(/_/g, " ") ?? "artifact"}</span>
      <span>{artifact.scope?.replace(/_/g, " ") ?? "artifact"}</span>
      {#if artifact.created_at}
        <span>{new Date(artifact.created_at).toLocaleString()}</span>
      {/if}
    </div>
  </div>

  <div class="artifact-facts">
    {#if artifact.datasetLabels?.length}
      <div class="fact-group">
        <span class="fact-label">Datasets</span>
        <span class="fact-value">{artifact.datasetLabels.join(", ")}</span>
      </div>
    {/if}
    {#if artifact.configLabels?.length}
      <div class="fact-group">
        <span class="fact-label">Configs</span>
        <span class="fact-value">{artifact.configLabels.join(", ")}</span>
      </div>
    {/if}
    {#if artifact.path}
      <div class="fact-group fact-group--wide">
        <span class="fact-label">Path</span>
        <span class="fact-value fact-value--mono">{artifact.path}</span>
      </div>
    {/if}
  </div>

  {#if artifact.detailKind === "markdown" && artifact.content}
    <ReportView text={artifact.content} />
  {:else if artifact.detailKind === "image"}
    <div class="artifact-image-frame">
      <img class="artifact-image" src={artifact.content_url} alt={artifact.title ?? artifact.path} />
    </div>
  {:else if (artifact.detailKind === "json" || artifact.detailKind === "text" || artifact.detailKind === "code") && artifact.content}
    <div class="artifact-code-frame">
      <pre><code>{artifact.content}</code></pre>
    </div>
  {:else if artifact.detailKind === "binary"}
    <div class="artifact-empty">Binary artifact preview is not available in the dashboard.</div>
  {:else}
    <div class="artifact-empty">No content available.</div>
  {/if}
</div>

<style>
  .artifact-detail {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .artifact-header {
    display: flex;
    justify-content: space-between;
    gap: 24px;
    align-items: flex-start;
    padding: 26px;
    border-radius: var(--radius-xl, 16px);
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-top: 3px solid var(--accent);
    box-shadow: var(--shadow-sm);
  }

  .artifact-kicker {
    margin-bottom: 10px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--accent);
  }

  h2 {
    margin: 0;
    font-size: 1.6rem;
    font-weight: 800;
    line-height: 1.15;
    letter-spacing: -0.02em;
    color: var(--text);
  }

  .artifact-summary {
    margin: 12px 0 0;
    max-width: 68ch;
    line-height: 1.6;
    color: var(--text-muted);
  }

  .artifact-meta {
    display: flex;
    flex-direction: column;
    gap: 8px;
    align-items: flex-end;
    min-width: 160px;
    font-size: 0.75rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-faint, var(--text-muted));
  }

  .artifact-empty {
    padding: 28px;
    border-radius: var(--radius-lg);
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    color: var(--text-muted);
  }

  .artifact-facts {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
  }

  .fact-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 16px 18px;
    border-radius: var(--radius-lg);
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    box-shadow: var(--shadow-xs);
  }

  .fact-group--wide {
    grid-column: 1 / -1;
  }

  .fact-label {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
  }

  .fact-value {
    color: var(--text);
    line-height: 1.5;
    font-weight: 500;
  }

  .fact-value--mono {
    font-family: var(--font-mono);
    font-size: 0.82rem;
    font-weight: 400;
    overflow-wrap: anywhere;
  }

  .artifact-image-frame,
  .artifact-code-frame {
    padding: 18px;
    border-radius: var(--radius-lg);
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    box-shadow: var(--shadow-xs);
  }

  .artifact-image {
    width: 100%;
    height: auto;
    display: block;
    border-radius: var(--radius);
  }

  .artifact-code-frame pre {
    overflow-x: auto;
  }

  .artifact-code-frame code {
    font-family: var(--font-mono);
    font-size: 0.85rem;
    line-height: 1.6;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    color: var(--text);
  }

  @media (max-width: 900px) {
    .artifact-header {
      flex-direction: column;
    }

    .artifact-meta {
      align-items: flex-start;
    }

    .artifact-facts {
      grid-template-columns: 1fr;
    }
  }
</style>
