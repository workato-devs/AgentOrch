from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_108445187


RECIPE_ID = "108445187"
SEED_TYPE = "api_platform_snowflake_workspaces_typeahead_variant"
TRACK = "live_snowflake_api_workspaces_typeahead"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "458af9a1"
WORKSPACE_TABLE = "product.workato_usage.workspace_dim"
# API endpoint recipe (trigger as 458af9a1; request.typeAhead optional,
# request.accountID required). Body wrapped in TRY (step 2):
#   IF (step 3): request.typeAhead blank ->
#     4  snowflake.search_rows_sql 5a86b1ad: workspace_dim query WITH the
#        "lower(concat(workspace_name, workspace_email)) like '%<typeAhead>%'"
#        clause -- faithful author quirk: the LIKE-filtered SQL runs on the
#        BLANK branch, where the missing typeAhead pill interpolates '' and
#        like '%%' matches every non-null concat (probe-verified). orderby
#        input 'task_limit DESC nulls last' is appended as ORDER BY by the
#        executor (engine fix 4d133d1e); limit 200, offset 0.
#     5  workato_api_platform.return_response 426432f0: 200,
#        response.workspaces ____source-mapped over rows
#        ({workspace_id, workspace: "<name> (<email>)"})
#   ELSE (step 6): typeAhead present ->
#     7  snowflake.search_rows_sql d3755b75: same query WITHOUT the like
#        clause (typeAhead is never used -- replayed faithfully)
#     8  workato_api_platform.return_response c6f3354f: 200, same mapping
# CATCH (step 9, as c96801ed, max_retry_count 0):
#   10 workato_api_platform.return_response 1c0a9f98: 500, no body
# Snowflake runs LIVE: the seed registers the table under the exact 3-part
# key 'product.workato_usage.workspace_dim' (recipe_116263482 precedent).
# The 'nulls last' ordering is provable by seeding a NULL task_limit row.
# The catch branch is exercised via seed.force_action_error on step 5a86b1ad.
_SQL_HEAD = (
    "select wd.workspace_name, wd.workspace_email, wd.workspace_id, wd.task_limit\n"
    "from product.workato_usage.workspace_dim wd\n"
    "where wd.sales_account_id = "
    "'#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\","
    "\"line\":\"458af9a1\",\"path\":[\"request\", \"accountID\"]}')}'\n"
    "and wd.is_latest\n"
)
_SQL_TAIL = (
    "and not wd.is_deleted\n"
    "and wd.is_paid_workspace\n"
    "and not wd.is_internal"
)
SQL_IF = _SQL_HEAD + (
    "and lower(concat(wd.workspace_name, wd.workspace_email)) like "
    "'%#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\","
    "\"line\":\"458af9a1\",\"path\":[\"request\", \"typeAhead\"]}')}%'\n"
) + _SQL_TAIL
SQL_ELSE = _SQL_HEAD + _SQL_TAIL
ORDERBY = "task_limit DESC nulls last"
IF_LHS = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\","
    "\"line\":\"458af9a1\",\"path\":[\"request\", \"typeAhead\"]}')}"
)


def _workspaces_mapping(line: str) -> dict[str, str]:
    def pill(field: str) -> str:
        return (
            "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\","
            "\"line\":\"" + line + "\",\"path\":[\"rows\", "
            "{\"path_element_type\": \"current_item\"}, \"" + field + "\"]}')}"
        )

    return {
        "____source": (
            "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\","
            "\"line\":\"" + line + "\",\"path\":[\"rows\"]}')}"
        ),
        "workspace": pill("workspace_name") + " (" + pill("workspace_email") + ")",
        "workspace_id": pill("workspace_id"),
    }


EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("snowflake", "search_rows_sql", "5a86b1ad"),
    ("workato_api_platform", "return_response", "426432f0"),
    ("snowflake", "search_rows_sql", "d3755b75"),
    ("workato_api_platform", "return_response", "c6f3354f"),
    ("workato_api_platform", "return_response", "1c0a9f98"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_api_platform.return_response",
]


def validate_108445187(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed")
    request_schema = str(((raw.get("input") or {}).get("request") or {}).get("schema") or "")
    if '"name":"typeAhead"' not in request_schema or '"name":"accountID"' not in request_schema:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger request schema changed")
    actions = _collect_keyword(raw, "action")
    actual = [(a.get("provider"), a.get("name"), a.get("as")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    for action, sql in ((actions[0], SQL_IF), (actions[2], SQL_ELSE)):
        search_input = _input(action)
        if search_input.get("sql") != sql:
            raise RuntimeError(
                f"recipe {RECIPE_ID} step {action.get('as')} SQL changed: {search_input.get('sql')!r}"
            )
        if str(search_input.get("orderby") or "") != ORDERBY:
            raise RuntimeError(f"recipe {RECIPE_ID} step {action.get('as')} orderby changed")
        if str(search_input.get("limit") or "") != "200" or str(search_input.get("offset") or "") != "0":
            raise RuntimeError(f"recipe {RECIPE_ID} step {action.get('as')} limit/offset changed")
    for action, line in ((actions[1], "5a86b1ad"), (actions[3], "d3755b75")):
        response_input = _input(action)
        if str(response_input.get("http_status_code") or "") != "200":
            raise RuntimeError(f"recipe {RECIPE_ID} step {action.get('as')} status changed")
        if (response_input.get("response") or {}).get("workspaces") != _workspaces_mapping(line):
            raise RuntimeError(f"recipe {RECIPE_ID} step {action.get('as')} workspaces mapping changed")
    catch_input = _input(actions[4])
    if str(catch_input.get("http_status_code") or "") != "500" or "response" in catch_input:
        raise RuntimeError(f"recipe {RECIPE_ID} catch response changed: {catch_input}")
    ifs = _collect_keyword(raw, "if")
    if len(ifs) != 1 or _single_condition(ifs[0]) != (IF_LHS, "blank", ""):
        raise RuntimeError(f"recipe {RECIPE_ID} IF step 3 changed")
    tries = _collect_keyword(raw, "try")
    if len(tries) != 1 or tries[0].get("number") != 2:
        raise RuntimeError(f"recipe {RECIPE_ID} try block changed")
    catches = _collect_keyword(raw, "catch")
    if (
        len(catches) != 1
        or catches[0].get("as") != "c96801ed"
        or str(_input(catches[0]).get("max_retry_count") or "") != "0"
        or str(_input(catches[0]).get("retry_interval") or "") != "2"
    ):
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


def seed_108445187(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_108445187(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    snowflake_seed = seed_in.get("snowflake_live")
    _require_snowflake_tables(RECIPE_ID, snowflake_seed, [WORKSPACE_TABLE])
    provision = ctx.tools.call("harness.snowflake_live.seed_tables", {"snowflake": snowflake_seed})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    if not isinstance(data.get("expect"), dict) or not isinstance(
        data["expect"].get("api_response"), dict
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must declare expect.api_response "
            "(http_status_code + response) explicitly"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(data["expect"]),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    for key, value in seed_in.items():
        if key == "snowflake_live":
            continue
        if isinstance(value, dict):
            out[str(key)] = deepcopy(value)
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    return attach_variant(out, ctx)


def run_108445187(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_108445187(raw)
    trigger = seed.get("trigger")
    if not isinstance(trigger, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing trigger object")
    _require_trigger(trigger)
    expect = seed.get("expect") if isinstance(seed.get("expect"), dict) else {}
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
            "trigger": trigger,
            "track": seed.get("track"),
            "expect": expect,
            "force_action_error": deepcopy(seed.get("force_action_error"))
            if isinstance(seed.get("force_action_error"), dict)
            else None,
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
    result["verifier"] = verify_108445187(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger(trigger: dict[str, Any]) -> None:
    request = trigger.get("request")
    if not isinstance(request, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input requires a request object")
    if not str(request.get("accountID") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} trigger request.accountID must be non-empty")
    if "typeAhead" in request and not isinstance(request.get("typeAhead"), str):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger request.typeAhead must be a string when present")


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
