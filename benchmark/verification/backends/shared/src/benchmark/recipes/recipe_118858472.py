from __future__ import annotations

import datetime as _dt
import json
import re
import zoneinfo
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_118858472


RECIPE_ID = "118858472"
SEED_TYPE = "clock_sheets_slack_onduty_digest_variant"
TRACK = "live_sheets_slack_onduty_digest"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "c37baaa3"
WEEK_DECLARE_AS = "e4240616"
SEARCH_AS = "9e3dbecf"
US_DECLARE_AS = "fce3e11c"
POST_BIZTECH_AS = "4bce594e"
POST_BTHR_AS = "2f65a9ec"
ZONE = "Europe/London"  # semantic zone inside the <anon> wrapper (de-tagged by resolve_zone_info)
SHEET_HEADERS = [
    "col_APJ TIME",
    "col_EMEA TIME",
    "col_US TIME",
    "col_WEEK NO",
    "col_DATE",
    "col_START TIME",
    "col_END TIME",
    "col_BT APJ",
    "col_BT EMEA",
    "col_BT US 1",
    "col_BT US 2",
    "col_BT FLEXI",
    "col_D-APJ",
    "col_D-EMEA",
    "col_D-US",
    "col_D-US-Alt",
    "col_D-Flexi",
]
DIGEST_COLUMNS = (
    "col_WEEK NO",
    "col_DATE",
    "col_BT APJ",
    "col_BT EMEA",
    "col_BT US 1",
    "col_BT US 2",
    "col_BT FLEXI",
    "col_D-APJ",
    "col_D-EMEA",
    "col_D-US",
    "col_D-Flexi",
)


_RAW_PIN_JSON = r"""{"as": "c37baaa3", "block": [{"as": "e4240616", "block": [], "input": {"variables": {"data": {"week_no": "=now.in_time_zone(\"<anon>Europe/London</anon>\").yweek"}, "schema": "[{\"name\":\"week_no\",\"type\":\"string\",\"optional\":true,\"label\":\"week_no\",\"control_type\":\"text\"}]"}}, "keyword": "action", "name": "declare_variable", "number": 2, "provider": "workato_variable", "skip": false}, {"as": "9e3dbecf", "block": [], "input": {"count": "200", "data": {"col_WEEK NO": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"e4240616\",\"path\":[\"week_no\"]}')}"}, "sheet": "2025", "spreadsheet": "<anon>2AbC3DeF4GhI5JkL6MnO7PqR8StU9VwX0YzA1BcD2EfG</anon>", "team_drives": "my_drive"}, "keyword": "action", "name": "search_spreadsheet_rows_v4_new", "number": 3, "provider": "google_sheets", "skip": false}, {"as": "fce3e11c", "block": [], "input": {"variables": {"data": {"us_shift_period": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_D-US-Alt\"]}').present?\n  \"#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_D-US\"]}')}\\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_D-US-Alt\"]}')}\"\nelse\n  _dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_D-US\"]}')\nend", "us_support": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_BT US 2\"]}') == \"-\"\n  \"`#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_BT US 1\"]}')}`\"\nelse\n  \"`#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_BT US 1\"]}')}` & `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_BT US 2\"]}')}`\"\nend"}, "schema": "[{\"control_type\":\"text\",\"label\":\"US Support\",\"name\":\"us_support\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"US Support\"},\"parent\":[\"variables\",\"data\"],\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true},{\"name\":\"us_shift_period\",\"type\":\"string\",\"optional\":true,\"label\":\"US Shift Period\",\"details\":{\"real_name\":\"US Shift Period\"},\"control_type\":\"text\",\"parent\":[\"variables\",\"data\"]}]"}}, "keyword": "action", "name": "declare_variable", "number": 4, "provider": "workato_variable", "skip": false}, {"as": "4bce594e", "block": [], "input": {"blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": ":firefighter_workato: Good day,\nHere's the *BT Operations* On-Duty for Week #{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_WEEK NO\"]}')} (#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_DATE\"]}')}):\n\n*APJ* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT APJ\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-APJ\"]}')}\n\n*EMEA* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT EMEA\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-EMEA\"]}')}\n\n*US* - #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"fce3e11c\",\"path\":[\"us_support\"]}')} :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"fce3e11c\",\"path\":[\"us_shift_period\"]}')}\n\n*Escalation* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT FLEXI\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-Flexi\"]}')}"}], "channel": "#biztech"}, "keyword": "action", "name": "post_bot_message", "number": 5, "provider": "slack_bot", "skip": false}, {"as": "2f65a9ec", "block": [], "input": {"blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": ":firefighter_workato: Good day,\nHere's the *BT Operations* On-Duty for Week #{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_WEEK NO\"]}')} (#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_DATE\"]}')}):\n\n*APJ* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT APJ\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-APJ\"]}')}\n\n*EMEA* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT EMEA\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-EMEA\"]}')}\n\n*US* - #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"fce3e11c\",\"path\":[\"us_support\"]}')} :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"fce3e11c\",\"path\":[\"us_shift_period\"]}')}\n\n*Escalation* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT FLEXI\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"9e3dbecf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-Flexi\"]}')}"}], "channel": "#bt-hr"}, "keyword": "action", "name": "post_bot_message", "number": 6, "provider": "slack_bot", "skip": false}], "input": {"days_of_week": "1", "time_unit": "weeks", "timezone": "<anon>Europe/London</anon>", "trigger_at": "08:00:00", "trigger_every": "1"}, "keyword": "trigger", "name": "scheduled_event", "number": 1, "provider": "clock", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (WEEK_DECLARE_AS, "workato_variable", "declare_variable"),
    (SEARCH_AS, "google_sheets", "search_spreadsheet_rows_v4_new"),
    (US_DECLARE_AS, "workato_variable", "declare_variable"),
    (POST_BIZTECH_AS, "slack_bot", "post_bot_message"),
    (POST_BTHR_AS, "slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "google_sheets.search_spreadsheet_rows_v4_new",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "google_sheets.search_spreadsheet_rows_v4_new",
    "slack.post_message",
]
REQUIRED_EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "week_no",
    "search_result_count",
    "matched_row",
    "us_support",
    "us_shift_period",
    "message_text",
)
_EXPECTATION_TARGET_KEYS = {"tool", "table_id", "lookup_table_id", "match_fields", "channel"}
_EXPECTATION_VALUE_KEYS = {
    "args_contains",
    "result_count",
    "response_contains",
    "result_contains",
    "created",
    "http_status_code",
    "text_fragments",
    "options_contains",
}
SPREADSHEET_LITERAL = "<anon>2AbC3DeF4GhI5JkL6MnO7PqR8StU9VwX0YzA1BcD2EfG</anon>"
_BARE_LEADING_ZERO_TIME_RE = re.compile(r"0\d:\d{2}")


def validate_118858472(raw: dict[str, Any]) -> dict[str, Any]:
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
    # Semantic pins on the drift-prone pieces.
    nodes = {str(node.get("as") or ""): node for node in _walk_nodes(raw)}
    week_formula = str(
        ((((nodes.get(WEEK_DECLARE_AS) or {}).get("input") or {}).get("variables") or {}).get("data") or {}).get("week_no")
        or ""
    )
    if week_formula != '=now.in_time_zone("<anon>Europe/London</anon>").yweek':
        raise RuntimeError(
            f"recipe {RECIPE_ID} week_no formula changed (the anon-wrapped tz de-tag "
            f"is load-bearing): {week_formula!r}"
        )
    search_input = (nodes.get(SEARCH_AS) or {}).get("input") or {}
    if (
        str(search_input.get("sheet") or "") != "2025"
        or str(search_input.get("count") or "") != "200"
        or sorted((search_input.get("data") or {}).keys()) != ["col_WEEK NO"]
        or WEEK_DECLARE_AS not in str((search_input.get("data") or {}).get("col_WEEK NO") or "")
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} search node changed: {search_input!r}")
    us_data = ((((nodes.get(US_DECLARE_AS) or {}).get("input") or {}).get("variables") or {}).get("data") or {})
    if sorted(us_data.keys()) != ["us_shift_period", "us_support"]:
        raise RuntimeError(f"recipe {RECIPE_ID} US declare variables changed")
    if '== "-"' not in str(us_data.get("us_support") or "") or ".present?" not in str(
        us_data.get("us_shift_period") or ""
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} US formulas lost their if/else arms")
    for step_as, channel in ((POST_BIZTECH_AS, "#biztech"), (POST_BTHR_AS, "#bt-hr")):
        node_input = (nodes.get(step_as) or {}).get("input") or {}
        if str(node_input.get("channel") or "") != channel:
            raise RuntimeError(f"recipe {RECIPE_ID} post {step_as} channel changed")
        blocks = node_input.get("blocks") or []
        if len(blocks) != 1 or blocks[0].get("block_type") != "section_with_text":
            raise RuntimeError(f"recipe {RECIPE_ID} post {step_as} blocks changed")
    biztech_text = str(((nodes.get(POST_BIZTECH_AS) or {}).get("input") or {}).get("blocks")[0].get("section_text"))
    bthr_text = str(((nodes.get(POST_BTHR_AS) or {}).get("input") or {}).get("blocks")[0].get("section_text"))
    if biztech_text != bthr_text:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the two digest texts diverged -- the byte-identical "
            f"twin-post analysis no longer holds"
        )
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
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


def seed_118858472(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118858472(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (payload-less "
            f"scheduler tick; no trigger field is ever dereferenced): {trigger!r}"
        )
    now = data.get("now")
    week_no = _derive_week(now)
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: a forced action error would fail the "
            f"whole run instead of exercising a recipe branch"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["sheets"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the sheets section; "
            f"got {sorted(seed_in.keys()) if isinstance(seed_in, dict) else seed_in!r}"
        )
    matched_row = _require_sheets_section(seed_in["sheets"], week_no)
    derived = _derive_ground_truth(week_no, matched_row)
    _require_expect_shape(data.get("expect"), derived)
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
        "now": now,
        "trigger": trigger,
        "expect": deepcopy(data["expect"]),
        "sheets": deepcopy(seed_in["sheets"]),
        "sheets_seed_response": deepcopy(seed_response),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_118858472(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118858472(raw)
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    if seed.get("now") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing the fixed 'now'")
    if not isinstance(seed.get("sheets"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing the sheets section")
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    initial_snapshot = ctx.tools.call("harness.google_sheets.snapshot", {})
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = ctx.tools.call("harness.google_sheets.snapshot", {})
    # No cleanup: the sheet seed fully overwrites the redirected tab on every
    # seed (replace_rows) and the Slack posts are terminal observables that
    # are never re-read (cleanup principle).
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "expect": seed.get("expect"),
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
    result["verifier"] = verify_118858472(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _derive_week(now: Any) -> int:
    if not isinstance(now, str) or not now.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input requires a fixed 'now' (the week_no "
            f"formula is a wall-clock yweek)"
        )
    try:
        dt = _dt.datetime.fromisoformat(now.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(f"recipe {RECIPE_ID} 'now' must be an ISO timestamp: {now!r}") from exc
    if dt.tzinfo is None:
        raise RuntimeError(f"recipe {RECIPE_ID} 'now' must carry timezone information: {now!r}")
    return dt.astimezone(zoneinfo.ZoneInfo(ZONE)).isocalendar()[1]


def _require_sheets_section(section: Any, week_no: int) -> dict[str, Any] | None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["headers", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets must be exactly {{'headers': ..., 'rows': ...}}"
        )
    if section["headers"] != SHEET_HEADERS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets.headers must be the LITERAL col_-prefixed "
            f"17-column schedule schema (datapills walk these exact keys)"
        )
    rows = section["rows"]
    if not isinstance(rows, list) or len(rows) < 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets.rows needs at least 2 rows (a "
            f"different-week decoy is part of every variant's selectivity proof)"
        )
    matching: list[dict[str, Any]] = []
    decoys = 0
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} sheet row {idx} must be an object")
        unknown = sorted(set(row) - set(SHEET_HEADERS))
        if unknown:
            raise RuntimeError(f"recipe {RECIPE_ID} sheet row {idx} has unknown columns: {unknown}")
        for key in SHEET_HEADERS:
            if key not in row or not isinstance(row[key], str):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} sheet row {idx} must carry every column as a "
                    f"string (missing/non-string {key!r})"
                )
            if _BARE_LEADING_ZERO_TIME_RE.fullmatch(row[key]):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} sheet row {idx}.{key} = {row[key]!r}: bare "
                    f"time cells must be seeded in the sheet's RENDERED form "
                    f"({row[key].lstrip('0')!r}) -- live Sheets USER_ENTERED drops "
                    f"the leading zero on read-back (live-lane verified 08:00 -> "
                    f"'8:00'), so seed-the-rendered-form keeps the round-trip an "
                    f"identity (118554940/118858162 precedent; range strings like "
                    f"'09:00 - 18:00' are NOT coerced and stay verbatim)"
                )
        if row["col_WEEK NO"] == str(week_no):
            matching.append(row)
        else:
            decoys += 1
    if len(matching) > 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} at most ONE seeded row may match WEEK NO {week_no} "
            f"(sheet-row pills read OUTSIDE any foreach with first-row semantics); "
            f"got {len(matching)}"
        )
    if decoys < 1:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant needs a different-week decoy row")
    if not matching:
        return None
    row = matching[0]
    for column in DIGEST_COLUMNS:
        if not row[column].strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} the matched row must carry a non-empty {column!r} "
                f"(a blank digest cell would masquerade as the zero-row branch; "
                f"col_D-US-Alt is the only formula-optional column)"
            )
    return dict(row)


def _derive_ground_truth(week_no: int, matched_row: dict[str, Any] | None) -> dict[str, Any]:
    if matched_row is None:
        us_support = "`` & ``"
        us_shift_period: str | None = None
    else:
        if matched_row["col_BT US 2"] == "-":
            us_support = "`%s`" % matched_row["col_BT US 1"]
        else:
            us_support = "`%s` & `%s`" % (matched_row["col_BT US 1"], matched_row["col_BT US 2"])
        if matched_row["col_D-US-Alt"].strip():
            us_shift_period = "%s\n%s" % (matched_row["col_D-US"], matched_row["col_D-US-Alt"])
        else:
            us_shift_period = matched_row["col_D-US"]
    return {
        "week_no": week_no,
        "matched_row": deepcopy(matched_row),
        "search_result_count": 0 if matched_row is None else 1,
        "us_support": us_support,
        "us_shift_period": us_shift_period,
        "message_text": _digest_text(matched_row, us_support, us_shift_period),
    }


def _digest_text(row: dict[str, Any] | None, us_support: str, us_shift_period: str | None) -> str:
    def cell(name: str) -> str:
        value = (row or {}).get(name)
        return "" if value is None else str(value)

    shift = "" if us_shift_period is None else str(us_shift_period)
    return (
        ":firefighter_workato: Good day,\n"
        "Here's the *BT Operations* On-Duty for Week %s (%s):\n\n"
        "*APJ* - `%s` :firefighter_6:\n%s\n\n"
        "*EMEA* - `%s` :firefighter_6:\n%s\n\n"
        "*US* - %s :firefighter_6:\n%s\n\n"
        "*Escalation* - `%s` :firefighter_6:\n%s"
    ) % (
        cell("col_WEEK NO"),
        cell("col_DATE"),
        cell("col_BT APJ"),
        cell("col_D-APJ"),
        cell("col_BT EMEA"),
        cell("col_D-EMEA"),
        us_support,
        shift,
        cell("col_BT FLEXI"),
        cell("col_D-Flexi"),
    )


def _require_expect_shape(expect: Any, derived: dict[str, Any]) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    checks = (
        expect.get("executed_action_count") == 5,
        expect.get("tools")
        == [
            "google_sheets.search_spreadsheet_rows_v4_new",
            "slack.post_message",
            "slack.post_message",
        ],
        expect.get("week_no") == derived["week_no"],
        expect.get("search_result_count") == derived["search_result_count"],
        expect.get("matched_row") == derived["matched_row"],
        expect.get("us_support") == derived["us_support"],
        expect.get("us_shift_period") == derived["us_shift_period"],
        expect.get("message_text") == derived["message_text"],
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with the derived ground "
            f"truth (week {derived['week_no']}, "
            f"{derived['search_result_count']} matching row(s)): {expect!r}"
        )
    _require_tool_expectations(expect, derived)


def _require_tool_expectations(expect: dict[str, Any], derived: dict[str, Any]) -> None:
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or len(items) != 3:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin all 3 external "
            f"calls (search + the two posts)"
        )
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[{idx}] must be an object")
        unknown = sorted(set(item) - _EXPECTATION_TARGET_KEYS - _EXPECTATION_VALUE_KEYS)
        if unknown:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] has non-corpus keys: {unknown}"
            )
        if not any(key in item for key in _EXPECTATION_VALUE_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] pins no ground-truth value"
            )
    search_item, first_post, second_post = items
    search_checks = (
        search_item.get("tool") == "google_sheets.search_spreadsheet_rows_v4_new",
        search_item.get("args_contains")
        == {
            "spreadsheet": SPREADSHEET_LITERAL,
            "sheet": "2025",
            "data": {"col_WEEK NO": derived["week_no"]},
            "count": "200",
        },
        search_item.get("result_count") == derived["search_result_count"],
    )
    if not all(search_checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0] must pin the verbatim search "
            f"args (int week pill) and the live match count: {search_item!r}"
        )
    for idx, item in ((1, first_post), (2, second_post)):
        post_checks = (
            item.get("tool") == "slack.post_message",
            item.get("channel") == "override",
            item.get("text_fragments") == [derived["message_text"]],
        )
        if not all(post_checks):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] must pin the FULL digest "
                f"text as its single fragment and the override channel: {item!r}"
            )


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
