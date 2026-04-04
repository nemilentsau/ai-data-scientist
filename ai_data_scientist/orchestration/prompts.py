"""Prompt loading and step rendering."""

from __future__ import annotations

from pathlib import Path

from ai_data_scientist.orchestration.models import WorkflowStep


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
