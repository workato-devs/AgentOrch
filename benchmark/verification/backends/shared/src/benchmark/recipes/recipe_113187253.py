from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_113187253


RECIPE_ID = "113187253"
SEED_TYPE = "api_platform_jamf_lock_passcode_history_variant"
TRACK = "workato_api_platform_jamf_lock_passcode_history"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "b9957e99"
SQL_STEP_AS = "0c921f5f"
SUCCESS_RETURN_AS = "452d8e25"
CATCH_AS = "ca54e56b"
CATCH_RETURN_AS = "30d5d137"
# 2-part schema.table names: _parts() maps them onto the benchmark database
# (<SNOWFLAKE_DATABASE>.JAMF.LOCK / <SNOWFLAKE_DATABASE>.SYCOMP.JAMF_LOCK).
JAMF_TABLE = "jamf.lock"
SYCOMP_TABLE = "sycomp.jamf_lock"
RAW_SQL = (
    "select pin, created_at\n"
    "from jamf.lock\n"
    "where serial_number = :serial_number\n"
    "union\n"
    "select pin::text, date_created as created_at\n"
    "from sycomp.jamf_lock\n"
    "where serialnumber = :serial_number"
)
# The connector's SEPARATE Order-by input ('created_at DESC') is appended by
# the engine because the raw SQL carries no ORDER BY (raw_executor
# snowflake_search_rows_sql; re-probed on the current tree). Snowflake
# applies a trailing ORDER BY to the WHOLE union result.
RESOLVED_SQL = RAW_SQL + " ORDER BY created_at DESC"
ANON_SUPPORT_LITERAL = "<anon>support@company.com</anon>"

# workato_api_platform.receive_request (as b9957e99, request schema
# [serial_number string REQUIRED]) -- request.serial_number is dereferenced
# TWICE: as the bind parameter of step 3 and as the 200-response echo.
# Responses declared 200/400. Body = one TRY:
#   3  snowflake.search_rows_sql 0c921f5f (LIVE): RAW_SQL -- a UNION whose
#      TWO arms both bind the SAME :serial_number name (parameters.data has
#      one key; pyformat repeats %(serial_number)s -- re-probed via
#      _bind_sql). The sycomp arm casts its INTEGER pin with ::text (the
#      `(?<!:)` lookbehind in _bind_sql leaves `::text` untouched) and
#      aliases date_created as created_at. UNION (not UNION ALL) DEDUPES
#      identical (pin, created_at) tuples across the arms. The connector
#      orderby input appends ORDER BY created_at DESC over the union.
#      No limit/offset inputs exist on the node.
#   4  return_response 452d8e25 http 200 {serial_number: request pill,
#      passcodes: ____source over rows -> {passcode <- pin_1c4f7b84,
#      date_generated <- created_at_9bdc63f8}}. The HASH-SUFFIXED pill names
#      resolve via lookup_path's `_<8-hex>` strip + case-insensitive retry
#      over the live row keys. TERMINAL. Zero rows -> passcodes [].
#   5  CATCH ca54e56b (max_retry_count 0) -> 6 return_response 30d5d137
#      http 400 {error_message: 'Please contact
#      <anon>support@company.com</anon> with the Job ID: #{job_context
#      .job_id}'} -- the anon-tagged support email renders VERBATIM (989
#      registered outputs already pin <anon> strings); job_id comes from the
#      seeded job_context. TERMINAL.
#
# Branch mapping:
# - union_merge_ordered 200: rows in BOTH tables incl. one identical
#   (pin, created_at) pair across tables -> UNION dedupes it; passcodes pin
#   the exact created_at-DESCENDING list.
# - single_source 200: the serial exists only in sycomp -> every passcode
#   comes from the ::text-cast arm (int pins render as strings).
# - zero-row 200: unknown serial -> {serial_number, passcodes: []}.
# - catch 400: seed.force_action_error on 0c921f5f raises BEFORE the live
#   adapter -> catch -> 400 {error_message}. 1 action; owns NO live state.
#
# DETERMINISM: created_at values must be DISTINCT across the DEDUPED result
# set (an ORDER BY tie would make the passcode order non-groundtruth); the
# seeder enforces it. Timestamps seed as 'YYYY-MM-DD HH:MM:SS' and read back
# as naive isoformat 'YYYY-MM-DDTHH:MM:SS' (_json_value).
# Backends: Snowflake runs LIVE (create-or-replace both tables, dropped in
# the runner's finally; READ-ONLY -- snapshot equality pinned). The API
# platform trigger/responses are deterministic Workato-internal mocks.

_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "b9957e99",
  "provider": "workato_api_platform",
  "name": "receive_request",
  "skip": false,
  "input": {
   "request": {
    "content_type": "json",
    "headers": "[]",
    "schema": "[{\"name\":\"serial_number\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Serial number\"}]"
   },
   "response": {
    "content_type": "json",
    "responses": [
     {
      "body_schema": "[{\"name\":\"serial_number\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Serial number\"},{\"name\":\"passcodes\",\"type\":\"array\",\"optional\":false,\"label\":\"Passcodes\",\"properties\":[{\"name\":\"passcode\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Passcode\"},{\"name\":\"date_generated\",\"type\":\"date_time\",\"optional\":false,\"control_type\":\"date_time\",\"label\":\"Date generated\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\"}],\"of\":\"object\"}]",
      "http_status_code": "200",
      "name": "Successful"
     },
     {
      "body_schema": "[{\"name\":\"error_message\",\"type\":\"string\",\"optional\":false,\"label\":\"Error Message\",\"control_type\":\"text\"}]",
      "http_status_code": "400",
      "name": "Failed"
     }
    ]
   }
  }
 },
 {
  "keyword": "try",
  "number": 2,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {}
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "0c921f5f",
  "provider": "snowflake",
  "name": "search_rows_sql",
  "skip": false,
  "input": {
   "orderby": "created_at DESC",
   "output_schema": "[{\"control_type\":\"text\",\"label\":\"Pin\",\"type\":\"string\",\"name\":\"pin\"},{\"control_type\":\"text\",\"label\":\"Created at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"type\":\"date_time\",\"name\":\"created_at\"}]",
   "parameters": {
    "data": {
     "serial_number": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"b9957e99\",\"path\":[\"request\", \"serial_number\"]}')}"
    },
    "schema": "[{\"name\":\"serial_number\",\"type\":\"string\",\"optional\":true,\"label\":\"serial_number\",\"details\":{\"real_name\":\"serial_number\"},\"control_type\":\"text\"}]"
   },
   "sql": "select pin, created_at\nfrom jamf.lock\nwhere serial_number = :serial_number\nunion\nselect pin::text, date_created as created_at\nfrom sycomp.jamf_lock\nwhere serialnumber = :serial_number"
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "452d8e25",
  "provider": "workato_api_platform",
  "name": "return_response",
  "skip": false,
  "input": {
   "http_status_code": "200",
   "response": {
    "passcodes": {
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"0c921f5f\",\"path\":[\"rows\"]}')}",
     "date_generated": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"0c921f5f\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"created_at_9bdc63f8\"]}')}",
     "passcode": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"0c921f5f\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"pin_1c4f7b84\"]}')}"
    },
    "serial_number": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"b9957e99\",\"path\":[\"request\", \"serial_number\"]}')}"
   }
  }
 },
 {
  "keyword": "catch",
  "number": 5,
  "as": "ca54e56b",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "max_retry_count": "0",
   "retry_interval": "2"
  }
 },
 {
  "keyword": "action",
  "number": 6,
  "as": "30d5d137",
  "provider": "workato_api_platform",
  "name": "return_response",
  "skip": false,
  "input": {
   "http_status_code": "400",
   "response": {
    "error_message": "Please contact <anon>support@company.com</anon> with the Job ID: #{_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_id\"]}')}"
   }
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = list(EXPECTED_RAW_TOOLS)
EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "http_status_code",
    "response",
    "return_step_as",
    "sql_row_count",
)
OPTIONAL_EXPECT_KEYS = {"catch_message"}
RETURN_STEP_AS = (SUCCESS_RETURN_AS, CATCH_RETURN_AS)
# jamf.lock: pin is a STRING column; sycomp.jamf_lock: pin is an INTEGER
# (NUMBER) column -- the SQL's ::text cast is what makes the union arms
# type-compatible. Both timestamp columns read back naive isoformat.
JAMF_COLUMNS = {
    "SERIAL_NUMBER": "string",
    "PIN": "string",
    "CREATED_AT": "timestamp",
}
SYCOMP_COLUMNS = {
    "SERIALNUMBER": "string",
    "PIN": "number",
    "DATE_CREATED": "timestamp",
}
_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


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


def validate_113187253(raw: dict[str, Any]) -> dict[str, Any]:
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
    # Semantic pins on the drift-prone pieces (the tree pin holds the bytes;
    # these name the trap when one changes).
    sql_pin = next(pin for pin in actual if pin["as"] == SQL_STEP_AS)
    if sql_pin["input"].get("sql") != RAW_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} union SQL changed: {sql_pin['input'].get('sql')!r}")
    if str(sql_pin["input"].get("orderby") or "") != "created_at DESC":
        raise RuntimeError(
            f"recipe {RECIPE_ID} connector orderby changed -- the appended ORDER BY "
            f"analysis no longer holds: {sql_pin['input'].get('orderby')!r}"
        )
    if RAW_SQL.count(":serial_number") != 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expects the single :serial_number bind name in BOTH "
            "union arms"
        )
    if "pin::text" not in RAW_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} the sycomp ::text cast changed")
    response_pin = next(pin for pin in actual if pin["as"] == SUCCESS_RETURN_AS)
    passcodes = ((response_pin["input"].get("response") or {}).get("passcodes") or {})
    if "pin_1c4f7b84" not in str(passcodes.get("passcode")) or "created_at_9bdc63f8" not in str(
        passcodes.get("date_generated")
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} hash-suffixed pill names changed -- the `_<8-hex>` "
            f"strip-fallback analysis no longer holds: {passcodes!r}"
        )
    catch_pin = next(pin for pin in actual if pin["as"] == CATCH_RETURN_AS)
    error_template = str((catch_pin["input"].get("response") or {}).get("error_message") or "")
    if ANON_SUPPORT_LITERAL not in error_template or "job_id" not in error_template:
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch error_message template changed: {error_template!r}"
        )
    actions = [pin for pin in actual if pin["keyword"] == "action"]
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "jamf_table": JAMF_TABLE,
        "sycomp_table": SYCOMP_TABLE,
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


def seed_113187253(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_113187253(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    serial = _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    expect = data.get("expect")
    force = data.get("force_action_error")
    _require_force_shape(force)
    _require_expect_shape(expect, force, serial, data)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": deepcopy(expect),
    }
    if force is not None:
        # CATCH branch: the forced error fires BEFORE the snowflake adapter
        # runs, so this variant owns no live resources and must not seed any.
        if sorted(seed_in.keys()) != []:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must not seed live sections "
                f"(nothing runs against Snowflake); got {sorted(seed_in.keys())}"
            )
    else:
        if sorted(seed_in.keys()) != ["snowflake_live"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} non-catch variants must seed exactly the "
                f"snowflake_live section; got {sorted(seed_in.keys())}"
            )
        jamf_rows, sycomp_rows = _require_snowflake_section(seed_in["snowflake_live"])
        derived = _derive_response(serial, jamf_rows, sycomp_rows)
        if expect.get("response") != derived:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.response contradicts the seeded lock rows: "
                f"expected {derived!r}, got {expect.get('response')!r}"
            )
        if expect.get("sql_row_count") != len(derived["passcodes"]):
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.sql_row_count must equal the DEDUPED union "
                f"row count {len(derived['passcodes'])}; got {expect.get('sql_row_count')!r}"
            )
        provision = ctx.tools.call(
            "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
        )
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
        out["snowflake_live"] = deepcopy(provision["state"])
        out["snowflake_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_113187253(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_113187253(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    live = isinstance(seed.get("snowflake_live"), dict)
    if not live and not isinstance(seed.get("force_action_error"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed carries neither snowflake_live state nor a forced "
            "catch error -- nothing to run"
        )
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    raw_execution: dict[str, Any] | None = None
    snowflake_cleanup: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = _snapshot(ctx, live)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx, live)
    finally:
        if live:
            # Both lock tables are benchmark-owned create-or-replace live
            # state: drop them even when execution fails (cleanup principle).
            # Catch variants own no live state.
            snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    details["cleanup_response"] = {"snowflake_live": snowflake_cleanup}
    if live and not (snowflake_cleanup or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake cleanup failed: {snowflake_cleanup}")
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_113187253(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> str:
    if sorted(trigger.keys()) != ["request"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the request object "
            f"(schema [serial_number]); got {sorted(trigger.keys())}"
        )
    request = trigger.get("request")
    if not isinstance(request, dict) or sorted(request.keys()) != ["serial_number"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.request must carry exactly serial_number; "
            f"got {request!r}"
        )
    serial = request.get("serial_number")
    if not isinstance(serial, str) or not serial.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} request.serial_number must be a non-empty string "
            f"(required trigger field); got {serial!r}"
        )
    return serial


def _require_force_shape(force: Any) -> None:
    if force is None:
        return
    if not isinstance(force, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error must be an object")
    if str(force.get("step_as") or "") != SQL_STEP_AS or not str(force.get("error") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error must target step_as {SQL_STEP_AS!r} "
            "with an explicit error message (the only fallible step inside the TRY)"
        )


def _require_expect_shape(expect: Any, force: Any, serial: str, data: dict[str, Any]) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(EXPECT_KEYS) - OPTIONAL_EXPECT_KEYS)
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if expect.get("return_step_as") not in RETURN_STEP_AS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.return_step_as must be one of {RETURN_STEP_AS}"
        )
    catch = force is not None
    if (expect.get("return_step_as") == CATCH_RETURN_AS) != catch:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the catch return step and force_action_error must be "
            "declared together (the static union SQL has no other deterministic failure)"
        )
    if str(expect.get("http_status_code")) != ("400" if catch else "200"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} http_status_code must be 400 on catch, 200 otherwise; "
            f"got {expect.get('http_status_code')!r}"
        )
    if expect.get("executed_action_count") != (1 if catch else 2):
        raise RuntimeError(
            f"recipe {RECIPE_ID} executed_action_count must be 1 on catch (the forced "
            f"error raises before the tool call), 2 otherwise; got "
            f"{expect.get('executed_action_count')!r}"
        )
    if catch:
        job_context = data.get("job_context")
        if not isinstance(job_context, dict) or not str(job_context.get("job_id") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must pin job_context.job_id (the 400 "
                "body renders the job_context.job_id pill)"
            )
        expected_message = (
            f"Please contact {ANON_SUPPORT_LITERAL} with the Job ID: {job_context['job_id']}"
        )
        if expect.get("sql_row_count") is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must pin sql_row_count null (the "
                "forced error raises before the tool call)"
            )
        if "catch_message" not in expect or expect["catch_message"] != force.get("error"):
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must pin expect.catch_message equal "
                "to the forced error text"
            )
        if expect.get("response") != {"error_message": expected_message}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must pin response "
                f"{{'error_message': {expected_message!r}}}; got {expect.get('response')!r}"
            )
        if expect.get("tools") != ["workato_api_platform.return_response"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants trace exactly the 400 return; got "
                f"{expect.get('tools')!r}"
            )
    else:
        if "catch_message" in expect:
            raise RuntimeError(f"recipe {RECIPE_ID} only catch variants may pin catch_message")
        if data.get("job_context") is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} only catch variants read job_context (dead seed "
                "state otherwise)"
            )
        if expect.get("tools") != EXPECTED_RAW_TOOLS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} non-catch variants trace search_rows_sql then the "
                f"200 return; got {expect.get('tools')!r}"
            )
        response = expect.get("response")
        if not isinstance(response, dict) or response.get("serial_number") != serial:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.response.serial_number must echo the request "
                f"serial {serial!r}; got {response!r}"
            )
    _require_tool_expectations(expect, catch, serial)


def _require_tool_expectations(expect: dict[str, Any], catch: bool, serial: str) -> None:
    items = expect.get("tool_expectations")
    expected_len = 1 if catch else 2
    if not isinstance(items, list) or len(items) != expected_len:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin all {expected_len} "
            "executed calls"
        )
    if catch:
        (return_item,) = items
        checks = (
            return_item.get("tool") == "workato_api_platform.return_response",
            return_item.get("http_status_code") == "400",
            return_item.get("response_contains") == expect.get("response"),
        )
        if not all(checks):
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch tool_expectations must pin the 400 return "
                f"with the exact error body: {items!r}"
            )
        return
    sql_item, return_item = items
    checks = (
        sql_item.get("tool") == "snowflake.search_rows_sql",
        sql_item.get("args_contains")
        == {"sql": RESOLVED_SQL, "parameters": {"serial_number": serial}},
        sql_item.get("result_count") == expect.get("sql_row_count"),
        return_item.get("tool") == "workato_api_platform.return_response",
        return_item.get("http_status_code") == "200",
        return_item.get("response_contains") == expect.get("response"),
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations do not pin the derived ground truth "
            f"(RESOLVED_SQL + single bind + deduped count + exact 200 body): {items!r}"
        )


def _require_snowflake_section(section: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(no CURRENT_* in the SQL -> current_time must NOT be declared)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted([JAMF_TABLE, SYCOMP_TABLE]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{JAMF_TABLE!r} and {SYCOMP_TABLE!r} (BOTH union arms reference a live table)"
        )
    jamf_rows = _require_table(tables[JAMF_TABLE], JAMF_TABLE, JAMF_COLUMNS, pin_kind=str)
    sycomp_rows = _require_table(tables[SYCOMP_TABLE], SYCOMP_TABLE, SYCOMP_COLUMNS, pin_kind=int)
    if not jamf_rows and not sycomp_rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} at least one table must carry rows -- the zero-match "
            "variant proves the WHERE bind via decoys, not via empty tables"
        )
    return jamf_rows, sycomp_rows


def _require_table(
    spec: Any,
    table: str,
    columns: dict[str, str],
    pin_kind: type,
) -> list[dict[str, Any]]:
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {table} spec must be exactly "
            "{'columns': ..., 'rows': ...}"
        )
    if spec["columns"] != columns:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {table} columns must be exactly {columns} "
            "(jamf pin STRING vs sycomp pin INTEGER is the ::text-cast semantics)"
        )
    rows = spec["rows"]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {table} rows must be a list")
    serial_key, pin_key, ts_key = list(columns.keys())
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(columns.keys()):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {table} row {idx} must fill exactly "
                f"{sorted(columns.keys())}; got {row!r}"
            )
        if not isinstance(row[serial_key], str) or not row[serial_key].strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {table} row {idx} {serial_key} must be a "
                f"non-empty string; got {row[serial_key]!r}"
            )
        if pin_kind is int:
            if isinstance(row[pin_key], bool) or not isinstance(row[pin_key], int):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table} row {idx} PIN must be an integer "
                    f"(NUMBER column exercises the ::text cast); got {row[pin_key]!r}"
                )
        else:
            if not isinstance(row[pin_key], str) or not row[pin_key].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table} row {idx} PIN must be a non-empty "
                    f"string; got {row[pin_key]!r}"
                )
        if not isinstance(row[ts_key], str) or not _TS_RE.fullmatch(row[ts_key]):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {table} row {idx} {ts_key} must be "
                f"'YYYY-MM-DD HH:MM:SS' (stable isoformat read-back); got {row[ts_key]!r}"
            )
    return [dict(row) for row in rows]


def _derive_response(
    serial: str,
    jamf_rows: list[dict[str, Any]],
    sycomp_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Groundtruth of the live union: match each arm on the SAME bind value,
    cast sycomp pins to text, DEDUPE identical (pin, created_at) tuples
    (UNION, not UNION ALL), order created_at DESC. Timestamps read back as
    naive isoformat ('YYYY-MM-DD HH:MM:SS' -> 'YYYY-MM-DDTHH:MM:SS')."""
    tuples: set[tuple[str, str]] = set()
    for row in jamf_rows:
        if row["SERIAL_NUMBER"] == serial:
            tuples.add((str(row["PIN"]), str(row["CREATED_AT"]).replace(" ", "T")))
    for row in sycomp_rows:
        if row["SERIALNUMBER"] == serial:
            tuples.add((str(row["PIN"]), str(row["DATE_CREATED"]).replace(" ", "T")))
    timestamps = [ts for _pin, ts in tuples]
    if len(set(timestamps)) != len(timestamps):
        raise RuntimeError(
            f"recipe {RECIPE_ID} matching rows must carry DISTINCT created_at values "
            "after union dedupe (an ORDER BY tie would make the passcode order "
            f"non-deterministic): {sorted(tuples)}"
        )
    ordered = sorted(tuples, key=lambda item: item[1], reverse=True)
    return {
        "serial_number": serial,
        "passcodes": [
            {"passcode": pin, "date_generated": ts} for pin, ts in ordered
        ],
    }


def _snapshot(ctx: RecipeContext, live: bool) -> dict[str, Any]:
    if not live:
        return {}
    return dict(ctx.tools.call("harness.snowflake.snapshot", {}))


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
