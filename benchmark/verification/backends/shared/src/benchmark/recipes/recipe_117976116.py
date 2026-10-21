from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_117976116


RECIPE_ID = "117976116"
SEED_TYPE = "sheets_admin_answers_slack_start_variant"
TRACK = "live_sheets_slack_batch_email_admin_update"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"
TRIGGER_AS = "3605cd52"
UPDATE_STEPS = (
    ("62bab84a", "name", "2"),
    ("c26913a7", "chilipiper", "3"),
    ("f8d7bbd5", "duration", "4"),
    ("e3445cc9", "blurb", "5"),
)
REPLY_AS = "64c5a9f3"
PARAM_KEYS = ("name", "chilipiper", "duration", "blurb")
SHEET_HEADERS = ["Question", "Answer", "Search", "Sets of Gift Cards"]
RAW_SHEET = "ADMIN"
RAW_SPREADSHEET = "<anon>2AbC3DeF4GhI5JkL6MnO7PqR8StU9VwX0YzA1BcD2EfG</anon>"
TS_RE = re.compile(r"^\d{10}\.\d{6}$")
CHANNEL_RE = re.compile(r"^C[A-Z0-9]+$")
# USER_ENTERED render-stability guards: seeded/param cell values must read
# back byte-identical from the live tab (dates/booleans/formulas get locale-
# parsed or evaluated, batch-06 lesson).
DATE_LIKE_RE = re.compile(r"^\d{1,4}[-/]\d{1,2}([-/]\d{1,4})?$")
# Rendered verbatim from the step-6 blocks (both section_texts render via
# slack_text regardless of block_type; the Start button / bot_command
# 44341431 / style are dropped metadata in a TEXT reply).
SECTION1_TEXT = (
    "> You have triggered the Batch Email Sender Bot. \U0001f916\n\n"
    "*Please input your email address here*:\n\n"
    "`https://docs.google.com/spreadsheets/d/"
    "<anon>3HiJ4KlM5NoPqRsT6Uv7WxY8Za9BcDeFgHiJkLmNoPqR</anon>/edit#gid=0`\n\n"
    "*Here are the instructions*:\n"
    "1. Please copy-paste your users' names, emails, and location in the sheet from snowflake.\n"
    "2. Drag Column D-F down. (Use row 2 as reference)\n"
    "3. Ensure that your participants' country are eligible for a gift card: "
    "https://app.workato.com/lookup_tables/3211451\n\n"
    "Quick tip: Deleting rows marked “Failed Test” can help cut down on waiting time.\n\n"
    "*Note that you have to make sure you have already login into Workato Design Team workspace."
)
SECTION2_TEXT = 'Press "Start" once you are ready!'

# slack_bot.bot_command_v2 (as 3605cd52, domain 'start', name 'update', scope
# 'sender', allow_dialog true; parameters name/chilipiper/duration/blurb ALL
# required). Dereferenced trigger pills: all 4 parameters + context.user_name
# (+ channel/message_ts consumed by the reply routing). Body — STRICTLY
# LINEAR, 5 unconditional actions, no if/try/foreach:
#   2  google_sheets.update_row_v4_new 62bab84a 'Name'   row 2 col_Answer=name
#   3  google_sheets.update_row_v4_new c26913a7 'Chili'  row 3 col_Answer=chilipiper
#   4  google_sheets.update_row_v4_new f8d7bbd5 'Duration' row 4 col_Answer=duration
#   5  google_sheets.update_row_v4_new e3445cc9 'Blurb'  row 5 col_Answer=blurb
#      (col_Answer -> header 'Answer' via the node schema labels; row_number
#      stays the LITERAL string '2'..'5'; the anon spreadsheet id + sheet
#      'ADMIN' ride along in the args while the live client binds the
#      env-bound benchmark tab. row_number is 1-based INCLUDING the header
#      row -> row 2 = FIRST data row; positional addressing, the Question
#      column is never consulted — probe-verified.)
#   6  slack_bot.post_bot_reply_v2 64c5a9f3: channel = SLACK_CHANNEL_OVERRIDE
#      (env wins over trigger channel), thread_ts = trigger message_ts, text
#      = section1 + '\n' + section2 + '\n' + context.user_name (both blocks'
#      section_texts render, incl. the section_with_button_with_long_action;
#      the Start button/bot_command 44341431 are dropped metadata; the anon
#      google-docs link stays a literal).
#
# Branch mapping: strictly linear -> every variant runs the same 5-step path;
# variants vary the DATA traps:
# - variant_00 update_all_four_and_reply: canonical ADMIN layout (Question
#   labels match the step comments rows 2-5) + a row-6 decoy that must stay
#   byte-identical (proves exactly rows 2-5 written, no append).
# - variant_01 overwrite_previous_values: rows 2-5 pre-loaded with PRIOR
#   Answer values (update-in-place proof) and the Question labels SHUFFLED
#   against the step comments (proves positional row_number addressing, not
#   Question matching); non-Answer columns byte-untouched.
# Non-branches (probe-verified hazards, not variants): a missing parameter
# resolves MISSING -> writes null; a short tab (< 5 rows incl. header) makes
# update_row write into blank rows. The seeder fail-fasts both (>= 4 data
# rows, all 4 params non-empty).
#
# Backends: google_sheets LIVE (harness.google_sheets.seed_rows fully
# overwrites the env-bound benchmark tab per run -> deterministic reruns, no
# sheet cleanup; USER_ENTERED means pins are the rendered read-back — the
# seeder rejects date-like/TRUE/FALSE/formula-prefixed cells). slack LIVE:
# the reply threads on the pinned synthetic trigger message_ts (live Slack
# accepts an unknown thread_ts — registered 118554940 precedent); the post
# is a terminal observable, never re-read -> no cleanup.

_STRUCTURE_PINS_JSON = r'''
[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "3605cd52",
  "provider": "slack_bot",
  "name": "bot_command_v2",
  "skip": false,
  "input": {
   "allow_dialog": "true",
   "domain": "start",
   "name": "update",
   "parameters": "[\n  {\n    \"name\": \"name\",\n    \"type\": \"string\",\n    \"optional\": false,\n    \"control_type\": \"text\"\n  },\n  {\n    \"name\": \"chilipiper\",\n    \"type\": \"string\",\n    \"optional\": false,\n    \"control_type\": \"text\"\n  },\n  {\n    \"name\": \"duration\",\n    \"type\": \"string\",\n    \"optional\": false,\n    \"control_type\": \"text\"\n  },\n  {\n    \"name\": \"blurb\",\n    \"type\": \"string\",\n    \"optional\": false,\n    \"control_type\": \"text\"\n  }\n]",
   "scope": "sender"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "62bab84a",
  "provider": "google_sheets",
  "name": "update_row_v4_new",
  "skip": false,
  "input": {
   "data": {
    "col_Answer": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"3605cd52\",\"path\":[\"parameters\", \"name\"]}')}"
   },
   "row_number": "2",
   "sheet": "ADMIN",
   "spreadsheet": "<anon>2AbC3DeF4GhI5JkL6MnO7PqR8StU9VwX0YzA1BcD2EfG</anon>",
   "team_drives": "my_drive"
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "c26913a7",
  "provider": "google_sheets",
  "name": "update_row_v4_new",
  "skip": false,
  "input": {
   "data": {
    "col_Answer": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"3605cd52\",\"path\":[\"parameters\", \"chilipiper\"]}')}"
   },
   "row_number": "3",
   "sheet": "ADMIN",
   "spreadsheet": "<anon>2AbC3DeF4GhI5JkL6MnO7PqR8StU9VwX0YzA1BcD2EfG</anon>",
   "team_drives": "my_drive"
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "f8d7bbd5",
  "provider": "google_sheets",
  "name": "update_row_v4_new",
  "skip": false,
  "input": {
   "data": {
    "col_Answer": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"3605cd52\",\"path\":[\"parameters\", \"duration\"]}')}"
   },
   "row_number": "4",
   "sheet": "ADMIN",
   "spreadsheet": "<anon>2AbC3DeF4GhI5JkL6MnO7PqR8StU9VwX0YzA1BcD2EfG</anon>",
   "team_drives": "my_drive"
  }
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "e3445cc9",
  "provider": "google_sheets",
  "name": "update_row_v4_new",
  "skip": false,
  "input": {
   "data": {
    "col_Answer": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"3605cd52\",\"path\":[\"parameters\", \"blurb\"]}')}"
   },
   "row_number": "5",
   "sheet": "ADMIN",
   "spreadsheet": "<anon>2AbC3DeF4GhI5JkL6MnO7PqR8StU9VwX0YzA1BcD2EfG</anon>",
   "team_drives": "my_drive"
  }
 },
 {
  "keyword": "action",
  "number": 6,
  "as": "64c5a9f3",
  "provider": "slack_bot",
  "name": "post_bot_reply_v2",
  "skip": false,
  "input": {
   "blocks": [
    {
     "block_type": "section_with_text",
     "button_type": "continue_flow",
     "section_text": "> You have triggered the Batch Email Sender Bot. 🤖\n\n*Please input your email address here*:\n\n`https://docs.google.com/spreadsheets/d/<anon>3HiJ4KlM5NoPqRsT6Uv7WxY8Za9BcDeFgHiJkLmNoPqR</anon>/edit#gid=0`\n\n*Here are the instructions*:\n1. Please copy-paste your users' names, emails, and location in the sheet from snowflake.\n2. Drag Column D-F down. (Use row 2 as reference)\n3. Ensure that your participants' country are eligible for a gift card: https://app.workato.com/lookup_tables/3211451\n\nQuick tip: Deleting rows marked “Failed Test” can help cut down on waiting time.\n\n*Note that you have to make sure you have already login into Workato Design Team workspace."
    },
    {
     "block_type": "section_with_button_with_long_action",
     "bot_command": "44341431",
     "button_title": "Start",
     "button_type": "bot_command",
     "section_text": "Press \"Start\" once you are ready!",
     "style": "default"
    }
   ],
   "text": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"3605cd52\",\"path\":[\"context\", \"user_name\"]}')}"
  }
 }
]
'''

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "google_sheets.update_row_v4_new",
    "slack.post_reply",
]
ALLOWED_TOOLS: list[str] = [
    "google_sheets.update_row_v4_new",
    "slack.post_reply",
]
EXPECTED_TOOL_SEQUENCE = [
    "google_sheets.update_row_v4_new",
    "google_sheets.update_row_v4_new",
    "google_sheets.update_row_v4_new",
    "google_sheets.update_row_v4_new",
    "slack.post_reply",
]
EXECUTED_ACTION_COUNT = 5
BRANCHES = ("update_all_four_and_reply", "overwrite_previous_values")
REQUIRED_EXPECT_KEYS = (
    "branch",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "reply_text",
    "final_rows",
    "final_row_count",
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


def validate_117976116(raw: dict[str, Any]) -> dict[str, Any]:
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
    # Load-bearing schema pin the tree pin does NOT cover: the engine maps
    # col_Answer onto the live tab through the update nodes' input schema
    # labels at runtime (raw_executor._sheet_column_labels).
    for node in _walk_nodes(raw):
        if str(node.get("name") or "") == "update_row_v4_new":
            labels = _column_labels(node)
            if labels.get("col_Answer") != "Answer":
                raise RuntimeError(
                    f"recipe {RECIPE_ID} update node {node.get('as')} no longer labels "
                    f"col_Answer as 'Answer': {labels}"
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


def seed_117976116(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_117976116(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole "
            "run instead of exercising a recipe branch"
        )
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    if not ctx.env.sheets_spreadsheet_id or not ctx.env.sheets_tab:
        raise RuntimeError("missing SHEETS_SPREADSHEET_ID / SHEETS_TAB; refusing to guess")
    trigger = trigger_input(ctx)
    params, user_name = _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["sheets"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed must declare exactly the sheets section")
    rows = _require_sheets_section(seed_in["sheets"], params)
    expect = data.get("expect")
    _require_expect_shape(expect, params=params, user_name=user_name, rows=rows)

    # LIVE seed: fully overwrite the env-bound benchmark tab (replace_rows).
    seed_response = ctx.tools.call(
        "harness.google_sheets.seed_rows", {"sheets": deepcopy(seed_in["sheets"])}
    )
    if not seed_response.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Google Sheets seed failed: {seed_response}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": deepcopy(expect),
        "sheets": deepcopy(seed_in["sheets"]),
        "sheets_seed_response": deepcopy(seed_response),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_117976116(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_117976116(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("sheets"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing the sheets section")
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    initial_snapshot = ctx.tools.call("harness.google_sheets.snapshot", {})
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = ctx.tools.call("harness.google_sheets.snapshot", {})
    # No cleanup: the seed fully overwrites the env-bound tab per run
    # (replace_rows) and the threaded reply is a terminal observable.
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "expect": expect,
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "expected_channel": ctx.env.slack_channel_override,
            "sheets": deepcopy(seed["sheets"]),
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
            "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_117976116(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_render_stable(value: str, where: str) -> None:
    if value != value.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} {where} must not carry leading/trailing whitespace "
            f"(USER_ENTERED trims): {value!r}"
        )
    if value.startswith(("=", "+")):
        raise RuntimeError(
            f"recipe {RECIPE_ID} {where} must not start with '='/'+' "
            f"(USER_ENTERED would evaluate a formula): {value!r}"
        )
    if value.upper() in {"TRUE", "FALSE"} or DATE_LIKE_RE.match(value):
        raise RuntimeError(
            f"recipe {RECIPE_ID} {where} must be render-stable under USER_ENTERED "
            f"(no booleans/date-like forms): {value!r}"
        )


def _require_trigger_shape(trigger: dict[str, Any]) -> tuple[dict[str, str], str]:
    if sorted(trigger.keys()) != ["channel", "context", "message_ts", "parameters"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly parameters + context + "
            f"channel + message_ts; got {sorted(trigger.keys())}"
        )
    parameters = trigger["parameters"]
    if not isinstance(parameters, dict) or sorted(parameters.keys()) != sorted(PARAM_KEYS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must carry exactly {sorted(PARAM_KEYS)} "
            "(all four are REQUIRED in the declared bot_command_v2 schema; a missing one "
            "would write null into the sheet)"
        )
    for key in PARAM_KEYS:
        value = parameters.get(key)
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters.{key} must be a non-empty string")
        _require_render_stable(value, f"parameters.{key}")
    values = [parameters[key] for key in PARAM_KEYS]
    if len(set(values)) != len(values):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the 4 parameter values must be pairwise distinct "
            f"(keeps the row 2-5 mapping observable): {values}"
        )
    context = trigger["context"]
    if not isinstance(context, dict) or sorted(context.keys()) != ["user_name"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger context must be exactly {{'user_name': ...}} "
            "(the reply's top-level text pill)"
        )
    user_name = context.get("user_name")
    if not isinstance(user_name, str) or not user_name.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} context.user_name must be a non-empty string (Slack "
            "always supplies it; an empty one would silently drop the reply's last line)"
        )
    if not isinstance(trigger.get("channel"), str) or not CHANNEL_RE.match(trigger["channel"]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger channel must be a C-prefixed Slack channel id "
            f"(the env override wins at run time); got {trigger.get('channel')!r}"
        )
    if not isinstance(trigger.get("message_ts"), str) or not TS_RE.match(trigger["message_ts"]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger message_ts must look like a Slack ts "
            f"(the reply threads on it); got {trigger.get('message_ts')!r}"
        )
    return {key: parameters[key] for key in PARAM_KEYS}, user_name


def _require_sheets_section(section: Any, params: dict[str, str]) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["headers", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets must be exactly {{'headers': ..., 'rows': ...}}"
        )
    if section["headers"] != SHEET_HEADERS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets.headers must be the 4-column ADMIN schema "
            f"{SHEET_HEADERS} (the update nodes label col_Answer -> 'Answer')"
        )
    rows = section["rows"]
    if not isinstance(rows, list) or len(rows) < 4:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets.rows needs at least 4 data rows (steps "
            "2-5 write rows 2-5; a shorter tab would make update_row write into "
            "blank rows — probe-verified hazard)"
        )
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(SHEET_HEADERS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} sheet row {idx} must carry exactly the 4 headers; "
                f"got {sorted(row.keys()) if isinstance(row, dict) else row!r}"
            )
        for key, value in row.items():
            if not isinstance(value, str):
                raise RuntimeError(f"recipe {RECIPE_ID} sheet row {idx}.{key} must be a string")
            if value:
                _require_render_stable(value, f"sheets.rows[{idx}].{key}")
    for step_idx, (_, param_key, row_number) in enumerate(UPDATE_STEPS):
        seeded = rows[int(row_number) - 2]["Answer"]
        if seeded == params[param_key]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seeded row {row_number} Answer must differ from "
                f"parameters.{param_key} {params[param_key]!r} (keeps the step-"
                f"{step_idx + 2} write observable)"
            )
    return rows


def _require_expect_shape(
    expect: Any,
    *,
    params: dict[str, str],
    user_name: str,
    rows: list[dict[str, Any]],
) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has unexpected keys: {unknown}")
    if expect["branch"] not in BRANCHES:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.branch must be one of {BRANCHES}; got {expect['branch']!r}"
        )
    if expect["executed_action_count"] != EXECUTED_ACTION_COUNT or expect["tools"] != EXPECTED_TOOL_SEQUENCE:
        raise RuntimeError(
            f"recipe {RECIPE_ID} is strictly linear: executed_action_count must be "
            f"{EXECUTED_ACTION_COUNT} and expect.tools must be {EXPECTED_TOOL_SEQUENCE}"
        )
    expected_reply = SECTION1_TEXT + "\n" + SECTION2_TEXT + "\n" + user_name
    if expect["reply_text"] != expected_reply:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.reply_text must be the exact 2 rendered section "
            f"texts + trailing user_name; want {expected_reply!r}, got {expect['reply_text']!r}"
        )
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or len(items) != len(EXPECTED_TOOL_SEQUENCE):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry"
        )
    for idx, item in enumerate(items):
        if not isinstance(item, dict) or item.get("tool") != EXPECTED_TOOL_SEQUENCE[idx]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] must pin tool "
                f"{EXPECTED_TOOL_SEQUENCE[idx]!r}: {item!r}"
            )
        unknown_keys = sorted(set(item.keys()) - _EXPECT_ITEM_KEYS)
        if unknown_keys:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] has unsupported keys: {unknown_keys}"
            )
        if not (set(item.keys()) & _EXPECT_VALUE_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] must pin at least one VALUE key "
                f"({sorted(_EXPECT_VALUE_KEYS)})"
            )
    for idx, (_, param_key, row_number) in enumerate(UPDATE_STEPS):
        expected_args = {
            "sheet": RAW_SHEET,
            "spreadsheet": RAW_SPREADSHEET,
            "row_number": row_number,
            "data": {"Answer": params[param_key]},
        }
        if items[idx].get("args_contains") != expected_args:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] must pin the verbatim "
                f"update args (LITERAL string row_number, label-decoded data): "
                f"{json.dumps(expected_args, ensure_ascii=False)}"
            )
    reply_item = items[4]
    if reply_item.get("channel") != "override" or reply_item.get("text_fragments") != [expected_reply]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[4] must pin channel 'override' and "
            "text_fragments [<the full reply_text>]"
        )
    expected_final = []
    updated = {row_number: params[param_key] for _, param_key, row_number in UPDATE_STEPS}
    for idx, row in enumerate(rows):
        final_row = {"row_number": idx + 2, **row}
        if str(idx + 2) in updated:
            final_row["Answer"] = updated[str(idx + 2)]
        expected_final.append(final_row)
    if expect["final_rows"] != expected_final:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_rows must pin the whole final tab "
            f"(only rows 2-5 Answer mutated): {json.dumps(expected_final, ensure_ascii=False)}"
        )
    if expect["final_row_count"] != len(rows):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.final_row_count must equal the seeded row count")


def _column_labels(node: dict[str, Any]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for schema in node.get("extended_input_schema") or []:
        if not isinstance(schema, dict) or schema.get("name") not in {"columns", "data", "rows"}:
            continue
        for prop in schema.get("properties") or []:
            if not isinstance(prop, dict):
                continue
            name = str(prop.get("name") or "")
            label = str(prop.get("label") or "")
            if name and label:
                labels[name] = label
    return labels


def _walk_nodes(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        found.append(child)
        found.extend(_walk_nodes(child))
    return found


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
