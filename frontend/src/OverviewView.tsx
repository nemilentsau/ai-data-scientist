import { ChartGallery } from "./ChartGallery";
import { Markdown } from "./Markdown";
import type { GalleryItem } from "./overview";
import { Eyebrow, SectionTitle, StatusChip } from "./ui";

export function OverviewView({
  question,
  goal,
  status,
  datasetName,
  artifactCount,
  agentRunCount,
  items,
  synthesisMarkdown,
  onSelectArtifact,
}: {
  question: string;
  goal: string;
  status: string;
  datasetName: string;
  artifactCount: number;
  agentRunCount: number;
  items: GalleryItem[];
  synthesisMarkdown: string | null;
  onSelectArtifact: (artifactId: string) => void;
}) {
  return (
    <div className="mx-auto max-w-4xl space-y-14 px-8 py-10">
      <header className="space-y-4">
        <Eyebrow>{datasetName} dataset · analysis</Eyebrow>
        <h1 className="text-3xl font-semibold leading-tight tracking-tight text-zinc-950">
          {question}
        </h1>
        <p className="max-w-3xl text-lg leading-8 text-zinc-600">{goal}</p>
        <div className="flex flex-wrap items-center gap-x-8 gap-y-3 pt-2">
          <StatusChip status={status} />
          <dl className="flex flex-wrap gap-x-8 gap-y-2">
            <Metric label="charts" value={artifactCount} />
            <Metric label="agent runs" value={agentRunCount} />
            <Metric label="dataset" value={datasetName} />
          </dl>
        </div>
      </header>

      <section className="space-y-6">
        <SectionTitle>Charts</SectionTitle>
        <ChartGallery items={items} onSelect={onSelectArtifact} />
      </section>

      {synthesisMarkdown ? (
        <section className="space-y-5">
          <SectionTitle>Summary report</SectionTitle>
          <Markdown text={synthesisMarkdown} />
        </section>
      ) : null}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="flex items-baseline gap-2">
      <dt className="order-2 font-mono text-[11px] uppercase tracking-[0.14em] text-zinc-400">
        {label}
      </dt>
      <dd className="order-1 font-mono text-lg font-semibold text-zinc-950">{value}</dd>
    </div>
  );
}
