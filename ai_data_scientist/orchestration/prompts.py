"""Prompt loading and step rendering."""

from __future__ import annotations

from pathlib import Path

from ai_data_scientist.orchestration.models import RoleSpec, WorkflowStep


def load_prompt_text(root: Path, prompt_ref: str) -> str:
    """Resolve a prompt reference as a repo-relative file or inline prompt."""
    prompt_path = Path(prompt_ref)
    if not prompt_path.is_absolute():
        prompt_path = root / prompt_path
    if prompt_path.exists():
        return prompt_path.read_text()
    return prompt_ref


def render_step_prompt(
    *,
    root: Path,
    step: WorkflowStep,
    image_paths: list[Path],
    attachment_mode: str,
) -> str:
    """Compatibility wrapper for the legacy workflow runner."""
    del attachment_mode
    role = RoleSpec(
        role=step.role,
        backend="",
        prompt=step.prompt,
        model=step.model,
        tools=step.tools,
        max_turns=step.max_turns,
    )
    return render_role_prompt(
        root=root,
        role=role,
        artifact_inputs=image_paths,
        role_memory=None,
    )


def render_role_prompt(
    *,
    root: Path,
    role: RoleSpec,
    artifact_inputs: list[Path],
    role_memory: Path | None,
) -> str:
    """Load a role prompt and prepend published artifacts plus optional role memory."""
    prompt = load_prompt_text(root, role.prompt).strip()

    artifact_lines = []
    for path in artifact_inputs:
        if path.is_absolute():
            try:
                display_path = path.relative_to(root)
            except ValueError:
                display_path = path
        else:
            display_path = path
        artifact_lines.append(f"- {display_path}")

    if not artifact_lines:
        artifact_lines.append("- (none)")

    prefix = ""
    if role_memory is not None and role_memory.exists():
        memory_text = role_memory.read_text().strip()
        if memory_text:
            prefix += f"Role memory for this invocation:\n{memory_text}\n\n"

    prefix += (
        "Published input artifacts for this invocation:\n"
        f"{'\n'.join(artifact_lines)}\n\n"
    )
    return prefix + prompt
