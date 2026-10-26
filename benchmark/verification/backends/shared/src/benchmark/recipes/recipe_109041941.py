from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_109041941


RECIPE_ID = "109041941"
SEED_TYPE = "workato_job_retry_pagination_variant"
TRACK = "workato_db_table_job_retry_loop"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "e927c754"
TABLE_ID = "17244"
COL_ID = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
COL_RECIPE = "e6ee22c4_0ce7_4a9f_b7b7_fc0a3c43f116"
COL_JOB = "aa006927_6cb7_4f29_b521_3b0fc0851b88"
COL_ERR = "78ed4fbf_788d_49dc_a971_930aff4dd0a1"
COL_RETRY = "9c21b0ac_dce3_43aa_a601_1d14a2b75600"
COL_CREATED = "a5612739_5401_4ae7_bd07_782c1a6fb2d1"
COL_UPDATED = "61aae604_a95e_4519_9091_bb0bf754a67f"
ROW_COLUMNS = (COL_ID, COL_JOB, COL_RECIPE, COL_ERR, COL_RETRY, COL_CREATED, COL_UPDATED)
RERUN_AS = "a9474f43"
STOP_STEP_NUMBER = 11
CATCH_CONTINUE_FRAGMENT = "It has not completed yet"
TOKEN_OMITTED = "<omitted>"

SEED_SECTIONS = {"workato_db_table"}
EXPECT_KEYS = (
    "tools",
    "tool_expectations",
    "trace_tools",
    "executed_action_count",
    "stopped",
    "continuation_tokens",
    "final_table_rows",
)
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "workato_db_table.get_records",
    "workato_app.rerun_jobs",
    "workato_db_table.update_record",
    "workato_runtime.update_variables",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_app.rerun_jobs",
    "workato_db_table.update_record",
]

_STRUCTURE_PINS_JSON = r'''
[
 {
  "as": "e927c754",
  "input": {
   "time_unit": "minutes",
   "trigger_every": "30"
  },
  "keyword": "trigger",
  "name": "scheduled_event",
  "number": 1,
  "provider": "clock",
  "skip": false
 },
 {
  "as": "ca43cdfa",
  "input": {
   "variables": {
    "data": {
     "limit": "200",
     "total_count": "0"
    },
    "schema": "[{\"control_type\":\"text\",\"label\":\"Cursor\",\"name\":\"cursor\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"Cursor\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"integer\",\"label\":\"Limit\",\"parse_output\":\"integer_conversion\",\"name\":\"limit\",\"type\":\"integer\",\"optional\":true,\"details\":{\"real_name\":\"Limit\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"name\":\"total_count\",\"type\":\"integer\",\"optional\":true,\"label\":\"Total Count\",\"details\":{\"real_name\":\"Total Count\"},\"control_type\":\"integer\",\"parent\":[\"variables\",\"data\"]}]"
   }
  },
  "keyword": "action",
  "name": "declare_variable",
  "number": 2,
  "provider": "workato_variable",
  "skip": false
 },
 {
  "as": "df17b6c8",
  "input": {},
  "keyword": "repeat",
  "name": null,
  "number": 3,
  "provider": null,
  "skip": false
 },
 {
  "as": "fc16e458",
  "input": {
   "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id",
   "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time",
   "78ed4fbf-788d-49dc-a971-930aff4dd0a1": "string",
   "9c21b0ac-dce3-43aa-a601-1d14a2b75600": "integer",
   "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time",
   "aa006927-6cb7-4f29-b521-3b0fc0851b88": "string",
   "continuation_token": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"ca43cdfa\",\"path\":[\"cursor\"]}').presence || skip",
   "e6ee22c4-0ce7-4a9f-b7b7-fc0a3c43f116": "string",
   "limit": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"ca43cdfa\",\"path\":[\"limit\"]}')}",
   "order_by_field_id": "aa006927-6cb7-4f29-b521-3b0fc0851b88",
   "order_direction": "asc",
   "table_id": "17244"
  },
  "keyword": "action",
  "name": "get_records",
  "number": 4,
  "provider": "workato_db_table",
  "skip": false
 },
 {
  "as": "544078ee",
  "input": {
   "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"fc16e458\",\"path\":[\"records\"]}')}"
  },
  "keyword": "foreach",
  "name": null,
  "number": 5,
  "provider": null,
  "repeat_mode": "simple",
  "skip": false,
  "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"fc16e458\",\"path\":[\"records\"]}')}"
 },
 {
  "as": null,
  "input": {},
  "keyword": "try",
  "name": null,
  "number": 6,
  "provider": null,
  "skip": false
 },
 {
  "as": "a9474f43",
  "input": {
   "jobs": [
    {
     "job_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"544078ee\",\"path\":[\"aa006927_6cb7_4f29_b521_3b0fc0851b88\"]}')}"
    }
   ],
   "recipe_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"544078ee\",\"path\":[\"e6ee22c4_0ce7_4a9f_b7b7_fc0a3c43f116\"]}')}"
  },
  "keyword": "action",
  "name": "rerun_jobs",
  "number": 7,
  "provider": "workato_app",
  "skip": false
 },
 {
  "as": "c1d510c6",
  "input": {
   "max_retry_count": "0",
   "retry_interval": "2"
  },
  "keyword": "catch",
  "name": null,
  "number": 8,
  "provider": null,
  "skip": false
 },
 {
  "as": "7927a7b5",
  "input": {
   "parameters": {
    "78ed4fbf_788d_49dc_a971_930aff4dd0a1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"c1d510c6\",\"path\":[\"message\"]}')}",
    "9c21b0ac_dce3_43aa_a601_1d14a2b75600": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"544078ee\",\"path\":[\"9c21b0ac_dce3_43aa_a601_1d14a2b75600\"]}') + 1"
   },
   "record_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"544078ee\",\"path\":[\"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\"]}')}",
   "table_id": "17244"
  },
  "keyword": "action",
  "name": "update_record",
  "number": 9,
  "provider": "workato_db_table",
  "skip": false
 },
 {
  "as": null,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"c1d510c6\",\"path\":[\"message\"]}')}",
     "operand": "not_contains",
     "rhs": "It has not completed yet"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "keyword": "if",
  "name": null,
  "number": 10,
  "provider": null,
  "skip": false
 },
 {
  "as": "9cb4faab",
  "input": {
   "stop_reason": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"c1d510c6\",\"path\":[\"message\"]}')}",
   "stop_with_error": "true"
  },
  "keyword": "stop",
  "name": null,
  "number": 11,
  "provider": null,
  "skip": false
 },
 {
  "as": "47e49dd2",
  "input": {
   "cursor": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"fc16e458\",\"path\":[\"continuation_token\"]}').presence || clear",
   "name": "66c4a53f-c03b-4996-bf77-0ed7cdd6951a:ca43cdfa:cursor\n66c4a53f-c03b-4996-bf77-0ed7cdd6951a:ca43cdfa:total_count",
   "total_count": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"ca43cdfa\",\"path\":[\"total_count\"]}') + (_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"fc16e458\",\"path\":[\"records\",{\"path_element_type\":\"size\"}]}').presence || 0)"
  },
  "keyword": "action",
  "name": "update_variables",
  "number": 12,
  "provider": "workato_variable",
  "skip": false
 },
 {
  "as": null,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"fc16e458\",\"path\":[\"continuation_token\"]}')}",
     "operand": "present",
     "rhs": ""
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "keyword": "while_condition",
  "name": null,
  "number": 13,
  "provider": null,
  "skip": false
 }
]
'''
STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)


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
        pin["source"] = node.get("source")
    if isinstance(node.get("filter"), dict):
        pin["filter"] = node["filter"]
    out = [pin]
    for child in node.get("block") or []:
        if isinstance(child, dict):
            out.extend(_structure(child))
    return out


def validate_109041941(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger 'as' changed: {raw.get('as')!r}")
    if raw.get("filter") is not None:
        raise RuntimeError(f"recipe {RECIPE_ID} grew a trigger filter: {raw.get('filter')!r}")
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


def _require_table_seed(section: Any) -> tuple[list[dict[str, Any]], str | None]:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.workato_db_table")
    unexpected = sorted(set(section) - {"tables", "continuation_tokens"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.workato_db_table unexpected keys: {unexpected}")
    tables = section.get("tables")
    if not isinstance(tables, dict) or sorted(tables.keys()) != [TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly table {TABLE_ID} "
            "(an empty list is a valid declared-but-empty table)"
        )
    rows = tables[TABLE_ID]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {TABLE_ID} rows must be a list")
    seen_ids: set[str] = set()
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(ROW_COLUMNS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} must carry exactly the 7 declared "
                f"columns: {sorted(row.keys()) if isinstance(row, dict) else row!r}"
            )
        for column in (COL_ID, COL_JOB, COL_RECIPE):
            if not str(row.get(column) or "").strip():
                raise RuntimeError(f"recipe {RECIPE_ID} table row {idx} requires non-empty {column}")
        if not isinstance(row.get(COL_RETRY), int) or isinstance(row.get(COL_RETRY), bool):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} retry count must be an int "
                "(the catch branch computes row.retry + 1 arithmetically)"
            )
        row_id = str(row[COL_ID])
        if row_id in seen_ids:
            raise RuntimeError(f"recipe {RECIPE_ID} duplicate table row id {row_id!r}")
        seen_ids.add(row_id)
    token: str | None = None
    if "continuation_tokens" in section:
        tokens = section.get("continuation_tokens")
        if (
            not isinstance(tokens, dict)
            or sorted(tokens.keys()) != [TABLE_ID]
            or not isinstance(tokens[TABLE_ID], str)
            or not tokens[TABLE_ID]
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} continuation_tokens must be the plain first-page form "
                f"{{'{TABLE_ID}': '<token>'}}: {tokens!r}"
            )
        token = tokens[TABLE_ID]
    return rows, token


def _require_force(data: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    force = data.get("force_action_error")
    if force is None:
        return None
    if not isinstance(force, dict) or sorted(force.keys()) != ["error", "step_as"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error must be exactly {{step_as, error}}: {force!r}"
        )
    if str(force.get("step_as") or "") != RERUN_AS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error must target the rerun_jobs step "
            f"{RERUN_AS!r}: {force.get('step_as')!r}"
        )
    if not str(force.get("error") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error requires an explicit error string")
    if len(rows) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} forced-error variants must seed exactly one table row "
            "(force_action_error fires on EVERY foreach iteration)"
        )
    return force


def _require_expect_shape(
    expect: Any,
    rows: list[dict[str, Any]],
    token: str | None,
    force: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    tools = expect.get("tools")
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tools, list) or not isinstance(tool_expectations, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools/tool_expectations must be lists")
    if len(tools) != len(tool_expectations):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry")
    unknown = sorted(set(tools) - set(ALLOWED_TOOLS))
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools has unknown tools: {unknown}")
    if not isinstance(expect.get("stopped"), bool):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.stopped must be an explicit boolean")
    if not isinstance(expect.get("trace_tools"), list) or not expect["trace_tools"]:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.trace_tools must pin the full raw trace")
    continuation = expect.get("continuation_tokens")
    if not isinstance(continuation, list) or not continuation:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.continuation_tokens must pin the per-page "
            f"get_records token args ('{TOKEN_OMITTED}' for the SKIP-omitted first page)"
        )
    pages = tools.count("workato_db_table.get_records")
    if len(continuation) != pages:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.continuation_tokens must carry one entry per "
            f"get_records call ({pages}): {continuation!r}"
        )
    if continuation[0] != TOKEN_OMITTED:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the first get_records must omit continuation_token "
            f"('=cursor.presence || skip'): {continuation[0]!r}"
        )
    for entry in continuation[1:]:
        if entry != token:
            raise RuntimeError(
                f"recipe {RECIPE_ID} later pages must pass the seeded first-page token "
                f"{token!r}: {entry!r}"
            )
    if token is not None and pages != 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} a seeded plain first-page token yields exactly two "
            f"get_records pages; expect.tools pins {pages}"
        )
    if token is None and pages != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} without a seeded token the do-while loop runs exactly once; "
            f"expect.tools pins {pages} get_records calls"
        )
    rerun_count = tools.count("workato_app.rerun_jobs")
    update_count = tools.count("workato_db_table.update_record")
    if force is None:
        if update_count:
            raise RuntimeError(
                f"recipe {RECIPE_ID} the catch update_record is reachable only via "
                "force_action_error"
            )
        if rerun_count != len(rows) * pages:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.tools must carry one rerun_jobs per row per page "
                f"({len(rows)}x{pages}): {rerun_count}"
            )
    else:
        if rerun_count:
            raise RuntimeError(
                f"recipe {RECIPE_ID} forced-error variants never complete rerun_jobs "
                "(the forced failure raises before the tool call)"
            )
        stops = CATCH_CONTINUE_FRAGMENT not in str(force.get("error"))
        if expect["stopped"] is not stops:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.stopped must be {stops} for catch message "
                f"{force.get('error')!r} (IF#10 not_contains {CATCH_CONTINUE_FRAGMENT!r})"
            )
        expected_updates = 1 if stops else pages
        if update_count != expected_updates:
            raise RuntimeError(
                f"recipe {RECIPE_ID} forced-error variants perform {expected_updates} catch "
                f"update_record call(s); expect.tools pins {update_count}"
            )
    if expect["stopped"] and force is None:
        raise RuntimeError(f"recipe {RECIPE_ID} the STOP step is reachable only through the catch branch")
    if not isinstance(expect.get("final_table_rows"), list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.final_table_rows must pin the final mock table")
    return expect


def seed_109041941(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_109041941(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (payload-less scheduler "
            f"tick; nothing dereferences the trigger): {trigger!r}"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != sorted(SEED_SECTIONS):
        raise RuntimeError(f"recipe {RECIPE_ID} seed must carry exactly the workato_db_table section")
    rows, token = _require_table_seed(seed_in["workato_db_table"])
    force = _require_force(data, rows)
    expect = _require_expect_shape(data.get("expect"), rows, token, force)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "trigger": trigger,
        "expect": deepcopy(expect),
        "raw_validation": validation,
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_109041941(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_109041941(raw)
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect"),
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    details["initial_snapshot"] = ctx.tools.call("harness.workato_db_table.snapshot", {})
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    details["raw_execution"] = raw_execution
    details["ground_truth"] = _ground_truth(raw_execution)
    details["final_snapshot"] = ctx.tools.call("harness.workato_db_table.snapshot", {})
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_109041941(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
