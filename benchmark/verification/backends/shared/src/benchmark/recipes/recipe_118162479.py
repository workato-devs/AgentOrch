from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_118162479


RECIPE_ID = "118162479"
SEED_TYPE = "api_platform_automation_compass_projects_by_status_variant"
TRACK = "workato_api_platform_snowflake_automation_compass"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "751ec271"
SEARCH_STEP_AS = "d8a6f6bf"
SUCCESS_RETURN_AS = "83954e0e"
CATCH_AS = "2da14745"
CATCH_RETURN_AS = "57671952"
STOP_STEP_AS = "8ce124ba"
# The literal 2-part name the SQL references; MUST be the registered
# snowflake_live table key so _rewrite_sql maps it onto the benchmark
# database (<SNOWFLAKE_DATABASE>.AUTOMATION_COMPASS.BUSINESS_PROCESS_DASHBOARD).
DASHBOARD_TABLE = "AUTOMATION_COMPASS.BUSINESS_PROCESS_DASHBOARD"
RAW_SQL = (
    "SELECT \n  STATUS AS NAME,\n  COUNT(*) AS VALUE\n"
    "FROM AUTOMATION_COMPASS.BUSINESS_PROCESS_DASHBOARD\n"
    "WHERE PROCESS_HIERARCHICAL_LEVEL = 4 -- Only count level 4 items as \"projects\"\n"
    "GROUP BY STATUS\nORDER BY \n  CASE \n    WHEN STATUS = 'Completed' THEN 1\n"
    "    WHEN STATUS = 'In Progress' THEN 2\n    WHEN STATUS = 'Planned' THEN 3\n"
    "    ELSE 4\n  END"
)
RAW_LIMIT = "50000"
# ORDER BY CASE buckets, in recipe order. NOTE the status literal is
# 'In Progress' (space) — sibling 118162476 uses 'In-Progress' (hyphen);
# never cross-contaminate the seed statuses.
CASE_BUCKETS = ("Completed", "In Progress", "Planned")
EXPECTED_COLUMNS = {
    "PROCESS_ID": "string",
    "PROCESS_NAME": "string",
    "PROCESS_HIERARCHICAL_LEVEL": "number",
    "STATUS": "string",
}

# workato_api_platform.receive_request (as 751ec271, request schema [] — NO
# request field is ever dereferenced). Byte-identical BODY twin of 117566182
# (raw_recipe.md differs only in header lines 1 + 11-14); structural sibling
# of registered 118162478 (same shell as-ids/uuids, delta = comment/sql/
# output_schema/response mapping). Body = one TRY (step 2):
#   3  snowflake.search_rows_sql d8a6f6bf (LIVE): RAW_SQL, limit '50000' —
#      WHERE PROCESS_HIERARCHICAL_LEVEL = 4 filters to level-4 "projects";
#      GROUP BY STATUS; ORDER BY CASE Completed->1, 'In Progress'->2,
#      Planned->3, ELSE 4 (any other status sorts LAST).
#   4  workato_api_platform.return_response 83954e0e (mock, TERMINAL): 200,
#      response.projectsByStatus = ____source over rows, one {name, value}
#      per group. Full-pill fields resolve NATIVELY: COUNT(*) arrives
#      Decimal -> int (_json_value), so `value` is an INT in the response
#      (probe-verified 2026-07-08; the "pin strings" note in the batch_C
#      triage is wrong for this shape — 118162478's string pins come from
#      string-TYPED seed columns, not from interpolation).
#   CATCH 2da14745 (max_retry_count 0):
#   6  return_response 57671952 (TERMINAL): 400 {error: catch.message}
#   7  stop 8ce124ba: DEAD CODE — return_response is terminal, so the stop
#      never traces (probe-verified; the catch trace is exactly 1 action).
#
# Branch mapping:
# - status_counts_200: level-4 rows across the named buckets (+ at most ONE
#   ELSE-bucket status) + non-level-4 decoys; seed insertion order differs
#   from CASE order so the live ORDER BY is proven. 2 actions.
# - no_level4_200: only non-level-4 rows (WHERE bites, table NOT empty) ->
#   GROUP BY yields 0 rows -> 200 {projectsByStatus: []}. 2 actions.
# - catch_400: seed.force_action_error on d8a6f6bf (the static SQL has no
#   trigger-controllable live failure) -> 400 {error} after 1 action; NO
#   snowflake state is seeded (the forced error fires before the adapter).
#
# Backends: Snowflake runs LIVE (harness.snowflake_live.seed_tables
# create-or-replace; dropped in the runner's finally). The API platform
# trigger/responses are deterministic Workato-internal mocks. READ-ONLY on
# Snowflake (snapshot equality verifier-pinned). The physical
# AUTOMATION_COMPASS tables are SHARED with 118162477/118162478/117566182 —
# never run family lanes concurrently.

_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "751ec271",
  "provider": "workato_api_platform",
  "name": "receive_request",
  "skip": false,
  "input": {
   "request": {
    "content_type": "json",
    "headers": "[]",
    "path_params": "[]",
    "schema": "[]"
   },
   "response": {
    "content_type": "json",
    "headers": "[{\"name\":\"Access-Control-Allow-Origin\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Access-Control-Allow-Origin\"},{\"name\":\"Access-Control-Allow-Methods\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Access-Control-Allow-Methods\"}]",
    "responses": [
     {
      "body_schema": "[{\"name\":\"projectsByStatus\",\"type\":\"array\",\"of\":\"object\",\"label\":\"Projects by Status\",\"optional\":false,\"properties\":[{\"control_type\":\"text\",\"label\":\"Name\",\"name\":\"name\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"integer\",\"label\":\"Value\",\"parse_output\":\"integer_conversion\",\"name\":\"value\",\"type\":\"integer\",\"optional\":false}]}]",
      "http_status_code": "200"
     },
     {
      "body_schema": "[{\"name\":\"error\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Error\"}]",
      "http_status_code": "400"
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
  "as": "d8a6f6bf",
  "provider": "snowflake",
  "name": "search_rows_sql",
  "skip": false,
  "input": {
   "limit": "50000",
   "output_schema": "[{\"name\":\"NAME\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"NAME\"},{\"name\":\"VALUE\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"VALUE\",\"parse_output\":\"integer_conversion\"}]",
   "sql": "SELECT \n  STATUS AS NAME,\n  COUNT(*) AS VALUE\nFROM AUTOMATION_COMPASS.BUSINESS_PROCESS_DASHBOARD\nWHERE PROCESS_HIERARCHICAL_LEVEL = 4 -- Only count level 4 items as \"projects\"\nGROUP BY STATUS\nORDER BY \n  CASE \n    WHEN STATUS = 'Completed' THEN 1\n    WHEN STATUS = 'In Progress' THEN 2\n    WHEN STATUS = 'Planned' THEN 3\n    ELSE 4\n  END"
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "83954e0e",
  "provider": "workato_api_platform",
  "name": "return_response",
  "skip": false,
  "input": {
   "http_status_code": "200",
   "response": {
    "projectsByStatus": {
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"d8a6f6bf\",\"path\":[\"rows\"]}')}",
     "name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"d8a6f6bf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"name\"]}')}",
     "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"d8a6f6bf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"value\"]}')}"
    }
   },
   "response_headers": {
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Origin": "*"
   }
  }
 },
 {
  "keyword": "catch",
  "number": 5,
  "as": "2da14745",
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
  "as": "57671952",
  "provider": "workato_api_platform",
  "name": "return_response",
  "skip": false,
  "input": {
   "http_status_code": "400",
   "response": {
    "error": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"2da14745\",\"path\":[\"message\"]}')}"
   },
   "response_headers": {
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Origin": "*"
   }
  }
 },
 {
  "keyword": "stop",
  "number": 7,
  "as": "8ce124ba",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "stop_reason": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"2da14745\",\"path\":[\"message\"]}')}",
   "stop_with_error": "true"
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_api_platform.return_response",
]
EXPECT_KEYS = (
    "case",
    "outcome",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "http_status_code",
    "response",
    "sql_row_count",
)
OPTIONAL_EXPECT_KEYS = {"catch_message"}
OUTCOMES = ("status_counts_200", "no_level4_200", "catch_400")


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


def validate_118162479(raw: dict[str, Any]) -> dict[str, Any]:
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
    sql_pin = next(pin for pin in actual if pin["as"] == SEARCH_STEP_AS)
    if sql_pin["input"].get("sql") != RAW_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} search SQL changed: {sql_pin['input'].get('sql')!r}")
    if sql_pin["input"].get("limit") != RAW_LIMIT:
        raise RuntimeError(f"recipe {RECIPE_ID} search limit changed: {sql_pin['input'].get('limit')!r}")
    actions = [pin for pin in actual if pin["keyword"] == "action"]
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "snowflake_table": DASHBOARD_TABLE,
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


def _grouped_status_counts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Derive the live query result from seed rows: WHERE level = 4, GROUP BY
    STATUS, ORDER BY CASE (named buckets first, ELSE bucket last). Values are
    ints — COUNT(*) comes back Decimal -> int and the full-pill response
    mapping keeps it native."""
    counts: dict[str, int] = {}
    first_seen: list[str] = []
    for row in rows:
        if row["PROCESS_HIERARCHICAL_LEVEL"] != 4:
            continue
        status = str(row["STATUS"])
        if status not in counts:
            first_seen.append(status)
        counts[status] = counts.get(status, 0) + 1
    else_statuses = [status for status in first_seen if status not in CASE_BUCKETS]
    if len(else_statuses) > 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} at most ONE else-bucket status may appear among "
            f"level-4 rows (multiple ELSE groups tie at CASE=4 and their relative "
            f"order is not deterministic groundtruth): {sorted(else_statuses)}"
        )
    ordered = [status for status in CASE_BUCKETS if status in counts] + else_statuses
    return [{"name": status, "value": counts[status]} for status in ordered]


def _require_snowflake_section(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the SQL uses no CURRENT_DATE/TIMESTAMP, so current_time is not allowed)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [DASHBOARD_TABLE]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{DASHBOARD_TABLE!r} (the literal 2-part SQL name)"
        )
    spec = tables[DASHBOARD_TABLE]
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table spec must be exactly {{'columns': ..., 'rows': ...}}"
        )
    if spec["columns"] != EXPECTED_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table must declare exactly the columns "
            f"{EXPECTED_COLUMNS} (level NUMBER keeps the '= 4' comparison native)"
        )
    rows = spec["rows"]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table rows must be a NON-EMPTY list — the no-level-4 "
            "branch proves the WHERE clause via decoys, never via an empty table"
        )
    ids: set[str] = set()
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(EXPECTED_COLUMNS.keys()):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} must fill exactly "
                f"{sorted(EXPECTED_COLUMNS.keys())}; got {row!r}"
            )
        if isinstance(row["PROCESS_HIERARCHICAL_LEVEL"], bool) or not isinstance(
            row["PROCESS_HIERARCHICAL_LEVEL"], int
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} row {idx} PROCESS_HIERARCHICAL_LEVEL must be an integer"
            )
        for key in ("PROCESS_ID", "PROCESS_NAME", "STATUS"):
            if not isinstance(row[key], str) or not row[key].strip():
                raise RuntimeError(f"recipe {RECIPE_ID} row {idx} {key} must be non-empty")
        ids.add(str(row["PROCESS_ID"]))
    if len(ids) != len(rows):
        raise RuntimeError(f"recipe {RECIPE_ID} PROCESS_ID values must be distinct")
    return rows


def _require_expect_shape(expect: Any, force: Any, derived: list[dict[str, Any]] | None) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(EXPECT_KEYS) - OPTIONAL_EXPECT_KEYS)
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    outcome = expect.get("outcome")
    if outcome not in OUTCOMES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.outcome must be one of {OUTCOMES}")
    if (outcome == "catch_400") != (force is not None):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the catch outcome and force_action_error must be "
            "declared together (the static SQL has no other deterministic failure)"
        )
    if outcome == "catch_400":
        checks = (
            derived is None,
            expect.get("http_status_code") == "400",
            expect.get("response") == {"error": (force or {}).get("error")},
            expect.get("catch_message") == (force or {}).get("error"),
            expect.get("sql_row_count") is None,
            expect.get("executed_action_count") == 1,
            expect.get("tools") == ["workato_api_platform.return_response"],
        )
        reason = (
            "catch variants pin 400 {error: <forced error>}, catch_message, null "
            "sql_row_count, 1 action, and no snowflake seed"
        )
    else:
        if derived is None:
            raise RuntimeError(f"recipe {RECIPE_ID} try variants require a snowflake_live seed")
        if outcome == "status_counts_200" and not derived:
            raise RuntimeError(
                f"recipe {RECIPE_ID} status_counts_200 requires at least one level-4 group"
            )
        if outcome == "no_level4_200" and derived:
            raise RuntimeError(
                f"recipe {RECIPE_ID} no_level4_200 requires ZERO level-4 rows; got {derived!r}"
            )
        checks = (
            expect.get("http_status_code") == "200",
            expect.get("response") == {"projectsByStatus": derived},
            expect.get("sql_row_count") == len(derived),
            expect.get("executed_action_count") == 2,
            expect.get("tools")
            == ["snowflake.search_rows_sql", "workato_api_platform.return_response"],
            "catch_message" not in expect,
        )
        reason = (
            "try variants must pin the EXACT derived response (WHERE level=4, GROUP "
            f"BY STATUS, CASE order with ELSE last): {{'projectsByStatus': {derived!r}}}"
        )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with outcome "
            f"{outcome!r} ({reason}): {expect!r}"
        )


def _require_order_proof(rows: list[dict[str, Any]], derived: list[dict[str, Any]]) -> None:
    """The main data variants must PROVE the live ORDER BY: with >= 2 groups the
    seed-insertion group order has to differ from the CASE-ordered response."""
    if len(derived) < 2:
        return
    first_seen: list[str] = []
    for row in rows:
        if row["PROCESS_HIERARCHICAL_LEVEL"] == 4 and str(row["STATUS"]) not in first_seen:
            first_seen.append(str(row["STATUS"]))
    if first_seen == [item["name"] for item in derived]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed insertion order equals the CASE order — shuffle "
            f"the seeded rows so the live ORDER BY is actually proven: {first_seen}"
        )


def seed_118162479(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118162479(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {"request": {}}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'request': {{}}}} (the "
            f"request schema is [] and nothing is dereferenced): {trigger!r}"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    force = data.get("force_action_error")
    if force is not None:
        if not isinstance(force, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} force_action_error must be an object")
        if str(force.get("step_as") or "") != SEARCH_STEP_AS or not str(force.get("error") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} force_action_error must target step_as "
                f"{SEARCH_STEP_AS!r} with an explicit error message"
            )
        if seed_in != {}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must seed NOTHING (the forced error "
                f"fires before the snowflake adapter): {sorted(seed_in)}"
            )
        derived = None
        rows = None
    else:
        if sorted(seed_in.keys()) != ["snowflake_live"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} try variants must seed exactly the snowflake_live "
                f"section; got {sorted(seed_in.keys())}"
            )
        rows = _require_snowflake_section(seed_in["snowflake_live"])
        derived = _grouped_status_counts(rows)
        _require_order_proof(rows, derived)
    _require_expect_shape(data.get("expect"), force, derived)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": deepcopy(data["expect"]),
    }
    if force is None:
        provision = ctx.tools.call(
            "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
        )
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
        out["snowflake_live"] = deepcopy(provision["state"])
        out["snowflake_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_118162479(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118162479(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    live = isinstance(seed.get("snowflake_live"), dict)
    if not live and not isinstance(seed.get("force_action_error"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed carries neither snowflake_live state nor a "
            "forced catch error — nothing to run"
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
            # Required cleanup: the shared AUTOMATION_COMPASS dashboard table is
            # benchmark-owned create-or-replace state — drop it whether or not
            # the run completed. Catch variants own NO live state.
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
    result["verifier"] = verify_118162479(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


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
