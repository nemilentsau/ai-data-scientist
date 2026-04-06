`framing.json` written. Key decisions:

- **Primary frame**: Regression on `performance_rating` — it's the most natural continuous target (mean ~50, std ~10, range 9.5–75.3).
- **Pure-noise risk flagged prominently**: The data has zero nulls, exactly 800 rows, and no obvious domain artifacts, suggesting synthetic generation with potentially no real signal. A null-model/permutation check is listed as a required check.
- **Ambiguities recorded**: No designated target column, salary_band's role is unclear, and no causal/temporal metadata exists.