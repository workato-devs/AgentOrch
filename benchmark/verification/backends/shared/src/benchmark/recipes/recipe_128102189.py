from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_128102189


RECIPE_ID = "128102189"
SEED_TYPE = "workato_db_new_record_google_sheets_append_variant"
TRACK = "live_google_sheets_workato_db_append"
TRIGGER_PROVIDER = "workato_db_table"
TRIGGER_NAME = "new_records_realtime"
TABLE_ID = "44529"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("clock", "wait_for_interval"),
    ("workato_db_table", "get_records"),
    ("google_sheets", "add_spreadsheet_row_v4"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "clock.wait_for_interval",
    "workato_db_table.get_records",
    "google_sheets.add_spreadsheet_row_v4",
]
ALLOWED_TOOLS: list[str] = [
    "clock.wait_for_interval",
    "workato_db_table.get_records",
    "google_sheets.add_spreadsheet_row_v4",
]
REQUIRED_RECORD_FIELDS = (
    "11fbe9a6_a16d_4d7e_86ea_afe42ec03005",
    "5863d8e2_5333_4d5b_8746_5c11a6d8958c",
    "bb38890a_d7c7_41a5_bf4c_563f40462f79",
    "c75de8c8_3884_4660_9f3c_0c441cb3498b",
    "009bb2a4_806a_4d7c_a367_6e1a49e94c1a",
    "be67b481_d995_44c0_a3fa_749d18239ba4",
)


def validate_128102189(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    trigger_input_obj = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    if str(trigger_input_obj.get("table_id") or "") != TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger table id changed")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    get_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    if str(get_input.get("table_id") or "") != TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} Workato DB table id changed")
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


def seed_128102189(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_128102189(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    record = trigger.get("record") if isinstance(trigger.get("record"), dict) else None
    if not isinstance(record, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing record object")
    for field in REQUIRED_RECORD_FIELDS:
        if field not in record:
            raise RuntimeError(f"recipe {RECIPE_ID} trigger record missing {field}")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    sheets_seed = seed_in.get("google_sheets")
    if not isinstance(sheets_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.google_sheets")
    sheet_response = ctx.tools.call("harness.google_sheets.seed_rows", {"sheets": sheets_seed})
    if not sheet_response.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Google Sheets seed failed: {sheet_response}")
    if not isinstance(seed_in.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.workato_db_table")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "google_sheets": deepcopy(sheets_seed),
        "google_sheets_seed_response": deepcopy(sheet_response),
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_128102189(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_128102189(raw)
    if not ctx.env.sheets_spreadsheet_id or not ctx.env.sheets_tab:
        raise RuntimeError("missing SHEETS_SPREADSHEET_ID or SHEETS_TAB for live Google Sheets add row")
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
    result["verifier"] = verify_128102189(result)
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
    if isinstance(seed.get("workato_db_table"), dict):
        out.update(ctx.tools.call("harness.workato_db_table.snapshot", {}))
    if isinstance(seed.get("google_sheets"), dict):
        out["google_sheets"] = ctx.tools.call("harness.google_sheets.snapshot", {})
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
