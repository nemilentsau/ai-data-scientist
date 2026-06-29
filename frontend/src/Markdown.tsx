import type { ReactNode } from "react";

type Block =
  | { type: "heading"; level: number; text: string }
  | { type: "paragraph"; text: string }
  | { type: "list"; ordered: boolean; items: string[] }
  | { type: "code"; content: string }
  | { type: "quote"; text: string }
  | { type: "hr" };

const HEADING = /^(#{1,6})\s+(.*)$/;
const HR = /^(-{3,}|\*{3,}|_{3,})$/;
const UNORDERED = /^[-*+]\s+(.*)$/;
const ORDERED = /^\d+\.\s+(.*)$/;
const INLINE = /`([^`]+)`|\*\*([^*]+)\*\*|\[([^\]]+)\]\(([^)\s]+)\)/g;

function isSpecial(line: string): boolean {
  const trimmed = line.trim();
  return (
    trimmed.startsWith("```") ||
    HEADING.test(line) ||
    HR.test(trimmed) ||
    UNORDERED.test(line) ||
    ORDERED.test(line) ||
    trimmed.startsWith(">")
  );
}

function parseBlocks(text: string): Block[] {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const blocks: Block[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i] ?? "";
    const trimmed = line.trim();

    if (trimmed.length === 0) {
      i += 1;
      continue;
    }

    if (trimmed.startsWith("```")) {
      const content: string[] = [];
      i += 1;
      while (i < lines.length && !(lines[i] ?? "").trim().startsWith("```")) {
        content.push(lines[i] ?? "");
        i += 1;
      }
      i += 1; // skip closing fence
      blocks.push({ type: "code", content: content.join("\n") });
      continue;
    }

    const heading = HEADING.exec(line);
    if (heading) {
      blocks.push({ type: "heading", level: heading[1]?.length ?? 1, text: heading[2] ?? "" });
      i += 1;
      continue;
    }

    if (HR.test(trimmed)) {
      blocks.push({ type: "hr" });
      i += 1;
      continue;
    }

    if (trimmed.startsWith(">")) {
      const quoteLines: string[] = [];
      while (i < lines.length && (lines[i] ?? "").trim().startsWith(">")) {
        quoteLines.push((lines[i] ?? "").trim().replace(/^>\s?/, ""));
        i += 1;
      }
      blocks.push({ type: "quote", text: quoteLines.join(" ") });
      continue;
    }

    const unordered = UNORDERED.exec(line);
    const ordered = ORDERED.exec(line);
    if (unordered || ordered) {
      const isOrdered = Boolean(ordered);
      const items: string[] = [];
      while (i < lines.length) {
        const current = lines[i] ?? "";
        const match = isOrdered ? ORDERED.exec(current) : UNORDERED.exec(current);
        if (!match) break;
        items.push(match[1] ?? "");
        i += 1;
      }
      blocks.push({ type: "list", ordered: isOrdered, items });
      continue;
    }

    const paragraph: string[] = [];
    while (i < lines.length) {
      const current = lines[i] ?? "";
      if (current.trim().length === 0 || isSpecial(current)) break;
      paragraph.push(current.trim());
      i += 1;
    }
    blocks.push({ type: "paragraph", text: paragraph.join(" ") });
  }

  return blocks;
}

function renderInline(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let key = 0;
  INLINE.lastIndex = 0;

  for (let match = INLINE.exec(text); match !== null; match = INLINE.exec(text)) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }

    const [, code, bold, linkText, linkHref] = match;
    if (code !== undefined) {
      nodes.push(
        <code key={key} className="rounded bg-zinc-100 px-1 py-0.5 font-mono text-[0.85em] text-zinc-800">
          {code}
        </code>,
      );
    } else if (bold !== undefined) {
      nodes.push(
        <strong key={key} className="font-semibold text-zinc-950">
          {bold}
        </strong>,
      );
    } else if (linkText !== undefined && linkHref !== undefined) {
      nodes.push(
        <a
          key={key}
          href={linkHref}
          target="_blank"
          rel="noreferrer"
          className="text-teal-700 underline decoration-teal-700/40 underline-offset-2 hover:text-teal-900"
        >
          {linkText}
        </a>,
      );
    }

    key += 1;
    lastIndex = INLINE.lastIndex;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes;
}

function renderBlock(block: Block, index: number): ReactNode {
  switch (block.type) {
    case "heading": {
      if (block.level <= 1) {
        return (
          <h1 key={index} className="text-2xl font-semibold tracking-tight text-zinc-950">
            {renderInline(block.text)}
          </h1>
        );
      }
      if (block.level === 2) {
        return (
          <h2 key={index} className="mt-2 text-lg font-semibold tracking-tight text-zinc-950">
            {renderInline(block.text)}
          </h2>
        );
      }
      return (
        <h3
          key={index}
          className="mt-2 font-mono text-xs font-semibold uppercase tracking-[0.14em] text-zinc-500"
        >
          {renderInline(block.text)}
        </h3>
      );
    }
    case "paragraph":
      return (
        <p key={index} className="text-zinc-700">
          {renderInline(block.text)}
        </p>
      );
    case "list":
      return block.ordered ? (
        <ol key={index} className="list-decimal space-y-1 pl-5 text-zinc-700 marker:text-zinc-400">
          {block.items.map((item, itemIndex) => (
            <li key={itemIndex}>{renderInline(item)}</li>
          ))}
        </ol>
      ) : (
        <ul key={index} className="list-disc space-y-1 pl-5 text-zinc-700 marker:text-zinc-400">
          {block.items.map((item, itemIndex) => (
            <li key={itemIndex}>{renderInline(item)}</li>
          ))}
        </ul>
      );
    case "code":
      return (
        <pre
          key={index}
          className="overflow-auto rounded border border-zinc-200 bg-zinc-50 p-3 font-mono text-xs leading-5 text-zinc-800"
        >
          <code>{block.content}</code>
        </pre>
      );
    case "quote":
      return (
        <blockquote key={index} className="border-l-2 border-zinc-300 pl-4 italic text-zinc-600">
          {renderInline(block.text)}
        </blockquote>
      );
    case "hr":
      return <hr key={index} className="border-zinc-200" />;
  }
}

export function Markdown({ text }: { text: string }) {
  return <div className="space-y-4 text-[15px] leading-7">{parseBlocks(text).map(renderBlock)}</div>;
}
