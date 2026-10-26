from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_123992155


RECIPE_ID = "123992155"
SEED_TYPE = "slack_bot_namecard_completion_variant"
TRACK = "live_google_sheets_slack_lookup_namecard_completion"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"
TRIGGER_AS = "79c4a18b"
TABLE_ID = "1840306"
SEARCH_AS = "12079e4b"
LOGGER_AS = "1f7aeafc"
UPDATE_ENTRY_AS = "171ad1f8"
SHEETS_SEARCH_AS = "89357d8d"
SHEETS_UPDATE_AS = "cfa21416"
SLACK_POST_AS = "336b10f9"
RAW_CHANNEL = "C03FVMYSM8X"  # non-U literal -> raw_executor routes to SLACK_CHANNEL_OVERRIDE
TS_TOKEN = "$SLACK_MESSAGE_TS"
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
SHEET_HEADERS = [
    "Name",
    "Japanese Name",
    "Job Title",
    "Japanese Job Title",
    "Workato Email",
    "Phone",
    "Template",
    "Location",
    "Status",
    "Remarks",
]
LOOKUP_COLS = tuple(f"col{idx}" for idx in range(1, 11))
COMPLETED_PREFIX = "Completed on "
SECTION_TEXT = (
    "This request has been `Completed`. <https://docs.google.com/spreadsheets/d/"
    "<anon>2PqR8StU9VwX0YzA1BcD2EfG3HiJ4KlM5NoPqRsT6Uv</anon>/edit#gid=1071595560"
    "|Here are the details.> "
)


_STRUCTURE_PINS_JSON = r'''
[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "79c4a18b",
  "provider": "slack_bot",
  "name": "bot_command_v2",
  "skip": false,
  "input": {
   "allow_dialog": "true",
   "domain": "SG",
   "name": "Namecard",
   "parameters": "[{\"name\":\"email\",\"type\":\"string\",\"optional\":false}]",
   "scope": "Done"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "12079e4b",
  "provider": "lookup_table",
  "name": "search_entries",
  "skip": false,
  "input": {
   "lookup_table_id": "1840306",
   "parameters": {
    "col5": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"79c4a18b\",\"path\":[\"parameters\", \"email\"]}')}"
   }
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "1f7aeafc",
  "provider": "logger",
  "name": "log_message",
  "skip": false,
  "input": {
   "message": "=_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_created_at\"]}').in_time_zone(\"Asia/Singapore\").strftime(\"%d %B %Y\")",
   "user_logs_enabled": "false"
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "171ad1f8",
  "provider": "lookup_table",
  "name": "update_entry",
  "skip": false,
  "input": {
   "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"12079e4b\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}",
   "ignore_not_found": "false",
   "lookup_table_id": "1840306",
   "parameters": {
    "col10": "Completed on #{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"1f7aeafc\",\"path\":[\"message\"]}')}",
    "col9": "Completed"
   }
  }
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "89357d8d",
  "provider": "google_sheets",
  "name": "search_spreadsheet_rows_v4_new",
  "skip": false,
  "input": {
   "column_headers": "Name\nJapanese Name\nJob Title\nJapanese Job Title\nWorkato Email\nPhone\nTemplate\nLocation\nStatus\nRemarks",
   "count": "200",
   "data": {
    "col_Remarks": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"12079e4b\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col10\"]}')}",
    "col_Workato Email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"12079e4b\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col5\"]}')}"
   },
   "sheet_name": "NEW Request",
   "spreadsheet_id": "<anon>2PqR8StU9VwX0YzA1BcD2EfG3HiJ4KlM5NoPqRsT6Uv</anon>",
   "team_drives": "0ALg5-mekeNJkUk9PVA/0ALg5-mekeNJkUk9PVA"
  }
 },
 {
  "keyword": "action",
  "number": 6,
  "as": "cfa21416",
  "provider": "google_sheets",
  "name": "update_row_v4_new",
  "skip": false,
  "input": {
   "column_headers": "Name\nJapanese Name\nJob Title\nJapanese Job Title\nWorkato Email\nPhone\nTemplate\nLocation\nStatus\nRemarks",
   "data": {
    "col_Remarks": "Completed on #{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"1f7aeafc\",\"path\":[\"message\"]}')}",
    "col_Status": "Completed"
   },
   "row_number": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"89357d8d\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"row_number\"]}')}",
   "sheet_name": "NEW Request",
   "spreadsheet_id": "<anon>2PqR8StU9VwX0YzA1BcD2EfG3HiJ4KlM5NoPqRsT6Uv</anon>",
   "team_drives": "0ALg5-mekeNJkUk9PVA/0ALg5-mekeNJkUk9PVA"
  }
 },
 {
  "keyword": "action",
  "number": 7,
  "as": "336b10f9",
  "provider": "slack_bot",
  "name": "post_bot_message",
  "skip": false,
  "input": {
   "advanced": {
    "ts": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"79c4a18b\",\"path\":[\"ts\"]}')}"
   },
   "attachment_fields": [
    {
     "title": "Full Name",
     "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"12079e4b\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col1\"]}')}"
    },
    {
     "title": "Job Title",
     "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"12079e4b\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col3\"]}')}"
    },
    {
     "title": "Email",
     "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"12079e4b\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col5\"]}')}"
    },
    {
     "title": "Phone",
     "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"12079e4b\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col6\"]}')}"
    },
    {
     "title": "Location",
     "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"12079e4b\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col8\"]}')}"
    }
   ],
   "blocks": [
    {
     "block_type": "section_with_text",
     "button_type": "continue_flow",
     "section_text": "This request has been `Completed`. <https://docs.google.com/spreadsheets/d/<anon>2PqR8StU9VwX0YzA1BcD2EfG3HiJ4KlM5NoPqRsT6Uv</anon>/edit#gid=1071595560|Here are the details.> "
    }
   ],
   "channel": "C03FVMYSM8X",
   "message": {
    "color": "good"
   }
  }
 }
]
'''

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "workato_runtime.log_message",
    "lookup_table.update_entry",
    "google_sheets.search_spreadsheet_rows_v4_new",
    "google_sheets.update_row_v4_new",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "lookup_table.update_entry",
    "google_sheets.search_spreadsheet_rows_v4_new",
    "google_sheets.update_row_v4_new",
    "slack.post_message",
]
AGENT_TOOL_SEQUENCE: list[str] = list(ALLOWED_TOOLS)
EXECUTED_ACTION_COUNT = 6
REQUIRED_EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "rendered_date",
    "slack_text",
    "target_row_number",
    "final_lookup_rows",
    "final_sheet_rows",
)
_EXPECT_ITEM_KEYS = {
    "tool", "table_id", "lookup_table_id", "match_fields", "channel",
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
}
_EXPECT_VALUE_KEYS = {
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
}


def _structure(node: dict[str, Any]) -> list[dict[str, Any]]:
    pin: dict[str, Any] = {
        "keyword": node.get("keyword"),
        "number": node.get("number"),
        "as": node.get("as"),
        "provider": node.get("provider"),
        "name": node.get("name"),
        "skip": bool(node.get("skip")),
        "input": node.get("input") or {},
    }
    if node.get("keyword") == "foreach":
        pin["repeat_mode"] = node.get("repeat_mode")
        pin["batch_size"] = node.get("batch_size")
        pin["source"] = node.get("source")
    if isinstance(node.get("filter"), dict):
        pin["filter"] = node["filter"]
    out = [pin]
    for child in node.get("block") or []:
        if isinstance(child, dict):
            out.extend(_structure(child))
    return out


def validate_123992155(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger 'as' changed: {raw.get('as')!r}")
    actual = _structure(raw)
    if len(actual) != len(STRUCTURE_PINS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} node count changed: {len(actual)} != {len(STRUCTURE_PINS)}"
        )
    for idx, (got, expected) in enumerate(zip(actual, STRUCTURE_PINS)):
        if got != expected:
            raise RuntimeError(
                f"recipe {RECIPE_ID} node {idx} (step {expected.get('number')}) changed:\n"
                f"expected: {json.dumps(expected, sort_keys=True)}\n"
                f"actual:   {json.dumps(got, sort_keys=True)}"
            )
    actions = [pin for pin in actual if pin["keyword"] == "action"]
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": [
            {
                "number": pin["number"],
                "provider": pin["provider"],
                "name": pin["name"],
                "as": pin["as"],
            }
            for pin in actions
        ],
    }


def seed_123992155(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_123992155(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole "
            "run instead of exercising a recipe branch"
        )
    trigger = trigger_input(ctx)
    email = _require_trigger_shape(trigger)
    job_context = data.get("job_context")
    rendered_date = _require_job_context(job_context)
    completed_text = COMPLETED_PREFIX + rendered_date
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in) != ["lookup_table", "sheets"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must carry exactly the lookup_table + sheets "
            f"sections; got {sorted(seed_in)}"
        )
    lookup_section = seed_in["lookup_table"]
    lookup_rows = _require_lookup_section(lookup_section, email, completed_text)
    target_index, target = _target_entry(lookup_rows, email)
    sheets_section = seed_in["sheets"]
    target_row_number = _require_sheets_section(sheets_section, target)
    expect = data.get("expect")
    _require_expect_shape(
        expect,
        email=email,
        rendered_date=rendered_date,
        lookup_rows=lookup_rows,
        target_index=target_index,
        target=target,
        sheet_rows=sheets_section["rows"],
        target_row_number=target_row_number,
    )
    slack_seed = data.get("slack_seed_message")
    if not isinstance(slack_seed, dict) or not str(slack_seed.get("text") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} every variant must declare slack_seed_message.text "
            "(chat.update needs a live bot-owned seeded ts)"
        )
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    if not ctx.env.sheets_spreadsheet_id or not ctx.env.sheets_tab:
        raise RuntimeError("missing SHEETS_SPREADSHEET_ID / SHEETS_TAB; refusing to guess")
    posted = ctx.tools.call(
        "harness.slack.seed_message",
        {"channel": ctx.env.slack_channel_override, "text": str(slack_seed["text"])},
    )
    channel = str(posted.get("channel") or ctx.env.slack_channel_override)
    ts = str(posted.get("ts") or "")
    if not ts:
        raise RuntimeError(f"recipe {RECIPE_ID} Slack seed message returned no ts: {posted}")
    seed_response = ctx.tools.call("harness.google_sheets.seed_rows", {"sheets": sheets_section})
    if not seed_response.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Google Sheets seed failed: {seed_response}")
    refs = {TS_TOKEN: ts, "$SLACK_CHANNEL": channel}
    trigger = _replace_value(trigger, refs)
    _require_no_tokens(trigger, "trigger")
    _require_no_tokens(expect, "expect")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": deepcopy(expect),
        "lookup_table": deepcopy(lookup_section),
        "sheets": deepcopy(sheets_section),
        "sheets_seed_response": seed_response,
        "job_context": deepcopy(job_context),
        "seed_slack_message": {"channel": channel, "ts": ts, "text": str(slack_seed["text"])},
    }
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_123992155(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_123992155(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
    if not isinstance(seed.get("sheets"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing sheets section")
    if not isinstance(seed.get("job_context"), dict) or not seed["job_context"].get("job_created_at"):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing pinned job_context.job_created_at")
    message = seed.get("seed_slack_message") if isinstance(seed.get("seed_slack_message"), dict) else {}
    if not (message.get("channel") and message.get("ts")):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing the live seed_slack_message ts")
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "lookup_table": deepcopy(seed["lookup_table"]),
        "sheets": deepcopy(seed["sheets"]),
        "job_context": deepcopy(seed["job_context"]),
        "seed_slack_message": deepcopy(message),
        "expected_channel": ctx.env.slack_channel_override,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    cleanup_response: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = _snapshot(ctx)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx)
    finally:
        # Required cleanup (rerun determinism): the run chat.updates the
        # bot-owned seeded placeholder in place; delete it so reruns of the
        # same variant never see (or double-update) a stale message. The
        # sheets seed fully overwrites the benchmark tab per run and the
        # lookup mock is seeded per run -- neither needs cleanup.
        cleanup_response = ctx.tools.call(
            "slack.delete_message",
            {"channel": message["channel"], "ts": message["ts"]},
        )
        details["cleanup_response"] = cleanup_response
    if not cleanup_response.get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Slack cleanup failed: {cleanup_response}")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_123992155(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> str:
    if set(trigger) != {"parameters", "ts"} or not isinstance(trigger.get("parameters"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly "
            "{'parameters': {'email': ...}, 'ts': ...}"
        )
    parameters = trigger["parameters"]
    if set(parameters) != {"email"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must carry exactly ['email'] "
            f"(the declared bot_command_v2 schema); got {sorted(parameters)}"
        )
    email = str(parameters.get("email") or "")
    if not email.strip() or "@" not in email:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters.email must be a real address")
    if trigger.get("ts") != TS_TOKEN:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger ts must be the {TS_TOKEN!r} token: step 7 "
            "chat.updates the trigger ts, which only works on the live bot-owned "
            "seed-posted message"
        )
    return email


def _require_job_context(job_context: Any) -> str:
    if not isinstance(job_context, dict) or sorted(job_context) != ["job_created_at"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} every variant must pin job_context "
            "{'job_created_at': <ISO-8601 UTC>} (step 3 renders it; no wall clock)"
        )
    stamp = str(job_context["job_created_at"])
    try:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(
            f"recipe {RECIPE_ID} job_created_at must be ISO-8601: {stamp!r}"
        ) from exc
    if parsed.tzinfo is None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} job_created_at must carry an explicit UTC offset: {stamp!r}"
        )
    # Asia/Singapore is fixed UTC+8 (no DST) -- mirrors the step-3 formula.
    return parsed.astimezone(timezone(timedelta(hours=8))).strftime("%d %B %Y")


def _require_lookup_section(section: Any, email: str, completed_text: str) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section) != ["tables"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.lookup_table must be exactly {{'tables': ...}}")
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables) != [TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must declare exactly table {TABLE_ID}"
        )
    rows = tables[TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"recipe {RECIPE_ID} table {TABLE_ID} must be a non-empty explicit list")
    for row in rows:
        if not isinstance(row, dict) or tuple(sorted(row)) != tuple(sorted(LOOKUP_COLS)):
            raise RuntimeError(
                f"recipe {RECIPE_ID} every lookup row must carry exactly col1..col10: {row!r}"
            )
        for col in LOOKUP_COLS:
            if not isinstance(row[col], str) or not row[col].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} lookup row {col} must be a non-empty string "
                    "(col10 especially: a blank col10 criterion would be DROPPED and "
                    f"widen the sheet search to email-only): {row!r}"
                )
        if row["col10"] == completed_text:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seeded col10 must differ from the post-update value "
                f"{completed_text!r} (keeps the pre-update-snapshot trap observable)"
            )
    return rows


def _target_entry(rows: list[dict[str, Any]], email: str) -> tuple[int, dict[str, Any]]:
    matches = [(idx, row) for idx, row in enumerate(rows) if row["col5"] == email]
    if not matches:
        raise RuntimeError(
            f"recipe {RECIPE_ID} no seeded lookup row carries col5 {email!r}: the recipe "
            "is strictly linear -- an unmatched email is a job error, not a variant branch"
        )
    return matches[0]


def _require_sheets_section(section: Any, target: dict[str, Any]) -> int:
    if not isinstance(section, dict) or sorted(section) != ["headers", "rows"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.sheets must be exactly {{headers, rows}}")
    if section["headers"] != SHEET_HEADERS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets.headers must pin the 10 raw column headers "
            f"exactly: {SHEET_HEADERS}"
        )
    rows = section["rows"]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.sheets.rows must be a non-empty list")
    matches: list[int] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row) != sorted(SHEET_HEADERS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded sheet row must carry exactly the 10 "
                f"declared headers: {row!r}"
            )
        for header in SHEET_HEADERS:
            if not isinstance(row[header], str):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} seeded sheet cells must be strings (USER_ENTERED "
                    f"rendered-form pins): {header!r} in {row!r}"
                )
        if not row["Workato Email"].strip():
            raise RuntimeError(f"recipe {RECIPE_ID} every seeded sheet row needs a Workato Email")
        if row["Remarks"] == target["col10"] and row["Workato Email"] == target["col5"]:
            matches.append(idx + 2)
    if len(matches) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} exactly ONE seeded sheet row must match the step-5 "
            f"criteria (Remarks == target col10 {target['col10']!r} AND Workato Email == "
            f"{target['col5']!r}); got rows {matches}"
        )
    return matches[0]


def _require_expect_shape(
    expect: Any,
    *,
    email: str,
    rendered_date: str,
    lookup_rows: list[dict[str, Any]],
    target_index: int,
    target: dict[str, Any],
    sheet_rows: list[dict[str, Any]],
    target_row_number: int,
) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has unexpected keys: {unknown}")
    completed_text = COMPLETED_PREFIX + rendered_date
    if expect["executed_action_count"] != EXECUTED_ACTION_COUNT:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.executed_action_count must be {EXECUTED_ACTION_COUNT} "
            "(6 linear actions incl. the internal logger step)"
        )
    if expect["tools"] != AGENT_TOOL_SEQUENCE:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools must be exactly {AGENT_TOOL_SEQUENCE}"
        )
    if expect["rendered_date"] != rendered_date:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.rendered_date must be {rendered_date!r} "
            f"(job_created_at in Asia/Singapore, '%d %B %Y'); got {expect['rendered_date']!r}"
        )
    expected_slack_text = SECTION_TEXT + (
        f"\nFull Name: {target['col1']}"
        f"\nJob Title: {target['col3']}"
        f"\nEmail: {target['col5']}"
        f"\nPhone: {target['col6']}"
        f"\nLocation: {target['col8']}"
    )
    if expect["slack_text"] != expected_slack_text:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.slack_text must be the exact rendered section + 5 "
            f"attachment-field lines over the FIRST matching lookup entry; want "
            f"{expected_slack_text!r}, got {expect['slack_text']!r}"
        )
    if expect["target_row_number"] != target_row_number:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.target_row_number must be {target_row_number} "
            f"(the single sheet row matching BOTH criteria); got {expect['target_row_number']!r}"
        )
    expected_lookup_rows = []
    for idx, row in enumerate(lookup_rows):
        final_row = dict(row)
        final_row["_row_id"] = idx
        final_row["_created_by"] = "seed"
        if idx == target_index:
            final_row["col9"] = "Completed"
            final_row["col10"] = completed_text
            final_row["_modified_by"] = "agent"
        expected_lookup_rows.append(final_row)
    if expect["final_lookup_rows"] != expected_lookup_rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_lookup_rows must pin the exact final "
            f"table {TABLE_ID} state (only entry {target_index} mutated): "
            f"{json.dumps(expected_lookup_rows, ensure_ascii=False)}"
        )
    expected_sheet_rows = []
    for idx, row in enumerate(sheet_rows):
        final_row = {"row_number": idx + 2, **row}
        if idx + 2 == target_row_number:
            final_row["Status"] = "Completed"
            final_row["Remarks"] = completed_text
        expected_sheet_rows.append(final_row)
    if expect["final_sheet_rows"] != expected_sheet_rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_sheet_rows must pin the exact FORMATTED "
            f"read-back of the whole tab (only row {target_row_number} mutated): "
            f"{json.dumps(expected_sheet_rows, ensure_ascii=False)}"
        )
    _require_expect_items(
        expect,
        email=email,
        completed_text=completed_text,
        target_index=target_index,
        target=target,
        match_count=sum(1 for row in lookup_rows if row["col5"] == email),
        target_row_number=target_row_number,
    )


def _require_expect_items(
    expect: dict[str, Any],
    *,
    email: str,
    completed_text: str,
    target_index: int,
    target: dict[str, Any],
    match_count: int,
    target_row_number: int,
) -> None:
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or len(items) != len(AGENT_TOOL_SEQUENCE):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry"
        )
    for idx, item in enumerate(items):
        if not isinstance(item, dict) or item.get("tool") != AGENT_TOOL_SEQUENCE[idx]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] must pin tool "
                f"{AGENT_TOOL_SEQUENCE[idx]!r}: {item!r}"
            )
        unknown = sorted(set(item.keys()) - _EXPECT_ITEM_KEYS)
        if unknown:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] has unsupported keys: {unknown}"
            )
        if not (set(item.keys()) & _EXPECT_VALUE_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] must pin at least one VALUE key "
                f"({sorted(_EXPECT_VALUE_KEYS)})"
            )
    search_item, update_item, sheets_search_item, sheets_update_item, slack_item = items
    if search_item.get("lookup_table_id") != TABLE_ID or search_item.get("args_contains") != {
        "lookup_table_id": TABLE_ID,
        "parameters": {"col5": email},
    } or search_item.get("result_count") != match_count:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0] must pin the verbatim col5 search "
            f"on table {TABLE_ID} with result_count {match_count}: {search_item!r}"
        )
    if update_item.get("lookup_table_id") != TABLE_ID or update_item.get("args_contains") != {
        "lookup_table_id": TABLE_ID,
        "id": target_index,
        "ignore_not_found": "false",
        "parameters": {"col9": "Completed", "col10": completed_text},
    }:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[1] must pin the full update_entry args "
            f"(id {target_index} = the FIRST matching row): {update_item!r}"
        )
    if sheets_search_item.get("args_contains") != {
        "data": {"col_Remarks": target["col10"], "col_Workato Email": target["col5"]},
        "count": "200",
    } or sheets_search_item.get("result_count") != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[2] must pin the PRE-update col10 "
            f"snapshot criteria {target['col10']!r} + email, count '200', result_count 1: "
            f"{sheets_search_item!r}"
        )
    if sheets_update_item.get("args_contains") != {
        "row_number": target_row_number,
        "data": {"Remarks": completed_text, "Status": "Completed"},
    }:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[3] must pin row_number "
            f"{target_row_number} and the label-mapped Status/Remarks data: "
            f"{sheets_update_item!r}"
        )
    fragments = slack_item.get("text_fragments")
    if slack_item.get("channel") != "override" or not isinstance(fragments, list) or not fragments:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[4] must pin channel 'override' and "
            f"non-empty text_fragments: {slack_item!r}"
        )
    slack_text = str(expect.get("slack_text") or "")
    for fragment in fragments:
        if not isinstance(fragment, str) or not fragment or fragment not in slack_text:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[4] fragment {fragment!r} is not a "
                "substring of expect.slack_text"
            )
    required_fragments = {
        "This request has been `Completed`.",
        f"Full Name: {target['col1']}",
        f"Job Title: {target['col3']}",
        f"Email: {target['col5']}",
        f"Phone: {target['col6']}",
        f"Location: {target['col8']}",
    }
    missing_fragments = sorted(required_fragments - set(fragments))
    if missing_fragments:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[4].text_fragments must include the "
            f"section sentence and all 5 field lines; missing {missing_fragments}"
        )


def _replace_value(value: Any, refs: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_value(item, refs) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_value(item, refs) for item in value]
    if isinstance(value, str):
        out = value
        for token, replacement in refs.items():
            out = out.replace(token, replacement)
        return out
    return value


def _require_no_tokens(value: Any, label: str) -> None:
    leftover = sorted(set(_TOKEN_RE.findall(json.dumps(value))))
    if leftover:
        raise RuntimeError(f"recipe {RECIPE_ID} {label} has unresolved seed tokens: {leftover}")


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return {
        "lookup_table": (ctx.tools.call("harness.lookup_table.snapshot", {}) or {}).get("lookup_table"),
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
