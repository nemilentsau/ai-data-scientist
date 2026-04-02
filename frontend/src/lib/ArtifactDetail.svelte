<script>
  import ReportView from "./ReportView.svelte";

  let { artifact } = $props();
</script>

<div class="flex flex-col gap-5">
  <div class="artifact-header flex justify-between gap-6 items-start p-[26px] rounded-2xl bg-bg-secondary border border-border border-t-[3px] border-t-accent shadow-sm max-md:flex-col">
    <div>
      <div class="mb-2.5 text-[0.7rem] font-bold uppercase tracking-[0.1em] text-accent">{artifact.category?.replace(/_/g, " ") ?? "Artifact"}</div>
      <h2 class="m-0 text-[1.6rem] font-extrabold leading-[1.15] tracking-[-0.02em] text-text">{artifact.title ?? artifact.artifact_id}</h2>
      {#if artifact.summary}
        <p class="mt-3 max-w-[68ch] leading-[1.6] text-text-muted">{artifact.summary}</p>
      {/if}
    </div>
    <div class="flex flex-col gap-2 items-end min-w-[160px] text-[0.75rem] font-medium uppercase tracking-[0.06em] text-text-faint max-md:items-start">
      <span>{artifact.type?.replace(/_/g, " ") ?? "artifact"}</span>
      <span>{artifact.scope?.replace(/_/g, " ") ?? "artifact"}</span>
      {#if artifact.created_at}
        <span>{new Date(artifact.created_at).toLocaleString()}</span>
      {/if}
    </div>
  </div>

  <div class="grid grid-cols-2 gap-3.5 max-md:grid-cols-1">
    {#if artifact.datasetLabels?.length}
      <div class="flex flex-col gap-1.5 py-4 px-[18px] rounded-xl bg-bg-secondary border border-border shadow-xs">
        <span class="text-[0.7rem] font-semibold uppercase tracking-[0.06em] text-text-muted">Datasets</span>
        <span class="text-text leading-[1.5] font-medium">{artifact.datasetLabels.join(", ")}</span>
      </div>
    {/if}
    {#if artifact.configLabels?.length}
      <div class="flex flex-col gap-1.5 py-4 px-[18px] rounded-xl bg-bg-secondary border border-border shadow-xs">
        <span class="text-[0.7rem] font-semibold uppercase tracking-[0.06em] text-text-muted">Configs</span>
        <span class="text-text leading-[1.5] font-medium">{artifact.configLabels.join(", ")}</span>
      </div>
    {/if}
    {#if artifact.path}
      <div class="col-span-full flex flex-col gap-1.5 py-4 px-[18px] rounded-xl bg-bg-secondary border border-border shadow-xs">
        <span class="text-[0.7rem] font-semibold uppercase tracking-[0.06em] text-text-muted">Path</span>
        <span class="text-text leading-[1.5] font-mono text-[0.82rem] font-normal break-all">{artifact.path}</span>
      </div>
    {/if}
  </div>

  {#if artifact.detailKind === "markdown" && artifact.content}
    <ReportView text={artifact.content} />
  {:else if artifact.detailKind === "image"}
    <div class="p-[18px] rounded-xl bg-bg-secondary border border-border shadow-xs">
      <img class="w-full h-auto block rounded-lg" src={artifact.content_url} alt={artifact.title ?? artifact.path} />
    </div>
  {:else if (artifact.detailKind === "json" || artifact.detailKind === "text" || artifact.detailKind === "code") && artifact.content}
    <div class="p-[18px] rounded-xl bg-bg-secondary border border-border shadow-xs">
      <pre class="overflow-x-auto"><code class="font-mono text-[0.85rem] leading-[1.6] whitespace-pre-wrap break-all text-text">{artifact.content}</code></pre>
    </div>
  {:else if artifact.detailKind === "binary"}
    <div class="p-7 rounded-xl bg-bg-secondary border border-border text-text-muted">Binary artifact preview is not available in the dashboard.</div>
  {:else}
    <div class="p-7 rounded-xl bg-bg-secondary border border-border text-text-muted">No content available.</div>
  {/if}
</div>
