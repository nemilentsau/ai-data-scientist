"""Experiment id helpers."""

from __future__ import annotations

import re
from datetime import UTC, datetime


def build_experiment_id(now: datetime | None = None, slug: str | None = None) -> str:
    """Build a stable experiment id from a timestamp and optional slug."""
    timestamp = (now or datetime.now(UTC)).strftime("%Y%m%d_%H%M%S")
    suffix = slugify(slug or "")
    if suffix:
        return f"exp_{timestamp}_{suffix}"
    return f"exp_{timestamp}"


def slugify(value: str) -> str:
    """Normalize an arbitrary string into a lowercase URL/path-safe slug."""
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower())
    return normalized.strip("-")

