# External Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the shared-session workflow runner with a fresh-invocation external orchestrator that uses explicit published artifacts, split planning/execution roles, bounded critique loops, and post-round memory curation.

**Architecture:** The new runtime uses one private workdir per invocation, one fresh CLI session per role run, and a canonical artifact tree under each benchmark case. The loop is deterministic at the routing layer, but analytical judgment stays in role agents: `task_framer`, `analysis_planner`, `analysis_executor`, `method_critic`, `visual_critic`, `verifier`, and `memory_curator`. Runtime backward compatibility is intentionally dropped, but experiment import/history compatibility is preserved.

**Tech Stack:** Python 3.14, `uv`, `pytest`, YAML configs, Codex CLI, Claude CLI, SQLite experiment catalog

---

## File Map

### Create

- `ai_data_scientist/orchestration/profile.py` — deterministic dataset profiling helpers that write canonical profile artifacts
- `ai_data_scientist/orchestration/ledgers.py` — ledger creation, status updates, and bounded role-memory paths
- `prompts/active/task-framer.md` — active role prompt for framing
- `prompts/active/analysis-planner.md` — active role prompt for planning hypotheses and required evidence
- `prompts/active/analysis-executor.md` — active role prompt for code, plots, and statistical execution
- `prompts/active/method-critic.md` — active role prompt for methodological critique
- `prompts/active/visual-critic.md` — active role prompt for visual critique
- `prompts/active/verifier.md` — active role prompt for round verdicts
- `prompts/active/memory-curator.md` — active role prompt for bounded role memory
- `results/configs/codex-multiagent-v1.yaml` — Codex-led execution config for the new runtime
- `results/configs/claude-multiagent-v1.yaml` — Claude-led execution config for the new runtime
- `tests/test_orchestration_config.py` — config/schema tests for the new orchestrator runtime
- `tests/test_orchestration_runtime.py` — runtime, adapters, publish contract, and loop tests
- `tests/test_orchestration_profile.py` — deterministic profile artifact tests

### Modify

- `ai_data_scientist/orchestration/models.py` — replace step/resume dataclasses with role spec, runtime policy, run context, invocation context, and verdict models
- `ai_data_scientist/orchestration/config.py` — normalize the new `roles` + `runtime` config shape and reject legacy runtime configs
- `ai_data_scientist/orchestration/workspace.py` — create run roots, invocation roots, materialized input trees, and fresh venv-backed invocation environments
- `ai_data_scientist/orchestration/outputs.py` — publish declared outputs, maintain artifact index, and persist run state/transitions
- `ai_data_scientist/orchestration/prompts.py` — render prompts from active prompt files, published artifacts, ledgers, and role memory
- `ai_data_scientist/orchestration/runner.py` — implement the deterministic state machine and bounded loop
- `ai_data_scientist/orchestration/adapters/base.py` — simplify the backend interface around one fresh invocation call
- `ai_data_scientist/orchestration/adapters/codex_cli.py` — run fresh Codex sessions per invocation, no `resume`
- `ai_data_scientist/orchestration/adapters/claude_cli.py` — run fresh Claude sessions per invocation, no `--resume`
- `ai_data_scientist/orchestration/trace.py` — aggregate invocation traces and logs into canonical run metadata
- `ai_data_scientist/orchestration/__init__.py` — export the new runtime surface
- `ai_data_scientist/cli/benchmark.py` — use the new runtime, new config names, and new result paths
- `ai_data_scientist/experiments/importer.py` — import multi-agent run trees and preserve old run import behavior
- `reviewer/scorer.py` — read canonical analysis artifacts from the new run layout
- `README.md` — document the new config shape, runtime layout, and prompt location
- `tests/test_run_benchmark.py` — update benchmark CLI tests for the new config names and run layout
- `tests/test_experiment_import.py` — extend import assertions for new multi-agent artifacts while keeping legacy coverage

### Delete

- `harness/prompt_template.txt` — legacy fallback prompt that no longer participates in runtime execution
- `harness/run_codex.sh` — legacy shim superseded by direct backend adapter invocation
- `harness/run_claude.sh` — legacy shim superseded by direct backend adapter invocation
- `tests/test_benchmark_orchestrator.py` — replace the monolithic resume/workspace test file with focused config/runtime/profile tests after porting its useful coverage

## Task 1: Define The New Config Schema And Runtime Models

**Files:**
- Create: `tests/test_orchestration_config.py`
- Modify: `ai_data_scientist/orchestration/models.py`
- Modify: `ai_data_scientist/orchestration/config.py`
- Modify: `ai_data_scientist/orchestration/__init__.py`

- [ ] **Step 1: Write the failing config tests**

```python
from __future__ import annotations

import pytest

from ai_data_scientist.orchestration.config import normalize_workflow_config


def test_new_runtime_config_builds_role_specs():
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
            },
        },
        "runtime": {
            "max_revision_rounds": 1,
            "max_reframes": 1,
            "memory_curator": True,
        },
    }

    spec = normalize_workflow_config(config)

    assert spec.roles["task_framer"].backend == "claude_cli"
    assert spec.roles["analysis_executor"].backend == "codex_cli"
    assert spec.runtime.max_revision_rounds == 1
    assert spec.runtime.memory_curator is True


def test_legacy_runtime_configs_fail_with_clear_error():
    config = {
        "name": "solo-codex",
        "team": [{"role": "codex", "prompt": "prompts/analyst-generic.md"}],
        "harness": "harness/run_codex.sh",
    }

    with pytest.raises(ValueError, match="Legacy runtime configs are no longer supported"):
        normalize_workflow_config(config)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_orchestration_config.py -v`

Expected: FAIL because `normalize_workflow_config()` still accepts the old `workflow`/`team` shapes and there are no role/runtime dataclasses yet.

- [ ] **Step 3: Write the minimal model and config implementation**

```python
from dataclasses import dataclass, field

DEFAULT_TOOLS = ("Bash", "Read", "Write", "Edit", "Glob", "Grep")


@dataclass(frozen=True)
class RoleSpec:
    role: str
    backend: str
    prompt: str
    model: str = ""
    tools: tuple[str, ...] = DEFAULT_TOOLS
    max_turns: int = 30


@dataclass(frozen=True)
class RuntimePolicy:
    max_revision_rounds: int = 1
    max_reframes: int = 1
    memory_curator: bool = True


@dataclass(frozen=True)
class OrchestratorSpec:
    name: str
    description: str
    roles: dict[str, RoleSpec]
    runtime: RuntimePolicy


@dataclass
class RunContext:
    root: Path
    results_dir: Path
    dataset_name: str
    spec: OrchestratorSpec | None = None
    status: str = "in_progress"
    revision_rounds: int = 0
    reframes: int = 0


def normalize_workflow_config(config: dict[str, object]) -> OrchestratorSpec:
    if "roles" not in config or "runtime" not in config:
        raise ValueError("Legacy runtime configs are no longer supported; use roles + runtime.")

    roles = {
        role_name: RoleSpec(
            role=role_name,
            backend=str(payload["backend"]),
            prompt=str(payload["prompt"]),
            model=str(payload.get("model", "") or ""),
            tools=tuple(payload.get("tools", DEFAULT_TOOLS)),
        )
        for role_name, payload in dict(config["roles"]).items()
    }
    runtime_payload = dict(config["runtime"])
    runtime = RuntimePolicy(
        max_revision_rounds=int(runtime_payload.get("max_revision_rounds", 1)),
        max_reframes=int(runtime_payload.get("max_reframes", 1)),
        memory_curator=bool(runtime_payload.get("memory_curator", True)),
    )
    return OrchestratorSpec(
        name=str(config.get("name") or "orchestrator-runtime"),
        description=str(config.get("description") or ""),
        roles=roles,
        runtime=runtime,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_orchestration_config.py -v`

Expected: PASS for both tests.

- [ ] **Step 5: Commit**

```bash
git add tests/test_orchestration_config.py ai_data_scientist/orchestration/models.py ai_data_scientist/orchestration/config.py ai_data_scientist/orchestration/__init__.py
git commit -m "refactor: define orchestrator v1 config schema"
```

## Task 2: Build Invocation Isolation And Publish Contracts

**Files:**
- Create: `tests/test_orchestration_runtime.py`
- Modify: `ai_data_scientist/orchestration/models.py`
- Modify: `ai_data_scientist/orchestration/workspace.py`
- Modify: `ai_data_scientist/orchestration/outputs.py`

- [ ] **Step 1: Write the failing runtime isolation tests**

```python
from __future__ import annotations

from pathlib import Path

from ai_data_scientist.orchestration.models import PublishContract, RoleSpec
from ai_data_scientist.orchestration.outputs import publish_declared_outputs
from ai_data_scientist.orchestration.workspace import create_invocation_context


def test_invocation_workspace_materializes_only_declared_inputs(tmp_path: Path):
    run_dir = tmp_path / "results" / "runs" / "codex-multiagent-v1" / "multimodal"
    source_artifact = run_dir / "artifacts" / "framing" / "framing.json"
    source_artifact.parent.mkdir(parents=True, exist_ok=True)
    source_artifact.write_text('{"primary_frame":"mixture"}')

    invocation = create_invocation_context(
        run_dir=run_dir,
        role=RoleSpec(role="analysis_planner", backend="claude_cli", prompt="prompt.md"),
        artifact_inputs=[source_artifact],
    )

    assert (invocation.input_dir / "artifacts" / "framing" / "framing.json").exists()
    assert not (invocation.input_dir / "artifacts" / "analysis").exists()


def test_publish_contract_copies_only_declared_outputs(tmp_path: Path):
    run_dir = tmp_path / "results" / "runs" / "codex-multiagent-v1" / "multimodal"
    invocation = create_invocation_context(
        run_dir=run_dir,
        role=RoleSpec(role="analysis_executor", backend="codex_cli", prompt="prompt.md"),
        artifact_inputs=[],
    )

    (invocation.work_dir / "analysis_report.md").write_text("# Analysis\n")
    (invocation.work_dir / "scratch.txt").write_text("debug only")

    publish_declared_outputs(
        run_dir=run_dir,
        invocation=invocation,
        contract=PublishContract(
            role="analysis_executor",
            declared_outputs=("analysis_report.md",),
        ),
    )

    assert (run_dir / "artifacts" / "analysis" / "analysis_report.md").exists()
    assert not (run_dir / "artifacts" / "analysis" / "scratch.txt").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_orchestration_runtime.py -v`

Expected: FAIL because there is no invocation context helper and no publish contract implementation.

- [ ] **Step 3: Implement invocation context and publish helpers**

```python
@dataclass(frozen=True)
class PublishContract:
    role: str
    declared_outputs: tuple[str, ...]


@dataclass
class InvocationContext:
    invocation_id: str
    role: str
    root_dir: Path
    input_dir: Path
    work_dir: Path
    output_dir: Path
    logs_dir: Path
    trace_dir: Path
    manifest_path: Path


@dataclass(frozen=True)
class InvocationResult:
    status: str
    final_message_path: Path
    raw_trace_path: Path


def create_invocation_context(*, run_dir: Path, role: RoleSpec, artifact_inputs: list[Path]) -> InvocationContext:
    invocation_id = f"{role.role}-0001"
    root_dir = run_dir / "invocations" / invocation_id
    input_dir = root_dir / "input"
    work_dir = root_dir / "workspace"
    output_dir = root_dir / "output"
    logs_dir = root_dir / "logs"
    trace_dir = root_dir / "trace"
    for path in (input_dir, work_dir, output_dir, logs_dir, trace_dir):
        path.mkdir(parents=True, exist_ok=True)

    for source_path in artifact_inputs:
        destination = input_dir / source_path.relative_to(run_dir)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)

    return InvocationContext(
        invocation_id=invocation_id,
        role=role.role,
        root_dir=root_dir,
        input_dir=input_dir,
        work_dir=work_dir,
        output_dir=output_dir,
        logs_dir=logs_dir,
        trace_dir=trace_dir,
        manifest_path=root_dir / "manifest.json",
    )


def publish_declared_outputs(*, run_dir: Path, invocation: InvocationContext, contract: PublishContract) -> list[Path]:
    published: list[Path] = []
    role_to_dir = {
        "task_framer": "framing",
        "analysis_planner": "planning",
        "analysis_executor": "analysis",
        "method_critic": "critiques",
        "visual_critic": "critiques",
        "verifier": "verification",
        "memory_curator": "memory",
    }
    destination_root = run_dir / "artifacts" / role_to_dir[contract.role]
    destination_root.mkdir(parents=True, exist_ok=True)
    for relative_output in contract.declared_outputs:
        source_path = invocation.work_dir / relative_output
        if not source_path.exists():
            continue
        destination_path = destination_root / Path(relative_output).name
        shutil.copy2(source_path, destination_path)
        published.append(destination_path)
    return published
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_orchestration_runtime.py -v`

Expected: PASS for both tests.

- [ ] **Step 5: Commit**

```bash
git add tests/test_orchestration_runtime.py ai_data_scientist/orchestration/models.py ai_data_scientist/orchestration/workspace.py ai_data_scientist/orchestration/outputs.py
git commit -m "refactor: add invocation isolation and publish contracts"
```

## Task 3: Switch Both Backend Adapters To Fresh Invocations

**Files:**
- Modify: `ai_data_scientist/orchestration/adapters/base.py`
- Modify: `ai_data_scientist/orchestration/adapters/codex_cli.py`
- Modify: `ai_data_scientist/orchestration/adapters/claude_cli.py`
- Modify: `ai_data_scientist/orchestration/prompts.py`
- Test: `tests/test_orchestration_runtime.py`

- [ ] **Step 1: Add failing tests for fresh-session backend behavior**

```python
def test_codex_adapter_starts_fresh_exec_for_every_invocation(tmp_path: Path, monkeypatch):
    recorded_commands: list[list[str]] = []
    role = RoleSpec(role="analysis_executor", backend="codex_cli", prompt="prompt.md")
    context = RunContext(root=tmp_path, results_dir=tmp_path / "results", dataset_name="multimodal")
    invocation = InvocationContext(
        invocation_id="analysis-executor-0001",
        role="analysis_executor",
        root_dir=tmp_path / "invocations" / "analysis-executor-0001",
        input_dir=tmp_path / "invocations" / "analysis-executor-0001" / "input",
        work_dir=tmp_path / "invocations" / "analysis-executor-0001" / "workspace",
        output_dir=tmp_path / "invocations" / "analysis-executor-0001" / "output",
        logs_dir=tmp_path / "invocations" / "analysis-executor-0001" / "logs",
        trace_dir=tmp_path / "invocations" / "analysis-executor-0001" / "trace",
        manifest_path=tmp_path / "invocations" / "analysis-executor-0001" / "manifest.json",
    )
    invocation.work_dir.mkdir(parents=True, exist_ok=True)

    def fake_run(command, **kwargs):
        recorded_commands.append(command)
        kwargs["stdout"].write('{"type":"thread.started","thread_id":"fresh-thread"}\n')
        return type("Completed", (), {"returncode": 0})()

    monkeypatch.setattr(codex_cli.subprocess, "run", fake_run)

    adapter = codex_cli.CodexCliAdapter(tmp_path)
    adapter.invoke(role, context, invocation, "Analyze the published artifacts.")

    assert all("resume" not in command for command in recorded_commands)


def test_claude_adapter_starts_fresh_session_for_every_invocation(tmp_path: Path, monkeypatch):
    recorded_commands: list[list[str]] = []
    role = RoleSpec(role="task_framer", backend="claude_cli", prompt="prompt.md", tools=("Bash", "Read"))
    context = RunContext(root=tmp_path, results_dir=tmp_path / "results", dataset_name="multimodal")
    invocation = InvocationContext(
        invocation_id="task-framer-0001",
        role="task_framer",
        root_dir=tmp_path / "invocations" / "task-framer-0001",
        input_dir=tmp_path / "invocations" / "task-framer-0001" / "input",
        work_dir=tmp_path / "invocations" / "task-framer-0001" / "workspace",
        output_dir=tmp_path / "invocations" / "task-framer-0001" / "output",
        logs_dir=tmp_path / "invocations" / "task-framer-0001" / "logs",
        trace_dir=tmp_path / "invocations" / "task-framer-0001" / "trace",
        manifest_path=tmp_path / "invocations" / "task-framer-0001" / "manifest.json",
    )
    invocation.work_dir.mkdir(parents=True, exist_ok=True)

    def fake_run(command, **kwargs):
        recorded_commands.append(command)
        kwargs["stdout"].write('{"result":"ok"}')
        return type("Completed", (), {"returncode": 0})()

    monkeypatch.setattr(claude_cli.subprocess, "run", fake_run)

    adapter = claude_cli.ClaudeCliAdapter(tmp_path)
    adapter.invoke(role, context, invocation, "Frame the task.")

    assert "--resume" not in recorded_commands[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_orchestration_runtime.py -v`

Expected: FAIL because the adapter interface still exposes `start_step()` and `continue_step()` and the existing commands still use `resume`.

- [ ] **Step 3: Replace the adapter interface with one-invocation execution**

```python
class BackendAdapter:
    backend_name: str = ""

    def __init__(self, root: Path):
        self.root = root

    def prepare_run(self, context: RunContext) -> None:
        """Mutate the run context with backend-specific shared state."""

    def invoke(
        self,
        role: RoleSpec,
        context: RunContext,
        invocation: InvocationContext,
        prompt: str,
    ) -> InvocationResult:
        raise NotImplementedError
```

```python
command = [
    "codex",
    "-a",
    "never",
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
```

```python
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
```

- [ ] **Step 4: Update prompt rendering so every invocation gets only published artifacts and role memory**

```python
def render_role_prompt(*, root: Path, role: RoleSpec, artifact_inputs: list[Path], role_memory: Path | None) -> str:
    prompt = load_prompt_text(root, role.prompt).strip()
    artifact_block = "\n".join(f"- {path}" for path in artifact_inputs)
    memory_block = ""
    if role_memory is not None and role_memory.exists():
        memory_block = (
            "Role memory for this invocation:\n"
            f"{role_memory.read_text().strip()}\n\n"
        )
    return (
        f"{memory_block}"
        "Published input artifacts for this invocation:\n"
        f"{artifact_block}\n\n"
        f"{prompt}"
    )
```

- [ ] **Step 5: Run the runtime test file**

Run: `uv run pytest tests/test_orchestration_runtime.py -v`

Expected: PASS with no backend command using `resume`.

- [ ] **Step 6: Commit**

```bash
git add ai_data_scientist/orchestration/adapters/base.py ai_data_scientist/orchestration/adapters/codex_cli.py ai_data_scientist/orchestration/adapters/claude_cli.py ai_data_scientist/orchestration/prompts.py tests/test_orchestration_runtime.py
git commit -m "refactor: run backends as fresh invocations"
```

## Task 4: Add Deterministic Profiling And The Happy-Path Planner/Executor Flow

**Files:**
- Create: `ai_data_scientist/orchestration/profile.py`
- Create: `prompts/active/task-framer.md`
- Create: `prompts/active/analysis-planner.md`
- Create: `prompts/active/analysis-executor.md`
- Create: `tests/test_orchestration_profile.py`
- Modify: `ai_data_scientist/orchestration/runner.py`
- Modify: `ai_data_scientist/orchestration/workspace.py`
- Test: `tests/test_orchestration_runtime.py`

- [ ] **Step 1: Write the failing profile and happy-path runner tests**

```python
def test_profile_dataset_writes_expected_artifacts(tmp_path: Path):
    dataset_csv = tmp_path / "dataset.csv"
    dataset_csv.write_text("x,y\n1,2\n3,4\n")

    profile_paths = profile_dataset(dataset_csv=dataset_csv, run_dir=tmp_path / "run")

    assert profile_paths["schema"].exists()
    assert profile_paths["column_summary"].exists()
    assert profile_paths["sample_rows"].exists()


def test_runner_executes_framer_planner_executor_in_order(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    dataset_csv = root / "dataset.csv"
    dataset_csv.write_text("x,y\n1,2\n")
    results_dir = root / "results" / "runs" / "codex-multiagent-v1" / "multimodal"
    calls: list[str] = []
    config = {
        "name": "codex-multiagent-v1",
        "roles": {
            "task_framer": {"backend": "claude_cli", "prompt": "prompts/active/task-framer.md"},
            "analysis_planner": {"backend": "claude_cli", "prompt": "prompts/active/analysis-planner.md"},
            "analysis_executor": {"backend": "codex_cli", "prompt": "prompts/active/analysis-executor.md"},
        },
        "runtime": {"max_revision_rounds": 1, "max_reframes": 1, "memory_curator": False},
    }

    class FakeAdapter:
        def __init__(self, _root: Path):
            self.root = _root

        def prepare_run(self, context):
            del context

        def invoke(self, role, context, invocation, prompt):
            del context, prompt
            calls.append(role.role)
            if role.role == "task_framer":
                (invocation.work_dir / "framing.json").write_text('{"primary_frame":"regression"}')
            elif role.role == "analysis_planner":
                (invocation.work_dir / "analysis_plan.md").write_text("# Plan\n")
                (invocation.work_dir / "hypotheses.json").write_text('{"items":[{"id":"hyp_1"}]}')
                (invocation.work_dir / "experiment_plan.json").write_text('{"items":[{"id":"exp_1"}]}')
            elif role.role == "analysis_executor":
                (invocation.work_dir / "analysis_report.md").write_text("# Analysis\n")
            return InvocationResult(status="completed", final_message_path=invocation.work_dir / "final.md", raw_trace_path=invocation.trace_dir / "trace.jsonl")

    monkeypatch.setitem(orchestration_runner.BACKEND_ADAPTERS, "codex_cli", FakeAdapter)
    monkeypatch.setitem(orchestration_runner.BACKEND_ADAPTERS, "claude_cli", FakeAdapter)

    succeeded = run_workflow(
        config=config,
        dataset_name="multimodal",
        dataset_csv=dataset_csv,
        results_dir=results_dir,
        root=root,
    )

    assert succeeded is True
    assert calls == ["task_framer", "analysis_planner", "analysis_executor"]
```

- [ ] **Step 2: Run the targeted tests**

Run: `uv run pytest tests/test_orchestration_profile.py tests/test_orchestration_runtime.py -v`

Expected: FAIL because there is no profiling module and the runner still assumes ordered workflow steps.

- [ ] **Step 3: Implement deterministic profiling**

```python
def profile_dataset(*, dataset_csv: Path, run_dir: Path) -> dict[str, Path]:
    profile_dir = run_dir / "artifacts" / "profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    frame = pd.read_csv(dataset_csv)
    (profile_dir / "schema.json").write_text(frame.dtypes.astype(str).to_json(indent=2))
    frame.describe(include="all").transpose().to_csv(profile_dir / "column_summary.csv")
    frame.head(20).to_csv(profile_dir / "sample_rows.csv", index=False)
    frame.isna().sum().to_csv(profile_dir / "null_summary.csv")

    return {
        "schema": profile_dir / "schema.json",
        "column_summary": profile_dir / "column_summary.csv",
        "sample_rows": profile_dir / "sample_rows.csv",
        "null_summary": profile_dir / "null_summary.csv",
    }
```

- [ ] **Step 4: Implement the first runner slice around `task_framer -> analysis_planner -> analysis_executor`**

```python
def resolve_role_inputs(context: RunContext, role_name: str) -> list[Path]:
    base = context.results_dir / "artifacts"
    mapping = {
        "task_framer": [base / "profile"],
        "analysis_planner": [base / "profile", base / "framing", base / "memory"],
        "analysis_executor": [base / "profile", base / "framing", base / "planning"],
    }
    paths: list[Path] = []
    for root in mapping[role_name]:
        if root.exists():
            paths.extend(path for path in sorted(root.rglob("*")) if path.is_file())
    return paths


def publish_role_outputs(
    context: RunContext,
    invocation: InvocationContext,
    role_name: str,
    result: InvocationResult,
) -> list[Path]:
    contracts = {
        "task_framer": PublishContract(role="task_framer", declared_outputs=("framing.json",)),
        "analysis_planner": PublishContract(
            role="analysis_planner",
            declared_outputs=("analysis_plan.md", "hypotheses.json", "experiment_plan.json"),
        ),
        "analysis_executor": PublishContract(
            role="analysis_executor",
            declared_outputs=("analysis_report.md",),
        ),
    }
    del result
    return publish_declared_outputs(
        run_dir=context.results_dir,
        invocation=invocation,
        contract=contracts[role_name],
    )


adapter_cache: dict[str, BackendAdapter] = {}


role_order = ("task_framer", "analysis_planner", "analysis_executor")
for role_name in role_order:
    role = spec.roles[role_name]
    artifact_inputs = resolve_role_inputs(context, role_name)
    invocation = create_invocation_context(run_dir=context.results_dir, role=role, artifact_inputs=artifact_inputs)
    prompt = render_role_prompt(
        root=context.root,
        role=role,
        artifact_inputs=[path.relative_to(context.results_dir) for path in artifact_inputs],
        role_memory=None,
    )
    adapter = adapter_cache.setdefault(role.backend, get_backend_adapter(role.backend, context.root))
    result = adapter.invoke(role, context, invocation, prompt)
    publish_role_outputs(context, invocation, role_name, result)
```

- [ ] **Step 5: Add the first active prompts**

```markdown
You are the `analysis_planner`.

Read the published framing and profile artifacts first.
Write:
- `analysis_plan.md`
- `hypotheses.json`
- `experiment_plan.json`

Each hypothesis and experiment request must use stable ids.
Do not write `analysis_report.md`.
```

```markdown
You are the `analysis_executor`.

Read the published plan artifacts first.
Write:
- `analysis_report.md`
- plot PNG files
- `findings.json`
- `claim_evidence_map.json`
- `stats/` JSON artifacts
Do not revise the requested experiments silently. If you cannot complete a requested experiment, record that in the revision execution memo.
```

- [ ] **Step 6: Run the profile and runtime tests**

Run: `uv run pytest tests/test_orchestration_profile.py tests/test_orchestration_runtime.py -v`

Expected: PASS for the profile file and planner/executor happy-path coverage.

- [ ] **Step 7: Commit**

```bash
git add ai_data_scientist/orchestration/profile.py ai_data_scientist/orchestration/runner.py ai_data_scientist/orchestration/workspace.py prompts/active/task-framer.md prompts/active/analysis-planner.md prompts/active/analysis-executor.md tests/test_orchestration_profile.py tests/test_orchestration_runtime.py
git commit -m "feat: add profiling and planner executor flow"
```

## Task 5: Add Critics, Verifier, Ledgers, And Memory Curation

**Files:**
- Create: `ai_data_scientist/orchestration/ledgers.py`
- Create: `prompts/active/method-critic.md`
- Create: `prompts/active/visual-critic.md`
- Create: `prompts/active/verifier.md`
- Create: `prompts/active/memory-curator.md`
- Modify: `ai_data_scientist/orchestration/models.py`
- Modify: `ai_data_scientist/orchestration/runner.py`
- Modify: `ai_data_scientist/orchestration/outputs.py`
- Test: `tests/test_orchestration_runtime.py`

- [ ] **Step 1: Add failing loop and memory tests**

```python
def collect_memory_inputs(run_dir: Path) -> list[Path]:
    artifact_root = run_dir / "artifacts"
    return [path for path in sorted(artifact_root.rglob("*")) if path.is_file()]


def test_verifier_revise_runs_a_new_planner_and_executor_round(tmp_path: Path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    dataset_csv = root / "dataset.csv"
    dataset_csv.write_text("x,y\n1,2\n")
    results_dir = root / "results" / "runs" / "codex-multiagent-v1" / "multimodal"
    calls: list[str] = []
    revise_config = {
        "name": "codex-multiagent-v1",
        "roles": {
            "task_framer": {"backend": "claude_cli", "prompt": "prompts/active/task-framer.md"},
            "analysis_planner": {"backend": "claude_cli", "prompt": "prompts/active/analysis-planner.md"},
            "analysis_executor": {"backend": "codex_cli", "prompt": "prompts/active/analysis-executor.md"},
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
            if role.role == "verifier":
                verdict = "revise" if calls.count("verifier") == 1 else "pass"
                (invocation.work_dir / "verification.json").write_text(
                    f'{{"verdict":"{verdict}","required_repairs":[],"reframing_reasons":[]}}'
                )
            elif role.role == "memory_curator":
                memory_dir = invocation.work_dir / "memory"
                memory_dir.mkdir(exist_ok=True)
                (memory_dir / "analysis_planner.md").write_text("Do not request exp_1 again.")
            else:
                (invocation.work_dir / f"{role.role}.json").write_text("{}")
            return InvocationResult(status="completed", final_message_path=invocation.work_dir / "final.md", raw_trace_path=invocation.trace_dir / "trace.jsonl")

    monkeypatch.setitem(orchestration_runner.BACKEND_ADAPTERS, "codex_cli", FakeAdapter)
    monkeypatch.setitem(orchestration_runner.BACKEND_ADAPTERS, "claude_cli", FakeAdapter)

    succeeded = run_workflow(
        config=revise_config,
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


def test_memory_curator_reads_only_published_artifacts(tmp_path: Path):
    run_dir = tmp_path / "run"
    (run_dir / "artifacts" / "verification" / "verification.json").parent.mkdir(parents=True, exist_ok=True)
    (run_dir / "artifacts" / "verification" / "verification.json").write_text('{"verdict":"revise"}')
    private_log = run_dir / "invocations" / "analysis_executor-0001" / "logs" / "session.log"
    private_log.parent.mkdir(parents=True, exist_ok=True)
    private_log.write_text("private detail")

    memory_inputs = collect_memory_inputs(run_dir)

    assert private_log not in memory_inputs
    assert run_dir / "artifacts" / "verification" / "verification.json" in memory_inputs
```

- [ ] **Step 2: Run the runtime tests**

Run: `uv run pytest tests/test_orchestration_runtime.py -v`

Expected: FAIL because there is no loop routing, no ledgers, and no memory curator.

- [ ] **Step 3: Implement ledgers and bounded role memory helpers**

```python
def initialize_ledgers(run_dir: Path) -> dict[str, Path]:
    ledgers_dir = run_dir / "artifacts" / "ledgers"
    ledgers_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "hypotheses": ledgers_dir / "hypothesis_ledger.json",
        "experiments": ledgers_dir / "experiment_ledger.json",
        "issues": ledgers_dir / "issue_ledger.json",
    }
    for path in files.values():
        if not path.exists():
            path.write_text('{"items":[]}\n')
    return files


def role_memory_paths(run_dir: Path) -> dict[str, Path]:
    memory_dir = run_dir / "artifacts" / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    return {
        "task_framer": memory_dir / "task_framer.md",
        "analysis_planner": memory_dir / "analysis_planner.md",
    }
```

- [ ] **Step 4: Extend the runner with the bounded loop and post-verifier memory curation**

```python
import json


def load_verifier_verdict(run_dir: Path) -> str:
    payload = json.loads((run_dir / "artifacts" / "verification" / "verification.json").read_text())
    return str(payload["verdict"])


adapter_cache: dict[str, BackendAdapter] = {}


def run_role(role_name: str) -> InvocationResult:
    role = context.spec.roles[role_name]
    artifact_inputs = resolve_role_inputs(context, role_name)
    invocation = create_invocation_context(run_dir=context.results_dir, role=role, artifact_inputs=artifact_inputs)
    prompt = render_role_prompt(
        root=context.root,
        role=role,
        artifact_inputs=[path.relative_to(context.results_dir) for path in artifact_inputs],
        role_memory=None,
    )
    adapter = adapter_cache.setdefault(role.backend, get_backend_adapter(role.backend, context.root))
    result = adapter.invoke(role, context, invocation, prompt)
    publish_role_outputs(context, invocation, role_name, result)
    return result


def run_parallel_roles(role_names: list[str]) -> list[InvocationResult]:
    return [run_role(role_name) for role_name in role_names]


while True:
    run_role("analysis_planner")
    run_role("analysis_executor")
    run_parallel_roles(["method_critic", "visual_critic"])
    verifier_result = run_role("verifier")
    run_role("memory_curator")

    verdict = load_verifier_verdict(context.results_dir)
    if verdict == "pass":
        context.status = "completed"
        break
    if verdict == "revise" and context.revision_rounds < context.spec.runtime.max_revision_rounds:
        context.revision_rounds += 1
        continue
    if verdict == "reframe" and context.reframes < context.spec.runtime.max_reframes:
        context.reframes += 1
        run_role("task_framer")
        continue
    context.status = "failed"
    break
```

- [ ] **Step 5: Add the remaining active prompts**

```markdown
You are the `verifier`.

Read the published framing, planning, execution, critique, and ledger artifacts.
Write `verification.json` with one of:
- `pass`
- `revise`
- `reframe`
- `fail_terminal`

If you choose `revise`, include concrete required repairs.
If you choose `reframe`, include concrete reframing reasons.
```

```markdown
You are the `memory_curator`.

Read only published artifacts and ledgers.
Rewrite:
- `memory/task_framer.md`
- `memory/analysis_planner.md`

Do not read private invocation logs.
Do not append forever. Rewrite bounded summaries for the next round.
```

- [ ] **Step 6: Run the runtime suite again**

Run: `uv run pytest tests/test_orchestration_runtime.py -v`

Expected: PASS for revise, reframe, and bounded-memory behavior.

- [ ] **Step 7: Commit**

```bash
git add ai_data_scientist/orchestration/ledgers.py ai_data_scientist/orchestration/models.py ai_data_scientist/orchestration/runner.py ai_data_scientist/orchestration/outputs.py prompts/active/method-critic.md prompts/active/visual-critic.md prompts/active/verifier.md prompts/active/memory-curator.md tests/test_orchestration_runtime.py
git commit -m "feat: add critique loop and bounded memory"
```

## Task 6: Migrate Benchmark Entry Points, Import, Scoring, And Docs

**Files:**
- Create: `results/configs/codex-multiagent-v1.yaml`
- Create: `results/configs/claude-multiagent-v1.yaml`
- Modify: `ai_data_scientist/cli/benchmark.py`
- Modify: `ai_data_scientist/experiments/importer.py`
- Modify: `reviewer/scorer.py`
- Modify: `README.md`
- Modify: `tests/test_run_benchmark.py`
- Modify: `tests/test_experiment_import.py`
- Delete: `harness/prompt_template.txt`
- Delete: `harness/run_codex.sh`
- Delete: `harness/run_claude.sh`
- Delete: `tests/test_benchmark_orchestrator.py`

- [ ] **Step 1: Write the failing benchmark and import tests**

```python
def test_benchmark_run_uses_new_multiagent_config_and_writes_canonical_artifacts(
    tmp_path: Path, monkeypatch
):
    _write_yaml(
        configs_dir / "codex-multiagent-v1.yaml",
        {
            "name": "codex-multiagent-v1",
            "roles": {
                "task_framer": {"backend": "claude_cli", "prompt": "prompts/active/task-framer.md"},
                "analysis_planner": {"backend": "claude_cli", "prompt": "prompts/active/analysis-planner.md"},
                "analysis_executor": {"backend": "codex_cli", "prompt": "prompts/active/analysis-executor.md"},
                "method_critic": {"backend": "claude_cli", "prompt": "prompts/active/method-critic.md"},
                "visual_critic": {"backend": "claude_cli", "prompt": "prompts/active/visual-critic.md"},
                "verifier": {"backend": "claude_cli", "prompt": "prompts/active/verifier.md"},
                "memory_curator": {"backend": "claude_cli", "prompt": "prompts/active/memory-curator.md"},
            },
            "runtime": {"max_revision_rounds": 1, "max_reframes": 1, "memory_curator": True},
        },
    )

    benchmark_cli.main()

    run_dir = runs_dir / "codex-multiagent-v1" / "multimodal"
    assert (run_dir / "artifacts" / "analysis" / "analysis_report.md").exists()
    assert (run_dir / "artifacts" / "verification" / "verification.json").exists()


def test_import_records_multiple_agent_runs_for_a_multiagent_case(tmp_path: Path):
    run_dir = tmp_path / "results" / "runs" / "codex-multiagent-v1" / "multimodal"
    (run_dir / "artifacts" / "analysis" / "analysis_report.md").parent.mkdir(parents=True, exist_ok=True)
    (run_dir / "artifacts" / "analysis" / "analysis_report.md").write_text("# Analysis\n")
    (run_dir / "artifacts" / "verification" / "verification.json").parent.mkdir(parents=True, exist_ok=True)
    (run_dir / "artifacts" / "verification" / "verification.json").write_text('{"verdict":"pass"}')
    (run_dir / "orchestration" / "transitions.jsonl").parent.mkdir(parents=True, exist_ok=True)
    (run_dir / "orchestration" / "transitions.jsonl").write_text(
        '{"role":"task_framer","invocation_id":"task-framer-0001"}\n'
        '{"role":"analysis_planner","invocation_id":"analysis-planner-0001"}\n'
        '{"role":"analysis_executor","invocation_id":"analysis-executor-0001"}\n'
    )

    manifest_dir = import_legacy_experiment(
        repo_root=tmp_path,
        experiment_id="exp_20260406_120000_multiagent",
        title="Multiagent import",
    )

    manifest = json.loads((manifest_dir / "manifest.json").read_text())
    assert len(manifest["agent_runs"]) == 3
```

- [ ] **Step 2: Run the benchmark and import test files**

Run: `uv run pytest tests/test_run_benchmark.py tests/test_experiment_import.py -v`

Expected: FAIL because the benchmark CLI still expects old config names and the importer still assumes one `agent_run` per case directory.

- [ ] **Step 3: Update the benchmark CLI and ship the first active configs**

```yaml
name: codex-multiagent-v1
description: External orchestrator with Codex execution
roles:
  task_framer:
    backend: claude_cli
    prompt: prompts/active/task-framer.md
    model: claude-opus-4-6
  analysis_planner:
    backend: claude_cli
    prompt: prompts/active/analysis-planner.md
    model: claude-opus-4-6
  analysis_executor:
    backend: codex_cli
    prompt: prompts/active/analysis-executor.md
    model: gpt-5.4
  method_critic:
    backend: claude_cli
    prompt: prompts/active/method-critic.md
    model: claude-opus-4-6
  visual_critic:
    backend: claude_cli
    prompt: prompts/active/visual-critic.md
    model: claude-opus-4-6
  verifier:
    backend: claude_cli
    prompt: prompts/active/verifier.md
    model: claude-opus-4-6
  memory_curator:
    backend: claude_cli
    prompt: prompts/active/memory-curator.md
    model: claude-opus-4-6
runtime:
  max_revision_rounds: 1
  max_reframes: 1
  memory_curator: true
```

```python
def run_workflow_for_dataset(config: dict, config_name: str, dataset_name: str, dataset_csv: Path) -> bool:
    run_results = RUNS_DIR / config_name / dataset_name
    run_results.mkdir(parents=True, exist_ok=True)
    return run_workflow(
        config=config,
        dataset_name=dataset_name,
        dataset_csv=dataset_csv,
        results_dir=run_results,
        root=ROOT,
    )
```

- [ ] **Step 4: Update importer and scorer for the canonical artifact tree**

```python
def _collect_case_artifacts(..., run_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file():
            continue
        if "invocations" in path.parts:
            continue
        artifact_type, role = _artifact_type_and_role(path)
        records.append(
            _build_artifact_record(
                repo_root=repo_root,
                experiment_id=experiment_id,
                config_snapshot_id=config_snapshot_id,
                path=path,
                artifact_type=artifact_type,
                role=role,
                case_id=case_id,
                workflow_run_id=workflow_run_id,
                agent_run_id=_agent_run_id_from_transition_log(path, run_dir),
            )
        )
    return records
```

```python
def _analysis_report_path(results_dir: Path) -> Path:
    return results_dir / "artifacts" / "analysis" / "analysis_report.md"


def _trace_path(results_dir: Path) -> Path:
    return results_dir / "orchestration" / "trace.jsonl"
```

- [ ] **Step 5: Update README and remove the legacy harness shims**

```markdown
### Workflow configs

The runtime now requires the external orchestrator config shape:

    name: codex-multiagent-v1
    roles:
      task_framer:
        backend: claude_cli
        prompt: prompts/active/task-framer.md
      analysis_executor:
        backend: codex_cli
        prompt: prompts/active/analysis-executor.md
    runtime:
      max_revision_rounds: 1
      max_reframes: 1
      memory_curator: true
```

- [ ] **Step 6: Run the targeted benchmark/import tests and then the full suite**

Run: `uv run pytest tests/test_run_benchmark.py tests/test_experiment_import.py -v`

Expected: PASS for benchmark CLI and importer tests.

Run: `uv run pytest tests/ -v`

Expected: PASS with `0 failed`.

- [ ] **Step 7: Commit**

```bash
git add ai_data_scientist/cli/benchmark.py ai_data_scientist/experiments/importer.py reviewer/scorer.py README.md results/configs/codex-multiagent-v1.yaml results/configs/claude-multiagent-v1.yaml tests/test_run_benchmark.py tests/test_experiment_import.py
git rm harness/prompt_template.txt harness/run_codex.sh harness/run_claude.sh tests/test_benchmark_orchestrator.py
git commit -m "refactor: migrate benchmark tooling to orchestrator v1"
```

## Coverage Notes

This plan covers the approved architecture spec sections as follows:

- isolated invocation workdirs and fresh sessions: Tasks 2 and 3
- deterministic profiling: Task 4
- split planning and execution roles: Task 4
- critics, verifier, bounded loop, and post-round memory: Task 5
- published-artifact-only continuity: Tasks 2 and 5
- benchmark/import/scoring migration: Task 6
- active prompts separated from historical prompt assets: Tasks 4 and 5
