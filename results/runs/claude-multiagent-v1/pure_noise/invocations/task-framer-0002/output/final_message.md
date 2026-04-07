`framing.json` written. Summary:

- **Primary frame**: Regression to explain `performance_rating` from the other employee attributes — this is the most natural target given the schema.
- **Alternative frames**: Salary band classification, employee clustering, satisfaction prediction.
- **Key risks flagged**: No explicit target variable was provided; feature distributions and sample rows strongly suggest the data may be synthetic noise with no genuine signal (e.g., salary bands uncorrelated with experience, performance_rating suspiciously ~N(50,10)). Required checks include correlation testing, baseline model R², and a permutation test to distinguish real signal from noise.