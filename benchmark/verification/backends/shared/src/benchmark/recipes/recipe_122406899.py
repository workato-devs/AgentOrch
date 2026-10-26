from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_122406899


RECIPE_ID = "122406899"
SEED_TYPE = "api_platform_employee_typeahead_export_variant"
TRACK = "workato_api_platform_employee_typeahead_export"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "33b2d099"
EMPLOYEE_TABLE = "employee"
SQL_STEP_AS = "b0b4151a"
SUCCESS_RETURN_AS = "2f77ac2a"
CATCH_RETURN_AS = "9c6d051c"
CATCH_AS = "c81b5d08"
RAW_SQL = (
    "select\n\tid,\n    concat(first_name, ' ', last_name, ' (', email, ')') as label\n"
    "from employee"
)
RESOLVED_SQL = RAW_SQL + " ORDER BY id DESC"


_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "33b2d099",
  "provider": "workato_api_platform",
  "name": "receive_request",
  "skip": false,
  "input": {
   "request": {
    "content_type": "json",
    "schema": "[]"
   },
   "response": {
    "content_type": "json",
    "responses": [
     {
      "body_schema": "[{\"name\":\"employees\",\"type\":\"array\",\"optional\":false,\"properties\":[{\"name\":\"id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"ID\"},{\"name\":\"label\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Label\"}],\"of\":\"object\",\"label\":\"Employees\"}]",
      "http_status_code": "200"
     },
     {
      "body_schema": "[{\"name\":\"error_message\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Error message\"}]",
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
  "as": "b0b4151a",
  "provider": "snowflake",
  "name": "search_rows_sql",
  "skip": false,
  "input": {
   "limit": "100000",
   "orderby": "id DESC",
   "output_schema": "[{\"control_type\":\"integer\",\"label\":\"ID\",\"type\":\"integer\",\"name\":\"id\",\"optional\":false,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"text\",\"label\":\"Label\",\"type\":\"string\",\"name\":\"label\"}]",
   "sql": "select\n\tid,\n    concat(first_name, ' ', last_name, ' (', email, ')') as label\nfrom employee"
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "2f77ac2a",
  "provider": "workato_api_platform",
  "name": "return_response",
  "skip": false,
  "input": {
   "http_status_code": "200",
   "response": {
    "employees": {
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"b0b4151a\",\"path\":[\"rows\"]}')}",
     "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"b0b4151a\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"id_b497e547\"]}')}",
     "label": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"b0b4151a\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"label_10e2e5a9\"]}')}"
    }
   }
  }
 },
 {
  "keyword": "catch",
  "number": 5,
  "as": "c81b5d08",
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
  "as": "9c6d051c",
  "provider": "workato_api_platform",
  "name": "return_response",
  "skip": false,
  "input": {
   "http_status_code": "400",
   "response": {
    "error_message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"c81b5d08\",\"path\":[\"message\"]}')}"
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
)
OPTIONAL_EXPECT_KEYS = {"catch_message"}
RETURN_STEP_AS = (SUCCESS_RETURN_AS, CATCH_RETURN_AS)
EMPLOYEE_COLUMNS = {
    "ID": "number",
    "FIRST_NAME": "string",
    "LAST_NAME": "string",
    "EMAIL": "string",
}


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


def validate_122406899(raw: dict[str, Any]) -> dict[str, Any]:
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
    if str(sql_pin["input"].get("orderby") or "") != "id DESC":
        raise RuntimeError(
            f"recipe {RECIPE_ID} connector orderby changed -- the appended ORDER BY "
            f"analysis no longer holds: {sql_pin['input'].get('orderby')!r}"
        )
    if str(sql_pin["input"].get("limit") or "") != "100000":
        raise RuntimeError(f"recipe {RECIPE_ID} connector limit changed")
    response_pin = next(pin for pin in actual if pin["as"] == SUCCESS_RETURN_AS)
    employees = ((response_pin["input"].get("response") or {}).get("employees") or {})
    if "id_b497e547" not in str(employees.get("id")) or "label_10e2e5a9" not in str(employees.get("label")):
        raise RuntimeError(
            f"recipe {RECIPE_ID} hash-suffixed pill names changed -- the `_<8-hex>` "
            f"strip-fallback analysis no longer holds: {employees!r}"
        )
    actions = [pin for pin in actual if pin["keyword"] == "action"]
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "employee_table": EMPLOYEE_TABLE,
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


def seed_122406899(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_122406899(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (request schema []; "
            f"nothing is dereferenced): {trigger!r}"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    expect = data.get("expect")
    force = data.get("force_action_error")
    _require_force_shape(force)
    _require_expect_shape(expect, force)
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
        rows = _require_snowflake_section(seed_in["snowflake_live"])
        derived = _derive_response(rows)
        if expect.get("response") != derived:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.response contradicts the seeded employees: "
                f"expected {derived!r}, got {expect.get('response')!r}"
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


def run_122406899(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_122406899(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    live = isinstance(seed.get("snowflake_live"), dict)
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
            # The employee table is benchmark-owned create-or-replace live
            # state: drop it even when execution fails (cleanup principle).
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
    result["verifier"] = verify_122406899(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


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
    catch = force is not None
    if (expect.get("return_step_as") == CATCH_RETURN_AS) != catch:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the catch return step and force_action_error must be "
            "declared together (the static SQL has no other deterministic failure)"
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
        if "catch_message" not in expect or expect["catch_message"] != force.get("error"):
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must pin expect.catch_message equal "
                "to the forced error text"
            )
        if expect.get("response") != {"error_message": force.get("error")}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must pin response "
                f"{{'error_message': <forced error>}}; got {expect.get('response')!r}"
            )
    elif "catch_message" in expect:
        raise RuntimeError(f"recipe {RECIPE_ID} only catch variants may pin catch_message")


def _require_snowflake_section(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(no CURRENT_* in the SQL -> current_time must NOT be declared)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [EMPLOYEE_TABLE]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{EMPLOYEE_TABLE!r} (the BARE 1-part name the SQL uses)"
        )
    spec = tables[EMPLOYEE_TABLE]
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table spec must be exactly {{'columns': ..., 'rows': ...}}"
        )
    if spec["columns"] != EMPLOYEE_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} employee columns must be exactly {EMPLOYEE_COLUMNS}"
        )
    rows = spec["rows"]
    if not isinstance(rows, list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} employee rows must be a list (empty for the zero-row variant)"
        )
    ids: list[int] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != set(EMPLOYEE_COLUMNS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} every employee row must fill all declared columns: {row!r}"
            )
        if not isinstance(row["ID"], int):
            raise RuntimeError(f"recipe {RECIPE_ID} ID must be an integer (NUMBER column): {row!r}")
        for key in ("FIRST_NAME", "LAST_NAME", "EMAIL"):
            if not isinstance(row[key], str) or not row[key].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} row {key} must be a non-empty string: {row!r}"
                )
        ids.append(row["ID"])
    if len(set(ids)) != len(ids):
        raise RuntimeError(
            f"recipe {RECIPE_ID} employee ids must be distinct (the appended ORDER BY "
            "id DESC pins the exact response order)"
        )
    return [dict(row) for row in rows]


def _derive_response(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Groundtruth of the live SELECT: id-descending employees with the
    live-concat label 'FIRST LAST (EMAIL)'; ids stay ints (NUMBER column)."""
    ordered = sorted(rows, key=lambda row: row["ID"], reverse=True)
    return {
        "employees": [
            {
                "id": row["ID"],
                "label": f"{row['FIRST_NAME']} {row['LAST_NAME']} ({row['EMAIL']})",
            }
            for row in ordered
        ]
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
