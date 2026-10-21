from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_127065639


RECIPE_ID = "127065639"
SEED_TYPE = "webhook_snowflake_cost_alerts_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "workato_webhooks"
TRIGGER_NAME = "new_event"
TRIGGER_AS = "85f4ecae"
WEBHOOK_SUFFIX = "Send_snowflake_cost_alerts"
DECLARE_STEP_AS = "697dfecf"
SELECT_STEP_AS = "da26d8b6"
MESSAGE_TIME_STEP_AS = "7e0a5c33"
HEADER_STEP_AS = "2c10f8fa"
FOREACH_AS = "ad870abd"
ALERT_TYPE_STEP_AS = "ab3cc5fa"
ITEM_LINE_STEP_AS = "dd42f163"
POST_STEP_AS = "7cd9d8f8"
INSERT_STEP_AS = "45d5ddb7"
ALERT_TABLE = "WORKATO_BUSINESS_SYSTEMS.SNOWFLAKE.SNOWFLAKE_COST_ALERTS"
MONITORING_TABLE = "WORKATO_BUSINESS_SYSTEMS.SNOWFLAKE.SNOWFLAKE_COST_ALERT_MONITORING"
RAW_CHANNEL = "C099RC7FRT4"

# workato_webhooks.new_event (as 85f4ecae, suffix 'Send_snowflake_cost_alerts',
# webhook_type rawdatatxt). The payload is NEVER dereferenced -- the trigger
# is a fixed seeded string. Body:
#   2  workato_variable.declare_variable 697dfecf: Alert_Table /
#      Monitoring_Table = the two 3-part Snowflake names (pinned below);
#      Slack_Message / Message_Time / Alert_Type start nil
#   3  snowflake.run_custom_sql da26d8b6 (LIVE): SELECT * FROM #{Alert_Table}
#   IF 4 (rows size greater_than 0):
#     5  update_variables 7e0a5c33: Message_Time = rows[0]['message_timestamp']
#     6  update_variables 2c10f8fa: Slack_Message = ':snowflake_db: Usage
#        threshold exceeded for the following services at *' + Message_Time +
#        '*:\n'  (double-quoted Ruby escapes decode to REAL newlines --
#        join-branch fix 7aad3c0c)
#     FOREACH 7 (ad870abd) over the rows, repeat_mode simple:
#       8  update_variables ab3cc5fa: Alert_Type = item['type'] (read back
#          within the SAME iteration -- sequential variable semantics)
#       9  update_variables dd42f163: Slack_Message += '\n> ' + Alert_Type +
#          ' - ' + item['category'] + ' | ' + item['spent_by'] +
#          ' | Total spent $' + item['total_spent'] + ' | Limit $' +
#          item['limit'] + '\n'
#     10 slack_bot.post_bot_message 7cd9d8f8 (LIVE slack; channel C099RC7FRT4
#        is redirected to the benchmark override channel): one
#        section_with_text block whose text is the accumulated Slack_Message
#     11 snowflake.run_custom_sql 45d5ddb7 (LIVE): INSERT INTO
#        #{Monitoring_Table} SELECT CATEGORY,SPENT_BY,TOTAL_SPENT,LIMIT,
#        DATE(MESSAGE_TIMESTAMP),CURRENT_TIMESTAMP() FROM #{Alert_Table}
#        WHERE TYPE='DAILY' -- CURRENT_TIMESTAMP() is deterministically
#        rewritten by the live client to seed.snowflake_live.current_time,
#        and DATE() casts the VARCHAR message timestamp; the WHERE filter is
#        data-driven (a mixed DAILY/WEEKLY seed covers both outcomes in one
#        run)
#
# Rows are read back with dual-case keys (snowflake_live row.setdefault
# lowercase), so the lowercase item derefs resolve against the UPPERCASE
# live columns. All alert columns are seeded VARCHAR so the rendered Slack
# bytes ('$123.45', the message timestamp) are pinned verbatim. The
# monitoring table's column ORDER is part of the contract (positional
# INSERT..SELECT): category, spent_by, total_spent, limit, alert_date DATE,
# inserted_at TIMESTAMP_NTZ.
#
# ROW-ORDER NOTE: SELECT * carries no ORDER BY; the seeded ground truth pins
# insertion order (single-batch insert into a fresh single-partition table --
# stable in Snowflake practice; the live lane confirms).

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "workato_webhooks", "name": "new_event", "as": "85f4ecae", "skip": false, "input": {"request": {"headers_schema": "[{\"control_type\":\"text\",\"label\":\"Accept encoding\",\"type\":\"string\",\"name\":\"accept_encoding\"},{\"control_type\":\"text\",\"label\":\"Authorization\",\"type\":\"string\",\"name\":\"authorization\"},{\"control_type\":\"text\",\"label\":\"Content length\",\"type\":\"string\",\"name\":\"content_length\"},{\"control_type\":\"text\",\"label\":\"Content type\",\"type\":\"string\",\"name\":\"content_type\"},{\"control_type\":\"text\",\"label\":\"User agent\",\"type\":\"string\",\"name\":\"user_agent\"},{\"control_type\":\"text\",\"label\":\"X amzn trace ID\",\"type\":\"string\",\"name\":\"x_amzn_trace_id\"},{\"control_type\":\"text\",\"label\":\"X correlation ID\",\"type\":\"string\",\"name\":\"x_correlation_id\"},{\"control_type\":\"text\",\"label\":\"X forwarded for\",\"type\":\"string\",\"name\":\"x_forwarded_for\"},{\"control_type\":\"text\",\"label\":\"X forwarded port\",\"type\":\"string\",\"name\":\"x_forwarded_port\"},{\"control_type\":\"text\",\"label\":\"X forwarded proto\",\"type\":\"string\",\"name\":\"x_forwarded_proto\"},{\"control_type\":\"text\",\"label\":\"X request ID\",\"type\":\"string\",\"name\":\"x_request_id\"}]", "query_params": "[]", "webhook_type": "rawdatatxt"}, "webhook_suffix": "Send_snowflake_cost_alerts"}, "block": [{"number": 2, "keyword": "action", "provider": "workato_variable", "name": "declare_variable", "as": "697dfecf", "skip": false, "input": {"variables": {"data": {"Alert_Table": "WORKATO_BUSINESS_SYSTEMS.SNOWFLAKE.SNOWFLAKE_COST_ALERTS", "Monitoring_Table": "WORKATO_BUSINESS_SYSTEMS.SNOWFLAKE.SNOWFLAKE_COST_ALERT_MONITORING"}, "schema": "[{\"control_type\":\"text\",\"label\":\"Slack_Message\",\"name\":\"Slack_Message\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"Slack_Message\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"text\",\"label\":\"Alert_Table\",\"name\":\"Alert_Table\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"Alert_Table\"},\"parent\":[\"variables\",\"data\"],\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true},{\"control_type\":\"text\",\"label\":\"Monitoring_Table\",\"name\":\"Monitoring_Table\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"Monitoring_Table\"},\"parent\":[\"variables\",\"data\"],\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true},{\"control_type\":\"text\",\"label\":\"Message_Time\",\"name\":\"Message_Time\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"Message_Time\"},\"parent\":[\"variables\",\"data\"],\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true},{\"name\":\"Alert_Type\",\"type\":\"string\",\"optional\":true,\"label\":\"Alert_Type\",\"details\":{\"real_name\":\"Alert_Type\"},\"control_type\":\"text\",\"parent\":[\"variables\",\"data\"]}]"}}, "block": []}, {"number": 3, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql", "as": "da26d8b6", "skip": false, "input": {"sql": "SELECT * FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"697dfecf\",\"path\":[\"Alert_Table\"]}')}", "update_only": "false"}, "block": []}, {"number": 4, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"da26d8b6\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}", "operand": "greater_than", "rhs": "0"}], "operand": "and", "type": "compound"}, "block": [{"number": 5, "keyword": "action", "provider": "workato_variable", "name": "update_variables", "as": "7e0a5c33", "skip": false, "input": {"Message_Time": "=_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"da26d8b6\",\"path\":[\"rows\"]}')[0]['message_timestamp']", "input_mode": "raw", "name": "3fffe537-8d72-465f-b322-cdd71f4c5c5d:697dfecf:Message_Time"}, "block": []}, {"number": 6, "keyword": "action", "provider": "workato_variable", "name": "update_variables", "as": "2c10f8fa", "skip": false, "input": {"Slack_Message": "=\":snowflake_db: Usage threshold exceeded for the following services at *\"+_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"697dfecf\",\"path\":[\"Message_Time\"]}')+\"*:\\n\"", "input_mode": "structured", "name": "3fffe537-8d72-465f-b322-cdd71f4c5c5d:697dfecf:Slack_Message"}, "block": []}, {"number": 7, "keyword": "foreach", "provider": "", "name": "", "as": "ad870abd", "skip": false, "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"da26d8b6\",\"path\":[\"rows\"]}')}"}, "repeat_mode": "simple", "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"da26d8b6\",\"path\":[\"rows\"]}')}", "block": [{"number": 8, "keyword": "action", "provider": "workato_variable", "name": "update_variables", "as": "ab3cc5fa", "skip": false, "input": {"Alert_Type": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"ad870abd\",\"path\":[]}')['type']", "input_mode": "raw", "name": "3fffe537-8d72-465f-b322-cdd71f4c5c5d:697dfecf:Alert_Type"}, "block": []}, {"number": 9, "keyword": "action", "provider": "workato_variable", "name": "update_variables", "as": "dd42f163", "skip": false, "input": {"Slack_Message": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"697dfecf\",\"path\":[\"Slack_Message\"]}')+\"\\n> \"+_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"697dfecf\",\"path\":[\"Alert_Type\"]}')+\" - \"+_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"ad870abd\",\"path\":[]}')['category']+\" | \"+_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"ad870abd\",\"path\":[]}')['spent_by']+\" | Total spent $\"+_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"ad870abd\",\"path\":[]}')['total_spent']+\" | Limit $\"+_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"ad870abd\",\"path\":[]}')['limit']+\"\\n\"", "input_mode": "structured", "name": "3fffe537-8d72-465f-b322-cdd71f4c5c5d:697dfecf:Slack_Message"}, "block": []}]}, {"number": 10, "keyword": "action", "provider": "slack_bot", "name": "post_bot_message", "as": "7cd9d8f8", "skip": false, "input": {"blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"697dfecf\",\"path\":[\"Slack_Message\"]}')}"}], "channel": "C099RC7FRT4"}, "block": []}, {"number": 11, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql", "as": "45d5ddb7", "skip": false, "input": {"sql": "INSERT INTO #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"697dfecf\",\"path\":[\"Monitoring_Table\"]}')}\nSELECT CATEGORY,SPENT_BY,TOTAL_SPENT,LIMIT,DATE(MESSAGE_TIMESTAMP),CURRENT_TIMESTAMP() \nFROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"697dfecf\",\"path\":[\"Alert_Table\"]}')}\nWHERE TYPE='DAILY'", "update_only": "false"}, "block": []}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (DECLARE_STEP_AS, "workato_variable", "declare_variable"),
    (SELECT_STEP_AS, "snowflake", "run_custom_sql"),
    (MESSAGE_TIME_STEP_AS, "workato_variable", "update_variables"),
    (HEADER_STEP_AS, "workato_variable", "update_variables"),
    (ALERT_TYPE_STEP_AS, "workato_variable", "update_variables"),
    (ITEM_LINE_STEP_AS, "workato_variable", "update_variables"),
    (POST_STEP_AS, "slack_bot", "post_bot_message"),
    (INSERT_STEP_AS, "snowflake", "run_custom_sql"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "snowflake.run_custom_sql",
    "workato_runtime.update_variables",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "slack.post_message",
]
ALERT_COLUMNS = ("type", "category", "spent_by", "total_spent", "limit", "message_timestamp")
MONITORING_COLUMNS = {
    "category": "string",
    "spent_by": "string",
    "total_spent": "string",
    "limit": "string",
    "alert_date": "date",
    "inserted_at": "timestamp_ntz",
}
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "sql_calls",
    "slack_message",
    "final_monitoring_rows",
)
_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}.*")


def validate_127065639(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    if str((raw.get("input") or {}).get("webhook_suffix") or "") != WEBHOOK_SUFFIX:
        raise RuntimeError(f"recipe {RECIPE_ID} webhook suffix changed")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    # Semantic pins on the drift-prone inputs (tree pin holds exact bytes).
    for node in _walk_nodes(raw):
        step = str(node.get("as") or "")
        node_input = node.get("input") or {}
        if step == DECLARE_STEP_AS:
            declared = (node_input.get("variables") or {}).get("data") or {}
            if declared.get("Alert_Table") != ALERT_TABLE or declared.get("Monitoring_Table") != MONITORING_TABLE:
                raise RuntimeError(f"recipe {RECIPE_ID} declared table names changed: {declared}")
        if step == INSERT_STEP_AS:
            sql = str(node_input.get("sql") or "")
            if "CURRENT_TIMESTAMP()" not in sql or "WHERE TYPE='DAILY'" not in sql:
                raise RuntimeError(f"recipe {RECIPE_ID} monitoring INSERT changed: {sql!r}")
        if step == POST_STEP_AS and str(node_input.get("channel") or "") != RAW_CHANNEL:
            raise RuntimeError(f"recipe {RECIPE_ID} slack channel changed")
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "webhook_suffix": WEBHOOK_SUFFIX,
        "alert_table": ALERT_TABLE,
        "monitoring_table": MONITORING_TABLE,
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


def seed_127065639(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_127065639(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if sorted(trigger.keys()) != ["payload"] or not isinstance(trigger.get("payload"), str) or not trigger["payload"].strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'payload': <non-empty str>}} "
            "(rawdatatxt webhook body; never dereferenced)"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the snowflake_live section"
        )
    _require_snowflake_section(seed_in["snowflake_live"])
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole "
            "run instead of exercising a recipe branch"
        )
    provision = ctx.tools.call(
        "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_127065639(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_127065639(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    if not str(seed["snowflake_live"].get("current_time") or ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} snowflake_live.current_time missing (the monitoring "
            "INSERT uses CURRENT_TIMESTAMP())"
        )
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect"),
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
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
        # Required cleanup: both tables are benchmark-owned live objects.
        # The Slack post is an ordinary observable (never re-read) -- no
        # cleanup, per the cleanup principle.
        cleanup_response = ctx.tools.call("harness.snowflake_live.cleanup", {})
        details["cleanup_response"] = {"snowflake_live": cleanup_response}
    if not (cleanup_response or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake cleanup failed: {cleanup_response}")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_127065639(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_snowflake_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["current_time", "tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly "
            "{'current_time': ..., 'tables': ...}"
        )
    if not _TIMESTAMP_RE.fullmatch(str(section["current_time"] or "")):
        raise RuntimeError(
            f"recipe {RECIPE_ID} snowflake_live.current_time must be a fixed timestamp "
            "(pins CURRENT_TIMESTAMP() in the monitoring INSERT)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted([ALERT_TABLE, MONITORING_TABLE]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the two qualified tables "
            f"{ALERT_TABLE!r} and {MONITORING_TABLE!r}"
        )
    alert = tables[ALERT_TABLE]
    if not isinstance(alert, dict) or list(alert.keys()) != ["columns", "rows"]:
        raise RuntimeError(f"recipe {RECIPE_ID} alert table spec must be {{'columns', 'rows'}}")
    if list(alert["columns"].keys()) != list(ALERT_COLUMNS) or any(
        kind != "string" for kind in alert["columns"].values()
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} alert columns must be exactly {list(ALERT_COLUMNS)} all "
            "VARCHAR ('string') so the rendered Slack bytes are pinned verbatim"
        )
    if not isinstance(alert["rows"], list):
        raise RuntimeError(f"recipe {RECIPE_ID} alert rows must be a list (may be empty)")
    for idx, row in enumerate(alert["rows"]):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(ALERT_COLUMNS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} alert row {idx} must carry exactly {list(ALERT_COLUMNS)}"
            )
        for key, value in row.items():
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} alert row {idx}.{key} must be a non-empty string"
                )
        if not _TIMESTAMP_RE.fullmatch(row["message_timestamp"]):
            raise RuntimeError(
                f"recipe {RECIPE_ID} alert row {idx}.message_timestamp must be a timestamp "
                "string (DATE() casts it in the monitoring INSERT)"
            )
    monitoring = tables[MONITORING_TABLE]
    if (
        not isinstance(monitoring, dict)
        or list(monitoring.keys()) != ["columns", "rows"]
        or monitoring["rows"] != []
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} monitoring table must seed empty rows (variant "
            "independence: every run starts from a clean log)"
        )
    if list(monitoring["columns"].keys()) != list(MONITORING_COLUMNS.keys()) or dict(
        monitoring["columns"]
    ) != MONITORING_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} monitoring columns must be exactly {MONITORING_COLUMNS} "
            "in that ORDER (the INSERT..SELECT is positional)"
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
    return ctx.tools.call("harness.snowflake.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
