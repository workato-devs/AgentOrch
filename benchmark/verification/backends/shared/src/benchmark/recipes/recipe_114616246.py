from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_114616246


RECIPE_ID = "114616246"
SEED_TYPE = "live_salesforce_google_sheets_variant"
TRACK = "live_salesforce_google_sheets"
TRIGGER_PROVIDER = "google_sheets"
TRIGGER_NAME = "updated_spreadsheet_row_v4_2"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("salesforce", "search_sobjects_soql_v2"),
    ("google_sheets", "update_row_v4_new"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.search_records",
    "google_sheets.update_row_v4_new",
]
ALLOWED_TOOLS: list[str] = ["google_sheets.update_row_v4_new", "salesforce.search_records"]
SHEET_HEADERS: list[str] = [
    "Symbol",
    "Account Name",
    "GICS Sector",
    "GICS Sub-Industry",
    "Headquarters Location",
    "Date added",
    "CIK",
    "Founded",
    "Customer",
    "SFDC Record",
]


def validate_114616246(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_114616246(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_114616246(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    salesforce_seed = seed_in.get("salesforce")
    if not isinstance(salesforce_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires a salesforce seed object")
    trigger = trigger_input(ctx)
    sheets_section = _require_sheets_section(seed_in.get("google_sheets"), trigger)
    provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": salesforce_seed})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    sheets_provision = ctx.tools.call("harness.google_sheets.seed_rows", {"sheets": sheets_section})
    if not sheets_provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Google Sheets seed failed: {sheets_provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "raw_validation": validation,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "sheets_seed_response": deepcopy(sheets_provision),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if isinstance(data.get("expect"), dict):
        out["expect"] = deepcopy(data["expect"])
    for key, value in seed_in.items():
        if isinstance(value, dict):
            out[str(key)] = deepcopy(value)
    return attach_variant(out, ctx)


def run_114616246(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_114616246(raw)
    if not ctx.env.sheets_spreadsheet_id or not ctx.env.sheets_tab:
        raise RuntimeError("missing SHEETS_SPREADSHEET_ID or SHEETS_TAB for live Google Sheets update")
    if not isinstance(seed.get("google_sheets"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed file missing google_sheets section; the update_row "
            "target row must be seeded, never residual live tab state"
        )
    initial_snapshot = _snapshot(ctx, seed)
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        # Owned Salesforce records must be removed even when replay/snapshot
        # fails; the sheet needs no cleanup (every seed fully overwrites it).
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
    result["verifier"] = verify_114616246(result)
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
    if isinstance(seed.get("lookup_table"), dict):
        out.update(ctx.tools.call("harness.lookup_table.snapshot", {}))
    if isinstance(seed.get("salesforce_live"), dict):
        out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
    if isinstance(seed.get("google_sheets"), dict):
        out["google_sheets"] = ctx.tools.call("harness.google_sheets.snapshot", {})
    return out


def _require_sheets_section(section: Any, trigger: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["headers", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.google_sheets must be exactly {{'headers','rows'}}"
        )
    if section.get("headers") != SHEET_HEADERS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.google_sheets.headers must be exactly the 10 trigger-"
            "schema labels in order (the update label-decodes col_Customer / 'col_SFDC "
            "Record' into these real columns)"
        )
    rows = section.get("rows")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.google_sheets.rows must be a non-empty list")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(SHEET_HEADERS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} sheet row {idx} must carry exactly the 10 headers; got "
                f"{sorted(row.keys()) if isinstance(row, dict) else row!r}"
            )
        for key, value in row.items():
            if not isinstance(value, str) or "\n" in value:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} sheet row {idx} {key!r} must be a single-line string "
                    "(rendered-form pinning)"
                )
    columns = trigger.get("columns")
    if not isinstance(columns, dict) or not isinstance(columns.get("col_2"), str) or not columns["col_2"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.columns.col_2 must be a non-empty string "
            "(the SOQL name filter dereferences it)"
        )
    row_number = trigger.get("row")
    if isinstance(row_number, bool) or not isinstance(row_number, int):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.row must be an integer sheet row: "
            f"{row_number!r}"
        )
    if not 2 <= row_number <= len(rows) + 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.row {row_number} is not a seeded data row "
            f"(seed covers rows 2..{len(rows) + 1}); the update target must exist"
        )
    target = rows[row_number - 2]
    if target["Account Name"] != columns["col_2"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seeded row {row_number} 'Account Name' "
            f"{target['Account Name']!r} must equal the trigger's watched col_2 value "
            f"{columns['col_2']!r} (the trigger reports that row's current cells)"
        )
    return {"headers": list(SHEET_HEADERS), "rows": deepcopy(rows)}


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
