from __future__ import annotations

import datetime
import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_130549037


RECIPE_ID = "130549037"
SEED_TYPE = "chi_2023_process_complexity_features_rollup_ctas_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "d5a45675"
DECLARE_STEP_AS = "70d77402"
SQL_STEP_AS = "46f5b240"
ASYNC_STEP_AS = "171a0a26"
CATCH_RETURN_AS = "6750cfd8"
STOP_STEP_AS = "a6f4c3df"
SUCCESS_RETURN_AS = "fdf1f721"
# The raw SQL spells these with inline <anon>2023</anon> tags; the
# snowflake_live boundary de-tags identifiers, so seeds register the CLEAN
# names and the tagged raw SQL still maps onto them.
TARGET_TABLE = "plg.chi_2023_process_complexity_recipe_features_operational"
INTERIM_TABLE = "plg.chi_2023_process_complexity_recipe_features_interim_operational"
HIERARCHY_TABLE = "plg.chi_2023_recipe_hierarchy_operational"
INTERIM_COLUMNS = {
    "calendar_date": "date",
    "data_center": "string",
    "flow_id": "string",
    "account_id": "string",
    "account_name": "string",
    "recipe_category_type": "string",
    "trigger_app": "string",
    "trigger_type": "string",
    "num_steps": "number",
    "tier_1_applications": "string",
    "tier_2_applications": "string",
    "tier_3_applications": "string",
    "tier_4_applications": "string",
    "tier_5_applications": "string",
    "has_bulkbatch_action": "boolean",
    "has_query_action": "boolean",
    "has_db_table": "boolean",
    "has_collections": "boolean",
    "has_variables": "boolean",
    "has_lookup_table": "boolean",
    "has_scripting": "boolean",
    "has_sync_function": "boolean",
    "has_async_function": "boolean",
    "has_looping_logic": "boolean",
    "has_if_then_logic": "boolean",
    "has_if_then_else_logic": "boolean",
    "has_try_catch_logic": "boolean",
}
HIERARCHY_COLUMNS = {
    "calendar_date": "date",
    "data_center": "string",
    "flow_id": "string",
    "root_flow": "string",
    "workflow_type": "string",
}

# workato_recipe_function.execute (as d5a45675, result schema {status}); no
# trigger parameters are read. Body:
#   2  declare_variable 70d77402: snap_date = now.strftime('%Y-%m-%d')
#      (pinned seed.now; unused by the SQL)
#   TRY (step 3):
#     4  snowflake.run_custom_sql 46f5b240 (LIVE): create or replace table
#        plg.chi_<anon>2023</anon>_process_complexity_recipe_features_operational
#        as WITH rollup_recipe_ft0 (interim JOIN hierarchy on
#        calendar_date/data_center/flow_id -- a flow at N hierarchy
#        memberships contributes to N workflows) / rollup_recipe_ft3
#        (per-root count(distinct flow_id||data_center),
#        sum(nvl(num_steps,0)), listagg(distinct tier apps), CASE-sum flag
#        counts) / tierN_app_split x5 (ACTIVE lateral flatten over
#        split(tier_apps, ','), blank/null filtered) / tierN_rollup x5
#        (listagg(distinct app) + count) / rollup_apptier (coalesce counts)
#        / rollup_recipe_features (root's own hierarchy row via
#        rh.flow_id = rh.root_flow, root's own interim row for
#        account/category/trigger, derived has_*/is_single_action/
#        is_pass_through booleans, HAVING account_id is not null);
#        14x group by all; trailing ';'
#     5  snowflake.run_custom_sql_async_v2 171a0a26 skip:true (traced
#        {skipped: true}, never executed)
#   CATCH (step 6, as 7f4abb25, max_retry_count 0):
#     7  return_result 6750cfd8 {status:'failed'} -- TERMINAL
#     8  STOP a6f4c3df -- unreachable after the terminal return
#   9  return_result fdf1f721 {status:'success'}
#
# Backends: Snowflake runs LIVE; seeds register CLEAN 2-part names (anon
# de-tag boundary). CTAS target registers {'rows': []}. No binds, no
# current_date/current_timestamp -> no current_time.
#
# GROUNDTRUTH DISCIPLINE: listagg(distinct ...) carries NO within-group
# ordering, so the final TIER_N_APPS strings are order-nondeterministic
# whenever a tier aggregates >1 app. Expects encode those columns as
# {"csv_set": [...]} and the verifier compares comma-split SETS -- exact
# content, order-free. Every other column is pinned byte/value-exact.
# The INTERMEDIATE ft3 listagg order never matters: its only consumers are
# the split/flatten CTEs, which re-distinct the individual apps.

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "workato_recipe_function", "name": "execute", "as": "d5a45675", "skip": false, "input": {"result_schema_json": "[{\"name\":\"status\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Status\"}]"}, "block": [{"number": 2, "keyword": "action", "provider": "workato_variable", "name": "declare_variable", "as": "70d77402", "skip": false, "input": {"variables": {"data": {"snap_date": "=now.strftime(\"%Y-%m-%d\")"}, "schema": "[{\"name\":\"snap_date\",\"type\":\"string\",\"optional\":true,\"label\":\"snap_date\",\"details\":{\"real_name\":\"snap_date\"},\"control_type\":\"text\"}]"}}, "block": []}, {"number": 3, "keyword": "try", "provider": "", "name": "", "as": "", "skip": false, "input": {}, "block": [{"number": 4, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql", "as": "46f5b240", "skip": false, "input": {"sql": "create or replace table plg.chi_<anon>2023</anon>_process_complexity_recipe_features_operational as\nwith rollup_recipe_ft0 as (\n    select ft.*, rh.workflow_type, rh.root_flow, ft.flow_id flow_id2\n    -- , rh.level, rh.hierarchy_path, rh.parent_id,\n    from plg.chi_<anon>2023</anon>_process_complexity_recipe_features_interim_operational ft\n    join plg.chi_<anon>2023</anon>_recipe_hierarchy_operational rh\n        on ft.calendar_date = rh.calendar_date and ft.data_center = rh.data_center and ft.flow_id = rh.flow_id\n    group by all\n    -- having ft.calendar_date = $snap_date\n)\n\n\n-- , rollup_recipe_ft1 as (\n--     select *\n--     from rollup_recipe_ft0,\n--         lateral flatten (input => hierarchy_path)\n-- )\n\n-- , rollup_recipe_ft2 as (\n--     select calendar_date, value::varchar ref_flow, flow_id, root_flow, this, data_center, num_steps, workflow_type\n--         , tier_1_applications, tier_2_applications, tier_3_applications, tier_4_applications, tier_5_applications\n--         , trigger_type, has_bulkbatch_action, has_query_action, is_single_action\n--         , has_db_table, has_collections, has_variables, has_lookup_table, has_python, has_js, has_ruby, has_scripting\n--         , has_if_then_logic, has_if_then_else_logic, is_pass_through, has_try_catch_logic\n--         , has_sync_function, has_async_function, has_looping_logic\n--     from rollup_recipe_ft1\n--     group by all\n-- )\n\n, rollup_recipe_ft3 as (\n    select calendar_date, data_center, root_flow\n    -- # steps, # downstream flows\n        , count(distinct (flow_id||data_center)) n_flows_in_workflow\n        , sum(nvl(num_steps,0)) n_downstream_steps\n    -- app tiering (should not include workato utilities - handled in upstream table)\n        , listagg(distinct (tier_1_applications), ',') tier_1_apps\n        , listagg(distinct (tier_2_applications), ',') tier_2_apps\n        , listagg(distinct (tier_3_applications), ',') tier_3_apps\n        , listagg(distinct (tier_4_applications), ',') tier_4_apps\n        , listagg(distinct (tier_5_applications), ',') tier_5_apps\n    /* bulk-batch, query. \n    Note: single actions are not included here, will account for it later */\n        , sum(case when has_bulkbatch_action = true then 1 else 0 end) n_flows_with_bulkbatch_action\n        , sum(case when has_query_action = true then 1 else 0 end) n_flows_with_query_action\n    -- data transformation\n        , sum(case when has_db_table = true then 1 else 0 end) n_flows_db_table\n        , sum(case when has_collections = true then 1 else 0 end) n_flows_collections\n        , sum(case when has_variables = true then 1 else 0 end) n_flows_variables\n        , sum(case when has_lookup_table = true then 1 else 0 end) n_flows_lookup_table\n        , sum(case when has_scripting = true then 1 else 0 end) n_flows_has_scripting\n    -- recipe logic & steps **is_pass_through handled later              \n        , sum(case when has_async_function = true then 1 else 0 end) n_flows_has_async    \n        , sum(case when has_sync_function = true then 1 else 0 end) n_flows_has_sync\n        , sum(case when has_looping_logic = true then 1 else 0 end) n_flows_has_looping\n        , sum(case when has_if_then_logic = true then 1 else 0 end) n_flows_if_then_logic\n        , sum(case when has_if_then_else_logic = true then 1 else 0 end) n_flows_if_then_else_logic\n        , sum(case when has_try_catch_logic = true then 1 else 0 end) n_flows_has_try_catch\n    from rollup_recipe_ft0\n    group by all\n)\n\n-- app_tier_consolidation - checking roll up of # off apps\n\n, tier1_app_split as (\n    select calendar_date, data_center, root_flow, a.value::string as tier_app\n    from rollup_recipe_ft3,\n        lateral flatten(input => split(tier_1_apps, ',')) a\n    where tier_app is not null and tier_app != ''\n    group by all\n)\n\n, tier2_app_split as (\n    select calendar_date, data_center, root_flow, a.value::string as tier_app\n    from rollup_recipe_ft3,\n        lateral flatten(input => split(tier_2_apps, ',')) a\n    where tier_app is not null and tier_app != ''\n    group by all\n)\n\n, tier3_app_split as (\n    select calendar_date, data_center, root_flow, a.value::string as tier_app\n    from rollup_recipe_ft3,\n        lateral flatten(input => split(tier_3_apps, ',')) a\n    where tier_app is not null and tier_app != ''\n    group by all\n)\n\n, tier4_app_split as (\n    select calendar_date, data_center, root_flow, a.value::string as tier_app\n    from rollup_recipe_ft3,\n        lateral flatten(input => split(tier_4_apps, ',')) a\n    where tier_app is not null and tier_app != ''\n    group by all\n)\n\n, tier5_app_split as (\n    select calendar_date, data_center, root_flow, a.value::string as tier_app\n    from rollup_recipe_ft3,\n        lateral flatten(input => split(tier_5_apps, ',')) a\n    where tier_app is not null and tier_app != ''\n    group by all\n)\n\n\n, tier1_rollup as (\n    select calendar_date, root_flow, data_center, listagg(distinct(tier_app), ',') tier_apps, count(tier_app) n_app_used\n    from tier1_app_split\n    group by all\n)\n\n, tier2_rollup as (\n    select calendar_date, root_flow, data_center, listagg(distinct(tier_app), ',') tier_apps, count(tier_app) n_app_used\n    from tier2_app_split\n    group by all\n)\n\n, tier3_rollup as (\n    select calendar_date, root_flow, data_center, listagg(distinct(tier_app), ',') tier_apps, count(tier_app) n_app_used\n    from tier3_app_split\n    group by all\n)\n\n, tier4_rollup as (\n    select calendar_date, root_flow, data_center, listagg(distinct(tier_app), ',') tier_apps, count(tier_app) n_app_used\n    from tier4_app_split\n    group by all\n)\n\n, tier5_rollup as (\n    select calendar_date, root_flow, data_center, listagg(distinct(tier_app), ',') tier_apps, count(tier_app) n_app_used\n    from tier5_app_split\n    group by all\n)\n\n, rollup_apptier as (\n    select rrft3.calendar_date, rrft3.root_flow, rrft3.data_center\n        , t1ru.tier_apps tier_1_apps\n        , t2ru.tier_apps tier_2_apps\n        , t3ru.tier_apps tier_3_apps\n        , t4ru.tier_apps tier_4_apps\n        , t5ru.tier_apps tier_5_apps\n        , coalesce(t1ru.n_app_used, 0) num_tier_1_app\n        , coalesce(t2ru.n_app_used, 0) num_tier_2_app\n        , coalesce(t3ru.n_app_used, 0) num_tier_3_app\n        , coalesce(t4ru.n_app_used, 0) num_tier_4_app\n        , coalesce(t5ru.n_app_used, 0) num_tier_5_app\n    from rollup_recipe_ft3 rrft3\n    left join tier1_rollup t1ru on rrft3.calendar_date = t1ru.calendar_date and rrft3.root_flow = t1ru.root_flow and rrft3.data_center = t1ru.data_center\n    left join tier2_rollup t2ru on rrft3.calendar_date = t2ru.calendar_date and rrft3.root_flow = t2ru.root_flow and rrft3.data_center = t2ru.data_center\n    left join tier3_rollup t3ru on rrft3.calendar_date = t3ru.calendar_date and rrft3.root_flow = t3ru.root_flow and rrft3.data_center = t3ru.data_center\n    left join tier4_rollup t4ru on rrft3.calendar_date = t4ru.calendar_date and rrft3.root_flow = t4ru.root_flow and rrft3.data_center = t4ru.data_center\n    left join tier5_rollup t5ru on rrft3.calendar_date = t5ru.calendar_date and rrft3.root_flow = t5ru.root_flow and rrft3.data_center = t5ru.data_center\n    group by all\n)\n\n, rollup_recipe_features as (\n    select  rrft3.calendar_date, rft.account_id, rft.account_name, rrft3.root_flow, rrft3.data_center, rh.workflow_type\n        , rrft3.n_flows_in_workflow, rrft3.n_downstream_steps, rft.recipe_category_type, rft.trigger_app\n        , ruat.tier_1_apps\n        , ruat.tier_2_apps\n        , ruat.tier_3_apps\n        , ruat.tier_4_apps\n        , ruat.tier_5_apps\n        , ruat.num_tier_1_app\n        , ruat.num_tier_2_app\n        , ruat.num_tier_3_app\n        , ruat.num_tier_4_app\n        , ruat.num_tier_5_app\n        , rft.trigger_type\n        , case when n_flows_with_bulkbatch_action > 0 then true else false end has_bulkbatch_action,\n        case when n_flows_with_query_action > 0 then true else false end has_query_action,\n        case when (n_flows_with_bulkbatch_action > 0 or n_flows_with_query_action > 0) then false else true end is_single_action,\n\n        case when n_flows_db_table > 0 then true else false end has_db_table,\n        case when n_flows_collections > 0 then true else false end has_collections,\n        case when n_flows_variables > 0 then true else false end has_variables, \n        case when n_flows_lookup_table > 0 then true else false end has_lookup_table,\n        case when n_flows_has_scripting > 0 then true else false end has_scripting,\n\n        case when n_flows_has_sync           > 0 then true else false end has_sync_function,\n        case when n_flows_has_async          > 0 then true else false end has_async_function, \n        case when n_flows_has_looping        > 0 then true else false end has_looping_logic,\n        case when n_flows_if_then_logic      > 0 then true else false end has_if_then_logic, \n        case when n_flows_if_then_else_logic > 0 then true else false end has_if_then_else_logic,\n        \n        case when \n           (n_flows_has_sync           > 0 or\n            n_flows_has_async          > 0 or\n            n_flows_has_looping        > 0 or\n            n_flows_if_then_logic      > 0 or\n            n_flows_if_then_else_logic > 0) then false else true end is_pass_through,\n        case when n_flows_has_try_catch > 0 then true else false end has_try_catch_logic\n            \n    from rollup_recipe_ft3 rrft3\n    left join plg.chi_<anon>2023</anon>_recipe_hierarchy_operational rh\n        on rrft3.calendar_date = rh.calendar_date and rrft3.data_center = rh.data_center and rrft3.root_flow = rh.root_flow and rh.flow_id = rh.root_flow\n    left join plg.chi_<anon>2023</anon>_process_complexity_recipe_features_interim_operational rft\n        on rrft3.root_flow = rft.flow_id and rrft3.data_center = rft.data_center and rrft3.calendar_date = rft.calendar_date\n    left join rollup_apptier ruat\n        on rrft3.root_flow = ruat.root_flow and rrft3.data_center = ruat.data_center and rrft3.calendar_date = ruat.calendar_date\n    where 1=1\n    group by all\n    /* we have situations as such that require removal of rows where account_id is null (i.e cannot join to plg.chi_<anon>2023</anon>_process_complexity_recipe_features_interim\n    ** the process complexity recipe features table considers that (aka \"real active\")\n         - task consumed within 12 months of calendar date\n         - task consumed only after subscription start date of the account\n         - account_id of recipe in recipe_dim = account_id of flow in consumption_usage_fact\n         - and has at least 1 successful non test job given the above conditions. \n    1) Root recipes have not qualified as a real active recipe. In such cases we will remove them from consideration (i.e they have no jobs)\n    2A) Root recipes have consumed tasks, but they were not mapped to the correct account e.g see flow_id 48001806 - where account_id was not appearing at first.\n    2B) Root recipes belonging to customer A, and then customer B after that. Attribution of tasks is to diff customers. Given the specific calendar date, and the account ID tagged\n        to it, we are looking at diff account from the account that task was accrued to. e.g flow id 32253544 */\n    having account_id is not null  \n)\n\nselect *\nfrom rollup_recipe_features\n;", "update_only": "false"}, "block": []}, {"number": 5, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql_async_v2", "as": "171a0a26", "skip": true, "block": []}, {"number": 6, "keyword": "catch", "provider": "", "name": "", "as": "7f4abb25", "skip": false, "input": {"max_retry_count": "0", "retry_interval": "2"}, "block": [{"number": 7, "keyword": "action", "provider": "workato_recipe_function", "name": "return_result", "as": "6750cfd8", "skip": false, "input": {"result": {"status": "failed"}}, "block": []}, {"number": 8, "keyword": "stop", "provider": "", "name": "", "as": "a6f4c3df", "skip": false, "input": {"stop_reason": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"7f4abb25\",\"path\":[\"type\"]}')}, #{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"7f4abb25\",\"path\":[\"message\"]}')}", "stop_with_error": "true"}, "block": []}]}]}, {"number": 9, "keyword": "action", "provider": "workato_recipe_function", "name": "return_result", "as": "fdf1f721", "skip": false, "input": {"result": {"status": "success"}}, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (DECLARE_STEP_AS, "workato_variable", "declare_variable"),
    (SQL_STEP_AS, "snowflake", "run_custom_sql"),
    (CATCH_RETURN_AS, "workato_recipe_function", "return_result"),
    (SUCCESS_RETURN_AS, "workato_recipe_function", "return_result"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
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


def validate_130549037(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_130549037(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130549037(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (no trigger parameters "
            f"are declared or read): {trigger!r}"
        )
    now = data.get("now")
    if not isinstance(now, str) or not now.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} variant input must pin now (snap_date strftime)")
    parsed_now = datetime.datetime.fromisoformat(now.replace("Z", "+00:00"))
    if parsed_now.tzinfo is None:
        raise RuntimeError(f"recipe {RECIPE_ID} now must carry an explicit UTC offset: {now!r}")
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
        "now": now,
        "expect": deepcopy(expect),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_130549037(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130549037(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    if not str(seed.get("now") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing pinned now")
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
    result["verifier"] = verify_130549037(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_snowflake_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the SQL uses no current_date/current_timestamp, so no current_time)"
        )
    tables = section["tables"]
    expected_keys = sorted([TARGET_TABLE, INTERIM_TABLE, HIERARCHY_TABLE])
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
    _require_typed_table(tables[INTERIM_TABLE], INTERIM_TABLE, INTERIM_COLUMNS)
    _require_typed_table(tables[HIERARCHY_TABLE], HIERARCHY_TABLE, HIERARCHY_COLUMNS)


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
            if kind == "boolean" and not isinstance(value, bool):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table} row {idx} {column} must be boolean"
                )
            if kind == "number" and (isinstance(value, bool) or not isinstance(value, int)):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table} row {idx} {column} must be an integer"
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
