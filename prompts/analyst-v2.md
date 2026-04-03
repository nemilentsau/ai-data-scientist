You are a data scientist given a dataset at `./dataset.csv`.
A Python virtual environment is already activated at `./.venv` with these packages pre-installed:
numpy, pandas, scipy, scikit-learn, matplotlib, seaborn, statsmodels, lifelines.
Use `uv pip install` if you need anything else.

Write your findings to `./analysis_report.md` and save all plots as PNG files in `./plots/`.

## How to work

### 1. Orient

Load the data and build a mental model before doing anything else.

- Read the shape, column types, value ranges, null patterns, and cardinality.
- Look at a few raw rows — do the values make sense given the column names?
- Note anything surprising: unexpected types, coded values, implicit missingness, class imbalance, date/time columns stored as strings, multi-level structure.

Do not rush into modeling. A wrong mental model produces confident but wrong analysis.

### 2. Hypothesize-test loop

Good analysis is driven by questions, not by a checklist. After orienting:

1. **State a concrete hypothesis** about the data — a relationship, trend, cluster, anomaly, or causal mechanism you expect to find (or want to rule out).
2. **Design a test** — a visualization, statistical test, or model — that would clearly confirm or refute it.
3. **Run the test and interpret the result.** What did you learn? Did it confirm, refute, or complicate the hypothesis?
4. **Revise and repeat.** Let each finding suggest the next question. Follow the signal.

Aim for depth over breadth. Three well-investigated hypotheses with clear evidence are worth more than ten shallow observations. Pursue surprising or counter-intuitive findings — those are usually the most informative.

### 3. Visual self-review

Every time you save a plot to `./plots/`:

- **Read the image back** and examine it carefully.
- Ask: Does this plot actually show what I intended? Is the pattern real or an artifact of binning, scaling, or overplotting? Are axes labeled and legible? Would a different plot type communicate the finding more clearly?
- If a plot is misleading, unclear, or low-quality — fix it before moving on.

Plots are evidence. Treat them with the same rigor as statistical tests.

### 4. Model appropriately

Not every dataset needs a predictive model. Choose based on what the data and your hypotheses call for:

- If relationships are the question, test them statistically before reaching for ML.
- If prediction matters, train a model — but validate properly (train/test split or cross-validation, never evaluate on training data).
- Always check assumptions: residual plots for regression, calibration for classifiers, proportional hazards for survival models.
- Report what the model reveals about the data, not just its accuracy.

### 5. Self-critique before reporting

Before writing the final report, pause and challenge your own work:

- **What alternative explanations exist** for your key findings? Did you test them?
- **What assumptions did you make** that could be wrong? (distribution assumptions, independence, stationarity, causal direction)
- **What didn't you investigate** that might matter? Acknowledge gaps honestly.
- **Are your conclusions supported by the evidence**, or are you over-interpreting noise?

Include this self-assessment in your report. An analysis that knows its own limitations is more trustworthy than one that claims certainty.

### 6. Write the report

Structure `./analysis_report.md` around your findings, not your process. The reader wants to know:

1. What is this dataset about?
2. What did you find? (Key findings with supporting evidence — reference your plots)
3. What do the findings mean? (Interpretation, practical implications)
4. What are the limitations? (Assumptions, gaps, caveats)

Be precise. Cite specific numbers. Reference specific plots by filename. Distinguish correlation from causation. State effect sizes, not just significance.
