from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_130712299
from .salesforce_recipe_utils import collect_actions


RECIPE_ID = "130712299"
SEED_TYPE = "genie_lesson_learned_google_sheets_append_variant"
TRACK = "live_google_sheets_genie_lesson_append"
TRIGGER_PROVIDER = "workato_genie"
TRIGGER_NAME = "start_workflow"
EXPECTED_ACTIONS = [
    ("google_sheets", "add_spreadsheet_row_v4"),
    ("workato_genie", "workflow_return_result"),
]
EXPECTED_RAW_TOOLS = [
    "google_sheets.add_spreadsheet_row_v4",
    "workato_genie.workflow_return_result",
]
ALLOWED_TOOLS = [
    "google_sheets.add_spreadsheet_row_v4",
    "workato_genie.workflow_return_result",
]
REQUIRED_PARAMETERS = ("what_happened", "leasson_learned", "improvement")


def validate_130712299(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    add_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    data = add_input.get("data") if isinstance(add_input.get("data"), dict) else {}
    if add_input.get("sheet") != "Sheet1" or data.get("col_1") != "=now":
        raise RuntimeError(f"recipe {RECIPE_ID} Google Sheets append target changed")
    for key in REQUIRED_PARAMETERS:
        if key not in str(data):
            raise RuntimeError(f"recipe {RECIPE_ID} Google Sheets parameter mapping changed for {key}")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_130712299(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130712299(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters") if isinstance(trigger.get("parameters"), dict) else None
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing parameters object")
    for key in REQUIRED_PARAMETERS:
        if parameters.get(key) in (None, ""):
            raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter missing {key}")
    seed_in = data.get("seed")
    sheets_seed = seed_in.get("sheets") if isinstance(seed_in, dict) else None
    if not isinstance(sheets_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.sheets")
    sheets_seed_response = ctx.tools.call("harness.google_sheets.seed_rows", {"sheets": sheets_seed})
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
        "sheets": deepcopy(sheets_seed),
        "sheets_seed_response": sheets_seed_response,
        "now": now,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_130712299(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130712299(raw)
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
    result["verifier"] = verify_130712299(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return {"google_sheets": ctx.tools.call("harness.google_sheets.snapshot", {})}


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"number": action.get("number"), "provider": action.get("provider"), "name": action.get("name"), "as": action.get("as")} for action in actions]
