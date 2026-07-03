---
name: backend-frontend-contract
description: Read before changing eda-artifacts backend run output contracts, artifact directory layouts, lineage fields, role schemas, or frontend run rendering. Enforces strict frontend contract validation with no fallback rendering.
user-invocable: false
---

# Backend / Frontend Contract

Any backend change that can alter files under a run directory is also a frontend
contract change until proven otherwise.

## Required Rules

- Do not add fallback rendering for unknown run artifacts.
- Do not map run-level selections to the first artifact.
- Do not silently ignore missing fields from `01-eda-framer/output.json`,
  `lineage.json`, builder outputs, or reviewer outputs.
- Unknown artifact paths, unknown artifact ids, missing required fields, and new
  backend stages must fail mechanically in the frontend resolver.
- The frontend must expose agent invocations explicitly. A generated run must
  show `eda_framer`, each `artifact_builder` attempt, and each
  `visual_reviewer` attempt as ordered agent runs with visible inputs and
  outputs.
- Update `frontend/src/selectedView.ts` whenever backend run layout, lineage,
  role output schemas, or artifact filenames change.
- Update `frontend/src/agentInvocations.ts` whenever graph roles, graph order,
  per-agent inputs, or per-agent outputs change.

## Required Checks

After backend contract/layout changes, run:

```bash
uv run pytest tests/test_frontend_contract.py -v
```

This test generates a backend fake run and forces the frontend TypeScript
resolver to classify every produced path and expose every Codex agent
invocation. A failure means the backend and frontend contracts are out of sync.

After frontend run-rendering changes, run:

```bash
cd frontend && npm run check
```
