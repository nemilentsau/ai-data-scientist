"""Unified benchmark workflow orchestration across CLI backends."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_PROMPT_PATH = "harness/prompt_template.txt"
BENCHMARK_VENV_DIRNAME = ".benchmark-venv"
SHARED_PACKAGES = (
    "numpy",
    "pandas",
    "scipy",
    "sklearn",
    "matplotlib",
    "seaborn",
    "statsmodels",
    "lifelines",
)
DEFAULT_TOOLS = ("Bash", "Read", "Write", "Edit", "Glob", "Grep")
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


@dataclass(frozen=True)
class WorkflowStep:
    """One logical workflow step executed in the shared workspace."""

    id: str
    role: str
    prompt: str
    model: str = ""
    tools: tuple[str, ...] = DEFAULT_TOOLS
    max_turns: int = 30
    image_inputs: tuple[str, ...] = ()
    required: bool = True


@dataclass(frozen=True)
class WorkflowSpec:
    """Normalized workflow configuration."""

    name: str
    description: str
    backend: str
    steps: tuple[WorkflowStep, ...]


@dataclass(frozen=True)
class BackendCapabilities:
    """Backend behavior toggles used by the orchestrator."""

    supports_resume: bool
    supports_image_attachments: bool


@dataclass
class SessionHandle:
    """Backend session metadata for the current workflow thread."""

    backend: str
    session_id: str
    step_id: str
    raw_trace_path: Path
    final_message_path: Path
    session_log_path: Path | None = None
    session_output_path: Path | None = None


@dataclass
class RunContext:
    """Mutable run state shared across workflow steps."""

    root: Path
    dataset_name: str
    results_dir: Path
    work_dir: Path
    backend: str
    env: dict[str, str]
    top_trace_path: Path
    run_state_path: Path
    top_session_log_path: Path | None = None
    top_session_json_path: Path | None = None
    top_final_message_path: Path | None = None
    matched_inputs: dict[str, list[Path]] = field(default_factory=dict)
    step_sessions: dict[str, SessionHandle] = field(default_factory=dict)
    completed_steps: list[str] = field(default_factory=list)
    skipped_steps: list[str] = field(default_factory=list)
    status: str = "in_progress"
    error: str | None = None
    cleaned_up: bool = False

    def step_dir(self, step_id: str) -> Path:
        path = self.results_dir / "steps" / step_id
        path.mkdir(parents=True, exist_ok=True)
        return path


class WorkflowExecutionError(RuntimeError):
    """Raised when a workflow cannot continue."""


class BackendAdapter:
    """Base backend adapter."""

    backend_name: str = ""

    def __init__(self, root: Path):
        self.root = root

    def capabilities(self) -> BackendCapabilities:
        raise NotImplementedError

    def start_step(self, step: WorkflowStep, context: RunContext) -> SessionHandle:
        raise NotImplementedError

    def continue_step(
        self,
        step: WorkflowStep,
        context: RunContext,
        session: SessionHandle,
    ) -> SessionHandle:
        raise NotImplementedError

    def collect_step_outputs(
        self,
        step: WorkflowStep,
        context: RunContext,
        session: SessionHandle,
    ) -> None:
        raise NotImplementedError


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
        step_id = str(raw_step.get("id") or f"step_{index}")
        step = WorkflowStep(
            id=step_id,
            role=str(raw_step.get("role") or step_id),
            prompt=_normalize_prompt_ref(raw_step.get("prompt")),
            model=str(raw_step.get("model", "") or ""),
            tools=_normalize_tools(raw_step.get("tools")),
            max_turns=int(raw_step.get("max_turns", 30) or 30),
            image_inputs=tuple(str(item) for item in raw_step.get("image_inputs", []) or []),
            required=bool(raw_step.get("required", True)),
        )
        steps.append(step)

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


def load_prompt_text(root: Path, prompt_ref: str) -> str:
    """Resolve a prompt reference as a repo-relative file or inline prompt."""
    prompt_path = Path(prompt_ref)
    if not prompt_path.is_absolute():
        prompt_path = root / prompt_path
    if prompt_path.exists():
        return prompt_path.read_text()
    return prompt_ref


def extract_codex_thread_id(trace_path: Path) -> str:
    """Extract the Codex thread id from the JSONL trace."""
    if not trace_path.exists():
        raise WorkflowExecutionError(f"Missing Codex trace file: {trace_path}")

    for line in trace_path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if payload.get("type") == "thread.started" and payload.get("thread_id"):
            return str(payload["thread_id"])

    raise WorkflowExecutionError(
        f"Codex trace {trace_path} does not contain a thread.started event."
    )


def ensure_shared_benchmark_venv(root: Path) -> Path:
    """Create a shared benchmark virtualenv with the common DS stack."""
    venv_dir = root / BENCHMARK_VENV_DIRNAME
    python_path = venv_dir / "bin" / "python"

    if not python_path.exists():
        subprocess.run(
            ["uv", "venv", str(venv_dir), "--python", "3.14", "--quiet"],
            cwd=root,
            check=True,
        )

    check_script = (
        "mods = "
        + repr(list(SHARED_PACKAGES))
        + "\nfor mod in mods:\n    __import__(mod)\n"
    )
    module_check = subprocess.run(
        [str(python_path), "-c", check_script],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if module_check.returncode != 0:
        subprocess.run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(python_path),
                "--quiet",
                "numpy",
                "pandas",
                "scipy",
                "scikit-learn",
                "matplotlib",
                "seaborn",
                "statsmodels",
                "lifelines",
            ],
            cwd=root,
            check=True,
        )

    return venv_dir


def _prepare_codex_home(work_dir: Path) -> Path:
    codex_home = work_dir / ".codex-home"
    codex_home.mkdir(parents=True, exist_ok=True)
    (codex_home / "shell_snapshots").mkdir(exist_ok=True)

    source_home = Path.home() / ".codex"
    for filename in ("auth.json", "version.json"):
        source = source_home / filename
        if source.exists():
            shutil.copy2(source, codex_home / filename)

    return codex_home


def _prepare_claude_hooks(root: Path, work_dir: Path) -> None:
    claude_dir = work_dir / ".claude"
    hooks_dir = claude_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    settings_path = root / ".claude" / "settings.json"
    hook_path = root / ".claude" / "hooks" / "trace.sh"
    if settings_path.exists():
        shutil.copy2(settings_path, claude_dir / "settings.json")
    if hook_path.exists():
        shutil.copy2(hook_path, hooks_dir / "trace.sh")


def _write_codex_top_session_header(
    results_dir: Path,
    *,
    dataset_name: str,
    root: Path,
    work_dir: Path,
) -> Path:
    session_log = results_dir / "session.log"
    header_lines = [
        f"dataset={dataset_name}",
        f"project_root={root}",
        f"work_dir={work_dir}",
        "max_turns=workflow",
        "tools=workflow-managed",
    ]
    version = subprocess.run(
        ["codex", "--version"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if version.stdout.strip():
        header_lines.append(version.stdout.strip())
    session_log.write_text("\n".join(header_lines) + "\n\n")
    return session_log


def prepare_run_context(
    *,
    root: Path,
    dataset_name: str,
    dataset_csv: Path,
    results_dir: Path,
    backend: str,
) -> RunContext:
    """Prepare the shared temp workspace and base environment."""
    benchmark_venv = ensure_shared_benchmark_venv(root)
    work_dir = Path(tempfile.mkdtemp())
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "steps").mkdir(parents=True, exist_ok=True)

    shutil.copy2(dataset_csv, work_dir / "dataset.csv")
    (work_dir / "plots").mkdir(exist_ok=True)
    (work_dir / ".matplotlib").mkdir(exist_ok=True)
    (work_dir / ".venv").symlink_to(benchmark_venv, target_is_directory=True)

    env = os.environ.copy()
    env["VIRTUAL_ENV"] = str(work_dir / ".venv")
    env["PATH"] = f"{work_dir / '.venv' / 'bin'}:{env.get('PATH', '')}"
    env["MPLCONFIGDIR"] = str(work_dir / ".matplotlib")

    top_trace = results_dir / "trace.jsonl"
    run_state = results_dir / "run_state.json"

    top_session_log = None
    top_session_json = None
    top_final_message = results_dir / "final_message.md"

    if backend == "codex_cli":
        codex_home = _prepare_codex_home(work_dir)
        env["CODEX_HOME"] = str(codex_home)
        top_session_log = _write_codex_top_session_header(
            results_dir,
            dataset_name=dataset_name,
            root=root,
            work_dir=work_dir,
        )
    elif backend == "claude_cli":
        _prepare_claude_hooks(root, work_dir)
        top_session_json = results_dir / "session.json"
    else:
        raise ValueError(f"Unsupported backend: {backend}")

    return RunContext(
        root=root,
        dataset_name=dataset_name,
        results_dir=results_dir,
        work_dir=work_dir,
        backend=backend,
        env=env,
        top_trace_path=top_trace,
        run_state_path=run_state,
        top_session_log_path=top_session_log,
        top_session_json_path=top_session_json,
        top_final_message_path=top_final_message,
    )


def resolve_step_image_inputs(context: RunContext, step: WorkflowStep) -> list[Path]:
    """Resolve relative glob patterns for a step inside the shared workspace."""
    matches: list[Path] = []
    seen: set[Path] = set()

    for pattern in step.image_inputs:
        for path in sorted(context.work_dir.glob(pattern)):
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                matches.append(path)

    context.matched_inputs[step.id] = matches
    return matches


def render_step_prompt(
    *,
    root: Path,
    step: WorkflowStep,
    image_paths: list[Path],
    attachment_mode: str,
) -> str:
    """Load a prompt and prepend image/input guidance for the backend."""
    prompt = load_prompt_text(root, step.prompt).strip()
    if not image_paths:
        return prompt

    relative_paths = "\n".join(
        f"- {path.relative_to(path.anchor) if path.is_absolute() else path}" for path in image_paths
    )
    if attachment_mode == "codex":
        prefix = (
            "Attached image files for this step:\n"
            f"{relative_paths}\n\n"
            "Use the attached images for visual inspection while revising the workspace "
            "outputs.\n\n"
        )
    else:
        prefix = (
            "Inspect these workspace image files during this step:\n"
            f"{relative_paths}\n\n"
            "Review the files directly from the shared workspace and revise the outputs if "
            "needed.\n\n"
        )
    return prefix + prompt


def append_trace(top_trace_path: Path, step_trace_path: Path) -> None:
    """Append step trace content into the top-level run trace."""
    if not step_trace_path.exists():
        return

    with top_trace_path.open("a") as top_trace, step_trace_path.open() as step_trace:
        for line in step_trace:
            top_trace.write(line)


def append_session_log(
    top_session_log_path: Path | None,
    step_id: str,
    session_log_path: Path,
) -> None:
    """Append step session logs into the top-level session log when present."""
    if top_session_log_path is None or not session_log_path.exists():
        return

    with top_session_log_path.open("a") as top_log, session_log_path.open() as step_log:
        top_log.write(f"=== step:{step_id} ===\n")
        for line in step_log:
            top_log.write(line)
        top_log.write("\n")


def publish_top_level_outputs(context: RunContext, final_session: SessionHandle) -> None:
    """Publish the final session outputs and workspace artifacts to top-level paths."""
    if final_session.final_message_path.exists() and context.top_final_message_path is not None:
        shutil.copy2(final_session.final_message_path, context.top_final_message_path)

    if context.top_session_json_path is not None and final_session.session_output_path is not None:
        if final_session.session_output_path.exists():
            shutil.copy2(final_session.session_output_path, context.top_session_json_path)

    report_path = context.work_dir / "analysis_report.md"
    if report_path.exists():
        shutil.copy2(report_path, context.results_dir / "analysis_report.md")

    plots_dir = context.work_dir / "plots"
    if plots_dir.exists() and any(plots_dir.iterdir()):
        destination = context.results_dir / "plots"
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(plots_dir, destination)

    for code_path in context.work_dir.glob("*.py"):
        shutil.copy2(code_path, context.results_dir / code_path.name)


def write_run_state(context: RunContext) -> None:
    """Persist current run state for debugging and resumability."""
    payload = {
        "backend": context.backend,
        "dataset_name": context.dataset_name,
        "work_dir": str(context.work_dir),
        "results_dir": str(context.results_dir),
        "status": context.status,
        "error": context.error,
        "cleaned_up": context.cleaned_up,
        "completed_steps": list(context.completed_steps),
        "skipped_steps": list(context.skipped_steps),
        "matched_inputs": {
            step_id: [str(path.relative_to(context.work_dir)) for path in paths]
            for step_id, paths in context.matched_inputs.items()
        },
        "steps": {
            step_id: {
                "backend": handle.backend,
                "session_id": handle.session_id,
                "step_id": handle.step_id,
                "raw_trace_path": str(handle.raw_trace_path),
                "final_message_path": str(handle.final_message_path),
                "session_log_path": str(handle.session_log_path)
                if handle.session_log_path is not None
                else None,
                "session_output_path": str(handle.session_output_path)
                if handle.session_output_path is not None
                else None,
            }
            for step_id, handle in context.step_sessions.items()
        },
    }
    context.run_state_path.write_text(json.dumps(payload, indent=2))


class CodexCliAdapter(BackendAdapter):
    """Codex CLI workflow adapter."""

    backend_name = "codex_cli"

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_resume=True, supports_image_attachments=True)

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
            session.session_id
            if session is not None
            else extract_codex_thread_id(step_trace)
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
        prompt: str,
        final_message_path: Path,
        image_paths: list[Path],
        session_id: str,
    ) -> list[str]:
        command = ["codex", "exec", "resume"]
        if step.model:
            command.extend(["-m", step.model])
        command.extend(["--json", "--skip-git-repo-check", "-o", str(final_message_path)])
        for path in image_paths:
            command.extend(["-i", str(path.resolve())])
        command.extend([session_id, prompt])
        return command


class ClaudeCliAdapter(BackendAdapter):
    """Claude CLI workflow adapter."""

    backend_name = "claude_cli"

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_resume=True, supports_image_attachments=False)

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


BACKEND_ADAPTERS: dict[str, type[BackendAdapter]] = {
    "codex_cli": CodexCliAdapter,
    "claude_cli": ClaudeCliAdapter,
}


def get_backend_adapter(backend: str, root: Path) -> BackendAdapter:
    """Instantiate a backend adapter from the registry."""
    adapter_cls = BACKEND_ADAPTERS.get(backend)
    if adapter_cls is None:
        raise ValueError(f"Unsupported backend: {backend}")
    return adapter_cls(root)


def run_workflow(
    *,
    config: dict[str, Any],
    dataset_name: str,
    dataset_csv: Path,
    results_dir: Path,
    root: Path,
) -> bool:
    """Run a normalized workflow against one dataset."""
    spec = normalize_workflow_config(config)
    context = prepare_run_context(
        root=root,
        dataset_name=dataset_name,
        dataset_csv=dataset_csv,
        results_dir=results_dir,
        backend=spec.backend,
    )
    adapter = get_backend_adapter(spec.backend, root)
    session: SessionHandle | None = None
    succeeded = False
    write_run_state(context)

    try:
        for step in spec.steps:
            image_paths = resolve_step_image_inputs(context, step)
            if step.image_inputs and not image_paths:
                if step.required:
                    raise WorkflowExecutionError(
                        f"Required step '{step.id}' matched no image inputs: {step.image_inputs}."
                    )
                context.skipped_steps.append(step.id)
                write_run_state(context)
                continue

            handle = (
                adapter.start_step(step, context)
                if session is None
                else adapter.continue_step(step, context, session)
            )
            adapter.collect_step_outputs(step, context, handle)
            context.step_sessions[step.id] = handle
            context.completed_steps.append(step.id)
            append_trace(context.top_trace_path, handle.raw_trace_path)
            if handle.session_log_path is not None:
                append_session_log(context.top_session_log_path, step.id, handle.session_log_path)
            session = handle
            write_run_state(context)

        if session is not None:
            publish_top_level_outputs(context, session)
        context.status = "completed"
        succeeded = True
    except (ValueError, WorkflowExecutionError) as exc:
        context.status = "failed"
        context.error = str(exc)
    finally:
        write_run_state(context)
        shutil.rmtree(context.work_dir, ignore_errors=True)
        context.cleaned_up = True
        write_run_state(context)

    return succeeded
