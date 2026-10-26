from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_92048772


RECIPE_ID = "92048772"
SEED_TYPE = "snowflake_terminated_employee_exclusion_deactivation_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "b9ad7cba"
DECLARE_STEP_AS = "c440cb90"
SQL_STEP_AS = "cd4e03b9"
UPDATE_VAR_STEP_AS = "f80af25c"
UPDATE_ROWS_STEP_AS = "bedec5f9"
EXCLUSION_TABLE = "SIGMA.USER_ALERT_EXCLUSION_LIST"
EMPLOYEE_TABLE = "PUBLIC.EMPLOYEE"
TABLE_COLUMNS: dict[str, dict[str, str]] = {
    EXCLUSION_TABLE: {"employee_id": "number", "active": "boolean", "reason": "string"},
    EMPLOYEE_TABLE: {"id": "number", "status": "string", "full_name": "string"},
}
VARIABLE_TARGET = "c2cf60d0-5620-4be0-b5a7-18a3bfc7780b:c440cb90:employee_i_ds_to_update"
REASON_TEXT = "User is no longer with the Company"
UPDATE_COLUMNS = {"active": "false", "reason": REASON_TEXT}
RAW_SQL = (
    "SELECT\nEAUL.EMPLOYEE_ID AS EMPLOYEE_ID\n\n"
    "FROM SIGMA.USER_ALERT_EXCLUSION_LIST AS EAUL\n\n"
    "INNER JOIN PUBLIC.EMPLOYEE AS E ON E.ID = EAUL.EMPLOYEE_ID\n\n"
    "WHERE\nUPPER(E.STATUS) = 'TERMINATED' AND\nEAUL.ACTIVE = TRUE "
)


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "clock", "name": "scheduled_event", "as": "b9ad7cba", "skip": false, "input": {"time_unit": "days", "timezone": "Etc/UTC", "trigger_at": "22:00:00", "trigger_every": "1"}, "block": [{"number": 2, "keyword": "action", "provider": "workato_variable", "name": "declare_variable", "as": "c440cb90", "skip": false, "input": {"variables": {"schema": "[{\"control_type\":\"text\",\"label\":\"Employee IDs to Update\",\"name\":\"employee_i_ds_to_update\",\"type\":\"string\",\"optional\":true}]"}}, "block": []}, {"number": 3, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql", "as": "cd4e03b9", "skip": false, "input": {"output_schema": "[{\"name\":\"employee_id\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"Employee ID\",\"parse_output\":\"integer_conversion\"}]", "sql": "SELECT\nEAUL.EMPLOYEE_ID AS EMPLOYEE_ID\n\nFROM SIGMA.USER_ALERT_EXCLUSION_LIST AS EAUL\n\nINNER JOIN PUBLIC.EMPLOYEE AS E ON E.ID = EAUL.EMPLOYEE_ID\n\nWHERE\nUPPER(E.STATUS) = 'TERMINATED' AND\nEAUL.ACTIVE = TRUE ", "update_only": "false"}, "block": []}, {"number": 4, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"cd4e03b9\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}", "operand": "greater_than", "rhs": "0"}], "operand": "and", "type": "compound"}, "block": [{"number": 5, "keyword": "action", "provider": "workato_variable", "name": "update_variables", "as": "f80af25c", "skip": false, "input": {"employee_i_ds_to_update": "=_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"cd4e03b9\",\"path\":[\"rows\"]}').format_map(\"'%{employee_id}'\").join(\",\\n\")", "name": "c2cf60d0-5620-4be0-b5a7-18a3bfc7780b:c440cb90:employee_i_ds_to_update"}, "block": []}, {"number": 6, "keyword": "action", "provider": "snowflake", "name": "update_rows", "as": "bedec5f9", "skip": false, "input": {"columns": {"active": "false", "reason": "User is no longer with the Company"}, "table": "SIGMA.USER_ALERT_EXCLUSION_LIST", "where": "EMPLOYEE_ID IN (#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c440cb90\",\"path\":[\"employee_i_ds_to_update\"]}')})"}, "block": []}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (DECLARE_STEP_AS, "workato_variable", "declare_variable"),
    (SQL_STEP_AS, "snowflake", "run_custom_sql"),
    (UPDATE_VAR_STEP_AS, "workato_variable", "update_variables"),
    (UPDATE_ROWS_STEP_AS, "snowflake", "update_rows"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "snowflake.run_custom_sql",
    "workato_runtime.update_variables",
    "snowflake.update_rows",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "snowflake.update_rows",
]
CASES = (
    "terminated_exclusions_deactivated",
    "zero_rows_if_false",
    "join_drops_unknown_employee",
)
REQUIRED_EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "qualifying_employee_ids",
    "variable_value",
    "update_args",
    "update_rows_updated",
    "final_exclusion_rows",
    "employee_rows",
)


def validate_92048772(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    # Semantic pins on the drift-prone bits (the tree pin holds the exact
    # bytes; these name the trap when one changes).
    sql_node = _node_by_as(raw, SQL_STEP_AS)
    if str((sql_node.get("input") or {}).get("sql") or "") != RAW_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} custom SQL changed")
    for fragment in (
        "FROM SIGMA.USER_ALERT_EXCLUSION_LIST AS EAUL",
        "INNER JOIN PUBLIC.EMPLOYEE AS E ON E.ID = EAUL.EMPLOYEE_ID",
        "UPPER(E.STATUS) = 'TERMINATED'",
        "EAUL.ACTIVE = TRUE",
    ):
        if fragment not in RAW_SQL:
            raise RuntimeError(f"recipe {RECIPE_ID} search SQL lost {fragment!r}")
    update_var = _node_by_as(raw, UPDATE_VAR_STEP_AS)
    var_input = update_var.get("input") or {}
    if str(var_input.get("name") or "") != VARIABLE_TARGET:
        raise RuntimeError(
            f"recipe {RECIPE_ID} update_variables target changed: {var_input.get('name')!r}"
        )
    formula = str(var_input.get("employee_i_ds_to_update") or "")
    if '.format_map("\'%{employee_id}\'")' not in formula or '.join(",\\n")' not in formula:
        raise RuntimeError(f"recipe {RECIPE_ID} id-list formula changed: {formula!r}")
    update_rows = _node_by_as(raw, UPDATE_ROWS_STEP_AS)
    rows_input = update_rows.get("input") or {}
    if str(rows_input.get("table") or "") != EXCLUSION_TABLE:
        raise RuntimeError(
            f"recipe {RECIPE_ID} update table changed: {rows_input.get('table')!r} "
            "(the registered seed key must equal it exactly)"
        )
    if rows_input.get("columns") != UPDATE_COLUMNS:
        raise RuntimeError(f"recipe {RECIPE_ID} update columns changed: {rows_input.get('columns')!r}")
    where = str(rows_input.get("where") or "")
    if not where.startswith("EMPLOYEE_ID IN (#{") or DECLARE_STEP_AS not in where:
        raise RuntimeError(f"recipe {RECIPE_ID} update where changed: {where!r}")
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "snowflake_tables": sorted(TABLE_COLUMNS.keys()),
        "actions": [
            {
                "number": a.get("number"),
                "provider": a.get("provider"),
                "name": a.get("name"),
                "as": a.get("as"),
            }
            for a in actions
        ],
    }


def seed_92048772(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_92048772(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (payload-less "
            f"scheduler tick; no trigger field is ever dereferenced): {trigger!r}"
        )
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: a forced action error would fail the "
            "whole run instead of exercising a recipe branch"
        )
    if data.get("job_context") is not None:
        raise RuntimeError(f"recipe {RECIPE_ID} never reads job_context (dead seed state)")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the snowflake_live section; "
            f"got {sorted(seed_in.keys())}"
        )
    exclusion_rows, employee_rows = _require_snowflake_section(seed_in["snowflake_live"])
    qualifying = _qualifying_ids(exclusion_rows, employee_rows)
    _require_expect_shape(data.get("expect"), exclusion_rows, employee_rows, qualifying)
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


def run_92048772(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_92048772(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    if seed.get("trigger") != {}:
        raise RuntimeError(f"recipe {RECIPE_ID} seed trigger must be the explicit payload-less {{}}")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect"),
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    raw_execution: dict[str, Any] | None = None
    cleanup: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = ctx.tools.call("harness.snowflake.snapshot", {})
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = ctx.tools.call("harness.snowflake.snapshot", {})
    finally:
        # Required cleanup: the seeder create-or-replaced both registered
        # 2-part tables; drop them whether or not the run completed (the
        # update lands in benchmark-owned live tables).
        cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    details["cleanup_response"] = {"snowflake_live": cleanup}
    if not (cleanup or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake cleanup failed: {cleanup}")
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
    result["verifier"] = verify_92048772(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_snowflake_section(section: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the SQL has no CURRENT_* — current_time must NOT be declared)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted(TABLE_COLUMNS.keys()):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly the 2 "
            f"literal 2-part names {sorted(TABLE_COLUMNS.keys())}"
        )
    for table, expected_columns in TABLE_COLUMNS.items():
        spec = tables[table]
        if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {table} spec must be exactly "
                "{'columns': ..., 'rows': ...}"
            )
        if spec["columns"] != expected_columns:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {table} must declare exactly the columns "
                f"{expected_columns}"
            )
        if not isinstance(spec["rows"], list) or not spec["rows"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {table} rows must be a non-empty list — the "
                "IF-false case proves the WHERE arms via non-qualifying rows, not an "
                "empty table"
            )
    exclusion_rows = [
        _require_exclusion_row(idx, row) for idx, row in enumerate(tables[EXCLUSION_TABLE]["rows"])
    ]
    employee_rows = [
        _require_employee_row(idx, row) for idx, row in enumerate(tables[EMPLOYEE_TABLE]["rows"])
    ]
    exclusion_ids = [row["employee_id"] for row in exclusion_rows]
    if len(set(exclusion_ids)) != len(exclusion_ids):
        raise RuntimeError(
            f"recipe {RECIPE_ID} exclusion EMPLOYEE_ID values must be distinct (the "
            f"IN-list update and the final-state pins key on them): {exclusion_ids}"
        )
    employee_ids = [row["id"] for row in employee_rows]
    if len(set(employee_ids)) != len(employee_ids):
        raise RuntimeError(
            f"recipe {RECIPE_ID} employee ID values must be distinct (a duplicate id "
            f"would fan out the INNER JOIN): {employee_ids}"
        )
    return exclusion_rows, employee_rows


def _require_exclusion_row(idx: int, row: Any) -> dict[str, Any]:
    if not isinstance(row, dict) or sorted(row.keys()) != ["active", "employee_id", "reason"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} exclusion row {idx} must fill exactly "
            f"employee_id/active/reason: {row!r}"
        )
    if not isinstance(row["employee_id"], int) or isinstance(row["employee_id"], bool):
        raise RuntimeError(
            f"recipe {RECIPE_ID} exclusion row {idx}.employee_id must be an int "
            f"(NUMBER column; the IN-list coerces string literals): {row!r}"
        )
    if not isinstance(row["active"], bool):
        raise RuntimeError(
            f"recipe {RECIPE_ID} exclusion row {idx}.active must be a boolean: {row!r}"
        )
    if not isinstance(row["reason"], str) or not row["reason"].strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} exclusion row {idx}.reason must be a non-empty string: {row!r}"
        )
    if row["reason"] == REASON_TEXT:
        raise RuntimeError(
            f"recipe {RECIPE_ID} exclusion row {idx} seeds the post-update reason "
            f"{REASON_TEXT!r} — the write would be unobservable"
        )
    return dict(row)


def _require_employee_row(idx: int, row: Any) -> dict[str, Any]:
    if not isinstance(row, dict) or sorted(row.keys()) != ["full_name", "id", "status"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} employee row {idx} must fill exactly "
            f"id/status/full_name: {row!r}"
        )
    if not isinstance(row["id"], int) or isinstance(row["id"], bool):
        raise RuntimeError(f"recipe {RECIPE_ID} employee row {idx}.id must be an int: {row!r}")
    for key in ("status", "full_name"):
        if not isinstance(row[key], str) or not row[key].strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} employee row {idx}.{key} must be a non-empty string: {row!r}"
            )
    return dict(row)


def _qualifying_ids(
    exclusion_rows: list[dict[str, Any]],
    employee_rows: list[dict[str, Any]],
) -> list[int]:
    """The ids the live SELECT must return, in exclusion-seed order: ACTIVE
    exclusion rows INNER JOINed to an employee whose UPPER(status) is
    'TERMINATED'."""
    by_id = {row["id"]: row for row in employee_rows}
    out: list[int] = []
    for row in exclusion_rows:
        employee = by_id.get(row["employee_id"])
        if employee is None:
            continue
        if row["active"] is True and employee["status"].upper() == "TERMINATED":
            out.append(row["employee_id"])
    return out


def _variable_value(qualifying: list[int]) -> str:
    return ",\n".join(f"'{employee_id}'" for employee_id in qualifying)


def _require_expect_shape(
    expect: Any,
    exclusion_rows: list[dict[str, Any]],
    employee_rows: list[dict[str, Any]],
    qualifying: list[int],
) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    case = expect.get("case")
    if case not in CASES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.case must be one of {CASES}")
    _require_case(case, exclusion_rows, employee_rows, qualifying)
    if expect.get("qualifying_employee_ids") != qualifying:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.qualifying_employee_ids must be the seed-order "
            f"qualifying ids {qualifying}; got {expect.get('qualifying_employee_ids')!r}"
        )
    branch_true = bool(qualifying)
    checks = (
        expect.get("executed_action_count") == (4 if branch_true else 2),
        expect.get("tools") == (ALLOWED_TOOLS if branch_true else ALLOWED_TOOLS[:1]),
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.executed_action_count/tools do not match the "
            f"{'IF-true' if branch_true else 'IF-false'} branch: {expect!r}"
        )
    if branch_true:
        variable_value = _variable_value(qualifying)
        expected_update_args = {
            "table": EXCLUSION_TABLE,
            "where": f"EMPLOYEE_ID IN ({variable_value})",
            "columns": dict(UPDATE_COLUMNS),
        }
        if expect.get("variable_value") != variable_value:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.variable_value must be the format_map/join "
                f"render {variable_value!r}; got {expect.get('variable_value')!r}"
            )
        if expect.get("update_args") != expected_update_args:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.update_args must be "
                f"{json.dumps(expected_update_args, ensure_ascii=False)}; got "
                f"{expect.get('update_args')!r}"
            )
        if expect.get("update_rows_updated") != len(qualifying):
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.update_rows_updated must be {len(qualifying)}"
            )
    else:
        for key in ("variable_value", "update_args", "update_rows_updated"):
            if expect.get(key) is not None:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} IF-false variants must pin expect.{key} as null; "
                    f"got {expect.get(key)!r}"
                )
    expected_final = []
    for row in exclusion_rows:
        if row["employee_id"] in qualifying:
            expected_final.append(
                {"EMPLOYEE_ID": row["employee_id"], "ACTIVE": False, "REASON": REASON_TEXT}
            )
        else:
            expected_final.append(
                {"EMPLOYEE_ID": row["employee_id"], "ACTIVE": row["active"], "REASON": row["reason"]}
            )
    if expect.get("final_exclusion_rows") != expected_final:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_exclusion_rows must pin the exact final "
            f"exclusion table (seed order): {json.dumps(expected_final, ensure_ascii=False)}"
        )
    expected_employees = [
        {"ID": row["id"], "STATUS": row["status"], "FULL_NAME": row["full_name"]}
        for row in employee_rows
    ]
    if expect.get("employee_rows") != expected_employees:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.employee_rows must pin the read-only employee "
            f"table (seed order): {json.dumps(expected_employees, ensure_ascii=False)}"
        )
    _require_tool_expectations(expect, qualifying)


def _require_case(
    case: str,
    exclusion_rows: list[dict[str, Any]],
    employee_rows: list[dict[str, Any]],
    qualifying: list[int],
) -> None:
    by_id = {row["id"]: row for row in employee_rows}
    status_killed = [
        row for row in exclusion_rows
        if row["active"] is True
        and row["employee_id"] in by_id
        and by_id[row["employee_id"]]["status"].upper() != "TERMINATED"
    ]
    inactive_killed = [
        row for row in exclusion_rows
        if row["active"] is False
        and row["employee_id"] in by_id
        and by_id[row["employee_id"]]["status"].upper() == "TERMINATED"
    ]
    join_orphans = [row for row in exclusion_rows if row["employee_id"] not in by_id]
    qualifying_statuses = [
        by_id[employee_id]["status"] for employee_id in qualifying
    ]
    if case == "terminated_exclusions_deactivated":
        checks = (
            len(qualifying) >= 2,
            len(status_killed) >= 1,
            len(inactive_killed) >= 1,
            any(status != "TERMINATED" for status in qualifying_statuses),
            not join_orphans,
        )
        reason = (
            "terminated_exclusions_deactivated must prove both WHERE arms live: >=2 "
            "qualifying rows (>=1 with non-uppercase seeded status so UPPER() is "
            "load-bearing), >=1 active exclusion killed by employee status, >=1 "
            "terminated employee killed by ACTIVE=false; no join orphans (that is "
            "variant join_drops_unknown_employee's arm)"
        )
    elif case == "zero_rows_if_false":
        checks = (
            len(qualifying) == 0,
            len(status_killed) >= 1,
            len(inactive_killed) >= 1,
        )
        reason = (
            "zero_rows_if_false seeds ONLY non-qualifying rows, at least one killed by "
            "each WHERE arm, so the empty SELECT comes from the WHERE, not an empty table"
        )
    else:  # join_drops_unknown_employee
        checks = (
            len(qualifying) >= 1,
            len(join_orphans) >= 1,
            all(row["active"] is True for row in join_orphans),
        )
        reason = (
            "join_drops_unknown_employee needs >=1 qualifying row plus >=1 ACTIVE "
            "exclusion row with NO PUBLIC.EMPLOYEE match — the INNER JOIN must drop "
            "it and the update must leave it active"
        )
    if not all(checks):
        raise RuntimeError(f"recipe {RECIPE_ID} case {case!r} seed requirements not met ({reason})")


def _require_tool_expectations(expect: dict[str, Any], qualifying: list[int]) -> None:
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or len(items) != 1 or not isinstance(items[0], dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin exactly the "
            "run_custom_sql call (update_rows is deliberately NOT an item: the shared "
            "verifier's generic _parse_snowflake_where cannot parse the IN-list where — the update "
            "args/result/final-state checks live in the recipe fragment)"
        )
    sql_item = items[0]
    checks = (
        sql_item.get("tool") == "snowflake.run_custom_sql",
        sql_item.get("args_contains") == {"sql": RAW_SQL, "parameters": {}},
        sql_item.get("result_count") == len(qualifying),
        sorted(sql_item.keys()) == ["args_contains", "result_count", "tool"],
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0] must pin the verbatim SQL with "
            f"empty parameters and result_count {len(qualifying)}: {sql_item!r}"
        )


def _normalize_tree(node: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "number": node.get("number"),
        "keyword": node.get("keyword"),
        "provider": node.get("provider") or "",
        "name": node.get("name") or "",
        "as": node.get("as") or "",
        "skip": bool(node.get("skip")),
    }
    if not out["skip"]:
        out["input"] = node.get("input")
    if node.get("keyword") == "foreach":
        out["repeat_mode"] = node.get("repeat_mode")
        out["source"] = node.get("source")
    if isinstance(node.get("filter"), dict):
        out["filter"] = node["filter"]
    out["block"] = [
        _normalize_tree(child) for child in node.get("block") or [] if isinstance(child, dict)
    ]
    return out


def _first_tree_mismatch(actual: Any, expected: Any, path: str = "root") -> str:
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            if key not in actual:
                return f"{path}.{key}: missing in raw recipe"
            if key not in expected:
                return f"{path}.{key}: unexpected in raw recipe"
            found = _first_tree_mismatch(actual[key], expected[key], f"{path}.{key}")
            if found:
                return found
        return ""
    if isinstance(expected, list) and isinstance(actual, list):
        if len(actual) != len(expected):
            return f"{path}: length {len(actual)} != {len(expected)}"
        for idx, (act, exp) in enumerate(zip(actual, expected)):
            found = _first_tree_mismatch(act, exp, f"{path}[{idx}]")
            if found:
                return found
        return ""
    if actual != expected:
        return f"{path}: {json.dumps(actual, default=str)[:200]} != {json.dumps(expected, default=str)[:200]}"
    return ""


def _node_by_as(raw: dict[str, Any], step_as: str) -> dict[str, Any]:
    node = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == step_as),
        None,
    )
    if not isinstance(node, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} step {step_as} missing")
    return node


def _walk_nodes(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        found.append(child)
        found.extend(_walk_nodes(child))
    return found


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
