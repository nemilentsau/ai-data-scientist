"""Claude CLI adapter."""

from __future__ import annotations

import json
import shutil
import subprocess
import uuid

from ai_data_scientist.orchestration.adapters.base import BackendAdapter
from ai_data_scientist.orchestration.models import (
    BackendCapabilities,
    RunContext,
    SessionHandle,
    WorkflowExecutionError,
    WorkflowStep,
)
from ai_data_scientist.orchestration.prompts import render_step_prompt


class ClaudeCliAdapter(BackendAdapter):
    """Claude CLI workflow adapter."""

    backend_name = "claude_cli"

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_resume=True, supports_image_attachments=False)

    def prepare_context(self, context: RunContext) -> None:
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

    def start_step(self, step: WorkflowStep, context: RunContext) -> SessionHandle:
        session_id = str(uuid.uuid4())
        return self._run_step(step=step, context=context, session_id=session_id, resume=False)

    def continue_step(
        self,
        step: WorkflowStep,
        context: RunContext,
        session: SessionHandle,
    ) -> SessionHandle:
        return self._run_step(
            step=step,
            context=context,
            session_id=session.session_id,
            resume=True,
        )

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

    def _run_step(
        self,
        *,
        step: WorkflowStep,
        context: RunContext,
        session_id: str,
        resume: bool,
    ) -> SessionHandle:
        step_dir = context.step_dir(step.id)
        step_trace = step_dir / "trace.jsonl"
        step_log = step_dir / "session.log"
        step_json = step_dir / "session.json"
        step_final = step_dir / "final_message.md"
        image_paths = context.matched_inputs.get(step.id, [])
        prompt = render_step_prompt(
            root=self.root,
            step=step,
            image_paths=image_paths,
            attachment_mode="claude",
        )

        env = context.env.copy()
        env["TRACE_FILE"] = str(step_trace)
        command = (
            self._build_start_command(step, session_id, prompt)
            if not resume
            else self._build_continue_command(step, session_id, prompt)
        )

        with step_json.open("w") as stdout_handle, step_log.open("w") as stderr_handle:
            completed = subprocess.run(
                command,
                cwd=context.work_dir,
                env=env,
                check=False,
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
            )

        if completed.returncode != 0:
            raise WorkflowExecutionError(
                f"Claude step '{step.id}' failed with exit code {completed.returncode}."
            )

        return SessionHandle(
            backend=self.backend_name,
            session_id=session_id,
            step_id=step.id,
            raw_trace_path=step_trace,
            final_message_path=step_final,
            session_log_path=step_log,
            session_output_path=step_json,
        )

    def _build_common_command(self, step: WorkflowStep, prompt: str) -> list[str]:
        command = [
            "claude",
            "-p",
            prompt,
            "--output-format",
            "json",
            "--allowedTools",
            ",".join(step.tools),
            "--max-turns",
            str(step.max_turns),
        ]
        if step.model:
            command.extend(["--model", step.model])
        return command

    def _build_start_command(self, step: WorkflowStep, session_id: str, prompt: str) -> list[str]:
        command = self._build_common_command(step, prompt)
        command.extend(["--session-id", session_id])
        return command

    def _build_continue_command(
        self,
        step: WorkflowStep,
        session_id: str,
        prompt: str,
    ) -> list[str]:
        command = self._build_common_command(step, prompt)
        command.extend(["--resume", session_id])
        return command

