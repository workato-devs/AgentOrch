from __future__ import annotations

import datetime
import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_130550781


RECIPE_ID = "130550781"
SEED_TYPE = "chi_2023_process_complexity_aggregated_ctas_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "b2acd0b3"
SQL_STEP_AS = "dc8b70a8"
ASYNC_STEP_AS = "cbeaea37"
CATCH_AS = "275a5039"
CATCH_RETURN_AS = "f32a5226"
STOP_STEP_AS = "4d914476"
SUCCESS_RETURN_AS = "353e2923"
# The raw SQL spells these with inline <anon>2023</anon> tags; the
# snowflake_live boundary de-tags identifiers (_strip_inline_anon in
# _rewrite_sql/_clean_table_name/_quote_identifier), so seeds register the
# CLEAN names and the tagged raw SQL still maps onto them (probe-verified on
# this tree; same fix precedent as batch05 130549575/130549037/130073081).
TARGET_TABLE = "plg.chi_2023_process_complexity_scoring_aggregated_operational"
SCORES_TABLE = "plg.chi_2023_process_complexity_scores_operational"
TIER_TABLE = "plg.recipe_sophistication_app_tier"
SCORES_COLUMNS = {
    "calendar_date": "date",
    "account_id": "string",
    "account_name": "string",
    "root_flow": "string",
    "data_center": "string",
    "overall_complexity": "float",
    "apps_used": "string",
    "num_tier_1_app": "number",
    "num_tier_2_app": "number",
}
TIER_COLUMNS = {
    "title": "string",
    "app_tier": "number",
    "category": "string",
}

# workato_recipe_function.execute (as b2acd0b3, result schema {status}); no
# trigger parameters are read (trigger_input must be exactly {}). Body:
#   TRY (step 2):
#     3  snowflake.run_custom_sql dc8b70a8 (LIVE): create or replace table
#        plg.chi_<anon>2023</anon>_process_complexity_scoring_aggregated_
#        operational as WITH base (round() CASE simple/moderate/complex +
#        round(percent_rank() over (partition by calendar_date, account_id
#        order by overall_complexity asc),2)) / business_critical_apps_cte
#        (num_tier_1+num_tier_2 >= 1 filter) / apps_used_split (lateral
#        flatten(split(apps_used,',')), a.value::string) / app_used_filtered
#        (left join tier ON title AND app_tier in (1,2); WHERE (category in
#        ('app','custom') and app_name != 'JDBC') or (category='others' and
#        app_name='On-prem files')) / ranked_top_apps (rank() by n_flows desc,
#        qualify rank_app <= 4) / top_business_critical_apps + business_
#        critical_apps_2 (listagg distinct) / median_complexity_metric
#        (percentile >= 0.67, round(median,2)) / complexity_volume_interim /
#        base2 (nvl fallbacks incl 'No business-critical apps used', lateral-
#        alias percentage division + round) / interim_final (volume <=12
#        downgrade / >15 upgrade / else flat; complexity pass thresholds
#        6.5/6.3/5.9; process_complexity_output CASE) / rounded_complexity_
#        values + pivot_complexity_distributions (coalesce(sum(case rounded=
#        1..10),0)) / final ('* exclude' join) select * from final
#     4  snowflake.run_custom_sql_async_v2 cbeaea37 skip:true (traced
#        {skipped: true}, never executed -- raw_executor skip handling)
#   CATCH (step 5, as 275a5039, max_retry_count 0):
#     6  return_result f32a5226 {status:'failed'} -- TERMINAL
#     7  STOP 4d914476 (stop_with_error, '#{catch.type}, #{catch.message}')
#        -- unreachable dead code: return_result is engine-terminal
#        (TERMINAL_TOOLS), so the stop node must never trace
#   8  return_result 353e2923 {status:'success'}
#
# Backends: Snowflake runs LIVE. Seeds register the CLEAN 2-part names; the
# CTAS target registers {'rows': []} (dropped pre-run, rewritten,
# cleanup-owned). The SQL has NO current_date/current_timestamp/sysdate ->
# no current_time key allowed. '::string' casts survive _bind_sql
# (probe-verified: no false binds, no '%' literals).
#
# GROUNDTRUTH DISCIPLINE: overall_complexity is FLOAT seeded on .25/.75
# fractions only, so every round() (categories, pivot buckets) and
# round(median,2) lands on binary-exact values and never sits on a .5
# half-rounding boundary. Counts/percentages are NUMBER (ints on read-back).
# LISTAGG(distinct ...) without WITHIN GROUP has UNSPECIFIED element order
# live -- expect pins those two columns as canonical sorted comma-sets and
# the verifier compares set-wise (all other columns exact).

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "workato_recipe_function", "name": "execute", "as": "b2acd0b3", "skip": false, "input": {"result_schema_json": "[{\"name\":\"status\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Status\"}]"}, "block": [{"number": 2, "keyword": "try", "provider": "", "name": "", "as": "", "skip": false, "input": {}, "block": [{"number": 3, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql", "as": "dc8b70a8", "skip": false, "input": {"sql": "create or replace table plg.chi_<anon>2023</anon>_process_complexity_scoring_aggregated_operational as \n/*\n1) note that customers with 0 active recipes will have no complexity at all, and they will not even show up in this table.\n2) when surfacing # workflows with 2+ biz critical apps, we have to do a lateral flatten of apps used and filter away and retrieve only tier 1 & 2 apps that are biz facing\n*/\nwith base as (\n    select *\n        , case \n            when round(overall_complexity) <= 3 then 'simple'\n            when round(overall_complexity) >= 4 and round(overall_complexity) <= 6 then 'moderate'\n            when round(overall_complexity) >= 7 then 'complex'\n            else 'simple' end workflow_complexity_category\n        , round(percent_rank() over (partition by calendar_date, account_id order by overall_complexity asc),2) as workflow_percentile\n    from plg.chi_<anon>2023</anon>_process_complexity_scores_operational\n    order by calendar_date, account_id, overall_complexity desc\n)\n\n, business_critical_apps_cte as (\n    select *, \n        case when (num_tier_1_app + num_tier_2_app) >= 1 then true else false end has_biz_critical_apps\n    from base\n    where has_biz_critical_apps = true\n) \n\n\n, apps_used_split as (\n    select calendar_date, account_id, root_flow||data_center root_flow_id, a.value::string app_name\n    from business_critical_apps_cte, \n        lateral flatten (input => split(apps_used, ',')) a\n    group by all\n    )\n\n, app_used_filtered as (\n    select *\n    from apps_used_split a\n    left join plg.recipe_sophistication_app_tier t\n        on a.app_name = t.title\n        and app_tier in (1,2)\n    where (\n        category in ('app', 'custom') and  app_name != 'JDBC'\n        )\n        or (category = 'others' and app_name = 'On-prem files') \n    order by calendar_date, account_id, app_tier, category\n)\n\n, ranked_top_apps as (\n    select calendar_date, account_id, app_name, count(distinct root_flow_id) n_flows,\n    rank() over (partition by calendar_date, account_id order by n_flows desc) rank_app\n    from app_used_filtered\n    group by all\n    qualify rank_app <= 4\n    order by 1,2,5\n)\n\n, top_business_critical_apps as (\n    select calendar_date, account_id, listagg(distinct app_name, ',') display_output_top_apps\n    from ranked_top_apps\n    group by all\n    )\n    \n, business_critical_apps_2 as (\n    select a.calendar_date, a.account_id, count(distinct root_flow_id) n_workflows_w_critical_apps, listagg(distinct app_name, ',') biz_critical_app_names\n        , b.display_output_top_apps\n    from app_used_filtered a\n    left join top_business_critical_apps b\n        on a.calendar_date = b.calendar_date and a.account_id = b.account_id\n    group by all\n    order by 3 desc\n)\n\n\n, median_complexity_metric_interim as (\n    select *\n    from base \n    where workflow_percentile >= 0.67\n)\n\n, median_complexity_metric as (\n    select calendar_date, account_id, account_name, round(median(overall_complexity),2) workflow_complexity_metric\n    from median_complexity_metric_interim\n    group by all\n)\n\n, complexity_volume_interim as (\n    select calendar_date, account_id, account_name\n        , sum(case when workflow_complexity_category in ('moderate', 'complex') then 1 else 0 end) as n_med_high_complexity_workflows\n        , count(account_id) as n_workflows_total\n    from base\n    group by all\n)\n\n, base2 as (\n    select v.*\n     , nvl(b.n_workflows_w_critical_apps,0) n_workflows_w_critical_apps\n     , nvl(biz_critical_app_names, 'No business-critical apps used') biz_critical_app_names\n     , nvl(display_output_top_apps, 'No business-critical apps used') display_output_top_apps\n     , nvl(round((n_workflows_w_critical_apps*100)/n_workflows_total),0) percentage_workflows_2plus_biz_apps\n     , round((n_med_high_complexity_workflows*100)/n_workflows_total) percentage_workflows_med_high_complexity\n     , nvl(workflow_complexity_metric, 0) workflow_complexity_metric\n    from complexity_volume_interim v\n    left join median_complexity_metric c\n        on v.calendar_date = c.calendar_date and v.account_id = c.account_id \n    left join business_critical_apps_2 b\n        on v.calendar_date = b.calendar_date and v.account_id = b.account_id\n)\n\n, interim_final as (\n    select b2.* \n        , case \n            when n_med_high_complexity_workflows <= 12 then 'downgrade'\n            when n_med_high_complexity_workflows >  15 then 'upgrade'\n            else 'flat' end volume_criteria\n            \n        , case \n            when volume_criteria = 'upgrade'   and workflow_complexity_metric >= 6.5 then 'pass'\n            when volume_criteria = 'upgrade'   and workflow_complexity_metric <  6.5 then 'no pass'\n            when volume_criteria = 'flat'      and workflow_complexity_metric >= 6.3 then 'pass'\n            when volume_criteria = 'flat'      and workflow_complexity_metric <  6.3 then 'no pass'\n            when volume_criteria = 'downgrade' and workflow_complexity_metric >  5.9 then 'pass'\n            when volume_criteria = 'downgrade' and workflow_complexity_metric <= 5.9 then 'no pass'\n            end complexity_criteria\n    \n        , case\n            when volume_criteria = 'upgrade' and complexity_criteria = 'pass' then 'upgrade'\n            when volume_criteria = 'upgrade' and complexity_criteria = 'no pass' then 'flat'\n            when volume_criteria = 'flat' and complexity_criteria = 'pass' then 'upgrade'\n            when volume_criteria = 'flat' and complexity_criteria = 'no pass' then 'flat'\n            when volume_criteria = 'downgrade' and complexity_criteria = 'pass' then 'flat'\n            when volume_criteria = 'downgrade' and complexity_criteria = 'no pass' then 'downgrade'\n            end process_complexity_output\n            \n    from base2 b2\n)\n\n, rounded_complexity_values as (\n    select calendar_date, account_id, account_name, round(overall_complexity) rounded_complexity, count(root_flow||data_center) n_workflows\n    from plg.chi_<anon>2023</anon>_process_complexity_scores_operational\n    group by all\n    order by 1,2,4\n)\n\n, pivot_complexity_distributions as (\n    select \n        calendar_date, account_id, account_name,\n        coalesce(sum(case when rounded_complexity = 1 then n_workflows end), 0) as complexity_1,\n        coalesce(sum(case when rounded_complexity = 2 then n_workflows end), 0) as complexity_2,\n        coalesce(sum(case when rounded_complexity = 3 then n_workflows end), 0) as complexity_3,\n        coalesce(sum(case when rounded_complexity = 4 then n_workflows end), 0) as complexity_4,\n        coalesce(sum(case when rounded_complexity = 5 then n_workflows end), 0) as complexity_5,\n        coalesce(sum(case when rounded_complexity = 6 then n_workflows end), 0) as complexity_6,\n        coalesce(sum(case when rounded_complexity = 7 then n_workflows end), 0) as complexity_7,\n        coalesce(sum(case when rounded_complexity = 8 then n_workflows end), 0) as complexity_8,\n        coalesce(sum(case when rounded_complexity = 9 then n_workflows end), 0) as complexity_9,\n        coalesce(sum(case when rounded_complexity = 10 then n_workflows end), 0) as complexity_10\n    from rounded_complexity_values\n    group by\n        calendar_date, account_id, account_name\n    order by \n        calendar_date, account_id\n)\n\n\n, final as (\n    select i.*, p.* exclude (calendar_date, account_id, account_name)\n    from interim_final i\n    left join pivot_complexity_distributions p\n        on i.calendar_date = p.calendar_date and i.account_id = p.account_id\n)\n\nselect *\nfrom final", "update_only": "false"}, "block": []}, {"number": 4, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql_async_v2", "as": "cbeaea37", "skip": true, "block": []}, {"number": 5, "keyword": "catch", "provider": "", "name": "", "as": "275a5039", "skip": false, "input": {"max_retry_count": "0", "retry_interval": "2"}, "block": [{"number": 6, "keyword": "action", "provider": "workato_recipe_function", "name": "return_result", "as": "f32a5226", "skip": false, "input": {"result": {"status": "failed"}}, "block": []}, {"number": 7, "keyword": "stop", "provider": "", "name": "", "as": "4d914476", "skip": false, "input": {"stop_reason": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"275a5039\",\"path\":[\"type\"]}')}, #{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"275a5039\",\"path\":[\"message\"]}')}", "stop_with_error": "true"}, "block": []}]}]}, {"number": 8, "keyword": "action", "provider": "workato_recipe_function", "name": "return_result", "as": "353e2923", "skip": false, "input": {"result": {"status": "success"}}, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (SQL_STEP_AS, "snowflake", "run_custom_sql"),
    (CATCH_RETURN_AS, "workato_recipe_function", "return_result"),
    (SUCCESS_RETURN_AS, "workato_recipe_function", "return_result"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "workato_recipe_function.return_result",
]
EXPECTED_RESULT_SCHEMA_JSON = (
    '[{"name":"status","type":"string","optional":false,"control_type":"text","label":"Status"}]'
)
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "return_value",
    "async_step_skipped",
    "final_snowflake_tables",
    "cleanup_tables",
)


def validate_130550781(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    schema_json = str((raw.get("input") or {}).get("result_schema_json") or "")
    if schema_json != EXPECTED_RESULT_SCHEMA_JSON:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger result schema changed")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    actions = _collect_actions(raw)
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


def seed_130550781(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130550781(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (no trigger parameters "
            f"are declared or read): {trigger!r}"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the snowflake_live section"
        )
    _require_snowflake_section(seed_in["snowflake_live"])
    force = data.get("force_action_error")
    _require_force_shape(force)
    expect = data.get("expect")
    _require_expect_shape(expect, force)
    provision = ctx.tools.call(
        "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_130550781(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130550781(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
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
    snowflake_cleanup: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = _snapshot(ctx)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx)
    finally:
        # All three registered tables (two seeded sources + the CTAS target)
        # are benchmark-owned live objects: drop them even on failure.
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
    result["verifier"] = verify_130550781(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_snowflake_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the SQL uses no current_date/current_timestamp/sysdate, so no current_time)"
        )
    tables = section["tables"]
    expected_keys = sorted([TARGET_TABLE, SCORES_TABLE, TIER_TABLE])
    if not isinstance(tables, dict) or sorted(tables.keys()) != expected_keys:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must register exactly {expected_keys} "
            "(CLEAN de-tagged 2-part names so _rewrite_sql maps the tagged raw SQL)"
        )
    target = tables[TARGET_TABLE]
    if target != {"rows": []}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} CTAS target {TARGET_TABLE} must be exactly {{'rows': []}}; "
            f"got {target!r}"
        )
    _require_typed_table(tables[SCORES_TABLE], SCORES_TABLE, SCORES_COLUMNS)
    _require_typed_table(tables[TIER_TABLE], TIER_TABLE, TIER_COLUMNS)
    for idx, row in enumerate(tables[SCORES_TABLE]["rows"]):
        value = row.get("overall_complexity")
        if value is None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} scores row {idx} must pin overall_complexity"
            )
        # .25/.75 fractions only: binary-exact AND never on a round() .5
        # boundary (categories, pivot buckets, median all stay deterministic).
        quarters = round(float(value) * 4)
        if float(value) * 4 != quarters or quarters % 2 == 0:
            raise RuntimeError(
                f"recipe {RECIPE_ID} scores row {idx} overall_complexity must sit on a "
                f".25/.75 fraction (binary-exact, off the .5 rounding boundary): {value!r}"
            )


def _require_typed_table(spec: Any, table: str, columns: dict[str, str]) -> None:
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(f"recipe {RECIPE_ID} table {table} spec must be {{'columns','rows'}}")
    if spec["columns"] != columns:
        raise RuntimeError(f"recipe {RECIPE_ID} table {table} columns must be exactly {columns}")
    rows = spec["rows"]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {table} rows must be a list (may be empty)")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table {table} row {idx} must be an object")
        extra = sorted(set(row.keys()) - set(columns.keys()))
        if extra:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {table} row {idx} uses undeclared columns: {extra}"
            )
        for column, value in row.items():
            kind = columns[column]
            if value is None:
                continue
            if kind == "number" and (isinstance(value, bool) or not isinstance(value, int)):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table} row {idx} {column} must be an integer"
                )
            if kind == "float" and (
                isinstance(value, bool) or not isinstance(value, (int, float))
            ):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table} row {idx} {column} must be numeric"
                )
            if kind == "string" and not isinstance(value, str):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table} row {idx} {column} must be a string"
                )
            if kind == "date":
                try:
                    datetime.date.fromisoformat(str(value))
                except ValueError as exc:
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} table {table} row {idx} {column} must be "
                        f"YYYY-MM-DD: {value!r}"
                    ) from exc


def _require_force_shape(force: Any) -> None:
    if force is None:
        return
    if not isinstance(force, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error must be an object")
    if str(force.get("step_as") or "") != SQL_STEP_AS or not str(force.get("error") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error must target step_as {SQL_STEP_AS!r} with an "
            "explicit error message (the CTAS is the only fallible step inside the TRY)"
        )


def _require_expect_shape(expect: Any, force: Any) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    is_catch = force is not None
    expected_return = {"status": "failed"} if is_catch else {"status": "success"}
    if expect.get("return_value") != expected_return:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.return_value must be {expected_return} "
            f"({'catch' if is_catch else 'success'} path): {expect.get('return_value')!r}"
        )
    if bool(expect.get("async_step_skipped")) == is_catch:
        raise RuntimeError(
            f"recipe {RECIPE_ID} async_step_skipped must be true exactly on success paths"
        )
    expected_count = 1 if is_catch else 2
    if expect.get("executed_action_count") != expected_count:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.executed_action_count must be {expected_count} "
            f"({'catch: only the terminal failed return' if is_catch else 'CTAS + success return'})"
        )
    final_tables = expect.get("final_snowflake_tables")
    if not isinstance(final_tables, dict) or TARGET_TABLE not in final_tables:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_snowflake_tables must pin the CTAS target "
            f"{TARGET_TABLE!r} (count 0 on the catch path: the pre-dropped target is never built)"
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
