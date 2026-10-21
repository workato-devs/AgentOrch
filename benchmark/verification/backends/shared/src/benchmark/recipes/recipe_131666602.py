from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_131666602
from .salesforce_recipe_utils import collect_actions, replace_tokens, salesforce_refs


RECIPE_ID = "131666602"
SEED_TYPE = "scheduled_asv_google_sheets_empty_input_variant"
TRACK = "live_google_sheets_scheduled_asv_empty_input"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
EXPECTED_ACTIONS = [
    ("google_sheets", "get_spreadsheet_rows_v4"),
    ("salesforce", "search_sobjects"),
    ("salesforce", "search_sobjects"),
    ("google_sheets", "update_row_v4_new"),
    ("google_sheets", "update_row_v4_new"),
    ("google_sheets", "add_spreadsheet_row_v4"),
    ("google_sheets", "add_spreadsheet_row_v4"),
]
EXPECTED_RAW_TOOLS = [
    "google_sheets.get_spreadsheet_rows_v4",
    "salesforce.search_records",
    "google_sheets.update_row_v4_new",
    "google_sheets.add_spreadsheet_row_v4",
]
ALLOWED_TOOLS = [
    "google_sheets.get_spreadsheet_rows_v4",
    "google_sheets.update_row_v4_new",
    "google_sheets.add_spreadsheet_row_v4",
    "salesforce.search_records",
]
_REF_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*_ID")


def _require_no_ref_tokens(value: Any, where: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _require_no_ref_tokens(item, f"{where}.{key}")
    elif isinstance(value, list):
        for idx, item in enumerate(value):
            _require_no_ref_tokens(item, f"{where}[{idx}]")
    elif isinstance(value, str) and _REF_TOKEN_RE.search(value):
        raise RuntimeError(
            f"recipe {RECIPE_ID} unresolved seed ref token in {where}: {value!r} "
            "(a $..._ID token requires a matching seed.salesforce record)"
        )


def validate_131666602(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    get_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if get_input.get("sheet") != "Copy of ASV DB":
        raise RuntimeError(f"recipe {RECIPE_ID} Google Sheets input tab changed")
    final_log_input = actions[-1].get("input") if isinstance(actions[-1].get("input"), dict) else {}
    if final_log_input.get("sheet") != "Runlog" or "job_created_at" not in str(final_log_input):
        raise RuntimeError(f"recipe {RECIPE_ID} final Runlog append changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_131666602(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_131666602(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    seed_in = data.get("seed")
    salesforce_seed = seed_in.get("salesforce") if isinstance(seed_in, dict) else None
    refs: dict[str, str] = {}
    provision: dict[str, Any] | None = None
    if salesforce_seed is not None:
        # The starts_with('006') TRUE branch (IF#7) reads live Salesforce:
        # provision the benchmark-owned Opportunity/Account FIRST so their live
        # ids can be threaded into the sheet's OppID cell and the expect block
        # via $OPPORTUNITY_ID / $ACCOUNT_ID tokens (a live Opportunity id is
        # the only faithful way to satisfy the '006' prefix condition).
        if not isinstance(salesforce_seed, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce must be an object")
        provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": salesforce_seed})
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
        refs = salesforce_refs(provision)
    sheets_seed = seed_in.get("google_sheets") if isinstance(seed_in, dict) else None
    if not isinstance(sheets_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.google_sheets")
    sheets_seed = replace_tokens(deepcopy(sheets_seed), refs)
    _require_no_ref_tokens(sheets_seed, "seed.google_sheets")
    expect = replace_tokens(
        deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}), refs
    )
    _require_no_ref_tokens(expect, "expect")
    sheet_response = ctx.tools.call("harness.google_sheets.seed_rows", {"sheets": sheets_seed})
    if not sheet_response.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Google Sheets seed failed: {sheet_response}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger_input(ctx),
        "track": data.get("track"),
        "expect": expect,
        "raw_validation": validation,
        "google_sheets": deepcopy(sheets_seed),
        "google_sheets_seed_response": deepcopy(sheet_response),
    }
    if provision is not None:
        out["salesforce_live"] = deepcopy(provision["state"])
        out["salesforce_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
    out["harness_tool_calls"] = ctx.tools.call_log()
    if isinstance(data.get("job_context"), dict):
        out["job_context"] = deepcopy(data["job_context"])
    return attach_variant(out, ctx)


def run_131666602(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_131666602(raw)
    if not ctx.env.sheets_spreadsheet_id or not ctx.env.sheets_tab:
        raise RuntimeError("missing SHEETS_SPREADSHEET_ID or SHEETS_TAB for live Google Sheets actions")
    initial_snapshot = _snapshot(ctx, seed)
    cleanup_response: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    if isinstance(seed.get("salesforce_live"), dict):
        # The starts_with('006') TRUE-branch variant seeds benchmark-owned live
        # Salesforce records: snapshot-then-cleanup so verification reads the
        # final state and no owned records survive even a failed replay.
        try:
            raw_execution = execute_raw_recipe(raw, seed, ctx)
            final_snapshot = _snapshot(ctx, seed)
        finally:
            cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
    else:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    details: dict[str, Any] = {
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
    }
    if cleanup_response is not None:
        details["cleanup_response"] = cleanup_response
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_131666602(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("salesforce_live"), dict):
        out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
    if isinstance(seed.get("google_sheets"), dict):
        out["google_sheets"] = ctx.tools.call("harness.google_sheets.snapshot", {})
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"number": action.get("number"), "provider": action.get("provider"), "name": action.get("name"), "as": action.get("as")} for action in actions]
