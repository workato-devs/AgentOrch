"""Dependency-free smoke-test adapter; replace it with a real model adapter."""

from __future__ import annotations

from typing import Any


class ExampleAdapter:
    def propose_plan(self, task: dict[str, Any]) -> list[dict[str, Any]]:
        # Deliberately empty: confirms data loading, run records, and scoring
        # without pretending to solve a task or accessing private artifacts.
        return []

    def start(self, task: dict[str, Any], *, mode: str,
              tool_specs: list[dict[str, Any]] | None = None) -> None:
        self.mode = mode

    def act(self, observation: dict[str, Any] | None) -> dict[str, Any]:
        return {"final_answer": {"status": "example adapter stopped"}}


def build() -> ExampleAdapter:
    return ExampleAdapter()
