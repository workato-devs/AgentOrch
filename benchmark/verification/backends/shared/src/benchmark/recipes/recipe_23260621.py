from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_23260621


RECIPE_ID = "23260621"
SEED_TYPE = "workato_recipe_function_google_sheets_signup_variant"
TRACK = "live_google_sheets_recipe_function_signup_log"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
SPREADSHEET_ID_RAW = "18AShtlbXcGNnwmHPm9EJT5fRTq5GrFHRnjR7h7HZqJ8"
SHEET_NAME = "Sheet1"
PARAMETER_KEYS = [
    "workato_user_id",
    "full_name",
    "work_email",
    "region",
    "company_name",
    "job_title",
    "phone_number",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "marketo_id",
    "intercom_id",
]
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("logger", "log_message"),
    ("google_sheets", "add_spreadsheet_row_v4"),
    ("workato_recipe_function", "return_result"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.log_message",
    "google_sheets.add_spreadsheet_row_v4",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "google_sheets.add_spreadsheet_row_v4",
    "workato_recipe_function.return_result",
]


def validate_23260621(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual = [(a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    sheet_input = actions[1].get("input") or {}
    if str(sheet_input.get("spreadsheet") or "") != SPREADSHEET_ID_RAW:
        raise RuntimeError(f"recipe {RECIPE_ID} Sheets spreadsheet id changed")
    if str(sheet_input.get("sheet") or "") != SHEET_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} Sheets tab changed")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": [
            {
                "number": a.get("number"),
                "provider": a.get("provider"),
                "name": a.get("name"),
                "as": a.get("as"),
            }
            for a in actions
        ],
    }


def seed_23260621(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_23260621(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input missing parameters object")
    if sorted(parameters.keys()) != sorted(PARAMETER_KEYS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must carry exactly the 13 "
            f"recipe-function keys; got {sorted(parameters.keys())}"
        )
    job_context = data.get("job_context")
    if not isinstance(job_context, dict) or job_context.get("job_created_at") in (None, ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires a pinned job_context.job_created_at "
            "(col_2 is a job_context strftime formula)"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    sheets_seed = seed_in.get("sheets")
    if not isinstance(sheets_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.sheets")
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    sheets_seed_response = ctx.tools.call("harness.google_sheets.seed_rows", {"sheets": sheets_seed})
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(expect),
        "raw_validation": validation,
        "job_context": deepcopy(job_context),
        "sheets": deepcopy(sheets_seed),
        "sheets_seed_response": sheets_seed_response,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if isinstance(data.get("force_action_error"), dict):
        out["force_action_error"] = deepcopy(data["force_action_error"])
    return attach_variant(out, ctx)


def run_23260621(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_23260621(raw)
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
    result["verifier"] = verify_23260621(result)
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
