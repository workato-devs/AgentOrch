from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_111073966


RECIPE_ID = "111073966"
SEED_TYPE = "recipe_function_netsuite_internal_id_lookup_variant"
TRACK = "workato_recipe_function_netsuite_internal_id_lookup"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "982dea24"
DB_TABLE_ID = "1831"
DB_FILTER_FIELD = "6152ba93_dcfb_40b5_ba46_b960344834d6"
DB_INTERNAL_ID_FIELD = "497983d1_6ba0_4c82_bf3f_92408f1b1ce3"
PAYMENT_TERM_TABLE = "NETSUITE.PAYMENT_TERM"
CURRENCY_TABLE = "NETSUITE.CURRENCY"
SUBSIDIARY_TABLE = "NETSUITE.SUBSIDIARY"
SNOWFLAKE_TABLES = (PAYMENT_TERM_TABLE, CURRENCY_TABLE, SUBSIDIARY_TABLE)
REQUIRED_PARAMS = ("billing_frequency", "payment_terms", "currency_code", "subsidiary_name")
OPTIONAL_PARAMS = ("salesforce_contract_id", "salesforce_order_id")
STOP_STEPS = (4, 7, 10, 13)


_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "982dea24",
  "provider": "workato_recipe_function",
  "name": "execute",
  "skip": false,
  "input": {
   "parameters_schema_json": "[{\"control_type\":\"text\",\"label\":\"Billing Frequency\",\"name\":\"billing_frequency\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Payment Terms\",\"name\":\"payment_terms\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Currency Code\",\"name\":\"currency_code\",\"type\":\"string\",\"optional\":true,\"hint\":\"currency alpha-3 code e.g. USD, EUR\"},{\"control_type\":\"text\",\"label\":\"Subsidiary Name\",\"name\":\"subsidiary_name\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Salesforce contract ID\",\"name\":\"salesforce_contract_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Salesforce order ID\",\"name\":\"salesforce_order_id\",\"type\":\"string\",\"optional\":true}]",
   "result_schema_json": "[{\"control_type\":\"integer\",\"label\":\"Charge schedule ID\",\"parse_output\":\"integer_conversion\",\"name\":\"charge_schedule_id\",\"type\":\"integer\",\"optional\":true},{\"control_type\":\"integer\",\"label\":\"Payment terms ID\",\"parse_output\":\"integer_conversion\",\"name\":\"payment_terms_id\",\"type\":\"integer\",\"optional\":true},{\"control_type\":\"integer\",\"label\":\"Currency Code ID\",\"parse_output\":\"integer_conversion\",\"name\":\"currency_code_id\",\"type\":\"integer\",\"optional\":true},{\"control_type\":\"integer\",\"label\":\"Subsidiary ID\",\"parse_output\":\"integer_conversion\",\"name\":\"subsidiary_id\",\"type\":\"integer\",\"optional\":true}]"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "fc9202cd",
  "provider": "workato_db_table",
  "name": "get_records",
  "skip": false,
  "input": {
   "04d84fee-0c3b-4b14-aee9-95730e7dcc2c": "string",
   "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id",
   "2e3560c9-6c1f-48f2-8b29-512611e26866": "string",
   "2e51a398-c781-4c8f-83f4-90ec1f46ab74": "string",
   "497983d1-6ba0-4c82-bf3f-92408f1b1ce3": "string",
   "4f328314-5315-4c9a-926e-24d2b606f910": "integer",
   "6152ba93-dcfb-40b5-ba46-b960344834d6": "string",
   "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time",
   "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time",
   "de94b173-cae2-4062-a0ea-89285db0f8ba": "integer",
   "filters": [
    {
     "field_id": "6152ba93-dcfb-40b5-ba46-b960344834d6",
     "op_default": "eq",
     "value_default": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"982dea24\",\"path\":[\"parameters\", \"billing_frequency\"]}')}"
    }
   ],
   "limit": "100",
   "order_direction": "asc",
   "table_id": "1831"
  }
 },
 {
  "keyword": "if",
  "number": 3,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"fc9202cd\",\"path\":[\"records\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "not_equals_to",
     "rhs": "1"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "stop",
  "number": 4,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "stop_reason": "Unable to identify Internal ID for Charge Schedule: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"982dea24\",\"path\":[\"parameters\", \"billing_frequency\"]}')}",
   "stop_with_error": "true"
  }
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "3867bf58",
  "provider": "snowflake",
  "name": "search_rows",
  "skip": false,
  "input": {
   "limit": "1",
   "offset": "0",
   "output_columns": "INTERNAL_ID\nDESCRIPTION\nINACTIVE",
   "parameters": {
    "data": {
     "inactive": "false",
     "payment_terms": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"982dea24\",\"path\":[\"parameters\", \"payment_terms\"]}')}"
    },
    "schema": "[{\"control_type\":\"text\",\"label\":\"Payment Terms\",\"name\":\"payment_terms\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"checkbox\",\"label\":\"Inactive\",\"render_input\":{},\"parse_output\":{},\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Inactive\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"inactive\",\"type\":\"boolean\",\"optional\":true},\"name\":\"inactive\",\"type\":\"boolean\",\"optional\":true}]"
   },
   "table": "NETSUITE.PAYMENT_TERM",
   "where": "DESCRIPTION = :payment_terms AND INACTIVE = :inactive"
  }
 },
 {
  "keyword": "if",
  "number": 6,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"3867bf58\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "not_equals_to",
     "rhs": "1"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "stop",
  "number": 7,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "stop_reason": "Unable to identify Internal ID for Payment Terms: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"982dea24\",\"path\":[\"parameters\", \"payment_terms\"]}')}",
   "stop_with_error": "true"
  }
 },
 {
  "keyword": "action",
  "number": 8,
  "as": "5a519601",
  "provider": "snowflake",
  "name": "search_rows",
  "skip": false,
  "input": {
   "limit": "1",
   "offset": "0",
   "output_columns": "INTERNAL_ID\nNAME\nISO_CODE\nINACTIVE",
   "parameters": {
    "data": {
     "inactive": "false",
     "iso_code": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"982dea24\",\"path\":[\"parameters\", \"currency_code\"]}')}"
    },
    "schema": "[{\"control_type\":\"text\",\"label\":\"ISO Code\",\"name\":\"iso_code\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"checkbox\",\"label\":\"Inactive\",\"render_input\":{},\"parse_output\":{},\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Inactive\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"inactive\",\"type\":\"boolean\",\"optional\":true},\"name\":\"inactive\",\"type\":\"boolean\",\"optional\":true}]"
   },
   "table": "NETSUITE.CURRENCY",
   "where": "ISO_CODE = :iso_code AND INACTIVE = :inactive"
  }
 },
 {
  "keyword": "if",
  "number": 9,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a519601\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "not_equals_to",
     "rhs": "1"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "stop",
  "number": 10,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "stop_reason": "Unable to identify Internal ID for Currency Code: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"982dea24\",\"path\":[\"parameters\", \"currency_code\"]}')}",
   "stop_with_error": "true"
  }
 },
 {
  "keyword": "action",
  "number": 11,
  "as": "3a531525",
  "provider": "snowflake",
  "name": "search_rows",
  "skip": false,
  "input": {
   "limit": "1",
   "offset": "0",
   "output_columns": "NAME\nISINACTIVE\nINTERNAL_ID",
   "parameters": {
    "data": {
     "inactive": "false",
     "subsidiary_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"982dea24\",\"path\":[\"parameters\", \"subsidiary_name\"]}')}"
    },
    "schema": "[{\"control_type\":\"text\",\"label\":\"Subsidiary Name\",\"name\":\"subsidiary_name\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"checkbox\",\"label\":\"Inactive\",\"render_input\":{},\"parse_output\":{},\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Inactive\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"inactive\",\"type\":\"boolean\",\"optional\":true},\"name\":\"inactive\",\"type\":\"boolean\",\"optional\":true}]"
   },
   "table": "NETSUITE.SUBSIDIARY",
   "where": "NAME = :subsidiary_name AND ISINACTIVE = :inactive"
  }
 },
 {
  "keyword": "if",
  "number": 12,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"3a531525\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "not_equals_to",
     "rhs": "1"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "stop",
  "number": 13,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "stop_reason": "Unable to identify Internal ID for Subsidiary: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"982dea24\",\"path\":[\"parameters\", \"subsidiary_name\"]}')}",
   "stop_with_error": "true"
  }
 },
 {
  "keyword": "action",
  "number": 14,
  "as": "32209795",
  "provider": "workato_recipe_function",
  "name": "return_result",
  "skip": false,
  "input": {
   "result": {
    "charge_schedule_id": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"fc9202cd\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"497983d1_6ba0_4c82_bf3f_92408f1b1ce3\"]}').presence or nil",
    "currency_code_id": "=_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a519601\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"internal_id\"]}').presence or nil",
    "payment_terms_id": "=_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"3867bf58\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"internal_id\"]}').presence or nil",
    "subsidiary_id": "=_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"3a531525\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"internal_id\"]}').presence or nil"
   }
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "snowflake.search_rows",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "snowflake.search_rows",
    "workato_recipe_function.return_result",
]
EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "stopped",
)
OPTIONAL_EXPECT_KEYS = {"stop_step_number", "result"}


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


def validate_111073966(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_111073966(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_111073966(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"workato_db_table", "snowflake_live"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    expect = data.get("expect")
    _require_expect_shape(expect)
    _require_db_section(seed_in.get("workato_db_table"))
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
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_111073966(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_111073966(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
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
        # Live Snowflake tables are benchmark-owned create-or-replace state:
        # drop them even when execution fails (cleanup principle). The mock
        # db table needs no cleanup (per-variant seed fully overwrites it).
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
    result["verifier"] = verify_111073966(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {"parameters"} or not isinstance(trigger.get("parameters"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input must be exactly {{'parameters': {{...}}}}")
    parameters = trigger["parameters"]
    extra = sorted(set(parameters) - set(REQUIRED_PARAMS) - set(OPTIONAL_PARAMS))
    if extra:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters has undeclared fields: {extra}")
    for key in REQUIRED_PARAMS:
        if not isinstance(parameters.get(key), str) or not parameters[key].strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger parameter {key!r} must be a non-empty string "
                "(every gate dereferences it)"
            )


def _require_expect_shape(expect: Any) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(EXPECT_KEYS) - OPTIONAL_EXPECT_KEYS)
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if expect.get("stopped"):
        if expect.get("stop_step_number") not in STOP_STEPS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} stopped variants must pin stop_step_number in {STOP_STEPS}"
            )
        if "result" in expect:
            raise RuntimeError(f"recipe {RECIPE_ID} stopped variants must not declare expect.result")
    else:
        if not isinstance(expect.get("result"), dict):
            raise RuntimeError(
                f"recipe {RECIPE_ID} non-stop variants must pin expect.result (the 4 returned ids)"
            )
        if "stop_step_number" in expect:
            raise RuntimeError(
                f"recipe {RECIPE_ID} non-stop variants must not declare stop_step_number"
            )


def _require_db_section(section: Any) -> None:
    if not isinstance(section, dict) or not isinstance(section.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.workato_db_table.tables")
    if sorted(section["tables"]) != [DB_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table.tables must declare exactly table {DB_TABLE_ID}"
        )
    if "continuation_tokens" in section:
        raise RuntimeError(f"recipe {RECIPE_ID} must not seed continuation_tokens (single-page read)")
    rows = section["tables"][DB_TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {DB_TABLE_ID} must be a non-empty explicit list "
            "(missing-match variants seed non-matching decoy rows, never an empty table)"
        )
    for row in rows:
        if not isinstance(row, dict) or not str(row.get(DB_FILTER_FIELD) or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded 1831 row needs a non-empty "
                f"{DB_FILTER_FIELD} (the billing-frequency filter key): {row!r}"
            )
        if not str(row.get(DB_INTERNAL_ID_FIELD) or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded 1831 row needs a non-empty "
                f"{DB_INTERNAL_ID_FIELD} (the returned Internal ID): {row!r}"
            )


def _require_snowflake_section(section: Any) -> None:
    if not isinstance(section, dict) or not isinstance(section.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.snowflake_live.tables")
    if sorted(section["tables"]) != sorted(SNOWFLAKE_TABLES):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{sorted(SNOWFLAKE_TABLES)} (uniform provisioning across variants)"
        )
    for table in SNOWFLAKE_TABLES:
        spec = section["tables"][table]
        if not isinstance(spec, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} snowflake table {table} spec must be an object")
        columns = spec.get("columns")
        if not isinstance(columns, dict) or not columns or not all(
            isinstance(kind, str) and kind.strip() for kind in columns.values()
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} snowflake table {table} must declare explicit column types"
            )
        rows = spec.get("rows")
        if not isinstance(rows, list) or not rows:
            raise RuntimeError(
                f"recipe {RECIPE_ID} snowflake table {table} must declare a non-empty rows list "
                "(missing-match variants seed decoys, never an empty table)"
            )
        declared = {str(name) for name in columns}
        for row in rows:
            if not isinstance(row, dict):
                raise RuntimeError(f"recipe {RECIPE_ID} snowflake table {table} rows must be objects")
            extra = {str(key) for key in row} - declared
            if extra:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} snowflake table {table} row uses undeclared columns: "
                    f"{sorted(extra)}"
                )


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    out: dict[str, Any] = {}
    out.update(ctx.tools.call("harness.snowflake.snapshot", {}))
    out.update(ctx.tools.call("harness.workato_db_table.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
