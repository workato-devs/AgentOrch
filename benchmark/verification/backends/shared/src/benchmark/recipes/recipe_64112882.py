from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_64112882
from .salesforce_recipe_utils import collect_actions, ground_truth


RECIPE_ID = "64112882"
SEED_TYPE = "api_platform_open_invoices_variant"
TRACK = "workato_api_open_invoices"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TABLE_ID = "1670"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_db_table", "get_records"),
    ("workato_api_platform", "return_response"),
    ("workato_api_platform", "return_response"),
]
EXPECTED_RAW_TOOLS = ["workato_db_table.get_records", "workato_api_platform.return_response"]
ALLOWED_TOOLS = ["workato_db_table.get_records", "workato_api_platform.return_response"]


def validate_64112882(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    raw_input = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    if "oppty_id" not in str(raw_input):
        raise RuntimeError(f"recipe {RECIPE_ID} API request schema changed")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    get_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if str(get_input.get("table_id") or "") != TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} Workato table id changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_64112882(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_64112882(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    request = trigger.get("request") if isinstance(trigger.get("request"), dict) else {}
    if not request.get("oppty_id"):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing request.oppty_id")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or not isinstance(seed_in.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.workato_db_table")
    expect = data.get("expect")
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} missing expect object")
    out = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(expect),
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "raw_validation": validation,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_64112882(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_64112882(raw)
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
            "ground_truth": ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_64112882(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    if isinstance(seed.get("workato_db_table"), dict):
        return ctx.tools.call("harness.workato_db_table.snapshot", {})
    return {}


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"number": action.get("number"), "provider": action.get("provider"), "name": action.get("name"), "as": action.get("as")} for action in actions]
