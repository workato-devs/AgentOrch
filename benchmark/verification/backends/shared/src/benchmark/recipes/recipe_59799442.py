from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_59799442


RECIPE_ID = "59799442"
SEED_TYPE = "snowflake_product_lookup_table_reconcile_variant"
TRACK = "snowflake_lookup_table_product_sync"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
SNOWFLAKE_TABLE = "SALESFORCE.PRODUCT"
LOOKUP_TABLE_ID = "2343007"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("snowflake", "search_rows"),
    ("lookup_table", "get_entries"),
    ("workato_smart_list", "create_list"),
    ("workato_smart_list", "query_list"),
    ("lookup_table", "delete_entry"),
    ("lookup_table", "search_entries"),
    ("lookup_table", "update_entry"),
    ("lookup_table", "add_entry"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows",
    "lookup_table.get_entries",
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
    "lookup_table.delete_entry",
    "lookup_table.search_entries",
    "lookup_table.update_entry",
    "lookup_table.add_entry",
]
ALLOWED_TOOLS: list[str] = EXPECTED_RAW_TOOLS


def validate_59799442(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    snowflake_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if str(snowflake_input.get("table") or "") != SNOWFLAKE_TABLE:
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake table changed")
    smart_input = actions[2].get("input") if isinstance(actions[2].get("input"), dict) else {}
    if str(smart_input.get("list_name") or "") != "PRODUCTS":
        raise RuntimeError(f"recipe {RECIPE_ID} smart-list name changed")
    for action in actions[1:]:
        if action.get("provider") == "workato_smart_list":
            continue
        raw_input = action.get("input") if isinstance(action.get("input"), dict) else {}
        if str(raw_input.get("lookup_table_id") or "") != LOOKUP_TABLE_ID:
            raise RuntimeError(f"recipe {RECIPE_ID} lookup table id changed")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
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


def seed_59799442(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_59799442(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed")
    snowflake_seed = seed_in.get("snowflake")
    lookup_seed = seed_in.get("lookup_table")
    if not isinstance(snowflake_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.snowflake")
    if not isinstance(lookup_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.lookup_table")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger_input(ctx),
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "snowflake": deepcopy(snowflake_seed),
        "lookup_table": deepcopy(lookup_seed),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_59799442(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_59799442(raw)
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
    result["verifier"] = verify_59799442(result)
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


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("snowflake"), dict):
        out.update(ctx.tools.call("harness.snowflake.snapshot", {}))
    if isinstance(seed.get("lookup_table"), dict):
        out.update(ctx.tools.call("harness.lookup_table.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
