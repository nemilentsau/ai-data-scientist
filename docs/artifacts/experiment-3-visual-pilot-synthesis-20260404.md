---
title: Experiment 3 Visual Pilot Synthesis
artifact_type: synthesis_note
summary: Visual review materially helped Claude on two datasets but mostly failed as a reframing mechanism; Codex also suffered from a resume-step writeback bug.
experiment_ids:
  - exp_20260404_experiment-3-visual-pilot
---

# Experiment 3 Visual Pilot Synthesis

## Scope

This note synthesizes the `claude-v3` and `codex-v3` results for:

- `multimodal`
- `heteroscedasticity`
- `interaction_effects`

Sources reviewed:

- `results/runs/claude-v3/benchmark_report.md`
- `results/runs/codex-v3/benchmark_report.md`
- `results/runs/claude-v3/*/analysis_report.md`
- `results/runs/codex-v3/*/analysis_report.md`
- `results/runs/claude-v3/*/steps/visual_review/final_message.md`
- `results/runs/codex-v3/*/steps/visual_review/final_message.md`
- `results/runs/claude-v3/multimodal/steps/visual_review/trace.jsonl`
- `results/runs/codex-v3/multimodal/steps/visual_review/trace.jsonl`

## Outcome Summary

The visual-review workflow helped Claude substantially on two of the three datasets:

- `heteroscedasticity`: Claude `solved`, Codex `partial`
- `interaction_effects`: Claude `solved`, Codex `partial`
- `multimodal`: Claude `partial`, Codex `wrong`

This means the visual pass was not a no-op. But it also was not enough to reliably correct a bad initial framing.

## Executive Diagnosis

The pilot surfaced two different bottlenecks:

1. **Reframing bottleneck**
   Visual review is good at tightening an existing analysis, but weak at overturning the analyst's initial problem framing.

2. **Integration bottleneck**
   Codex's reviewer often found real corrections, but could not write them back into `analysis_report.md`, so the scored artifact stayed stale.

Claude mostly hit the first bottleneck.
Codex hit both.

## Why Claude Improved On Two Datasets

Claude's visual-review step was genuinely corrective, not merely cosmetic.

### `heteroscedasticity`

The reviewer rebuilt the diagnostics rather than just commenting on them:

- it replaced a misleading QQ construction in `regression_diagnostics.png`
- added a scale-location plot
- added `funnel_noise_analysis.png`
- strengthened the report from "strong linear trend with caveats" to "linear mean trend plus serious heteroscedasticity / funnel-noise interpretation"

The final reviewer message explicitly documents those changes, including new plots and revised interpretation.

This matters because the benchmark rewards:

- explicit residual diagnostics
- explicit identification of non-constant variance
- concrete remedy suggestions

Claude's visual pass moved the report into that space.

### `interaction_effects`

Claude's reviewer also did real analytical escalation:

- upgraded the finding from generic "synergy" to a **crossing interaction**
- added a direct main-effects-vs-interaction model comparison
- added `plots/10_corrective_diagnostics.png`
- documented that the main-effects-only view underperforms
- explained the ad-budget feature-importance artifact instead of leaving it as a misleading model output

Again, this is exactly the kind of shift the rubric rewards: not just seeing the heatmap, but formally establishing that the interaction is the dominant mechanism.

## Why Claude Still Failed `multimodal`

Claude's `multimodal` review improved the report, but only locally.

The reviewer:

- strengthened the heteroscedasticity diagnosis
- corrected elasticity interpretation
- documented the LOWESS boundary artifact
- found a `1,500–2,000 sqft` rent-per-sqft bump
- fixed Q-Q interpretation

Those are real improvements. But they all stay inside the original framing: "this is a size-driven rent regression problem with some diagnostics and local nonlinearities."

The benchmark's core requirement was different:

- inspect the target distribution directly
- recognize that `monthly_rent_usd` is multi-peaked
- reject the single-population / single-Gaussian framing
- suggest segmentation or mixture analysis

Claude did not do that.

The evidence is straightforward:

- the final report still describes rent as **right-skewed**, not multimodal
- the only target-distribution view is a small panel inside the summary dashboard
- the visual review trace focuses on bathroom anomalies, elasticity reconciliation, heteroscedasticity, and local rent-per-sqft structure
- there is no dedicated histogram / KDE investigation of the target's modal structure

So the failure on `multimodal` was not "Claude cannot inspect plots." It did inspect them. The failure was that the reviewer inherited the analyst's framing and used its effort budget to refine that framing instead of challenging it.

This is the strongest evidence that **visual review is not the same thing as critique**.

## Why Codex Did Not Improve Much

Codex's visual-review step did real work:

- for `heteroscedasticity`, it quantified the residual fan-out and proposed stronger caveats
- for `interaction_effects`, it formally tested `time_of_day_hour × channel_score` and found the missing positive interaction
- for `multimodal`, it diagnosed misspecification and weakened the bathroom claim using HC3 and RESET-style checks

So the weak benchmark movement was not because Codex ignored the plots.

### Reason 1: Writeback bug

The most immediate issue is operational.

Across all three Codex visual-review runs, the reviewer says it could not update `analysis_report.md` because the workspace was read-only. That means:

- the reviewer found better conclusions
- but those corrections often remained in `steps/visual_review/final_message.md`
- while the scorer still graded the top-level `analysis_report.md`

This is a harness bug, not just a model limitation.

### Reason 2: The corrections were mostly local, not reframing-level

Even where Codex found new evidence, the reviewer usually concluded that the existing report was "directionally correct" and should only be tightened.

That is enough to improve nuance, but not enough to move a rubric that expects:

- heteroscedasticity to become the main story
- the interaction to be formally modeled and centered
- the rent target to be treated as a mixture signal

### Reason 3: Codex inherited the wrong plot set on `multimodal`

Codex's `multimodal` visual-review inputs were:

- `adjusted_effects.png`
- `price_per_sqft_vs_sqft.png`
- `rent_vs_sqft.png`
- `residuals_vs_fitted.png`

There was no target-distribution plot attached.

So even before the critique/writeback bug, the reviewer was being asked to visually inspect the wrong evidence for the benchmark's core discovery.

### Reason 4: The review step behaved more like a validator than an adversarial critic

The Codex reviewer repeatedly took the stance:

- the report is mostly correct
- here are the smallest corrections I would make

That is the right behavior for polishing a report.
It is the wrong behavior for discovering that the report is answering the wrong question.

## Comparison: What Visual Review Can And Cannot Do

This experiment suggests a sharper conclusion than "visual review helps" or "visual review does not help."

Visual review is good at:

- catching plot-conclusion mismatches
- strengthening diagnostics
- adding missing caveats
- formalizing patterns already hinted at visually
- improving communication of a basically correct analysis

Visual review is weak at:

- noticing that the analyst generated the wrong plots
- discarding the original task framing
- switching from pooled modeling to segmentation / mixture logic
- forcing a new first-principles EDA pass on the target distribution

That is why it helped on `heteroscedasticity` and `interaction_effects`, but not on `multimodal`.

Those first two datasets can still be solved by strengthening or formalizing what the existing plots already imply.
`multimodal` requires a different first question.

## Implications For Workflow Design

The next harness iteration should separate three functions that are currently conflated:

1. **Analyst**
   Builds the first-pass report and plot set.

2. **Critic**
   Challenges framing, missing plots, and untested assumptions.
   This step should be adversarial and willing to say:
   "You are answering the wrong question."

3. **Visual reviewer**
   Checks whether the existing plots and revised report actually align.

That sequence matters.

If visual review is used before critique, it mostly becomes a sophisticated editor for the analyst's worldview.

## Bottom Line

The experiment shows that visual review is useful, but not sufficient.

- Claude proves that a visual follow-up pass can materially improve reports when the core structure is already on the page.
- Codex shows that the current harness can also lose those gains entirely if reviewer corrections do not persist back into the scored artifact.
- `multimodal` shows the deeper limitation: **without an explicit critique step, the system refines the analyst's framing instead of challenging it**.

So the next improvement priority should be:

1. fix Codex writeback on resume
2. add a true critic / analyst-revision loop
3. only then treat visual review as the final alignment pass
