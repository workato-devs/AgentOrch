from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_118162481


RECIPE_ID = "118162481"
SEED_TYPE = "api_platform_automation_compass_trend_data_variant"
TRACK = "workato_api_platform_snowflake_automation_compass"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "751ec271"
SEARCH_STEP_AS = "d8a6f6bf"
SUCCESS_RETURN_AS = "83954e0e"
CATCH_AS = "2da14745"
CATCH_RETURN_AS = "57671952"
STOP_STEP_AS = "8ce124ba"
METRICS_TABLE = "AUTOMATION_COMPASS.HISTORICAL_METRICS"
RAW_SQL = (
    "SELECT \n  MONTHNAME(MONTH_DATE) AS MONTH,\n"
    "  AUTOMATION_SCORE AS AUTOMATION_SCORE,\n"
    "  AI_READINESS_SCORE AS AI_READINESS  \n"
    "FROM AUTOMATION_COMPASS.HISTORICAL_METRICS\n\nORDER BY MONTH"
)
RAW_LIMIT = "6"
EXPECTED_COLUMNS = {
    "MONTH_DATE": "date",
    "AUTOMATION_SCORE": "number",
    "AI_READINESS_SCORE": "number",
}
MONTH_ABBREVIATIONS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
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
      "body_schema": "[{\"name\":\"trendData\",\"type\":\"array\",\"optional\":false,\"label\":\"Trend Data\",\"properties\":[{\"name\":\"month\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Month\"},{\"name\":\"automationScore\",\"type\":\"integer\",\"optional\":false,\"label\":\"Automation Score\",\"control_type\":\"integer\",\"parse_output\":\"integer_conversion\"},{\"name\":\"aiReadiness\",\"type\":\"integer\",\"optional\":false,\"label\":\"AI Readiness\",\"control_type\":\"integer\",\"parse_output\":\"integer_conversion\"}],\"of\":\"object\"}]",
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
   "limit": "6",
   "output_schema": "[{\"control_type\":\"text\",\"label\":\"MONTH\",\"name\":\"MONTH\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"integer\",\"label\":\"AUTOMATION SCORE\",\"parse_output\":\"integer_conversion\",\"name\":\"AUTOMATION_SCORE\",\"type\":\"integer\",\"optional\":false},{\"control_type\":\"integer\",\"label\":\"AI READINESS\",\"parse_output\":\"integer_conversion\",\"name\":\"AI_READINESS\",\"type\":\"integer\",\"optional\":false}]",
   "sql": "SELECT \n  MONTHNAME(MONTH_DATE) AS MONTH,\n  AUTOMATION_SCORE AS AUTOMATION_SCORE,\n  AI_READINESS_SCORE AS AI_READINESS  \nFROM AUTOMATION_COMPASS.HISTORICAL_METRICS\n\nORDER BY MONTH"
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
    "trendData": {
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"d8a6f6bf\",\"path\":[\"rows\"]}')}",
     "aiReadiness": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"d8a6f6bf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"ai_readiness\"]}')}",
     "automationScore": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"d8a6f6bf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"automation_score\"]}')}",
     "month": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"d8a6f6bf\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"month\"]}')}"
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
    "seeded_row_count",
)
OPTIONAL_EXPECT_KEYS = {"catch_message"}
OUTCOMES = ("trend_200", "empty_trend_200", "catch_400")


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


def validate_118162481(raw: dict[str, Any]) -> dict[str, Any]:
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
        "snowflake_table": METRICS_TABLE,
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


def _month_abbreviation(month_date: str) -> str:
    return MONTH_ABBREVIATIONS[int(str(month_date)[5:7]) - 1]


def _derived_trend(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Derive the live query result from seed rows: MONTHNAME() 3-letter
    abbreviation, ORDER BY MONTH = ALPHABETICAL string sort, engine-appended
    limit 6 truncation. Scores stay native ints."""
    items = [
        {
            "month": _month_abbreviation(row["MONTH_DATE"]),
            "automationScore": row["AUTOMATION_SCORE"],
            "aiReadiness": row["AI_READINESS_SCORE"],
        }
        for row in rows
    ]
    items.sort(key=lambda item: item["month"])
    return items[:6]


def _require_snowflake_section(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the SQL uses no CURRENT_DATE/TIMESTAMP, so current_time is not allowed)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [METRICS_TABLE]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{METRICS_TABLE!r} (the literal 2-part SQL name)"
        )
    spec = tables[METRICS_TABLE]
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table spec must be exactly {{'columns': ..., 'rows': ...}}"
        )
    if spec["columns"] != EXPECTED_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table must declare exactly the columns {EXPECTED_COLUMNS} "
            "(MONTH_DATE as DATE keeps MONTHNAME() well-defined; scores as NUMBER keep "
            "the response pills native ints)"
        )
    rows = spec["rows"]
    if not isinstance(rows, list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} table rows must be a list (empty ONLY for the "
            "empty_trend_200 branch)"
        )
    months: list[str] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(EXPECTED_COLUMNS.keys()):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} must fill exactly "
                f"{sorted(EXPECTED_COLUMNS.keys())}; got {row!r}"
            )
        month_date = str(row["MONTH_DATE"])
        if len(month_date) != 10 or month_date[4] != "-" or month_date[7] != "-" or not (
            month_date[:4].isdigit() and month_date[5:7].isdigit() and month_date[8:].isdigit()
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} row {idx} MONTH_DATE must be a YYYY-MM-DD literal: {row!r}"
            )
        if not 1 <= int(month_date[5:7]) <= 12:
            raise RuntimeError(f"recipe {RECIPE_ID} row {idx} MONTH_DATE month out of range")
        for key in ("AUTOMATION_SCORE", "AI_READINESS_SCORE"):
            if isinstance(row[key], bool) or not isinstance(row[key], int):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} row {idx} {key} must be an integer (NUMBER column)"
                )
        months.append(_month_abbreviation(month_date))
    if len(set(months)) != len(months):
        raise RuntimeError(
            f"recipe {RECIPE_ID} month names must be DISTINCT (equal MONTH values tie "
            f"under ORDER BY MONTH and their order is not deterministic): {months}"
        )
    return rows


def _require_quirk_proof(rows: list[dict[str, Any]], derived: list[dict[str, Any]]) -> None:
    """trend_200 variants must prove alphabetical != chronological: the pinned
    month order has to differ from the same months sorted by MONTH_DATE."""
    if len(rows) < 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trend_200 requires >= 2 rows so the alphabetical "
            "ORDER BY MONTH quirk is provable"
        )
    chronological = [
        _month_abbreviation(row["MONTH_DATE"])
        for row in sorted(rows, key=lambda row: str(row["MONTH_DATE"]))
    ][: len(derived)]
    pinned = [item["month"] for item in derived]
    if pinned == chronological:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the alphabetical order coincides with chronological "
            f"order — pick months that PROVE the quirk: {pinned}"
        )


def _require_expect_shape(
    expect: Any,
    force: Any,
    rows: list[dict[str, Any]] | None,
    derived: list[dict[str, Any]] | None,
) -> None:
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
            expect.get("seeded_row_count") is None,
            expect.get("executed_action_count") == 1,
            expect.get("tools") == ["workato_api_platform.return_response"],
        )
        reason = "catch variants pin 400 {error}, catch_message, 1 action, no snowflake seed"
    else:
        if rows is None or derived is None:
            raise RuntimeError(f"recipe {RECIPE_ID} try variants require a snowflake_live seed")
        if outcome == "trend_200" and not derived:
            raise RuntimeError(f"recipe {RECIPE_ID} trend_200 requires seeded month rows")
        if outcome == "empty_trend_200" and rows:
            raise RuntimeError(
                f"recipe {RECIPE_ID} empty_trend_200 requires an EMPTY seeded table"
            )
        checks = (
            expect.get("http_status_code") == "200",
            expect.get("response") == {"trendData": derived},
            expect.get("sql_row_count") == len(derived),
            expect.get("seeded_row_count") == len(rows),
            len(derived) == min(len(rows), 6),
            expect.get("executed_action_count") == 2,
            expect.get("tools")
            == ["snowflake.search_rows_sql", "workato_api_platform.return_response"],
            "catch_message" not in expect,
        )
        reason = (
            "try variants must pin the EXACT derived trendData (alphabetical MONTHNAME "
            f"order, limit-6 truncation): {{'trendData': {derived!r}}}"
        )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with outcome "
            f"{outcome!r} ({reason}): {expect!r}"
        )


def seed_118162481(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118162481(raw)
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
        rows = None
        derived = None
    else:
        if sorted(seed_in.keys()) != ["snowflake_live"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} try variants must seed exactly the snowflake_live "
                f"section; got {sorted(seed_in.keys())}"
            )
        rows = _require_snowflake_section(seed_in["snowflake_live"])
        derived = _derived_trend(rows)
        if rows:
            _require_quirk_proof(rows, derived)
    _require_expect_shape(data.get("expect"), force, rows, derived)
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


def run_118162481(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118162481(raw)
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
            # Required cleanup: the shared AUTOMATION_COMPASS metrics table is
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
    result["verifier"] = verify_118162481(result)
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
