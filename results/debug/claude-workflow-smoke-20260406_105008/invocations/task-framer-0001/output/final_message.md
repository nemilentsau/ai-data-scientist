`framing.json` written. Key decisions:

- **Primary frame**: predicting `performance_rating` from employee attributes — the most natural continuous target given the schema.
- **Conservative stance**: required checks include a permutation/shuffle test to guard against spurious signal, and multicollinearity assessment before interpreting coefficients.
- **Risks flagged**: no declared target, plausible spurious correlations at n=800, suspicious zero-null pattern suggesting synthetic data, and a right-skewed commute distribution.