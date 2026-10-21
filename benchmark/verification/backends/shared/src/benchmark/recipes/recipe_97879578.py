from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_97879578


RECIPE_ID = "97879578"
SEED_TYPE = "training_enrollment_incomplete_publisher_variant"
TRACK = "workato_internal_pub_sub_incomplete_enrollments"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "bacef247"
TABLE_ID = "531"
TOPIC_ID = "35836"
GET_RECORDS_AS = "7ad806f7"
CATCH_AS = "862e5750"
STOP_AS = "c56feff1"
TIMEOUT_FRAGMENT = "Request ran for longer than 30000ms"
STATUS_FIELD = "bc4dccae_9c53_472e_a321_491a9982ddbb"
COURSE_FIELD = "0687d8fc_75c3_402e_bfb5_8343057213de"
EMAIL_FIELD = "724ce614_876b_4775_b110_ca6cc4a252ea"
RECORD_ID_FIELD = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"

# clock.scheduled_event (as bacef247, daily 12:00 America/New_York -- NO
# trigger field is ever dereferenced, so trigger_input is an explicit {}).
# The ENTIRE body sits inside TRY 2:
#   3  declare_list c7ed0f1e 'Tracker' (email, record_id, course_id,
#      number_of_reminders, last_reminder_sent -- the last two are NEVER
#      populated by any insert)
#   4  declare_variable 57ff4b8b page_token_incomplete (nil) + limit 200
#   REPEAT 5 (do-while):
#     6  workato_db_table.get_records 7ad806f7 table 531, filters
#        [status ne 'Completed', status ne 'Exempted'],
#        continuation_token = page_token_incomplete.presence or skip
#        (nil on the first page -> the arg is OMITTED from tool args entirely;
#        the mock ignores the recipe's limit input)
#     IF 7 (records size > 0):
#       8  insert_to_list_batch fcae2215 (course_id/email/record_id from the
#          row columns)
#     9  update_variables dc377fb4 page_token_incomplete =
#        step continuation_token.presence or clear
#     WHILE 10: STEP 7ad806f7.continuation_token present (rhs-less condition)
#   FOREACH 11 (as 2734e647) over Tracker:
#     12 workato_pub_sub.publish_to_topic 72e54ca1 topic 35836, message
#        {course_id, email, record_id from item; last_reminder_sent /
#        number_of_reminders read UNMAPPED tracker fields -> the engine
#        resolves the absent pills to None (JSON null) inside the message
#        object; type 'Incomplete'} -- nil parity pinned per variant.
#   CATCH 13 (as 862e5750, max_retry_count 0):
#     IF 14 (catch.message not_contains 'Request ran for longer than
#            30000ms'):
#       15 STOP (as c56feff1, stop_with_error=true, reason = catch.message).
#          The executor records ONLY {stopped: true} in the trace for stop
#          keywords (raw_executor.execute_node); stop_reason/stop_with_error
#          are never captured, so catch-path expects pin the stopped trace
#          marker + zero publishes, never an error result.
#     (message CONTAINS the 30000ms fragment -> IF false -> no stop; the
#      recipe simply ends after the catch block)
#
# Backends: workato_db_table 531 (read-only mock) + workato_pub_sub (mock,
# records topic_id + message) -- all Workato-internal, no cleanup. The catch
# branch is reachable ONLY via seed.force_action_error on step 7ad806f7 (mock
# table reads cannot fail organically); the forced error raises BEFORE the
# tool call is traced, so catch variants record zero get_records calls.
#
# DETERMINISTIC MOCK PAGINATION (pinned groundtruth, diverges from real
# Workato ON PURPOSE): the mock re-serves the full filtered table on every
# page, so the two-page variant duplicates tracker rows and publishes
# duplicates. Expects pin that exact duplicate accumulation.

_RAW_PIN_JSON = r"""{"as": "bacef247", "block": [{"as": "", "block": [{"as": "c7ed0f1e", "block": [], "input": {"list_item_schema_json": "[{\"name\":\"email\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Email\"},{\"name\":\"record_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Record ID\"},{\"name\":\"course_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Course ID\"},{\"name\":\"number_of_reminders\",\"type\":\"integer\",\"optional\":true,\"control_type\":\"integer\",\"label\":\"Number of reminders\",\"parse_output\":\"integer_conversion\"},{\"name\":\"last_reminder_sent\",\"type\":\"date_time\",\"optional\":true,\"control_type\":\"date\",\"label\":\"Last reminder sent\",\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\"}]", "name": "Tracker"}, "keyword": "action", "name": "declare_list", "number": 3, "provider": "workato_variable", "skip": false}, {"as": "57ff4b8b", "block": [], "input": {"variables": {"data": {"limit": "200"}, "schema": "[{\"control_type\":\"text\",\"label\":\"Page Token (Incomplete)\",\"name\":\"page_token_incomplete\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"integer\",\"label\":\"Limit\",\"parse_output\":\"integer_conversion\",\"name\":\"limit\",\"type\":\"integer\",\"optional\":true}]"}}, "keyword": "action", "name": "declare_variable", "number": 4, "provider": "workato_variable", "skip": false}, {"as": "6478cf3a", "block": [{"as": "7ad806f7", "block": [], "input": {"0687d8fc-75c3-402e-bfb5-8343057213de": "string", "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "13a7e919-7149-448c-873b-98a976f658e6": "string", "1d1b3bf7-70b3-4a04-ac81-41e8df1ddc95": "string", "23cee0e4-f136-40bb-8d4f-a8092297528c": "date", "4df4f772-13ea-4fe8-b962-756afcc564a6": "date", "50e36191-795d-4265-bd93-d9dc2a7842e4": "date", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "669c476a-7ccc-4512-9591-6830eecb375a": "string", "6ece122a-925c-422f-8b69-eb02ab0d2eea": "string", "7245032e-ccd9-46d5-96c0-df87ed58f9b0": "date", "724ce614-876b-4775-b110-ca6cc4a252ea": "string", "790d4b39-1df0-4529-92ce-9001b332023b": "string", "7dff7741-58f3-45c9-94a4-2ecfc1fd77cd": "string", "94971dcf-b0ae-4ccb-9b48-08be704974c6": "date", "9fb28649-581f-44ba-a7eb-fead22d6461d": "string", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "bc4dccae-9c53-472e-a321-491a9982ddbb": "string", "continuation_token": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"57ff4b8b\",\"path\":[\"page_token_incomplete\"]}').presence or skip", "dd6d47cc-2f17-417a-a7e3-d9527f80383f": "integer", "f5296d41-114a-4bd8-bff6-84de59ea7e65": "string", "filters": [{"field_id": "bc4dccae-9c53-472e-a321-491a9982ddbb", "op_default": "ne", "value_default": "Completed"}, {"field_id": "bc4dccae-9c53-472e-a321-491a9982ddbb", "op_default": "ne", "value_default": "Exempted"}], "limit": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"57ff4b8b\",\"path\":[\"limit\"]}')}", "order_direction": "asc", "table_id": "531"}, "keyword": "action", "name": "get_records", "number": 6, "provider": "workato_db_table", "skip": false}, {"as": "", "block": [{"as": "fcae2215", "block": [], "input": {"list_items": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"7ad806f7\",\"path\":[\"records\"]}')}", "course_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"7ad806f7\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"0687d8fc_75c3_402e_bfb5_8343057213de\"]}')}", "email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"7ad806f7\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"724ce614_876b_4775_b110_ca6cc4a252ea\"]}')}", "record_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"7ad806f7\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\"]}')}"}, "location": "end", "name": "71e178ea-79e9-4242-a5f5-033c1477cce0:c7ed0f1e"}, "keyword": "action", "name": "insert_to_list_batch", "number": 8, "provider": "workato_variable", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"7ad806f7\",\"path\":[\"records\", {\"path_element_type\": \"size\"}]}')}", "operand": "greater_than", "rhs": "0"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 7, "provider": "", "skip": false}, {"as": "dc377fb4", "block": [], "input": {"name": "83bb59cc-51c7-4b79-aa58-937caffce079:57ff4b8b:page_token_incomplete", "page_token_incomplete": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"7ad806f7\",\"path\":[\"continuation_token\"]}').presence or clear"}, "keyword": "action", "name": "update_variables", "number": 9, "provider": "workato_variable", "skip": false}, {"as": "", "block": [], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"7ad806f7\",\"path\":[\"continuation_token\"]}')}", "operand": "present"}], "operand": "and", "type": "compound"}, "keyword": "while_condition", "name": "", "number": 10, "provider": "", "skip": false}], "input": {}, "keyword": "repeat", "name": "", "number": 5, "provider": "", "skip": false}, {"as": "2734e647", "block": [{"as": "72e54ca1", "block": [], "input": {"message": {"course_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"2734e647\",\"path\":[\"course_id\"]}')}", "email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"2734e647\",\"path\":[\"email\"]}')}", "last_reminder_sent": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"2734e647\",\"path\":[\"last_reminder_sent\"]}')}", "number_of_reminders": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"2734e647\",\"path\":[\"number_of_reminders\"]}')}", "record_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"2734e647\",\"path\":[\"record_id\"]}')}", "type": "Incomplete"}, "topic_id": "35836"}, "keyword": "action", "name": "publish_to_topic", "number": 12, "provider": "workato_pub_sub", "skip": false}], "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c7ed0f1e\",\"path\":[\"list_items\"]}')}"}, "keyword": "foreach", "name": "", "number": 11, "provider": "", "repeat_mode": "simple", "skip": false, "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c7ed0f1e\",\"path\":[\"list_items\"]}')}"}, {"as": "862e5750", "block": [{"as": "", "block": [{"as": "c56feff1", "block": [], "input": {"stop_reason": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"862e5750\",\"path\":[\"message\"]}')}", "stop_with_error": "true"}, "keyword": "stop", "name": "", "number": 15, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"862e5750\",\"path\":[\"message\"]}')}", "operand": "not_contains", "rhs": "Request ran for longer than 30000ms"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 14, "provider": "", "skip": false}], "input": {"max_retry_count": "0", "retry_interval": "2"}, "keyword": "catch", "name": "", "number": 13, "provider": "", "skip": false}], "input": {}, "keyword": "try", "name": "", "number": 2, "provider": "", "skip": false}], "input": {"time_unit": "days", "timezone": "<anon>America/New_York</anon>", "trigger_at": "12:00:00", "trigger_every": "1"}, "keyword": "trigger", "name": "scheduled_event", "number": 1, "provider": "clock", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("c7ed0f1e", "workato_variable", "declare_list"),
    ("57ff4b8b", "workato_variable", "declare_variable"),
    ("7ad806f7", "workato_db_table", "get_records"),
    ("fcae2215", "workato_variable", "insert_to_list_batch"),
    ("dc377fb4", "workato_variable", "update_variables"),
    ("72e54ca1", "workato_pub_sub", "publish_to_topic"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_list",
    "workato_runtime.declare_variable",
    "workato_db_table.get_records",
    "workato_runtime.insert_to_list_batch",
    "workato_runtime.update_variables",
    "workato_pub_sub.publish_to_topic",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_pub_sub.publish_to_topic",
]
REQUIRED_ROW_FIELDS = (STATUS_FIELD, COURSE_FIELD, EMAIL_FIELD, RECORD_ID_FIELD)


def validate_97879578(raw: dict[str, Any]) -> dict[str, Any]:
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
    stop_nodes = [node for node in _walk_nodes(raw) if node.get("keyword") == "stop"]
    if (
        len(stop_nodes) != 1
        or str(stop_nodes[0].get("as") or "") != STOP_AS
        or str((stop_nodes[0].get("input") or {}).get("stop_with_error") or "") != "true"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} catch stop step changed: {stop_nodes}")
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "table_id": TABLE_ID,
        "topic_id": TOPIC_ID,
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


def seed_97879578(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_97879578(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be an explicit empty object -- the recipe "
            f"never dereferences a trigger field; got {trigger}"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["workato_db_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the workato_db_table section; "
            f"got {sorted(seed_in.keys())}"
        )
    _require_db_section(seed_in["workato_db_table"])
    force = data.get("force_action_error")
    if force is not None:
        _require_force_shape(force)
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    if (force is not None) != bool(expect.get("catch_used")):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.catch_used must be true exactly when the variant seeds "
            "force_action_error (the catch is unreachable organically on the mock)"
        )
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


def run_97879578(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_97879578(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
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
    result["verifier"] = verify_97879578(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


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
            "(zero-match variants seed only Completed/Exempted rows)"
        )
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table row {idx} must be an object")
        for field in REQUIRED_ROW_FIELDS:
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table row {idx} requires non-empty string {field!r} "
                    "(status feeds the ne-filters; course/email/record feed the tracker)"
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


def _require_force_shape(force: Any) -> None:
    if not isinstance(force, dict) or sorted(force.keys()) != ["error", "step_as"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error must be exactly "
            f"{{'step_as': {GET_RECORDS_AS!r}, 'error': <message>}}; got {force}"
        )
    if str(force.get("step_as") or "") != GET_RECORDS_AS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error only targets the TRY-wrapped get_records "
            f"step {GET_RECORDS_AS!r} (the only organically-unfailable read); got {force}"
        )
    if not isinstance(force.get("error"), str) or not force["error"].strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error.error must be a non-empty message "
            "(it drives the catch IF's 30000ms containment split)"
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
    return ctx.tools.call("harness.workato_db_table.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
