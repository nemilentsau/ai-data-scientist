---
title: Experiment 3 Visual Pilot Synthesis
artifact_type: synthesis_note
summary: After rerunning codex-v3, Codex now solves heteroscedasticity and interaction_effects, but multimodal still fails; the visual-review step still cannot write back, so the remaining gap is primarily about reframing rather than raw analysis quality.
experiment_ids:
  - exp_20260404_experiment-3-visual-pilot
---

# Experiment 3 Visual Pilot Synthesis

## Scope

This note synthesizes the current `claude-v3` and rerun `codex-v3` results for:

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
- `results/runs/codex-v3/*/run_state.json`

## Outcome Summary

The refreshed experiment picture is now:

- `heteroscedasticity`: Claude `solved`, Codex `solved`
- `interaction_effects`: Claude `solved`, Codex `solved`
- `multimodal`: Claude `partial`, Codex `wrong`

This is materially different from the earlier Codex readout. After the rerun, Codex is no longer weak across the board. It is competitive on the two datasets whose core signal can be recovered through strong first-pass diagnostics and standard modeling.

## What Changed In The Codex Rerun

The rerun replaced the earlier Codex outcomes of `partial / partial / wrong` with `solved / solved / wrong`.

That means the earlier takeaway, "Codex did not improve much," is no longer accurate. The updated conclusion is narrower:

- Codex can solve `heteroscedasticity` and `interaction_effects` at benchmark quality.
- Codex still fails `multimodal`.
- The current Codex visual-review step still does not integrate its corrections into the scored report.

So the remaining problem is not general analytical competence. It is the combination of:

- no true critique/reframing loop
- a reviewer that still cannot write back to `analysis_report.md`
- and, on `multimodal`, the wrong plot set being handed to the reviewer

## Why Codex Now Solves `heteroscedasticity` And `interaction_effects`

The important point is that the new Codex wins do **not** show a functioning visual-correction loop. They show a much stronger analyst pass.

### `heteroscedasticity`

The new Codex analyst report squarely hits the benchmark contract:

- identifies the spend-revenue mean trend
- runs explicit residual diagnostics
- names heteroscedasticity as the variance problem
- cites the Breusch-Pagan test
- uses HC3 robust standard errors as the remedy

The visual reviewer only adds tightening:

- sharper wording on funnel shape and heavy tails
- confirmation that quadratic spend and channel-specific slopes do not matter much
- more specific comments on outliers

Those are useful edits, but they are not what moved the verdict to `solved`. The analyst report already did that.

### `interaction_effects`

The same pattern holds here. The new Codex analyst report:

- explicitly tests `channel_score × time_of_day_hour`
- compares main-effects and interaction models
- identifies the interaction as the headline finding
- downweights `ad_budget_usd`, device, and page load time

The visual reviewer again adds nuance rather than rescue:

- warns that the hour-by-hour pattern is noisy at fine granularity
- notes mild calibration underprediction at the tails
- confirms the interaction is not being driven by a few influential points

So the rerun demonstrates that Codex can produce a benchmark-passing report on these datasets before the visual reviewer needs to intervene.

## Why `multimodal` Still Fails

`multimodal` remains the clearest example of why visual review is not enough.

The new Codex analyst again framed the task as a rent-regression problem:

- `sq_ft` as the dominant driver
- parking as a confounded effect
- location and age as weak after adjustment

This analysis is coherent, but it still misses the defining benchmark requirement:

- inspect the target distribution directly
- recognize that `monthly_rent_usd` is multi-peaked
- reject the single-population framing
- suggest segmentation or mixture analysis

The failure is visible in both the report and the attached plot set.

The `multimodal` visual-review inputs were:

- `plot_01_rent_vs_sqft.png`
- `plot_02_parking_by_size_quartile.png`
- `plot_03_rent_per_sqft_vs_distance.png`
- `plot_04_standardized_coefficients.png`

There is still no histogram, KDE, or dedicated target-distribution plot of `monthly_rent_usd`.

So even though the reviewer did run and inspect images, it inherited the analyst's framing and was asked to review the wrong evidence. Its output tightens the regression story by adding:

- heteroscedasticity language
- a small `sq_ft × bedrooms` interaction
- stronger residual caveats

But those edits all stay inside the same wrong worldview.

## The Codex Visual Reviewer Is Still Not Functioning As A Corrective Loop

The rerun also confirms that the Codex resume-step integration bug is still real.

Across the refreshed Codex visual-review outputs, the reviewer again says it could not edit `analysis_report.md` because the workspace was read-only.

That matters for interpretation:

- the visual reviewer is active
- the visual reviewer does inspect the generated PNGs
- but its corrections still remain in `steps/visual_review/final_message.md`
- while the scorer still grades the top-level `analysis_report.md`

This means the current Codex benchmark is still not measuring "analyst plus functioning visual reviewer." It is mostly measuring the analyst, with reviewer comments stranded beside the scored artifact.

## What This Means For The Claude vs Codex Comparison

The updated comparison is more balanced than before.

Claude still has the better overall Experiment 3 result because:

- it solves `heteroscedasticity`
- it solves `interaction_effects`
- it reaches `partial` on `multimodal` rather than `wrong`

But the cross-agent gap is now much smaller than the earlier writeup implied.

The real remaining difference is:

- both agents can solve the datasets where the right signal is already accessible through conventional analysis
- neither agent truly solves the reframing problem on `multimodal`
- Claude's workflow is operationally better because its reviewer can actually edit the report
- Codex's reviewer is still non-integrating, so its value is mostly diagnostic rather than corrective

## Updated Bottom Line

Experiment 3 now supports a sharper conclusion:

1. Visual review is not a substitute for critique. The `multimodal` failure still comes from missing the need to question the original framing and inspect the target distribution directly.
2. Codex is stronger than the earlier run suggested. After rerun, it fully solves `heteroscedasticity` and `interaction_effects`.
3. The Codex visual-review step is still operationally broken for benchmark purposes. It can see plots, but it still cannot write its corrections back into the scored report.

So the next workflow priority remains the same:

- add a true critique / revision loop for reframing
- separately fix the Codex resume/writeback path so visual review becomes part of the scored artifact rather than a side note
