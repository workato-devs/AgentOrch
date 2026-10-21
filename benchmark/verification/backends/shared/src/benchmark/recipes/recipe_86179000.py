from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_86179000


RECIPE_ID = "86179000"
SEED_TYPE = "recipe_function_snowflake_history_schema_sync_variant"
TRACK = "live_snowflake_recipe_function_history_schema_sync"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "ab4ebba5"

# Callable recipe function (trigger ab4ebba5): keeps a Snowflake history table's
# schema in sync with its base table. Whole body wrapped in TRY (step 2):
#   3  declare_variable (2631f665): base/history database, schema and table
#      names, all six copied verbatim from trigger parameters
#   4  snowflake.run_custom_sql (c97a2c66): DESCRIBE TABLE <base db>.<base
#      schema>.<base table> -- LIVE DDL introspection through the custom-SQL
#      path (no statement whitelist; probe-verified DESCRIBE runs live and
#      returns lowercase 'name'/'type' columns)
#   5  update_variables (051a3e1d): table_header = rows.pluck('name')
#      .join(",").upcase.split(",")  (computed but never consumed downstream;
#      must still execute for trace parity)
#   6  snowflake.run_custom_sql (bec1a644): WITH HISTORY_TABLE_HEADER/
#      BASE_TABLE_HEADER CTEs over INFORMATION_SCHEMA.COLUMNS, SELECT
#      COLUMN_NAME FROM base EXCEPT history -- the new-column set
#   7  IF bec1a644 rows.size > 0:
#      8   logger (e0ee7862): rows.format_map("'%{column_name}'").join(', ')
#          (quote-wrapped placeholder chain -- the batch-02 engine gap, now
#          fixed and probe-verified)
#      9   snowflake.run_custom_sql (e5b3b4e2): COLUMN_NAME, DATA_TYPE FROM
#          INFORMATION_SCHEMA.COLUMNS WHERE ... COLUMN_NAME IN (<logger msg>)
#      10  update_variables (8d8ed948): sql_script_for_adding_fields =
#          rows.format_map('%{column_name} %{data_type}').join(', ')
#      11  snowflake.run_custom_sql (bbfd0d45): ALTER TABLE <history db>.
#          <history schema>.<history table> ADD <sql_script> -- LIVE ALTER
#          (probe-verified: ALTER TABLE ... ADD col TEXT runs live and the
#          column appears in the table)
#   12 return_result (da6b3bcb): {is_successful: "true", fields_added:
#      e5b3b4e2 rows.size} -- when step 9 never ran (IF false) the size pill
#      resolves MISSING -> null (Workato-faithful nil)
#   CATCH (step 13, as 1ae64ff0, max_retry_count 0):
#   14 return_result (2abe3ee4): {is_successful: "false", fields_added: "0",
#      error_message: catch message}
#
# DETERMINISM CONSTRAINT (probe-verified live): the EXCEPT result set and the
# COLUMN_NAME IN (...) result set are UNORDERED -- two extra base columns came
# back in a different order on consecutive runs. Every ALTER-branch variant
# must therefore add exactly ONE column so the logger message, the IN-list SQL,
# sql_script_for_adding_fields and the ALTER statement are order-independent
# and can be pinned exactly.
#
# SEEDING CONSTRAINT: snowflake_live table keys must be the fully-qualified
# 3-part <database>.<schema>.<table> names EXACTLY as the recipe interpolates
# them (params are uppercase), because SnowflakeLiveClient._rewrite_sql
# replaces the registered key text inside the SQL; a 2-part key would corrupt
# "DESCRIBE TABLE <db>.<key>" into "<db>.<quoted 3-part name>". The params
# database must equal env SNOWFLAKE_DATABASE (the harness forces every
# qualified name into that database and INFORMATION_SCHEMA is resolved there);
# seed_86179000 fails fast on any mismatch.
#
# Catch variant: params name a base table that is never seeded; the live
# DESCRIBE fails with the deterministic Snowflake compilation error (probed
# verbatim: "002003 (42S02): SQL compilation error:\nTable '<name>' does not
# exist or not authorized.") and the catch branch returns it.
#
# Cleanup: seeded tables are create-or-replace'd by every seed and dropped by
# harness.snowflake_live.cleanup in finally (the ALTER mutates the history
# table, so cleanup is a rerun-safety requirement, not cosmetics).

_STRUCTURE_PINS_JSON = r'''
[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "ab4ebba5",
  "provider": "workato_recipe_function",
  "name": "execute",
  "skip": false,
  "input": {
   "parameters_schema_json": "[{\"control_type\":\"text\",\"label\":\"Base Table Database\",\"name\":\"base_table_database\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Base Table Schema\",\"name\":\"base_table_schema\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Base Table\",\"name\":\"base_table\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"History table database\",\"name\":\"history_table_database\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"History table schema\",\"name\":\"history_table_schema\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"History table\",\"name\":\"history_table\",\"type\":\"string\",\"optional\":false}]",
   "result_schema_json": "[{\"name\":\"is_successful\",\"type\":\"boolean\",\"optional\":false,\"control_type\":\"checkbox\",\"label\":\"Is successful\",\"render_input\":{},\"parse_output\":{},\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Is successful\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"is_successful\",\"type\":\"boolean\",\"optional\":false}},{\"name\":\"fields_added\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"Fields added\",\"parse_output\":\"integer_conversion\"},{\"name\":\"error_message\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Error message\"}]"
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
  "as": "2631f665",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "base_Table": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"ab4ebba5\",\"path\":[\"parameters\", \"base_table\"]}')}",
     "base_table_database": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"ab4ebba5\",\"path\":[\"parameters\", \"base_table_database\"]}')}",
     "base_table_schema": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"ab4ebba5\",\"path\":[\"parameters\", \"base_table_schema\"]}')}",
     "history_table": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"ab4ebba5\",\"path\":[\"parameters\", \"history_table\"]}')}",
     "history_table_database": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"ab4ebba5\",\"path\":[\"parameters\", \"history_table_database\"]}')}",
     "history_table_schema": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"ab4ebba5\",\"path\":[\"parameters\", \"history_table_schema\"]}')}"
    },
    "schema": "[{\"control_type\":\"text\",\"label\":\"Base Table Database\",\"name\":\"base_table_database\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"Base Table Database\"}},{\"control_type\":\"text\",\"label\":\"Base Table Schema\",\"name\":\"base_table_schema\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"Base Table Schema\"}},{\"control_type\":\"text\",\"label\":\"Base Table\",\"name\":\"base_Table\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"Base Table\"}},{\"control_type\":\"text\",\"label\":\"Table Header\",\"name\":\"table_header\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"Base Table Header\"}},{\"control_type\":\"text\",\"label\":\"SQL Script for Adding Fields\",\"name\":\"sql_script_for_adding_fields\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"SQL Script for Adding Fields\"}},{\"control_type\":\"text\",\"label\":\"History Table Database\",\"name\":\"history_table_database\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"History Table Database\"}},{\"control_type\":\"text\",\"label\":\"History Table Schema\",\"name\":\"history_table_schema\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"History Table Schema\"}},{\"control_type\":\"text\",\"label\":\"History Table\",\"name\":\"history_table\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"History Table\"}}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "c97a2c66",
  "provider": "snowflake",
  "name": "run_custom_sql",
  "skip": false,
  "input": {
   "output_schema": "[{\"name\":\"name\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Name\"}]",
   "sql": "DESCRIBE TABLE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2631f665\",\"path\":[\"base_table_database\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2631f665\",\"path\":[\"base_table_schema\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2631f665\",\"path\":[\"base_Table\"]}')}",
   "update_only": "false"
  }
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "051a3e1d",
  "provider": "workato_variable",
  "name": "update_variables",
  "skip": false,
  "input": {
   "name": "aa56d1bf-2b3a-43e5-966b-a369022ddfc1:2631f665:table_header",
   "table_header": "=_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"c97a2c66\",\"path\":[\"rows\"]}').pluck('name').join(\",\").upcase.split(\",\")"
  }
 },
 {
  "keyword": "action",
  "number": 6,
  "as": "bec1a644",
  "provider": "snowflake",
  "name": "run_custom_sql",
  "skip": false,
  "input": {
   "output_schema": "[{\"name\":\"column_name\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Column name\"}]",
   "sql": "WITH HISTORY_TABLE_HEADER AS (\n    SELECT\n    COLUMN_NAME\n  \n    FROM INFORMATION_SCHEMA.COLUMNS\n    \n    WHERE\n    TABLE_NAME = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2631f665\",\"path\":[\"history_table\"]}')}' AND\n    TABLE_SCHEMA = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2631f665\",\"path\":[\"history_table_schema\"]}')}'\n),\n\nBASE_TABLE_HEADER AS (\n    SELECT\n    COLUMN_NAME\n  \n    FROM INFORMATION_SCHEMA.COLUMNS\n    \n    WHERE\n    TABLE_NAME = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2631f665\",\"path\":[\"base_Table\"]}')}' AND\n    TABLE_SCHEMA = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2631f665\",\"path\":[\"base_table_schema\"]}')}'\n)\n\nSELECT COLUMN_NAME FROM BASE_TABLE_HEADER\nEXCEPT\nSELECT COLUMN_NAME FROM HISTORY_TABLE_HEADER;",
   "update_only": "false"
  }
 },
 {
  "keyword": "if",
  "number": 7,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"bec1a644\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}",
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
  "number": 8,
  "as": "e0ee7862",
  "provider": "logger",
  "name": "log_message",
  "skip": false,
  "input": {
   "message": "=_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"bec1a644\",\"path\":[\"rows\"]}').format_map(\"'%{column_name}'\").join(', ')",
   "user_logs_enabled": "false"
  }
 },
 {
  "keyword": "action",
  "number": 9,
  "as": "e5b3b4e2",
  "provider": "snowflake",
  "name": "run_custom_sql",
  "skip": false,
  "input": {
   "output_schema": "[{\"name\":\"column_name\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Column name\"},{\"name\":\"data_type\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Data type\"}]",
   "sql": "SELECT\nCOLUMN_NAME,\nDATA_TYPE\n\nFROM INFORMATION_SCHEMA.COLUMNS\n\nWHERE\nTABLE_NAME = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2631f665\",\"path\":[\"base_Table\"]}')}' AND\nTABLE_SCHEMA = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2631f665\",\"path\":[\"base_table_schema\"]}')}' AND\nCOLUMN_NAME IN (#{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"e0ee7862\",\"path\":[\"message\"]}')})",
   "update_only": "false"
  }
 },
 {
  "keyword": "action",
  "number": 10,
  "as": "8d8ed948",
  "provider": "workato_variable",
  "name": "update_variables",
  "skip": false,
  "input": {
   "name": "aa56d1bf-2b3a-43e5-966b-a369022ddfc1:2631f665:sql_script_for_adding_fields",
   "sql_script_for_adding_fields": "=_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"e5b3b4e2\",\"path\":[\"rows\"]}').format_map('%{column_name} %{data_type}').join(', ')"
  }
 },
 {
  "keyword": "action",
  "number": 11,
  "as": "bbfd0d45",
  "provider": "snowflake",
  "name": "run_custom_sql",
  "skip": false,
  "input": {
   "sql": "ALTER TABLE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2631f665\",\"path\":[\"history_table_database\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2631f665\",\"path\":[\"history_table_schema\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2631f665\",\"path\":[\"history_table\"]}')}\nADD #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2631f665\",\"path\":[\"sql_script_for_adding_fields\"]}')}",
   "update_only": "false"
  }
 },
 {
  "keyword": "action",
  "number": 12,
  "as": "da6b3bcb",
  "provider": "workato_recipe_function",
  "name": "return_result",
  "skip": false,
  "input": {
   "result": {
    "fields_added": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"e5b3b4e2\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}",
    "is_successful": "true"
   }
  }
 },
 {
  "keyword": "catch",
  "number": 13,
  "as": "1ae64ff0",
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
  "number": 14,
  "as": "2abe3ee4",
  "provider": "workato_recipe_function",
  "name": "return_result",
  "skip": false,
  "input": {
   "result": {
    "error_message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"1ae64ff0\",\"path\":[\"message\"]}')}",
    "fields_added": "0",
    "is_successful": "false"
   }
  }
 }
]
'''

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "snowflake.run_custom_sql",
    "workato_runtime.update_variables",
    "workato_runtime.log_message",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "workato_recipe_function.return_result",
]
PARAM_KEYS = (
    "base_table_database",
    "base_table_schema",
    "base_table",
    "history_table_database",
    "history_table_schema",
    "history_table",
)
SEED_SECTIONS = {"snowflake_live"}
EXPECT_KEYS = ("tools", "tool_expectations", "executed_action_count", "result", "snowflake_sqls", "variable_updates", "final_tables")


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


def validate_86179000(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_86179000(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_86179000(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = _require_parameters(trigger, ctx)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - SEED_SECTIONS)
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    snowflake_seed = seed_in.get("snowflake_live")
    expect = data.get("expect")
    _require_expect_shape(expect)
    _require_snowflake_seed(snowflake_seed, parameters, expect)
    provision_seed = deepcopy(snowflake_seed)
    expected_updates = expect.get("variable_updates") or []
    expected_header = (
        expected_updates[0].get("table_header")
        if expected_updates and isinstance(expected_updates[0], dict)
        else None
    )
    if isinstance(expected_header, list) and expected_header:
        base_name = "%s.%s.%s" % (
            parameters["base_table_database"],
            parameters["base_table_schema"],
            parameters["base_table"],
        )
        history_name = "%s.%s.%s" % (
            parameters["history_table_database"],
            parameters["history_table_schema"],
            parameters["history_table"],
        )
        tables = provision_seed.get("tables") or {}
        column_order = {base_name: list(map(str, expected_header))}
        history_spec = tables.get(history_name) or {}
        history_columns = {
            str(name).casefold()
            for name in (history_spec.get("columns") or {})
        }
        column_order[history_name] = [
            str(name)
            for name in expected_header
            if str(name).casefold() in history_columns
        ]
        provision_seed["_simulated_column_order"] = column_order
    provision = ctx.tools.call(
        "harness.snowflake_live.seed_tables",
        {"snowflake": provision_seed},
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "expect": deepcopy(expect),
        "raw_validation": validation,
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_86179000(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_86179000(raw)
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    cleanup_response: dict[str, Any] | None = None
    initial_snapshot = ctx.tools.call("harness.snowflake.snapshot", {})
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = ctx.tools.call("harness.snowflake.snapshot", {})
    finally:
        cleanup_response = ctx.tools.call("harness.snowflake_live.cleanup", {})
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
    if not cleanup_response.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake cleanup failed: {cleanup_response}")
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
            "cleanup_response": {"snowflake_live": cleanup_response},
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_86179000(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_parameters(trigger: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input requires a parameters object")
    unexpected = sorted(set(parameters) - set(PARAM_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters has unexpected keys: {unexpected}")
    for key in PARAM_KEYS:
        value = parameters.get(key)
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters.{key} must be a non-empty string")
        if value != value.upper():
            # INFORMATION_SCHEMA stores uppercase identifiers and the recipe
            # compares them as case-sensitive string literals.
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger parameters.{key} must be uppercase: {value!r}"
            )
    env_database = str(ctx.env.snowflake_database or "").upper()
    if not env_database:
        raise RuntimeError(f"recipe {RECIPE_ID} requires SNOWFLAKE_DATABASE in the environment")
    for key in ("base_table_database", "history_table_database"):
        if parameters[key] != env_database:
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger parameters.{key} ({parameters[key]!r}) must equal the "
                f"live SNOWFLAKE_DATABASE ({env_database!r}): the harness forces qualified names "
                "into that database and INFORMATION_SCHEMA is resolved there"
            )
    return parameters


def _require_expect_shape(expect: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    tools = expect.get("tools")
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tools, list) or not tools or tools[-1] != "workato_recipe_function.return_result":
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools must be the allowed-tool sequence ending in "
            "workato_recipe_function.return_result"
        )
    if not isinstance(tool_expectations, list) or len(tool_expectations) != len(tools):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry")
    result = expect.get("result")
    if not isinstance(result, dict) or "is_successful" not in result or "fields_added" not in result:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.result must pin the recipe-function return "
            "(is_successful + fields_added)"
        )
    if not isinstance(expect.get("snowflake_sqls"), list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.snowflake_sqls must pin the resolved SQL texts")
    if not isinstance(expect.get("variable_updates"), list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.variable_updates must pin the update_variables writes")
    if not isinstance(expect.get("final_tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.final_tables must pin the final live table rows")
    if str(result.get("is_successful")) == "false" and not isinstance(expect.get("catch"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} failure variants must pin expect.catch {{type, message}}"
        )


def _require_snowflake_seed(snowflake_seed: Any, parameters: dict[str, Any], expect: dict[str, Any]) -> None:
    if not isinstance(snowflake_seed, dict) or not isinstance(snowflake_seed.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.snowflake_live.tables (may be empty)")
    tables = snowflake_seed["tables"]
    for table, spec in tables.items():
        if not isinstance(spec, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} snowflake_live table {table} spec must be an object")
        columns = spec.get("columns")
        if not isinstance(columns, dict) or not columns or not all(
            isinstance(kind, str) and kind.strip() for kind in columns.values()
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} snowflake_live table {table} must declare explicit column types"
            )
        rows = spec.get("rows")
        if not isinstance(rows, list):
            raise RuntimeError(f"recipe {RECIPE_ID} snowflake_live table {table} must declare rows")
        lower_columns = {str(name).strip().lower() for name in columns}
        for row in rows:
            if not isinstance(row, dict):
                raise RuntimeError(f"recipe {RECIPE_ID} snowflake_live table {table} rows must be objects")
            extra = {str(key).strip().lower() for key in row} - lower_columns
            if extra:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} snowflake_live table {table} row uses undeclared columns: {sorted(extra)}"
                )
    base_name = "%s.%s.%s" % (
        parameters["base_table_database"],
        parameters["base_table_schema"],
        parameters["base_table"],
    )
    history_name = "%s.%s.%s" % (
        parameters["history_table_database"],
        parameters["history_table_schema"],
        parameters["history_table"],
    )
    if isinstance(expect.get("catch"), dict):
        if base_name in tables:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must name a base table that is NOT seeded; "
                f"{base_name} is in seed.snowflake_live.tables"
            )
        return
    for name, label in ((base_name, "base"), (history_name, "history")):
        if name not in tables:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed.snowflake_live.tables must contain the {label} table under "
                f"the exact fully-qualified key {name!r} (the harness rewrites that literal in the "
                f"recipe SQL); got keys {sorted(tables)}"
            )
    base_columns = {str(name).lower() for name in tables[base_name]["columns"]}
    history_columns = {str(name).lower() for name in tables[history_name]["columns"]}
    new_columns = base_columns - history_columns
    if len(new_columns) > 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} ALTER variants must add exactly ONE column "
            f"(EXCEPT/IN result order is live-nondeterministic; probed); got {sorted(new_columns)}"
        )


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
