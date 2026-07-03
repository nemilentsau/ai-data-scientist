import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { FileContent } from "./FileContent";
import type { RunArtifact } from "./types";

function text(path: string, body: string): RunArtifact {
  return { kind: "text", path, size: body.length, text: body };
}

describe("FileContent", () => {
  it("renders result.summary preview rows as a real table", () => {
    const summary = JSON.stringify({
      row_count: 19,
      columns: ["rent_bin", "listing_count"],
      preview_rows: [
        { rent_bin: "$500-$750", listing_count: 126 },
        { rent_bin: "$750-$1000", listing_count: 262 },
      ],
    });

    const html = renderToStaticMarkup(
      <FileContent
        artifact={text("03-execution/x/attempt-1/result.summary.json", summary)}
        path="03-execution/x/attempt-1/result.summary.json"
      />,
    );

    expect(html).toContain("<table");
    expect(html).toContain("rent_bin");
    expect(html).toContain("$750-$1000");
    expect(html).toContain("262");
    expect(html).toContain("19");
  });

  it("renders markdown reports as prose, not a raw code box", () => {
    const html = renderToStaticMarkup(
      <FileContent
        artifact={text("06-synthesis/report.md", "# Summary\n\nIt is right-skewed.")}
        path="06-synthesis/report.md"
      />,
    );

    expect(html).toContain("<h1");
    expect(html).toContain("It is right-skewed.");
  });

  it("renders SQL as a code block", () => {
    const html = renderToStaticMarkup(
      <FileContent
        artifact={text("02-artifact-builder/x/attempt-1/query.sql", "SELECT 1")}
        path="02-artifact-builder/x/attempt-1/query.sql"
      />,
    );

    expect(html).toContain("<pre");
    expect(html).toContain("SELECT 1");
  });

  it("renders rendered charts as an image", () => {
    const html = renderToStaticMarkup(
      <FileContent
        artifact={{ kind: "image", path: "04-render/x/attempt-1/chart.png", size: 1024, url: "/img.png" }}
        path="04-render/x/attempt-1/chart.png"
      />,
    );

    expect(html).toContain("<img");
    expect(html).toContain('src="/img.png"');
  });
});
