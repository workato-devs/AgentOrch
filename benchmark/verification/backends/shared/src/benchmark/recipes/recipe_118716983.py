from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_118716983


RECIPE_ID = "118716983"
SEED_TYPE = "sheets_slack_allhands_slot_swap_variant"
TRACK = "live_sheets_slack_allhands_slot_swap"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"
TRIGGER_AS = "dd6c40b1"
SEARCH_CURRENT_AS = "d833fbb1"
SEARCH_TARGET_AS = "e65217d3"
POST_REQUEST_AS = "e2021af2"
UPDATE_CURRENT_AS = "8a6f0b71"
UPDATE_TARGET_AS = "be51b2f4"
POST_CONFIRM_CURRENT_AS = "4cd2958c"
POST_CONFIRM_TARGET_AS = "b3290ba6"

# slack_bot.bot_command_v2 /change presentation (as dd6c40b1) parameters
# {presentation_list: required 'topics', new_date: optional} — DESPITE the
# label, new_date carries the OTHER slot's TOPIC (both searches filter
# col_Topics). Strictly linear, no ifs/foreach; every sheet-row pill reads
# rows[current_item] OUTSIDE any foreach = FIRST-MATCH semantics:
#   2  google_sheets.search_spreadsheet_rows_v4_new d833fbb1 (LIVE, sheet
#      'scheduled', count 200) data {col_Topics: #{presentation_list}} —
#      the 'current slot' row.
#   3  google_sheets.search_spreadsheet_rows_v4_new e65217d3 same, data
#      {col_Topics: #{new_date}} — the 'target slot' row.
#   4  slack_bot.post_bot_message e2021af2 channel = e65217d3 first
#      col_Member. Block section_with_button_with_long_action ('Approve',
#      bot_command 58847136): the engine renders ONLY section_text and does
#      NOT wait (user_selection is never dereferenced downstream, so the
#      linearization is behavior-preserving; batch-05 118858162 precedent).
#      section_text interleaves col_Who / col_Scheduled Time / col_Topics
#      pills from BOTH searches with literal \n\t\t separators, the RIGHT
#      SINGLE QUOTE in 'Here’s' and EN-DASH '–' separators — pinned verbatim.
#   5  google_sheets.update_row_v4_new 8a6f0b71: row_number = d833fbb1 first
#      row_number, data {col_Scheduled Time: e65217d3 first value} (the
#      engine maps col_-keys to the plain header 'Scheduled Time').
#   6  google_sheets.update_row_v4_new be51b2f4: row_number = e65217d3 first
#      row_number, data = d833fbb1 first PRE-UPDATE value — the swap works
#      because pills read the STEP-OUTPUT SNAPSHOT, not the live sheet.
#   7  slack_bot.post_bot_message 4cd2958c channel = d833fbb1 first
#      col_Member: 'Your all hands slot on {cur} has been swapped to {tgt}.'
#   8  slack_bot.post_bot_message b3290ba6 reverse confirmation to the
#      e65217d3 member.
#
# Backends: google_sheets LIVE (SHEETS_SPREADSHEET_ID/SHEETS_TAB redirect;
# the tab is seeded LABEL-HEADED — plain 'Topics'/'Scheduled Time'/… headers
# — because update_row writes the stripped header name; the engine adds
# col_<Header> aliases to search rows from the node output schema, probe-
# verified) + slack LIVE (all three channel cells are non-'U' values and
# route to SLACK_CHANNEL_OVERRIDE; posts are terminal observables, never
# re-read). Seeding hazard (probe-verified): harness.google_sheets.seed_rows
# takes {'sheets': {...}} — a {'google_sheets': …} arg key silently seeds
# NOTHING. USER_ENTERED locale-parses date-like cells, so Scheduled Time
# seeds pin RENDERED month-name forms ('July 24' style, live-probe-verified
# round-trip) and never ISO datetimes. No cleanup: every seed fully
# overwrites the redirected tab (replace_rows) and Slack posts are terminal.
#
# Zero-match searches are a faithful ERROR path (row_number int(MISSING)
# raises), NOT a benchmark variant — probe-verified, kept out of variants.

_RAW_PIN_JSON = r"""{"as": "dd6c40b1", "block": [{"as": "d833fbb1", "block": [], "input": {"count": "200", "data": {"col_Topics": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"dd6c40b1\",\"path\":[\"parameters\", \"presentation_list\"]}')}"}, "sheet": "scheduled", "spreadsheet": "<anon>2AbC3DeF4GhI5JkL6MnO7PqR8StU9VwX0YzA1BcD2EfG</anon>", "team_drives": "my_drive"}, "keyword": "action", "name": "search_spreadsheet_rows_v4_new", "number": 2, "provider": "google_sheets", "skip": false}, {"as": "e65217d3", "block": [], "input": {"count": "200", "data": {"col_Topics": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"dd6c40b1\",\"path\":[\"parameters\", \"new_date\"]}')}"}, "sheet": "scheduled", "spreadsheet": "<anon>2AbC3DeF4GhI5JkL6MnO7PqR8StU9VwX0YzA1BcD2EfG</anon>", "team_drives": "my_drive"}, "keyword": "action", "name": "search_spreadsheet_rows_v4_new", "number": 3, "provider": "google_sheets", "skip": false}, {"as": "e2021af2", "block": [], "input": {"blocks": [{"block_type": "section_with_button_with_long_action", "bot_command": "58847136", "button_title": "Approve", "button_type": "continue_flow", "section_text": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"d833fbb1\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_Who\"]}')} is requesting to swap an all-hands slot with you. Here\u2019s the new schedule:\n\t\t#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"e65217d3\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_Scheduled Time\"]}')}: #{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"d833fbb1\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_Topics\"]}')} \u2013 #{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"d833fbb1\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_Who\"]}')}\n\t\t#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"d833fbb1\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_Scheduled Time\"]}')}: #{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"e65217d3\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_Topics\"]}')} \u2013 #{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"e65217d3\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_Who\"]}')}", "style": "default"}], "channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"e65217d3\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_Member\"]}')}"}, "keyword": "action", "name": "post_bot_message", "number": 4, "provider": "slack_bot", "skip": false}, {"as": "8a6f0b71", "block": [], "input": {"data": {"col_Scheduled Time": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"e65217d3\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_Scheduled Time\"]}')}"}, "row_number": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"d833fbb1\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"row_number\"]}')}", "sheet": "scheduled", "spreadsheet": "<anon>2AbC3DeF4GhI5JkL6MnO7PqR8StU9VwX0YzA1BcD2EfG</anon>", "team_drives": "my_drive"}, "keyword": "action", "name": "update_row_v4_new", "number": 5, "provider": "google_sheets", "skip": false}, {"as": "be51b2f4", "block": [], "input": {"data": {"col_Scheduled Time": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"d833fbb1\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_Scheduled Time\"]}')}"}, "row_number": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"e65217d3\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"row_number\"]}')}", "sheet": "scheduled", "spreadsheet": "<anon>2AbC3DeF4GhI5JkL6MnO7PqR8StU9VwX0YzA1BcD2EfG</anon>", "team_drives": "my_drive"}, "keyword": "action", "name": "update_row_v4_new", "number": 6, "provider": "google_sheets", "skip": false}, {"as": "4cd2958c", "block": [], "input": {"blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": "Your all hands slot on #{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"d833fbb1\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_Scheduled Time\"]}')} has been swapped to #{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"e65217d3\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_Scheduled Time\"]}')}."}], "channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"d833fbb1\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_Member\"]}')}"}, "keyword": "action", "name": "post_bot_message", "number": 7, "provider": "slack_bot", "skip": false}, {"as": "b3290ba6", "block": [], "input": {"blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": "Your all hands slot on #{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"e65217d3\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_Scheduled Time\"]}')} has been swapped to #{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"d833fbb1\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_Scheduled Time\"]}')}."}], "channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"e65217d3\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_Member\"]}')}"}, "keyword": "action", "name": "post_bot_message", "number": 8, "provider": "slack_bot", "skip": false}], "input": {"allow_dialog": "true", "domain": "change", "name": "presentation", "parameters": "[{\"name\":\"presentation_list\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"topics\"},{\"name\":\"new_date\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"new date\"}]", "scope": "timing"}, "keyword": "trigger", "name": "bot_command_v2", "number": 1, "provider": "slack_bot", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

SHEET_HEADERS = [
    "Topics",
    "Member",
    "GC",
    "Scheduled Time",
    "Epoch Time",
    "2 Weeks Reminder",
    "2 Days Reminder",
    "Today",
    "Checks (2 Wks)",
    "Checks (2 Days)",
    "Who",
    "Search",
]
COL_ALIASES = ["col_" + header for header in SHEET_HEADERS]

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (SEARCH_CURRENT_AS, "google_sheets", "search_spreadsheet_rows_v4_new"),
    (SEARCH_TARGET_AS, "google_sheets", "search_spreadsheet_rows_v4_new"),
    (POST_REQUEST_AS, "slack_bot", "post_bot_message"),
    (UPDATE_CURRENT_AS, "google_sheets", "update_row_v4_new"),
    (UPDATE_TARGET_AS, "google_sheets", "update_row_v4_new"),
    (POST_CONFIRM_CURRENT_AS, "slack_bot", "post_bot_message"),
    (POST_CONFIRM_TARGET_AS, "slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "google_sheets.search_spreadsheet_rows_v4_new",
    "slack.post_message",
    "google_sheets.update_row_v4_new",
]
ALLOWED_TOOLS: list[str] = [
    "google_sheets.search_spreadsheet_rows_v4_new",
    "google_sheets.update_row_v4_new",
    "slack.post_message",
]
EXPECTED_TOOL_SEQUENCE = [
    "google_sheets.search_spreadsheet_rows_v4_new",
    "google_sheets.search_spreadsheet_rows_v4_new",
    "slack.post_message",
    "google_sheets.update_row_v4_new",
    "google_sheets.update_row_v4_new",
    "slack.post_message",
    "slack.post_message",
]
BRANCHES = ("swap_two_slots", "swap_with_decoys")
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "branch",
    "swap",
    "slack_texts",
    "final_rows",
    "final_row_count",
)
SWAP_KEYS = (
    "current_row_number",
    "target_row_number",
    "current_scheduled_time",
    "target_scheduled_time",
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


def validate_118716983(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    # Load-bearing schema pins the tree pin does NOT cover (the engine reads
    # these schemas at runtime): the search nodes must declare all 12
    # col_<Header> output names (search-row aliasing) and the update nodes'
    # input schema must label 'col_Scheduled Time' -> 'Scheduled Time'
    # (data-key mapping onto the label-headed live tab).
    for node in _walk_nodes(raw):
        as_id = str(node.get("as") or "")
        if as_id in (SEARCH_CURRENT_AS, SEARCH_TARGET_AS):
            names = _schema_col_names(node)
            if sorted(names) != sorted(COL_ALIASES):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} search node {as_id} output schema col_ names "
                    f"changed: {sorted(names)}"
                )
        if as_id in (UPDATE_CURRENT_AS, UPDATE_TARGET_AS):
            labels = _column_labels(node)
            if labels.get("col_Scheduled Time") != "Scheduled Time":
                raise RuntimeError(
                    f"recipe {RECIPE_ID} update node {as_id} no longer maps "
                    f"'col_Scheduled Time' to the plain header: {labels}"
                )
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
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


def seed_118716983(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118716983(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    presentation_list, new_date = _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["sheets"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed must declare exactly the sheets section")
    rows = _require_sheets_section(seed_in["sheets"])
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    _require_expect_items(expect)
    if expect.get("branch") not in BRANCHES:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.branch must be one of {BRANCHES}; got {expect.get('branch')!r}"
        )
    if expect.get("executed_action_count") != 7 or expect.get("tools") != EXPECTED_TOOL_SEQUENCE:
        raise RuntimeError(
            f"recipe {RECIPE_ID} is strictly linear: executed_action_count must be 7 and "
            f"expect.tools must be {EXPECTED_TOOL_SEQUENCE}"
        )
    _require_swap_coherence(expect, rows, presentation_list, new_date)
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole run"
        )
    # LIVE seed: fully overwrite the redirected benchmark tab. The arg key
    # MUST be 'sheets' — a 'google_sheets' key silently seeds nothing
    # (probe-verified live_tools hazard).
    seed_response = ctx.tools.call(
        "harness.google_sheets.seed_rows", {"sheets": deepcopy(seed_in["sheets"])}
    )
    if not seed_response.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Google Sheets seed failed: {seed_response}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "sheets": deepcopy(seed_in["sheets"]),
        "sheets_seed_response": deepcopy(seed_response),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_118716983(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118716983(raw)
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    if not isinstance(seed.get("sheets"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing the sheets section")
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    initial_snapshot = ctx.tools.call("harness.google_sheets.snapshot", {})
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = ctx.tools.call("harness.google_sheets.snapshot", {})
    # No cleanup: the seed fully overwrites the redirected tab on every run
    # (replace_rows) and the Slack posts are terminal observables.
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
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
            "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_118716983(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> tuple[str, str]:
    if sorted(trigger.keys()) != ["parameters"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'parameters': ...}}; "
            f"got {sorted(trigger.keys())}"
        )
    parameters = trigger["parameters"]
    if not isinstance(parameters, dict) or sorted(parameters.keys()) != ["new_date", "presentation_list"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must be exactly "
            "{'presentation_list', 'new_date'} (new_date is the OTHER slot's TOPIC)"
        )
    for key in ("presentation_list", "new_date"):
        if not isinstance(parameters.get(key), str) or not parameters[key].strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger parameters.{key} must be a non-empty string "
                "(a zero-match search is a faithful error path, not a variant)"
            )
    return parameters["presentation_list"], parameters["new_date"]


def _require_sheets_section(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["headers", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets must be exactly {{'headers': ..., 'rows': ...}}"
        )
    if section["headers"] != SHEET_HEADERS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets.headers must be the LABEL-HEADED 12-column "
            f"schedule schema {SHEET_HEADERS} — update_row writes the stripped header "
            "name, so a col_-literal tab would append ghost columns"
        )
    rows = section["rows"]
    if not isinstance(rows, list) or len(rows) < 3:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets.rows needs the swap pair plus at least one "
            "decoy row"
        )
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} sheet row {idx} must be an object")
        if sorted(row.keys()) != sorted(SHEET_HEADERS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} sheet row {idx} must carry exactly the 12 headers; "
                f"got {sorted(row.keys())}"
            )
        for key, value in row.items():
            if not isinstance(value, str):
                raise RuntimeError(f"recipe {RECIPE_ID} sheet row {idx}.{key} must be a string")
        if row["Member"].startswith("U"):
            raise RuntimeError(
                f"recipe {RECIPE_ID} sheet row {idx} Member must NOT start with 'U' — "
                "U-prefixed cells pass VERBATIM as live DM targets instead of routing to "
                "SLACK_CHANNEL_OVERRIDE"
            )
    return rows


def _require_swap_coherence(
    expect: dict[str, Any],
    rows: list[dict[str, Any]],
    presentation_list: str,
    new_date: str,
) -> None:
    swap = expect.get("swap")
    if not isinstance(swap, dict) or sorted(swap.keys()) != sorted(SWAP_KEYS):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.swap must pin exactly {sorted(SWAP_KEYS)}")
    current_matches = [idx + 2 for idx, row in enumerate(rows) if row["Topics"] == presentation_list]
    target_matches = [idx + 2 for idx, row in enumerate(rows) if row["Topics"] == new_date]
    if not current_matches or not target_matches:
        raise RuntimeError(
            f"recipe {RECIPE_ID} both trigger topics must match seeded rows "
            f"(presentation_list matches {current_matches}, new_date matches {target_matches})"
        )
    current_row = current_matches[0]
    target_row = target_matches[0]
    if current_row == target_row:
        raise RuntimeError(f"recipe {RECIPE_ID} the swap pair must be two DIFFERENT rows")
    current_time = rows[current_row - 2]["Scheduled Time"]
    target_time = rows[target_row - 2]["Scheduled Time"]
    if current_time == target_time:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the swap pair must carry DIFFERENT Scheduled Time values "
            "(otherwise the swap is unobservable)"
        )
    pinned = (
        swap.get("current_row_number"), swap.get("target_row_number"),
        swap.get("current_scheduled_time"), swap.get("target_scheduled_time"),
    )
    derived = (current_row, target_row, current_time, target_time)
    if pinned != derived:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.swap {pinned} does not match the seeded first-match "
            f"semantics {derived}"
        )
    texts = expect.get("slack_texts")
    if (
        not isinstance(texts, list)
        or len(texts) != 3
        or not all(isinstance(text, str) and text.strip() for text in texts)
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.slack_texts must pin the 3 rendered post texts in "
            "step order (request block, current-member confirmation, target-member confirmation)"
        )
    final_rows = expect.get("final_rows")
    if not isinstance(final_rows, list) or len(final_rows) != len(rows):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_rows must pin every seeded row "
            f"({len(rows)} rows)"
        )
    if expect.get("final_row_count") != len(rows):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.final_row_count must equal the seeded row count")


def _require_expect_items(expect: dict[str, Any]) -> None:
    items = expect.get("tool_expectations")
    if not isinstance(items, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must be a list")
    for idx, item in enumerate(items):
        if not isinstance(item, dict) or not item.get("tool"):
            raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[{idx}] must be an object with a tool")
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
        if item.get("tool") == "slack.post_message":
            if item.get("channel") != "override" or not item.get("text_fragments"):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} tool_expectations[{idx}] slack posts must pin "
                    "channel 'override' and non-empty text_fragments"
                )


def _schema_col_names(node: dict[str, Any]) -> list[str]:
    names: list[str] = []

    def walk(entries: Any) -> None:
        for entry in entries or []:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name") or "")
            if name.startswith("col_"):
                names.append(name)
            walk(entry.get("properties"))

    walk(node.get("extended_output_schema"))
    return names


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


def _normalize_tree(node: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "number": node.get("number"),
        "keyword": node.get("keyword"),
        "provider": node.get("provider") or "",
        "name": node.get("name") or "",
        "as": node.get("as") or "",
        "skip": bool(node.get("skip")),
    }
    if not out["skip"]:
        out["input"] = node.get("input")
    if node.get("keyword") == "foreach":
        out["repeat_mode"] = node.get("repeat_mode")
        out["source"] = node.get("source")
    if isinstance(node.get("filter"), dict):
        out["filter"] = node["filter"]
    out["block"] = [
        _normalize_tree(child) for child in node.get("block") or [] if isinstance(child, dict)
    ]
    return out


def _first_tree_mismatch(actual: Any, expected: Any, path: str = "root") -> str:
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            if key not in actual:
                return f"{path}.{key}: missing in raw recipe"
            if key not in expected:
                return f"{path}.{key}: unexpected in raw recipe"
            found = _first_tree_mismatch(actual[key], expected[key], f"{path}.{key}")
            if found:
                return found
        return ""
    if isinstance(expected, list) and isinstance(actual, list):
        if len(actual) != len(expected):
            return f"{path}: length {len(actual)} != {len(expected)}"
        for idx, (act, exp) in enumerate(zip(actual, expected)):
            found = _first_tree_mismatch(act, exp, f"{path}[{idx}]")
            if found:
                return found
        return ""
    if actual != expected:
        return f"{path}: {json.dumps(actual, default=str)[:200]} != {json.dumps(expected, default=str)[:200]}"
    return ""


def _walk_nodes(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        found.append(child)
        found.extend(_walk_nodes(child))
    return found


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
