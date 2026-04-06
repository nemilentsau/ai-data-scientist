"""Codex CLI adapter."""

from __future__ import annotations

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


class CodexCliAdapter(BackendAdapter):
    """Codex CLI workflow adapter."""

    backend_name = "codex_cli"

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_resume=False, supports_image_attachments=True)

    def prepare_run(self, context: RunContext) -> None:
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
        del step, context, session

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
            invocation_cwd=invocation.work_dir,
        )
        result = self.invoke(role, context, invocation, prompt)
        return SessionHandle(
            backend=self.backend_name,
            session_id=invocation.invocation_id,
            step_id=step.id,
            raw_trace_path=result.raw_trace_path or invocation.trace_dir / "trace.jsonl",
            final_message_path=result.final_message_path or invocation.output_dir / "final_message.md",
            session_log_path=invocation.logs_dir / "session.log",
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
        step_final = invocation.output_dir / "final_message.md"
        image_paths = self._invocation_image_paths(invocation)
        command = (
            self._build_fresh_command(role, invocation, prompt, step_final, image_paths)
        )

        with step_trace.open("w") as stdout_handle, step_log.open("w") as stderr_handle:
            completed = subprocess.run(
                command,
                cwd=invocation.work_dir,
                env=context.env,
                check=False,
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=True,
            )

        if completed.returncode != 0:
            raise WorkflowExecutionError(
                f"Codex invocation '{invocation.invocation_id}' failed with exit code {completed.returncode}."
            )

        if not step_final.exists():
            step_final.write_text("")

        return InvocationResult(
            status="completed",
            final_message_path=step_final,
            raw_trace_path=step_trace,
        )

    def _build_fresh_command(
        self,
        role: RoleSpec,
        invocation: InvocationContext,
        prompt: str,
        final_message_path: Path,
        image_paths: list[Path],
    ) -> list[str]:
        command = ["codex", "-a", "never"]
        if role.model:
            command.extend(["-m", role.model])
        for path in image_paths:
            command.extend(["-i", str(path)])
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
                str(invocation.work_dir),
                "-o",
                str(final_message_path),
                prompt,
            ]
        )
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

    def _invocation_image_paths(self, invocation: InvocationContext) -> list[Path]:
        image_suffixes = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff"}
        return [
            path
            for path in sorted(invocation.input_dir.rglob("*"))
            if path.is_file() and path.suffix.lower() in image_suffixes
        ]

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
