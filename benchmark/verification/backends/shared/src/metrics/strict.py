"""Canonical source-fixture integrity checks.

``strict_pass`` requires exact tool sequence and raw canonical expected
argument values. Connector/query/result semantic equivalences are retained as
diagnostics here because this module validates serialized fixture expectations,
not two connector executions. Public agent evaluation compares SQL/SOQL by
runtime result/state in ``task.run_eval``. Replay-only checks do not apply.
"""

from __future__ import annotations

import math
from typing import Any

from benchmark.verifier import _check, _strict_tool_checks


STRICT_COMPONENTS = (
    "tool_sequence",
    "tool_call",
    "tool_argument",
    "tool_argument_semantic",
    "result_count",
    "response",
    "write_state",
    "other",
)


def _check_component(name: str) -> str:
    """Assign one strict verifier check to one non-overlapping metric axis."""

    if name == "tool_sequence_matches_expected":
        return "tool_sequence"
    if name.endswith("_called_expected_tool"):
        return "tool_call"
    if "_raw_args_contain_expected_fields" in name:
        return "tool_argument"
    if (
        "_args_contain_expected_fields" in name
        or "_snowflake_sql_result_semantics_matches" in name
        or "_snowflake_sql_execution_equivalence_matches" in name
    ):
        return "tool_argument_semantic"
    if name.endswith("_posted_expected_text") or name.endswith(
        "_used_override_channel"
    ):
        return "tool_argument"
    if name.endswith("_result_count_matches"):
        return "result_count"
    if any(
        marker in name
        for marker in (
            "_returned_expected_options",
            "_options_contain_expected_items",
            "_returned_expected_response",
            "_returned_expected_http_status",
            "_response_contains_expected_fields",
            "_returned_expected_result",
            "_result_contains_expected_fields",
        )
    ):
        return "response"
    if any(
        marker in name
        for marker in (
            "_workato_db_final_row_matches",
            "_upsert_created_flag_matches",
            "_lookup_final_entry_matches",
            "_snowflake_expected_row_",
            "_snowflake_applied_row_",
            "_snowflake_final_row_",
            "_snowflake_upsert_count_matches",
            "_snowflake_created_count_matches",
            "_snowflake_updated_count_matches",
            "_snowflake_updated_columns_match",
            "_salesforce_update_succeeded",
            "_salesforce_final_fields_match_update_args",
            "_salesforce_final_fields_contain_expected_fields",
        )
    ):
        return "write_state"
    return "other"


def _component_metrics(checks: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {
        component: [] for component in STRICT_COMPONENTS
    }
    for check in checks:
        grouped[_check_component(str(check.get("name") or ""))].append(check)

    metrics: dict[str, Any] = {}
    for component, component_checks in grouped.items():
        checked = bool(component_checks)
        metrics[f"{component}_checked"] = checked
        metrics[f"{component}_pass"] = (
            all(bool(check.get("ok")) for check in component_checks)
            if checked
            else None
        )
        metrics[f"{component}_check_count"] = len(component_checks)
        metrics[f"{component}_passed_check_count"] = sum(
            1 for check in component_checks if check.get("ok") is True
        )
    return metrics


def expected_tools(expect: dict[str, Any]) -> list[str]:
    tools = expect.get("tools")
    if isinstance(tools, list):
        return [str(t) for t in tools]
    items = expect.get("tool_expectations")
    if isinstance(items, list):
        return [str(item.get("tool")) for item in items if isinstance(item, dict)]
    return []


def gold_action_budget(expect: dict[str, Any]) -> int:
    """Gold-trace action count estimate (the efficient reference path). Never
    use this directly as the agent's budget — the gold trace is an efficient
    reference implementation, not the minimum information-gathering process
    available to an agent. Use compute_action_budget."""
    count = expect.get("executed_action_count")
    count = int(count) if isinstance(count, int) and not isinstance(count, bool) else 0
    return max(count, len(expected_tools(expect)), 1)


def compute_action_budget(expect: dict[str, Any], required_system_count: int = 0) -> int:
    """Primary (1.0x) action budget: gold actions plus room to orient — an
    agent may need reads/schema checks the gold recipe never issued. Short
    recipes get an absolute floor (+3); longer ones scale (1.5x); multi-system
    tasks get at least one action per system plus slack."""
    gold_actions = gold_action_budget(expect)
    return max(
        gold_actions + 3,
        math.ceil(gold_actions * 1.5),
        int(required_system_count) + 2,
    )


def evaluate(expect: dict[str, Any], tool_calls: list[dict[str, Any]],
             final_snapshot: dict[str, Any],
             evaluation_time: str | None = None) -> dict[str, Any]:
    if not isinstance(expect, dict) or (
            not isinstance(expect.get("tools"), list)
            and not isinstance(expect.get("tool_expectations"), list)):
        raise RuntimeError("variant expect block missing tools/tool_expectations; "
                           "cannot score an agent run without ground truth")
    tools = expected_tools(expect)
    actual = [str(call.get("tool") or "") for call in tool_calls]
    checks = [_check(
        "tool_sequence_matches_expected",
        actual == tools,
        {"expected_tools": tools, "actual_tools": actual},
    )]
    details = {
        "expect": expect,
        "final_snapshot": final_snapshot or {},
        "evaluation_time": evaluation_time,
    }
    for idx, item in enumerate(expect.get("tool_expectations") or []):
        if not isinstance(item, dict):
            checks.append(_check("tool_expectation_is_object", False,
                                 {"index": idx, "value": item}))
            continue
        checks.extend(_strict_tool_checks(idx, item, tool_calls, details))
    return {
        "strict_pass": all(
            c["ok"] or c.get("diagnostic") is True for c in checks
        ),
        "component_metrics": _component_metrics(checks),
        "checks": checks,
    }
