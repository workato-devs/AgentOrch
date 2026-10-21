from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_131314498
from .salesforce_recipe_utils import collect_actions


RECIPE_ID = "131314498"
SEED_TYPE = "slack_dynamic_menu_aws_country_smart_list_variant"
TRACK = "workato_lookup_smart_list_slack_dynamic_menu"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "dynamic_menu"
LOOKUP_TABLE_ID = "4511400"
EXPECTED_ACTIONS = [
    ("lookup_table", "get_entries"),
    ("workato_variable", "declare_list"),
    ("workato_smart_list", "create_list"),
    ("workato_smart_list", "query_list"),
    ("slack_bot", "generate_menu_options"),
]
EXPECTED_RAW_TOOLS = [
    "lookup_table.get_entries",
    "workato_runtime.declare_list",
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
    "slack_bot.generate_menu_options",
]
ALLOWED_TOOLS = [
    "lookup_table.get_entries",
    "slack_bot.generate_menu_options",
]


def validate_131314498(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    lookup_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if lookup_input.get("lookup_table_id") != LOOKUP_TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} lookup table changed")
    smart_query = str((actions[3].get("input") or {}).get("sql") or "")
    if "LIKE" not in smart_query or "typeahead" not in smart_query:
        raise RuntimeError(f"recipe {RECIPE_ID} smart-list typeahead query changed")
    menu_input = actions[4].get("input") if isinstance(actions[4].get("input"), dict) else {}
    if "country" not in str(menu_input.get("options") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} menu option mapping changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_131314498(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_131314498(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if not isinstance(trigger.get("typeahead"), dict) or trigger["typeahead"].get("value") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing typeahead.value")
    seed_in = data.get("seed")
    lookup_seed = seed_in.get("lookup_table") if isinstance(seed_in, dict) else None
    if not isinstance(lookup_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.lookup_table")
    if LOOKUP_TABLE_ID not in (lookup_seed.get("tables") or {}):
        raise RuntimeError(f"recipe {RECIPE_ID} lookup seed missing table {LOOKUP_TABLE_ID}")
    out = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "lookup_table": deepcopy(lookup_seed),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_131314498(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_131314498(raw)
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
    result["verifier"] = verify_131314498(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    if isinstance(seed.get("lookup_table"), dict):
        return ctx.tools.call("harness.lookup_table.snapshot", {})
    return {}


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"number": action.get("number"), "provider": action.get("provider"), "name": action.get("name"), "as": action.get("as")} for action in actions]
