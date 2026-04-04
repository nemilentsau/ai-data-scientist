---
title: "V2 Prompt Experiment: Synthesis Overview"
artifact_type: synthesis_note
summary: Cross-case synthesis comparing Claude and Codex under the hypothesis-driven v2 prompt, with trace-level analysis of whether prompt instructions changed agent behavior.
experiment_ids:
  - exp_20260403_173315_hypothesis-driven-v2-prompt
---

# V2 Prompt Experiment: Synthesis Overview

## Scope

This note analyzes the full results of the `hypothesis-driven-v2-prompt` experiment, which tested the improved analyst prompt (`prompts/analyst-v2.md`) across both Claude (`solo-v2`) and Codex (`codex-v2`) on all 20 benchmark datasets.

The v2 prompt added three instructions over the v1 checklist:

1. **Hypothesis-driven analysis loop** — observe, hypothesize, test, revise
2. **Visual self-review** — read back every generated plot and examine it
3. **Self-critique before reporting** — challenge assumptions and acknowledge gaps

This synthesis answers: did the new instructions change what the agents actually do, and where did they still fail?

Sources reviewed:

- All 40 trace files (`results/runs/solo-v2/*/trace.jsonl`, `results/runs/codex-v2/*/trace.jsonl`)
- All 40 score files and analysis reports
- The v1 legacy overview (`docs/artifacts/general-overview-20260401-081508.md`)
- `prompts/analyst-v2.md`

## Benchmark Outcome

### Claude (solo-v2)

| Verdict | Count | Datasets |
|---------|-------|----------|
| solved | 15 | anscombes_quartet, class_imbalance, deterministic_linear, high_dim_sparse, interaction_effects, lognormal_skew, mnar, multicollinearity, pure_noise, quadratic, simpsons_paradox, spurious_correlation, survival_censored, time_series_seasonality, well_separated_clusters |
| partial | 3 | multimodal (25%/17%), overlapping_clusters (17%/0%), outlier_dominated (83%/100%) |
| wrong | 2 | concept_drift (12%/0%), heteroscedasticity (17%/17%) |

### Codex (codex-v2)

| Verdict | Count | Datasets |
|---------|-------|----------|
| solved | 11 | anscombes_quartet, class_imbalance, deterministic_linear, high_dim_sparse, multicollinearity, quadratic, simpsons_paradox, spurious_correlation, survival_censored, time_series_seasonality, well_separated_clusters |
| partial | 3 | lognormal_skew (88%/100%), mnar (67%/67%), outlier_dominated (83%/100%) |
| wrong | 5 | concept_drift (12%/0%), heteroscedasticity (17%/0%), interaction_effects (17%/50%), multimodal (0%/0%), pure_noise (83%/100%) |
| failed | 1 | overlapping_clusters (0%/0%) |

### Comparison with v1 Baseline

| Metric | Claude v1 | Claude v2 | Codex v1 | Codex v2 |
|--------|-----------|-----------|----------|----------|
| Solved | 12 | **15** | 10 | 11 |
| Partial | 4 | 3 | 3 | 3 |
| Wrong/Failed | 4 | 2 | 7 | 6 |

Claude gained three solved datasets: `interaction_effects`, `mnar`, and `pure_noise` — all previously partial or wrong. Codex gained one (`multicollinearity`) and lost one (`pure_noise`), netting roughly flat.

## Executive Diagnosis

The v2 prompt produced a measurable improvement for Claude but not for Codex. The reason is structural: **Claude can read images; Codex cannot.** The visual self-review instruction — the single most impactful addition — is only actionable by one of the two agents.

Beyond that, both agents still share the same core failure mode identified in the v1 overview: **premature task framing**. They lock onto a regression narrative before considering whether the dataset calls for clustering, temporal segmentation, distribution analysis, or variance modeling.

The v2 prompt's hypothesis-driven loop helps when the agent forms the right hypothesis early. It does not help when the agent's hypothesis space excludes the correct analytical frame entirely.

## Did the Agents Follow the New Instructions?

### Visual Self-Review

**Claude: YES — mechanically and universally.** Every single dataset shows a consistent pattern: generate a plot in Bash, then immediately read the `.png` file back. Claude averaged 9 image reads per dataset (range: 5–14). This is genuine multimodal inspection — Claude sees the pixel content.

**Codex: SYSTEMATICALLY VIOLATED.** Across all 20 datasets, Codex never read image pixel data. At best, 3 datasets had `Image.open` calls that only checked `img.size` and `img.mode` — metadata, not content. In the remaining datasets, zero image-reading commands were issued. Codex often claimed in its narrative to be "inspecting each PNG one by one" without executing any image-reading command. **Codex CLI has no multimodal input capability** — the prompt instruction is structurally impossible for it to follow.

**Impact:** This single difference likely explains much of the Claude-vs-Codex gap. For multimodal, viewing the histogram would reveal three peaks. For heteroscedasticity, the residual plot shows the fan shape. For interaction_effects, the heatmap reveals the non-additive surface. Claude solved all three; Codex missed all three.

### Hypothesis-Driven Analysis

**Claude: Inconsistent but effective when triggered.** On solved datasets, Claude often formed the right hypothesis early and pursued it. For `simpsons_paradox`, seeing the treatment-by-department cross-tab immediately triggered confounding analysis. For `survival_censored`, recognizing the censoring indicator led to correct lifelines usage.

On failing datasets, Claude formed hypotheses but within the wrong frame:
- `concept_drift`: hypothesized temporal patterns and regime structure, but tested with rolling means and autocorrelation rather than pre/post coefficient comparison
- `multimodal`: hypothesized "nested regression models" — never hypothesized a mixture distribution
- `overlapping_clusters`: hypothesized GPA prediction from covariates — never hypothesized latent clusters

**Codex: Present when signal is strong, absent when subtle.** Codex used hypothesis language in 55% of reports. On `concept_drift`, it generated 8 explicit hypotheses but never hypothesized an abrupt relationship flip. On `multimodal`, zero hypothesis language appeared — pure regression checklist.

**Pattern:** Hypothesis formation helps only when the agent's prior knowledge includes the correct analytical frame. Neither agent hypothesized clustering for overlapping_clusters, mixture modeling for multimodal, or relationship instability for concept_drift.

### Self-Critique

**Both agents: Structurally present, functionally decorative.**

Every failing dataset's report contains a "Limitations and Self-Critique" section. The striking finding is that agents often name the exact analysis they should have done — and then do not do it:

- `concept_drift` (Codex): "What I did not investigate deeply: Regime-switching or changepoint models." This is the correct technique. Listed as future work. Never executed.
- `concept_drift` (Claude): "The data could in principle contain structural breaks, though the daily average plot shows no obvious regime changes." Named changepoint detection, dismissed it based on marginal averages — the drift is in the relationship, not the marginals.
- `overlapping_clusters` (both): Acknowledged not investigating "latent student segments or clusters." Never went back to test it.
- `multimodal` (Claude): "There may be distinct sub-markets with different pricing dynamics that a single model averages over." This is the correct insight in speculative form. Never connected it to the histogram already viewed.

**Self-critique functions as a post-hoc disclaimer, not a revision trigger.** The narrative is already committed by the time the limitations section is written. The agent treats gaps as acceptable caveats rather than as signals to go back and test.

## Persistent Failure Modes

### 1. Concept Drift — Wrong for both agents (12%/0%)

Both agents pooled all 1500 observations into standard models with shuffled cross-validation. The dataset's defining feature — an abrupt flip in the temperature→defect_rate relationship at the midpoint — was destroyed by pooling.

Claude tested rolling means and autocorrelation (correct instinct, wrong target — these check marginal stability, not relationship stability). Codex tested for a monotonic linear trend (p=0.847) and concluded "no drift."

Neither agent ever:
- Split the data at the midpoint and compared coefficients
- Computed rolling correlations or rolling regression slopes
- Compared a single pooled model against a two-regime model

**The v2 prompt did not help** because "hypothesize and test" still operated within a stationarity assumption. The hypothesis space needs to include "the relationship itself may change over time."

### 2. Multimodal — Partial for Claude (25%/17%), Wrong for Codex (0%/0%)

Claude generated and viewed a histogram of `monthly_rent_usd` but did not identify the three peaks. The scorer confirmed: "Despite creating and viewing a histogram of the target, the agent never identifies the distribution as multimodal." Claude built its entire analysis on single-distribution OLS.

Codex never plotted a histogram of the target at all. Its four plots were all regression-oriented. OLS diagnostics showed extreme non-normality (Omnibus=129.23, Jarque-Bera p=3.64e-28) but this was dismissed as a minor caveat.

**Failure mode:** Both agents treated `monthly_rent_usd` as an obvious regression target and never considered its distributional shape. The correct first question is "what does the target look like?" before "what predicts the target?"

### 3. Overlapping Clusters — Partial for Claude (17%/0%), Failed for Codex (0%/0%)

Both agents treated `gpa` as a prediction target. Claude at least ran k-means (k=3) as a side investigation but treated it as a throwaway test — no silhouette scores, no elbow analysis, no multiple-k comparison, no soft clustering. Codex never ran any clustering algorithm at all.

**Failure mode:** Identical to v1. The regression-first bias is so strong that neither agent considered whether the dataset is fundamentally about latent group structure rather than prediction.

### 4. Heteroscedasticity — Wrong for both (Claude 17%/17%, Codex 17%/0%)

Both agents built strong spend→revenue models (R²≈0.95) and stopped there. Claude's log-log transform inadvertently stabilized variance, masking the heteroscedasticity. Codex produced a residual plot but interpreted it as confirming linearity, missing the fan-shaped pattern.

Neither agent ran a Breusch-Pagan or White test. Neither noticed that ROAS standard deviation drops 2:1 across spend deciles. Both reported OLS significance as trustworthy without variance caveats.

**Failure mode:** When the primary signal (spend→revenue) is strong, the agents declare success and do not check model assumptions. The v2 prompt says "check assumptions" but neither agent applied this to heteroscedasticity specifically.

## What Separated Solved from Failed

### Tool counts do not predict success

| Verdict | Claude avg events | Codex avg cmds |
|---------|-------------------|----------------|
| solved | ~25 | ~13 |
| wrong/failed | ~26 | ~13 |

The difference is in *what* the tools do, not how many there are.

### The real differentiator: forming the right question early

On every solved dataset, the agent recognized the correct analytical frame within the first few tool calls:

- `simpsons_paradox`: saw treatment × department cross-tab → confounding analysis
- `survival_censored`: saw `event_occurred` column → censoring → lifelines
- `pure_noise` (Claude): tested multiple relationships → all near-zero → concluded correctly
- `interaction_effects` (Claude): saw channel × time_of_day pattern in EDA → tested interaction model

On every failed dataset, the agent committed to the wrong frame early and never revised:

- `concept_drift`: committed to pooled modeling by event 3
- `multimodal`: committed to regression by event 2
- `overlapping_clusters`: committed to GPA prediction by event 2

**Once the narrative is set, self-critique does not override it.** The agent writes limitations acknowledging gaps but never goes back to fill them.

## Comparison with V1 Overview Predictions

The v1 overview diagnosed the same core problems and recommended a multi-agent team with distinct roles (hypothesis generator, analyst, visual reviewer, method critic, claim verifier). How did the v2 single-agent prompt compare?

| V1 Recommendation | V2 Prompt Approximation | Outcome |
|-------------------|------------------------|---------|
| Hypothesis Generator | "State a concrete hypothesis" instruction | Partially effective — helps when the right hypothesis is in the agent's prior |
| Visual Reviewer | "Read the image back" instruction | Effective for Claude (solves 3+ extra datasets), impossible for Codex |
| Method Critic | "Self-critique before reporting" instruction | Structurally present but does not trigger revision |
| Claim Verifier | Not addressed in v2 prompt | Still missing — partial runs still stop one step short |

The v2 prompt successfully implemented visual review for Claude but failed to replicate the critic and verifier roles. A single agent writing its own limitations section is not equivalent to a separate agent challenging the framing.

## Conclusions

### What the v2 prompt fixed

1. **Visual self-review works for Claude.** Claude now reads back every plot and uses the visual information in its analysis. This directly contributed to solving `interaction_effects`, `mnar`, and `pure_noise`.
2. **Hypothesis language is more common.** Reports are better structured around questions and evidence rather than a linear checklist.
3. **Self-critique sections exist universally.** Even when decorative, they make the agent's reasoning gaps visible to human reviewers.

### What the v2 prompt did not fix

1. **Premature task framing.** Both agents still default to regression and do not consider clustering, mixture modeling, or temporal segmentation unless the signal is obvious.
2. **Self-critique does not trigger revision.** Agents identify gaps in their limitations sections but treat them as acceptable caveats rather than action items.
3. **Codex cannot do visual review.** The instruction is structurally impossible — Codex CLI has no multimodal input. This makes the v2 prompt effectively a v1 prompt for Codex.
4. **Concept drift remains unsolved.** Neither agent checks relationship stability over time, only marginal stability.
5. **The hardest datasets are immune to prompt-level fixes.** Multimodal, overlapping_clusters, and concept_drift require the agent to question its default analytical frame — something a prompt instruction alone cannot reliably induce.

### Recommended next steps

1. **For Codex:** The visual self-review instruction should be replaced with an explicit "generate and interpret diagnostic statistics" checklist, since image reading is unavailable. Alternatively, a preprocessing step could extract numerical summaries from plots.
2. **For both agents:** The prompt should include explicit "alternative framing" checkpoints — after initial EDA, the agent should be forced to enumerate at least three possible analytical frames (supervised, unsupervised, temporal, distributional) and justify which one it chose.
3. **For the hardest datasets:** The v1 overview's multi-agent recommendation remains the strongest path. A separate hypothesis-generator agent with a different prior would catch the framing errors that self-critique does not.
4. **For near-solved partials:** A claim-verification pass focused on proof completeness would convert several partial verdicts to solved (outlier_dominated, lognormal_skew, mnar for Codex).
