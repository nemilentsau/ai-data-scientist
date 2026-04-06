"""Claude CLI adapter."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from ai_data_scientist.orchestration.adapters.base import BackendAdapter
from ai_data_scientist.orchestration.models import (
    BackendCapabilities,
    InvocationContext,
    InvocationResult,
    RoleSpec,
    RunContext,
    SessionHandle,
    WorkflowExecutionError,
    WorkflowStep,
)
from ai_data_scientist.orchestration.prompts import render_role_prompt
from ai_data_scientist.orchestration.workspace import create_invocation_context


class ClaudeCliAdapter(BackendAdapter):
    """Claude CLI workflow adapter."""

    backend_name = "claude_cli"

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_resume=False, supports_image_attachments=False)

    def prepare_run(self, context: RunContext) -> None:
        claude_dir = context.work_dir / ".claude"
        hooks_dir = claude_dir / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)

        settings_path = context.root / ".claude" / "settings.json"
        hook_path = context.root / ".claude" / "hooks" / "trace.sh"
        if settings_path.exists():
            shutil.copy2(settings_path, claude_dir / "settings.json")
        if hook_path.exists():
            shutil.copy2(hook_path, hooks_dir / "trace.sh")

        context.top_session_json_path = context.results_dir / "session.json"

    def invoke(
        self,
        role: RoleSpec,
        context: RunContext,
        invocation: InvocationContext,
        prompt: str,
    ) -> InvocationResult:
        result = self._run_invocation(role=role, context=context, invocation=invocation, prompt=prompt)
        return InvocationResult(
            status="completed",
            final_message_path=result.final_message_path,
            raw_trace_path=result.raw_trace_path,
        )

    def start_step(self, step: WorkflowStep, context: RunContext) -> SessionHandle:
        return self._run_legacy_step(step, context)

    def continue_step(
        self,
        step: WorkflowStep,
        context: RunContext,
        session: SessionHandle,
    ) -> SessionHandle:
        del session
        return self._run_legacy_step(step, context)

    def collect_step_outputs(
        self,
        step: WorkflowStep,
        context: RunContext,
        session: SessionHandle,
    ) -> None:
        del step, context
        if session.session_output_path is None or not session.session_output_path.exists():
            return

        try:
            payload = json.loads(session.session_output_path.read_text())
        except json.JSONDecodeError:
            return

        final_text = str(payload.get("result") or "").strip()
        if final_text:
            session.final_message_path.write_text(final_text)

    def _run_legacy_step(self, step: WorkflowStep, context: RunContext) -> SessionHandle:
        role = RoleSpec(
            role=step.role,
            backend=self.backend_name,
            prompt=step.prompt,
            model=step.model,
            tools=step.tools,
            max_turns=step.max_turns,
        )
        invocation = create_invocation_context(
            run_dir=context.results_dir,
            role=role,
            artifact_inputs=[],
        )
        artifact_inputs = self._materialize_invocation_inputs(
            invocation=invocation,
            sources=context.matched_inputs.get(step.id, []),
            source_root=context.work_dir,
        )
        prompt = render_role_prompt(
            root=self.root,
            role=role,
            artifact_inputs=artifact_inputs,
            role_memory=None,
        )
        result = self.invoke(role, context, invocation, prompt)
        return SessionHandle(
            backend=self.backend_name,
            session_id=invocation.invocation_id,
            step_id=step.id,
            raw_trace_path=result.raw_trace_path or invocation.trace_dir / "trace.jsonl",
            final_message_path=result.final_message_path or invocation.output_dir / "final_message.md",
            session_log_path=invocation.logs_dir / "session.log",
            session_output_path=invocation.output_dir / "session.json",
        )

    def _run_invocation(
        self,
        *,
        role: RoleSpec,
        context: RunContext,
        invocation: InvocationContext,
        prompt: str,
    ) -> InvocationResult:
        step_trace = invocation.trace_dir / "trace.jsonl"
        step_log = invocation.logs_dir / "session.log"
        step_json = invocation.output_dir / "session.json"
        step_final = invocation.output_dir / "final_message.md"
        self._ensure_invocation_claude_config(context=context, invocation=invocation)
        env = context.env.copy()
        env["TRACE_FILE"] = str(step_trace)
        command = self._build_fresh_command(role, prompt)

        with step_json.open("w") as stdout_handle, step_log.open("w") as stderr_handle:
            completed = subprocess.run(
                command,
                cwd=invocation.work_dir,
                env=env,
                check=False,
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
            )

        if completed.returncode != 0:
            raise WorkflowExecutionError(
                f"Claude invocation '{invocation.invocation_id}' failed with exit code {completed.returncode}."
            )

        if step_json.exists():
            try:
                payload = json.loads(step_json.read_text())
            except json.JSONDecodeError:
                payload = {}
            final_text = str(payload.get("result") or "").strip()
            if final_text:
                step_final.write_text(final_text)

        if not step_final.exists():
            step_final.write_text("")

        return InvocationResult(
            status="completed",
            final_message_path=step_final,
            raw_trace_path=step_trace,
        )

    def _build_fresh_command(self, role: RoleSpec, prompt: str) -> list[str]:
        command = [
            "claude",
            "-p",
            prompt,
            "--output-format",
            "json",
            "--allowedTools",
            ",".join(role.tools),
            "--max-turns",
            str(role.max_turns),
        ]
        if role.model:
            command.extend(["--model", role.model])
        return command

    def _materialize_invocation_inputs(
        self,
        *,
        invocation: InvocationContext,
        sources: list[Path],
        source_root: Path,
    ) -> list[Path]:
        copied_inputs: list[Path] = []
        for source_path in sources:
            try:
                relative_path = source_path.relative_to(source_root)
            except ValueError:
                relative_path = Path(source_path.name)
            destination = invocation.input_dir / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination)
            copied_inputs.append(destination)
        return copied_inputs

    def _ensure_invocation_claude_config(
        self,
        *,
        context: RunContext,
        invocation: InvocationContext,
    ) -> None:
        source = context.work_dir / ".claude"
        destination = invocation.work_dir / ".claude"
        if not source.exists():
            return
        if destination.exists():
            return
        shutil.copytree(source, destination, dirs_exist_ok=True)
