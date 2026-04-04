"""Codex CLI adapter."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ai_data_scientist.orchestration.adapters.base import BackendAdapter
from ai_data_scientist.orchestration.models import (
    BackendCapabilities,
    RunContext,
    SessionHandle,
    WorkflowExecutionError,
    WorkflowStep,
)
from ai_data_scientist.orchestration.prompts import render_step_prompt
from ai_data_scientist.orchestration.trace import extract_codex_thread_id


class CodexCliAdapter(BackendAdapter):
    """Codex CLI workflow adapter."""

    backend_name = "codex_cli"

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_resume=True, supports_image_attachments=True)

    def prepare_context(self, context: RunContext) -> None:
        codex_home = context.work_dir / ".codex-home"
        codex_home.mkdir(parents=True, exist_ok=True)
        (codex_home / "shell_snapshots").mkdir(exist_ok=True)
        source_home = Path.home() / ".codex"
        for filename in ("auth.json", "version.json"):
            source = source_home / filename
            if source.exists():
                shutil.copy2(source, codex_home / filename)

        context.env["CODEX_HOME"] = str(codex_home)
        context.top_session_log_path = self._write_top_session_header(context)

    def start_step(self, step: WorkflowStep, context: RunContext) -> SessionHandle:
        image_paths = context.matched_inputs.get(step.id, [])
        return self._run_step(step=step, context=context, session=None, image_paths=image_paths)

    def continue_step(
        self,
        step: WorkflowStep,
        context: RunContext,
        session: SessionHandle,
    ) -> SessionHandle:
        image_paths = context.matched_inputs.get(step.id, [])
        return self._run_step(step=step, context=context, session=session, image_paths=image_paths)

    def collect_step_outputs(
        self,
        step: WorkflowStep,
        context: RunContext,
        session: SessionHandle,
    ) -> None:
        del step, context, session

    def _run_step(
        self,
        *,
        step: WorkflowStep,
        context: RunContext,
        session: SessionHandle | None,
        image_paths: list[Path],
    ) -> SessionHandle:
        step_dir = context.step_dir(step.id)
        step_trace = step_dir / "trace.jsonl"
        step_log = step_dir / "session.log"
        step_final = step_dir / "final_message.md"
        prompt = render_step_prompt(
            root=self.root,
            step=step,
            image_paths=image_paths,
            attachment_mode="codex",
        )

        command = (
            self._build_start_command(step, context, prompt, step_final, image_paths)
            if session is None
            else self._build_continue_command(
                step,
                context,
                prompt,
                step_final,
                image_paths,
                session.session_id,
            )
        )

        with step_trace.open("w") as stdout_handle, step_log.open("w") as stderr_handle:
            completed = subprocess.run(
                command,
                cwd=context.work_dir,
                env=context.env,
                check=False,
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
            )

        if completed.returncode != 0:
            raise WorkflowExecutionError(
                f"Codex step '{step.id}' failed with exit code {completed.returncode}."
            )

        session_id = (
            session.session_id if session is not None else extract_codex_thread_id(step_trace)
        )
        return SessionHandle(
            backend=self.backend_name,
            session_id=session_id,
            step_id=step.id,
            raw_trace_path=step_trace,
            final_message_path=step_final,
            session_log_path=step_log,
        )

    def _build_start_command(
        self,
        step: WorkflowStep,
        context: RunContext,
        prompt: str,
        final_message_path: Path,
        image_paths: list[Path],
    ) -> list[str]:
        command = ["codex", "-a", "never"]
        if step.model:
            command.extend(["-m", step.model])
        for path in image_paths:
            command.extend(["-i", str(path.resolve())])
        command.extend(
            [
                "--disable",
                "plugins",
                "--disable",
                "shell_snapshot",
                "exec",
                "-s",
                "workspace-write",
                "--json",
                "--skip-git-repo-check",
                "-C",
                str(context.work_dir),
                "-o",
                str(final_message_path),
                prompt,
            ]
        )
        return command

    def _build_continue_command(
        self,
        step: WorkflowStep,
        context: RunContext,
        prompt: str,
        final_message_path: Path,
        image_paths: list[Path],
        session_id: str,
    ) -> list[str]:
        command = [
            "codex",
            "-a",
            "never",
            "-s",
            "workspace-write",
            "-C",
            str(context.work_dir),
            "--disable",
            "plugins",
            "--disable",
            "shell_snapshot",
            "exec",
            "resume",
        ]
        if step.model:
            command.extend(["-m", step.model])
        command.extend(["--json", "--skip-git-repo-check", "-o", str(final_message_path)])
        for path in image_paths:
            command.extend(["-i", str(path.resolve())])
        command.extend([session_id, prompt])
        return command

    def _write_top_session_header(self, context: RunContext) -> Path:
        session_log = context.results_dir / "session.log"
        header_lines = [
            f"dataset={context.dataset_name}",
            f"project_root={context.root}",
            f"work_dir={context.work_dir}",
            "max_turns=workflow",
            "tools=workflow-managed",
        ]
        version = subprocess.run(
            ["codex", "--version"],
            cwd=context.root,
            check=False,
            capture_output=True,
            text=True,
        )
        if version.stdout.strip():
            header_lines.append(version.stdout.strip())
        session_log.write_text("\n".join(header_lines) + "\n\n")
        return session_log
