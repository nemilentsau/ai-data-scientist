export function RunOverview({
  runName,
  status,
  userQuestion,
  analysisGoal,
  artifactCount,
  agentRunCount,
}: {
  runName: string;
  status: string;
  userQuestion: string;
  analysisGoal: string;
  artifactCount: number;
  agentRunCount: number;
}) {
  return (
    <section className="border-b-2 border-zinc-950 bg-white">
      <div className="grid gap-4 px-5 py-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-x-3 gap-y-2">
            <h2 className="break-all font-mono text-base font-semibold">{runName}</h2>
            <span className={`border px-2 py-1 font-mono text-xs ${statusClass(status)}`}>
              {status}
            </span>
          </div>
          <p className="max-w-5xl text-base leading-6 text-zinc-950">{userQuestion}</p>
          <p className="mt-2 max-w-5xl text-sm leading-6 text-zinc-600">{analysisGoal}</p>
        </div>
        <dl className="grid grid-cols-3 border-y-2 border-zinc-950 text-sm xl:border-y-0 xl:border-l-2">
          <Metric label="Artifacts" value={artifactCount} />
          <Metric label="Agent runs" value={agentRunCount} />
          <Metric label="Dataset" value="multimodal" />
        </dl>
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="border-r border-zinc-300 px-3 py-3 last:border-r-0">
      <dt className="mb-1 font-mono text-[11px] uppercase tracking-[0.14em] text-zinc-500">
        {label}
      </dt>
      <dd className="truncate font-mono text-lg font-semibold">{value}</dd>
    </div>
  );
}

function statusClass(status: string): string {
  if (status === "passed_visual_gate") return "border-teal-700 bg-teal-50 text-teal-950";
  if (status === "running") return "border-amber-700 bg-amber-50 text-amber-950";
  if (status === "failed") return "border-red-700 bg-red-50 text-red-950";
  return "border-zinc-400 bg-white text-zinc-700";
}
