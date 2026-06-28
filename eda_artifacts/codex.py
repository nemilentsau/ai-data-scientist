import json
import subprocess
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class EdaFramerOutput:
    user_question: str
    analysis_plan: str
    hypotheses: list[dict[str, Any]]
    artifact_requests: list[dict[str, Any]]
    stop_conditions: list[str]


@dataclass(frozen=True)
class ArtifactBuilderOutput:
    sql: str
    chart_spec: dict[str, Any]


@dataclass(frozen=True)
class VisualReviewerOutput:
    verdict: str
    visual_findings: list[str]
    required_revision: str
    report_markdown: str


RoleOutput = EdaFramerOutput | ArtifactBuilderOutput | VisualReviewerOutput
RawRoleOutput = RoleOutput | dict[str, Any]


@dataclass(frozen=True)
class CodexRoleRequest:
    role: str
    prompt: str
    work_dir: Path
    images: list[Path] | None = None
    output_schema_path: Path | None = None
    output_path: Path | None = None


class CodexAdapter(Protocol):
    def invoke(self, request: CodexRoleRequest) -> RawRoleOutput:
        ...


class FakeCodexAdapter:
    def __init__(self, queued_outputs: dict[str, list[RawRoleOutput]]) -> None:
        self._queued_outputs = {
            role: list(outputs)
            for role, outputs in queued_outputs.items()
        }
        self.requests: list[CodexRoleRequest] = []

    def invoke(self, request: CodexRoleRequest) -> RawRoleOutput:
        self.requests.append(request)
        outputs = self._queued_outputs.get(request.role, [])
        if not outputs:
            raise IndexError(f"No queued Codex output for role '{request.role}'.")
        return outputs.pop(0)


class CodexExecAdapter:
    def __init__(self, model: str = "gpt-5.5", timeout_seconds: int = 180) -> None:
        self.model = model
        self.timeout_seconds = timeout_seconds

    def invoke(self, request: CodexRoleRequest) -> dict[str, Any]:
        if request.output_path is None:
            raise ValueError("CodexExecAdapter requires request.output_path.")
        output_path = request.output_path.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = self.build_command(request)
        try:
            subprocess.run(
                command,
                input=request.prompt,
                text=True,
                cwd=request.work_dir.resolve(),
                check=True,
                capture_output=True,
                timeout=self.timeout_seconds,
            )
        except subprocess.CalledProcessError as error:
            raise RuntimeError(
                "codex exec failed for role "
                f"{request.role!r} with exit code {error.returncode}.\n"
                f"stderr:\n{error.stderr or ''}\n"
                f"stdout:\n{error.stdout or error.output or ''}"
            ) from error
        except subprocess.TimeoutExpired as error:
            raise TimeoutError(
                f"codex exec timed out for role {request.role!r} "
                f"after {self.timeout_seconds} seconds."
            ) from error
        if not output_path.exists():
            raise FileNotFoundError(output_path)
        return json.loads(output_path.read_text())

    def build_command(self, request: CodexRoleRequest) -> list[str]:
        command = [
            "codex",
            "exec",
            "--model",
            self.model,
            "--json",
            "--ephemeral",
            "--cd",
            str(request.work_dir.resolve()),
            "--sandbox",
            "workspace-write",
        ]
        if request.output_schema_path is not None:
            command.extend(["--output-schema", str(request.output_schema_path.resolve())])
        if request.output_path is not None:
            command.extend(["-o", str(request.output_path.resolve())])
        for image_path in request.images or []:
            command.extend(["--image", str(image_path.resolve())])
        command.append("-")
        return command


def write_output_json(path: Path, output: RoleOutput | dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if is_dataclass(output):
        payload = asdict(output)
    else:
        payload = output
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


ROLE_OUTPUT_SCHEMAS: dict[str, dict[str, Any]] = {
    "eda_framer": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "user_question",
            "analysis_plan",
            "hypotheses",
            "artifact_requests",
            "stop_conditions",
        ],
        "properties": {
            "user_question": {"type": "string"},
            "analysis_plan": {"type": "string"},
            "hypotheses": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["id", "statement", "rationale", "variables"],
                    "properties": {
                        "id": {"type": "string"},
                        "statement": {"type": "string"},
                        "rationale": {"type": "string"},
                        "variables": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            "artifact_requests": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "id",
                        "hypothesis_id",
                        "artifact_type",
                        "description",
                        "statistical_purpose",
                        "expected_fields",
                    ],
                    "properties": {
                        "id": {"type": "string"},
                        "hypothesis_id": {"type": "string"},
                        "artifact_type": {"type": "string", "enum": ["chart", "table"]},
                        "description": {"type": "string"},
                        "statistical_purpose": {"type": "string"},
                        "expected_fields": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
            "stop_conditions": {"type": "array", "items": {"type": "string"}},
        },
    },
    "artifact_builder": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["sql", "chart_spec"],
        "properties": {
            "sql": {"type": "string"},
            "chart_spec": {"type": "string"},
        },
    },
    "visual_reviewer": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["verdict", "visual_findings", "required_revision", "report_markdown"],
        "properties": {
            "verdict": {"type": "string", "enum": ["pass", "revise"]},
            "visual_findings": {"type": "array", "items": {"type": "string"}},
            "required_revision": {"type": "string"},
            "report_markdown": {"type": "string"},
        },
    },
}


def write_role_output_schema(path: Path, role: str) -> None:
    schema = ROLE_OUTPUT_SCHEMAS.get(role)
    if schema is None:
        raise KeyError(f"No output schema registered for role '{role}'.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(schema, indent=2, sort_keys=True))
