from __future__ import annotations

import datetime
import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_130549575


RECIPE_ID = "130549575"
SEED_TYPE = "chi_2023_process_complexity_scores_ctas_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "d5a45675"
DECLARE_STEP_AS = "70d77402"
SQL_STEP_AS = "66f12abe"
ASYNC_STEP_AS = "171a0a26"
CATCH_RETURN_AS = "e5f6e2ad"
STOP_STEP_AS = "2fd1fda3"
SUCCESS_RETURN_AS = "fdf1f721"
TARGET_TABLE = "plg.chi_2023_process_complexity_scores_operational"
FEATURES_TABLE = "plg.chi_2023_process_complexity_recipe_features_operational"
MATRIX_TABLE = "plg.chi_2023_process_complexity_scoring_matrix"
FEATURES_COLUMNS = {
    "calendar_date": "date",
    "account_id": "string",
    "account_name": "string",
    "root_flow": "string",
    "data_center": "string",
    "recipe_category_type": "string",
    "n_downstream_steps": "number",
    "n_flows_in_workflow": "number",
    "tier_1_apps": "string",
    "tier_2_apps": "string",
    "tier_3_apps": "string",
    "tier_4_apps": "string",
    "tier_5_apps": "string",
    "trigger_type": "string",
    "has_bulkbatch_action": "boolean",
    "has_query_action": "boolean",
    "is_single_action": "boolean",
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
    "is_pass_through": "boolean",
    "has_try_catch_logic": "boolean",
    "num_tier_1_app": "number",
    "num_tier_2_app": "number",
    "num_tier_3_app": "number",
    "num_tier_4_app": "number",
    "num_tier_5_app": "number",
}
MATRIX_COLUMNS = {
    "criteria_cat": "string",
    "sub_criteria_cat": "string",
    "value": "string",
    "score": "string",
    "weight": "number",
}


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "workato_recipe_function", "name": "execute", "as": "d5a45675", "skip": false, "input": {"result_schema_json": "[{\"name\":\"status\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Status\"}]"}, "block": [{"number": 2, "keyword": "action", "provider": "workato_variable", "name": "declare_variable", "as": "70d77402", "skip": false, "input": {"variables": {"data": {"snap_date": "=now.strftime(\"%Y-%m-%d\")"}, "schema": "[{\"name\":\"snap_date\",\"type\":\"string\",\"optional\":true,\"label\":\"snap_date\",\"details\":{\"real_name\":\"snap_date\"},\"control_type\":\"text\"}]"}}, "block": []}, {"number": 3, "keyword": "try", "provider": "", "name": "", "as": "", "skip": false, "input": {}, "block": [{"number": 4, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql", "as": "66f12abe", "skip": false, "input": {"sql": "create or replace table plg.chi_<anon>2023</anon>_process_complexity_scores_operational as \nwith process_length_interim as (\n    select r.calendar_date, r.root_flow, r.data_center, r.n_downstream_steps, s.value value_to_find, s.score score_sort\n        , rank() over (partition by r.calendar_date, r.root_flow, r.n_downstream_steps order by score_sort::number asc) v_rank\n    from plg.chi_<anon>2023</anon>_process_complexity_recipe_features_operational r\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix s\n        on r.n_downstream_steps <= s.value\n        and s.sub_criteria_cat = 'num_steps' and criteria_cat = 'general'\n    qualify v_rank = 1\n)\n\n, process_length_score as (\n    select calendar_date, root_flow, data_center, n_downstream_steps, value_to_find\n    from process_length_interim\n    group by all\n)\n\n, app_tier_pivot_scores as (\n    select calendar_date, root_flow, data_center,\n        num_tier_1_app, \n        num_tier_2_app, \n        num_tier_3_app, \n        num_tier_4_app, \n        num_tier_5_app,\n        case when num_tier_1_app = 0 then 0 else min(atm1.score::number) * min(atm1.weight) end at1_score,\n        case when num_tier_2_app = 0 then 0 else min(atm2.score::number) * min(atm2.weight) end at2_score,\n        case when num_tier_3_app = 0 then 0 else min(atm3.score::number) * min(atm3.weight) end at3_score,\n        case when num_tier_4_app = 0 then 0 else min(atm4.score::number) * min(atm4.weight) end at4_score,\n        case when num_tier_5_app = 0 then 0 else min(atm5.score::number) * min(atm5.weight) end at5_score\n    from plg.chi_<anon>2023</anon>_process_complexity_recipe_features_operational r\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix atm1 on r.num_tier_1_app::number <= atm1.value::number and atm1.criteria_cat = 'app_tier' and atm1.sub_criteria_cat = 1\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix atm2 on r.num_tier_2_app::number <= atm2.value::number and atm2.criteria_cat = 'app_tier' and atm2.sub_criteria_cat = 2\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix atm3 on r.num_tier_3_app::number <= atm3.value::number and atm3.criteria_cat = 'app_tier' and atm3.sub_criteria_cat = 3\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix atm4 on r.num_tier_4_app::number <= atm4.value::number and atm4.criteria_cat = 'app_tier' and atm4.sub_criteria_cat = 4\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix atm5 on r.num_tier_5_app::number <= atm5.value::number and atm5.criteria_cat = 'app_tier' and atm5.sub_criteria_cat = 5\n    group by all\n)\n\n, app_tier_section as (\n    select calendar_date, root_flow, data_center,\n        (greatest( at1_score, at2_score, at3_score, at4_score, at5_score)) + \n         (((at1_score+ at2_score+ at3_score+at4_score+ at5_score) - (greatest( at1_score, at2_score, at3_score, at4_score, at5_score))) / 30) app_tier_section_score\n    from app_tier_pivot_scores\n    group by all\n)\n\n, final as (\n    select b.calendar_date,b.account_id, b.account_name, b.root_flow, b.data_center\n        , b.recipe_category_type\n        , b.n_downstream_steps\n        , b.n_flows_in_workflow\n        , trim(replace(replace(concat_ws(',', coalesce(b.tier_1_apps, ''), coalesce(b.tier_2_apps, ''), coalesce(b.tier_3_apps, ''), coalesce(b.tier_4_apps, ''), coalesce(b.tier_5_apps, '')),',,', ','), ',,', ','),',') apps_used,\n\n        b.trigger_type,\n        b.has_bulkbatch_action,\n        b.has_query_action,\n        b.is_single_action,\n        b.has_collections,\n        b.has_variables,\n        b.has_lookup_table,\n        b.has_scripting,\n        b.has_sync_function,\n        b.has_async_function,\n        b.has_looping_logic,\n        b.has_if_then_logic,\n        b.has_if_then_else_logic,\n        b.is_pass_through,\n        b.has_try_catch_logic,\n        num_tier_1_app,\n        num_tier_2_app,\n        num_tier_3_app,\n        num_tier_4_app,\n        num_tier_5_app,\n\n\n        /*scores*/\n        (recipe_type_matrix.score * recipe_type_matrix.weight) recipe_type_score, //GENERAL recipe_type_score\n        (num_steps_matrix.score   * num_steps_matrix.weight) num_steps_score, //GENERAL num_steps_score\n    \n    /* old section of # standard connectors etc*/\n    -- case when rs.num_standard_conn = 0 then 0 else (num_standard_conn_cte.stan_conn_value * num_standard_conn_cte.stan_conn_weight) end as stan_conn_score, // num_stan_conn_score\n    -- num_custom_conn_cte.custom_conn_score, //custom connector score\n    -- num_http_conn_cte.http_conn_score, // http conn score\n    \n        (trigger_matrix.score * trigger_matrix.weight) trigger_type_score, //trigger type\n        case when b.has_bulkbatch_action = false then 0 else (dp1.score * dp1.weight) end as bulkbatch_score, // bulkbatch\n        case when b.has_query_action = false then 0 else (dp2.score * dp2.weight) end as query_action_score, // query action\n        case when b.is_single_action = false then 0 else (dp3.score * dp3.weight) end as single_action_score, // single action\n        \n        case when b.has_collections = false then 0 else (dp4.score * dp4.weight) end as has_collections_score, // collections\n        case when b.has_variables = false then 0 else (dp5.score * dp5.weight) end as has_variables_score, // variables\n        case when b.has_lookup_table = false then 0 else (dp6.score * dp6.weight) end as has_lookup_table_score, // lookup tables\n        case when b.has_scripting = false then 0 else (dp7.score * dp7.weight) end as has_scripting_score, // scripting\n        \n        case when b.has_sync_function = false then 0 else (sl1.score * sl1.weight) end as has_sync_function_score, // sync function\n        case when b.has_async_function = false then 0 else (sl2.score * sl2.weight) end as has_async_function_score, // async function\n        case when b.has_looping_logic = false then 0 else (sl3.score * sl3.weight) end as has_loop_score, // loop\n        case when b.has_if_then_logic = false then 0 else (sl4.score * sl4.weight) end as if_then_score, // if then\n        case when b.has_if_then_else_logic = false then 0 else (sl5.score * sl5.weight) end as if_then_else_score, // if then else\n        case when b.is_pass_through = false then 0 else (sl6.score * sl6.weight) end as pass_through_score, // pass-through\n        case when b.has_try_catch_logic = false then 0 else (sl7.score * sl7.weight) end as try_catch_score, // try-catch\n\n        case \n            when b.has_async_function = true and b.has_sync_function = true then (has_async_function_score + has_loop_score + if_then_score + if_then_else_score + pass_through_score + try_catch_score)\n            else (has_sync_function_score + has_async_function_score + has_loop_score + if_then_score + if_then_else_score + pass_through_score + try_catch_score) \n        end as step_logic_score, //step logic \n\n\n         /* section scores */\n        recipe_type_score as general_type_section_score, //general section - recipe type score\n        num_steps_score as general_steps_section_score, //general section - # steps score\n    -- case when (stan_conn_score + custom_conn_score + http_conn_score) > 10 then 10 else (stan_conn_score + custom_conn_score + http_conn_score) end connections_section_score, // conn       score  -- this is old\n        (\n            trigger_type_score + \n            (case \n                when (bulkbatch_score + query_action_score + single_action_score) > 10 then 10\n            else (bulkbatch_score + query_action_score + single_action_score) end \n                + \n            case\n                when (has_collections_score + has_variables_score + has_lookup_table_score + has_scripting_score) > 10 then 10 \n                else (has_collections_score + has_variables_score + has_lookup_table_score + has_scripting_score) end \n            )\n        ) data_proc_section_score, // data proc + transformation\n        \n    step_logic_score as step_logic_section_score, //step logic score (repeat from above)\n    ats.app_tier_section_score, // app_tier_score\n\n\n    // section complexity\n    ( (general_type_section_score * 10 )/ general_weight_matrix_type.value ) general_complexity_recipe_type,\n    ( (general_steps_section_score * 10) / general_weight_matrix_steps.value ) general_complexity_steps,\n    ( (data_proc_section_score * 10) / data_proc_weight_matrix.value) data_proc_complexity, \n    ( (step_logic_section_score *10) / step_logic_weight_matrix.value) step_logic_complexity, \n    ( (app_tier_section_score * 10) / app_tier_weight_matrix.value) app_tier_complexity,\n\n     // final/overall complexity\n    (\n        (general_complexity_recipe_type * general_weight_matrix_type.weight) +\n        (general_complexity_steps * general_weight_matrix_steps.weight) + \n        (data_proc_complexity * data_proc_weight_matrix.weight) + \n        (step_logic_complexity * step_logic_weight_matrix.weight) + \n        (app_tier_complexity * app_tier_weight_matrix.weight) \n    ) overall_raw,\n    \n    round(overall_raw, 2) overall_complexity\n    \n    \n    from plg.chi_<anon>2023</anon>_process_complexity_recipe_features_operational b\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix recipe_type_matrix on b.recipe_category_type = recipe_type_matrix.value and recipe_type_matrix.sub_criteria_cat = 'recipe_type' // recipe type\n    left join process_length_score nsc on nsc.root_flow = b.root_flow and nsc.calendar_date = b.calendar_date and nsc.data_center = b.data_center\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix num_steps_matrix on num_steps_matrix.sub_criteria_cat = 'num_steps' and num_steps_matrix.criteria_cat = 'general' and num_steps_matrix.value = nsc.value_to_find //num steps\n    -- left join num_standard_conn_cte on num_standard_conn_cte.flow_id_standard_conn = rs.flow_id /*# stan connectors*/ and num_standard_conn_cte.entry_date = rs.entry_date\n    -- left join num_custom_conn_cte on num_custom_conn_cte.flow_id_custom_conn = rs.flow_id /* #custom connectors */ and num_custom_conn_cte.entry_date = rs.entry_date\n    -- left join num_http_conn_cte on num_http_conn_cte.flow_id_http_conn = rs.flow_id /* # http_sftp_rest connectors */ and num_http_conn_cte.entry_date = rs.entry_date\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix trigger_matrix on b.trigger_type = trigger_matrix.value and trigger_matrix.sub_criteria_cat = 'trigger_type' // trigger_type\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix dp1 on b.has_bulkbatch_action = dp1.value and dp1.sub_criteria_cat = 'has_bulkbatch_action' // bulkbatch action\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix dp2 on b.has_query_action = dp2.value and dp2.sub_criteria_cat = 'has_query_action' // query action\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix dp3 on b.is_single_action = dp3.value and dp3.sub_criteria_cat = 'is_single_action' // single action\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix dp0 on b.has_db_table = dp0.value and dp0.sub_criteria_cat = 'has_db_table' // db tables\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix dp4 on b.has_collections = dp4.value and dp4.sub_criteria_cat = 'has_collections' // collections\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix dp5 on b.has_variables = dp5.value and dp5.sub_criteria_cat = 'has_variables' // variables\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix dp6 on b.has_lookup_table = dp6.value and dp6.sub_criteria_cat = 'has_lookup_table' // lookup tables\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix dp7 on b.has_scripting = dp7.value and dp7.sub_criteria_cat = 'has_scripting' // scripting\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix sl1 on b.has_sync_function = sl1.value and sl1.sub_criteria_cat = 'has_sync_function' // sync function\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix sl2 on b.has_async_function = sl2.value and sl2.sub_criteria_cat = 'has_async_function' // a-sync function\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix sl3 on b.has_looping_logic = sl3.value and sl3.sub_criteria_cat = 'has_looping_logic' // looping logic\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix sl4 on b.has_if_then_logic = sl4.value and sl4.sub_criteria_cat = 'has_if_then_logic' // if_then \n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix sl5 on b.has_if_then_else_logic = sl5.value and sl5.sub_criteria_cat = 'has_if_then_else_logic' // if-then/else\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix sl6 on b.is_pass_through = sl6.value and sl6.sub_criteria_cat = 'is_pass_through' // is pass through\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix sl7 on b.has_try_catch_logic = sl7.value and sl7.sub_criteria_cat = 'has_try_catch_logic' // try-catch\n    -- left join tiered_applications ta on rs.flow_id = ta.flow_id_tiered_app and ta.entry_date = rs.entry_date\n    left join app_tier_section ats on b.root_flow = ats.root_flow and ats.calendar_date = b.calendar_date and ats.data_center = b.data_center\n    -- left join app_tier_pivot_scores atps on rs.flow_id = atps.flow_id and atps.entry_date = rs.entry_date\n    \n    // join section weights\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix general_weight_matrix_type on general_weight_matrix_type.sub_criteria_cat = 'general_type'\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix general_weight_matrix_steps on general_weight_matrix_steps.sub_criteria_cat = 'general_steps'\n    -- left join plg.recipe_sophistication_matrix connections_weight_matrix on connections_weight_matrix.sub_criteria_cat = 'connections'\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix data_proc_weight_matrix on data_proc_weight_matrix.sub_criteria_cat = 'data_proc'\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix step_logic_weight_matrix on step_logic_weight_matrix.sub_criteria_cat = 'step_logic'\n    left join plg.chi_<anon>2023</anon>_process_complexity_scoring_matrix app_tier_weight_matrix on app_tier_weight_matrix.sub_criteria_cat = 'app_tier'\n\n    group by all\n)\n\nselect *\nfrom final\ngroup by all\n\n;", "update_only": "false"}, "block": []}, {"number": 5, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql_async_v2", "as": "171a0a26", "skip": true, "block": []}, {"number": 6, "keyword": "catch", "provider": "", "name": "", "as": "0df25e1b", "skip": false, "input": {"max_retry_count": "0", "retry_interval": "2"}, "block": [{"number": 7, "keyword": "action", "provider": "workato_recipe_function", "name": "return_result", "as": "e5f6e2ad", "skip": false, "input": {"result": {"status": "failed"}}, "block": []}, {"number": 8, "keyword": "stop", "provider": "", "name": "", "as": "2fd1fda3", "skip": false, "input": {"stop_reason": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"0df25e1b\",\"path\":[\"type\"]}')}, #{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"0df25e1b\",\"path\":[\"message\"]}')}", "stop_with_error": "true"}, "block": []}]}]}, {"number": 9, "keyword": "action", "provider": "workato_recipe_function", "name": "return_result", "as": "fdf1f721", "skip": false, "input": {"result": {"status": "success"}}, "block": []}]}"""
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


def validate_130549575(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_130549575(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130549575(raw)
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


def run_130549575(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130549575(raw)
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
    result["verifier"] = verify_130549575(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_snowflake_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the SQL uses no current_date/current_timestamp, so no current_time)"
        )
    tables = section["tables"]
    expected_keys = sorted([TARGET_TABLE, FEATURES_TABLE, MATRIX_TABLE])
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
    _require_typed_table(tables[FEATURES_TABLE], FEATURES_TABLE, FEATURES_COLUMNS)
    _require_typed_table(tables[MATRIX_TABLE], MATRIX_TABLE, MATRIX_COLUMNS)
    for idx, row in enumerate(tables[MATRIX_TABLE]["rows"]):
        if not isinstance(row.get("weight"), int) or isinstance(row.get("weight"), bool):
            raise RuntimeError(
                f"recipe {RECIPE_ID} matrix row {idx} weight must be an integer (NUMBER "
                f"column is scale-0; fractional weights would silently round live): {row!r}"
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
