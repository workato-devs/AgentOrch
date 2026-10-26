from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_118159799


RECIPE_ID = "118159799"
SEED_TYPE = "recipe_function_snowflake_event_log_add_column_variant"
TRACK = "workato_recipe_function_snowflake_event_log_ddl"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "8b893097"
SQL_STEP_AS = "17ed1d04"
SUCCESS_RETURN_AS = "a029e8b7"
CATCH_AS = "09d0de88"
CATCH_RETURN_AS = "0f4503dd"
TRIGGER_PARAMETERS = (
    "event_log_database",
    "event_log_schema",
    "event_log_table",
    "sql_script_for_adding_fields",
)
RAW_SQL_TEMPLATE = (
    "ALTER TABLE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\","
    "\"line\":\"8b893097\",\"path\":[\"parameters\", \"event_log_database\"]}')}."
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\","
    "\"line\":\"8b893097\",\"path\":[\"parameters\", \"event_log_schema\"]}')}."
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\","
    "\"line\":\"8b893097\",\"path\":[\"parameters\", \"event_log_table\"]}')}"
    "\nADD #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\","
    "\"line\":\"8b893097\",\"path\":[\"parameters\", \"sql_script_for_adding_fields\"]}')}"
)
DUPLICATE_COLUMN_ERROR = (
    "001430 (42601): SQL compilation error:\ncolumn '{column}' already exists"
)
_SCRIPT_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s+\S.*$", flags=re.S)
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "8b893097",
  "provider": "workato_recipe_function",
  "name": "execute",
  "skip": false,
  "input": {
   "parameters_schema_json": "[{\"control_type\":\"text\",\"label\":\"Event Log Database\",\"name\":\"event_log_database\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Event Log Schema\",\"name\":\"event_log_schema\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Event Log Table\",\"name\":\"event_log_table\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"SQL Script for Adding Fields\",\"name\":\"sql_script_for_adding_fields\",\"type\":\"string\",\"optional\":false}]",
   "result_schema_json": "[{\"name\":\"success\",\"type\":\"boolean\",\"optional\":false,\"label\":\"Success\",\"control_type\":\"checkbox\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Success\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"success\",\"type\":\"boolean\",\"optional\":false}},{\"name\":\"error_message\",\"type\":\"string\",\"optional\":true,\"label\":\"Error Message\",\"control_type\":\"text\"}]"
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
  "as": "17ed1d04",
  "provider": "snowflake",
  "name": "run_custom_sql",
  "skip": false,
  "input": {
   "sql": "ALTER TABLE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"8b893097\",\"path\":[\"parameters\", \"event_log_database\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"8b893097\",\"path\":[\"parameters\", \"event_log_schema\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"8b893097\",\"path\":[\"parameters\", \"event_log_table\"]}')}\nADD #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"8b893097\",\"path\":[\"parameters\", \"sql_script_for_adding_fields\"]}')}",
   "update_only": "false"
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "a029e8b7",
  "provider": "workato_recipe_function",
  "name": "return_result",
  "skip": false,
  "input": {
   "result": {
    "success": "true"
   }
  }
 },
 {
  "keyword": "catch",
  "number": 5,
  "as": "09d0de88",
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
  "as": "0f4503dd",
  "provider": "workato_recipe_function",
  "name": "return_result",
  "skip": false,
  "input": {
   "result": {
    "error_message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"09d0de88\",\"path\":[\"message\"]}')}",
    "success": "false"
   }
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "workato_recipe_function.return_result",
]
EXPECT_KEYS = (
    "case",
    "outcome",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "resolved_sql",
    "result",
    "table_key",
    "column",
)
OUTCOMES = ("added_column_true", "duplicate_column_false")


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


def validate_118159799(raw: dict[str, Any]) -> dict[str, Any]:
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
    if sql_pin["input"].get("sql") != RAW_SQL_TEMPLATE:
        raise RuntimeError(f"recipe {RECIPE_ID} ALTER template changed: {sql_pin['input'].get('sql')!r}")
    if sql_pin["input"].get("update_only") != "false":
        raise RuntimeError(f"recipe {RECIPE_ID} update_only changed")
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


def _require_trigger_shape(trigger: dict[str, Any]) -> tuple[str, str, str]:
    """Returns (table_key, script, script_column)."""
    if sorted(trigger.keys()) != ["parameters"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly 'parameters': {trigger!r}"
        )
    parameters = trigger["parameters"]
    if not isinstance(parameters, dict) or sorted(parameters.keys()) != sorted(TRIGGER_PARAMETERS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must be exactly "
            f"{sorted(TRIGGER_PARAMETERS)}: {parameters!r}"
        )
    for key in TRIGGER_PARAMETERS:
        if not isinstance(parameters[key], str) or not parameters[key].strip():
            raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter {key} must be non-empty")
    for key in ("event_log_database", "event_log_schema", "event_log_table"):
        if not _IDENT_RE.fullmatch(parameters[key]):
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger parameter {key} must be a plain identifier "
                f"(the assembled name is the registered table key): {parameters[key]!r}"
            )
    script = parameters["sql_script_for_adding_fields"]
    match = _SCRIPT_RE.fullmatch(script)
    if not match:
        raise RuntimeError(
            f"recipe {RECIPE_ID} sql_script_for_adding_fields must be a single "
            f"'<COLUMN> <TYPE...>' clause: {script!r}"
        )
    table_key = ".".join(
        (parameters["event_log_database"], parameters["event_log_schema"], parameters["event_log_table"])
    )
    return table_key, script, match.group(1).upper()


def _resolved_sql(trigger: dict[str, Any]) -> str:
    parameters = trigger["parameters"]
    return (
        f"ALTER TABLE {parameters['event_log_database']}."
        f"{parameters['event_log_schema']}.{parameters['event_log_table']}\n"
        f"ADD {parameters['sql_script_for_adding_fields']}"
    )


def _require_snowflake_section(section: Any, table_key: str) -> dict[str, str]:
    """Returns the declared columns spec (uppercase names as authored)."""
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the DDL uses no CURRENT_DATE/TIMESTAMP, so current_time is not allowed)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [table_key]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly the "
            f"table the trigger parameters assemble ({table_key!r} — _rewrite_sql keys "
            f"on the byte-identical name): {sorted(tables) if isinstance(tables, dict) else tables!r}"
        )
    spec = tables[table_key]
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table spec must be exactly {{'columns': ..., 'rows': ...}}"
        )
    columns = spec["columns"]
    if not isinstance(columns, dict) or not columns:
        raise RuntimeError(f"recipe {RECIPE_ID} table columns must be a non-empty object")
    for name in columns:
        if not _IDENT_RE.fullmatch(str(name)):
            raise RuntimeError(f"recipe {RECIPE_ID} column name must be a plain identifier: {name!r}")
    rows = spec["rows"]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table rows must be NON-EMPTY — the post-ALTER snapshot "
            "proves the new column via the read-back row keys, and an empty table "
            "snapshot carries no columns"
        )
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(str(k).upper() for k in row) != sorted(
            str(k).upper() for k in columns
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} must fill exactly the declared "
                f"columns; got {row!r}"
            )
    return {str(name).upper(): str(kind) for name, kind in columns.items()}


def _require_expect_shape(
    expect: Any,
    outcome_columns: dict[str, str],
    table_key: str,
    script_column: str,
    resolved_sql: str,
) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    outcome = expect.get("outcome")
    if outcome not in OUTCOMES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.outcome must be one of {OUTCOMES}")
    column_exists = script_column in outcome_columns
    if outcome == "added_column_true":
        if column_exists:
            raise RuntimeError(
                f"recipe {RECIPE_ID} added_column_true requires a script column the "
                f"seeded table LACKS; {script_column!r} is already declared"
            )
        checks = (
            expect.get("result") == {"success": "true"},
            expect.get("executed_action_count") == 2,
            expect.get("tools")
            == ["snowflake.run_custom_sql", "workato_recipe_function.return_result"],
        )
        reason = (
            "success variants pin result {'success': 'true'} (raw input literal "
            "STRING — no boolean conversion on return_result) after 2 actions"
        )
    else:
        if not column_exists:
            raise RuntimeError(
                f"recipe {RECIPE_ID} duplicate_column_false requires a script column "
                f"the seeded table ALREADY declares; {script_column!r} is missing from "
                f"{sorted(outcome_columns)}"
            )
        live_error = DUPLICATE_COLUMN_ERROR.format(column=script_column)
        checks = (
            expect.get("result") == {"success": "false", "error_message": live_error},
            expect.get("executed_action_count") == 1,
            expect.get("tools") == ["workato_recipe_function.return_result"],
        )
        reason = (
            "duplicate variants pin result {'success': 'false', 'error_message': "
            + repr(live_error)
            + "} — the deterministic live Snowflake DDL error — after 1 action (the "
            "failed snowflake call never traces)"
        )
    common = (
        expect.get("resolved_sql") == resolved_sql,
        expect.get("table_key") == table_key,
        expect.get("column") == script_column,
    )
    if not all(checks) or not all(common):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with outcome "
            f"{outcome!r} ({reason}; resolved_sql/table_key/column must pin the "
            f"trigger-derived values): {expect!r}"
        )


def seed_118159799(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118159799(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} both branches are LIVE-natural (duplicate column "
            "drives the catch); force_action_error is not allowed"
        )
    trigger = trigger_input(ctx)
    table_key, _script, script_column = _require_trigger_shape(trigger)
    resolved_sql = _resolved_sql(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} every variant must seed exactly the snowflake_live "
            f"section (both branches run live DDL); got "
            f"{sorted(seed_in) if isinstance(seed_in, dict) else seed_in!r}"
        )
    columns = _require_snowflake_section(seed_in["snowflake_live"], table_key)
    _require_expect_shape(data.get("expect"), columns, table_key, script_column, resolved_sql)
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


def run_118159799(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118159799(raw)
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
        # MANDATORY cleanup: the ALTER PERSISTS on the seeded event-log table —
        # drop the create-or-replace table whether or not the run completed.
        snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    details["cleanup_response"] = {"snowflake_live": snowflake_cleanup}
    if not (snowflake_cleanup or {}).get("ok", False):
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
    result["verifier"] = verify_118159799(result)
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
