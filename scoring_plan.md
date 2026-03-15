# Plan: Replace Generic Rubric with Per-Dataset Checkpoint Scoring

## Context

The current scoring system uses 7 generic dimensions (data_loading, EDA, pattern_identification, etc.) each scored 0-5, summed to 35. This is broken: an agent scored 33/35 on Simpson's Paradox while completely missing the trend reversal — the entire point of the dataset. The 7-dimension system rewards technical polish over actual insight.

We control the datasets. We know exactly what each one tests, what the correct findings are, and what the right metrics should be. The scoring must be concrete, per-dataset, and pattern-centric.

## Design

### Core concept: Checkpoints

Each dataset gets 5-8 concrete, verifiable checkpoints. Each checkpoint is scored as **HIT** (full points), **PARTIAL** (partial points), or **MISS** (0 points). Every dataset's checkpoints sum to exactly **100 points**.

### Checkpoint categories and weights

| Category | Weight | Purpose |
|----------|--------|---------|
| `core_insight` | 40-50 pts | The central pattern. Missing this = missing the point |
| `analysis_step` | 30-40 pts | Specific analytical steps needed to find the pattern |
| `technical` | 10-20 pts | Correct viz, proper tests, no overcomplicated models |

No more generic "EDA quality" or "code quality" dimensions. If a specific visualization matters for a dataset, it's a checkpoint. If it doesn't matter, it's not scored.

### Data structures

```python
# In datasets/registry.py
@dataclass(frozen=True)
class Checkpoint:
    id: str                     # "simpsons_reversal_identified"
    description: str            # human-readable, shown to reviewer
    points: int                 # full-hit points
    partial_points: int         # partial-hit points (0 for binary checks)
    category: str               # "core_insight" | "analysis_step" | "technical"
    verification_hint: str = "" # how the reviewer should verify this

# DatasetMeta gets a new field:
checkpoints: list[Checkpoint]   # must sum to 100 points
```

```python
# In reviewer/scorer.py
@dataclass
class CheckpointResult:
    checkpoint_id: str
    verdict: str            # "hit" | "partial" | "miss"
    points_earned: int
    points_possible: int
    justification: str

@dataclass
class ScoreResult:
    dataset_name: str
    agent: str
    checkpoint_results: list[CheckpointResult]
    score: int              # 0-100
    max_score: int          # 100
    summary: str
    raw_response: str
```

### Example checkpoints (3 datasets)

**Simpson's Paradox (100 pts)**
| Checkpoint | Category | Pts | Partial |
|-----------|----------|-----|---------|
| Computed aggregate treatment effect | analysis_step | 10 | 5 |
| Computed within-group treatment effects | analysis_step | 15 | 7 |
| Identified direction REVERSES aggregate vs within-group | core_insight | 35 | 15 |
| Named Simpson's Paradox or explained mechanism | core_insight | 15 | 7 |
| Identified confounder variable | analysis_step | 10 | 5 |
| Visualization showing reversal | technical | 10 | 5 |
| Correct practical conclusion | technical | 5 | 0 |

**Pure Noise (100 pts)**
| Checkpoint | Category | Pts | Partial |
|-----------|----------|-----|---------|
| Concluded no meaningful relationships | core_insight | 40 | 15 |
| Performed significance tests | analysis_step | 15 | 7 |
| Reported low R² / no predictive power | analysis_step | 10 | 5 |
| Did NOT report spurious pattern as real | core_insight | 20 | 0 |
| Tested multiple variable pairs | analysis_step | 10 | 5 |
| Produced viz showing no structure | technical | 5 | 0 |

**Deterministic Linear (100 pts)**
| Checkpoint | Category | Pts | Partial |
|-----------|----------|-----|---------|
| Reported slope ≈ 2.0 | core_insight | 20 | 10 |
| Reported intercept ≈ 3.0 | core_insight | 20 | 10 |
| Reported R² = 1.0 | analysis_step | 15 | 7 |
| Stated relationship is exact/deterministic | core_insight | 15 | 5 |
| Wrote equation y = 2x + 3 | analysis_step | 10 | 5 |
| Did NOT overcomplicate with nonlinear models | technical | 10 | 0 |
| Identified noise columns as irrelevant | analysis_step | 10 | 5 |

### Reviewer prompt change

The reviewer LLM gets a dataset-specific rubric listing each checkpoint with verification hints. It returns:

```json
{
  "checkpoints": {
    "simpsons_reversal_identified": {
      "verdict": "hit",
      "justification": "Agent explicitly states treatment A appears worse overall but better within each department"
    }
  },
  "summary": "Overall assessment paragraph"
}
```

Scoring is mechanical: map verdicts to points, sum.

### Report change

- Summary table uses 0-100 scale
- Per-dataset sections show checkpoint table with verdict/points
- New aggregate metric: **Core Insight Hit Rate** (fraction of core_insight checkpoints scored as HIT across all datasets)

## Files to modify

1. **`datasets/registry.py`** — Add `Checkpoint` dataclass, add `checkpoints` field to `DatasetMeta`, define checkpoints for all 20 datasets (~7 checkpoints each, ~140 total)
2. **`reviewer/rubric.py`** — Complete rewrite: replace 7 generic dimensions with `format_checkpoint_rubric_for_prompt(dataset_meta)`
3. **`reviewer/scorer.py`** — New `CheckpointResult`/`ScoreResult`, new prompt builder, new scoring logic
4. **`reviewer/report.py`** — Checkpoint breakdown tables, core insight hit rate, 0-100 scale
5. **`run_benchmark.py`** — Update score.json serialization to use new structure
6. **`tests/test_rubric.py`** — Rewrite for checkpoint-based rubric
7. **`tests/test_scorer.py`** — Rewrite for checkpoint-based scoring
8. **`tests/test_report.py`** — Update for 0-100 scale and checkpoint tables
9. **`tests/test_registry.py`** — Add: all datasets have checkpoints, totals = 100, unique IDs, every dataset has core_insight checkpoint

## Verification

1. `uv run pytest tests/ -v` — all tests pass
2. Spot-check: re-score the existing Simpson's Paradox result — should now score ~26/100 (only analysis_step and technical hits, core_insight misses) instead of 33/35
3. Check that all 20 datasets have checkpoints summing to exactly 100
