# Harness Scripts

The shell scripts in this directory are legacy provider harnesses kept for provenance and backward compatibility with older config snapshots.

The canonical execution path now lives in the Python package:

- `ai_data_scientist.orchestration.*`
- `ai_data_scientist.cli.benchmark`

Current configs may still include a `harness:` field for historical reasons, but benchmark execution is orchestrated by Python rather than these shell scripts.

