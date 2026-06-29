import type { ReactNode } from "react";

import { statusTone, type StatusTone } from "./format";

const TONE_DOT: Record<StatusTone, string> = {
  pass: "bg-teal-600",
  revise: "bg-amber-500",
  fail: "bg-red-600",
  neutral: "bg-zinc-400",
};

const TONE_CHIP: Record<StatusTone, string> = {
  pass: "border-teal-200 bg-teal-50 text-teal-800",
  revise: "border-amber-200 bg-amber-50 text-amber-800",
  fail: "border-red-200 bg-red-50 text-red-800",
  neutral: "border-zinc-200 bg-zinc-50 text-zinc-600",
};

export function StatusDot({ status }: { status: string }) {
  return (
    <span
      className={`inline-block h-2 w-2 shrink-0 rounded-full ${TONE_DOT[statusTone(status)]}`}
      aria-hidden
    />
  );
}

export function StatusChip({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 font-mono text-xs ${TONE_CHIP[statusTone(status)]}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${TONE_DOT[statusTone(status)]}`} aria-hidden />
      {status}
    </span>
  );
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-zinc-400">{children}</p>
  );
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return <h3 className="text-base font-semibold tracking-tight text-zinc-950">{children}</h3>;
}

export function CodeBlock({ text, language }: { text: string; language?: string }) {
  return (
    <pre className="overflow-auto rounded-md border border-zinc-200 bg-zinc-50 p-4 font-mono text-xs leading-5 text-zinc-800">
      <code data-language={language}>{text}</code>
    </pre>
  );
}

export function DefinitionList({
  items,
}: {
  items: Array<{ term: string; value: ReactNode }>;
}) {
  return (
    <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-[170px_minmax(0,1fr)]">
      {items.map(({ term, value }) => (
        <div key={term} className="contents">
          <dt className="font-mono text-xs uppercase tracking-[0.12em] text-zinc-400">{term}</dt>
          <dd className="text-zinc-800">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function DataTable({
  columns,
  rows,
}: {
  columns: string[];
  rows: Array<Record<string, unknown>>;
}) {
  return (
    <div className="overflow-x-auto rounded-md border border-zinc-200">
      <table className="min-w-full border-collapse text-left text-xs">
        <thead>
          <tr className="border-b border-zinc-200 bg-zinc-50">
            {columns.map((column) => (
              <th
                key={column}
                className="whitespace-nowrap px-3 py-2 font-mono text-[11px] font-medium uppercase tracking-[0.1em] text-zinc-500"
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex} className="border-b border-zinc-100 last:border-b-0">
              {columns.map((column) => (
                <td key={column} className="whitespace-nowrap px-3 py-1.5 font-mono text-zinc-700">
                  {formatCell(row[column])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Collapsible({
  summary,
  children,
  defaultOpen = false,
}: {
  summary: ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
}) {
  return (
    <details open={defaultOpen} className="group rounded-md border border-zinc-200">
      <summary className="flex cursor-pointer items-center gap-2 px-4 py-3 text-sm font-medium text-zinc-700 marker:content-none hover:text-zinc-950">
        <span className="font-mono text-zinc-400 transition group-open:rotate-90">›</span>
        {summary}
      </summary>
      <div className="space-y-5 border-t border-zinc-200 px-4 py-4">{children}</div>
    </details>
  );
}

export function EmptyNote({ children }: { children: ReactNode }) {
  return <p className="text-sm text-zinc-500">{children}</p>;
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return String(value);
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}
