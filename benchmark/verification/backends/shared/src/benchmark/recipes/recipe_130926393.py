from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_130926393
from .salesforce_recipe_utils import collect_actions


RECIPE_ID = "130926393"
SEED_TYPE = "salesforce_closed_opportunity_workato_db_delete_date_variant"
TRACK = "workato_db_salesforce_closed_opportunity_tracking"
TRIGGER_PROVIDER = "salesforce"
TRIGGER_NAME = "updated_custom_object"
TABLE_ID = "46815"
OPPORTUNITY_FIELD = "ca9edae0_2cda_4c9f_ba6d_0f6c46d3833a"
DELETE_DATE_FIELD = "39f0b478_001e_48e6_bc84_5485aae16b03"
EXPECTED_ACTIONS = [
    ("workato_db_table", "get_records"),
    ("workato_db_table", "update_record"),
    ("workato_db_table", "update_record"),
]
EXPECTED_RAW_TOOLS = [
    "workato_db_table.get_records",
    "workato_db_table.update_record",
]
ALLOWED_TOOLS = [
    "workato_db_table.get_records",
    "workato_db_table.update_record",
]


def validate_130926393(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if "IsClosed" not in str(raw.get("filter") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce closed-opportunity trigger filter changed")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    search_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if search_input.get("table_id") != TABLE_ID or OPPORTUNITY_FIELD.replace("_", "-") not in str(search_input):
        raise RuntimeError(f"recipe {RECIPE_ID} Workato DB lookup mapping changed")
    closed_lost_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    closed_won_input = actions[2].get("input") if isinstance(actions[2].get("input"), dict) else {}
    if closed_lost_input.get("table_id") != TABLE_ID or "=now + 4.weeks" not in str(closed_lost_input):
        raise RuntimeError(f"recipe {RECIPE_ID} Closed Lost delete-date mapping changed")
    if closed_won_input.get("table_id") != TABLE_ID or "=now + 1.years" not in str(closed_won_input):
        raise RuntimeError(f"recipe {RECIPE_ID} Closed Won delete-date mapping changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_130926393(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130926393(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger.get("Id") in (None, "") or trigger.get("StageName") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing Id or StageName")
    if not isinstance(trigger.get("IsClosed"), bool):
        # Both trigger-filter outcomes are benchmarked: IsClosed true runs the
        # tracked-opportunity update path, IsClosed false is the verified
        # zero-action trigger-filter-false path. Only the missing/non-boolean
        # case is invalid input.
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input must carry an explicit IsClosed boolean")
    seed_in = data.get("seed")
    db_seed = seed_in.get("workato_db_table") if isinstance(seed_in, dict) else None
    if not isinstance(db_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.workato_db_table")
    now = data.get("now")
    if now in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} requires fixed now")
    out = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "workato_db_table": deepcopy(db_seed),
        "now": now,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_130926393(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130926393(raw)
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
    result["verifier"] = verify_130926393(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


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
    return [{"number": action.get("number"), "provider": action.get("provider"), "name": action.get("name"), "as": action.get("as")} for action in actions]
