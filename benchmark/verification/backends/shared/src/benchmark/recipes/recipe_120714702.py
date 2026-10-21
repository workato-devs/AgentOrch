from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_120714702


RECIPE_ID = "120714702"
SEED_TYPE = "live_salesforce_google_sheets_customer_check_variant"
TRACK = "live_salesforce_google_sheets_smart_list"
TRIGGER_PROVIDER = "google_sheets"
TRIGGER_NAME = "new_polling_spreadsheet_row_v4"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_variable", "declare_variable"),
    ("salesforce", "search_sobjects"),
    ("workato_variable", "update_variables"),
    ("workato_smart_list", "create_list"),
    ("workato_smart_list", "query_list"),
    ("workato_variable", "update_variables"),
    ("workato_smart_list", "query_list"),
    ("workato_variable", "update_variables"),
    ("google_sheets", "update_row_v4_new"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "salesforce.search_records",
    "workato_runtime.update_variables",
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
    "google_sheets.update_row_v4_new",
]
ALLOWED_TOOLS: list[str] = [
    "google_sheets.update_row_v4_new",
    "salesforce.search_records",
]


def validate_120714702(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
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


def seed_120714702(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_120714702(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")

    sheets_seed = seed_in.get("google_sheets")
    if not isinstance(sheets_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.google_sheets")
    sheet_response = ctx.tools.call("harness.google_sheets.seed_rows", {"sheets": sheets_seed})
    if not sheet_response.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Google Sheets seed failed: {sheet_response}")

    salesforce_seed = seed_in.get("salesforce")
    if not isinstance(salesforce_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce")
    provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": salesforce_seed})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")

    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger_input(ctx),
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "google_sheets": deepcopy(sheets_seed),
        "google_sheets_seed_response": deepcopy(sheet_response),
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_120714702(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_120714702(raw)
    if not ctx.env.sheets_spreadsheet_id or not ctx.env.sheets_tab:
        raise RuntimeError("missing SHEETS_SPREADSHEET_ID or SHEETS_TAB for live Google Sheets update")
    initial_snapshot = _snapshot(ctx, seed)
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        # Cleanup runs even when replay crashes: leaked benchmark-owned live
        # records would poison later runs (benchmark cleanup policy cleanup
        # principle). On success the snapshot above is captured first.
        cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
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
            "cleanup_response": cleanup_response,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_120714702(result)
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
