`framing.json` written. Key decisions:

- **Primary frame**: Regression on `performance_rating` — the most natural continuous outcome in an employee dataset.
- **Conservative stance**: Multiple framing risks flag that the data may contain no real signal (performance_rating's distribution is consistent with pure noise, columns may be independent). The required checks prioritize null-model comparisons and correlation validation before any substantive modeling.