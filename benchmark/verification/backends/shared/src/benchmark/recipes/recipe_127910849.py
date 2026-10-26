from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_127910849
from .salesforce_recipe_utils import collect_actions, copy_expect


RECIPE_ID = "127910849"
SEED_TYPE = "genie_live_jira_issue_create_variant"
TRACK = "live_jira_genie_create"
TRIGGER_PROVIDER = "workato_genie"
TRIGGER_NAME = "start_workflow"
EXPECTED_ACTIONS = [
    ("jira", "create_issue"),
    ("workato_genie", "workflow_return_result"),
]
EXPECTED_RAW_TOOLS = ["jira.create_issue", "workato_genie.workflow_return_result"]
ALLOWED_TOOLS = ["jira.create_issue", "workato_genie.workflow_return_result"]


def validate_127910849(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    create_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if create_input.get("project_issuetype") != "GL--Task":
        raise RuntimeError(f"recipe {RECIPE_ID} Jira project/type changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_127910849(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_127910849(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters") if isinstance(trigger.get("parameters"), dict) else None
    if not isinstance(parameters, dict) or not parameters.get("summary"):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing parameters.summary")
    out = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": deepcopy(trigger),
        "track": data.get("track"),
        "expect": copy_expect(data),
        "raw_validation": validation,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_127910849(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_127910849(raw)
    raw_execution = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
    finally:
        # Cleanup runs even when replay crashes: a leaked live Jira issue
        # would poison later runs (benchmark cleanup policy cleanup
        # principle). On a crash the created issue is recovered from the
        # registry call log instead of the missing trace.
        cleanup_response = _cleanup_issue(raw_execution, ctx)
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "cleanup_response": cleanup_response,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_127910849(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _cleanup_issue(raw_execution: dict[str, Any] | None, ctx: RecipeContext) -> dict[str, Any]:
    rows = (raw_execution or {}).get("trace") or ctx.tools.call_log({"jira.create_issue"})
    for row in rows:
        if isinstance(row, dict) and row.get("tool") == "jira.create_issue":
            result = row.get("result") if isinstance(row.get("result"), dict) else {}
            key = str(result.get("key") or "")
            if key:
                return ctx.tools.call("jira.delete_issue", {"key": key})
    return {}


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"number": a.get("number"), "provider": a.get("provider"), "name": a.get("name"), "as": a.get("as")} for a in actions]
