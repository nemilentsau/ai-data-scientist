import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { Markdown } from "./Markdown";

function render(text: string): string {
  return renderToStaticMarkup(<Markdown text={text} />);
}

describe("Markdown", () => {
  it("renders level-1 and level-2 headings", () => {
    const html = render("# Summary\n\n## target_distribution_histogram");
    expect(html).toContain("<h1");
    expect(html).toContain("Summary</h1>");
    expect(html).toContain("<h2");
    expect(html).toContain("target_distribution_histogram</h2>");
  });

  it("renders blank-line separated paragraphs", () => {
    const html = render("First para.\n\nSecond para.");
    expect(html).toContain("<p");
    expect(html).toContain("First para.");
    expect(html).toContain("Second para.");
    expect(html.match(/<p/g)?.length).toBe(2);
  });

  it("renders bold and inline code within prose", () => {
    const html = render("It is **right-skewed** for `monthly_rent_usd` values.");
    expect(html).toMatch(/<strong[^>]*>right-skewed<\/strong>/);
    expect(html).toMatch(/<code[^>]*>monthly_rent_usd<\/code>/);
  });

  it("renders unordered and ordered lists", () => {
    const unordered = render("- alpha\n- beta");
    expect(unordered).toContain("<ul");
    expect(unordered.match(/<li/g)?.length).toBe(2);
    expect(unordered).toContain("alpha");

    const ordered = render("1. first\n2. second");
    expect(ordered).toContain("<ol");
    expect(ordered.match(/<li/g)?.length).toBe(2);
  });

  it("renders fenced code without interpreting markdown inside", () => {
    const html = render("```\nSELECT **x** FROM t\n```");
    expect(html).toContain("<pre");
    expect(html).toContain("SELECT **x** FROM t");
    expect(html).not.toContain("<strong>x</strong>");
  });

  it("renders links with an href", () => {
    const html = render("see [the docs](https://example.com/x)");
    expect(html).toContain('href="https://example.com/x"');
    expect(html).toContain(">the docs</a>");
  });

  it("renders horizontal rules and blockquotes", () => {
    expect(render("a\n\n---\n\nb")).toContain("<hr");
    expect(render("> quoted line")).toContain("<blockquote");
  });
});
