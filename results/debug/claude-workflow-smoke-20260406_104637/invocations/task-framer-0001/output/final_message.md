`framing.json` written. Key decisions:

- **Primary frame**: Predicting/explaining `performance_rating` — the most natural continuous target in an employee dataset.
- **Framing risks** flag the strong possibility that this is pure-noise synthetic data (zero nulls, clean ranges, no visible correlations in sample rows), so any discovered relationships should be validated against a permutation-null baseline.
- **Required checks** emphasize multiple-comparison correction and permutation testing to guard against spurious findings.