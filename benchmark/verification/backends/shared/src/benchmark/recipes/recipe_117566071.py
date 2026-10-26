from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_117566071


RECIPE_ID = "117566071"
SEED_TYPE = "api_platform_automation_compass_overview_metrics_variant"
TRACK = "workato_api_platform_snowflake_automation_compass"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "751ec271"
SEARCH_STEP_AS = "d8a6f6bf"
SUCCESS_RETURN_AS = "83954e0e"
CATCH_AS = "2da14745"
CATCH_RETURN_AS = "57671952"
STOP_STEP_AS = "8ce124ba"
DASHBOARD_TABLE = "AUTOMATION_COMPASS.BUSINESS_PROCESS_DASHBOARD"
RAW_SQL = (
    "SELECT \n  CEIL(AVG(COMPLETION_PERCENTAGE)) AS AUTOMATION_SCORE,\n"
    "  CEIL(AVG(AI_READINESS_SCORE)) AS AI_READINESS,\n"
    "  SUM(CASE WHEN PROCESS_HIERARCHICAL_LEVEL = 4 THEN 1 ELSE 0 END) AS TOTAL_PROJECTS,\n"
    "  SUM(CASE WHEN PROCESS_HIERARCHICAL_LEVEL = 4 AND STATUS = 'Completed' THEN 1 ELSE 0 END) AS COMPLETED_PROJECTS,\n"
    "  SUM(CASE WHEN PROCESS_HIERARCHICAL_LEVEL = 4 AND STATUS = 'In Progress' THEN 1 ELSE 0 END) AS IN_PROGRESS_PROJECTS,\n"
    "  SUM(CASE WHEN PROCESS_HIERARCHICAL_LEVEL = 4 AND STATUS = 'Planned' THEN 1 ELSE 0 END) AS PLANNED_PROJECTS,\n"
    "  SUM(CASE WHEN PROCESS_HIERARCHICAL_LEVEL = 4 AND STATUS = 'Unplanned' THEN 1 ELSE 0 END) AS UNPLANNED_PROJECTS,\n"
    "  SUM(CASE WHEN PROCESS_HIERARCHICAL_LEVEL = 4 AND AI_IMPACT_LEVEL >= 3 THEN 1 ELSE 0 END) AS HIGH_VALUE_OPPORTUNITIES\n"
    "\nFROM AUTOMATION_COMPASS.BUSINESS_PROCESS_DASHBOARD"
)
RAW_LIMIT = "50000"
EXPECTED_COLUMNS = {
    "PROCESS_ID": "string",
    "PROCESS_NAME": "string",
    "PROCESS_HIERARCHICAL_LEVEL": "number",
    "STATUS": "string",
    "COMPLETION_PERCENTAGE": "number",
    "AI_READINESS_SCORE": "number",
    "AI_IMPACT_LEVEL": "number",
}
RESPONSE_KEYS = (
    "automationScore",
    "aiReadiness",
    "totalProjects",
    "completedProjects",
    "inProgressProjects",
    "plannedProjects",
    "unplannedProjects",
    "highValueOpportunities",
)


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
      "body_schema": "[{\"control_type\":\"integer\",\"label\":\"Automation Score\",\"parse_output\":\"integer_conversion\",\"name\":\"automationScore\",\"type\":\"integer\",\"optional\":false},{\"control_type\":\"integer\",\"label\":\"AI Readiness\",\"parse_output\":\"integer_conversion\",\"name\":\"aiReadiness\",\"type\":\"integer\",\"optional\":false},{\"control_type\":\"integer\",\"label\":\"Total Projects\",\"parse_output\":\"integer_conversion\",\"name\":\"totalProjects\",\"type\":\"integer\",\"optional\":false},{\"control_type\":\"integer\",\"label\":\"Completed Projects\",\"parse_output\":\"integer_conversion\",\"name\":\"completedProjects\",\"type\":\"integer\",\"optional\":false},{\"control_type\":\"integer\",\"label\":\"In Progress Projects\",\"parse_output\":\"integer_conversion\",\"name\":\"inProgressProjects\",\"type\":\"integer\",\"optional\":false},{\"control_type\":\"integer\",\"label\":\"Planned Projects\",\"parse_output\":\"integer_conversion\",\"name\":\"plannedProjects\",\"type\":\"integer\",\"optional\":false},{\"control_type\":\"integer\",\"label\":\"Unplanned Projects\",\"parse_output\":\"integer_conversion\",\"name\":\"unplannedProjects\",\"type\":\"integer\",\"optional\":false},{\"control_type\":\"integer\",\"label\":\"High Value Opportunities\",\"parse_output\":\"integer_conversion\",\"name\":\"highValueOpportunities\",\"type\":\"integer\",\"optional\":false}]",
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
   "output_schema": "[{\"name\":\"AUTOMATION_SCORE\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"AUTOMATION SCORE\",\"parse_output\":\"integer_conversion\"},{\"name\":\"AI_READINESS\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"AI READINESS\",\"parse_output\":\"integer_conversion\"},{\"name\":\"TOTAL_PROJECTS\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"TOTAL PROJECTS\",\"parse_output\":\"integer_conversion\"},{\"name\":\"COMPLETED_PROJECTS\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"COMPLETED PROJECTS\",\"parse_output\":\"integer_conversion\"},{\"name\":\"IN_PROGRESS_PROJECTS\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"IN PROGRESS PROJECTS\",\"parse_output\":\"integer_conversion\"},{\"name\":\"PLANNED_PROJECTS\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"PLANNED PROJECTS\",\"parse_output\":\"integer_conversion\"},{\"name\":\"UNPLANNED_PROJECTS\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"UNPLANNED PROJECTS\",\"parse_output\":\"integer_conversion\"},{\"name\":\"HIGH_VALUE_OPPORTUNITIES\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"HIGH VALUE OPPORTUNITIES\",\"parse_output\":\"integer_conversion\"}]",
   "sql": "SELECT \n  CEIL(AVG(COMPLETION_PERCENTAGE)) AS AUTOMATION_SCORE,\n  CEIL(AVG(AI_READINESS_SCORE)) AS AI_READINESS,\n  SUM(CASE WHEN PROCESS_HIERARCHICAL_LEVEL = 4 THEN 1 ELSE 0 END) AS TOTAL_PROJECTS,\n  SUM(CASE WHEN PROCESS_HIERARCHICAL_LEVEL = 4 AND STATUS = 'Completed' THEN 1 ELSE 0 END) AS COMPLETED_PROJECTS,\n  SUM(CASE WHEN PROCESS_HIERARCHICAL_LEVEL = 4 AND STATUS = 'In Progress' THEN 1 ELSE 0 END) AS IN_PROGRESS_PROJECTS,\n  SUM(CASE WHEN PROCESS_HIERARCHICAL_LEVEL = 4 AND STATUS = 'Planned' THEN 1 ELSE 0 END) AS PLANNED_PROJECTS,\n  SUM(CASE WHEN PROCESS_HIERARCHICAL_LEVEL = 4 AND STATUS = 'Unplanned' THEN 1 ELSE 0 END) AS UNPLANNED_PROJECTS,\n  SUM(CASE WHEN PROCESS_HIERARCHICAL_LEVEL = 4 AND AI_IMPACT_LEVEL >= 3 THEN 1 ELSE 0 END) AS HIGH_VALUE_OPPORTUNITIES\n\nFROM AUTOMATION_COMPASS.BUSINESS_PROCESS_DASHBOARD"
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
    "aiReadiness": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"d8a6f6bf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"ai_readiness\"]}')}",
    "automationScore": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"d8a6f6bf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"automation_score\"]}')}",
    "completedProjects": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"d8a6f6bf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"completed_projects\"]}')}",
    "highValueOpportunities": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"d8a6f6bf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"high_value_opportunities\"]}')}",
    "inProgressProjects": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"d8a6f6bf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"in_progress_projects\"]}')}",
    "plannedProjects": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"d8a6f6bf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"planned_projects\"]}')}",
    "totalProjects": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"d8a6f6bf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"total_projects\"]}')}",
    "unplannedProjects": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"d8a6f6bf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"unplanned_projects\"]}')}"
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
OUTCOMES = ("metrics_200", "catch_400")
MAX_ROWS = 20


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


def validate_117566071(raw: dict[str, Any]) -> dict[str, Any]:
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


def _ceil_div(total: int, count: int) -> int:
    return -(-total // count)


def _derived_metrics(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Derive the single aggregate row from seed rows with exact live parity
    (see the CEIL exactness note above)."""
    level4 = [row for row in rows if row["PROCESS_HIERARCHICAL_LEVEL"] == 4]
    return {
        "automationScore": _ceil_div(sum(row["COMPLETION_PERCENTAGE"] for row in rows), len(rows)),
        "aiReadiness": _ceil_div(sum(row["AI_READINESS_SCORE"] for row in rows), len(rows)),
        "totalProjects": len(level4),
        "completedProjects": sum(1 for row in level4 if row["STATUS"] == "Completed"),
        "inProgressProjects": sum(1 for row in level4 if row["STATUS"] == "In Progress"),
        "plannedProjects": sum(1 for row in level4 if row["STATUS"] == "Planned"),
        "unplannedProjects": sum(1 for row in level4 if row["STATUS"] == "Unplanned"),
        "highValueOpportunities": sum(1 for row in level4 if row["AI_IMPACT_LEVEL"] >= 3),
    }


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
            f"recipe {RECIPE_ID} table must declare exactly the columns {EXPECTED_COLUMNS}"
        )
    rows = spec["rows"]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} metrics variants require a NON-EMPTY table (the empty "
            "zero-branch renders all-NULL aggregates and is documented, not pinned)"
        )
    if len(rows) > MAX_ROWS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} at most {MAX_ROWS} rows (keeps the integer-math "
            f"CEIL(AVG(..)) derivation exact against Snowflake's scale-6 AVG)"
        )
    ids: set[str] = set()
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(EXPECTED_COLUMNS.keys()):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} must fill exactly "
                f"{sorted(EXPECTED_COLUMNS.keys())}; got {row!r}"
            )
        for key in (
            "PROCESS_HIERARCHICAL_LEVEL",
            "COMPLETION_PERCENTAGE",
            "AI_READINESS_SCORE",
            "AI_IMPACT_LEVEL",
        ):
            if isinstance(row[key], bool) or not isinstance(row[key], int):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} row {idx} {key} must be an integer (NULLs would "
                    f"silently shrink the AVG denominator): {row!r}"
                )
        if not 0 <= row["COMPLETION_PERCENTAGE"] <= 100 or not 0 <= row["AI_READINESS_SCORE"] <= 100:
            raise RuntimeError(f"recipe {RECIPE_ID} row {idx} percentage columns must be 0..100")
        for key in ("PROCESS_ID", "PROCESS_NAME", "STATUS"):
            if not isinstance(row[key], str) or not row[key].strip():
                raise RuntimeError(f"recipe {RECIPE_ID} row {idx} {key} must be non-empty")
        ids.add(str(row["PROCESS_ID"]))
    if len(ids) != len(rows):
        raise RuntimeError(f"recipe {RECIPE_ID} PROCESS_ID values must be distinct")
    return rows


def _require_expect_shape(expect: Any, force: Any, derived: dict[str, int] | None) -> None:
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
        reason = "catch variants pin 400 {error}, catch_message, 1 action, no snowflake seed"
    else:
        if derived is None:
            raise RuntimeError(f"recipe {RECIPE_ID} metrics variants require a snowflake_live seed")
        zero_keys = sorted(key for key, value in derived.items() if value < 1)
        if zero_keys:
            raise RuntimeError(
                f"recipe {RECIPE_ID} every pinned aggregate must be >= 1 (triage caution: "
                f"no 0/NULL aggregate pins); derived zeros: {zero_keys}"
            )
        checks = (
            expect.get("http_status_code") == "200",
            expect.get("response") == derived,
            expect.get("sql_row_count") == 1,
            expect.get("executed_action_count") == 2,
            expect.get("tools")
            == ["snowflake.search_rows_sql", "workato_api_platform.return_response"],
            "catch_message" not in expect,
        )
        reason = (
            "metrics variants must pin sql_row_count 1 (aggregates always return one "
            f"row) and the EXACT derived 8-scalar object {derived!r}"
        )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with outcome "
            f"{outcome!r} ({reason}): {expect!r}"
        )


def seed_117566071(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_117566071(raw)
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
    else:
        if sorted(seed_in.keys()) != ["snowflake_live"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} metrics variants must seed exactly the "
                f"snowflake_live section; got {sorted(seed_in.keys())}"
            )
        rows = _require_snowflake_section(seed_in["snowflake_live"])
        derived = _derived_metrics(rows)
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


def run_117566071(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_117566071(raw)
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
    result["verifier"] = verify_117566071(result)
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
