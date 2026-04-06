"""Ledger and bounded-memory helpers for the external orchestrator."""

from __future__ import annotations

import json
from pathlib import Path


def initialize_ledgers(run_dir: Path) -> dict[str, Path]:
    """Create canonical ledger files for the current run if they do not exist."""
    ledgers_dir = run_dir / "artifacts" / "ledgers"
    ledgers_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "hypotheses": ledgers_dir / "hypothesis_ledger.json",
        "experiments": ledgers_dir / "experiment_ledger.json",
        "issues": ledgers_dir / "issue_ledger.json",
    }
    for path in files.values():
        if not path.exists():
            path.write_text('{"items":[]}\n')
    return files


def role_memory_paths(run_dir: Path) -> dict[str, Path]:
    """Return bounded memory files for roles that consume curator summaries."""
    memory_dir = run_dir / "artifacts" / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    return {
        "task_framer": memory_dir / "task_framer.md",
        "analysis_planner": memory_dir / "analysis_planner.md",
    }


def collect_memory_inputs(run_dir: Path) -> list[Path]:
    """Return all published artifact files for downstream roles."""
    artifact_root = run_dir / "artifacts"
    if not artifact_root.exists():
        return []
    return [path for path in sorted(artifact_root.rglob("*")) if path.is_file()]


def collect_task5_feedback_inputs(run_dir: Path) -> list[Path]:
    """Return published critique and verification artifacts for the next round."""
    artifacts_dir = run_dir / "artifacts"
    feedback_roots = [
        artifacts_dir / "critiques" / "method_critic",
        artifacts_dir / "critiques" / "visual_critic",
        artifacts_dir / "verification",
    ]
    paths: list[Path] = []
    seen: set[Path] = set()
    for root in feedback_roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            paths.append(path)
    return paths


def read_verification_verdict(run_dir: Path) -> str:
    """Load the verifier verdict from the canonical published artifact tree."""
    verification_path = run_dir / "artifacts" / "verification" / "verification.json"
    payload = json.loads(verification_path.read_text())
    return str(payload.get("verdict") or "")
