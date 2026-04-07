`framing.json` written. Key decisions:

- **Primary frame**: performance_rating prediction — it's the most natural continuous outcome in an HR dataset.
- **Framing risks** emphasize the possibility of no genuine signal: the sample rows show no obvious feature-outcome patterns, distributions look diffuse, and multiple-testing inflation is a real concern with 9 predictors.
- **Required checks** are designed to catch spurious findings early — permutation tests, Bonferroni correction, and baseline model comparison will surface whether any apparent relationships are noise.