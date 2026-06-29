# Run Inspector Reframe — Design

Date: 2026-06-29
Status: Approved (direction), implementing

## Problem

The current frontend (`frontend/src/App.tsx`, ~1.5k lines) is a three-pane
*file/IDE inspector*: monospace path links, "all files by stage", raw JSON,
dark SQL blocks, and three columns that duplicate artifact status / lineage /
review context. The actual product of an EDA run — the question, the charts,
the reviewer verdicts, and the synthesis report — is buried behind clicking
individual files. The user's verdict: "complete and utter garbage."

## Decisions

- **Primary job:** read & judge the analysis result (report-first). Keep light
  pipeline *traces* for now; full tracing is deferred to Opik/Langfuse later.
- **Scope:** full reframe of the presentation layer. The data-derivation layer
  is reused unchanged.
- **Aesthetic:** clean editorial light — generous whitespace, real type
  hierarchy, monospace reserved for code/IDs/paths/metrics, hairline dividers
  instead of heavy black borders, one restrained accent (teal), subtle status
  chips.
- **Zero cards.** For every region, the semantically-correct element is chosen;
  a card is used only when nothing else fits (it never does here). See mapping.

## Information architecture

Slim header + ~240px left "table of contents" sidebar + one wide centered
reading column. The content column is a small router with four views:

1. **Overview** (landing): hero (user question, analysis goal, status, compact
   metrics) → **chart gallery** (one figure per artifact) → **synthesis report**
   rendered as prose.
2. **Artifact detail** (per artifact): large chart; reviewer verdict + visual
   adequacy + statistical findings + carry-forward limits + required revision as
   readable prose/lists; plan/request as a description list; collapsible
   **Evidence** (SQL, `result.summary` preview as a real table, raw file links);
   contextual lineage (inputs / used-by); attempt history when > 1.
3. **Pipeline**: ordered agent runs (`eda_framer → builder×N → reviewer×N`) as a
   vertical timeline with expandable inputs/outputs. The seam for Opik/Langfuse.
4. **Files**: by-stage browser + the **strict** per-file viewer
   (`selectedView.ts`), preserving the "fail on unknown artifact, no fallback
   rendering" guarantee (the contract-failure panel stays).

Sidebar lists: Overview · each artifact (status dot + humanized title) ·
Pipeline · Files.

## Element mapping (no cards)

| Region | Data shape | Element |
| --- | --- | --- |
| Hero | title + prose + few metrics | heading + `<p>` + inline metrics row |
| Chart gallery | chart + title + verdict + purpose | grid of `<figure>`/`<figcaption>` |
| Reviewer findings | lists of strings | `<ul>`; verdict → inline chip |
| Plan / request, lineage | key/value, link lists | `<dl>`, link lists |
| Evidence | disclosure + code + table | `<details>` + code block + `<table>` |
| Result preview | tabular rows | `<table>` |
| Pipeline | sequence of steps | `<ol>` timeline |
| Sidebar / files | navigable items | `<ul>` link lists |
| Reports (md) | prose | rendered Markdown |

## Code structure

**Reused unchanged** (keeps the Python contract guard + `backendContract.test.ts`
green): `runApi.ts`, `runFolder.ts`, `agentInvocations.ts`, `artifactLoop.ts`,
`selectedView.ts`, `types.ts`.

**New presentation files** (one job each):

- `App.tsx` — slim shell: load run(s), run selection, view routing.
- `runView.ts` — pure `RunView` routing type + helpers (tested).
- `format.ts` — `humanizeArtifactId`, status tone, dataset-from-rootName (tested).
- `Markdown.tsx` — small dependency-free markdown renderer (tested).
- `ui.tsx` — `StatusChip`, `Eyebrow`, `CodeBlock`, `DataTable`, `Collapsible`,
  `DefinitionList`.
- `RunHeader.tsx`, `RunSidebar.tsx`.
- `OverviewView.tsx`, `ChartGallery.tsx`.
- `ArtifactDetailView.tsx`.
- `PipelineView.tsx` (folds in old `AgentInvocationList`).
- `FilesView.tsx` + `FileContent.tsx` (strict renderer extracted from today's
  `ArtifactWorkspace`; renders `result.summary` preview rows as a table).

Old `RunOverview.tsx` / `AgentInvocationList.tsx` / `ArtifactWorkspace` are
folded into the above; their tests are replaced.

## Constraints honored

- No new runtime deps (markdown hand-rolled; keep `lucide-react`).
- TS-only, strict, no `.js`/`.jsx`. Port stays `localhost:5180`.
- `npm run check` (typecheck + vitest + build) must pass.
- Data derivation + contract guards unchanged; `selectedView` strictness kept;
  ordered agent runs remain visible (Pipeline view).

## Testing (TDD, `renderToStaticMarkup` style)

Pure modules (`format`, `runView`, `Markdown`) get unit tests first. Each view
gets a render-to-static-markup test asserting the right content appears (chart
image, verdict, findings prose, humanized titles, data-table cells). The three
current component tests are rewritten to the new components; new tests added.
