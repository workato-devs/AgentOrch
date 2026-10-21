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
from ..verifier import verify_104739509


RECIPE_ID = "104739509"
SEED_TYPE = "hour_confirmation_reminder_variant"
TRACK = "live_slack_hour_confirmation_reminders"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "4b44d429"
TABLE_ID = "14273"
STATUS_FIELD = "062ca716_d11a_43e9_8125_308d95d2d231"
MONTH_FIELD = "4cf93d5d_e636_4fe4_bbc4_4983bf76dcf0"
CONVERSATION_FIELD = "7fdc0acb_9070_4a7f_ba90_2f9138631573"
MESSAGE_TS_FIELD = "1d540a5c_b3bf_47e2_b82f_7d031a47427f"
_TS_RE = re.compile(r"^\d+\.\d+$")

# clock.scheduled_event (as 4b44d429, cron '0 15 2-5 * 1-5' Asia/Singapore --
# the variant MUST pin trigger.scheduled_time; no wall-clock reads):
#   2  declare_variable b4b30b57 month_slack_formatted =
#      (scheduled_time - 1.months).strftime("%b %Y")
#   3  declare_list acd13e57 'Messages IDs' (conversation_id, message_id,
#      permalink)
#   4  declare_variable 05837b82 next_page_token (nil)
#   REPEAT 5 (do-while):
#     6  workato_db_table.get_records table 14273, filters
#        [status eq 'Pending Confirmation', month eq month_slack_formatted],
#        continuation_token = interpolated next_page_token variable (renders
#        "" on the first page -- the arg is ALWAYS present for this recipe)
#     IF 7 (records size > 0):
#       8  insert_to_list_batch e104fa6b (conversation_id, message_id,
#          permalink = "https://workato.slack.com/archives/#{channel}/p" +
#          ts.gsub(".",""))
#     IF 9 (step 6 continuation_token present):
#       10 update_variables 6c33c31e next_page_token = step token
#     ELSE 11:
#       12 update_variables d3dd55f4 next_page_token = '=clear' (-> "")
#     WHILE 13: VARIABLE 05837b82.next_page_token present (the '=clear'
#       else-branch is what terminates the loop, not the step token)
#   FOREACH 14 (as 1740fce5) over the accumulated list:
#     15 slack_bot.post_bot_message 0af1c396 channel = item.conversation_id;
#        blocks render two section_text lines:
#          '*Reminder to Confirm Hours Worked in <month>*'
#          ':blob_wave: Do remember to confirm your hours <<permalink>|here>!'
#
# Backends: workato_db_table 14273 is a READ-ONLY Workato-internal mock
# (seeded per variant). Slack runs LIVE: the row conversation ids are C...
# channel ids, so raw_executor routes every post to SLACK_CHANNEL_OVERRIDE
# (non-U channels override); the rendered permalink text still carries the
# ROW's original channel id. Ordinary posts are the observable artifact -- no
# cleanup required per the cleanup principle (nothing later reads them).
#
# DETERMINISTIC MOCK PAGINATION (pinned groundtruth, diverges from real
# Workato ON PURPOSE): the mock re-serves the FULL filtered table on every
# page (workato_db_table.py get_records), so the two-page variant accumulates
# duplicate reminder rows and posts duplicates. Expects pin that exact
# duplicate accumulation; do not "fix" seeds to hide it.

_RAW_PIN_JSON = r"""{"as": "4b44d429", "block": [{"as": "b4b30b57", "block": [], "input": {"variables": {"data": {"month_slack_formatted": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"clock\",\"line\":\"4b44d429\",\"path\":[\"scheduled_time\"]}') - 1.months).strftime(\"%b %Y\")"}, "schema": "[{\"control_type\":\"text\",\"label\":\"Month (Slack Formatted)\",\"name\":\"month_slack_formatted\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"Month (Slack Formatted)\"}}]"}}, "keyword": "action", "name": "declare_variable", "number": 2, "provider": "workato_variable", "skip": false}, {"as": "acd13e57", "block": [], "input": {"list_item_schema_json": "[{\"name\":\"conversation_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Conversation ID\"},{\"name\":\"message_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Message ID\"},{\"name\":\"permalink\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Permalink\"}]", "name": "Messages IDs"}, "keyword": "action", "name": "declare_list", "number": 3, "provider": "workato_variable", "skip": false}, {"as": "05837b82", "block": [], "input": {"variables": {"schema": "[{\"name\":\"next_page_token\",\"type\":\"string\",\"optional\":true,\"label\":\"Next page token\",\"details\":{\"real_name\":\"Next page token\"},\"control_type\":\"text\"}]"}}, "keyword": "action", "name": "declare_variable", "number": 4, "provider": "workato_variable", "skip": false}, {"as": "0f28f2ce", "block": [{"as": "6cec4fd0", "block": [], "input": {"062ca716-d11a-43e9-8125-308d95d2d231": "string", "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "142931bd-9fde-47f4-9408-ff7b814bdbd6": "string", "1d540a5c-b3bf-47e2-b82f-7d031a47427f": "string", "4cf93d5d-e636-4fe4-bbc4-4983bf76dcf0": "string", "4ef894b0-e764-4597-85d2-391b3262b5a8": "string", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "770b992c-087e-44fe-807b-e99ceedd25b0": "string", "7dd08541-f7bd-40f6-b2cd-f023cb5aaca1": "string", "7fdc0acb-9070-4a7f-ba90-2f9138631573": "string", "93a68411-d668-4c65-883e-cf4459f983c1": "integer", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "b25620db-a04b-422b-a636-4c38737833a4": "string", "bfaf4995-50c7-4488-a063-d0483b382acf": "boolean", "continuation_token": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"05837b82\",\"path\":[\"next_page_token\"]}')}", "ea2bd65a-b30b-44f4-94f9-c1418cb563b3": "string", "filters": [{"field_id": "062ca716-d11a-43e9-8125-308d95d2d231", "op_default": "eq", "value_default": "Pending Confirmation"}, {"field_id": "4cf93d5d-e636-4fe4-bbc4-4983bf76dcf0", "op_default": "eq", "value_default": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"b4b30b57\",\"path\":[\"month_slack_formatted\"]}')}"}], "limit": "200", "order_direction": "asc", "table_id": "14273"}, "keyword": "action", "name": "get_records", "number": 6, "provider": "workato_db_table", "skip": false}, {"as": "", "block": [{"as": "e104fa6b", "block": [], "input": {"list_items": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"6cec4fd0\",\"path\":[\"records\"]}')}", "conversation_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"6cec4fd0\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"7fdc0acb_9070_4a7f_ba90_2f9138631573\"]}')}", "message_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"6cec4fd0\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"1d540a5c_b3bf_47e2_b82f_7d031a47427f\"]}')}", "permalink": "=\"https://workato.slack.com/archives/#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"6cec4fd0\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"7fdc0acb_9070_4a7f_ba90_2f9138631573\"]}')}/p\" + _dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"6cec4fd0\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"1d540a5c_b3bf_47e2_b82f_7d031a47427f\"]}').gsub(\".\",\"\")"}, "location": "end", "name": "6c44a0e8-ae2e-4ced-bd19-7cfc5fa3c3dd:acd13e57"}, "keyword": "action", "name": "insert_to_list_batch", "number": 8, "provider": "workato_variable", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"6cec4fd0\",\"path\":[\"records\", {\"path_element_type\": \"size\"}]}')}", "operand": "greater_than", "rhs": "0"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 7, "provider": "", "skip": false}, {"as": "", "block": [{"as": "6c33c31e", "block": [], "input": {"name": "b507c454-3566-417b-b8e1-967a9c593659:05837b82:next_page_token", "next_page_token": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"6cec4fd0\",\"path\":[\"continuation_token\"]}')}"}, "keyword": "action", "name": "update_variables", "number": 10, "provider": "workato_variable", "skip": false}, {"as": "", "block": [{"as": "d3dd55f4", "block": [], "input": {"name": "b507c454-3566-417b-b8e1-967a9c593659:05837b82:next_page_token", "next_page_token": "=clear"}, "keyword": "action", "name": "update_variables", "number": 12, "provider": "workato_variable", "skip": false}], "input": {}, "keyword": "else", "name": "", "number": 11, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"6cec4fd0\",\"path\":[\"continuation_token\"]}')}", "operand": "present", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 9, "provider": "", "skip": false}, {"as": "", "block": [], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"05837b82\",\"path\":[\"next_page_token\"]}')}", "operand": "present", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "while_condition", "name": "", "number": 13, "provider": "", "skip": false}], "input": {}, "keyword": "repeat", "name": "", "number": 5, "provider": "", "skip": false}, {"as": "1740fce5", "block": [{"as": "0af1c396", "block": [], "input": {"blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": "*Reminder to Confirm Hours Worked in #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"b4b30b57\",\"path\":[\"month_slack_formatted\"]}')}*"}, {"block_type": "section_with_text", "button_type": "continue_flow", "section_text": ":blob_wave: Do remember to confirm your hours <#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"1740fce5\",\"path\":[\"permalink\"]}')}|here>!"}], "channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"1740fce5\",\"path\":[\"conversation_id\"]}')}"}, "keyword": "action", "name": "post_bot_message", "number": 15, "provider": "slack_bot", "skip": false}], "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"acd13e57\",\"path\":[\"list_items\"]}')}"}, "keyword": "foreach", "name": "", "number": 14, "provider": "", "repeat_mode": "simple", "skip": false, "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"acd13e57\",\"path\":[\"list_items\"]}')}"}], "input": {"cron_expression": "0 15 2-5 * 1-5", "time_unit": "custom_schedule", "timezone": "Asia/Singapore"}, "keyword": "trigger", "name": "scheduled_event", "number": 1, "provider": "clock", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("b4b30b57", "workato_variable", "declare_variable"),
    ("acd13e57", "workato_variable", "declare_list"),
    ("05837b82", "workato_variable", "declare_variable"),
    ("6cec4fd0", "workato_db_table", "get_records"),
    ("e104fa6b", "workato_variable", "insert_to_list_batch"),
    ("6c33c31e", "workato_variable", "update_variables"),
    ("d3dd55f4", "workato_variable", "update_variables"),
    ("0af1c396", "slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "workato_runtime.declare_list",
    "workato_db_table.get_records",
    "workato_runtime.insert_to_list_batch",
    "workato_runtime.update_variables",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "slack.post_message",
]
REQUIRED_ROW_FIELDS = (STATUS_FIELD, MONTH_FIELD, CONVERSATION_FIELD, MESSAGE_TS_FIELD)


def validate_104739509(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    trigger_input_obj = raw.get("input") or {}
    if (
        str(trigger_input_obj.get("cron_expression") or "") != "0 15 2-5 * 1-5"
        or str(trigger_input_obj.get("timezone") or "") != "Asia/Singapore"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger schedule changed: {trigger_input_obj}")
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
        "table_id": TABLE_ID,
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


def seed_104739509(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_104739509(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["workato_db_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the workato_db_table section; "
            f"got {sorted(seed_in.keys())}"
        )
    _require_db_section(seed_in["workato_db_table"])
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_104739509(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_104739509(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
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
            "expect": seed.get("expect"),
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_104739509(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != ["scheduled_time"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly scheduled_time; "
            f"got {sorted(trigger.keys())}"
        )
    value = trigger.get("scheduled_time")
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input.scheduled_time must be a string")
    try:
        parsed = datetime.datetime.fromisoformat(value)
    except ValueError as exc:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.scheduled_time is not ISO-8601: {value!r}"
        ) from exc
    if parsed.tzinfo is None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.scheduled_time must carry an explicit UTC offset "
            "(the recipe schedule is timezone-pinned to Asia/Singapore)"
        )


def _require_db_section(section: Any) -> None:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed.workato_db_table must be an object")
    unknown = sorted(set(section.keys()) - {"tables", "continuation_tokens"})
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.workato_db_table has unknown keys: {unknown}")
    tables = section.get("tables")
    if not isinstance(tables, dict) or sorted(tables.keys()) != [TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table.tables must declare exactly table {TABLE_ID!r}"
        )
    rows = tables[TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {TABLE_ID} seed must be a non-empty row list "
            "(zero-match variants seed rows the filters exclude)"
        )
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table row {idx} must be an object")
        for field in REQUIRED_ROW_FIELDS:
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table row {idx} requires non-empty string {field!r} "
                    "(status/month feed the filters, conversation/ts feed the reminder list)"
                )
        conversation = row[CONVERSATION_FIELD]
        if not conversation.startswith("C"):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} conversation id must be a C... channel id "
                f"(deterministic SLACK_CHANNEL_OVERRIDE routing); got {conversation!r}"
            )
        if not _TS_RE.fullmatch(row[MESSAGE_TS_FIELD]):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} message ts must look like a Slack ts "
                f"(digits.digits, the permalink gsub strips the dot); got {row[MESSAGE_TS_FIELD]!r}"
            )
    tokens = section.get("continuation_tokens")
    if tokens is not None:
        if not isinstance(tokens, dict) or sorted(tokens.keys()) != [TABLE_ID]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed continuation_tokens must declare exactly table {TABLE_ID!r}"
            )
        if not isinstance(tokens[TABLE_ID], str) or not tokens[TABLE_ID].strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed continuation_tokens[{TABLE_ID!r}] must be a non-empty "
                "string (a plain first-page token; the mock never re-issues it)"
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
    return ctx.tools.call("harness.workato_db_table.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
