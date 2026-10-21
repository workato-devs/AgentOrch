from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

ToolFn = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    expose_to_agent: bool = True


@dataclass(frozen=True)
class ToolCall:
    tool: str
    args: dict[str, Any]
    result: dict[str, Any]


@dataclass
class ToolRegistry:
    _tools: dict[str, ToolFn] = field(default_factory=dict)
    _specs: dict[str, ToolSpec] = field(default_factory=dict)
    _calls: list[ToolCall] = field(default_factory=list)
    _forced_error: dict[str, Any] | None = None
    _tool_attempt_counts: dict[str, int] = field(default_factory=dict)

    def configure_forced_error(
        self,
        forced_error: dict[str, Any] | None,
    ) -> None:
        self._forced_error = (
            dict(forced_error)
            if isinstance(forced_error, dict)
            else None
        )

    @staticmethod
    def _contains_subset(actual: Any, expected: Any) -> bool:
        if isinstance(expected, dict):
            return isinstance(actual, dict) and all(
                key in actual
                and ToolRegistry._contains_subset(actual[key], value)
                for key, value in expected.items()
            )
        if isinstance(expected, list):
            return isinstance(actual, list) and all(
                any(
                    ToolRegistry._contains_subset(candidate, wanted)
                    for candidate in actual
                )
                for wanted in expected
            )
        return actual == expected

    def register(
        self,
        name: str,
        fn: ToolFn,
        *,
        description: str,
        input_schema: dict[str, Any],
        expose_to_agent: bool = True,
    ) -> None:
        if name in self._tools:
            raise RuntimeError(f"tool already registered: {name}")
        self._tools[name] = fn
        self._specs[name] = ToolSpec(
            name=name,
            description=description,
            input_schema=input_schema,
            expose_to_agent=expose_to_agent,
        )

    def call(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name not in self._tools:
            raise RuntimeError(f"tool not registered: {name}")
        if not isinstance(args, dict):
            raise RuntimeError(f"tool args must be an object: {name}")
        attempt = self._tool_attempt_counts.get(name, 0) + 1
        self._tool_attempt_counts[name] = attempt
        forced = self._forced_error or {}
        selector = forced.get("args_contains") or {}
        occurrence = forced.get("occurrence_index")
        if (
            str(forced.get("tool") or "") == name
            and (
                (
                    isinstance(selector, dict)
                    and bool(selector)
                    and self._contains_subset(args, selector)
                )
                or (
                    not selector
                    and isinstance(occurrence, int)
                    and occurrence == attempt
                )
            )
        ):
            raise RuntimeError(
                str(
                    forced.get("error")
                    or "simulated connector failure"
                )
            )
        # Connector adapters may normalize logical arguments into the
        # physical invocation they actually issue (for example, routing a
        # configured Slack channel through the benchmark override).  Keep one
        # private copy so the trajectory records that physical invocation.
        call_args = dict(args)
        try:
            result = self._tools[name](call_args)
        except RuntimeError:
            raise
        except Exception as exc:  # noqa: BLE001 — fail closed at the tool boundary
            # Any exception a tool implementation raises on agent input must
            # surface as a failed tool call the agent can react to, never
            # crash the evaluator. Weak models exercise argument shapes
            # strong models never produce (string limits, missing SQL
            # bindings, list-shaped records); a genuine harness defect shows
            # up as an elevated failed-call rate in the health roll-up
            # rather than a dead job.
            raise RuntimeError(
                f"invalid arguments for {name}: {type(exc).__name__}: {exc}"
            ) from exc
        if not isinstance(result, dict):
            raise RuntimeError(f"tool returned non-object result: {name}")
        self._calls.append(
            ToolCall(tool=name, args=dict(call_args), result=dict(result))
        )
        return result

    def exposed_specs(self, names: set[str] | None = None) -> list[dict[str, Any]]:
        return [
            {
                "name": spec.name,
                "description": spec.description,
                "input_schema": spec.input_schema,
            }
            for spec in self._specs.values()
            if spec.expose_to_agent and (names is None or spec.name in names)
        ]

    def call_log(self, names: set[str] | None = None) -> list[dict[str, Any]]:
        return [
            {"tool": call.tool, "args": call.args, "result": call.result}
            for call in self._calls
            if names is None or call.tool in names
        ]

    def call_log_excluding(self, names: set[str]) -> list[dict[str, Any]]:
        return [
            {"tool": call.tool, "args": call.args, "result": call.result}
            for call in self._calls
            if call.tool not in names
        ]
