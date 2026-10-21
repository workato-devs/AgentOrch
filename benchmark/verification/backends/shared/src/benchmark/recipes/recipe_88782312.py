from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_88782312


RECIPE_ID = "88782312"
SEED_TYPE = "slack_bot_command_swag_request_google_sheets_append_variant"
TRACK = "live_google_sheets_slack_bot_swag_request_append"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"
SHEET_NAME = "Swag Input Sheet"
CONFIRMATION_TEXT = "Your item has been added"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("google_sheets", "add_spreadsheet_row_v4"),
    ("slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "google_sheets.add_spreadsheet_row_v4",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "google_sheets.add_spreadsheet_row_v4",
    "slack.post_message",
]


def validate_88782312(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    sheet_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if str(sheet_input.get("sheet_name") or "") != SHEET_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} target sheet changed")
    post_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    blocks = post_input.get("blocks") if isinstance(post_input.get("blocks"), list) else []
    first_block = blocks[0] if blocks and isinstance(blocks[0], dict) else {}
    if str(first_block.get("section_text") or "") != CONFIRMATION_TEXT:
        raise RuntimeError(f"recipe {RECIPE_ID} confirmation text changed")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": _action_summary(actions),
    }


def seed_88782312(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88782312(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters") if isinstance(trigger.get("parameters"), dict) else {}
    for field in ("item", "office", "quantity"):
        if parameters.get(field) in (None, ""):
            raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing parameters.{field}")
    context = trigger.get("context") if isinstance(trigger.get("context"), dict) else {}
    if context.get("user_email") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing context.user_email")
    job_context = data.get("job_context")
    if not isinstance(job_context, dict) or job_context.get("job_created_at") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} requires job_context.job_created_at")
    seed_in = data.get("seed") if isinstance(data.get("seed"), dict) else {}
    sheets_seed = seed_in.get("sheets")
    if not isinstance(sheets_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.sheets")
    sheets_seed_response = ctx.tools.call("harness.google_sheets.seed_rows", {"sheets": sheets_seed})
    if not sheets_seed_response.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Google Sheets seed failed: {sheets_seed_response}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "job_context": deepcopy(job_context),
        "sheets": deepcopy(sheets_seed),
        "sheets_seed_response": deepcopy(sheets_seed_response),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if isinstance(data.get("force_action_error"), dict):
        out["force_action_error"] = deepcopy(data["force_action_error"])
    return attach_variant(out, ctx)


def run_88782312(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88782312(raw)
    if any(tool.startswith("slack.") for tool in ALLOWED_TOOLS) and not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
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
    result["verifier"] = verify_88782312(result)
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
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"number": action.get("number"), "provider": action.get("provider"), "name": action.get("name"), "as": action.get("as")}
        for action in actions
    ]
