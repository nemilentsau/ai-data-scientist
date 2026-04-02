<script>
  let { criteria } = $props();
  let expandedId = $state(null);

  const statusColors = {
    hit: "var(--green)",
    miss: "var(--red)",
    partial: "var(--orange)",
  };

  const groupOrder = ["must_have", "supporting", "forbidden"];
  const groupLabels = {
    must_have: "Must Have",
    supporting: "Supporting",
    forbidden: "Forbidden",
  };

  let grouped = $derived.by(() => {
    const groups = {};
    for (const c of criteria) {
      const g = c.group || "other";
      if (!groups[g]) groups[g] = [];
      groups[g].push(c);
    }
    return groupOrder
      .filter((g) => groups[g])
      .map((g) => ({ key: g, label: groupLabels[g] ?? g, items: groups[g] }));
  });
</script>

<div class="criteria">
  {#each grouped as group}
    <div class="group">
      <div class="group-header">
        <span class="group-name">{group.label}</span>
        <span class="group-count">
          {group.items.filter((c) => c.status === "hit").length}/{group.items.length}
        </span>
      </div>

      {#each group.items as criterion}
        <button
          class="criterion"
          class:expanded={expandedId === criterion.criterion_id}
          onclick={() =>
            (expandedId = expandedId === criterion.criterion_id ? null : criterion.criterion_id)}
        >
          <div class="criterion-header">
            <span
              class="status-dot"
              style="background: {statusColors[criterion.status] ?? 'var(--text-muted)'}"
            ></span>
            <span class="criterion-name">
              {criterion.criterion_id.replace(/_/g, " ")}
            </span>
            <span
              class="status-label"
              style="color: {statusColors[criterion.status] ?? 'var(--text-muted)'}"
            >
              {criterion.status}
            </span>
          </div>
          {#if expandedId === criterion.criterion_id}
            <div class="criterion-body">
              <div class="field">
                <span class="field-label">Justification</span>
                <p>{criterion.justification}</p>
              </div>
              {#if criterion.evidence}
                <div class="field">
                  <span class="field-label">Evidence</span>
                  <p class="evidence">{criterion.evidence}</p>
                </div>
              {/if}
            </div>
          {/if}
        </button>
      {/each}
    </div>
  {/each}
</div>

<style>
  .criteria {
    display: flex;
    flex-direction: column;
    gap: 22px;
  }

  .group-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 4px 10px;
    border-bottom: 2px solid var(--border);
    margin-bottom: 4px;
  }

  .group-name {
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text);
  }

  .group-count {
    font-size: 0.78rem;
    font-family: var(--font-mono);
    font-weight: 700;
    color: var(--text-muted);
    font-variant-numeric: tabular-nums;
  }

  .criterion {
    display: flex;
    flex-direction: column;
    width: 100%;
    text-align: left;
    padding: 12px 16px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-left: 3px solid transparent;
    border-radius: var(--radius);
    box-shadow: var(--shadow-xs);
    transition: all var(--transition-fast, 120ms ease);
  }

  .criterion:hover {
    border-color: color-mix(in srgb, var(--accent) 25%, var(--border));
    border-left-color: color-mix(in srgb, var(--accent) 25%, var(--border));
    box-shadow: var(--shadow-sm);
  }

  .criterion.expanded {
    border-color: var(--accent);
    border-left-color: var(--accent);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 6%, transparent);
  }

  .criterion-header {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .status-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    flex-shrink: 0;
    box-shadow: 0 0 0 3px color-mix(in srgb, currentColor 10%, transparent);
  }

  .criterion-name {
    flex: 1;
    font-size: 0.88rem;
    font-weight: 500;
    text-transform: capitalize;
    color: var(--text);
  }

  .status-label {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 2px 8px;
    border-radius: 999px;
    background: color-mix(in srgb, currentColor 8%, var(--bg));
  }

  .criterion-body {
    margin-top: 14px;
    padding-top: 14px;
    border-top: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .field-label {
    display: block;
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-faint, var(--text-muted));
    margin-bottom: 4px;
  }

  .criterion-body p {
    font-size: 0.88rem;
    line-height: 1.65;
    color: var(--text-muted);
  }

  .evidence {
    font-family: var(--font-mono);
    font-size: 0.82rem;
    background: var(--bg);
    padding: 12px 14px;
    border-radius: var(--radius);
    border: 1px solid var(--border);
    white-space: pre-wrap;
    word-break: break-word;
    line-height: 1.6;
  }
</style>
