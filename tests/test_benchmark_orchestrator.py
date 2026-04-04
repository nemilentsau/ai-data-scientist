"""Tests for workflow normalization and backend orchestration."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import benchmark_orchestrator as orchestrator


def _write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_legacy_codex_config_becomes_single_analyst_workflow():
    config = {
        "name": "solo-codex",
        "description": "Single Codex agent",
        "team": [{"role": "codex", "prompt": "prompts/analyst-generic.md", "max_turns": 30}],
        "harness": "harness/run_codex.sh",
    }

    spec = orchestrator.normalize_workflow_config(config)

    assert spec.backend == "codex_cli"
    assert len(spec.steps) == 1
    assert spec.steps[0].id == "analyst"
    assert spec.steps[0].role == "analyst"
    assert spec.steps[0].prompt == "prompts/analyst-generic.md"
    assert spec.steps[0].image_inputs == ()
    assert spec.steps[0].required is True


def test_legacy_claude_config_becomes_single_analyst_workflow():
    config = {
        "name": "solo-baseline",
        "description": "Single Claude agent",
        "team": [
            {
                "role": "claude",
                "model": "claude-opus-4-6",
                "prompt": "prompts/analyst-generic.md",
                "max_turns": 30,
                "tools": ["Bash", "Read"],
            }
        ],
        "harness": "harness/run_claude.sh",
    }

    spec = orchestrator.normalize_workflow_config(config)

    assert spec.backend == "claude_cli"
    assert len(spec.steps) == 1
    assert spec.steps[0].tools == ("Bash", "Read")
    assert spec.steps[0].model == "claude-opus-4-6"


def test_workflow_config_preserves_ordered_steps_and_image_requirements():
    config = {
        "name": "codex-v3",
        "backend": "codex_cli",
        "workflow": {
            "steps": [
                {
                    "id": "analyst",
                    "role": "analyst",
                    "prompt": "prompts/analyst-v2.md",
                    "max_turns": 30,
                },
                {
                    "id": "visual_review",
                    "role": "visual_reviewer",
                    "prompt": "prompts/visual-review.md",
                    "image_inputs": ["plots/*.png"],
                    "required": True,
                },
            ]
        },
    }

    spec = orchestrator.normalize_workflow_config(config)

    assert spec.backend == "codex_cli"
    assert [step.id for step in spec.steps] == ["analyst", "visual_review"]
    assert spec.steps[1].image_inputs == ("plots/*.png",)
    assert spec.steps[1].required is True


def test_codex_resume_command_uses_thread_id_instead_of_last(tmp_path: Path, monkeypatch):
    root = tmp_path
    results_dir = tmp_path / "results"
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    context = orchestrator.RunContext(
        root=root,
        dataset_name="multimodal",
        results_dir=results_dir,
        work_dir=work_dir,
        backend="codex_cli",
        env=os.environ.copy(),
        top_trace_path=results_dir / "trace.jsonl",
        run_state_path=results_dir / "run_state.json",
        top_session_log_path=results_dir / "session.log",
    )
    context.step_dir("analyst")
    context.step_dir("visual_review")

    recorded_commands: list[list[str]] = []

    def fake_run(command, **kwargs):
        recorded_commands.append(command)
        stdout_handle = kwargs["stdout"]
        if "resume" in command:
            stdout_handle.write('{"type":"turn.started"}\n')
        else:
            stdout_handle.write('{"type":"thread.started","thread_id":"thread-123"}\n')
        stdout_handle.flush()
        return type("Completed", (), {"returncode": 0})()

    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)

    adapter = orchestrator.CodexCliAdapter(root)
    analyst = orchestrator.WorkflowStep(
        id="analyst",
        role="analyst",
        prompt="Analyze",
    )
    review = orchestrator.WorkflowStep(
        id="visual_review",
        role="visual_reviewer",
        prompt="Review",
        image_inputs=("plots/*.png",),
    )
    plot_path = work_dir / "plots" / "chart.png"
    plot_path.parent.mkdir(exist_ok=True)
    plot_path.write_bytes(b"png")
    context.matched_inputs["analyst"] = []
    context.matched_inputs["visual_review"] = [plot_path]

    first = adapter.start_step(analyst, context)
    second = adapter.continue_step(review, context, first)

    assert first.session_id == "thread-123"
    assert second.session_id == "thread-123"
    assert "resume" in recorded_commands[1]
    assert "thread-123" in recorded_commands[1]
    assert "--last" not in recorded_commands[1]


def test_claude_followup_reuses_generated_session_uuid(tmp_path: Path, monkeypatch):
    root = tmp_path
    _write_file(root / ".claude" / "settings.json", "{}")
    _write_file(root / ".claude" / "hooks" / "trace.sh", "#!/usr/bin/env bash\n")
    results_dir = tmp_path / "results"
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    context = orchestrator.RunContext(
        root=root,
        dataset_name="concept_drift",
        results_dir=results_dir,
        work_dir=work_dir,
        backend="claude_cli",
        env=os.environ.copy(),
        top_trace_path=results_dir / "trace.jsonl",
        run_state_path=results_dir / "run_state.json",
        top_session_json_path=results_dir / "session.json",
    )
    context.step_dir("analyst")
    context.step_dir("visual_review")

    session_uuid = uuid.UUID("11111111-1111-1111-1111-111111111111")
    monkeypatch.setattr(orchestrator.uuid, "uuid4", lambda: session_uuid)

    recorded_commands: list[list[str]] = []

    def fake_run(command, **kwargs):
        recorded_commands.append(command)
        trace_path = Path(kwargs["env"]["TRACE_FILE"])
        trace_path.write_text('{"event":"tool"}\n')
        kwargs["stdout"].write('{"result":"step done"}')
        kwargs["stdout"].flush()
        return type("Completed", (), {"returncode": 0})()

    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)

    adapter = orchestrator.ClaudeCliAdapter(root)
    analyst = orchestrator.WorkflowStep(id="analyst", role="analyst", prompt="Analyze")
    review = orchestrator.WorkflowStep(id="visual_review", role="visual_reviewer", prompt="Review")
    context.matched_inputs["analyst"] = []
    context.matched_inputs["visual_review"] = []

    first = adapter.start_step(analyst, context)
    adapter.collect_step_outputs(analyst, context, first)
    second = adapter.continue_step(review, context, first)

    assert first.session_id == str(session_uuid)
    assert second.session_id == str(session_uuid)
    assert "--session-id" in recorded_commands[0]
    assert str(session_uuid) in recorded_commands[0]
    assert "--resume" in recorded_commands[1]
    assert str(session_uuid) in recorded_commands[1]
    assert first.final_message_path.read_text() == "step done"


class _FakeClaudeWorkflowAdapter(orchestrator.BackendAdapter):
    backend_name = "claude_cli"
    saw_second_step_workspace = False

    def capabilities(self) -> orchestrator.BackendCapabilities:
        return orchestrator.BackendCapabilities(
            supports_resume=True,
            supports_image_attachments=False,
        )

    def start_step(
        self,
        step: orchestrator.WorkflowStep,
        context: orchestrator.RunContext,
    ) -> orchestrator.SessionHandle:
        return self._write_step(step, context, session_id="fake-session")

    def continue_step(
        self,
        step: orchestrator.WorkflowStep,
        context: orchestrator.RunContext,
        session: orchestrator.SessionHandle,
    ) -> orchestrator.SessionHandle:
        assert session.session_id == "fake-session"
        self.__class__.saw_second_step_workspace = (
            (context.work_dir / "analysis_report.md").exists()
            and (context.work_dir / "plots" / "chart.png").exists()
        )
        return self._write_step(step, context, session_id=session.session_id)

    def collect_step_outputs(
        self,
        step: orchestrator.WorkflowStep,
        context: orchestrator.RunContext,
        session: orchestrator.SessionHandle,
    ) -> None:
        del step, context, session

    def _write_step(
        self,
        step: orchestrator.WorkflowStep,
        context: orchestrator.RunContext,
        *,
        session_id: str,
    ) -> orchestrator.SessionHandle:
        step_dir = context.step_dir(step.id)
        trace_path = step_dir / "trace.jsonl"
        trace_path.write_text(f'{{"event":"{step.id}"}}\n')
        final_message = step_dir / "final_message.md"
        final_message.write_text(f"{step.id} done")
        session_json = step_dir / "session.json"
        session_json.write_text(f'{{"result":"{step.id} done"}}')
        session_log = step_dir / "session.log"
        session_log.write_text(f"{step.id} log")

        if step.id == "analyst":
            (context.work_dir / "analysis_report.md").write_text("# Analysis\n")
            plot_path = context.work_dir / "plots" / "chart.png"
            plot_path.parent.mkdir(exist_ok=True)
            plot_path.write_bytes(b"png")
            (context.work_dir / "analysis.py").write_text("print('analysis')\n")
        elif step.id == "visual_review":
            report_path = context.work_dir / "analysis_report.md"
            report_path.write_text(report_path.read_text() + "\nReviewed visually.\n")

        return orchestrator.SessionHandle(
            backend=self.backend_name,
            session_id=session_id,
            step_id=step.id,
            raw_trace_path=trace_path,
            final_message_path=final_message,
            session_log_path=session_log,
            session_output_path=session_json,
        )


def _make_workflow_root(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    dataset_csv = root / "datasets" / "generated" / "dataset.csv"
    _write_file(dataset_csv, "x,y\n1,2\n")
    _write_file(root / ".claude" / "settings.json", "{}")
    _write_file(root / ".claude" / "hooks" / "trace.sh", "#!/usr/bin/env bash\n")
    _write_file(root / "prompts" / "analyst.md", "Analyze the dataset.")
    _write_file(root / "prompts" / "review.md", "Review the generated plots.")
    return root, dataset_csv


def _fake_shared_venv(root: Path) -> Path:
    venv_dir = root / orchestrator.BENCHMARK_VENV_DIRNAME
    (venv_dir / "bin").mkdir(parents=True, exist_ok=True)
    return venv_dir


def test_step_traces_append_in_order_and_outputs_publish_after_final_step(
    tmp_path: Path,
    monkeypatch,
):
    root, dataset_csv = _make_workflow_root(tmp_path)
    results_dir = root / "results" / "runs" / "claude-v3" / "multimodal"
    config = {
        "name": "claude-v3",
        "backend": "claude_cli",
        "workflow": {
            "steps": [
                {"id": "analyst", "role": "analyst", "prompt": "prompts/analyst.md"},
                {
                    "id": "visual_review",
                    "role": "visual_reviewer",
                    "prompt": "prompts/review.md",
                    "image_inputs": ["plots/*.png"],
                },
            ]
        },
    }

    monkeypatch.setattr(orchestrator, "ensure_shared_benchmark_venv", _fake_shared_venv)
    monkeypatch.setitem(orchestrator.BACKEND_ADAPTERS, "claude_cli", _FakeClaudeWorkflowAdapter)
    _FakeClaudeWorkflowAdapter.saw_second_step_workspace = False

    succeeded = orchestrator.run_workflow(
        config=config,
        dataset_name="multimodal",
        dataset_csv=dataset_csv,
        results_dir=results_dir,
        root=root,
    )

    assert succeeded is True
    assert _FakeClaudeWorkflowAdapter.saw_second_step_workspace is True
    assert (results_dir / "analysis_report.md").read_text().endswith("Reviewed visually.\n")
    assert (results_dir / "plots" / "chart.png").exists()
    assert (results_dir / "analysis.py").exists()
    assert (results_dir / "final_message.md").read_text() == "visual_review done"
    assert (results_dir / "session.json").read_text() == '{"result":"visual_review done"}'
    assert (results_dir / "trace.jsonl").read_text() == (
        '{"event":"analyst"}\n{"event":"visual_review"}\n'
    )

    run_state = (results_dir / "run_state.json").read_text()
    assert '"completed_steps": [\n    "analyst",\n    "visual_review"\n  ]' in run_state
    assert '"cleaned_up": true' in run_state


def test_required_visual_review_failure_marks_run_failed_when_no_images_exist(
    tmp_path: Path,
    monkeypatch,
):
    class NoPlotAdapter(_FakeClaudeWorkflowAdapter):
        def _write_step(self, step, context, *, session_id):  # type: ignore[override]
            handle = super()._write_step(step, context, session_id=session_id)
            if step.id == "analyst":
                plot_path = context.work_dir / "plots" / "chart.png"
                if plot_path.exists():
                    plot_path.unlink()
            return handle

    root, dataset_csv = _make_workflow_root(tmp_path)
    results_dir = root / "results" / "runs" / "claude-v3" / "concept_drift"
    config = {
        "name": "claude-v3",
        "backend": "claude_cli",
        "workflow": {
            "steps": [
                {"id": "analyst", "role": "analyst", "prompt": "prompts/analyst.md"},
                {
                    "id": "visual_review",
                    "role": "visual_reviewer",
                    "prompt": "prompts/review.md",
                    "image_inputs": ["plots/*.png"],
                    "required": True,
                },
            ]
        },
    }

    monkeypatch.setattr(orchestrator, "ensure_shared_benchmark_venv", _fake_shared_venv)
    monkeypatch.setitem(orchestrator.BACKEND_ADAPTERS, "claude_cli", NoPlotAdapter)

    succeeded = orchestrator.run_workflow(
        config=config,
        dataset_name="concept_drift",
        dataset_csv=dataset_csv,
        results_dir=results_dir,
        root=root,
    )

    assert succeeded is False
    run_state = (results_dir / "run_state.json").read_text()
    assert '"status": "failed"' in run_state
    assert '"completed_steps": [\n    "analyst"\n  ]' in run_state
    assert not (results_dir / "analysis_report.md").exists()


def test_optional_visual_review_skips_cleanly_when_no_images_exist(
    tmp_path: Path,
    monkeypatch,
):
    class NoPlotAdapter(_FakeClaudeWorkflowAdapter):
        def _write_step(self, step, context, *, session_id):  # type: ignore[override]
            handle = super()._write_step(step, context, session_id=session_id)
            if step.id == "analyst":
                plot_path = context.work_dir / "plots" / "chart.png"
                if plot_path.exists():
                    plot_path.unlink()
            return handle

    root, dataset_csv = _make_workflow_root(tmp_path)
    results_dir = root / "results" / "runs" / "claude-v3" / "pure_noise"
    config = {
        "name": "claude-v3",
        "backend": "claude_cli",
        "workflow": {
            "steps": [
                {"id": "analyst", "role": "analyst", "prompt": "prompts/analyst.md"},
                {
                    "id": "visual_review",
                    "role": "visual_reviewer",
                    "prompt": "prompts/review.md",
                    "image_inputs": ["plots/*.png"],
                    "required": False,
                },
            ]
        },
    }

    monkeypatch.setattr(orchestrator, "ensure_shared_benchmark_venv", _fake_shared_venv)
    monkeypatch.setitem(orchestrator.BACKEND_ADAPTERS, "claude_cli", NoPlotAdapter)

    succeeded = orchestrator.run_workflow(
        config=config,
        dataset_name="pure_noise",
        dataset_csv=dataset_csv,
        results_dir=results_dir,
        root=root,
    )

    assert succeeded is True
    run_state = (results_dir / "run_state.json").read_text()
    assert '"status": "completed"' in run_state
    assert '"skipped_steps": [\n    "visual_review"\n  ]' in run_state
    assert (results_dir / "analysis_report.md").exists()
    assert (results_dir / "trace.jsonl").read_text() == '{"event":"analyst"}\n'
