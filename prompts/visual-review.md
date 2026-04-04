Visually inspect the provided plots and any related report content in the workspace.

Focus on whether the visuals reveal structure, artifacts, assumption violations, or contradictions that the current report understates or misses.

If the report is already aligned with the plots, keep the conclusions stable. If not, revise `analysis_report.md` so the final report reflects what the visuals actually show.

You are not limited to commentary. If the plots suggest missing analysis, you should run additional code, compute additional diagnostics, generate additional plots, and then update the report. Treat this as a corrective analysis pass, not a passive review pass.

Be concrete about:
- distribution shape
- clustering or separation
- time drift or changepoints
- outliers or leverage points
- residual patterns and heteroscedasticity
- interactions or nonlinear structure

If the current plots are insufficient to resolve an ambiguity, create the plot or statistic you need and use it.

Do not rewrite the entire report unless necessary. Make the smallest changes needed to correct or strengthen the final analysis, but prefer correctness over minimal edits.
