from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_123071571


RECIPE_ID = "123071571"
SEED_TYPE = "recipe_function_slack_message_log_variant"
TRACK = "workato_controlled_lookup_message_log"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
LOOKUP_TABLE_ID = "3145890"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("lookup_table", "search_entries"),
    ("lookup_table", "add_entry"),
    ("workato_recipe_function", "return_result"),
    ("json_parser", "parse_json"),
    ("workato_recipe_function", "return_result"),
    ("lookup_table", "delete_entry"),
    ("workato_recipe_function", "return_result"),
    ("lookup_table", "update_entry"),
    ("workato_recipe_function", "return_result"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "lookup_table.add_entry",
    "workato_recipe_function.return_result",
    "workato_runtime.parse_json",
    "lookup_table.delete_entry",
    "lookup_table.update_entry",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "lookup_table.add_entry",
    "lookup_table.delete_entry",
    "lookup_table.update_entry",
    "workato_recipe_function.return_result",
]


def validate_123071571(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    lookup_actions = [action for action in actions if action.get("provider") == "lookup_table"]
    for action in lookup_actions:
        raw_input = action.get("input") or {}
        if str(raw_input.get("lookup_table_id") or "") != LOOKUP_TABLE_ID:
            raise RuntimeError(f"recipe {RECIPE_ID} lookup table id changed")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "lookup_table_id": LOOKUP_TABLE_ID,
        "actions": [
            {
                "number": action.get("number"),
                "provider": action.get("provider"),
                "name": action.get("name"),
                "as": action.get("as"),
            }
            for action in actions
        ],
    }


def seed_123071571(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_123071571(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if not isinstance(seed_in.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.lookup_table")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "raw_validation": validation,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if isinstance(data.get("expect"), dict):
        out["expect"] = deepcopy(data["expect"])
    for key, value in seed_in.items():
        if isinstance(value, dict):
            out[str(key)] = deepcopy(value)
    for key in ("force_action_error", "job_context"):
        if isinstance(data.get(key), dict):
            out[key] = deepcopy(data[key])
    return attach_variant(out, ctx)


def run_123071571(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_123071571(raw)
    trigger = seed.get("trigger")
    if not isinstance(trigger, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing trigger object")
    _require_trigger(trigger)
    expect = seed.get("expect") if isinstance(seed.get("expect"), dict) else {}
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
            "trigger": trigger,
            "track": seed.get("track"),
            "expect": expect,
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_123071571(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _require_trigger(trigger: dict[str, Any]) -> None:
    params = trigger.get("parameters")
    if not isinstance(params, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger.parameters must be an object")
    for field in ("primary_id", "operation"):
        if params.get(field) in (None, ""):
            raise RuntimeError(f"recipe {RECIPE_ID} trigger.parameters.{field} must be non-empty")


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("lookup_table"), dict):
        out.update(ctx.tools.call("harness.lookup_table.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
