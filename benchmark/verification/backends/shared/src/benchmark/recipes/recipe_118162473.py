from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_118162473


RECIPE_ID = "118162473"
SEED_TYPE = "api_platform_business_unit_processes_snowflake_query_variant"
TRACK = "benchmark_final_state"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "751ec271"
SEARCH_STEP_AS = "60b10d1f"
SUCCESS_RESPONSE_AS = "83954e0e"
CATCH_AS = "2da14745"
ERROR_RESPONSE_AS = "57671952"
STOP_AS = "8ce124ba"

# Structural sibling of family head 118162472 (same try/catch/return
# skeleton). Its byte-twin 117564458 is OUTSIDE batch 06 (unbuilt). Shape:
#   workato_api_platform.receive_request 751ec271 (request schema pins ONE
#   required string param businessUnitCode; trigger seed is exactly
#   {"request": {"businessUnitCode": ...}})
#   TRY(2)> snowflake.search_rows_sql 60b10d1f (LIVE): 14-column SELECT from
#     BUSINESS_PROCESS_DASHBOARD WHERE BU_CODE = :businessUnitCode (bind
#     param rendered from the trigger request pill; pyformat rewrite in the
#     live client) ORDER BY PROCESS_HIERARCHICAL_LEVEL, PROCESS_NAME.
#     The bind WHERE is the data branch lever: match vs zero rows.
#   return_response 83954e0e: 200 {businessProcesses: ____source over rows}.
#     Six interpolated pills (id/businessUnitCode/name/hierarchicalLevel/
#     hierarchicalLevelName/status; single-pill fullmatch keeps native types)
#     plus EIGHT `=_dp(...).presence || nil` formula pills (parentId/
#     currentAutomationLevel/targetAutomationLevel/workatoIntegrationLevel/
#     currentAIInvolvementLevel/aiImpactLevel/projectPageUrl/
#     completionPercentage) — Rails presence parity: NULL and '' -> null,
#     0 STAYS 0 (probe-verified).
#   CATCH 2da14745 (max_retry_count 0)> return_response 57671952: 400
#     {error: catch message pill}; stop 8ce124ba is DEAD (return_response is
#     terminal — catch variants expect executed_action_count 1, no stop row).
# LOAD-BEARING seed typing (triage-proven): COMPLETION_PERCENTAGE is seeded
# as a FLOAT column so a fractional pin (45.5) survives — NUMBER(38,0)
# rounds on insert (45.5 -> 46). Level columns are NUMBER so hierarchical/
# automation levels read back as native ints.
# Backends: Snowflake LIVE (seeder create-or-replace, runner drops in
# finally, READ-ONLY — snapshot equality pinned); api_platform is the
# Workato-internal mock. Physical table name is shared across the
# AUTOMATION_COMPASS family — never run family variants concurrently.
DASHBOARD_TABLE = "AUTOMATION_COMPASS.BUSINESS_PROCESS_DASHBOARD"
DASHBOARD_COLUMNS = {
    "PROCESS_ID": "string",
    "BU_CODE": "string",
    "PROCESS_NAME": "string",
    "PROCESS_HIERARCHICAL_LEVEL": "number",
    "PROCESS_HIERARCHICAL_LEVEL_NAME": "string",
    "PARENT_PROCESS_ID": "string",
    "CURRENT_AUTOMATION_LEVEL": "number",
    "TARGET_AUTOMATION_LEVEL": "number",
    "WORKATO_INTEGRATION_LEVEL": "number",
    "AI_INVOLVEMENT_LEVEL": "number",
    "AI_IMPACT_LEVEL": "number",
    "STATUS": "string",
    "PROJECT_PAGE_URL": "string",
    "COMPLETION_PERCENTAGE": "float",
}
# Response non-optional fields: every seeded row must fill these; the rest
# may be omitted (NULL) to exercise the presence||nil -> null path.
REQUIRED_ROW_KEYS = (
    "PROCESS_ID",
    "BU_CODE",
    "PROCESS_NAME",
    "PROCESS_HIERARCHICAL_LEVEL",
    "PROCESS_HIERARCHICAL_LEVEL_NAME",
    "STATUS",
)
RAW_SQL = (
    "SELECT \n  PROCESS_ID AS ID,\n  BU_CODE AS BUSINESS_UNIT_CODE,\n"
    "  PROCESS_NAME AS NAME,\n  PROCESS_HIERARCHICAL_LEVEL AS HIERARCHICAL_LEVEL,\n"
    "  PROCESS_HIERARCHICAL_LEVEL_NAME AS HIERARCHICAL_LEVEL_NAME,\n"
    "  PARENT_PROCESS_ID AS PARENT_ID,\n"
    "  CURRENT_AUTOMATION_LEVEL AS CURRENT_AUTOMATION_LEVEL,\n"
    "  TARGET_AUTOMATION_LEVEL AS TARGET_AUTOMATION_LEVEL,\n"
    "  WORKATO_INTEGRATION_LEVEL AS WORKATO_INTEGRATION_LEVEL,\n"
    "  AI_INVOLVEMENT_LEVEL AS CURRENT_AI_INVOLVEMENT_LEVEL,\n"
    "  AI_IMPACT_LEVEL AS AI_IMPACT_LEVEL,\n  STATUS AS STATUS,\n"
    "  PROJECT_PAGE_URL AS PROJECT_PAGE_URL,\n"
    "  COMPLETION_PERCENTAGE AS COMPLETION_PERCENTAGE\n"
    "FROM \n  AUTOMATION_COMPASS.BUSINESS_PROCESS_DASHBOARD\n"
    "WHERE \n  BU_CODE = :businessUnitCode\n"
    "ORDER BY \n  PROCESS_HIERARCHICAL_LEVEL, PROCESS_NAME"
)
TRIGGER_REQUEST_SCHEMA = (
    "[{\"name\":\"businessUnitCode\",\"type\":\"string\",\"optional\":false,"
    "\"label\":\"Business Unit Code\",\"control_type\":\"text\"}]"
)
BIND_PARAMETER_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\","
    "\"line\":\"" + TRIGGER_AS + "\",\"path\":[\"request\", \"businessUnitCode\"]}')}"
)
RESPONSE_ARRAY_KEY = "businessProcesses"
RESPONSE_MAPPING_KEYS = [
    "____source",
    "aiImpactLevel",
    "businessUnitCode",
    "completionPercentage",
    "currentAIInvolvementLevel",
    "currentAutomationLevel",
    "hierarchicalLevel",
    "hierarchicalLevelName",
    "id",
    "name",
    "parentId",
    "projectPageUrl",
    "status",
    "targetAutomationLevel",
    "workatoIntegrationLevel",
]
SOURCE_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\","
    "\"line\":\"" + SEARCH_STEP_AS + "\",\"path\":[\"rows\"]}')}"
)
CATCH_MESSAGE_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\","
    "\"line\":\"" + CATCH_AS + "\",\"path\":[\"message\"]}')}"
)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (SEARCH_STEP_AS, "snowflake", "search_rows_sql"),
    (SUCCESS_RESPONSE_AS, "workato_api_platform", "return_response"),
    (ERROR_RESPONSE_AS, "workato_api_platform", "return_response"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = list(EXPECTED_RAW_TOOLS)
SUCCESS_TOOLS = ["snowflake.search_rows_sql", "workato_api_platform.return_response"]
CATCH_TOOLS = ["workato_api_platform.return_response"]
REQUIRED_EXPECT_KEYS = ("executed_action_count", "tools", "tool_expectations", "return_value")
VALUE_KEYS = (
    "args_contains",
    "result_count",
    "response_contains",
    "result_contains",
    "created",
    "http_status_code",
    "text_fragments",
    "options_contains",
)


def validate_118162473(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    request = (raw.get("input") or {}).get("request") or {}
    if request.get("schema") != TRIGGER_REQUEST_SCHEMA:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger request schema changed: {request.get('schema')!r}")
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    search_input = actions[0].get("input") or {}
    if search_input.get("sql") != RAW_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake SQL changed")
    if str(search_input.get("limit") or "") != "50000":
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake limit changed")
    if str(search_input.get("offset") or "") != "0":
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake offset changed")
    parameters = search_input.get("parameters") or {}
    if (parameters.get("data") or {}) != {"businessUnitCode": BIND_PARAMETER_PILL}:
        raise RuntimeError(f"recipe {RECIPE_ID} bind parameter mapping changed: {parameters!r}")
    success_input = actions[1].get("input") or {}
    if str(success_input.get("http_status_code") or "") != "200":
        raise RuntimeError(f"recipe {RECIPE_ID} success response status changed")
    mapping = (success_input.get("response") or {}).get(RESPONSE_ARRAY_KEY)
    if not isinstance(mapping, dict) or sorted(mapping.keys()) != sorted(RESPONSE_MAPPING_KEYS):
        raise RuntimeError(f"recipe {RECIPE_ID} success response mapping changed: {mapping!r}")
    if mapping.get("____source") != SOURCE_PILL:
        raise RuntimeError(f"recipe {RECIPE_ID} response ____source pill changed")
    presence_fields = (
        "parentId",
        "currentAutomationLevel",
        "targetAutomationLevel",
        "workatoIntegrationLevel",
        "currentAIInvolvementLevel",
        "aiImpactLevel",
        "projectPageUrl",
        "completionPercentage",
    )
    for field in presence_fields:
        text = str(mapping.get(field) or "")
        if not (text.startswith("=_dp(") and text.endswith(".presence || nil")):
            raise RuntimeError(
                f"recipe {RECIPE_ID} response field {field} lost its presence||nil formula: {text!r}"
            )
    error_input = actions[2].get("input") or {}
    if str(error_input.get("http_status_code") or "") != "400":
        raise RuntimeError(f"recipe {RECIPE_ID} error response status changed")
    if error_input.get("response") != {"error": CATCH_MESSAGE_PILL}:
        raise RuntimeError(f"recipe {RECIPE_ID} error response body changed")
    stop = _find_node(raw, STOP_AS)
    if not isinstance(stop, dict) or stop.get("keyword") != "stop":
        raise RuntimeError(f"recipe {RECIPE_ID} trailing catch stop step missing")
    if str((stop.get("input") or {}).get("stop_with_error") or "") != "true":
        raise RuntimeError(f"recipe {RECIPE_ID} stop step no longer stop_with_error")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "snowflake_tables": [DASHBOARD_TABLE],
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


def seed_118162473(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118162473(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    force = data.get("force_action_error")
    expect = data.get("expect")
    _require_expect(expect, force)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
    }
    if force is not None:
        _require_catch_seed(seed_in, force)
    else:
        _require_try_seed(seed_in)
        provision = ctx.tools.call(
            "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
        )
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
        out["snowflake_live"] = deepcopy(provision["state"])
        out["snowflake_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_118162473(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118162473(raw)
    trigger = seed.get("trigger")
    if not isinstance(trigger, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing trigger object")
    _require_trigger(trigger)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    live = isinstance(seed.get("snowflake_live"), dict)
    if not live and not isinstance(seed.get("force_action_error"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed carries neither snowflake_live state nor a forced "
            "catch error — nothing to run"
        )
    raw_execution: dict[str, Any] | None = None
    initial_snapshot: dict[str, Any] = {}
    final_snapshot: dict[str, Any] = {}
    cleanup: dict[str, Any] | None = None
    try:
        initial_snapshot = _snapshot(ctx, live)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, live)
    finally:
        if live:
            cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    if live and not (cleanup or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake cleanup failed: {cleanup}")
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
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "cleanup_response": {"snowflake_live": cleanup},
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_118162473(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger(trigger: dict[str, Any]) -> None:
    request = trigger.get("request")
    if (
        sorted(trigger.keys()) != ["request"]
        or not isinstance(request, dict)
        or sorted(request.keys()) != ["businessUnitCode"]
        or not isinstance(request.get("businessUnitCode"), str)
        or not request["businessUnitCode"].strip()
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger must be exactly {{'request': "
            f"{{'businessUnitCode': <non-empty string>}}}}; got {trigger!r}"
        )


def _require_expect(expect: Any, force: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    tools = expect.get("tools")
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or not isinstance(tools, list) or len(items) != len(tools):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin every expected call"
        )
    for idx, item in enumerate(items):
        if not isinstance(item, dict) or item.get("tool") != tools[idx]:
            raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[{idx}] does not match tools")
        if not any(key in item for key in VALUE_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] carries no value-asserting key"
            )
    if force is not None:
        checks = (
            expect.get("executed_action_count") == 1,
            tools == CATCH_TOOLS,
            expect.get("return_value") == {"error": str((force or {}).get("error") or "")},
            items[0].get("http_status_code") == "400",
        )
        reason = (
            "catch variants run ONLY the 400 return_response (forced error fires before "
            "the snowflake adapter; the 400 response is terminal, the stop step is dead)"
        )
    else:
        checks = (
            expect.get("executed_action_count") == 2,
            tools == SUCCESS_TOOLS,
            isinstance(expect.get("return_value"), dict)
            and isinstance(expect["return_value"].get(RESPONSE_ARRAY_KEY), list)
            and sorted(expect["return_value"].keys()) == [RESPONSE_ARRAY_KEY],
            items[1].get("http_status_code") == "200",
            isinstance(items[0].get("args_contains"), dict)
            and isinstance(items[0]["args_contains"].get("parameters"), dict),
        )
        reason = (
            "success variants run search -> 200 response, pin the resolved bind "
            f"parameters and the exact {RESPONSE_ARRAY_KEY} body as return_value"
        )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with its branch ({reason}): {expect!r}"
        )


def _require_catch_seed(seed_in: dict[str, Any], force: Any) -> None:
    if not isinstance(force, dict) or str(force.get("step_as") or "") != SEARCH_STEP_AS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the catch is not naturally reachable: catch variants must "
            f"declare force_action_error.step_as == {SEARCH_STEP_AS!r}"
        )
    if not str(force.get("error") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error.error must be explicit")
    if seed_in != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch variants must seed NOTHING (the forced error fires "
            f"BEFORE the snowflake adapter — no live table may be provisioned); got "
            f"{sorted(seed_in.keys())}"
        )


def _require_try_seed(seed_in: dict[str, Any]) -> None:
    if sorted(seed_in.keys()) != ["snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} success variants must seed exactly the snowflake_live "
            f"section; got {sorted(seed_in.keys())}"
        )
    section = seed_in["snowflake_live"]
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the SQL uses no CURRENT_DATE/TIMESTAMP, so current_time is not allowed)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [DASHBOARD_TABLE]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{[DASHBOARD_TABLE]}"
        )
    rows = _require_table(DASHBOARD_TABLE, tables[DASHBOARD_TABLE], DASHBOARD_COLUMNS)
    if not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} {DASHBOARD_TABLE} rows must be NON-EMPTY — the no-match "
            "branch proves the bind WHERE bites via decoy rows, not an empty table"
        )
    seen_ids: set[str] = set()
    for idx, row in enumerate(rows):
        for key in REQUIRED_ROW_KEYS:
            if key not in row:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {DASHBOARD_TABLE} row {idx} must fill the "
                    f"non-optional response field column {key} (only presence||nil "
                    f"columns may be omitted); got {sorted(row.keys())}"
                )
        if row["PROCESS_ID"] in seen_ids:
            raise RuntimeError(f"recipe {RECIPE_ID} duplicate PROCESS_ID {row['PROCESS_ID']!r}")
        seen_ids.add(row["PROCESS_ID"])


def _require_table(name: str, spec: Any, columns: dict[str, str]) -> list[dict[str, Any]]:
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {name} spec must be exactly {{'columns': ..., 'rows': ...}}"
        )
    if spec["columns"] != columns:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {name} must declare exactly the columns {columns} "
            "(FLOAT completion keeps fractional pins exact; NUMBER levels stay ints)"
        )
    rows = spec["rows"]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {name} rows must be a list")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table {name} row {idx} must be an object")
        for key, value in row.items():
            if key not in columns:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {name} row {idx} has undeclared column {key!r}"
                )
            _require_column_value(name, idx, key, columns[key], value)
    return rows


def _require_column_value(table: str, idx: int, key: str, kind: str, value: Any) -> None:
    if kind in {"number", "integer"}:
        if isinstance(value, bool) or not isinstance(value, int):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {table} row {idx} column {key} must be an "
                f"integer (NUMBER(38,0) rounds fractional seeds); got {value!r}"
            )
        return
    if kind == "float":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {table} row {idx} column {key} must be numeric; "
                f"got {value!r}"
            )
        return
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {table} row {idx} column {key} must be a non-empty "
            f"string; got {value!r}"
        )


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _find_node(node: dict[str, Any], as_id: str) -> dict[str, Any] | None:
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if str(child.get("as") or "") == as_id:
            return child
        found = _find_node(child, as_id)
        if found is not None:
            return found
    return None


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
