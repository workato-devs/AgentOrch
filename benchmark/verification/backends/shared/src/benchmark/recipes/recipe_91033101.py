from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_91033101


RECIPE_ID = "91033101"
SEED_TYPE = "standup_meeting_service_variant"
TRACK = "live_slack_standup_service"
TRIGGER_PROVIDER = "workato_service"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "16525f59"
SERVICE_NAME = "Standup Meeting"
LOOKUP_TABLE_ID = "3357221"
THREAD_FIRST_POST_AS = "3a224cd0"
CATCH_AS = "38bfd4f3"
REQUIRED_REQUEST_FIELDS = ("user", "channel_name", "channel_id", "is_threaded", "lookup_table_entry_id")

# Callable service 'Standup Meeting' (trigger as 16525f59; request user /
# channel_name / channel_id / is_threaded / lookup_table_entry_id -- the last
# is schema-required but never dereferenced). Side-effect-only service (no
# send_reply):
#   TRY 2
#     IF 3 (is_threaded == 'no')
#       4 slack_bot.post_bot_message a4707917: channel = request.user (a
#         'U...' literal posts AS-IS, so variants MUST map it via seed
#         slack_channel_map {'<user>': '__override__'}), text 'Time for our
#         standup meeting for #{channel_name}' (attachment buttons are
#         metadata, not part of the live text)
#     IF 5 (is_threaded == 'yes')
#       6 lookup_table.search_entries 9dadcd46 (table 3357221, col2 =
#         request.channel_id)
#       IF 7 (entries current_item entry.col7 blank -- first entry)
#         8 slack_bot.post_bot_message 3a224cd0: channel = request.channel_id
#           (non-'U' -> redirected to SLACK_CHANNEL_OVERRIDE), block
#           section_text '<!here> Time for our standup meeting for
#           #{channel_name}. Responses will be collected in the thread.'
#         9 lookup_table.update_entry 8f926f05: id = first entry id, col7 =
#           3a224cd0.ts.to_i (the LIVE posted ts floored -- nondeterministic;
#           the verifier derives it from the trace, never a pinned literal)
#       IF 10 (col7 present AND now.to_i - col7.to_i > 86400 -- reads the
#            SEARCH result, so the IF-7 write never re-triggers it)
#         11 slack_bot.post_bot_message 21795fc5 (same block)
#         12 lookup_table.update_entry df1d2971 (col7 = 21795fc5.ts.to_i)
#   CATCH 13 (as 38bfd4f3, retry 3/10s; engine single-execution)
#     14 slack_bot.post_bot_message 9dc0a2ff: channel = request.user, 'Time
#        for our daily standup meeting for #{channel_name}' -- only reachable
#        via seed.force_action_error on step 3a224cd0 (mock/live steps do not
#        fail naturally with a seeded matching row)
# Backends: lookup table 3357221 is Workato-internal mock state (per-variant
# isolated); Slack posts run LIVE (post_bot_message -> slack.post_message).
# Every live post is read from the trace for verification (the threaded
# variants derive col7 from the posted ts), so run_91033101 deletes each
# benchmark post in finally and fails on a failed delete.
EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("a4707917", "slack_bot", "post_bot_message"),
    ("9dadcd46", "lookup_table", "search_entries"),
    ("3a224cd0", "slack_bot", "post_bot_message"),
    ("8f926f05", "lookup_table", "update_entry"),
    ("21795fc5", "slack_bot", "post_bot_message"),
    ("df1d2971", "lookup_table", "update_entry"),
    ("9dc0a2ff", "slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "slack.post_message",
    "lookup_table.search_entries",
    "lookup_table.update_entry",
]
ALLOWED_TOOLS: list[str] = [
    "slack.post_message",
    "lookup_table.search_entries",
    "lookup_table.update_entry",
]
EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "lookup_final_tables",
    "catch_used",
    "col7_write",
)

# Verbatim raw-recipe pin: the full normalized node tree (number, keyword,
# provider, name, as, skip, input; the catch node pins max_retry_count 3 /
# retry_interval 10). Any drift in the is_threaded gates, the blank/stale
# col7 conditions, the ts.to_i write-backs or the posted texts fails
# validation instead of silently changing groundtruth.
_RAW_PIN_JSON = r"""{"as": "16525f59", "block": [{"as": "", "block": [{"as": "", "block": [{"as": "a4707917", "block": [], "input": {"attachment_buttons": [{"bot_command": "standup collect response", "params": "channel_id: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"16525f59\",\"path\":[\"request\", \"channel_id\"]}')} q1: na q2: na q3: na channel_name: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"16525f59\",\"path\":[\"request\", \"channel_name\"]}')}", "title": "Get started"}], "channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"16525f59\",\"path\":[\"request\", \"user\"]}')}", "text": "Time for our standup meeting for #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"16525f59\",\"path\":[\"request\", \"channel_name\"]}')}"}, "keyword": "action", "name": "post_bot_message", "number": 4, "provider": "slack_bot", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"16525f59\",\"path\":[\"request\", \"is_threaded\"]}')}", "operand": "equals_to", "rhs": "no"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 3, "provider": "", "skip": false}, {"as": "", "block": [{"as": "9dadcd46", "block": [], "input": {"lookup_table_id": "3357221", "parameters": {"col2": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"16525f59\",\"path\":[\"request\", \"channel_id\"]}')}"}}, "keyword": "action", "name": "search_entries", "number": 6, "provider": "lookup_table", "skip": false}, {"as": "", "block": [{"as": "3a224cd0", "block": [], "input": {"blocks": [{"block_type": "section_with_button_with_long_action", "bot_command": "46340660", "button_title": "Standup Now", "button_type": "bot_command", "params": "channel_id: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"16525f59\",\"path\":[\"request\", \"channel_id\"]}')} q1: na q2: na q3: na channel_name: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"16525f59\",\"path\":[\"request\", \"channel_name\"]}')}", "section_text": "<!here> Time for our standup meeting for #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"16525f59\",\"path\":[\"request\", \"channel_name\"]}')}. Responses will be collected in the thread.", "style": "default"}], "channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"16525f59\",\"path\":[\"request\", \"channel_id\"]}')}"}, "keyword": "action", "name": "post_bot_message", "number": 8, "provider": "slack_bot", "skip": false}, {"as": "8f926f05", "block": [], "input": {"id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"9dadcd46\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}", "ignore_not_found": "false", "lookup_table_id": "3357221", "parameters": {"col7": "=_('data.slack_bot.3a224cd0.ts').to_i"}}, "keyword": "action", "name": "update_entry", "number": 9, "provider": "lookup_table", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"9dadcd46\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col7\"]}')}", "operand": "blank", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 7, "provider": "", "skip": false}, {"as": "", "block": [{"as": "21795fc5", "block": [], "input": {"blocks": [{"block_type": "section_with_button_with_long_action", "bot_command": "46340660", "button_title": "Standup Now", "button_type": "bot_command", "params": "channel_id: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"16525f59\",\"path\":[\"request\", \"channel_id\"]}')} q1: na q2: na q3: na channel_name: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"16525f59\",\"path\":[\"request\", \"channel_name\"]}')}", "section_text": "<!here> Time for our standup meeting for #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"16525f59\",\"path\":[\"request\", \"channel_name\"]}')}. Responses will be collected in the thread.", "style": "default"}], "channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"16525f59\",\"path\":[\"request\", \"channel_id\"]}')}"}, "keyword": "action", "name": "post_bot_message", "number": 11, "provider": "slack_bot", "skip": false}, {"as": "df1d2971", "block": [], "input": {"id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"9dadcd46\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}", "ignore_not_found": "false", "lookup_table_id": "3357221", "parameters": {"col7": "=_('data.slack_bot.21795fc5.ts').to_i"}}, "keyword": "action", "name": "update_entry", "number": 12, "provider": "lookup_table", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"9dadcd46\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col7\"]}')}", "operand": "present", "rhs": ""}, {"lhs": "=now.to_i - _('data.lookup_table.9dadcd46.entries.first.entry.col7').to_i", "operand": "greater_than", "rhs": "86400"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 10, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"16525f59\",\"path\":[\"request\", \"is_threaded\"]}')}", "operand": "equals_to", "rhs": "yes"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 5, "provider": "", "skip": false}, {"as": "38bfd4f3", "block": [{"as": "9dc0a2ff", "block": [], "input": {"attachment_buttons": [{"bot_command": "standup collect feedback", "params": "channel_id: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"16525f59\",\"path\":[\"request\", \"channel_id\"]}')} q1: na q2: na q3: na channel_name: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"16525f59\",\"path\":[\"request\", \"channel_name\"]}')}", "title": "Get started"}], "channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"16525f59\",\"path\":[\"request\", \"user\"]}')}", "text": "Time for our daily standup meeting for #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"16525f59\",\"path\":[\"request\", \"channel_name\"]}')}"}, "keyword": "action", "name": "post_bot_message", "number": 14, "provider": "slack_bot", "skip": false}], "input": {"max_retry_count": "3", "retry_interval": "10"}, "keyword": "catch", "name": "", "number": 13, "provider": "", "skip": false}], "input": {}, "keyword": "try", "name": "", "number": 2, "provider": "", "skip": false}], "input": {"request_schema_json": "[{\"control_type\":\"text\",\"label\":\"User\",\"name\":\"user\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Channel name\",\"name\":\"channel_name\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Channel ID\",\"name\":\"channel_id\",\"type\":\"string\",\"optional\":false},{\"name\":\"is_threaded\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Is threaded\"},{\"name\":\"lookup_table_entry_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Lookup table entry ID\"}]", "service_name": "Standup Meeting"}, "keyword": "trigger", "name": "receive_request", "number": 1, "provider": "workato_service", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)


def validate_91033101(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    if str((raw.get("input") or {}).get("service_name") or "") != SERVICE_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger service name changed")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "service_name": SERVICE_NAME,
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


def seed_91033101(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_91033101(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    request = _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"lookup_table", "slack_channel_map"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    lookup_seed = seed_in.get("lookup_table")
    matched_col7 = _require_lookup_section(lookup_seed, request)
    force = data.get("force_action_error")
    if force is not None:
        if not isinstance(force, dict) or str(force.get("step_as") or "") != THREAD_FIRST_POST_AS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} force_action_error is only meaningful on the threaded first "
                f"post step_as {THREAD_FIRST_POST_AS!r} (nothing else fails naturally); got {force}"
            )
        if not str(force.get("error") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} force_action_error.error must be a non-empty string")
        if request["is_threaded"] != "yes" or matched_col7 != "":
            raise RuntimeError(
                f"recipe {RECIPE_ID} the catch branch needs is_threaded 'yes' AND a blank-col7 "
                "matching row so the failing step 3a224cd0 is actually reached"
            )
    channel_map = seed_in.get("slack_channel_map")
    needs_user_dm = request["is_threaded"] == "no" or force is not None
    if needs_user_dm:
        if channel_map != {request["user"]: "__override__"}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} this variant posts to channel = request.user (a 'U...' "
                "literal posts AS-IS live); seed.slack_channel_map must be exactly "
                f"{{{request['user']!r}: '__override__'}}"
            )
    elif channel_map is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} slack_channel_map is only meaningful for variants that post to "
            "request.user (is_threaded 'no' or the forced catch)"
        )
    stale_check_reachable = request["is_threaded"] == "yes" and matched_col7 != ""
    if stale_check_reachable and data.get("now") in (None, ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} threaded variants with a non-blank col7 evaluate "
            "'now.to_i - col7.to_i' (IF 10) and must pin data.now"
        )
    expect = data.get("expect")
    _require_expect_shape(expect, force)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "lookup_table": deepcopy(lookup_seed),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if channel_map is not None:
        out["slack_channel_map"] = deepcopy(channel_map)
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    return attach_variant(out, ctx)


def run_91033101(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_91033101(raw)
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing resolved expect block")
    cleanup_responses: list[dict[str, Any]] = []
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect"),
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    raw_execution: dict[str, Any] = {}
    try:
        details["initial_snapshot"] = ctx.tools.call("harness.lookup_table.snapshot", {})
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = ctx.tools.call("harness.lookup_table.snapshot", {})
    finally:
        # Cleanup principle: the threaded variants read the posted ts back out
        # of the trace for verification, so every benchmark post is deleted
        # after the snapshots. Fail-fast below on any failed delete.
        cleanup_responses = _cleanup_slack_posts(raw_execution, ctx)
        details["cleanup_responses"] = cleanup_responses
    failed_deletes = [response for response in cleanup_responses if not response.get("ok")]
    if failed_deletes:
        raise RuntimeError(f"recipe {RECIPE_ID} Slack cleanup failed: {failed_deletes}")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_91033101(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> dict[str, str]:
    request = trigger.get("request")
    if not isinstance(request, dict) or sorted(trigger.keys()) != ["request"]:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input must be exactly {{'request': {{...}}}}")
    if sorted(request.keys()) != sorted(REQUIRED_REQUEST_FIELDS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger request must carry exactly "
            f"{sorted(REQUIRED_REQUEST_FIELDS)}; got {sorted(request.keys())}"
        )
    for field in REQUIRED_REQUEST_FIELDS:
        if not isinstance(request.get(field), str) or not request[field].strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger request field {field!r} must be a non-empty string"
            )
    if request["is_threaded"] not in {"yes", "no"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} request.is_threaded must be 'yes' or 'no' (the IF 3 / IF 5 gates)"
        )
    if not request["user"].startswith("U"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} request.user must be a 'U...' Slack user id (the DM branches "
            "post to it as a channel)"
        )
    if request["channel_id"].startswith("U"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} request.channel_id must be a non-user channel id so the live "
            "post redirects to SLACK_CHANNEL_OVERRIDE"
        )
    return {field: request[field] for field in REQUIRED_REQUEST_FIELDS}


def _require_lookup_section(lookup_seed: Any, request: dict[str, str]) -> str:
    tables = lookup_seed.get("tables") if isinstance(lookup_seed, dict) else None
    if not isinstance(tables, dict) or sorted(tables.keys()) != [LOOKUP_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly lookup_table.tables[{LOOKUP_TABLE_ID!r}]"
        )
    rows = tables[LOOKUP_TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"recipe {RECIPE_ID} table {LOOKUP_TABLE_ID} seed must be a non-empty row list")
    matches: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table {LOOKUP_TABLE_ID} rows must be objects")
        for field in ("id", "col2", "col7"):
            if field not in row:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {LOOKUP_TABLE_ID} row {idx} must carry explicit {field!r}"
                )
        col7 = row["col7"]
        if not isinstance(col7, str) or (col7 != "" and not col7.isdigit()):
            raise RuntimeError(
                f"recipe {RECIPE_ID} row {idx} col7 must be '' or an epoch-seconds digit string; "
                f"got {col7!r}"
            )
        if str(row["col2"]) == request["channel_id"]:
            matches.append(row)
    if request["is_threaded"] == "yes" and len(matches) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} threaded variants need exactly ONE row with col2 == "
            f"request.channel_id {request['channel_id']!r} (no matching row would walk the "
            "documented update-MISSING-id error edge); got {0}".format(len(matches))
        )
    return str(matches[0]["col7"]) if matches else ""


def _require_expect_shape(expect: Any, force: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    if not isinstance(expect.get("catch_used"), bool) or not isinstance(expect.get("col7_write"), bool):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.catch_used / expect.col7_write must be bools")
    if expect["catch_used"] is not (force is not None):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.catch_used must mirror the presence of force_action_error "
            "(the catch is only reachable via the forced failure)"
        )
    if expect["catch_used"] and not str(expect.get("forced_error_message") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch variants must pin expect.forced_error_message"
        )
    tables = expect.get("lookup_final_tables")
    if not isinstance(tables, dict) or sorted(tables.keys()) != [LOOKUP_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.lookup_final_tables must pin exactly table {LOOKUP_TABLE_ID}"
        )
    sentinel_used = "__POSTED_TS_EPOCH__" in json.dumps(tables)
    if bool(expect["col7_write"]) != sentinel_used:
        raise RuntimeError(
            f"recipe {RECIPE_ID} col7_write variants must (and only they may) use the "
            "'__POSTED_TS_EPOCH__' sentinel in lookup_final_tables -- the written col7 is the "
            "LIVE posted ts floored, derived from the trace at verify time"
        )


def _cleanup_slack_posts(raw_execution: dict[str, Any], ctx: RecipeContext) -> list[dict[str, Any]]:
    cleanup: list[dict[str, Any]] = []
    for row in raw_execution.get("trace") or []:
        if not isinstance(row, dict) or row.get("tool") != "slack.post_message":
            continue
        result = row.get("result") if isinstance(row.get("result"), dict) else {}
        channel = str(result.get("channel") or "")
        ts = str(result.get("ts") or "")
        if channel and ts:
            cleanup.append(ctx.tools.call("slack.delete_message", {"channel": channel, "ts": ts}))
    return cleanup


def _normalize_tree(node: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "number": node.get("number"),
        "keyword": node.get("keyword"),
        "provider": node.get("provider") or "",
        "name": node.get("name") or "",
        "as": node.get("as") or "",
        "skip": bool(node.get("skip")),
    }
    if node.get("keyword") == "foreach":
        out["repeat_mode"] = node.get("repeat_mode")
        out["source"] = node.get("source")
    if not out["skip"]:
        out["input"] = node.get("input")
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
