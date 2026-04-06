"""Workflow execution entrypoint."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from ai_data_scientist.orchestration.adapters.base import BackendAdapter
from ai_data_scientist.orchestration.adapters.claude_cli import ClaudeCliAdapter
from ai_data_scientist.orchestration.adapters.codex_cli import CodexCliAdapter
from ai_data_scientist.orchestration.config import normalize_workflow_config
from ai_data_scientist.orchestration.ledgers import (
    collect_task5_feedback_inputs,
    initialize_ledgers,
    read_verification_verdict,
    role_memory_paths,
)
from ai_data_scientist.orchestration.models import (
    PublishContract,
    WorkflowExecutionError,
)
from ai_data_scientist.orchestration.outputs import publish_declared_outputs, stage_declared_outputs
from ai_data_scientist.orchestration.profile import profile_dataset
from ai_data_scientist.orchestration.prompts import render_role_prompt
from ai_data_scientist.orchestration.workspace import (
    create_invocation_context,
    prepare_run_context,
    resolve_role_inputs,
)

BACKEND_ADAPTERS: dict[str, type[BackendAdapter]] = {
    "codex_cli": CodexCliAdapter,
    "claude_cli": ClaudeCliAdapter,
}

ROLE_ORDER = ("task_framer", "analysis_planner", "analysis_executor")
ORCHESTRATOR_BACKEND_LABEL = "external_orchestrator_v1"
TASK5_CRITIC_ORDER = ("method_critic", "visual_critic")
ROLE_OUTPUT_CONTRACTS: dict[str, PublishContract] = {
    "task_framer": PublishContract(role="task_framer", declared_outputs=("framing.json",)),
    "analysis_planner": PublishContract(
        role="analysis_planner",
        declared_outputs=("analysis_plan.md", "hypotheses.json", "experiment_plan.json"),
    ),
    "analysis_executor": PublishContract(
        role="analysis_executor",
        declared_outputs=(
            "analysis_report.md",
            "findings.json",
            "claim_evidence_map.json",
            "plots",
            "stats",
        ),
    ),
    "method_critic": PublishContract(role="method_critic", declared_outputs=("critique.md",)),
    "visual_critic": PublishContract(role="visual_critic", declared_outputs=("critique.md",)),
    "verifier": PublishContract(
        role="verifier",
        declared_outputs=("verification.json",),
    ),
    "memory_curator": PublishContract(
        role="memory_curator",
        declared_outputs=("memory/task_framer.md", "memory/analysis_planner.md"),
    ),
}


def get_backend_adapter(backend: str, root: Path) -> BackendAdapter:
    """Instantiate a backend adapter from the registry."""
    adapter_cls = BACKEND_ADAPTERS.get(backend)
    if adapter_cls is None:
        raise ValueError(f"Unsupported backend: {backend}")
    return adapter_cls(root)


def _prepare_backend_adapter(
    *,
    backend: str,
    root: Path,
    context,
    adapter_cache: dict[str, BackendAdapter],
    prepared_backends: set[str],
) -> BackendAdapter:
    adapter = adapter_cache.get(backend)
    if adapter is None:
        adapter = get_backend_adapter(backend, root)
        adapter_cache[backend] = adapter
    if backend not in prepared_backends:
        adapter.prepare_run(context)
        prepared_backends.add(backend)
    return adapter


def _merge_unique_paths(*groups: list[Path]) -> list[Path]:
    merged: list[Path] = []
    seen: set[Path] = set()
    for group in groups:
        for path in group:
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            merged.append(path)
    return merged


def _write_invocation_manifest(*, invocation, role, result) -> None:
    payload = {
        "invocation_id": invocation.invocation_id,
        "role": role.role,
        "backend": role.backend,
        "model": role.model or None,
        "status": result.status,
    }
    invocation.manifest_path.write_text(json.dumps(payload, indent=2))


def _run_role(
    *,
    root: Path,
    results_dir: Path,
    context,
    role_name: str,
    adapter_cache: dict[str, BackendAdapter],
    prepared_backends: set[str],
    role_memory: Path | None = None,
    artifact_inputs: list[Path] | None = None,
) -> None:
    role = context.spec.roles[role_name]
    resolved_inputs = artifact_inputs if artifact_inputs is not None else resolve_role_inputs(results_dir, role_name)
    invocation = create_invocation_context(
        run_dir=results_dir,
        role=role,
        artifact_inputs=resolved_inputs,
    )
    invocation_inputs = [
        invocation.input_dir / source.relative_to(results_dir)
        for source in resolved_inputs
    ]
    prompt = render_role_prompt(
        root=root,
        role=role,
        artifact_inputs=invocation_inputs,
        role_memory=role_memory,
    )
    adapter = _prepare_backend_adapter(
        backend=role.backend,
        root=root,
        context=context,
        adapter_cache=adapter_cache,
        prepared_backends=prepared_backends,
    )
    result = adapter.invoke(role, context, invocation, prompt)
    _write_invocation_manifest(invocation=invocation, role=role, result=result)
    if result.status != "completed":
        raise WorkflowExecutionError(
            f"Role '{role_name}' finished with status '{result.status}'."
        )
    stage_declared_outputs(
        invocation=invocation,
        contract=ROLE_OUTPUT_CONTRACTS[role_name],
    )
    publish_declared_outputs(
        run_dir=results_dir,
        invocation=invocation,
        contract=ROLE_OUTPUT_CONTRACTS[role_name],
    )
    context.completed_steps.append(role_name)


def _run_task4_slice(
    *,
    root: Path,
    results_dir: Path,
    context,
    adapter_cache: dict[str, BackendAdapter],
    prepared_backends: set[str],
    memory_paths: dict[str, Path],
) -> None:
    for role_name in ROLE_ORDER:
        _run_role(
            root=root,
            results_dir=results_dir,
            context=context,
            role_name=role_name,
            adapter_cache=adapter_cache,
            prepared_backends=prepared_backends,
            role_memory=memory_paths.get(role_name),
        )


def _run_task5_bounded_loop(
    *,
    root: Path,
    results_dir: Path,
    context,
    adapter_cache: dict[str, BackendAdapter],
    prepared_backends: set[str],
    memory_paths: dict[str, Path],
) -> None:
    task5_feedback_inputs: list[Path] = []
    _run_role(
        root=root,
        results_dir=results_dir,
        context=context,
        role_name="task_framer",
        adapter_cache=adapter_cache,
        prepared_backends=prepared_backends,
        role_memory=memory_paths.get("task_framer"),
    )

    while True:
        for role_name in ("analysis_planner", "analysis_executor"):
            base_inputs = resolve_role_inputs(results_dir, role_name)
            _run_role(
                root=root,
                results_dir=results_dir,
                context=context,
                role_name=role_name,
                adapter_cache=adapter_cache,
                prepared_backends=prepared_backends,
                role_memory=memory_paths.get(role_name),
                artifact_inputs=_merge_unique_paths(base_inputs, task5_feedback_inputs),
            )

        critic_inputs = resolve_role_inputs(results_dir, "method_critic")
        for role_name in TASK5_CRITIC_ORDER:
            _run_role(
                root=root,
                results_dir=results_dir,
                context=context,
                role_name=role_name,
                adapter_cache=adapter_cache,
                prepared_backends=prepared_backends,
                artifact_inputs=critic_inputs,
            )

        verifier_inputs = resolve_role_inputs(results_dir, "verifier")
        _run_role(
            root=root,
            results_dir=results_dir,
            context=context,
            role_name="verifier",
            adapter_cache=adapter_cache,
            prepared_backends=prepared_backends,
            artifact_inputs=verifier_inputs,
        )

        if context.spec.runtime.memory_curator and "memory_curator" in context.spec.roles:
            _run_role(
                root=root,
                results_dir=results_dir,
                context=context,
                role_name="memory_curator",
                adapter_cache=adapter_cache,
                prepared_backends=prepared_backends,
            )

        verdict = read_verification_verdict(results_dir)
        task5_feedback_inputs = collect_task5_feedback_inputs(results_dir)
        if verdict == "pass":
            return
        if verdict == "revise" and context.revision_rounds < context.spec.runtime.max_revision_rounds:
            context.revision_rounds += 1
            continue
        if verdict == "reframe" and context.reframes < context.spec.runtime.max_reframes:
            context.reframes += 1
            framer_inputs = _merge_unique_paths(
                resolve_role_inputs(results_dir, "task_framer"),
                task5_feedback_inputs,
            )
            _run_role(
                root=root,
                results_dir=results_dir,
                context=context,
                role_name="task_framer",
                adapter_cache=adapter_cache,
                prepared_backends=prepared_backends,
                role_memory=memory_paths.get("task_framer"),
                artifact_inputs=framer_inputs,
            )
            continue
        raise WorkflowExecutionError(
            f"Verifier verdict '{verdict}' exceeded the configured revision and reframe limits."
        )


def run_workflow(
    *,
    config: dict[str, Any],
    dataset_name: str,
    dataset_csv: Path,
    results_dir: Path,
    root: Path,
) -> bool:
    """Run the deterministic orchestrator slice against one dataset."""
    spec = normalize_workflow_config(config)
    missing_roles = [role_name for role_name in ROLE_ORDER if role_name not in spec.roles]
    if missing_roles:
        raise ValueError(
            "Orchestrator configs must declare task_framer, analysis_planner, and analysis_executor."
        )
    task5_mode = any(role_name in spec.roles for role_name in ("method_critic", "visual_critic", "verifier"))
    if task5_mode and not all(
        role_name in spec.roles for role_name in ("method_critic", "visual_critic", "verifier")
    ):
        raise ValueError(
            "Task 5 runtime configs must declare method_critic, visual_critic, and verifier."
        )
    if task5_mode and spec.runtime.memory_curator and "memory_curator" not in spec.roles:
        raise ValueError(
            "Task 5 runtime configs with memory curation enabled must declare memory_curator."
        )

    context = prepare_run_context(
        root=root,
        dataset_name=dataset_name,
        dataset_csv=dataset_csv,
        results_dir=results_dir,
        backend=ORCHESTRATOR_BACKEND_LABEL,
    )
    context.spec = spec

    adapter_cache: dict[str, BackendAdapter] = {}
    prepared_backends: set[str] = set()
    memory_paths = role_memory_paths(results_dir)
    initialize_ledgers(results_dir)
    succeeded = False

    try:
        profile_dataset(dataset_csv=dataset_csv, run_dir=results_dir)
        if task5_mode:
            _run_task5_bounded_loop(
                root=root,
                results_dir=results_dir,
                context=context,
                adapter_cache=adapter_cache,
                prepared_backends=prepared_backends,
                memory_paths=memory_paths,
            )
        else:
            _run_task4_slice(
                root=root,
                results_dir=results_dir,
                context=context,
                adapter_cache=adapter_cache,
                prepared_backends=prepared_backends,
                memory_paths=memory_paths,
            )
        context.status = "completed"
        succeeded = True
    except (ValueError, WorkflowExecutionError) as exc:
        context.status = "failed"
        context.error = str(exc)
    finally:
        context.cleaned_up = True
        shutil.rmtree(context.work_dir, ignore_errors=True)

    return succeeded
