"""Tests for orchestration config normalization."""

from __future__ import annotations

import pytest

from ai_data_scientist.orchestration.config import (
    normalize_workflow_config,
    primary_agent_metadata,
)


def test_roles_runtime_config_builds_role_and_runtime_specs():
    config = {
        "name": "codex-multiagent-v1",
        "description": "External orchestrator runtime",
        "roles": {
            "task_framer": {
                "backend": "claude_cli",
                "prompt": "prompts/active/task-framer.md",
                "model": "claude-opus-4-6",
            },
            "analysis_executor": {
                "backend": "codex_cli",
                "prompt": "prompts/active/analysis-executor.md",
                "model": "gpt-5.4",
                "tools": ["Read", "Write"],
            },
        },
        "runtime": {
            "max_revision_rounds": 1,
            "max_reframes": 1,
            "memory_curator": True,
        },
    }

    spec = normalize_workflow_config(config)

    assert spec.name == "codex-multiagent-v1"
    assert spec.description == "External orchestrator runtime"
    assert spec.roles["task_framer"].backend == "claude_cli"
    assert spec.roles["task_framer"].prompt == "prompts/active/task-framer.md"
    assert spec.roles["analysis_executor"].backend == "codex_cli"
    assert spec.roles["analysis_executor"].tools == ("Read", "Write")
    assert spec.runtime.max_revision_rounds == 1
    assert spec.runtime.max_reframes == 1
    assert spec.runtime.memory_curator is True


def test_roles_runtime_config_rejects_missing_prompt_path():
    config = {
        "name": "codex-multiagent-v1",
        "roles": {
            "task_framer": {
                "backend": "claude_cli",
            }
        },
        "runtime": {},
    }

    with pytest.raises(ValueError, match="explicit prompt path"):
        normalize_workflow_config(config)


def test_orchestrator_spec_rejects_legacy_workflow_fields():
    config = {
        "name": "codex-multiagent-v1",
        "roles": {
            "task_framer": {
                "backend": "claude_cli",
                "prompt": "prompts/active/task-framer.md",
            }
        },
        "runtime": {},
    }

    spec = normalize_workflow_config(config)

    with pytest.raises(TypeError, match="roles \\+ runtime"):
        _ = spec.backend

    with pytest.raises(TypeError, match="roles \\+ runtime"):
        _ = spec.steps


@pytest.mark.parametrize(
    "config",
    [
        {
            "name": "legacy-team",
            "team": [{"role": "codex", "prompt": "prompts/analyst-generic.md"}],
            "harness": "harness/run_codex.sh",
        },
        {
            "name": "legacy-workflow",
            "backend": "codex_cli",
            "workflow": {
                "steps": [
                    {
                        "id": "analyst",
                        "role": "analyst",
                        "prompt": "prompts/analyst-v2.md",
                    }
                ]
            },
        },
    ],
)
def test_legacy_runtime_configs_are_rejected(config: dict[str, object]):
    with pytest.raises(ValueError, match="Legacy runtime configs are no longer supported"):
        normalize_workflow_config(config)


def test_primary_agent_metadata_prefers_analysis_executor_for_roles_runtime():
    config = {
        "roles": {
            "task_framer": {
                "backend": "claude_cli",
                "prompt": "prompts/active/task-framer.md",
                "model": "claude-opus-4-6",
            },
            "analysis_executor": {
                "backend": "codex_cli",
                "prompt": "prompts/active/analysis-executor.md",
                "model": "gpt-5.4",
            },
        },
        "runtime": {"max_revision_rounds": 2},
    }

    metadata = primary_agent_metadata(config)

    assert metadata == {"role": "analysis_executor", "model": "gpt-5.4"}


def test_primary_agent_metadata_falls_back_to_first_role_when_preferred_roles_absent():
    config = {
        "roles": {
            "method_critic": {
                "backend": "claude_cli",
                "prompt": "prompts/active/method-critic.md",
                "model": "claude-opus-4-6",
            },
            "visual_critic": {
                "backend": "codex_cli",
                "prompt": "prompts/active/visual-critic.md",
                "model": "gpt-5.4",
            },
        },
        "runtime": {"max_reframes": 1},
    }

    metadata = primary_agent_metadata(config)

    assert metadata == {"role": "method_critic", "model": "claude-opus-4-6"}


def test_primary_agent_metadata_rejects_malformed_roles_entries():
    config = {
        "roles": {
            "analysis_executor": "not-a-mapping",
        },
        "runtime": {},
    }

    with pytest.raises(ValueError, match="roles \\+ runtime"):
        primary_agent_metadata(config)


def test_primary_agent_metadata_still_reads_legacy_team_configs():
    config = {
        "name": "solo-codex",
        "description": "Single Codex agent",
        "team": [{"role": "codex", "prompt": "prompts/analyst-generic.md", "max_turns": 30}],
        "harness": "harness/run_codex.sh",
    }

    metadata = primary_agent_metadata(config)

    assert metadata == {"role": "codex", "model": None}
