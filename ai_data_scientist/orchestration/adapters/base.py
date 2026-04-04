"""Backend adapter interface."""

from __future__ import annotations

from pathlib import Path

from ai_data_scientist.orchestration.models import (
    BackendCapabilities,
    RunContext,
    SessionHandle,
    WorkflowStep,
)


class BackendAdapter:
    """Base backend adapter."""

    backend_name: str = ""

    def __init__(self, root: Path):
        self.root = root

    def capabilities(self) -> BackendCapabilities:
        raise NotImplementedError

    def prepare_context(self, context: RunContext) -> None:
        """Mutate the run context with backend-specific environment setup."""

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
