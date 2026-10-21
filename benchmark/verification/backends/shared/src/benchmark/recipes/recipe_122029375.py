from __future__ import annotations

import datetime
import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_122029375


RECIPE_ID = "122029375"
SEED_TYPE = "awp_error_monitoring_upsert_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "3cb8ebe2"
TABLE_ID = "22941"
GET_STEP_AS = "b42b94f0"
ADD_STEP_AS = "541d8b17"
UPDATE_STEP_AS = "f837811d"
RETURN_STEP_AS = "adb55c8a"
# Workato's built-in Record ID column (present in the live get/add/update
# output schemas). The mock stamps it on written rows ONLY when the seeder
# opts in via seed.workato_db_table.record_id_column — that flag is what
# fixes the triage-recorded gap (add-branch return_result.record_id was
# null before; replay-proved non-null on HEAD 80d400ce).
RECORD_ID_FIELD = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
FIELD_OPPORTUNITY_ID = "10757a15_4ad8_4803_a0d5_a4fb5c4cd715"
FIELD_OPPORTUNITY_NAME = "98172da9_d7ab_495a_94c5_3a990624cc5b"
FIELD_WU_OPPORTUNITY_ID = "2ef50623_658b_4865_8313_d7cb36dd9cd6"
FIELD_WU_EMAIL = "8037e991_6030_444a_814f_a6edfaa60946"
FIELD_PROVISIONING_TYPE = "0a27ae00_2609_40f7_bd31_9849efcf3221"
FIELD_STATUS = "5655a8a0_c22e_4149_b4ed_1a1f60e2017a"
FIELD_REQUEST_ID = "1a916688_0ba6_4d2f_aa4d_7edec4ab052b"
FIELD_WORKSPACE_ID = "67bce975_b9ff_4024_9ae8_03340dd707a7"
FIELD_DATA_CENTER = "00bcb999_193b_4dbe_8397_c9318b28a3ae"
FIELD_WORKSPACE_DETAILS = "abbf2d87_cf64_4721_8a87_6171b3829a84"
FIELD_ERROR_MESSAGE = "6dbb2499_b3ec_425f_a194_46d2130e91d3"
FIELD_ERROR_COUNT = "61bda534_ffe1_4c05_966d_fa4b69aee197"
FIELD_ACTION_EMAIL = "66f468b3_e889_436d_9b50_4caaeab621e3"
FIELD_SLACK_MESSAGE_ID = "a884b2c3_09e7_4772_8af1_388c697f1989"
FIELD_ERROR_CREATED_AT = "2331024f_31aa_4430_850b_6befd8836047"
FIELD_ERROR_RESOLVED_AT = "16590fef_c626_46a9_a5e2_458cb23a69b4"
FIELD_LAST_UPDATED = "22fca2b0_55b6_477f_9fe9_b50a34a4c9c7"
SEEDABLE_ROW_FIELDS = (
    RECORD_ID_FIELD,
    FIELD_OPPORTUNITY_ID,
    FIELD_OPPORTUNITY_NAME,
    FIELD_WU_OPPORTUNITY_ID,
    FIELD_WU_EMAIL,
    FIELD_PROVISIONING_TYPE,
    FIELD_STATUS,
    FIELD_REQUEST_ID,
    FIELD_WORKSPACE_ID,
    FIELD_DATA_CENTER,
    FIELD_WORKSPACE_DETAILS,
    FIELD_ERROR_MESSAGE,
    FIELD_ERROR_COUNT,
    FIELD_ACTION_EMAIL,
    FIELD_SLACK_MESSAGE_ID,
    FIELD_ERROR_CREATED_AT,
    FIELD_ERROR_RESOLVED_AT,
    FIELD_LAST_UPDATED,
)
REQUIRED_SEED_ROW_FIELDS = (
    RECORD_ID_FIELD,
    FIELD_WU_OPPORTUNITY_ID,
    FIELD_PROVISIONING_TYPE,
    FIELD_ERROR_COUNT,
)
TRIGGER_PARAMETERS = (
    "provisioning_type",
    "workato_user_email",
    "workato_user_opportunity_id",
    "opportunity_id",
    "opportunity_name",
    "repeated_job",
)

# workato_recipe_function.execute (as 3cb8ebe2; parameters provisioning_type/
# workato_user_email/workato_user_opportunity_id/opportunity_id/
# opportunity_name (strings) + repeated_job (boolean); result schema
# {found boolean, record_id string}):
#   2  workato_db_table.get_records b42b94f0 table 22941 '[AWP] Error
#      Monitoring' — filters eq workato_user_opportunity_id AND eq
#      provisioning_type (pill values; field ids dash->underscore
#      normalized), limit 100, order asc (mock returns seed order).
#   IF 3 (records size equals_to '0'):
#     4  workato_db_table.add_record 541d8b17: opportunity/user fields from
#        parameters, status 'New', error_count '1', error_created_at =
#        job_context.job_created_at pill, workspace_details '=' (empty
#        formula -> '').
#   ELSE 5:
#     6  workato_db_table.update_record f837811d: record_id = records
#        current_item Record ID; same fields minus status/error_created_at;
#        error_count = repeated_job.is_true? ? <current> : <current> + 1;
#        workspace_details '='.
#   7  workato_recipe_function.return_result adb55c8a (TERMINAL):
#      found = multiline 'if size == 0 false else true end';
#      record_id = add pill OR update pill — exactly one branch ran, the
#      other side is MISSING and the 'or' falls through to the present one.
#
# Semantics pinned by variants (probed/replayed on HEAD 80d400ce):
# - seed.workato_db_table.record_id_column: true (set by THIS seeder) makes
#   the mock stamp the built-in Record ID column (string of the row id) on
#   written rows AND in the add/update result record — the add branch then
#   returns the REAL new id (str(len(seeded rows))), never null.
# - error_count is an INT in every seeded row (typed integer column). A
#   string seed would string-join in the '+ 1' ternary arm ('3' + 1 ->
#   '31', probed); with int seeds the false arm renders the engine-
#   canonical STRING '4' while the true arm passes the INT 3 through.
# - both eq filters must match the same record (AND semantics): a row
#   matching only one filter is invisible to the recipe.
# - return_result is terminal: the trace never carries a stop row.
# Workato-internal backend (data table mock + recipe function): mock per
# backend policy, per-variant isolated, no cleanup.

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "workato_recipe_function", "name": "execute", "as": "3cb8ebe2", "skip": false, "input": {"parameters_schema_json": "[{\"name\":\"provisioning_type\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Provisioning type\"},{\"name\":\"workato_user_email\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Workato user email\"},{\"name\":\"workato_user_opportunity_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Workato user opportunity ID\"},{\"name\":\"opportunity_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Opportunity ID\"},{\"name\":\"opportunity_name\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Opportunity name\"},{\"name\":\"repeated_job\",\"type\":\"boolean\",\"optional\":false,\"control_type\":\"checkbox\",\"label\":\"Repeated job\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Repeated job\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"repeated_job\",\"type\":\"boolean\",\"optional\":false}}]", "result_schema_json": "[{\"name\":\"found\",\"type\":\"boolean\",\"optional\":false,\"control_type\":\"checkbox\",\"label\":\"Found\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Found\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"found\",\"type\":\"boolean\",\"optional\":false}},{\"name\":\"record_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Record ID\"}]"}, "block": [{"number": 2, "keyword": "action", "provider": "workato_db_table", "name": "get_records", "as": "b42b94f0", "skip": false, "input": {"00bcb999-193b-4dbe-8397-c9318b28a3ae": "string", "0a27ae00-2609-40f7-bd31-9849efcf3221": "string", "10757a15-4ad8-4803-a0d5-a4fb5c4cd715": "string", "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "16590fef-c626-46a9-a5e2-458cb23a69b4": "date_time", "1a916688-0ba6-4d2f-aa4d-7edec4ab052b": "string", "22fca2b0-55b6-477f-9fe9-b50a34a4c9c7": "date_time", "2331024f-31aa-4430-850b-6befd8836047": "date_time", "2ef50623-658b-4865-8313-d7cb36dd9cd6": "string", "5655a8a0-c22e-4149-b4ed-1a1f60e2017a": "string", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "61bda534-ffe1-4c05-966d-fa4b69aee197": "integer", "66f468b3-e889-436d-9b50-4caaeab621e3": "string", "67bce975-b9ff-4024-9ae8-03340dd707a7": "string", "6dbb2499-b3ec-425f-a194-46d2130e91d3": "string", "8037e991-6030-444a-814f-a6edfaa60946": "string", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "a884b2c3-09e7-4772-8af1-388c697f1989": "string", "abbf2d87-cf64-4721-8a87-6171b3829a84": "string", "filters": [{"field_id": "2ef50623-658b-4865-8313-d7cb36dd9cd6", "op_default": "eq", "value_default": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"3cb8ebe2\",\"path\":[\"parameters\", \"workato_user_opportunity_id\"]}')}"}, {"field_id": "0a27ae00-2609-40f7-bd31-9849efcf3221", "op_default": "eq", "value_default": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"3cb8ebe2\",\"path\":[\"parameters\", \"provisioning_type\"]}')}"}], "limit": "100", "order_direction": "asc", "table_id": "22941"}, "block": []}, {"number": 3, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"b42b94f0\",\"path\":[\"records\", {\"path_element_type\": \"size\"}]}')}", "operand": "equals_to", "rhs": "0"}], "operand": "and", "type": "compound"}, "block": [{"number": 4, "keyword": "action", "provider": "workato_db_table", "name": "add_record", "as": "541d8b17", "skip": false, "input": {"parameters": {"0a27ae00_2609_40f7_bd31_9849efcf3221": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"3cb8ebe2\",\"path\":[\"parameters\", \"provisioning_type\"]}')}", "10757a15_4ad8_4803_a0d5_a4fb5c4cd715": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"3cb8ebe2\",\"path\":[\"parameters\", \"opportunity_id\"]}')}", "2331024f_31aa_4430_850b_6befd8836047": "#{_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_created_at\"]}')}", "2ef50623_658b_4865_8313_d7cb36dd9cd6": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"3cb8ebe2\",\"path\":[\"parameters\", \"workato_user_opportunity_id\"]}')}", "5655a8a0_c22e_4149_b4ed_1a1f60e2017a": "New", "61bda534_ffe1_4c05_966d_fa4b69aee197": "1", "8037e991_6030_444a_814f_a6edfaa60946": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"3cb8ebe2\",\"path\":[\"parameters\", \"workato_user_email\"]}')}", "98172da9_d7ab_495a_94c5_3a990624cc5b": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"3cb8ebe2\",\"path\":[\"parameters\", \"opportunity_name\"]}')}", "abbf2d87_cf64_4721_8a87_6171b3829a84": "="}, "table_id": "22941"}, "block": []}, {"number": 5, "keyword": "else", "provider": "", "name": "", "as": "", "skip": false, "input": {}, "block": [{"number": 6, "keyword": "action", "provider": "workato_db_table", "name": "update_record", "as": "f837811d", "skip": false, "input": {"parameters": {"0a27ae00_2609_40f7_bd31_9849efcf3221": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"3cb8ebe2\",\"path\":[\"parameters\", \"provisioning_type\"]}')}", "10757a15_4ad8_4803_a0d5_a4fb5c4cd715": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"3cb8ebe2\",\"path\":[\"parameters\", \"opportunity_id\"]}')}", "2ef50623_658b_4865_8313_d7cb36dd9cd6": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"3cb8ebe2\",\"path\":[\"parameters\", \"workato_user_opportunity_id\"]}')}", "61bda534_ffe1_4c05_966d_fa4b69aee197": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"3cb8ebe2\",\"path\":[\"parameters\",\"repeated_job\"]}').is_true? ? _dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"b42b94f0\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"61bda534_ffe1_4c05_966d_fa4b69aee197\"]}') : _dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"b42b94f0\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"61bda534_ffe1_4c05_966d_fa4b69aee197\"]}') + 1", "8037e991_6030_444a_814f_a6edfaa60946": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"3cb8ebe2\",\"path\":[\"parameters\", \"workato_user_email\"]}')}", "98172da9_d7ab_495a_94c5_3a990624cc5b": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"3cb8ebe2\",\"path\":[\"parameters\", \"opportunity_name\"]}')}", "abbf2d87_cf64_4721_8a87_6171b3829a84": "="}, "record_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"b42b94f0\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\"]}')}", "table_id": "22941"}, "block": []}]}]}, {"number": 7, "keyword": "action", "provider": "workato_recipe_function", "name": "return_result", "as": "adb55c8a", "skip": false, "input": {"result": {"found": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"b42b94f0\",\"path\":[\"records\",{\"path_element_type\":\"size\"}]}') == 0\nfalse\nelse\ntrue\nend", "record_id": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"541d8b17\",\"path\":[\"record\",\"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\"]}') or _dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"f837811d\",\"path\":[\"record\",\"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\"]}')"}}, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (GET_STEP_AS, "workato_db_table", "get_records"),
    (ADD_STEP_AS, "workato_db_table", "add_record"),
    (UPDATE_STEP_AS, "workato_db_table", "update_record"),
    (RETURN_STEP_AS, "workato_recipe_function", "return_result"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.add_record",
    "workato_db_table.update_record",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.add_record",
    "workato_db_table.update_record",
    "workato_recipe_function.return_result",
]
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "branch",
    "returned_result",
    "final_table_rows",
)


def validate_122029375(raw: dict[str, Any]) -> dict[str, Any]:
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
    for step_as in (GET_STEP_AS, ADD_STEP_AS, UPDATE_STEP_AS):
        node = _node_by_as(raw, step_as)
        if str((node.get("input") or {}).get("table_id") or "") != TABLE_ID:
            raise RuntimeError(
                f"recipe {RECIPE_ID} step {step_as} no longer targets table {TABLE_ID!r}"
            )
    update = _node_by_as(raw, UPDATE_STEP_AS)
    count_formula = str(
        ((update.get("input") or {}).get("parameters") or {}).get(FIELD_ERROR_COUNT) or ""
    )
    if ".is_true? ?" not in count_formula or not count_formula.endswith(" + 1"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} repeated_job error_count ternary changed: {count_formula!r}"
        )
    record_id_pill = str((update.get("input") or {}).get("record_id") or "")
    if RECORD_ID_FIELD not in record_id_pill:
        raise RuntimeError(
            f"recipe {RECIPE_ID} update no longer targets the built-in Record ID column"
        )
    add = _node_by_as(raw, ADD_STEP_AS)
    add_parameters = (add.get("input") or {}).get("parameters") or {}
    if add_parameters.get(FIELD_STATUS) != "New" or add_parameters.get(FIELD_ERROR_COUNT) != "1":
        raise RuntimeError(f"recipe {RECIPE_ID} add-branch literals changed: {add_parameters!r}")
    if "job_context" not in str(add_parameters.get(FIELD_ERROR_CREATED_AT) or ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} add-branch error_created_at no longer reads job_context"
        )
    return_node = _node_by_as(raw, RETURN_STEP_AS)
    result_input = (return_node.get("input") or {}).get("result") or {}
    record_id_formula = str(result_input.get("record_id") or "")
    if f'"{ADD_STEP_AS}"' not in record_id_formula or f'"{UPDATE_STEP_AS}"' not in record_id_formula or " or " not in record_id_formula:
        raise RuntimeError(
            f"recipe {RECIPE_ID} return record_id add-or-update formula changed: "
            f"{record_id_formula!r}"
        )
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "table_id": TABLE_ID,
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


def seed_122029375(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_122029375(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    job_context = data.get("job_context")
    _require_job_context(job_context)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["workato_db_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the workato_db_table section; "
            f"got {sorted(seed_in.keys()) if isinstance(seed_in, dict) else seed_in!r}"
        )
    rows = _require_table_section(seed_in["workato_db_table"])
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    _require_expect_coherence(trigger, rows, expect)
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole "
            "run instead of exercising a recipe branch"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        # Builder-side opt-in: stamp Workato's built-in Record ID column on
        # written rows + write results, matching the live output schema (the
        # add-branch return_result.record_id pins the real id, never null).
        "workato_db_table": {
            "record_id_column": True,
            "tables": {TABLE_ID: deepcopy(rows)},
        },
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_122029375(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_122029375(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    table_section = seed.get("workato_db_table")
    if not isinstance(table_section, dict) or table_section.get("record_id_column") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed file must carry workato_db_table.record_id_column "
            "true (the add-branch record_id groundtruth depends on it)"
        )
    if not isinstance(seed.get("job_context"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing job_context")
    initial_snapshot = _snapshot(ctx)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = _snapshot(ctx)
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "expect": seed.get("expect"),
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_122029375(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != ["parameters"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the parameters object; "
            f"got {sorted(trigger.keys())}"
        )
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict) or sorted(parameters.keys()) != sorted(TRIGGER_PARAMETERS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must carry exactly "
            f"{sorted(TRIGGER_PARAMETERS)} (all declared non-optional); got "
            f"{sorted(parameters.keys()) if isinstance(parameters, dict) else parameters!r}"
        )
    for key in TRIGGER_PARAMETERS:
        value = parameters[key]
        if key == "repeated_job":
            if not isinstance(value, bool):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} parameters.repeated_job must be a JSON boolean "
                    f"(boolean_conversion checkbox); got {value!r}"
                )
            continue
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} parameters.{key} must be a non-empty string; got {value!r}"
            )


def _require_job_context(job_context: Any) -> None:
    if not isinstance(job_context, dict) or sorted(job_context.keys()) != ["job_created_at"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must carry job_context with exactly "
            f"job_created_at (the add branch stamps it); got {job_context!r}"
        )
    value = job_context["job_created_at"]
    try:
        parsed = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(
            f"recipe {RECIPE_ID} job_context.job_created_at must be an ISO datetime: "
            f"{value!r}"
        ) from exc
    if parsed.tzinfo is None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} job_context.job_created_at must carry an explicit "
            f"offset: {value!r}"
        )


def _require_table_section(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table must be exactly {{'tables': ...}} "
            "(the seeder itself sets record_id_column)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed tables must declare exactly table {TABLE_ID!r} "
            "(rows may be an explicit empty list)"
        )
    rows = tables[TABLE_ID]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {TABLE_ID} rows must be a list")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table row {idx} must be an object")
        unknown = sorted(set(row.keys()) - set(SEEDABLE_ROW_FIELDS))
        if unknown:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} has unknown columns: {unknown}"
            )
        missing = [key for key in REQUIRED_SEED_ROW_FIELDS if key not in row]
        if missing:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} is missing required columns "
                f"{missing} (Record ID + both filter fields + error_count)"
            )
        if row[RECORD_ID_FIELD] != str(idx):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} must seed Record ID {str(idx)!r} "
                f"(the mock's row-id stamp — a mismatched seed would desync the update "
                f"read-back); got {row[RECORD_ID_FIELD]!r}"
            )
        count = row[FIELD_ERROR_COUNT]
        if not isinstance(count, int) or isinstance(count, bool):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} error_count must be an INT "
                f"(string-seeded counts string-join in the '+ 1' arm: '3' + 1 -> '31'); "
                f"got {count!r}"
            )
        for key, value in row.items():
            if key == FIELD_ERROR_COUNT:
                continue
            if not isinstance(value, str):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table row {idx}.{key} must be a string; got {value!r}"
                )
    return rows


def _require_expect_coherence(
    trigger: dict[str, Any],
    rows: list[dict[str, Any]],
    expect: dict[str, Any],
) -> None:
    # The branch is fully determined by the seeded rows vs the two eq filters
    # (AND semantics, replay-verified) — the authored expect may never
    # contradict it.
    parameters = trigger["parameters"]
    matches = [
        row
        for row in rows
        if row.get(FIELD_WU_OPPORTUNITY_ID) == parameters["workato_user_opportunity_id"]
        and row.get(FIELD_PROVISIONING_TYPE) == parameters["provisioning_type"]
    ]
    branch = "add" if not matches else "update"
    if expect.get("branch") != branch:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.branch is {expect.get('branch')!r} but the seeded "
            f"rows/filters produce the {branch!r} branch ({len(matches)} match(es))"
        )
    if expect.get("executed_action_count") != 3:
        raise RuntimeError(
            f"recipe {RECIPE_ID} both branches execute exactly 3 actions "
            f"(get + write + return); got {expect.get('executed_action_count')!r}"
        )
    returned = expect.get("returned_result")
    if not isinstance(returned, dict) or sorted(returned.keys()) != ["found", "record_id"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.returned_result must be {{found, record_id}}; "
            f"got {returned!r}"
        )
    if branch == "add":
        expected_id = str(len(rows))
        if returned.get("found") is not False or returned.get("record_id") != expected_id:
            raise RuntimeError(
                f"recipe {RECIPE_ID} add-branch returned_result must be "
                f"{{found: false, record_id: {expected_id!r}}} (the mock's next row id); "
                f"got {returned!r}"
            )
    else:
        if len(matches) != 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} update variants must seed exactly ONE matching "
                f"record (the recipe updates records.first); got {len(matches)}"
            )
        expected_id = str(matches[0][RECORD_ID_FIELD])
        if returned.get("found") is not True or returned.get("record_id") != expected_id:
            raise RuntimeError(
                f"recipe {RECIPE_ID} update-branch returned_result must be "
                f"{{found: true, record_id: {expected_id!r}}}; got {returned!r}"
            )
    final_rows = expect.get("final_table_rows")
    expected_final_count = len(rows) + (1 if branch == "add" else 0)
    if not isinstance(final_rows, list) or len(final_rows) != expected_final_count:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_table_rows must list exactly "
            f"{expected_final_count} rows (seeds {'+ the added record' if branch == 'add' else 'with the matched record updated in place'})"
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


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return ctx.tools.call("harness.workato_db_table.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
