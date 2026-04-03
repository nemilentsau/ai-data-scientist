<script>
  let { criteria } = $props();
  let expandedId = $state(null);

  const statusColors = {
    hit: "var(--color-green)",
    miss: "var(--color-red)",
    partial: "var(--color-orange)",
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

<div class="flex flex-col gap-[22px]">
  {#each grouped as group}
    <div>
      <div class="flex justify-between items-center px-1 pb-2.5 border-b-2 border-border mb-1">
        <span class="text-[0.78rem] font-bold uppercase tracking-[0.06em] text-text">{group.label}</span>
        <span class="text-[0.78rem] font-mono font-bold text-text-muted tabular-nums">{group.items.filter((c) => c.status === "hit").length}/{group.items.length}</span>
      </div>

      {#each group.items as criterion}
        <button
          class="criterion flex flex-col w-full text-left py-3 px-4 bg-bg-secondary border border-border border-l-[3px] border-l-transparent rounded-lg shadow-xs transition-all duration-100 ease-out"
          class:expanded={expandedId === criterion.criterion_id}
          onclick={() =>
            (expandedId = expandedId === criterion.criterion_id ? null : criterion.criterion_id)}
        >
          <div class="flex items-center gap-2.5">
            <span
              class="w-[9px] h-[9px] rounded-full shrink-0 shadow-[0_0_0_3px_color-mix(in_srgb,currentColor_10%,transparent)]"
              style="background: {statusColors[criterion.status] ?? 'var(--color-text-muted)'}"
            ></span>
            <span class="flex-1 text-[0.88rem] font-medium capitalize text-text">
              {criterion.criterion_id.replace(/_/g, " ")}
            </span>
            <span
              class="text-[0.7rem] font-bold uppercase tracking-[0.05em] py-0.5 px-2 rounded-full bg-[color-mix(in_srgb,currentColor_8%,var(--color-bg))]"
              style="color: {statusColors[criterion.status] ?? 'var(--color-text-muted)'}"
            >
              {criterion.status}
            </span>
          </div>
          {#if expandedId === criterion.criterion_id}
            <div class="mt-3.5 pt-3.5 border-t border-border flex flex-col gap-3">
              <div>
                <span class="block text-[0.68rem] font-semibold uppercase tracking-[0.06em] text-text-faint mb-1">Justification</span>
                <p class="text-[0.88rem] leading-[1.65] text-text-muted">{criterion.justification}</p>
              </div>
              {#if criterion.evidence}
                <div>
                  <span class="block text-[0.68rem] font-semibold uppercase tracking-[0.06em] text-text-faint mb-1">Evidence</span>
                  <p class="font-mono text-[0.82rem] bg-bg py-3 px-3.5 rounded-lg border border-border whitespace-pre-wrap break-words leading-[1.6]">{criterion.evidence}</p>
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
  .criterion:hover {
    border-color: color-mix(in srgb, var(--color-accent) 25%, var(--color-border));
    border-left-color: color-mix(in srgb, var(--color-accent) 25%, var(--color-border));
    box-shadow: var(--shadow-sm);
  }

  .criterion.expanded {
    border-color: var(--color-accent);
    border-left-color: var(--color-accent);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--color-accent) 6%, transparent);
  }
</style>
