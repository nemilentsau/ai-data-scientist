"""Tests for invocation isolation and publish contracts."""

from __future__ import annotations

import json
import os
from pathlib import Path

import ai_data_scientist.orchestration.runner as orchestration_runner
from ai_data_scientist.orchestration import prompts
from ai_data_scientist.orchestration.adapters import claude_cli, codex_cli
from ai_data_scientist.orchestration.ledgers import collect_memory_inputs
from ai_data_scientist.orchestration.models import (
    InvocationResult,
    PublishContract,
    RoleSpec,
    RunContext,
    WorkflowStep,
)
from ai_data_scientist.orchestration.outputs import publish_declared_outputs
from ai_data_scientist.orchestration.workspace import create_invocation_context
from ai_data_scientist.orchestration.runner import run_workflow


def test_create_invocation_context_materializes_only_declared_inputs(tmp_path: Path):
    run_dir = tmp_path / "results" / "runs" / "codex-multiagent-v1" / "multimodal"
    input_artifact = run_dir / "artifacts" / "framing" / "framing.json"
    input_artifact.parent.mkdir(parents=True, exist_ok=True)
    input_artifact.write_text('{"primary_frame":"mixture"}')

    invocation = create_invocation_context(
        run_dir=run_dir,
        role=RoleSpec(role="analysis_planner", backend="claude_cli", prompt="prompt.md"),
        artifact_inputs=[input_artifact],
    )

    assert invocation.input_dir == run_dir / "invocations" / "analysis-planner-0001" / "input"
    assert (invocation.input_dir / "artifacts" / "framing" / "framing.json").read_text() == (
        '{"primary_frame":"mixture"}'
    )
    assert (invocation.work_dir / "analysis_report.md").exists() is False


def test_create_invocation_context_uses_unique_ids_for_repeated_roles(tmp_path: Path):
    run_dir = tmp_path / "results" / "runs" / "codex-multiagent-v1" / "multimodal"

    first = create_invocation_context(
        run_dir=run_dir,
        role=RoleSpec(role="analysis_planner", backend="claude_cli", prompt="prompt.md"),
        artifact_inputs=[],
    )
    second = create_invocation_context(
        run_dir=run_dir,
        role=RoleSpec(role="analysis_planner", backend="claude_cli", prompt="prompt.md"),
        artifact_inputs=[],
    )

    assert first.invocation_id == "analysis-planner-0001"
    assert second.invocation_id == "analysis-planner-0002"


def test_publish_declared_outputs_copies_only_declared_outputs_from_output_dir(tmp_path: Path):
    run_dir = tmp_path / "results" / "runs" / "codex-multiagent-v1" / "multimodal"
    invocation = create_invocation_context(
        run_dir=run_dir,
        role=RoleSpec(role="analysis_executor", backend="codex_cli", prompt="prompt.md"),
        artifact_inputs=[],
    )

    (invocation.output_dir / "analysis_report.md").write_text("# Analysis\n")
    (invocation.output_dir / "scratch.txt").write_text("debug only")

    published = publish_declared_outputs(
        run_dir=run_dir,
        invocation=invocation,
        contract=PublishContract(
            role="analysis_executor",
            declared_outputs=("analysis_report.md",),
        ),
    )

    assert published == [run_dir / "artifacts" / "analysis" / "analysis_report.md"]
    assert (run_dir / "artifacts" / "analysis" / "analysis_report.md").read_text() == (
        "# Analysis\n"
    )
    assert not (run_dir / "artifacts" / "analysis" / "scratch.txt").exists()


def test_publish_declared_outputs_preserves_nested_relative_paths(tmp_path: Path):
    run_dir = tmp_path / "results" / "runs" / "codex-multiagent-v1" / "multimodal"
    invocation = create_invocation_context(
        run_dir=run_dir,
        role=RoleSpec(role="analysis_executor", backend="codex_cli", prompt="prompt.md"),
        artifact_inputs=[],
    )

    nested_output = invocation.output_dir / "plots" / "diagnostics" / "residuals.png"
    nested_output.parent.mkdir(parents=True, exist_ok=True)
    nested_output.write_text("png-bytes")

    published = publish_declared_outputs(
        run_dir=run_dir,
        invocation=invocation,
        contract=PublishContract(
            role="analysis_executor",
            declared_outputs=("plots/diagnostics/residuals.png",),
        ),
    )

    assert published == [
        run_dir
        / "artifacts"
        / "analysis"
        / "plots"
        / "diagnostics"
        / "residuals.png"
    ]
    assert (
        run_dir / "artifacts" / "analysis" / "plots" / "diagnostics" / "residuals.png"
    ).read_text() == "png-bytes"


def test_publish_declared_outputs_separates_method_and_visual_critics(tmp_path: Path):
    run_dir = tmp_path / "results" / "runs" / "codex-multiagent-v1" / "multimodal"
    method_invocation = create_invocation_context(
        run_dir=run_dir,
        role=RoleSpec(role="method_critic", backend="claude_cli", prompt="prompt.md"),
        artifact_inputs=[],
    )
    visual_invocation = create_invocation_context(
        run_dir=run_dir,
        role=RoleSpec(role="visual_critic", backend="claude_cli", prompt="prompt.md"),
        artifact_inputs=[],
    )

    (method_invocation.output_dir / "critique.md").write_text("method critique")
    (visual_invocation.output_dir / "critique.md").write_text("visual critique")

    method_published = publish_declared_outputs(
        run_dir=run_dir,
        invocation=method_invocation,
        contract=PublishContract(role="method_critic", declared_outputs=("critique.md",)),
    )
    visual_published = publish_declared_outputs(
        run_dir=run_dir,
        invocation=visual_invocation,
        contract=PublishContract(role="visual_critic", declared_outputs=("critique.md",)),
    )

    assert method_published == [
        run_dir / "artifacts" / "critiques" / "method_critic" / "critique.md"
    ]
    assert visual_published == [
        run_dir / "artifacts" / "critiques" / "visual_critic" / "critique.md"
    ]
    assert (
        run_dir / "artifacts" / "critiques" / "method_critic" / "critique.md"
    ).read_text() == "method critique"
    assert (
        run_dir / "artifacts" / "critiques" / "visual_critic" / "critique.md"
    ).read_text() == "visual critique"


def test_publish_declared_outputs_skips_missing_files_without_failing(tmp_path: Path):
    run_dir = tmp_path / "results" / "runs" / "codex-multiagent-v1" / "multimodal"
    invocation = create_invocation_context(
        run_dir=run_dir,
        role=RoleSpec(role="analysis_executor", backend="codex_cli", prompt="prompt.md"),
        artifact_inputs=[],
    )

    published = publish_declared_outputs(
        run_dir=run_dir,
        invocation=invocation,
        contract=PublishContract(
            role="analysis_executor",
            declared_outputs=("analysis_report.md", "claim_evidence_map.json"),
        ),
    )

    assert published == []
    assert not (run_dir / "artifacts" / "analysis" / "analysis_report.md").exists()


def test_codex_adapter_invoke_uses_fresh_workspace_without_resume(
    tmp_path: Path, monkeypatch
):
    recorded_commands: list[list[str]] = []
    recorded_workdirs: list[Path] = []
    role = RoleSpec(
        role="analysis_executor",
        backend="codex_cli",
        prompt="prompts/active/analysis-executor.md",
    )
    run_context = RunContext(
        root=tmp_path,
        dataset_name="multimodal",
        results_dir=tmp_path / "results",
        work_dir=tmp_path / "run-work",
        backend="codex_cli",
        env=os.environ.copy(),
        top_trace_path=tmp_path / "results" / "trace.jsonl",
        run_state_path=tmp_path / "results" / "run_state.json",
        top_session_log_path=tmp_path / "results" / "session.log",
    )
    invocation = create_invocation_context(
        run_dir=run_context.results_dir,
        role=role,
        artifact_inputs=[],
    )

    def fake_run(command, **kwargs):
        recorded_commands.append(command)
        recorded_workdirs.append(Path(kwargs["cwd"]))
        if "stdout" not in kwargs:
            return type("Completed", (), {"returncode": 0, "stdout": "codex 1.0"})()
        kwargs["stdout"].write('{"type":"thread.started","thread_id":"fresh-thread"}\n')
        kwargs["stdout"].flush()
        return type("Completed", (), {"returncode": 0})()

    monkeypatch.setattr(codex_cli.subprocess, "run", fake_run)

    adapter = codex_cli.CodexCliAdapter(tmp_path)
    adapter.prepare_run(run_context)
    result = adapter.invoke(role, run_context, invocation, "Analyze the published artifacts.")

    assert result.status == "completed"
    assert recorded_commands
    assert all("resume" not in command for command in recorded_commands)
    assert recorded_workdirs[-1] == invocation.work_dir
    assert invocation.work_dir in recorded_workdirs
    assert invocation.work_dir.exists()


def test_codex_bridge_uses_invocation_copies_for_prompt_and_attachments(
    tmp_path: Path, monkeypatch
):
    recorded_artifact_inputs: list[list[Path]] = []
    recorded_commands: list[list[str]] = []
    role = RoleSpec(
        role="analysis_executor",
        backend="codex_cli",
        prompt="prompts/active/analysis-executor.md",
    )
    run_context = RunContext(
        root=tmp_path,
        dataset_name="multimodal",
        results_dir=tmp_path / "results",
        work_dir=tmp_path / "work",
        backend="codex_cli",
        env=os.environ.copy(),
        top_trace_path=tmp_path / "results" / "trace.jsonl",
        run_state_path=tmp_path / "results" / "run_state.json",
        top_session_log_path=tmp_path / "results" / "session.log",
    )
    run_context.work_dir.mkdir(parents=True, exist_ok=True)
    run_context.results_dir.mkdir(parents=True, exist_ok=True)
    original_image = run_context.work_dir / "plots" / "chart.png"
    original_image.parent.mkdir(parents=True, exist_ok=True)
    original_image.write_bytes(b"png")
    run_context.matched_inputs["analyst"] = [original_image]

    def fake_render_role_prompt(*, root, role, artifact_inputs, role_memory, invocation_cwd):
        del root, role, role_memory, invocation_cwd
        recorded_artifact_inputs.append(list(artifact_inputs))
        return "Analyze the published artifacts."

    def fake_run(command, **kwargs):
        recorded_commands.append(command)
        if "stdout" not in kwargs:
            return type("Completed", (), {"returncode": 0, "stdout": "codex 1.0"})()
        kwargs["stdout"].write('{"type":"thread.started","thread_id":"fresh-thread"}\n')
        kwargs["stdout"].flush()
        return type("Completed", (), {"returncode": 0})()

    monkeypatch.setattr(codex_cli, "render_role_prompt", fake_render_role_prompt)
    monkeypatch.setattr(codex_cli.subprocess, "run", fake_run)

    adapter = codex_cli.CodexCliAdapter(tmp_path)
    adapter.prepare_run(run_context)
    adapter.start_step(
        WorkflowStep(id="analyst", role="analysis_executor", prompt="prompt.md"),
        run_context,
    )

    expected_copy = run_context.results_dir / "invocations" / "analysis-executor-0001" / "input" / "plots" / "chart.png"
    assert recorded_artifact_inputs == [[expected_copy]]
    assert original_image not in recorded_artifact_inputs[0]
    assert any("-i" in command for command in recorded_commands)
    assert expected_copy.as_posix() in recorded_commands[-1]


def test_claude_adapter_invoke_uses_fresh_workspace_without_resume(
    tmp_path: Path, monkeypatch
):
    recorded_commands: list[list[str]] = []
    recorded_workdirs: list[Path] = []
    role = RoleSpec(
        role="task_framer",
        backend="claude_cli",
        prompt="prompts/active/task-framer.md",
        tools=("Bash", "Read"),
    )
    run_context = RunContext(
        root=tmp_path,
        dataset_name="multimodal",
        results_dir=tmp_path / "results",
        work_dir=tmp_path / "run-work",
        backend="claude_cli",
        env=os.environ.copy(),
        top_trace_path=tmp_path / "results" / "trace.jsonl",
        run_state_path=tmp_path / "results" / "run_state.json",
        top_session_json_path=tmp_path / "results" / "session.json",
    )
    invocation = create_invocation_context(
        run_dir=run_context.results_dir,
        role=role,
        artifact_inputs=[],
    )
    (tmp_path / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".claude" / "settings.json").write_text("{}")
    (tmp_path / ".claude" / "hooks" / "trace.sh").write_text("#!/usr/bin/env bash\n")

    def fake_run(command, **kwargs):
        recorded_commands.append(command)
        recorded_workdirs.append(Path(kwargs["cwd"]))
        if kwargs["cwd"] != run_context.work_dir and not (Path(kwargs["cwd"]) / ".claude" / "settings.json").exists():
            raise AssertionError(".claude settings were not visible in the invocation cwd")
        kwargs["stdout"].write('{"result":"ok"}')
        kwargs["stdout"].flush()
        return type("Completed", (), {"returncode": 0})()

    monkeypatch.setattr(claude_cli.subprocess, "run", fake_run)

    adapter = claude_cli.ClaudeCliAdapter(tmp_path)
    adapter.prepare_run(run_context)
    result = adapter.invoke(role, run_context, invocation, "Frame the task.")

    assert result.status == "completed"
    assert recorded_commands
    assert all("--resume" not in command for command in recorded_commands)
    assert recorded_workdirs == [invocation.work_dir]
    assert invocation.work_dir.exists()


def test_render_role_prompt_uses_published_artifacts_and_role_memory_only(tmp_path: Path):
    prompt_root = tmp_path / "repo"
    prompt_file = prompt_root / "prompts" / "active" / "analysis-planner.md"
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text("Plan the next round.\n")

    published_artifacts = [
        tmp_path / "results" / "runs" / "run-1" / "artifacts" / "framing" / "framing.json",
        tmp_path / "results" / "runs" / "run-1" / "artifacts" / "profile" / "schema.json",
    ]
    for artifact in published_artifacts:
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("{}")

    role_memory = tmp_path / "results" / "runs" / "run-1" / "memory" / "analysis_planner.md"
    role_memory.parent.mkdir(parents=True, exist_ok=True)
    role_memory.write_text("Do not repeat exp_1.\n")

    rendered = prompts.render_role_prompt(
        root=prompt_root,
        role=RoleSpec(
            role="analysis_planner",
            backend="claude_cli",
            prompt="prompts/active/analysis-planner.md",
        ),
        artifact_inputs=published_artifacts,
        role_memory=role_memory,
        invocation_cwd=None,
    )

    assert "Role memory for this invocation:" in rendered
    assert "Do not repeat exp_1." in rendered
    assert "Published input artifacts for this invocation" in rendered
    assert "framing.json" in rendered
    assert "schema.json" in rendered
    assert "Plan the next round." in rendered


def test_render_role_prompt_uses_paths_relative_to_invocation_workspace(tmp_path: Path):
    prompt_root = tmp_path / "repo"
    prompt_file = prompt_root / "prompts" / "active" / "task-framer.md"
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text("Write framing.json.\n")

    invocation_root = (
        tmp_path
        / "results"
        / "runs"
        / "run-1"
        / "invocations"
        / "task-framer-0001"
    )
    artifact = invocation_root / "input" / "artifacts" / "profile" / "schema.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("{}")
    invocation_cwd = invocation_root / "workspace"
    invocation_cwd.mkdir(parents=True, exist_ok=True)

    rendered = prompts.render_role_prompt(
        root=prompt_root,
        role=RoleSpec(
            role="task_framer",
            backend="claude_cli",
            prompt="prompts/active/task-framer.md",
        ),
        artifact_inputs=[artifact],
        role_memory=None,
        invocation_cwd=invocation_cwd,
    )

    assert "../input/artifacts/profile/schema.json" in rendered
    assert "results/runs/run-1/invocations/task-framer-0001" not in rendered


def test_runner_executes_task_framer_planner_executor_in_order(
    tmp_path: Path, monkeypatch
):
    root = tmp_path / "repo"
    root.mkdir()
    dataset_csv = root / "dataset.csv"
    dataset_csv.write_text("x,y\n1,2\n")
    results_dir = root / "results" / "runs" / "codex-multiagent-v1" / "multimodal"
    calls: list[str] = []
    config = {
        "name": "codex-multiagent-v1",
        "description": "External orchestrator runtime",
        "roles": {
            "task_framer": {
                "backend": "claude_cli",
                "prompt": "prompts/active/task-framer.md",
            },
            "analysis_planner": {
                "backend": "claude_cli",
                "prompt": "prompts/active/analysis-planner.md",
            },
            "analysis_executor": {
                "backend": "codex_cli",
                "prompt": "prompts/active/analysis-executor.md",
            },
        },
        "runtime": {
            "max_revision_rounds": 1,
            "max_reframes": 1,
            "memory_curator": False,
        },
    }
    render_calls: list[tuple[str, list[Path]]] = []

    rendered_cwds: list[Path | None] = []

    def fake_render_role_prompt(*, root, role, artifact_inputs, role_memory, invocation_cwd):
        del root, role_memory
        render_calls.append((role.role, list(artifact_inputs)))
        rendered_cwds.append(invocation_cwd)
        assert artifact_inputs
        assert all(path.is_relative_to(results_dir / "invocations") for path in artifact_inputs)
        assert all("/artifacts/" not in str(path) or "/input/artifacts/" in str(path) for path in artifact_inputs)
        return f"prompt::{role.role}"

    class FakeAdapter:
        def __init__(self, _root: Path):
            self.root = _root

        def prepare_run(self, context):
            del context

        def invoke(self, role, context, invocation, prompt):
            del context, prompt
            calls.append(role.role)
            dataset_path = invocation.input_dir / "artifacts" / "dataset" / "dataset.csv"
            assert dataset_path.exists()
            if role.role == "task_framer":
                assert (invocation.input_dir / "artifacts" / "profile" / "schema.json").exists()
                (invocation.work_dir / "framing.json").write_text(
                    '{"primary_frame":"regression"}'
                )
            elif role.role == "analysis_planner":
                assert (invocation.input_dir / "artifacts" / "dataset" / "dataset.csv").exists()
                assert (invocation.input_dir / "artifacts" / "profile" / "schema.json").exists()
                assert (invocation.input_dir / "artifacts" / "framing" / "framing.json").exists()
                (invocation.work_dir / "analysis_plan.md").write_text("# Plan\n")
                (invocation.work_dir / "hypotheses.json").write_text('{"items":[{"id":"hyp_1"}]}')
                (invocation.work_dir / "experiment_plan.json").write_text(
                    '{"items":[{"id":"exp_1"}]}'
                )
            elif role.role == "analysis_executor":
                assert (invocation.input_dir / "artifacts" / "dataset" / "dataset.csv").exists()
                assert (invocation.input_dir / "artifacts" / "profile" / "schema.json").exists()
                assert (invocation.input_dir / "artifacts" / "framing" / "framing.json").exists()
                assert (invocation.input_dir / "artifacts" / "planning" / "analysis_plan.md").exists()
                (invocation.work_dir / "analysis_report.md").write_text("# Analysis\n")
                (invocation.work_dir / "findings.json").write_text('{"items":[{"id":"finding_1"}]}')
                (invocation.work_dir / "claim_evidence_map.json").write_text(
                    '{"items":[{"claim_id":"claim_1","evidence_ids":["ev_1"]}]}'
                )
                plot_dir = invocation.work_dir / "plots" / "diagnostics"
                plot_dir.mkdir(parents=True, exist_ok=True)
                (plot_dir / "residuals.png").write_text("png-bytes")
                stats_dir = invocation.work_dir / "stats"
                stats_dir.mkdir(parents=True, exist_ok=True)
                (stats_dir / "summary.json").write_text('{"rows":1}')
            return InvocationResult(
                status="completed",
                final_message_path=invocation.work_dir / "final.md",
                raw_trace_path=invocation.trace_dir / "trace.jsonl",
    )

    monkeypatch.setitem(orchestration_runner.BACKEND_ADAPTERS, "codex_cli", FakeAdapter)
    monkeypatch.setitem(orchestration_runner.BACKEND_ADAPTERS, "claude_cli", FakeAdapter)
    monkeypatch.setattr(orchestration_runner, "render_role_prompt", fake_render_role_prompt)
    monkeypatch.setattr(
        orchestration_runner,
        "prepare_run_context",
        lambda **kwargs: RunContext(
            root=kwargs["root"],
            dataset_name=kwargs["dataset_name"],
            results_dir=kwargs["results_dir"],
            work_dir=kwargs["results_dir"] / "work",
            backend=kwargs["backend"],
            env=os.environ.copy(),
            top_trace_path=kwargs["results_dir"] / "trace.jsonl",
            run_state_path=kwargs["results_dir"] / "run_state.json",
            top_session_log_path=kwargs["results_dir"] / "session.log",
            top_session_json_path=kwargs["results_dir"] / "session.json",
            top_final_message_path=kwargs["results_dir"] / "final_message.md",
        ),
    )

    succeeded = run_workflow(
        config=config,
        dataset_name="multimodal",
        dataset_csv=dataset_csv,
        results_dir=results_dir,
        root=root,
    )

    assert succeeded is True
    assert calls == ["task_framer", "analysis_planner", "analysis_executor"]
    assert [role for role, _ in render_calls] == [
        "task_framer",
        "analysis_planner",
        "analysis_executor",
    ]
    assert rendered_cwds == [
        results_dir / "invocations" / "task-framer-0001" / "workspace",
        results_dir / "invocations" / "analysis-planner-0001" / "workspace",
        results_dir / "invocations" / "analysis-executor-0001" / "workspace",
    ]
    assert (results_dir / "artifacts" / "profile" / "schema.json").exists()
    assert (results_dir / "artifacts" / "dataset" / "dataset.csv").exists()
    assert (results_dir / "artifacts" / "framing" / "framing.json").exists()
    assert (results_dir / "artifacts" / "planning" / "analysis_plan.md").exists()
    assert (results_dir / "artifacts" / "analysis" / "analysis_report.md").exists()
    assert (
        results_dir / "artifacts" / "analysis" / "findings.json"
    ).exists()
    assert (
        results_dir / "artifacts" / "analysis" / "claim_evidence_map.json"
    ).exists()
    assert (
        results_dir
        / "artifacts"
        / "analysis"
        / "plots"
        / "diagnostics"
        / "residuals.png"
    ).exists()
    assert (
        results_dir / "artifacts" / "analysis" / "stats" / "summary.json"
    ).exists()


def test_runner_writes_invocation_manifest_for_each_role(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    dataset_csv = root / "dataset.csv"
    dataset_csv.write_text("x,y\n1,2\n")
    results_dir = root / "results" / "runs" / "codex-multiagent-v1" / "multimodal"
    config = {
        "name": "codex-multiagent-v1",
        "description": "External orchestrator runtime",
        "roles": {
            "task_framer": {
                "backend": "claude_cli",
                "prompt": "prompts/active/task-framer.md",
            },
            "analysis_planner": {
                "backend": "claude_cli",
                "prompt": "prompts/active/analysis-planner.md",
            },
            "analysis_executor": {
                "backend": "codex_cli",
                "prompt": "prompts/active/analysis-executor.md",
            },
        },
        "runtime": {
            "max_revision_rounds": 1,
            "max_reframes": 1,
            "memory_curator": False,
        },
    }

    class FakeAdapter:
        def __init__(self, _root: Path):
            self.root = _root

        def prepare_run(self, context):
            del context

        def invoke(self, role, context, invocation, prompt):
            del context, prompt
            if role.role == "task_framer":
                (invocation.work_dir / "framing.json").write_text('{"primary_frame":"regression"}')
            elif role.role == "analysis_planner":
                (invocation.work_dir / "analysis_plan.md").write_text("# Plan\n")
                (invocation.work_dir / "hypotheses.json").write_text('{"items":[{"id":"hyp_1"}]}')
                (invocation.work_dir / "experiment_plan.json").write_text(
                    '{"items":[{"id":"exp_1"}]}'
                )
            elif role.role == "analysis_executor":
                (invocation.work_dir / "analysis_report.md").write_text("# Analysis\n")
                (invocation.work_dir / "findings.json").write_text('{"items":[{"id":"finding_1"}]}')
                (invocation.work_dir / "claim_evidence_map.json").write_text('{"items":[]}')
                (invocation.work_dir / "plots").mkdir(parents=True, exist_ok=True)
                (invocation.work_dir / "stats").mkdir(parents=True, exist_ok=True)
            return InvocationResult(
                status="completed",
                final_message_path=invocation.work_dir / "final.md",
                raw_trace_path=invocation.trace_dir / "trace.jsonl",
            )

    monkeypatch.setitem(orchestration_runner.BACKEND_ADAPTERS, "codex_cli", FakeAdapter)
    monkeypatch.setitem(orchestration_runner.BACKEND_ADAPTERS, "claude_cli", FakeAdapter)
    monkeypatch.setattr(
        orchestration_runner,
        "prepare_run_context",
        lambda **kwargs: RunContext(
            root=kwargs["root"],
            dataset_name=kwargs["dataset_name"],
            results_dir=kwargs["results_dir"],
            work_dir=kwargs["results_dir"] / "work",
            backend=kwargs["backend"],
            env=os.environ.copy(),
            top_trace_path=kwargs["results_dir"] / "trace.jsonl",
            run_state_path=kwargs["results_dir"] / "run_state.json",
            top_session_log_path=kwargs["results_dir"] / "session.log",
            top_session_json_path=kwargs["results_dir"] / "session.json",
            top_final_message_path=kwargs["results_dir"] / "final_message.md",
        ),
    )

    succeeded = run_workflow(
        config=config,
        dataset_name="multimodal",
        dataset_csv=dataset_csv,
        results_dir=results_dir,
        root=root,
    )

    assert succeeded is True

    task_manifest = json.loads(
        (results_dir / "invocations" / "task-framer-0001" / "manifest.json").read_text()
    )
    planner_manifest = json.loads(
        (results_dir / "invocations" / "analysis-planner-0001" / "manifest.json").read_text()
    )
    executor_manifest = json.loads(
        (results_dir / "invocations" / "analysis-executor-0001" / "manifest.json").read_text()
    )

    assert task_manifest["invocation_id"] == "task-framer-0001"
    assert task_manifest["role"] == "task_framer"
    assert task_manifest["status"] == "completed"
    assert planner_manifest["invocation_id"] == "analysis-planner-0001"
    assert planner_manifest["role"] == "analysis_planner"
    assert planner_manifest["status"] == "completed"
    assert executor_manifest["invocation_id"] == "analysis-executor-0001"
    assert executor_manifest["role"] == "analysis_executor"
    assert executor_manifest["status"] == "completed"


def test_verifier_revise_runs_a_new_planner_executor_and_critics_round(
    tmp_path: Path, monkeypatch
):
    root = tmp_path / "repo"
    root.mkdir()
    dataset_csv = root / "dataset.csv"
    dataset_csv.write_text("x,y\n1,2\n")
    results_dir = root / "results" / "runs" / "codex-multiagent-v1" / "multimodal"
    calls: list[str] = []
    input_snapshots: dict[str, list[list[str]]] = {}
    verifier_calls = {"count": 0}
    config = {
        "name": "codex-multiagent-v1",
        "description": "External orchestrator runtime",
        "roles": {
            "task_framer": {"backend": "claude_cli", "prompt": "prompts/active/task-framer.md"},
            "analysis_planner": {
                "backend": "claude_cli",
                "prompt": "prompts/active/analysis-planner.md",
            },
            "analysis_executor": {
                "backend": "codex_cli",
                "prompt": "prompts/active/analysis-executor.md",
            },
            "method_critic": {"backend": "claude_cli", "prompt": "prompts/active/method-critic.md"},
            "visual_critic": {"backend": "claude_cli", "prompt": "prompts/active/visual-critic.md"},
            "verifier": {"backend": "claude_cli", "prompt": "prompts/active/verifier.md"},
            "memory_curator": {"backend": "claude_cli", "prompt": "prompts/active/memory-curator.md"},
        },
        "runtime": {"max_revision_rounds": 1, "max_reframes": 0, "memory_curator": True},
    }

    class FakeAdapter:
        def __init__(self, _root: Path):
            self.root = _root

        def prepare_run(self, context):
            del context

        def invoke(self, role, context, invocation, prompt):
            del context, prompt
            calls.append(role.role)
            input_snapshots.setdefault(role.role, []).append(
                sorted(
                    str(path.relative_to(invocation.input_dir))
                    for path in invocation.input_dir.rglob("*")
                    if path.is_file()
                )
            )
            if role.role == "task_framer":
                (invocation.work_dir / "framing.json").write_text('{"primary_frame":"regression"}')
            elif role.role == "analysis_planner":
                (invocation.work_dir / "analysis_plan.md").write_text("# Plan\n")
                (invocation.work_dir / "hypotheses.json").write_text('{"items":[{"id":"hyp_1"}]}')
                (invocation.work_dir / "experiment_plan.json").write_text(
                    '{"items":[{"id":"exp_1"}]}'
                )
            elif role.role == "analysis_executor":
                (invocation.work_dir / "analysis_report.md").write_text("# Analysis\n")
                (invocation.work_dir / "findings.json").write_text('{"items":[{"id":"finding_1"}]}')
                (invocation.work_dir / "claim_evidence_map.json").write_text(
                    '{"items":[{"claim_id":"claim_1","evidence_ids":["ev_1"]}]}'
                )
                plot_dir = invocation.work_dir / "plots" / "diagnostics"
                plot_dir.mkdir(parents=True, exist_ok=True)
                (plot_dir / "residuals.png").write_text("png-bytes")
                stats_dir = invocation.work_dir / "stats"
                stats_dir.mkdir(parents=True, exist_ok=True)
                (stats_dir / "summary.json").write_text('{"rows":1}')
            elif role.role in {"method_critic", "visual_critic"}:
                (invocation.work_dir / "critique.md").write_text(f"{role.role} critique")
            elif role.role == "verifier":
                verifier_calls["count"] += 1
                verdict = "revise" if verifier_calls["count"] == 1 else "pass"
                (invocation.work_dir / "verification.json").write_text(
                    f'{{"verdict":"{verdict}","required_repairs":["add_checks"],"reframing_reasons":[]}}'
                )
            elif role.role == "memory_curator":
                (invocation.work_dir / "memory").mkdir(parents=True, exist_ok=True)
                (invocation.work_dir / "memory" / "task_framer.md").write_text(
                    "task framer memory"
                )
                (invocation.work_dir / "memory" / "analysis_planner.md").write_text(
                    "planner memory"
                )
            return InvocationResult(
                status="completed",
                final_message_path=invocation.work_dir / "final.md",
                raw_trace_path=invocation.trace_dir / "trace.jsonl",
            )

    monkeypatch.setitem(orchestration_runner.BACKEND_ADAPTERS, "codex_cli", FakeAdapter)
    monkeypatch.setitem(orchestration_runner.BACKEND_ADAPTERS, "claude_cli", FakeAdapter)
    monkeypatch.setattr(
        orchestration_runner,
        "prepare_run_context",
        lambda **kwargs: RunContext(
            root=kwargs["root"],
            dataset_name=kwargs["dataset_name"],
            results_dir=kwargs["results_dir"],
            work_dir=kwargs["results_dir"] / "work",
            backend=kwargs["backend"],
            env=os.environ.copy(),
            top_trace_path=kwargs["results_dir"] / "trace.jsonl",
            run_state_path=kwargs["results_dir"] / "run_state.json",
            top_session_log_path=kwargs["results_dir"] / "session.log",
            top_session_json_path=kwargs["results_dir"] / "session.json",
            top_final_message_path=kwargs["results_dir"] / "final_message.md",
        ),
    )

    succeeded = run_workflow(
        config=config,
        dataset_name="multimodal",
        dataset_csv=dataset_csv,
        results_dir=results_dir,
        root=root,
    )

    assert succeeded is True
    assert calls == [
        "task_framer",
        "analysis_planner",
        "analysis_executor",
        "method_critic",
        "visual_critic",
        "verifier",
        "memory_curator",
        "analysis_planner",
        "analysis_executor",
        "method_critic",
        "visual_critic",
        "verifier",
        "memory_curator",
    ]
    assert input_snapshots["method_critic"] == input_snapshots["visual_critic"]
    assert "artifacts/analysis/analysis_report.md" in input_snapshots["method_critic"][0]
    assert "artifacts/critiques/method_critic/critique.md" in input_snapshots["verifier"][0]
    assert "artifacts/critiques/visual_critic/critique.md" in input_snapshots["verifier"][0]
    assert "artifacts/verification/verification.json" in input_snapshots["analysis_planner"][1]
    assert "artifacts/critiques/method_critic/critique.md" in input_snapshots["analysis_planner"][1]
    assert "artifacts/critiques/visual_critic/critique.md" in input_snapshots["analysis_planner"][1]
    assert "artifacts/verification/verification.json" in input_snapshots["analysis_executor"][1]
    assert "artifacts/critiques/method_critic/critique.md" in input_snapshots["analysis_executor"][1]
    assert "artifacts/critiques/visual_critic/critique.md" in input_snapshots["analysis_executor"][1]
    assert "artifacts/verification/verification.json" in input_snapshots["memory_curator"][0]
    assert (results_dir / "artifacts" / "memory" / "task_framer.md").exists()
    assert (results_dir / "artifacts" / "memory" / "analysis_planner.md").exists()


def test_verifier_reframe_runs_task_framer_with_verification_and_critiques(
    tmp_path: Path, monkeypatch
):
    root = tmp_path / "repo"
    root.mkdir()
    dataset_csv = root / "dataset.csv"
    dataset_csv.write_text("x,y\n1,2\n")
    results_dir = root / "results" / "runs" / "codex-multiagent-v1" / "multimodal"
    calls: list[str] = []
    input_snapshots: dict[str, list[list[str]]] = {}
    verifier_calls = {"count": 0}
    config = {
        "name": "codex-multiagent-v1",
        "description": "External orchestrator runtime",
        "roles": {
            "task_framer": {"backend": "claude_cli", "prompt": "prompts/active/task-framer.md"},
            "analysis_planner": {
                "backend": "claude_cli",
                "prompt": "prompts/active/analysis-planner.md",
            },
            "analysis_executor": {
                "backend": "codex_cli",
                "prompt": "prompts/active/analysis-executor.md",
            },
            "method_critic": {"backend": "claude_cli", "prompt": "prompts/active/method-critic.md"},
            "visual_critic": {"backend": "claude_cli", "prompt": "prompts/active/visual-critic.md"},
            "verifier": {"backend": "claude_cli", "prompt": "prompts/active/verifier.md"},
            "memory_curator": {"backend": "claude_cli", "prompt": "prompts/active/memory-curator.md"},
        },
        "runtime": {"max_revision_rounds": 0, "max_reframes": 1, "memory_curator": True},
    }

    class FakeAdapter:
        def __init__(self, _root: Path):
            self.root = _root

        def prepare_run(self, context):
            del context

        def invoke(self, role, context, invocation, prompt):
            del context, prompt
            calls.append(role.role)
            input_snapshots.setdefault(role.role, []).append(
                sorted(
                    str(path.relative_to(invocation.input_dir))
                    for path in invocation.input_dir.rglob("*")
                    if path.is_file()
                )
            )
            if role.role == "task_framer":
                (invocation.work_dir / "framing.json").write_text('{"primary_frame":"regression"}')
            elif role.role == "analysis_planner":
                (invocation.work_dir / "analysis_plan.md").write_text("# Plan\n")
                (invocation.work_dir / "hypotheses.json").write_text('{"items":[{"id":"hyp_1"}]}')
                (invocation.work_dir / "experiment_plan.json").write_text(
                    '{"items":[{"id":"exp_1"}]}'
                )
            elif role.role == "analysis_executor":
                (invocation.work_dir / "analysis_report.md").write_text("# Analysis\n")
                (invocation.work_dir / "findings.json").write_text('{"items":[{"id":"finding_1"}]}')
                (invocation.work_dir / "claim_evidence_map.json").write_text(
                    '{"items":[{"claim_id":"claim_1","evidence_ids":["ev_1"]}]}'
                )
                plot_dir = invocation.work_dir / "plots" / "diagnostics"
                plot_dir.mkdir(parents=True, exist_ok=True)
                (plot_dir / "residuals.png").write_text("png-bytes")
                stats_dir = invocation.work_dir / "stats"
                stats_dir.mkdir(parents=True, exist_ok=True)
                (stats_dir / "summary.json").write_text('{"rows":1}')
            elif role.role in {"method_critic", "visual_critic"}:
                (invocation.work_dir / "critique.md").write_text(f"{role.role} critique")
            elif role.role == "verifier":
                verifier_calls["count"] += 1
                verdict = "reframe" if verifier_calls["count"] == 1 else "pass"
                (invocation.work_dir / "verification.json").write_text(
                    f'{{"verdict":"{verdict}","required_repairs":[],"reframing_reasons":["change framing"]}}'
                )
            elif role.role == "memory_curator":
                (invocation.work_dir / "memory").mkdir(parents=True, exist_ok=True)
                (invocation.work_dir / "memory" / "task_framer.md").write_text(
                    "task framer memory"
                )
                (invocation.work_dir / "memory" / "analysis_planner.md").write_text(
                    "planner memory"
                )
            return InvocationResult(
                status="completed",
                final_message_path=invocation.work_dir / "final.md",
                raw_trace_path=invocation.trace_dir / "trace.jsonl",
            )

    monkeypatch.setitem(orchestration_runner.BACKEND_ADAPTERS, "codex_cli", FakeAdapter)
    monkeypatch.setitem(orchestration_runner.BACKEND_ADAPTERS, "claude_cli", FakeAdapter)
    monkeypatch.setattr(
        orchestration_runner,
        "prepare_run_context",
        lambda **kwargs: RunContext(
            root=kwargs["root"],
            dataset_name=kwargs["dataset_name"],
            results_dir=kwargs["results_dir"],
            work_dir=kwargs["results_dir"] / "work",
            backend=kwargs["backend"],
            env=os.environ.copy(),
            top_trace_path=kwargs["results_dir"] / "trace.jsonl",
            run_state_path=kwargs["results_dir"] / "run_state.json",
            top_session_log_path=kwargs["results_dir"] / "session.log",
            top_session_json_path=kwargs["results_dir"] / "session.json",
            top_final_message_path=kwargs["results_dir"] / "final_message.md",
        ),
    )

    succeeded = run_workflow(
        config=config,
        dataset_name="multimodal",
        dataset_csv=dataset_csv,
        results_dir=results_dir,
        root=root,
    )

    assert succeeded is True
    assert calls == [
        "task_framer",
        "analysis_planner",
        "analysis_executor",
        "method_critic",
        "visual_critic",
        "verifier",
        "memory_curator",
        "task_framer",
        "analysis_planner",
        "analysis_executor",
        "method_critic",
        "visual_critic",
        "verifier",
        "memory_curator",
    ]
    assert "artifacts/critiques/method_critic/critique.md" in input_snapshots["task_framer"][1]
    assert "artifacts/critiques/visual_critic/critique.md" in input_snapshots["task_framer"][1]
    assert "artifacts/verification/verification.json" in input_snapshots["task_framer"][1]


def test_memory_curator_reads_only_published_artifacts(tmp_path: Path):
    run_dir = tmp_path / "run"
    (run_dir / "artifacts" / "verification" / "verification.json").parent.mkdir(
        parents=True, exist_ok=True
    )
    (run_dir / "artifacts" / "verification" / "verification.json").write_text(
        '{"verdict":"revise"}'
    )
    (run_dir / "artifacts" / "analysis" / "analysis_report.md").parent.mkdir(
        parents=True, exist_ok=True
    )
    (run_dir / "artifacts" / "analysis" / "analysis_report.md").write_text("# Analysis\n")
    private_log = run_dir / "invocations" / "analysis_executor-0001" / "logs" / "session.log"
    private_log.parent.mkdir(parents=True, exist_ok=True)
    private_log.write_text("private detail")

    memory_inputs = collect_memory_inputs(run_dir)

    assert private_log not in memory_inputs
    assert run_dir / "artifacts" / "verification" / "verification.json" in memory_inputs
    assert run_dir / "artifacts" / "analysis" / "analysis_report.md" in memory_inputs
