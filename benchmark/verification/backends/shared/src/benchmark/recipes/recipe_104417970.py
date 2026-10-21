from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_104417970


RECIPE_ID = '104417970'
SEED_TYPE = 'final_state_benchmark_variant'
TRACK = 'benchmark_final_state'
TRIGGER_PROVIDER = 'slack_bot'
TRIGGER_NAME = 'bot_command_v2'
EXPECTED_ACTIONS: list[tuple[str, str]] = [('slack_bot', 'post_bot_reply_v2'),
 ('google_sheets', 'search_spreadsheet_rows_v4_new'),
 ('lookup_table', 'get_entry'),
 ('google_sheets', 'search_spreadsheet_rows_v4_new'),
 ('google_sheets', 'search_spreadsheet_rows_v4_new'),
 ('lookup_table', 'add_entry'),
 ('lookup_table', 'add_entry'),
 ('lookup_table', 'add_entry'),
 ('google_sheets', 'update_row_v4_new'),
 ('slack_bot', 'post_bot_reply_v2'),
 ('slack_bot', 'post_bot_reply_v2')]
EXPECTED_RAW_TOOLS: list[str] = ['slack.post_reply',
 'google_sheets.search_spreadsheet_rows_v4_new',
 'lookup_table.get_entry',
 'google_sheets.search_spreadsheet_rows_v4_new',
 'google_sheets.search_spreadsheet_rows_v4_new',
 'lookup_table.add_entry',
 'lookup_table.add_entry',
 'lookup_table.add_entry',
 'google_sheets.update_row_v4_new',
 'slack.post_reply',
 'slack.post_reply']
ALLOWED_TOOLS: list[str] = ['google_sheets.search_spreadsheet_rows_v4_new',
 'google_sheets.update_row_v4_new',
 'lookup_table.add_entry',
 'lookup_table.get_entry',
 'slack.post_reply']
# The live harness binds ONE spreadsheet/tab from env, so the participant sheet
# ("Product Design Batch Email Sender": Name..Tests) and the ADMIN sheet
# (Question..Sets of Gift Cards) share a single seeded tab. Union headers in
# schema order; the searches filter on "col_Search Row" (participant rows) vs
# "col_Search" (ADMIN rows), which decode to the distinct "Search Row" and
# "Search" columns, so the two row families never cross-match.
SHEET_HEADERS: list[str] = [
    "Name",
    "Email",
    "Location",
    "Company",
    "Search Row",
    "Tests",
    "Question",
    "Answer",
    "Search",
    "Sets of Gift Cards",
]
LOOKUP_TABLE_IDS = ("3211451", "3231913")


def validate_104417970(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_104417970(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_104417970(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if "sheets" in seed_in:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed carries the legacy mock-style 'sheets' section, which "
            "is never applied; declare the live tab state under seed.google_sheets instead"
        )
    sheets_section = _require_sheets_section(seed_in.get("google_sheets"))
    _require_lookup_section(seed_in.get("lookup_table"))
    sheets_provision = ctx.tools.call("harness.google_sheets.seed_rows", {"sheets": sheets_section})
    if not sheets_provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Google Sheets seed failed: {sheets_provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "raw_validation": validation,
        "sheets_seed_response": deepcopy(sheets_provision),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if isinstance(seed_in.get("salesforce"), dict):
        provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": seed_in["salesforce"]})
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
        out["salesforce_live"] = deepcopy(provision["state"])
        out["salesforce_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
    if isinstance(data.get("expect"), dict):
        out["expect"] = deepcopy(data["expect"])
    for key, value in seed_in.items():
        if isinstance(value, dict):
            out[str(key)] = deepcopy(value)
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    for key in ("force_action_error", "job_context"):
        if isinstance(data.get(key), dict):
            out[key] = deepcopy(data[key])
    return attach_variant(out, ctx)


def run_104417970(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_104417970(raw)
    if any(tool.startswith("slack.") for tool in ALLOWED_TOOLS):
        if not ctx.env.slack_channel_override:
            raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    if not ctx.env.sheets_spreadsheet_id or not ctx.env.sheets_tab:
        raise RuntimeError("missing SHEETS_SPREADSHEET_ID or SHEETS_TAB for live Google Sheets")
    if not isinstance(seed.get("google_sheets"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed file missing google_sheets section; the sheet searches "
            "must read seeded state, never residual live tab state"
        )
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
    result["verifier"] = verify_104417970(result)
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
    if isinstance(seed.get("lookup_table"), dict):
        out.update(ctx.tools.call("harness.lookup_table.snapshot", {}))
    if isinstance(seed.get("salesforce_live"), dict):
        out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
    if isinstance(seed.get("google_sheets"), dict):
        out["google_sheets"] = ctx.tools.call("harness.google_sheets.snapshot", {})
    return out


def _require_sheets_section(section: Any) -> dict[str, Any]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["headers", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.google_sheets must be exactly {{'headers','rows'}}"
        )
    if section.get("headers") != SHEET_HEADERS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.google_sheets.headers must be exactly the 10 union "
            "labels in schema order (participant Name..Tests + ADMIN Question..Sets of "
            "Gift Cards on the single env-bound tab)"
        )
    rows = section.get("rows")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.google_sheets.rows must be a non-empty list")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(SHEET_HEADERS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} sheet row {idx} must carry exactly the 10 union headers; "
                f"got {sorted(row.keys()) if isinstance(row, dict) else row!r}"
            )
        for key, value in row.items():
            if not isinstance(value, str) or "\n" in value:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} sheet row {idx} {key!r} must be a single-line string "
                    "(only the recipe's own row-2 update writes multi-line cells)"
                )
    return {"headers": list(SHEET_HEADERS), "rows": deepcopy(rows)}


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    context = trigger.get("context")
    if not isinstance(context, dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry a context object (the bot replies "
            "dereference context.user_name / context.user_handle)"
        )
    user_name = context.get("user_name")
    if not isinstance(user_name, str) or not user_name:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.context.user_name must be a non-empty string: "
            f"{user_name!r}"
        )
    if "user_handle" in context and not isinstance(context["user_handle"], str):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.context.user_handle must be a string when "
            f"present: {context['user_handle']!r}"
        )


def _require_lookup_section(section: Any) -> None:
    if not isinstance(section, dict) or not isinstance(section.get("tables"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table must declare a tables object"
        )
    missing = [table for table in LOOKUP_TABLE_IDS if table not in section["tables"]]
    if missing:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must seed both benchmark tables "
            f"{list(LOOKUP_TABLE_IDS)}; missing {missing}"
        )


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
