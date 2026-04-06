"""Workflow config normalization."""

from __future__ import annotations

from typing import Any

from ai_data_scientist.orchestration.models import (
    DEFAULT_TOOLS,
    OrchestratorSpec,
    RoleSpec,
    RuntimePolicy,
)

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
    prompt = str(value or "").strip()
    if not prompt:
        raise ValueError("Orchestrator roles must declare an explicit prompt path.")
    return prompt


def _build_orchestrator_spec(config: dict[str, Any]) -> OrchestratorSpec:
    roles_data = config.get("roles")
    runtime_data = config.get("runtime")
    if not isinstance(roles_data, dict) or not roles_data:
        raise ValueError("Orchestrator configs must declare roles and runtime.")
    if not isinstance(runtime_data, dict):
        raise ValueError("Orchestrator configs must declare roles and runtime.")

    roles: dict[str, RoleSpec] = {}
    for role_name, raw_role in roles_data.items():
        if not isinstance(raw_role, dict):
            raise ValueError(f"Role '{role_name}' must be a mapping.")
        backend = normalize_backend_name(raw_role.get("backend"))
        if backend is None:
            raise ValueError(f"Role '{role_name}' must declare a backend.")
        prompt = _normalize_prompt_ref(raw_role.get("prompt"))
        roles[role_name] = RoleSpec(
            role=role_name,
            backend=backend,
            prompt=prompt,
            model=str(raw_role.get("model", "") or ""),
            tools=_normalize_tools(raw_role.get("tools")),
            max_turns=int(raw_role.get("max_turns", 30) or 30),
        )

    runtime = RuntimePolicy(
        max_revision_rounds=int(runtime_data.get("max_revision_rounds", 1) or 1),
        max_reframes=int(runtime_data.get("max_reframes", 1) or 1),
        memory_curator=bool(runtime_data.get("memory_curator", True)),
    )

    return OrchestratorSpec(
        name=str(config.get("name") or "benchmark-workflow"),
        description=str(config.get("description") or ""),
        roles=roles,
        runtime=runtime,
    )


def normalize_workflow_config(config: dict[str, Any]) -> OrchestratorSpec:
    """Normalize the current orchestrator config shape."""
    if "team" in config or "workflow" in config:
        raise ValueError(
            "Legacy runtime configs are no longer supported; use roles + runtime."
        )
    if "roles" in config or "runtime" in config:
        return _build_orchestrator_spec(config)
    raise ValueError("Orchestrator configs must declare roles and runtime.")


def primary_agent_metadata(config: dict[str, Any]) -> dict[str, str | None]:
    """Infer provider role/model for scoring and imports."""
    if "roles" in config or "runtime" in config:
        roles = config.get("roles")
        runtime = config.get("runtime")
        if not isinstance(roles, dict) or not isinstance(runtime, dict) or not roles:
            raise ValueError("roles + runtime configs must define at least one role mapping.")

        preferred_role_name = next(
            (
                candidate
                for candidate in ("analysis_executor", "analysis_planner", "task_framer")
                if candidate in roles
            ),
            next(iter(roles.keys())),
        )
        primary_role = roles.get(preferred_role_name)
        if not isinstance(primary_role, dict):
            raise ValueError("roles + runtime configs must map role names to mappings.")
        return {
            "role": preferred_role_name,
            "model": str(primary_role.get("model") or "") or None,
        }

    team = config.get("team") or []
    primary = team[0] if team else {}
    backend = infer_backend_name(config) or "codex_cli"

    if isinstance(primary, dict) and primary.get("role"):
        return {
            "role": str(primary["role"]),
            "model": str(primary.get("model") or "") or None,
        }

    workflow = config.get("workflow") or {}
    steps = workflow.get("steps") if isinstance(workflow, dict) else []
    if isinstance(steps, list) and steps:
        first_step = steps[0] if isinstance(steps[0], dict) else {}
        if first_step.get("role") or first_step.get("id"):
            return {
                "role": str(first_step.get("role") or first_step.get("id")),
                "model": str(first_step.get("model") or "") or None,
            }
        return {
            "role": BACKEND_ROLE_NAMES.get(backend, backend),
            "model": str(first_step.get("model") or "") or None,
        }

    return {
        "role": str(config.get("name") or "agent"),
        "model": None,
    }
