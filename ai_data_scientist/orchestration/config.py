"""Workflow config normalization."""

from __future__ import annotations

from typing import Any

from ai_data_scientist.orchestration.models import DEFAULT_TOOLS, WorkflowSpec, WorkflowStep

DEFAULT_PROMPT_PATH = "harness/prompt_template.txt"
BACKEND_ROLE_NAMES = {
    "codex_cli": "codex",
    "claude_cli": "claude",
}
BACKEND_ALIASES = {
    "codex": "codex_cli",
    "codex_cli": "codex_cli",
    "claude": "claude_cli",
    "claude_cli": "claude_cli",
}


def normalize_backend_name(value: str | None) -> str | None:
    """Map config/backend aliases into normalized backend names."""
    if value is None:
        return None
    return BACKEND_ALIASES.get(str(value).strip())


def infer_backend_name(config: dict[str, Any]) -> str | None:
    """Infer the backend from config role or legacy harness path."""
    team = config.get("team") or []
    primary = team[0] if team else {}
    backend = normalize_backend_name(primary.get("role"))
    if backend is not None:
        return backend

    harness = str(config.get("harness", ""))
    if "codex" in harness:
        return "codex_cli"
    if "claude" in harness:
        return "claude_cli"
    return None


def _normalize_tools(value: Any) -> tuple[str, ...]:
    if not value:
        return DEFAULT_TOOLS
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value)
    return tuple(str(value).split(","))


def _normalize_prompt_ref(value: Any) -> str:
    prompt = str(value or DEFAULT_PROMPT_PATH).strip()
    return prompt or DEFAULT_PROMPT_PATH


def _build_old_style_workflow(config: dict[str, Any]) -> WorkflowSpec:
    team = config.get("team") or []
    primary = team[0] if team else {}
    backend = infer_backend_name(config)
    if backend is None:
        raise ValueError("Could not infer backend from legacy config.")

    step = WorkflowStep(
        id="analyst",
        role="analyst",
        prompt=_normalize_prompt_ref(primary.get("prompt")),
        model=str(primary.get("model", "") or ""),
        tools=_normalize_tools(primary.get("tools")),
        max_turns=int(primary.get("max_turns", 30) or 30),
        image_inputs=(),
        required=True,
    )
    return WorkflowSpec(
        name=str(config.get("name") or "benchmark-workflow"),
        description=str(config.get("description") or ""),
        backend=backend,
        steps=(step,),
    )


def _build_new_style_workflow(config: dict[str, Any]) -> WorkflowSpec:
    backend = normalize_backend_name(config.get("backend"))
    if backend is None:
        raise ValueError("New-style workflow configs must declare backend.")

    workflow = config.get("workflow") or {}
    steps_data = workflow.get("steps")
    if not isinstance(steps_data, list) or not steps_data:
        raise ValueError("New-style workflow configs must declare workflow.steps.")

    steps: list[WorkflowStep] = []
    for index, raw_step in enumerate(steps_data, start=1):
        steps.append(
            WorkflowStep(
                id=str(raw_step.get("id") or f"step_{index}"),
                role=str(raw_step.get("role") or raw_step.get("id") or f"step_{index}"),
                prompt=_normalize_prompt_ref(raw_step.get("prompt")),
                model=str(raw_step.get("model", "") or ""),
                tools=_normalize_tools(raw_step.get("tools")),
                max_turns=int(raw_step.get("max_turns", 30) or 30),
                image_inputs=tuple(
                    str(item) for item in raw_step.get("image_inputs", []) or []
                ),
                required=bool(raw_step.get("required", True)),
            )
        )

    return WorkflowSpec(
        name=str(config.get("name") or "benchmark-workflow"),
        description=str(config.get("description") or ""),
        backend=backend,
        steps=tuple(steps),
    )


def normalize_workflow_config(config: dict[str, Any]) -> WorkflowSpec:
    """Normalize legacy and new workflow config shapes."""
    if "workflow" in config:
        return _build_new_style_workflow(config)
    return _build_old_style_workflow(config)


def primary_agent_metadata(config: dict[str, Any]) -> dict[str, str | None]:
    """Infer provider role/model for scoring and imports."""
    team = config.get("team") or []
    primary = team[0] if team else {}
    backend = infer_backend_name(config) or "codex_cli"

    if primary.get("role") and "model" in primary:
        return {
            "role": str(primary["role"]),
            "model": str(primary.get("model") or "") or None,
        }

    try:
        spec = normalize_workflow_config(config)
    except ValueError:
        return {
            "role": str(config.get("name") or "agent"),
            "model": None,
        }

    return {
        "role": BACKEND_ROLE_NAMES.get(spec.backend, backend),
        "model": spec.steps[0].model or None,
    }

