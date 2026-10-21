from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_100956844


RECIPE_ID = "100956844"
SEED_TYPE = "recipe_function_snowflake_role_router_variant"
TRACK = "workato_recipe_function_snowflake_role_router"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
# The one logical live table, referenced by the recipe under TWO spellings.
# BOTH must be registered as snowflake_live seed keys with an IDENTICAL spec:
# _parts() maps each to <SNOWFLAKE_DATABASE>.SNOWFLAKE.USER_ROLE_MAPPING (the
# same physical table), and _rewrite_sql only rewrites REGISTERED spellings --
# dotted 2-part names are not covered by the bare-name fallback. Live-probe
# note (2026-07-07): an UNREGISTERED 'snowflake.user_role_mapping' does NOT
# fail live -- the session database makes the un-rewritten 2-part reference
# resolve to the same seeded table -- so registration of both spellings is a
# determinism requirement, not an error-avoidance one, and the catch branch
# cannot be reached by omitting a spelling (it is reached via
# force_action_error instead).
TABLE_SPELLING_3PART = "workato_business_systems.snowflake.user_role_mapping"
TABLE_SPELLING_2PART = "snowflake.user_role_mapping"
TABLE_COLUMNS = (
    "SNOWFLAKE_ROLE",
    "TEAM_ID",
    "DEPARTMENT_ID",
    "TYPE",
    "ACTIVE",
    "CREATED_AT",
    "MODIFIED_AT",
)
# Callable recipe function (trigger as b42ceda3; parameters team_id /
# department_id / role_id -- role_id is declared but never dereferenced).
# Body wrapped in TRY (step 2):
#   declare_variable 80adce7c role_id (schema only -> nil)
#   run_custom_sql ef0f23d9: team-specific lookup (3-part spelling,
#     team_id + department_id + type='Team' literals interpolated)
#   IF ef0f23d9.rows.size > 0:
#     update_variables 05963c6a role_id = first row's snowflake_role
#   ELSE:
#     run_custom_sql c8e2fd08: department fallback (2-part spelling,
#       department_id + type='Department')
#     update_variables eaa07831 role_id = first row's snowflake_role
#       (MISSING -> None when the fallback also returns zero rows)
#   return_result a0ddfd71 {role_id: variable .presence or nil}
# CATCH (step 11, as 4dc92ee0, max_retry_count 0) -> STOP step 12 with error,
#   stop_reason = catch message.
TEAM_SQL = (
    "select * \nfrom workato_business_systems.snowflake.user_role_mapping\nwhere team_id = "
    "'#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"b42ceda3\","
    "\"path\":[\"parameters\", \"team_id\"]}')}' and department_id = "
    "'#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"b42ceda3\","
    "\"path\":[\"parameters\", \"department_id\"]}')}' and type = 'Team'"
)
DEPARTMENT_SQL = (
    "select * \nfrom snowflake.user_role_mapping\nwhere department_id = "
    "'#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"b42ceda3\","
    "\"path\":[\"parameters\", \"department_id\"]}')}' and type = 'Department'"
)
TEAM_ROLE_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"ef0f23d9\","
    "\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"snowflake_role\"]}')}"
)
DEPARTMENT_ROLE_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"c8e2fd08\","
    "\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"snowflake_role\"]}')}"
)
ROWS_SIZE_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"ef0f23d9\","
    "\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}"
)
RETURN_ROLE_FORMULA = (
    "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"80adce7c\","
    "\"path\":[\"role_id\"]}').presence or nil"
)
CATCH_STOP_REASON = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"4dc92ee0\","
    "\"path\":[\"message\"]}')}"
)
VARIABLE_TARGET_SUFFIX = ":80adce7c:role_id"
EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("workato_variable", "declare_variable", "80adce7c"),
    ("snowflake", "run_custom_sql", "ef0f23d9"),
    ("workato_variable", "update_variables", "05963c6a"),
    ("snowflake", "run_custom_sql", "c8e2fd08"),
    ("workato_variable", "update_variables", "eaa07831"),
    ("workato_recipe_function", "return_result", "a0ddfd71"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "snowflake.run_custom_sql",
    "workato_runtime.update_variables",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "workato_recipe_function.return_result",
]


def validate_100956844(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    schema_json = str((raw.get("input") or {}).get("parameters_schema_json") or "")
    for name in ("team_id", "department_id", "role_id"):
        if f'"name":"{name}"' not in schema_json:
            raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter schema changed")
    actions = _collect_keyword(raw, "action")
    actual = [(a.get("provider"), a.get("name"), a.get("as")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    declare_input = _input(actions[0])
    declare_schema = str((declare_input.get("variables") or {}).get("schema") or "")
    if '"name":"role_id"' not in declare_schema or (declare_input.get("variables") or {}).get("data"):
        raise RuntimeError(f"recipe {RECIPE_ID} role_id declaration changed: {declare_input}")
    team_sql_input = _input(actions[1])
    if team_sql_input.get("sql") != TEAM_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} team SQL changed: {team_sql_input.get('sql')!r}")
    team_update = _input(actions[2])
    if team_update.get("role_id") != TEAM_ROLE_PILL or not str(
        team_update.get("name") or ""
    ).endswith(VARIABLE_TARGET_SUFFIX):
        raise RuntimeError(f"recipe {RECIPE_ID} team role update changed: {team_update}")
    department_sql_input = _input(actions[3])
    if department_sql_input.get("sql") != DEPARTMENT_SQL:
        raise RuntimeError(
            f"recipe {RECIPE_ID} department SQL changed: {department_sql_input.get('sql')!r}"
        )
    department_update = _input(actions[4])
    if department_update.get("role_id") != DEPARTMENT_ROLE_PILL or not str(
        department_update.get("name") or ""
    ).endswith(VARIABLE_TARGET_SUFFIX):
        raise RuntimeError(f"recipe {RECIPE_ID} department role update changed: {department_update}")
    return_input = _input(actions[5])
    if (return_input.get("result") or {}).get("role_id") != RETURN_ROLE_FORMULA:
        raise RuntimeError(f"recipe {RECIPE_ID} return_result mapping changed: {return_input}")
    ifs = _collect_keyword(raw, "if")
    if len(ifs) != 1 or ifs[0].get("number") != 5:
        raise RuntimeError(f"recipe {RECIPE_ID} IF steps changed")
    conditions = _input(ifs[0]).get("conditions")
    if (
        not isinstance(conditions, list)
        or len(conditions) != 1
        or conditions[0].get("lhs") != ROWS_SIZE_PILL
        or conditions[0].get("operand") != "greater_than"
        or conditions[0].get("rhs") != "0"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} IF condition changed: {conditions}")
    elses = _collect_keyword(raw, "else")
    if len(elses) != 1 or elses[0].get("number") != 7:
        raise RuntimeError(f"recipe {RECIPE_ID} ELSE block changed")
    catches = _collect_keyword(raw, "catch")
    if (
        len(catches) != 1
        or catches[0].get("as") != "4dc92ee0"
        or str(_input(catches[0]).get("max_retry_count") or "") != "0"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} catch block changed")
    stops = _collect_keyword(raw, "stop")
    if (
        len(stops) != 1
        or stops[0].get("number") != 12
        or str(_input(stops[0]).get("stop_with_error") or "") != "true"
        or _input(stops[0]).get("stop_reason") != CATCH_STOP_REASON
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} stop step changed: {stops}")
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


def seed_100956844(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_100956844(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input requires a parameters object")
    for name in ("team_id", "department_id"):
        if not str(parameters.get(name) or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger input requires a non-empty parameters.{name}"
            )
    if "role_id" not in parameters:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger input must carry parameters.role_id "
            "(declared required by the function schema, even though unused)"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    snowflake_seed = seed_in.get("snowflake_live")
    _require_snowflake_tables(snowflake_seed)
    expect = data.get("expect")
    if not isinstance(expect, dict) or "stopped" not in expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare expect.stopped")
    provision = ctx.tools.call("harness.snowflake_live.seed_tables", {"snowflake": snowflake_seed})
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


def run_100956844(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_100956844(raw)
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
    result["verifier"] = verify_100956844(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_snowflake_tables(snowflake_seed: Any) -> None:
    if not isinstance(snowflake_seed, dict) or not isinstance(snowflake_seed.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.snowflake_live.tables")
    tables = snowflake_seed["tables"]
    for spelling in (TABLE_SPELLING_3PART, TABLE_SPELLING_2PART):
        if not isinstance(tables.get(spelling), dict):
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed must register BOTH table spellings; missing {spelling!r}"
            )
    spec_3part = tables[TABLE_SPELLING_3PART]
    spec_2part = tables[TABLE_SPELLING_2PART]
    if spec_3part != spec_2part:
        raise RuntimeError(
            f"recipe {RECIPE_ID} both table spellings map to the same live table and must carry "
            "IDENTICAL specs (columns + rows) for deterministic create-or-replace seeding"
        )
    for spelling, spec in ((TABLE_SPELLING_3PART, spec_3part), (TABLE_SPELLING_2PART, spec_2part)):
        columns = spec.get("columns")
        if not isinstance(columns, dict) or tuple(columns) != TABLE_COLUMNS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} snowflake_live table {spelling} must declare exactly the "
                f"columns {TABLE_COLUMNS} (got {tuple(columns) if isinstance(columns, dict) else columns})"
            )
        rows = spec.get("rows")
        if not isinstance(rows, list):
            raise RuntimeError(
                f"recipe {RECIPE_ID} snowflake_live table {spelling} must declare rows (may be empty)"
            )
        for row in rows:
            if not isinstance(row, dict):
                raise RuntimeError(f"recipe {RECIPE_ID} snowflake_live rows must be objects")
            extra = {str(key).strip().upper() for key in row} - set(TABLE_COLUMNS)
            if extra:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} snowflake_live table {spelling} row uses undeclared "
                    f"columns: {sorted(extra)}"
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
