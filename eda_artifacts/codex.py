import json
import subprocess
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class EdaFramerOutput:
    primary_question: str
    required_checks: list[str]
    chart_requests: list[str]
    stop_conditions: list[str]


@dataclass(frozen=True)
class ArtifactBuilderOutput:
    sql: str
    chart_spec: dict[str, Any]
    report_markdown: str


@dataclass(frozen=True)
class VisualReviewerOutput:
    verdict: str
    visual_findings: list[str]
    required_revision: str


RoleOutput = EdaFramerOutput | ArtifactBuilderOutput | VisualReviewerOutput


@dataclass(frozen=True)
class CodexRoleRequest:
    role: str
    prompt: str
    work_dir: Path
    images: list[Path] | None = None
    output_schema_path: Path | None = None
    output_path: Path | None = None


class CodexAdapter(Protocol):
    def invoke(self, request: CodexRoleRequest) -> RoleOutput:
        """Invoke a Codex role and return a structured result."""


class FakeCodexAdapter:
    def __init__(self, queued_outputs: dict[str, list[RoleOutput]]) -> None:
        self._queued_outputs = {
            role: list(outputs)
            for role, outputs in queued_outputs.items()
        }
        self.requests: list[CodexRoleRequest] = []

    def invoke(self, request: CodexRoleRequest) -> RoleOutput:
        self.requests.append(request)
        outputs = self._queued_outputs.get(request.role, [])
        if not outputs:
            raise IndexError(f"No queued Codex output for role '{request.role}'.")
        return outputs.pop(0)


class CodexExecAdapter:
    def __init__(self, model: str = "gpt-5.5") -> None:
        self.model = model

    def invoke(self, request: CodexRoleRequest) -> dict[str, Any]:
        if request.output_path is None:
            raise ValueError("CodexExecAdapter requires request.output_path.")
        completed = subprocess.run(
            self.build_command(request),
            input=request.prompt,
            text=True,
            cwd=request.work_dir,
            check=True,
            capture_output=True,
        )
        if not request.output_path.exists():
            raise FileNotFoundError(request.output_path)
        return json.loads(request.output_path.read_text())

    def build_command(self, request: CodexRoleRequest) -> list[str]:
        command = [
            "codex",
            "exec",
            "--model",
            self.model,
            "--json",
            "--ephemeral",
            "--cd",
            str(request.work_dir),
            "--sandbox",
            "workspace-write",
            "--ask-for-approval",
            "never",
        ]
        if request.output_schema_path is not None:
            command.extend(["--output-schema", str(request.output_schema_path)])
        if request.output_path is not None:
            command.extend(["-o", str(request.output_path)])
        for image_path in request.images or []:
            command.extend(["--image", str(image_path)])
        command.append("-")
        return command


def write_output_json(path: Path, output: RoleOutput | dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if is_dataclass(output):
        payload = asdict(output)
    else:
        payload = output
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))

