from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_122809739


RECIPE_ID = "122809739"
SEED_TYPE = "api_platform_walnutiq_output_poll_variant"
TRACK = "workato_api_platform_walnutiq_output_poll"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "a322b3cc"
OUTPUTS_TABLE = "walnutiq.outputs"
SQL_STEP_AS = "a94d022e"
SUCCESS_RETURN_AS = "209c4d97"
ELSE_RETURN_AS = "f8346730"
CATCH_RETURN_AS = "4524f2d3"
CATCH_AS = "e49a6953"
RAW_SQL = (
    "SELECT id, content, created_at, output_file_id FROM walnutiq.outputs "
    "WHERE workflow_run_id = :id ORDER BY created_at DESC LIMIT 1"
)

# workato_api_platform.receive_request (as a322b3cc; path_params
# workflow_run_id is the ONLY dereferenced trigger field). Body = one TRY:
#   3  snowflake.run_custom_sql a94d022e (LIVE Snowflake): RAW_SQL with
#      bind :id = path_params.workflow_run_id; the SQL carries its own
#      ORDER BY created_at DESC LIMIT 1 (so the client appends nothing)
#   4  IF rows size > 0 -> 5 return_response 209c4d97 http 201
#      {pending 'false', id / content / created_at / file_link from
#       rows current_item (current_item outside a loop = first row)}
#   6  ELSE -> 7 return_response f8346730 http 200 {pending 'true'}
#   8  CATCH e49a6953 (max_retry_count 0) -> 9 return_response 4524f2d3
#      http 200 {pending 'true'} (same body as ELSE, distinct trace step)
#
# Branch mapping (per benmark_rules):
# - variant_00 latest_row_201: two rows for run 4711 with different
#   created_at plus a NEWER row for another run id (the WHERE must beat
#   recency) -> ORDER BY DESC LIMIT 1 returns the newest 4711 row -> 201
#   pending:'false' with its fields. 2 actions.
# - variant_01 no_rows_200_pending: run id 9999 matches nothing -> ELSE ->
#   200 {pending 'true'} via f8346730. 2 actions.
# - variant_02 catch_200_pending: seed.force_action_error on a94d022e ->
#   the TRY catches -> 200 {pending 'true'} via 4524f2d3. 1 action (the
#   forced error raises before any tool call). The SQL and table are static,
#   so no trigger-controllable live failure exists; the forced error is the
#   deterministic catch path.
#
# ENGINE FIDELITY NOTES:
# - created_at renders as snowflake_live._json_value isoformat of the live
#   TIMESTAMP_NTZ read-back (naive, e.g. '2026-06-30T18:45:30'); seeds use
#   'YYYY-MM-DD HH:MM:SS' literals so the rendered form is stable and the
#   expects pin it exactly.
# - response.pending is the raw literal string 'false'/'true' (the
#   boolean_conversion in the schema is not applied by the engine).
# - the :id bind carries the path-param STRING against the NUMBER
#   workflow_run_id column; live Snowflake implicitly casts numeric strings.
#   Seeds only use numeric-string run ids. VERIFY on the first live run.
#
# Backends: Snowflake runs LIVE (harness.snowflake_live.seed_tables
# create-or-replace; dropped in the runner's finally). walnutiq.outputs is a
# 2-part name -> WALNUTIQ schema in the live database. The API platform
# trigger/responses are deterministic Workato-internal mocks (terminal).
# The recipe is READ-ONLY on Snowflake (snapshot equality verifier-pinned).

_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "a322b3cc",
  "provider": "workato_api_platform",
  "name": "receive_request",
  "skip": false,
  "input": {
   "request": {
    "content_type": "json",
    "path_params": "[{\"name\":\"workflow_run_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Workflow run ID\"}]"
   },
   "response": {
    "content_type": "json",
    "responses": [
     {
      "body_schema": "[{\"control_type\":\"checkbox\",\"label\":\"Pending\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"name\":\"pending\",\"type\":\"boolean\",\"optional\":false,\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Pending\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"pending\",\"type\":\"boolean\",\"optional\":false}},{\"control_type\":\"text\",\"label\":\"ID\",\"name\":\"id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Content\",\"name\":\"content\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Created at\",\"name\":\"created_at\",\"type\":\"string\",\"optional\":false},{\"name\":\"file_link\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"File link\"}]",
      "http_status_code": "201",
      "name": "Success"
     },
     {
      "body_schema": "[{\"name\":\"pending\",\"type\":\"boolean\",\"optional\":false,\"control_type\":\"checkbox\",\"label\":\"Pending\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Pending\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"pending\",\"type\":\"boolean\",\"optional\":false}}]",
      "http_status_code": "200",
      "name": "Error"
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
  "as": "a94d022e",
  "provider": "snowflake",
  "name": "run_custom_sql",
  "skip": false,
  "input": {
   "output_schema": "[{\"control_type\":\"text\",\"label\":\"ID\",\"type\":\"string\",\"name\":\"id\"},{\"control_type\":\"text\",\"label\":\"Content\",\"type\":\"string\",\"name\":\"content\"},{\"control_type\":\"text\",\"label\":\"Created at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"type\":\"date_time\",\"name\":\"created_at\"},{\"name\":\"output_file_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Output file ID\"}]",
   "parameters": {
    "data": {
     "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"a322b3cc\",\"path\":[\"path_params\", \"workflow_run_id\"]}')}"
    },
    "schema": "[{\"name\":\"id\",\"type\":\"integer\",\"optional\":true,\"label\":\"id\",\"details\":{\"real_name\":\"id\"},\"control_type\":\"integer\"}]"
   },
   "sql": "SELECT id, content, created_at, output_file_id FROM walnutiq.outputs WHERE workflow_run_id = :id ORDER BY created_at DESC LIMIT 1",
   "update_only": "false"
  }
 },
 {
  "keyword": "if",
  "number": 4,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"a94d022e\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "greater_than",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "209c4d97",
  "provider": "workato_api_platform",
  "name": "return_response",
  "skip": false,
  "input": {
   "http_status_code": "201",
   "response": {
    "content": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"a94d022e\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"content\"]}')}",
    "created_at": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"a94d022e\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"created_at\"]}')}",
    "file_link": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"a94d022e\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"output_file_id\"]}')}",
    "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"a94d022e\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}",
    "pending": "false"
   }
  }
 },
 {
  "keyword": "else",
  "number": 6,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {}
 },
 {
  "keyword": "action",
  "number": 7,
  "as": "f8346730",
  "provider": "workato_api_platform",
  "name": "return_response",
  "skip": false,
  "input": {
   "http_status_code": "200",
   "response": {
    "pending": "true"
   }
  }
 },
 {
  "keyword": "catch",
  "number": 8,
  "as": "e49a6953",
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
  "number": 9,
  "as": "4524f2d3",
  "provider": "workato_api_platform",
  "name": "return_response",
  "skip": false,
  "input": {
   "http_status_code": "200",
   "response": {
    "pending": "true"
   }
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "workato_api_platform.return_response",
]
EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "http_status_code",
    "response",
    "return_step_as",
)
OPTIONAL_EXPECT_KEYS = {"catch_message"}
RETURN_STEP_AS = (SUCCESS_RETURN_AS, ELSE_RETURN_AS, CATCH_RETURN_AS)


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


def validate_122809739(raw: dict[str, Any]) -> dict[str, Any]:
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
    sql_pin = next(pin for pin in actual if pin["as"] == SQL_STEP_AS)
    if sql_pin["input"].get("sql") != RAW_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} custom SQL changed: {sql_pin['input'].get('sql')!r}")
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


def seed_122809739(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_122809739(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"snowflake_live"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    expect = data.get("expect")
    force = data.get("force_action_error")
    _require_force_shape(force)
    _require_expect_shape(expect, force)
    _require_snowflake_section(seed_in.get("snowflake_live"))
    provision = ctx.tools.call(
        "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": deepcopy(expect),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_122809739(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_122809739(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live section")
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
        details["initial_snapshot"] = _snapshot(ctx)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx)
    finally:
        # walnutiq.outputs is benchmark-owned create-or-replace live state:
        # drop it even when execution fails (cleanup principle). The API
        # responses are not persistent.
        snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    details["cleanup_response"] = {"snowflake_live": snowflake_cleanup}
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
    result["verifier"] = verify_122809739(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {"path_params"} or not isinstance(trigger.get("path_params"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'path_params': {{...}}}}"
        )
    path_params = trigger["path_params"]
    if set(path_params) != {"workflow_run_id"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} path_params must declare exactly workflow_run_id"
        )
    run_id = path_params["workflow_run_id"]
    if not isinstance(run_id, str) or not run_id.isdigit():
        raise RuntimeError(
            f"recipe {RECIPE_ID} workflow_run_id must be a numeric string (the :id bind "
            f"compares against the NUMBER workflow_run_id column live): {run_id!r}"
        )


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


def _require_expect_shape(expect: Any, force: Any) -> None:
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
    if (expect.get("return_step_as") == CATCH_RETURN_AS) != (force is not None):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the catch return step and force_action_error must be "
            "declared together (the static SQL has no other deterministic failure)"
        )
    if "catch_message" in expect and force is not None and expect["catch_message"] != force.get("error"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.catch_message must equal the forced error text"
        )


def _require_snowflake_section(section: Any) -> None:
    if not isinstance(section, dict) or not isinstance(section.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.snowflake_live.tables")
    if sorted(section["tables"]) != [OUTPUTS_TABLE]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly {OUTPUTS_TABLE!r}"
        )
    spec = section["tables"][OUTPUTS_TABLE]
    if not isinstance(spec, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} snowflake table spec must be an object")
    columns = spec.get("columns")
    expected_columns = {
        "ID": "string",
        "CONTENT": "string",
        "CREATED_AT": "timestamp",
        "OUTPUT_FILE_ID": "string",
        "WORKFLOW_RUN_ID": "number",
    }
    if columns != expected_columns:
        raise RuntimeError(
            f"recipe {RECIPE_ID} walnutiq.outputs columns must be exactly {expected_columns} "
            f"(TIMESTAMP -> TIMESTAMP_NTZ keeps the created_at isoformat rendering stable)"
        )
    rows = spec.get("rows")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} walnutiq.outputs must declare a non-empty rows list "
            "(the pending variant seeds rows for OTHER run ids, never an empty table)"
        )
    for row in rows:
        if not isinstance(row, dict) or set(row) != set(expected_columns):
            raise RuntimeError(
                f"recipe {RECIPE_ID} every walnutiq.outputs row must fill all declared columns: {row!r}"
            )
        if not isinstance(row["WORKFLOW_RUN_ID"], int):
            raise RuntimeError(
                f"recipe {RECIPE_ID} WORKFLOW_RUN_ID must be an integer (NUMBER column): {row!r}"
            )


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return dict(ctx.tools.call("harness.snowflake.snapshot", {}))


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
