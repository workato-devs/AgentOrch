from __future__ import annotations

import datetime
import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_119586008


RECIPE_ID = "119586008"
SEED_TYPE = "api_platform_chi_department_scorecard_variant"
TRACK = "workato_api_platform_chi_department_scorecard"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "464453de"
SQL1_AS = "28928828"
SQL2_AS = "58637f4a"
DEAD_SQL_AS = "213ea423"
CATCH_AS = "6d3b3e78"
CATCH_RETURN_AS = "9a3e3470"
SUCCESS_RETURN_AS = "e62afcce"
COMPOSITE_TABLE = "plg.chi_2024_temp_final_composite_wip_operational"
ADOPTION_TABLE = "plg.chi_2024_department_adoption_base_operational"

COMPOSITE_COLUMNS = {
    "ACCOUNT_ID": "string",
    "ACCOUNT_NAME": "string",
    "CALENDAR_DATE": "date",
    "CURRENT_ARR_USD": "number",
    "INDUSTRY": "string",
    "CAT_COMPANY_SIZE": "string",
    "IS_PAYING": "boolean",
    "CUST_TYPE": "string",
}
ADOPTION_COLUMNS = {
    "ACCOUNT_ID": "string",
    "CALENDAR_DATE": "date",
    "DEPARTMENT": "string",
    "PROCESS": "string",
    "SUB_PROCESS": "string",
}
KNOWN_DEPARTMENTS = (
    "finance and accounting",
    "it automations",
    "human resources",
    "revops",
    "customer support and operations",
    "data operations",
    "product and engineering",
)
RESPONSE_FIELDS = (
    "ACCOUNT_ID",
    "ACCOUNT_NAME",
    "CALENDAR_DATE",
    "CAT_COMPANY_SIZE",
    "CURRENT_ARR_USD",
    "INDUSTRY",
    "department_scores",
    "department_usecases",
)


_RAW_PIN_JSON = r"""{"as": "464453de", "block": [{"as": "", "block": [{"as": "28928828", "block": [], "input": {"output_schema": "[{\"control_type\":\"text\",\"label\":\"Max calendar date\",\"type\":\"string\",\"name\":\"max_calendar_date\"}]", "sql": "SELECT\n  MAX(CALENDAR_DATE) AS max_calendar_date\nFROM plg.chi_2024_temp_final_composite_wip_operational\nWHERE\n  CALENDAR_DATE <= '#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"464453de\",\"path\":[\"request\", \"date\"]}')}'", "update_only": "false"}, "keyword": "action", "name": "run_custom_sql", "number": 3, "provider": "snowflake", "skip": false}, {"as": "58637f4a", "block": [], "input": {"output_schema": "[{\"control_type\":\"text\",\"label\":\"Account ID\",\"type\":\"string\",\"name\":\"account_id\"},{\"control_type\":\"text\",\"label\":\"Account name\",\"type\":\"string\",\"name\":\"account_name\"},{\"control_type\":\"text\",\"label\":\"Calendar date\",\"type\":\"string\",\"name\":\"calendar_date\"},{\"control_type\":\"number\",\"label\":\"Current arr usd\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"current_arr_usd\"},{\"control_type\":\"text\",\"label\":\"Industry\",\"type\":\"string\",\"name\":\"industry\"},{\"control_type\":\"text\",\"label\":\"Cat company size\",\"type\":\"string\",\"name\":\"cat_company_size\"},{\"control_type\":\"text\",\"label\":\"Department scorecard\",\"type\":\"string\",\"name\":\"department_scorecard\"},{\"label\":\"department_usecases\",\"type\":\"string\",\"name\":\"department_usecases\",\"optional\":false,\"of\":\"object\",\"control_type\":\"text\"}]", "sql": "WITH account_info AS (\n  SELECT *\n  FROM plg.chi_2024_temp_final_composite_wip_operational\n  WHERE calendar_date = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"28928828\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"max_calendar_date\"]}')}'\n    AND account_id = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"464453de\",\"path\":[\"request\", \"account_id\"]}')}'\n    AND is_paying\n    AND cust_type = 'direct'\n),\n\nsubproc_list AS (\n  SELECT *\n  FROM plg.chi_2024_department_adoption_base_operational\n  WHERE calendar_date = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"28928828\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"max_calendar_date\"]}')}'\n    AND account_id = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"464453de\",\"path\":[\"request\", \"account_id\"]}')}'\n    AND sub_process != 'not conclusive'\n),\n\n-- For dictionary\nsubproc_agg AS (\n  SELECT\n    department,\n    process,\n    ARRAY_AGG(DISTINCT sub_process) AS sub_processes\n  FROM subproc_list\n  GROUP BY department, process\n),\n\nprocess_agg AS (\n  SELECT\n    department,\n    OBJECT_AGG(process, sub_processes) AS processes_by_dept\n  FROM subproc_agg\n  GROUP BY department\n),\n\n-- For scorecard\ndept_scorecard AS (\n  SELECT\n    a.account_id,\n    a.account_name,\n    a.calendar_date,\n    a.current_arr_usd,\n    a.industry,\n    a.cat_company_size,\n  \n    CONCAT(\n      'Finance & Accounting:', ROUND(SUM(CASE WHEN d.department = 'finance and accounting' THEN 1 ELSE 0 END) / 32 * 100), '%, ',\n      'IT:', ROUND(SUM(CASE WHEN d.department = 'it automations' THEN 1 ELSE 0 END) / 44 * 100), '%, ',\n      'Human Resources:', ROUND(SUM(CASE WHEN d.department = 'human resources' THEN 1 ELSE 0 END) / 45 * 100), '%, ',\n      'RevOps:', ROUND(SUM(CASE WHEN d.department = 'revops' THEN 1 ELSE 0 END) / 49 * 100), '%, ',\n      'CS Ops:', ROUND(SUM(CASE WHEN d.department = 'customer support and operations' THEN 1 ELSE 0 END) / 22 * 100), '%, ',\n      'Data Ops:', ROUND(SUM(CASE WHEN d.department = 'data operations' THEN 1 ELSE 0 END) / 8 * 100), '%, ',\n      'Product and Engineering:', ROUND(SUM(CASE WHEN d.department = 'product and engineering' THEN 1 ELSE 0 END) / 7 * 100), '%'\n    ) AS department_scorecard\n  FROM account_info a\n  JOIN subproc_list d\n    ON a.account_id = d.account_id\n  GROUP BY all\n),\n\n-- Final join of both parts\ndictionary_output AS (\n  SELECT\n    OBJECT_AGG(department, processes_by_dept) AS dept_process_subprocess_dict\n  FROM process_agg\n)\n\n-- Final SELECT\nSELECT \n  s.*,\n  s.department_scorecard,\n  to_json(d.dept_process_subprocess_dict) as department_usecases\nFROM dept_scorecard s\nJOIN dictionary_output d\n;", "update_only": "false"}, "keyword": "action", "name": "run_custom_sql", "number": 4, "provider": "snowflake", "skip": false}, {"as": "213ea423", "block": [], "keyword": "action", "name": "run_custom_sql", "number": 5, "provider": "snowflake", "skip": true}, {"as": "6d3b3e78", "block": [{"as": "9a3e3470", "block": [], "input": {"http_status_code": "404"}, "keyword": "action", "name": "return_response", "number": 7, "provider": "workato_api_platform", "skip": false}], "input": {"max_retry_count": "0", "retry_interval": "2"}, "keyword": "catch", "name": "", "number": 6, "provider": "", "skip": false}], "input": {}, "keyword": "try", "name": "", "number": 2, "provider": "", "skip": false}, {"as": "e62afcce", "block": [], "input": {"http_status_code": "200", "response": {"ACCOUNT_ID": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"58637f4a\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"account_id\"]}')}", "ACCOUNT_NAME": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"58637f4a\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"account_name\"]}')}", "CALENDAR_DATE": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"58637f4a\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"calendar_date\"]}')}", "CAT_COMPANY_SIZE": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"58637f4a\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"cat_company_size\"]}')}", "CURRENT_ARR_USD": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"58637f4a\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"current_arr_usd\"]}')}", "INDUSTRY": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"58637f4a\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"industry\"]}')}", "department_scores": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"58637f4a\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"department_scorecard\"]}')}", "department_usecases": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"58637f4a\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"department_usecases\"]}')}"}}, "keyword": "action", "name": "return_response", "number": 8, "provider": "workato_api_platform", "skip": false}], "input": {"request": {"content_type": "json", "headers": "[]", "schema": "[{\"control_type\":\"text\",\"label\":\"yyyy-mm-dd\",\"type\":\"string\",\"name\":\"date\",\"optional\":false,\"hint\":\"yyyy-mm-dd\"},{\"control_type\":\"text\",\"label\":\"Account ID\",\"type\":\"string\",\"name\":\"account_id\",\"optional\":false}]"}, "response": {"content_type": "json", "responses": [{"body_schema": "[{\"control_type\":\"text\",\"label\":\"ACCOUNT ID\",\"type\":\"string\",\"name\":\"ACCOUNT_ID\"},{\"control_type\":\"text\",\"label\":\"ACCOUNT NAME\",\"type\":\"string\",\"name\":\"ACCOUNT_NAME\"},{\"control_type\":\"text\",\"label\":\"CALENDAR DATE\",\"type\":\"string\",\"name\":\"CALENDAR_DATE\"},{\"control_type\":\"number\",\"label\":\"CURRENT ARR USD\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"CURRENT_ARR_USD\"},{\"control_type\":\"text\",\"label\":\"INDUSTRY\",\"type\":\"string\",\"name\":\"INDUSTRY\"},{\"control_type\":\"text\",\"label\":\"CAT COMPANY SIZE\",\"type\":\"string\",\"name\":\"CAT_COMPANY_SIZE\"},{\"name\":\"department_scores\",\"type\":\"string\",\"optional\":false,\"label\":\"department_scores\",\"control_type\":\"text\"},{\"name\":\"department_usecases\",\"type\":\"string\",\"optional\":false,\"label\":\"department_usecases\",\"of\":\"object\",\"control_type\":\"text\"}]", "http_status_code": "200", "name": "success"}, {"http_status_code": "404", "name": "fail"}]}}, "keyword": "trigger", "name": "receive_request", "number": 1, "provider": "workato_api_platform", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (SQL1_AS, "snowflake", "run_custom_sql"),
    (SQL2_AS, "snowflake", "run_custom_sql"),
    (CATCH_RETURN_AS, "workato_api_platform", "return_response"),
    (SUCCESS_RETURN_AS, "workato_api_platform", "return_response"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "workato_api_platform.return_response",
]
REQUIRED_EXPECT_KEYS = (
    "case",
    "outcome",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "http_status_code",
    "response",
    "return_step_as",
    "max_calendar_date",
    "result_rows_count",
)
OPTIONAL_EXPECT_KEYS = {"catch_message"}
OUTCOMES = ("account_found_200", "no_rows_200_empty", "catch_404")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_119586008(raw: dict[str, Any]) -> dict[str, Any]:
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
    nodes = {str(node.get("as") or ""): node for node in _walk_nodes(raw)}
    # Semantic pins (the tree pin holds the bytes; these name the traps):
    # 1. the MAX(CALENDAR_DATE) <= request.date query,
    sql1 = str((nodes[SQL1_AS].get("input") or {}).get("sql") or "")
    if "MAX(CALENDAR_DATE)" not in sql1 or "CALENDAR_DATE <=" not in sql1:
        raise RuntimeError(f"recipe {RECIPE_ID} step-3 SQL changed")
    # 2. the CTE battery's load-bearing clauses incl. the literal '%' CONCAT
    #    (the fixed engine gap) and the ON-less final JOIN,
    sql2 = str((nodes[SQL2_AS].get("input") or {}).get("sql") or "")
    for fragment in (
        "ARRAY_AGG(DISTINCT sub_process)",
        "OBJECT_AGG(process, sub_processes)",
        "OBJECT_AGG(department, processes_by_dept)",
        "sub_process != 'not conclusive'",
        "AND is_paying",
        "cust_type = 'direct'",
        "GROUP BY all",
        "'%, ',",
        "to_json(d.dept_process_subprocess_dict)",
        "FROM dept_scorecard s\nJOIN dictionary_output d",
        "s.department_scorecard,",
    ):
        if fragment not in sql2:
            raise RuntimeError(f"recipe {RECIPE_ID} step-4 SQL lost fragment {fragment!r}")
    # 3. the dead step stays skipped,
    if not nodes[DEAD_SQL_AS].get("skip"):
        raise RuntimeError(f"recipe {RECIPE_ID} step 213ea423 is no longer skipped")
    # 4. both responses (catch 404 has NO body; the 200 maps the 8 fields).
    if str((nodes[CATCH_RETURN_AS].get("input") or {}).get("http_status_code")) != "404":
        raise RuntimeError(f"recipe {RECIPE_ID} catch status changed")
    if "response" in (nodes[CATCH_RETURN_AS].get("input") or {}):
        raise RuntimeError(f"recipe {RECIPE_ID} the 404 must have no response body")
    success_input = nodes[SUCCESS_RETURN_AS].get("input") or {}
    if str(success_input.get("http_status_code")) != "200" or sorted(
        (success_input.get("response") or {}).keys()
    ) != sorted(RESPONSE_FIELDS):
        raise RuntimeError(f"recipe {RECIPE_ID} 200 response mapping changed")
    actions = [a for a in _collect_actions(raw)]
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
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


def seed_119586008(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_119586008(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the snowflake_live section: got "
            f"{sorted(seed_in.keys()) if isinstance(seed_in, dict) else seed_in!r}"
        )
    _require_snowflake_section(seed_in["snowflake_live"])
    force = data.get("force_action_error")
    _require_force_shape(force)
    _require_expect_shape(data.get("expect"), force, trigger, seed_in["snowflake_live"])
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


def run_119586008(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_119586008(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live section")
    _require_trigger_shape(seed.get("trigger") or {})
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
        # The seeded plg tables are benchmark-owned create-or-replace live
        # state: drop them even when execution fails (cleanup principle). The
        # API responses are not persistent.
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
    result["verifier"] = verify_119586008(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != ["request"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'request': ...}}; got "
            f"{sorted(trigger.keys())}"
        )
    request = trigger["request"]
    if not isinstance(request, dict) or sorted(request.keys()) != ["account_id", "date"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} request must carry exactly date + account_id: {request!r}"
        )
    if not isinstance(request["date"], str) or not _DATE_RE.match(request["date"]):
        raise RuntimeError(f"recipe {RECIPE_ID} request.date must be yyyy-mm-dd: {request!r}")
    datetime.date.fromisoformat(request["date"])
    if not isinstance(request["account_id"], str) or not request["account_id"].strip():
        raise RuntimeError(f"recipe {RECIPE_ID} request.account_id must be a non-empty string")


def _require_snowflake_section(section: Any) -> None:
    if not isinstance(section, dict) or not isinstance(section.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.snowflake_live.tables")
    unexpected = sorted(set(section.keys()) - {"tables"})
    if unexpected:
        raise RuntimeError(
            f"recipe {RECIPE_ID} snowflake_live has unexpected keys: {unexpected} "
            f"(the SQL never uses current date/time, so current_time must not be seeded)"
        )
    if sorted(section["tables"]) != sorted([ADOPTION_TABLE, COMPOSITE_TABLE]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{COMPOSITE_TABLE!r} and {ADOPTION_TABLE!r}"
        )
    for name, columns in ((COMPOSITE_TABLE, COMPOSITE_COLUMNS), (ADOPTION_TABLE, ADOPTION_COLUMNS)):
        spec = section["tables"][name]
        if not isinstance(spec, dict) or spec.get("columns") != columns:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {name} columns must be exactly {columns} (every "
                f"SQL-referenced column needs a declared type)"
            )
        rows = spec.get("rows")
        if not isinstance(rows, list) or not rows:
            raise RuntimeError(f"recipe {RECIPE_ID} {name} rows must be a NON-EMPTY list")
        for row in rows:
            if not isinstance(row, dict) or set(row) != set(columns):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} every {name} row must fill all declared columns: {row!r}"
                )
            if not _DATE_RE.match(str(row["CALENDAR_DATE"])):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} CALENDAR_DATE must be yyyy-mm-dd (DATE column, "
                    f"bare isoformat read-back): {row!r}"
                )
    composite = section["tables"][COMPOSITE_TABLE]["rows"]
    keys = [(str(row["ACCOUNT_ID"]), str(row["CALENDAR_DATE"])) for row in composite]
    if len(set(keys)) != len(keys):
        raise RuntimeError(
            f"recipe {RECIPE_ID} composite (account_id, calendar_date) pairs must be "
            f"unique (account_info must stay a single row for GROUP BY all determinism)"
        )
    for row in composite:
        if not isinstance(row["IS_PAYING"], bool):
            raise RuntimeError(f"recipe {RECIPE_ID} IS_PAYING must be a JSON boolean: {row!r}")
        if isinstance(row["CURRENT_ARR_USD"], bool) or not isinstance(row["CURRENT_ARR_USD"], int):
            raise RuntimeError(
                f"recipe {RECIPE_ID} CURRENT_ARR_USD must be an integer (NUMBER column "
                f"defaults to scale 0 -- decimals would round on insert): {row!r}"
            )
    if not any(not row["IS_PAYING"] or str(row["CUST_TYPE"]) != "direct" for row in composite):
        raise RuntimeError(
            f"recipe {RECIPE_ID} composite rows must include at least one non-paying or "
            f"non-direct decoy (the account_info filters must be observable)"
        )
    adoption = section["tables"][ADOPTION_TABLE]["rows"]
    for row in adoption:
        if str(row["DEPARTMENT"]) not in KNOWN_DEPARTMENTS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} DEPARTMENT must be one of the 7 scorecard "
                f"departments (anything else would silently skew the usecases dict): {row!r}"
            )
    if not any(str(row["SUB_PROCESS"]) == "not conclusive" for row in adoption):
        raise RuntimeError(
            f"recipe {RECIPE_ID} adoption rows must include at least one 'not conclusive' "
            f"decoy (the sub_process filter must be observable)"
        )
    groups: dict[tuple[str, str, str, str], set[str]] = {}
    for row in adoption:
        sub = str(row["SUB_PROCESS"])
        if sub == "not conclusive":
            continue
        key = (
            str(row["ACCOUNT_ID"]),
            str(row["CALENDAR_DATE"]),
            str(row["DEPARTMENT"]),
            str(row["PROCESS"]),
        )
        groups.setdefault(key, set()).add(sub)
    for key, subs in groups.items():
        if len(subs) > 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} ARRAY_AGG(DISTINCT sub_process) has NO deterministic "
                f"order for multi-element groups; every (account, date, department, "
                f"process) group must keep exactly ONE distinct sub_process: {key} -> {subs}"
            )


def _require_force_shape(force: Any) -> None:
    if force is None:
        return
    if not isinstance(force, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error must be an object")
    if str(force.get("step_as") or "") != SQL1_AS or not str(force.get("error") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error must target step_as {SQL1_AS!r} with an "
            f"explicit error message (the catch is reachable ONLY via SQL failure; the "
            f"request-driven SQL has no trigger-controllable live failure)"
        )


def _require_expect_shape(
    expect: Any, force: Any, trigger: dict[str, Any], snowflake: dict[str, Any]
) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS) - OPTIONAL_EXPECT_KEYS)
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    outcome = expect.get("outcome")
    if outcome not in OUTCOMES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.outcome must be one of {OUTCOMES}")
    if (outcome == "catch_404") != (force is not None):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the catch outcome and force_action_error must be declared "
            f"together"
        )
    request = trigger["request"]
    composite = snowflake["tables"][COMPOSITE_TABLE]["rows"]
    adoption = snowflake["tables"][ADOPTION_TABLE]["rows"]
    if outcome == "catch_404":
        checks = (
            expect.get("executed_action_count") == 1,
            expect.get("tools") == ["workato_api_platform.return_response"],
            expect.get("http_status_code") == "404",
            expect.get("return_step_as") == CATCH_RETURN_AS,
            expect.get("response") == {},
            expect.get("max_calendar_date") is None,
            expect.get("result_rows_count") is None,
            isinstance(expect.get("catch_message"), str)
            and expect["catch_message"] == force.get("error"),
        )
        if not all(checks):
            raise RuntimeError(f"recipe {RECIPE_ID} catch_404 expect block is incoherent: {expect!r}")
        return
    # SQL branches: recompute the step-3 MAX locally (ISO strings compare
    # lexicographically) and pin outcome coherence against the seed.
    candidate_dates = sorted(
        str(row["CALENDAR_DATE"]) for row in composite if str(row["CALENDAR_DATE"]) <= request["date"]
    )
    if not candidate_dates:
        raise RuntimeError(
            f"recipe {RECIPE_ID} at least one composite CALENDAR_DATE must be <= "
            f"request.date (a NULL max would poison the step-4 date filter)"
        )
    max_date = candidate_dates[-1]
    if expect.get("max_calendar_date") != max_date:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.max_calendar_date must equal the seeded MAX "
            f"({max_date!r}): {expect.get('max_calendar_date')!r}"
        )
    account_info = [
        row for row in composite
        if str(row["ACCOUNT_ID"]) == request["account_id"]
        and str(row["CALENDAR_DATE"]) == max_date
        and row["IS_PAYING"] is True
        and str(row["CUST_TYPE"]) == "direct"
    ]
    subproc = [
        row for row in adoption
        if str(row["ACCOUNT_ID"]) == request["account_id"]
        and str(row["CALENDAR_DATE"]) == max_date
        and str(row["SUB_PROCESS"]) != "not conclusive"
    ]
    response = expect.get("response")
    common = (
        expect.get("executed_action_count") == 3,
        expect.get("tools") == [
            "snowflake.run_custom_sql",
            "snowflake.run_custom_sql",
            "workato_api_platform.return_response",
        ],
        expect.get("http_status_code") == "200",
        expect.get("return_step_as") == SUCCESS_RETURN_AS,
        isinstance(response, dict) and sorted(response.keys()) == sorted(RESPONSE_FIELDS),
        "catch_message" not in expect,
    )
    if outcome == "account_found_200":
        arr = account_info[0]["CURRENT_ARR_USD"] if account_info else None
        checks = common + (
            len(account_info) == 1,
            len(subproc) >= 1,
            expect.get("result_rows_count") == 1,
            response.get("ACCOUNT_ID") == request["account_id"],
            response.get("ACCOUNT_NAME") == (account_info[0]["ACCOUNT_NAME"] if account_info else None),
            response.get("CALENDAR_DATE") == max_date,
            response.get("CURRENT_ARR_USD") == arr,
            isinstance(response.get("department_scores"), str)
            and "%%" not in response["department_scores"]
            and response["department_scores"].count("%") == 7,
            isinstance(response.get("department_usecases"), str),
        )
    else:  # no_rows_200_empty
        checks = common + (
            len(account_info) == 0 or len(subproc) == 0,
            expect.get("result_rows_count") == 0,
            all(response.get(field) is None for field in RESPONSE_FIELDS),
        )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with outcome {outcome!r}: {expect!r}"
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


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return dict(ctx.tools.call("harness.snowflake.snapshot", {}))


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
