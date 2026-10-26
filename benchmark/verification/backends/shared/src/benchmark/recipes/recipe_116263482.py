from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_116263482


RECIPE_ID = "116263482"
SEED_TYPE = "recipe_function_direct_hire_default_apps_variant"
TRACK = "workato_recipe_function_direct_hire_default_apps"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
APP_TABLE = "BENCH.APP"
EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("workato_variable", "declare_list", "c556d2b4"),
    ("workato_variable", "declare_list", "a140d0a9"),
    ("workato_variable", "insert_to_list", "e9078443"),
    ("workato_variable", "declare_variable", "c32cdbf8"),
    ("snowflake", "search_rows_sql", "8c579c0a"),
    ("workato_variable", "insert_to_list", "9489afdf"),
    ("workato_recipe_function", "return_result", "abc3d957"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_list",
    "workato_runtime.insert_to_list",
    "workato_runtime.declare_variable",
    "snowflake.search_rows_sql",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_recipe_function.return_result",
]
APP_SQL = (
    "SELECT\nA.ID AS APP_ID,\nA.NAME AS APP_NAME,\nA.STATUS\n\nFROM APP A\n\n"
    "WHERE A.ID IN ('#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\","
    "\"line\":\"c32cdbf8\",\"path\":[\"where_clause\"]}')}')"
)
WHERE_CLAUSE_FORMULA = (
    "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c556d2b4\","
    "\"path\":[\"list_items\"]}').pluck('app_id').uniq.smart_join(\"', '\")"
)
DIRECT_HIRE_LHS = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\","
    "\"line\":\"a753c75f\",\"path\":[\"parameters\", \"direct_hire\"]}')}"
)
ET_ARRAY_LHS = '=["ET1", "ET2", "ET3", "ET8"]'
ET_RHS = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\","
    "\"line\":\"a753c75f\",\"path\":[\"parameters\", \"employment_type_id\"]}')}"
)
LIST_SIZE_LHS = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c556d2b4\","
    "\"path\":[\"list_items\", {\"path_element_type\": \"size\"}]}')}"
)
FOREACH_SOURCE = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"8c579c0a\","
    "\"path\":[\"rows\"]}')}"
)
STATUS_LHS = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"47a5b050\","
    "\"path\":[\"status\"]}')}"
)
INACTIVE_STOP_REASON = (
    "Inactive app evaluted: #{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\","
    "\"line\":\"47a5b050\",\"path\":[\"app_name\"]}')}"
)
CATCH_STOP_REASON = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"3b0db497\","
    "\"path\":[\"message\"]}')}"
)
RETURN_APPS_MAPPING = {
    "____source": (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\","
        "\"line\":\"a140d0a9\",\"path\":[\"list_items\"]}')}"
    ),
    "app_id": (
        "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"a140d0a9\","
        "\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"app_id\"]}')"
        ".presence or nil"
    ),
    "app_name": (
        "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"a140d0a9\","
        "\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"app_name\"]}')"
        ".presence or nil"
    ),
}
FOREACH_INSERT_ITEM = {
    "app_id": (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"47a5b050\","
        "\"path\":[\"app_id\"]}')}"
    ),
    "app_name": (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"47a5b050\","
        "\"path\":[\"app_name\"]}')}"
    ),
}
EXPECTED_STOP_STEPS: list[int] = [13, 17]


def validate_116263482(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    schema_json = str((raw.get("input") or {}).get("parameters_schema_json") or "")
    if '"name":"direct_hire"' not in schema_json or '"name":"employment_type_id"' not in schema_json:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter schema changed")
    actions = _collect_keyword(raw, "action")
    actual = [(a.get("provider"), a.get("name"), a.get("as")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    insert_default = _input(actions[2])
    if insert_default.get("list_item") != {"app_id": "A121"} or not str(
        insert_default.get("name") or ""
    ).endswith(":c556d2b4"):
        raise RuntimeError(f"recipe {RECIPE_ID} Default App IDs insert changed: {insert_default}")
    declare_variable = _input(actions[3])
    where_clause = ((declare_variable.get("variables") or {}).get("data") or {}).get("where_clause")
    if where_clause != WHERE_CLAUSE_FORMULA:
        raise RuntimeError(f"recipe {RECIPE_ID} where_clause formula changed: {where_clause!r}")
    search_input = _input(actions[4])
    if search_input.get("sql") != APP_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} APP SQL changed: {search_input.get('sql')!r}")
    if str(search_input.get("limit") or "") != "50000":
        raise RuntimeError(f"recipe {RECIPE_ID} APP query limit changed")
    insert_final = _input(actions[5])
    if insert_final.get("list_item") != FOREACH_INSERT_ITEM or not str(
        insert_final.get("name") or ""
    ).endswith(":a140d0a9"):
        raise RuntimeError(f"recipe {RECIPE_ID} Final Apps List insert changed: {insert_final}")
    return_input = _input(actions[6])
    if (return_input.get("result") or {}).get("apps") != RETURN_APPS_MAPPING:
        raise RuntimeError(f"recipe {RECIPE_ID} return_result apps mapping changed: {return_input}")
    ifs = {node.get("number"): _single_condition(node) for node in _collect_keyword(raw, "if")}
    if sorted(ifs) != [5, 6, 8, 12]:
        raise RuntimeError(f"recipe {RECIPE_ID} IF steps changed: {sorted(ifs)}")
    if ifs[5] != (DIRECT_HIRE_LHS, "is_true", ""):
        raise RuntimeError(f"recipe {RECIPE_ID} IF5 changed: {ifs[5]}")
    if ifs[6] != (ET_ARRAY_LHS, "contains", ET_RHS):
        raise RuntimeError(f"recipe {RECIPE_ID} IF6 changed: {ifs[6]}")
    if ifs[8] != (LIST_SIZE_LHS, "greater_than", "0"):
        raise RuntimeError(f"recipe {RECIPE_ID} IF8 changed: {ifs[8]}")
    if ifs[12] != (STATUS_LHS, "not_equals_to", "Active"):
        raise RuntimeError(f"recipe {RECIPE_ID} IF12 changed: {ifs[12]}")
    foreachs = _collect_keyword(raw, "foreach")
    if len(foreachs) != 1 or foreachs[0].get("as") != "47a5b050":
        raise RuntimeError(f"recipe {RECIPE_ID} foreach changed")
    if _input(foreachs[0]).get("source") != FOREACH_SOURCE or foreachs[0].get("repeat_mode") != "simple":
        raise RuntimeError(f"recipe {RECIPE_ID} foreach source changed")
    stops = _collect_keyword(raw, "stop")
    if [stop.get("number") for stop in stops] != EXPECTED_STOP_STEPS:
        raise RuntimeError(f"recipe {RECIPE_ID} stop steps changed: {stops}")
    for stop, reason in zip(stops, (INACTIVE_STOP_REASON, CATCH_STOP_REASON)):
        stop_input = _input(stop)
        if str(stop_input.get("stop_with_error") or "") != "true" or stop_input.get("stop_reason") != reason:
            raise RuntimeError(f"recipe {RECIPE_ID} stop step {stop.get('number')} changed: {stop_input}")
    catches = _collect_keyword(raw, "catch")
    if len(catches) != 1 or catches[0].get("as") != "3b0db497" or str(
        _input(catches[0]).get("max_retry_count") or ""
    ) != "0":
        raise RuntimeError(f"recipe {RECIPE_ID} catch block changed")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": [
            {
                "number": action.get("number"),
                "provider": action.get("provider"),
                "name": action.get("name"),
                "as": action.get("as"),
            }
            for action in actions
        ],
    }


def seed_116263482(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_116263482(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input requires a parameters object")
    if not isinstance(parameters.get("direct_hire"), bool):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input requires boolean parameters.direct_hire")
    if not str(parameters.get("employment_type_id") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger input requires a non-empty parameters.employment_type_id"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    snowflake_seed = seed_in.get("snowflake_live")
    _require_snowflake_tables(RECIPE_ID, snowflake_seed, [APP_TABLE])
    provision = ctx.tools.call("harness.snowflake_live.seed_tables", {"snowflake": snowflake_seed})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if isinstance(data.get("expect"), dict):
        out["expect"] = deepcopy(data["expect"])
    for key, value in seed_in.items():
        if key == "snowflake_live":
            continue
        if isinstance(value, dict):
            out[str(key)] = deepcopy(value)
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    for key in ("force_action_error", "job_context"):
        if isinstance(data.get(key), dict):
            out[key] = deepcopy(data[key])
    return attach_variant(out, ctx)


def run_116263482(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_116263482(raw)
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    snowflake_cleanup: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        if isinstance(seed.get("snowflake_live"), dict):
            snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "cleanup_response": {"snowflake_live": snowflake_cleanup},
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_116263482(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_snowflake_tables(recipe_id: str, snowflake_seed: Any, tables: list[str]) -> None:
    if not isinstance(snowflake_seed, dict) or not isinstance(snowflake_seed.get("tables"), dict):
        raise RuntimeError(f"recipe {recipe_id} requires seed.snowflake_live.tables")
    for table in tables:
        spec = snowflake_seed["tables"].get(table)
        if not isinstance(spec, dict):
            raise RuntimeError(
                f"recipe {recipe_id} seed must define snowflake_live.tables[{table!r}] explicitly"
            )
        columns = spec.get("columns")
        if not isinstance(columns, dict) or not columns or not all(
            isinstance(kind, str) and kind.strip() for kind in columns.values()
        ):
            raise RuntimeError(
                f"recipe {recipe_id} snowflake_live table {table} must declare explicit column types"
            )
        rows = spec.get("rows")
        if not isinstance(rows, list):
            raise RuntimeError(
                f"recipe {recipe_id} snowflake_live table {table} must declare rows (may be empty)"
            )
        lower_columns = {str(name).strip().lower() for name in columns}
        for row in rows:
            if not isinstance(row, dict):
                raise RuntimeError(f"recipe {recipe_id} snowflake_live table {table} rows must be objects")
            extra = {str(key).strip().lower() for key in row} - lower_columns
            if extra:
                raise RuntimeError(
                    f"recipe {recipe_id} snowflake_live table {table} row uses undeclared columns: {sorted(extra)}"
                )


def _collect_keyword(node: dict[str, Any], keyword: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == keyword and not child.get("skip"):
            found.append(child)
        found.extend(_collect_keyword(child, keyword))
    return found


def _input(node: dict[str, Any]) -> dict[str, Any]:
    value = node.get("input")
    return value if isinstance(value, dict) else {}


def _single_condition(node: dict[str, Any]) -> tuple[str, str, str]:
    conditions = _input(node).get("conditions")
    if not isinstance(conditions, list) or len(conditions) != 1 or not isinstance(conditions[0], dict):
        raise RuntimeError(f"recipe {RECIPE_ID} IF step {node.get('number')} is not a single condition")
    condition = conditions[0]
    return (
        str(condition.get("lhs") or ""),
        str(condition.get("operand") or ""),
        str(condition.get("rhs") or ""),
    )


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("snowflake_live"), dict):
        out.update(ctx.tools.call("harness.snowflake.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
