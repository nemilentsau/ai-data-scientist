`framing.json` written. Key decisions:

- **Primary frame**: Performance rating drivers — the most natural analytical question given the schema has one clear outcome variable (`performance_rating`) and several plausible predictors.
- **Required checks**: Emphasizes statistical significance testing and a global null-model F-test before any interpretation, which is critical given the noise risk.
- **Framing risks**: Flags that features may be pure noise with no true signal, synthetic data limitations, and the ambiguity around which variable is the target (since none is explicitly labeled).