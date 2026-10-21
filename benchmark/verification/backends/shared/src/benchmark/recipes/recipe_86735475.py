from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_86735475


RECIPE_ID = "86735475"
SEED_TYPE = "workato_pub_sub_google_sheets_ic_raw_upsert_variant"
TRACK = "live_google_sheets_pub_sub_ic_raw_upsert"
TRIGGER_PROVIDER = "workato_pub_sub"
TRIGGER_NAME = "subscribe_to_topic"
SHEET_TAB = "IC RAW"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("google_sheets", "search_spreadsheet_rows_v4_new"),
    ("google_sheets", "update_row_v4_new"),
    ("google_sheets", "add_spreadsheet_row_v4"),
    ("logger", "log_message"),
    ("logger", "log_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "google_sheets.search_spreadsheet_rows_v4_new",
    "google_sheets.update_row_v4_new",
    "google_sheets.add_spreadsheet_row_v4",
    "workato_runtime.log_message",
    "workato_runtime.log_message",
]
ALLOWED_TOOLS: list[str] = [
    "google_sheets.search_spreadsheet_rows_v4_new",
    "google_sheets.update_row_v4_new",
    "google_sheets.add_spreadsheet_row_v4",
    "workato_runtime.log_message",
]


def validate_86735475(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    search_input = actions[0].get("input") or {}
    if str(search_input.get("sheet_name") or "") != SHEET_TAB:
        raise RuntimeError(f"recipe {RECIPE_ID} search tab changed")
    add_input = actions[2].get("input") or {}
    if str(add_input.get("sheet_name") or "") != SHEET_TAB:
        raise RuntimeError(f"recipe {RECIPE_ID} add tab changed")
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


def seed_86735475(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_86735475(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    sheets_seed = seed_in.get("sheets")
    if not isinstance(sheets_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.sheets")
    sheets_seed_response = ctx.tools.call("harness.google_sheets.seed_rows", {"sheets": sheets_seed})
    if not sheets_seed_response.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Google Sheets seed failed: {sheets_seed_response}")
    trigger = trigger_input(ctx)
    if not isinstance(trigger.get("message"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger missing message object")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") or {}),
        "raw_validation": validation,
        "sheets": deepcopy(sheets_seed),
        "sheets_seed_response": sheets_seed_response,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if isinstance(data.get("force_action_error"), dict):
        out["force_action_error"] = deepcopy(data["force_action_error"])
    return attach_variant(out, ctx)


def run_86735475(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_86735475(raw)
    if not ctx.env.sheets_spreadsheet_id or not ctx.env.sheets_tab:
        raise RuntimeError("missing SHEETS_SPREADSHEET_ID or SHEETS_TAB for live Google Sheets upsert")
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
    result["verifier"] = verify_86735475(result)
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
    return {"google_sheets": ctx.tools.call("harness.google_sheets.snapshot", {})}


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
