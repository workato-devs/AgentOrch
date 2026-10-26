from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_122664591


RECIPE_ID = "122664591"
SEED_TYPE = "scheduled_snowflake_count_google_sheets_variant"
TRACK = "controlled_snowflake_live_google_sheets"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("snowflake", "run_custom_sql"),
    ("google_sheets", "add_spreadsheet_row_v4"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "google_sheets.add_spreadsheet_row_v4",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "google_sheets.add_spreadsheet_row_v4",
]
EXPECTED_SQL_FRAGMENT = "numEntOEM"
EXPECTED_RAW_SHEET = "NumEnterpriseOEM"


def validate_122664591(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    if EXPECTED_SQL_FRAGMENT not in str((actions[0].get("input") or {}).get("sql") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake SQL changed")
    if str((actions[1].get("input") or {}).get("sheet") or "") != EXPECTED_RAW_SHEET:
        raise RuntimeError(f"recipe {RECIPE_ID} Google Sheets target sheet changed")
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


def seed_122664591(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_122664591(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    for key in ("snowflake", "sheets"):
        if not isinstance(seed_in.get(key), dict):
            raise RuntimeError(f"recipe {RECIPE_ID} requires seed.{key}")
    sheets_seed_response = ctx.tools.call("harness.google_sheets.seed_rows", {"sheets": seed_in["sheets"]})
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger_input(ctx),
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") or {}),
        "raw_validation": validation,
        "snowflake": deepcopy(seed_in["snowflake"]),
        "sheets": deepcopy(seed_in["sheets"]),
        "sheets_seed_response": sheets_seed_response,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if isinstance(data.get("job_context"), dict):
        out["job_context"] = deepcopy(data["job_context"])
    return attach_variant(out, ctx)


def run_122664591(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_122664591(raw)
    if not ctx.env.sheets_spreadsheet_id or not ctx.env.sheets_tab:
        raise RuntimeError("missing SHEETS_SPREADSHEET_ID or SHEETS_TAB for live Google Sheets append")
    initial_snapshot = _snapshot(ctx)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = _snapshot(ctx)
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
    result["verifier"] = verify_122664591(result)
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


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return {
        "snowflake": ctx.tools.call("harness.snowflake.snapshot", {}).get("snowflake", {}),
        "google_sheets": ctx.tools.call("harness.google_sheets.snapshot", {}),
    }


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
