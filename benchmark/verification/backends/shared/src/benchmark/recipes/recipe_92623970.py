from __future__ import annotations

import datetime
import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_92623970


RECIPE_ID = "92623970"
SEED_TYPE = "locker_booking_expiry_reminder_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "3c691145"
BOOKING_TABLE_ID = "1889452"
LOCKERS_TABLE_ID = "1889451"
SEARCH_STEP_AS = "5459eaeb"
FOREACH_AS = "a23a2ba4"
SIDE_SEARCH_STEP_AS = "567b312a"
LOGGER_STEP_AS = "0ff012d7"
POST_STEP_AS = "6b0fa2e4"
UPDATE_STEP_AS = "05d87fc1"


_RAW_PIN_JSON = r"""{"as": "3c691145", "block": [{"as": "5459eaeb", "block": [], "input": {"lookup_table_id": "1889452", "parameters": {"col5": "=now.to_date.strftime(\"%B %Y\")", "col6": "Approved"}}, "keyword": "action", "name": "search_entries", "number": 2, "provider": "lookup_table", "skip": false}, {"as": "a23a2ba4", "block": [{"as": "", "block": [{"as": "567b312a", "block": [], "input": {"lookup_table_id": "1889451", "parameters": {"col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a23a2ba4\",\"path\":[\"entry\", \"col3\"]}')}"}}, "keyword": "action", "name": "search_entries", "number": 5, "provider": "lookup_table", "skip": false}, {"as": "0ff012d7", "block": [], "input": {"message": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"clock\",\"line\":\"3c691145\",\"path\":[\"scheduled_time\"]}') + 1.months).strftime(\"%B %Y\")"}, "keyword": "action", "name": "log_message", "number": 6, "provider": "logger", "skip": false}, {"as": "6b0fa2e4", "block": [], "input": {"blocks": [{"block_type": "section_with_text", "section_text": "*#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a23a2ba4\",\"path\":[\"entry\", \"col3\"]}')}* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a23a2ba4\",\"path\":[\"entry\", \"col5\"]}')}` Locker Booking"}, {"block_type": "divider"}, {"block_type": "section_with_text", "bot_command": "2331920", "button_title": "Extend Booking", "params": "user_id:#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a23a2ba4\",\"path\":[\"entry\", \"col1\"]}')}, office:#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a23a2ba4\",\"path\":[\"entry\", \"col3\"]}')}", "section_text": "Hi <@#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a23a2ba4\",\"path\":[\"entry\", \"col1\"]}')}>, your locker `#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a23a2ba4\",\"path\":[\"entry\", \"col4\"]}')}` booking for `#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a23a2ba4\",\"path\":[\"entry\", \"col5\"]}')}` is going to expire soon. Please confirm if you would like to extend your booking to *#{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"0ff012d7\",\"path\":[\"message\"]}')}*. ", "style": "primary"}, {"block_type": "repeat_block_group", "objects": {"blocks": [{"actions": [{"bot_command": "18452836", "button_title": "Extend Booking", "params": "entry_id: #{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a23a2ba4\",\"path\":[\"id\"]}')}", "style": "primary", "type": "button"}], "block_type": "actions"}]}}], "channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a23a2ba4\",\"path\":[\"entry\", \"col1\"]}')}"}, "keyword": "action", "name": "post_bot_message", "number": 7, "provider": "slack_bot", "skip": false}, {"as": "05d87fc1", "block": [], "input": {"id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a23a2ba4\",\"path\":[\"id\"]}')}", "ignore_not_found": "false", "lookup_table_id": "1889452", "parameters": {"col7": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"6b0fa2e4\",\"path\":[\"ts\"]}')}", "col8": "Not Renewed"}}, "keyword": "action", "name": "update_entry", "number": 8, "provider": "lookup_table", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a23a2ba4\",\"path\":[\"entry\", \"col8\"]}')}", "operand": "blank", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 4, "provider": "", "skip": false}], "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"5459eaeb\",\"path\":[\"entries\"]}')}"}, "keyword": "foreach", "name": "", "number": 3, "provider": "", "repeat_mode": "simple", "skip": false, "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"5459eaeb\",\"path\":[\"entries\"]}')}"}], "input": {"days_of_month": "25,27,28,29,30,31,26,last_day", "time_unit": "months", "timezone": "Asia/Singapore", "trigger_at": "10:00:00", "trigger_every": "1"}, "keyword": "trigger", "name": "scheduled_event", "number": 1, "provider": "clock", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (SEARCH_STEP_AS, "lookup_table", "search_entries"),
    (SIDE_SEARCH_STEP_AS, "lookup_table", "search_entries"),
    (LOGGER_STEP_AS, "logger", "log_message"),
    (POST_STEP_AS, "slack_bot", "post_bot_message"),
    (UPDATE_STEP_AS, "lookup_table", "update_entry"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "workato_runtime.log_message",
    "slack.post_message",
    "lookup_table.update_entry",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "slack.post_message",
    "lookup_table.update_entry",
]
BOOKING_COLS = tuple(f"col{i}" for i in range(1, 11))
LOCKERS_COLS = tuple(f"col{i}" for i in range(1, 9))
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "month_label",
    "next_month_label",
    "notified_entry_ids",
    "logger_message",
    "slack_texts",
    "final_booking_rows",
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
_SLACK_USER_RE = re.compile(r"^U[A-Z0-9]{8,}$")
_TS_SENTINEL_RE = re.compile(r"^__SLACK_TS_(\d+)__$")
_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def validate_92623970(raw: dict[str, Any]) -> dict[str, Any]:
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
    # Semantic pins on the drift-prone inputs (the tree pin holds exact bytes).
    for node in _walk_nodes(raw):
        step = str(node.get("as") or "")
        node_input = node.get("input") or {}
        if step == SEARCH_STEP_AS:
            parameters = node_input.get("parameters") or {}
            if (
                str(node_input.get("lookup_table_id")) != BOOKING_TABLE_ID
                or parameters.get("col5") != '=now.to_date.strftime("%B %Y")'
                or parameters.get("col6") != "Approved"
            ):
                raise RuntimeError(f"recipe {RECIPE_ID} booking search changed: {node_input}")
        if step == SIDE_SEARCH_STEP_AS and str(node_input.get("lookup_table_id")) != LOCKERS_TABLE_ID:
            raise RuntimeError(f"recipe {RECIPE_ID} side search table changed")
        if step == LOGGER_STEP_AS and "+ 1.months" not in str(node_input.get("message") or ""):
            raise RuntimeError(f"recipe {RECIPE_ID} logger formula changed")
        if step == UPDATE_STEP_AS:
            parameters = node_input.get("parameters") or {}
            if (
                str(node_input.get("lookup_table_id")) != BOOKING_TABLE_ID
                or parameters.get("col8") != "Not Renewed"
                or "ts" not in str(parameters.get("col7") or "")
            ):
                raise RuntimeError(f"recipe {RECIPE_ID} update_entry mapping changed: {node_input}")
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "booking_table_id": BOOKING_TABLE_ID,
        "lockers_table_id": LOCKERS_TABLE_ID,
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


def seed_92623970(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_92623970(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if sorted(trigger.keys()) != ["scheduled_time"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly scheduled_time "
            f"(the +1.months logger formula dereferences it): {sorted(trigger.keys())}"
        )
    scheduled_time = _parse_offset_datetime(trigger["scheduled_time"], "trigger.scheduled_time")
    now = data.get("now")
    if not isinstance(now, str) or not now.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must pin now "
            "(=now.to_date.strftime feeds the booking search)"
        )
    now_dt = _parse_offset_datetime(now, "now")
    if (now_dt.year, now_dt.month) != (scheduled_time.year, scheduled_time.month):
        raise RuntimeError(
            f"recipe {RECIPE_ID} now and scheduled_time must fall in the same calendar "
            f"month (the reminder mixes the now-month search with the scheduled_time+1 "
            f"message): {now!r} vs {trigger['scheduled_time']!r}"
        )
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole "
            "run instead of exercising a recipe branch"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["lookup_table", "slack_channel_map"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the lookup_table and "
            "slack_channel_map sections"
        )
    _require_lookup_section(seed_in["lookup_table"], seed_in["slack_channel_map"])
    month_label = _month_label(now_dt)
    next_month_label = _month_label(_shift_month(scheduled_time))
    _require_expect_shape(data.get("expect"), seed_in["lookup_table"], month_label, next_month_label)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "now": now,
        "lookup_table": deepcopy(seed_in["lookup_table"]),
        "slack_channel_map": deepcopy(seed_in["slack_channel_map"]),
        "expect": deepcopy(data["expect"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_92623970(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_92623970(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
    if not isinstance(seed.get("slack_channel_map"), dict) or not seed["slack_channel_map"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed file missing slack_channel_map (live isolation: "
            "entry.col1 user-id channels must route to the override channel)"
        )
    if not str(seed.get("now") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing pinned now")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect"),
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    details["initial_snapshot"] = _snapshot(ctx)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    details["raw_execution"] = raw_execution
    details["ground_truth"] = _ground_truth(raw_execution)
    details["final_snapshot"] = _snapshot(ctx)
    # Cleanup note: the lookup tables are per-variant mock state; the Slack
    # post is read back into col7 (benchmark-verified state) and stays in the
    # override channel, per the cleanup policy for verified posts.
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_92623970(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _parse_offset_datetime(value: Any, label: str) -> datetime.datetime:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} {label} must be an ISO datetime string")
    parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise RuntimeError(f"recipe {RECIPE_ID} {label} must carry an explicit offset: {value!r}")
    return parsed


def _month_label(dt: datetime.datetime) -> str:
    return f"{_MONTHS[dt.month - 1]} {dt.year}"


def _shift_month(dt: datetime.datetime) -> datetime.datetime:
    year, month = (dt.year + 1, 1) if dt.month == 12 else (dt.year, dt.month + 1)
    return dt.replace(year=year, month=month, day=1)


def _require_lookup_section(section: Any, channel_map: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.lookup_table must be exactly {{'tables'}}")
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted([BOOKING_TABLE_ID, LOCKERS_TABLE_ID]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly tables "
            f"{BOOKING_TABLE_ID!r} (bookings) and {LOCKERS_TABLE_ID!r} (lockers database)"
        )
    if not isinstance(channel_map, dict) or not channel_map:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.slack_channel_map must be a non-empty object")
    for user, target in channel_map.items():
        if not _SLACK_USER_RE.fullmatch(str(user)) or target != "__override__":
            raise RuntimeError(
                f"recipe {RECIPE_ID} slack_channel_map entries must map U... ids to "
                f"'__override__' (live isolation): {user!r} -> {target!r}"
            )
    bookings = tables[BOOKING_TABLE_ID]
    if not isinstance(bookings, list) or not bookings:
        raise RuntimeError(f"recipe {RECIPE_ID} booking table rows must be a non-empty list")
    for idx, row in enumerate(bookings):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(BOOKING_COLS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} booking row {idx} must carry exactly col1..col10"
            )
        for key, value in row.items():
            if not isinstance(value, str):
                raise RuntimeError(f"recipe {RECIPE_ID} booking row {idx}.{key} must be a string")
        if not _SLACK_USER_RE.fullmatch(row["col1"]) or row["col1"] not in channel_map:
            raise RuntimeError(
                f"recipe {RECIPE_ID} booking row {idx}.col1 must be a U... id present in "
                f"slack_channel_map (no variant may ever DM a real user): {row['col1']!r}"
            )
    lockers = tables[LOCKERS_TABLE_ID]
    if not isinstance(lockers, list) or not lockers:
        raise RuntimeError(
            f"recipe {RECIPE_ID} lockers table rows must be a non-empty list (the dead "
            "side search still executes and the table must exist)"
        )
    for idx, row in enumerate(lockers):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(LOCKERS_COLS):
            raise RuntimeError(f"recipe {RECIPE_ID} lockers row {idx} must carry exactly col1..col8")
        for key, value in row.items():
            if not isinstance(value, str):
                raise RuntimeError(f"recipe {RECIPE_ID} lockers row {idx}.{key} must be a string")


def _require_expect_shape(
    expect: Any,
    lookup_section: dict[str, Any],
    month_label: str,
    next_month_label: str,
) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if expect.get("month_label") != month_label:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.month_label must equal the now render "
            f"{month_label!r}: {expect.get('month_label')!r}"
        )
    if expect.get("next_month_label") != next_month_label:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.next_month_label must equal the scheduled_time+1 "
            f"render {next_month_label!r}: {expect.get('next_month_label')!r}"
        )
    notified = expect.get("notified_entry_ids")
    slack_texts = expect.get("slack_texts")
    if not isinstance(notified, list) or not isinstance(slack_texts, list) or len(notified) != len(slack_texts):
        raise RuntimeError(
            f"recipe {RECIPE_ID} notified_entry_ids and slack_texts must be same-length lists"
        )
    if expect.get("executed_action_count") != 1 + 4 * len(notified):
        raise RuntimeError(
            f"recipe {RECIPE_ID} executed_action_count must be 1 + 4*notified "
            f"(search + [side search, logger, post, update] per blank-col8 match)"
        )
    expected_tools = ["lookup_table.search_entries"] + [
        tool
        for _ in notified
        for tool in ("lookup_table.search_entries", "slack.post_message", "lookup_table.update_entry")
    ]
    if expect.get("tools") != expected_tools:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools inconsistent with notified count: "
            f"{expect.get('tools')!r}"
        )
    if notified:
        if expect.get("logger_message") != next_month_label:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.logger_message must be the next-month render "
                f"{next_month_label!r}"
            )
        for idx, text in enumerate(slack_texts):
            if not isinstance(text, str) or f"*{next_month_label}*. " not in text:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} slack_texts[{idx}] must carry the bolded "
                    f"next-month label with its trailing '. ' verbatim"
                )
    elif expect.get("logger_message") is not None:
        raise RuntimeError(f"recipe {RECIPE_ID} logger_message must be null when nothing is notified")
    booking_rows = lookup_section["tables"][BOOKING_TABLE_ID]
    for entry_id in notified:
        if not isinstance(entry_id, int) or not 0 <= entry_id < len(booking_rows):
            raise RuntimeError(
                f"recipe {RECIPE_ID} notified_entry_ids must be seed row indexes "
                f"(mock _row_id): {notified!r}"
            )
    final_rows = expect.get("final_booking_rows")
    if not isinstance(final_rows, list) or len(final_rows) != len(booking_rows):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_booking_rows must pin the WHOLE booking table "
            f"({len(booking_rows)} rows)"
        )
    sentinel_count = 0
    for idx, row in enumerate(final_rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(BOOKING_COLS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} final_booking_rows[{idx}] must carry exactly col1..col10"
            )
        match = _TS_SENTINEL_RE.fullmatch(str(row.get("col7") or ""))
        if idx in notified:
            if not match or int(match.group(1)) != notified.index(idx):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} final_booking_rows[{idx}].col7 must be the "
                    f"'__SLACK_TS_<n>__' sentinel (live ts is cross-checked against the "
                    f"run's own post trace, never pinned)"
                )
            sentinel_count += 1
            if row.get("col8") != "Not Renewed":
                raise RuntimeError(
                    f"recipe {RECIPE_ID} final_booking_rows[{idx}].col8 must be 'Not Renewed'"
                )
        elif match:
            raise RuntimeError(
                f"recipe {RECIPE_ID} final_booking_rows[{idx}] carries a ts sentinel but "
                f"is not a notified entry"
            )
    if sentinel_count != len(notified):
        raise RuntimeError(f"recipe {RECIPE_ID} every notified entry needs exactly one ts sentinel")
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or not items:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must be a non-empty list")
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[{idx}] must be an object")
        unknown = sorted(set(item.keys()) - _EXPECT_ITEM_KEYS)
        if unknown:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] has unrecognized keys: {unknown}"
            )
        if item.get("tool") not in ALLOWED_TOOLS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}].tool must be one of "
                f"{ALLOWED_TOOLS}; got {item.get('tool')!r}"
            )
        if not any(key in item for key in _EXPECT_VALUE_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] must carry at least one value "
                "key (corpus lint)"
            )
        if item.get("tool") == "lookup_table.update_entry":
            parameters = (item.get("args_contains") or {}).get("parameters")
            if isinstance(parameters, dict) and "col7" in parameters:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} tool_expectations[{idx}] must not pin col7 "
                    "(the live Slack ts is nondeterministic; the verifier cross-checks it "
                    "against the run's own post trace)"
                )
    if items[0].get("tool") != "lookup_table.search_entries":
        raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[0] must pin the booking search")
    first_params = (items[0].get("args_contains") or {}).get("parameters") or {}
    if first_params.get("col5") != month_label or first_params.get("col6") != "Approved":
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0] must pin col5={month_label!r} "
            f"col6='Approved': {first_params!r}"
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


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return dict(ctx.tools.call("harness.lookup_table.snapshot", {}))


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
