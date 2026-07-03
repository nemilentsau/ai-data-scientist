import { formatBytes, safeParseJson } from "./runFolder";
import type { RunArtifact } from "./types";
import { CodeBlock, DataTable, DefinitionList, EmptyNote } from "./ui";
import { Markdown } from "./Markdown";

export function FileContent({ artifact, path }: { artifact: RunArtifact; path: string }) {
  if (artifact.kind === "image") {
    return (
      <figure className="space-y-2">
        <img
          src={artifact.url}
          alt={path}
          className="max-h-[72vh] max-w-full rounded-md border border-zinc-200 bg-white object-contain p-2"
        />
        <figcaption className="font-mono text-xs text-zinc-400">{formatBytes(artifact.size)}</figcaption>
      </figure>
    );
  }

  if (artifact.kind === "binary") {
    return (
      <div className="rounded-md border border-zinc-200 bg-zinc-50 p-4">
        <p className="text-sm font-medium text-zinc-800">Binary artifact · {formatBytes(artifact.size)}</p>
        <p className="mt-2 max-w-xl text-sm leading-6 text-zinc-600">
          Browser inspection does not parse this file. Use the adjacent
          <span className="font-mono"> result.summary.json </span>
          for table shape and preview rows.
        </p>
      </div>
    );
  }

  if (path.endsWith("result.summary.json")) {
    return <ResultSummaryTable text={artifact.text} />;
  }

  if (path.endsWith(".json")) {
    const parsed = safeParseJson(artifact.text);
    return (
      <CodeBlock
        language="json"
        text={parsed.ok ? JSON.stringify(parsed.value, null, 2) : artifact.text}
      />
    );
  }

  if (path.endsWith(".csv")) return <CsvTable text={artifact.text} />;
  if (path.endsWith(".sql")) return <CodeBlock text={artifact.text} language="sql" />;
  if (path.endsWith(".md")) return <Markdown text={artifact.text} />;

  return <CodeBlock text={artifact.text} language="text" />;
}

function ResultSummaryTable({ text }: { text: string }) {
  const parsed = safeParseJson(text);
  if (!parsed.ok || !isRecord(parsed.value)) {
    return <CodeBlock text={text} language="json" />;
  }

  const value = parsed.value;
  const columns = stringArray(value.columns);
  const previewRows = Array.isArray(value.preview_rows)
    ? value.preview_rows.filter(isRecord)
    : [];
  const rowCount = typeof value.row_count === "number" ? value.row_count : undefined;
  const tableColumns = columns.length > 0 ? columns : columnsFromRows(previewRows);

  return (
    <div className="space-y-4">
      <DefinitionList
        items={[
          { term: "Rows", value: rowCount ?? "Not recorded." },
          { term: "Columns", value: tableColumns.length > 0 ? tableColumns.join(", ") : "Not recorded." },
        ]}
      />
      {previewRows.length > 0 ? (
        <div className="space-y-2">
          <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-zinc-400">
            Preview · first {previewRows.length} rows
          </p>
          <DataTable columns={tableColumns} rows={previewRows} />
        </div>
      ) : (
        <EmptyNote>No preview rows were recorded.</EmptyNote>
      )}
    </div>
  );
}

function CsvTable({ text }: { text: string }) {
  const lines = text.trim().split(/\r?\n/);
  const header = (lines[0] ?? "").split(",");
  const rows = lines.slice(1, 12).map((line) => {
    const cells = line.split(",");
    return Object.fromEntries(header.map((column, index) => [column, cells[index] ?? ""]));
  });

  return (
    <div className="space-y-2">
      <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-zinc-400">
        First {rows.length} rows
      </p>
      <DataTable columns={header} rows={rows} />
    </div>
  );
}

function columnsFromRows(rows: Array<Record<string, unknown>>): string[] {
  const seen = new Set<string>();
  for (const row of rows) {
    for (const key of Object.keys(row)) seen.add(key);
  }
  return Array.from(seen);
}

function stringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
