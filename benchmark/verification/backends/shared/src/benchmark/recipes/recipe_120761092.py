from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_120761092


RECIPE_ID = "120761092"
SEED_TYPE = "api_platform_walnutiq_companies_list_variant"
TRACK = "workato_api_platform_walnutiq_companies_list"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "7e04a37a"
COMPANIES_TABLE = "walnutiq.companies"
SQL_STEP_AS = "24986ee3"
SUCCESS_RETURN_AS = "1801d6d0"
STOP_STEP_AS = "fc3279e9"
CATCH_AS = "c7cc2a1d"
CATCH_RETURN_AS = "618a4cc1"
RAW_SQL = (
    "SELECT id, company_name, zoominfo_id, updated_at FROM walnutiq.companies "
    "ORDER BY updated_at DESC "
)


_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "7e04a37a",
  "provider": "workato_api_platform",
  "name": "receive_request",
  "skip": false,
  "input": {
   "request": {
    "content_type": "json"
   },
   "response": {
    "content_type": "json",
    "responses": [
     {
      "body_schema": "[{\"name\":\"results\",\"type\":\"array\",\"of\":\"object\",\"label\":\"Results\",\"optional\":false,\"properties\":[{\"control_type\":\"number\",\"label\":\"ID\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"id\"},{\"control_type\":\"text\",\"label\":\"Company name\",\"type\":\"string\",\"name\":\"company_name\"},{\"control_type\":\"number\",\"label\":\"Zoominfo ID\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"zoominfo_id\"},{\"control_type\":\"text\",\"label\":\"Updated at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"type\":\"date_time\",\"name\":\"updated_at\"}]}]",
      "http_status_code": "200",
      "name": "Success"
     },
     {
      "body_schema": "[{\"name\":\"message\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Message\"}]",
      "http_status_code": "500",
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
  "as": "24986ee3",
  "provider": "snowflake",
  "name": "run_custom_sql",
  "skip": false,
  "input": {
   "output_schema": "[{\"control_type\":\"number\",\"label\":\"ID\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"id\"},{\"control_type\":\"text\",\"label\":\"Company name\",\"type\":\"string\",\"name\":\"company_name\"},{\"control_type\":\"number\",\"label\":\"Zoominfo ID\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"zoominfo_id\"},{\"control_type\":\"text\",\"label\":\"Updated at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"type\":\"date_time\",\"name\":\"updated_at\"}]",
   "sql": "SELECT id, company_name, zoominfo_id, updated_at FROM walnutiq.companies ORDER BY updated_at DESC ",
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
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"24986ee3\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}",
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
  "as": "1801d6d0",
  "provider": "workato_api_platform",
  "name": "return_response",
  "skip": false,
  "input": {
   "http_status_code": "200",
   "response": {
    "results": {
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"24986ee3\",\"path\":[\"rows\"]}')}",
     "company_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"24986ee3\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"company_name\"]}')}",
     "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"24986ee3\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}",
     "updated_at": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"24986ee3\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"updated_at\"]}')}",
     "zoominfo_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"24986ee3\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"zoominfo_id\"]}')}"
    }
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
  "keyword": "stop",
  "number": 7,
  "as": "fc3279e9",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "stop_reason": "No results found",
   "stop_with_error": "true"
  }
 },
 {
  "keyword": "catch",
  "number": 8,
  "as": "c7cc2a1d",
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
  "as": "618a4cc1",
  "provider": "workato_api_platform",
  "name": "return_response",
  "skip": false,
  "input": {
   "http_status_code": "500",
   "response": {
    "message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"c7cc2a1d\",\"path\":[\"message\"]}')}"
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
    "outcome",
    "http_status_code",
    "response",
    "return_step_as",
    "stopped",
)
OPTIONAL_EXPECT_KEYS = {"catch_message"}
OUTCOMES = ("results_200", "stop_no_results", "catch_500")
EXPECTED_COLUMNS = {
    "ID": "number",
    "COMPANY_NAME": "string",
    "ZOOMINFO_ID": "number",
    "UPDATED_AT": "timestamp",
}
_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


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


def validate_120761092(raw: dict[str, Any]) -> dict[str, Any]:
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


def _require_expect_shape(expect: Any, force: Any, row_count: int) -> None:
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
    if (outcome == "catch_500") != (force is not None):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the catch outcome and force_action_error must be declared "
            "together (the static SQL has no other deterministic failure)"
        )
    if outcome == "results_200":
        if row_count < 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} results_200 requires at least one seeded company row"
            )
        checks = (
            expect.get("http_status_code") == "200",
            expect.get("return_step_as") == SUCCESS_RETURN_AS,
            isinstance(expect.get("response"), dict),
            len((expect.get("response") or {}).get("results") or []) == row_count,
            expect.get("stopped") is False,
            expect.get("executed_action_count") == 2,
            "catch_message" not in expect,
        )
    elif outcome == "stop_no_results":
        if row_count != 0:
            raise RuntimeError(
                f"recipe {RECIPE_ID} stop_no_results requires an EMPTY seeded table"
            )
        checks = (
            expect.get("http_status_code") is None,
            expect.get("return_step_as") is None,
            expect.get("response") is None,
            expect.get("stopped") is True,
            expect.get("executed_action_count") == 1,
            "catch_message" not in expect,
        )
    else:  # catch_500
        checks = (
            expect.get("http_status_code") == "500",
            expect.get("return_step_as") == CATCH_RETURN_AS,
            expect.get("response") == {"message": force.get("error")},
            expect.get("stopped") is False,
            expect.get("executed_action_count") == 1,
            expect.get("catch_message") == force.get("error"),
        )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with outcome {outcome!r}: {expect!r}"
        )


def _require_snowflake_section(section: Any) -> int:
    if not isinstance(section, dict) or not isinstance(section.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.snowflake_live.tables")
    if sorted(section["tables"]) != [COMPANIES_TABLE]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{COMPANIES_TABLE!r}"
        )
    spec = section["tables"][COMPANIES_TABLE]
    if not isinstance(spec, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} snowflake table spec must be an object")
    if spec.get("columns") != EXPECTED_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} walnutiq.companies columns must be exactly "
            f"{EXPECTED_COLUMNS} (TIMESTAMP -> TIMESTAMP_NTZ keeps the updated_at "
            f"isoformat rendering stable)"
        )
    rows = spec.get("rows")
    if not isinstance(rows, list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} walnutiq.companies rows must be a list (empty ONLY for "
            "the stop_no_results branch)"
        )
    for row in rows:
        if not isinstance(row, dict) or set(row) != set(EXPECTED_COLUMNS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} every walnutiq.companies row must fill all declared "
                f"columns: {row!r}"
            )
        for key in ("ID", "ZOOMINFO_ID"):
            if isinstance(row[key], bool) or not isinstance(row[key], int):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {key} must be an integer (NUMBER column): {row!r}"
                )
        if not _TIMESTAMP_RE.match(str(row["UPDATED_AT"])):
            raise RuntimeError(
                f"recipe {RECIPE_ID} UPDATED_AT must be a 'YYYY-MM-DD HH:MM:SS' literal "
                f"(stable isoformat read-back): {row!r}"
            )
    if len({row["UPDATED_AT"] for row in rows}) != len(rows):
        raise RuntimeError(
            f"recipe {RECIPE_ID} UPDATED_AT values must be distinct (the ORDER BY "
            "updated_at DESC groundtruth must be deterministic)"
        )
    return len(rows)


def seed_120761092(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_120761092(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (no request field is "
            f"ever dereferenced): {trigger!r}"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"snowflake_live"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    row_count = _require_snowflake_section(seed_in.get("snowflake_live"))
    force = data.get("force_action_error")
    _require_force_shape(force)
    _require_expect_shape(data.get("expect"), force, row_count)
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
        "expect": deepcopy(data["expect"]),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_120761092(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_120761092(raw)
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
        # walnutiq.companies is benchmark-owned create-or-replace live state:
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
    result["verifier"] = verify_120761092(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


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
