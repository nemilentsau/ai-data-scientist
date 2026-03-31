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
    gap: 16px;
  }

  .group-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 4px 6px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 4px;
  }

  .group-name {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
  }

  .group-count {
    font-size: 0.75rem;
    font-family: var(--font-mono);
    color: var(--text-muted);
  }

  .criterion {
    display: flex;
    flex-direction: column;
    width: 100%;
    text-align: left;
    padding: 8px 12px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    transition: all 0.1s;
  }

  .criterion:hover {
    background: var(--bg-tertiary);
  }

  .criterion.expanded {
    border-color: var(--text-muted);
  }

  .criterion-header {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .criterion-name {
    flex: 1;
    font-size: 0.85rem;
    text-transform: capitalize;
  }

  .status-label {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .criterion-body {
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .field-label {
    display: block;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    margin-bottom: 4px;
  }

  .criterion-body p {
    font-size: 0.85rem;
    line-height: 1.6;
    color: var(--text-muted);
  }

  .evidence {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    background: var(--bg);
    padding: 8px 12px;
    border-radius: var(--radius);
    white-space: pre-wrap;
    word-break: break-word;
  }
</style>
