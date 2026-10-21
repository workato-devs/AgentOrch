from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_130070527


RECIPE_ID = "130070527"
SEED_TYPE = "genie_workato_db_idea_add_variant"
TRACK = "workato_genie_workato_db_add"
TRIGGER_PROVIDER = "workato_genie"
TRIGGER_NAME = "start_workflow"
TABLE_ID = "55027"
EXPECTED_SUCCESS_ACTIONS = [
    ("workato_db_table", "add_record"),
    ("workato_genie", "workflow_return_result"),
]
EXPECTED_RAW_TOOLS = [
    "workato_db_table.add_record",
    "workato_genie.workflow_return_result",
]
ALLOWED_TOOLS = ["workato_db_table.add_record", "workato_genie.workflow_return_result"]
REQUIRED_PARAMETERS = ("title", "idea", "business_use_case", "user_painpoint", "workarounds")


def validate_130070527(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_success_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_SUCCESS_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} success action sequence changed: {actual}")
    add_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if str(add_input.get("table_id") or "") != TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} Workato DB table changed")
    for key in REQUIRED_PARAMETERS:
        if key not in str(add_input):
            raise RuntimeError(f"recipe {RECIPE_ID} add-record mapping no longer references parameters.{key}")
    if "user_email" not in str(add_input) or "call_id" not in str(add_input):
        raise RuntimeError(f"recipe {RECIPE_ID} add-record mapping no longer references Genie context")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_130070527(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130070527(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters") if isinstance(trigger.get("parameters"), dict) else None
    context = trigger.get("context") if isinstance(trigger.get("context"), dict) else None
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing parameters object")
    for key in REQUIRED_PARAMETERS:
        if key not in parameters:
            raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter missing {key}")
    if not isinstance(context, dict) or "user_email" not in context or "call_id" not in context:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger context missing user_email or call_id")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or not isinstance(seed_in.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.workato_db_table")
    out = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_130070527(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130070527(raw)
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = _snapshot(ctx, seed)
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
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_130070527(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _collect_success_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict) or child.get("keyword") == "catch":
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_success_actions(child))
    return found


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    if isinstance(seed.get("workato_db_table"), dict):
        return ctx.tools.call("harness.workato_db_table.snapshot", {})
    return {}


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"number": a.get("number"), "provider": a.get("provider"), "name": a.get("name"), "as": a.get("as")} for a in actions]
