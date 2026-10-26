from __future__ import annotations

import datetime
import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe, shift_months
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_127982810


RECIPE_ID = "127982810"
SEED_TYPE = "agentic_itgenie_monthly_process_metrics_variant"
TRACK = "workato_db_monthly_process_metrics"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "01defda5"
USAGE_TABLE_ID = "37040"
CONV_TABLE_ID = "34765"
SINK_TABLE_ID = "37039"
CREATED_AT_COL = "a5612739_5401_4ae7_bd07_782c1a6fb2d1"
GENIE_COL = "a3c19569_a685_4ad4_b181_726a52c25919"
EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("dda3ad96", "workato_variable", "declare_variable"),
    ("d8e2644f", "workato_variable", "declare_list"),
    ("e9a69756", "workato_db_table", "get_records"),
    ("4e440342", "workato_variable", "insert_to_list_batch"),
    ("58e05796", "workato_variable", "update_variables"),
    ("081b7c80", "workato_variable", "declare_variable"),
    ("4001b581", "workato_variable", "declare_list"),
    ("9d4f7dca", "workato_db_table", "get_records"),
    ("d1fe1903", "workato_variable", "insert_to_list_batch"),
    ("caa690d5", "workato_variable", "update_variables"),
    ("2286b831", "workato_variable", "declare_variable"),
    ("cc1734de", "workato_variable", "declare_variable"),
    ("48f84dd7", "workato_variable", "declare_variable"),
    ("1a865f7f", "workato_db_table", "add_record"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "workato_runtime.declare_list",
    "workato_db_table.get_records",
    "workato_runtime.insert_to_list_batch",
    "workato_runtime.update_variables",
    "workato_db_table.add_record",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.add_record",
]
_EXPECT_ITEM_KEYS = {
    "tool", "table_id", "lookup_table_id", "match_fields", "channel",
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
}
_EXPECT_VALUE_KEYS = {
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
}

_RAW_PIN_JSON = r"""{"as": "01defda5", "block": [{"as": "dda3ad96", "block": [], "input": {"variables": {"data": {"period_end": "=1.days.ago", "period_start": "=1.months.ago"}, "schema": "[{\"control_type\":\"text\",\"label\":\"period_start\",\"name\":\"period_start\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"period_start\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"text\",\"label\":\"period_end\",\"name\":\"period_end\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"period_end\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"name\":\"next_token\",\"type\":\"string\",\"optional\":true,\"label\":\"next_token\",\"details\":{\"real_name\":\"next_token\"},\"control_type\":\"text\",\"parent\":[\"variables\",\"data\"]}]"}}, "keyword": "action", "name": "declare_variable", "number": 2, "provider": "workato_variable", "skip": false}, {"as": "d8e2644f", "block": [], "input": {"list_item_schema_json": "[{\"name\":\"process_id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Process ID\"},{\"name\":\"action_category\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Action category\"},{\"name\":\"ticket_resolution_time\",\"type\":\"integer\",\"optional\":true,\"control_type\":\"integer\",\"label\":\"Ticket resolution time\",\"parse_output\":\"integer_conversion\"},{\"name\":\"ticket_created_by\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Ticket created by\"}]", "name": "Usage Metrics"}, "keyword": "action", "name": "declare_list", "number": 3, "provider": "workato_variable", "skip": false}, {"as": "15d1c62b", "block": [{"as": "e9a69756", "block": [], "input": {"0104b7ef-de3c-4a5f-ba6b-c1ddc4bc6f17": "string", "045d2afd-0012-4bbc-a53d-b4008c51179b": "string", "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "211810bd-e2db-4feb-b058-41337cb362a1": "string", "265ff871-ab3e-4c7d-9e1a-31c20636a96c": "string", "3323868d-d1f3-4ff1-8b8e-35aed4265162": "boolean", "351b4fb5-864b-47da-89e6-30433d1ecc70": "integer", "4c816268-1553-4ec9-a667-6322dd4cbc9e": "string", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "69527934-bfb0-4080-a583-b2c931c8c6f4": "boolean", "7469ad3d-9dd3-48cc-b2dd-4c3b5c4afa10": "string", "77394afc-f172-4058-86ed-5a786c86d4bb": "string", "921f48e9-6692-4c1f-93ae-19d2c3a2237b": "string", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "continuation_token": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"dda3ad96\",\"path\":[\"next_token\"]}').presence", "dcca5c9e-25f1-46c6-ae80-ec07f872e9a6": "string", "filters": [{"field_id": "a5612739-5401-4ae7-bd07-782c1a6fb2d1", "op_date_time": "gte", "value_date_time": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"dda3ad96\",\"path\":[\"period_start\"]}')"}], "limit": "200", "order_direction": "asc", "table_id": "37040"}, "keyword": "action", "name": "get_records", "number": 5, "provider": "workato_db_table", "skip": false}, {"as": "4e440342", "block": [], "input": {"list_items": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"e9a69756\",\"path\":[\"records\"]}')}", "action_category": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"e9a69756\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"921f48e9_6692_4c1f_93ae_19d2c3a2237b\"]}')}", "process_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"e9a69756\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"211810bd_e2db_4feb_b058_41337cb362a1\"]}')}", "ticket_created_by": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"e9a69756\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"7469ad3d_9dd3_48cc_b2dd_4c3b5c4afa10\"]}')}", "ticket_resolution_time": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"e9a69756\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"351b4fb5_864b_47da_89e6_30433d1ecc70\"]}')"}, "location": "end", "name": "da12955a-a570-4b7d-a402-090a03f38e12:d8e2644f"}, "keyword": "action", "name": "insert_to_list_batch", "number": 6, "provider": "workato_variable", "skip": false}, {"as": "58e05796", "block": [], "input": {"name": "3d84fc22-12da-448e-8313-54473d672c2e:dda3ad96:next_token", "next_token": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"e9a69756\",\"path\":[\"continuation_token\"]}').presence"}, "keyword": "action", "name": "update_variables", "number": 7, "provider": "workato_variable", "skip": false}, {"as": "", "block": [], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"e9a69756\",\"path\":[\"continuation_token\"]}')}", "operand": "present", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "while_condition", "name": "", "number": 8, "provider": "", "skip": false}], "input": {}, "keyword": "repeat", "name": "", "number": 4, "provider": "", "skip": false}, {"as": "081b7c80", "block": [], "input": {"variables": {"schema": "[{\"name\":\"next_token\",\"type\":\"string\",\"optional\":true,\"label\":\"next_token\",\"details\":{\"real_name\":\"next_token\"},\"control_type\":\"text\",\"parent\":[\"variables\",\"data\"]}]"}}, "keyword": "action", "name": "declare_variable", "number": 9, "provider": "workato_variable", "skip": false}, {"as": "4001b581", "block": [], "input": {"list_item_schema_json": "[{\"name\":\"user\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"User\"},{\"name\":\"conversation_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Conversation ID\"},{\"name\":\"is_positive_feedback\",\"type\":\"boolean\",\"optional\":false,\"control_type\":\"checkbox\",\"label\":\"Is positive feedback\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Is positive feedback\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"is_positive_feedback\",\"type\":\"boolean\",\"optional\":false}},{\"name\":\"request_category\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Request category\"},{\"name\":\"status\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Status\"},{\"name\":\"genie\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Genie\"}]", "name": "Conversation History"}, "keyword": "action", "name": "declare_list", "number": 10, "provider": "workato_variable", "skip": false}, {"as": "2ecfb784", "block": [{"as": "9d4f7dca", "block": [], "input": {"11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "1c051ec0-efbc-4a92-9d96-478d26cad7ac": "string", "427c8630-e3fd-4de8-a1ad-a6a275fd02b8": "string", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "6b7c1778-edcb-4af3-a5dd-36b48c4a9470": "boolean", "72d4f203-1690-43d0-8ef4-2a3d9242ce33": "string", "75d850a9-449e-4463-9f42-bbfaf3a1af69": "string", "a1a26026-73a1-45cc-b01b-92f2e50b02b7": "string", "a3c19569-a685-4ad4-b181-726a52c25919": "string", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "c1038835-5595-41a2-a305-276b519408f6": "string", "continuation_token": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"081b7c80\",\"path\":[\"next_token\"]}').presence", "da8772ab-1a41-4b46-b19a-539304e4d64a": "string", "e11ce1c2-5282-4841-95a9-c3864b28e6b0": "string", "filters": [{"field_id": "a3c19569-a685-4ad4-b181-726a52c25919", "op_date_time": "eq", "op_default": "eq", "value_default": "#{_dp('{\"pill_type\":\"project_property\",\"property_name\":\"GenieName\"}')}"}, {"field_id": "a5612739-5401-4ae7-bd07-782c1a6fb2d1", "op_date_time": "gte", "value_date_time": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"dda3ad96\",\"path\":[\"period_start\"]}')}"}], "limit": "200", "order_direction": "asc", "table_id": "34765"}, "keyword": "action", "name": "get_records", "number": 12, "provider": "workato_db_table", "skip": false}, {"as": "d1fe1903", "block": [], "input": {"list_items": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"9d4f7dca\",\"path\":[\"records\"]}')}", "conversation_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"9d4f7dca\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"427c8630_e3fd_4de8_a1ad_a6a275fd02b8\"]}')}", "genie": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"9d4f7dca\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"a3c19569_a685_4ad4_b181_726a52c25919\"]}')}", "is_positive_feedback": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"9d4f7dca\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"6b7c1778_edcb_4af3_a5dd_36b48c4a9470\"]}')}", "request_category": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"9d4f7dca\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"75d850a9_449e_4463_9f42_bbfaf3a1af69\"]}')}", "status": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"9d4f7dca\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"1c051ec0_efbc_4a92_9d96_478d26cad7ac\"]}')}", "user": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"9d4f7dca\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"a1a26026_73a1_45cc_b01b_92f2e50b02b7\"]}')}"}, "location": "end", "name": "b84b0f00-0794-4f87-88b9-e789b2829e56:4001b581"}, "keyword": "action", "name": "insert_to_list_batch", "number": 13, "provider": "workato_variable", "skip": false}, {"as": "caa690d5", "block": [], "input": {"name": "9a55b611-7d90-469d-9991-ab0d94fb9d87:081b7c80:next_token", "next_token": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"9d4f7dca\",\"path\":[\"continuation_token\"]}').presence"}, "keyword": "action", "name": "update_variables", "number": 14, "provider": "workato_variable", "skip": false}, {"as": "", "block": [], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"9d4f7dca\",\"path\":[\"continuation_token\"]}')}", "operand": "present", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "while_condition", "name": "", "number": 15, "provider": "", "skip": false}], "input": {}, "keyword": "repeat", "name": "", "number": 11, "provider": "", "skip": false}, {"as": "2286b831", "block": [], "input": {"variables": {"data": {"average_ticket_resolution_time": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"d8e2644f\",\"path\":[\"list_items\"]}').where(\"ticket_resolution_time !=\": null).pluck(:ticket_resolution_time).length > 0 ? _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"d8e2644f\",\"path\":[\"list_items\"]}').where(\"ticket_resolution_time !=\": null).pluck(:ticket_resolution_time).sum/_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"d8e2644f\",\"path\":[\"list_items\"]}').where(\"ticket_resolution_time !=\": null).pluck(:ticket_resolution_time).length : skip", "ticketing_processes_count": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"d8e2644f\",\"path\":[\"list_items\"]}').where(action_category: \"ticketing\").pluck(:process_id).uniq.length", "total_processes_count": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"4001b581\",\"path\":[\"list_items\"]}').pluck(:conversation_id).uniq.length"}, "schema": "[{\"control_type\":\"integer\",\"label\":\"total_processes_count\",\"parse_output\":\"integer_conversion\",\"name\":\"total_processes_count\",\"type\":\"integer\",\"optional\":true,\"details\":{\"real_name\":\"total_processes_count\"}},{\"control_type\":\"integer\",\"label\":\"ticketing_processes_count\",\"parse_output\":\"integer_conversion\",\"name\":\"ticketing_processes_count\",\"type\":\"integer\",\"optional\":true,\"details\":{\"real_name\":\"ticketing_processes_count\"}},{\"name\":\"average_ticket_resolution_time\",\"type\":\"string\",\"optional\":true,\"label\":\"average_ticket_resolution_time\",\"details\":{\"real_name\":\"average_ticket_resolution_time\"},\"control_type\":\"text\"}]"}}, "keyword": "action", "name": "declare_variable", "number": 16, "provider": "workato_variable", "skip": false}, {"as": "cc1734de", "block": [], "input": {"variables": {"data": {"non_ticketing_processes_count": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"total_processes_count\"]}') - _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"ticketing_processes_count\"]}')"}, "schema": "[{\"name\":\"non_ticketing_processes_count\",\"type\":\"integer\",\"optional\":true,\"label\":\"non_ticketing_processes_count\",\"details\":{\"real_name\":\"non_ticketing_processes_count\"},\"control_type\":\"integer\"}]"}}, "keyword": "action", "name": "declare_variable", "number": 17, "provider": "workato_variable", "skip": false}, {"as": "48f84dd7", "block": [], "input": {"variables": {"data": {"ticket_deflection_rate": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"total_processes_count\"]}') != 0 ? (_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"cc1734de\",\"path\":[\"non_ticketing_processes_count\"]}')*100/_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"total_processes_count\"]}')).to_i : skip"}, "schema": "[{\"name\":\"ticket_deflection_rate\",\"type\":\"string\",\"optional\":true,\"label\":\"ticket_deflection_rate\",\"details\":{\"real_name\":\"ticket_deflection_rate\"},\"control_type\":\"text\"}]"}}, "keyword": "action", "name": "declare_variable", "number": 18, "provider": "workato_variable", "skip": false}, {"as": "1a865f7f", "block": [], "input": {"parameters": {"41d1a848_0abd_47b4_9ff3_457bce148aa9": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"total_processes_count\"]}')}", "6a482238_5023_41fb_9b9d_687c23e2c5ca": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"cc1734de\",\"path\":[\"non_ticketing_processes_count\"]}')}", "7bf0cddb_eb7f_463f_9cff_046f3f2aa754": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"ticketing_processes_count\"]}')}", "7f9d71ad_4816_4554_87d6_8b0a1d3cada8": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"48f84dd7\",\"path\":[\"ticket_deflection_rate\"]}')}", "885e94ee_fc2a_4569_bc26_7fef1095ee90": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"4001b581\",\"path\":[\"list_items\"]}').where('is_positive_feedback !=': \"\").length)*100 /_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"4001b581\",\"path\":[\"list_items\",{\"path_element_type\":\"size\"}]}') ", "b650960e_fab7_433e_a684_9f093f8820a9": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"dda3ad96\",\"path\":[\"period_start\"]}')}", "e9925628_9ae9_4654_8279_e839fea15b2e": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"4001b581\",\"path\":[\"list_items\"]}').pluck('user').uniq.length", "f1757c5a_1087_49b9_a91e_4c851c954639": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"average_ticket_resolution_time\"]}').present? ? (_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"average_ticket_resolution_time\"]}').to_f * _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"cc1734de\",\"path\":[\"non_ticketing_processes_count\"]}').to_f) / 3600000 : skip", "ff6aefdb_b233_47a1_9896_7092bacef527": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"dda3ad96\",\"path\":[\"period_end\"]}')}"}, "table_id": "37039"}, "keyword": "action", "name": "add_record", "number": 19, "provider": "workato_db_table", "skip": false}], "input": {"days_of_month": "1", "time_unit": "months", "trigger_at": "00:00:00", "trigger_every": "1"}, "keyword": "trigger", "name": "scheduled_event", "number": 1, "provider": "clock", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)


def validate_127982810(raw: dict[str, Any]) -> dict[str, Any]:
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
    # Twin-drift guard: this clone family differs ONLY in table ids, so pin
    # every workato_db_table step to THIS recipe's ids explicitly.
    table_by_as = {"e9a69756": USAGE_TABLE_ID, "9d4f7dca": CONV_TABLE_ID, "1a865f7f": SINK_TABLE_ID}
    for node in _walk_nodes(raw):
        if node.get("provider") != "workato_db_table":
            continue
        expected_table = table_by_as.get(str(node.get("as") or ""))
        actual_table = str((node.get("input") or {}).get("table_id") or "")
        if expected_table is None or actual_table != expected_table:
            raise RuntimeError(
                f"recipe {RECIPE_ID} db step {node.get('as')!r} targets table "
                f"{actual_table!r}, expected {expected_table!r} (twin drift?)"
            )
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "usage_table_id": USAGE_TABLE_ID,
        "conv_table_id": CONV_TABLE_ID,
        "sink_table_id": SINK_TABLE_ID,
        "actions": [
            {"number": a.get("number"), "provider": a.get("provider"),
              "name": a.get("name"), "as": a.get("as")}
            for a in actions
        ],
    }


def seed_127982810(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_127982810(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly an empty object (payload-less "
            f"scheduler tick; no trigger field is dereferenced); got {trigger}"
        )
    now_value = data.get("now")
    period_start = _require_timezone_aware_now(now_value)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["project_properties", "workato_db_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly workato_db_table + "
            f"project_properties; got {sorted(seed_in.keys()) if isinstance(seed_in, dict) else seed_in}"
        )
    genie_name = _require_project_properties(seed_in["project_properties"])
    _require_db_section(seed_in["workato_db_table"], genie_name, period_start)
    expect = data.get("expect")
    _require_expect_shape(expect)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "expect": deepcopy(expect),
        "raw_validation": validation,
        "now": now_value,
        "project_properties": deepcopy(seed_in["project_properties"]),
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_127982810(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_127982810(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table state")
    if seed.get("now") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing pinned now")
    if not isinstance(seed.get("project_properties"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing project_properties")
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
    result["verifier"] = verify_127982810(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_timezone_aware_now(now_value: Any) -> datetime.datetime:
    if not isinstance(now_value, str) or not now_value.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input requires a fixed 'now' "
            "(period_start/period_end derive from 1.months.ago / 1.days.ago)"
        )
    try:
        parsed = datetime.datetime.fromisoformat(now_value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(f"recipe {RECIPE_ID} 'now' is not an ISO timestamp: {now_value!r}") from exc
    if parsed.tzinfo is None:
        raise RuntimeError(f"recipe {RECIPE_ID} 'now' must carry timezone information: {now_value!r}")
    return shift_months(parsed, -1)


def _require_project_properties(properties: Any) -> str:
    if (
        not isinstance(properties, dict)
        or sorted(properties.keys()) != ["GenieName"]
        or not isinstance(properties.get("GenieName"), str)
        or not properties["GenieName"].strip()
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.project_properties must carry exactly the non-empty "
            f"GenieName property (the Genie eq filter reads it); got {properties}"
        )
    return properties["GenieName"]


def _require_db_section(section: Any, genie_name: str, period_start: datetime.datetime) -> None:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed.workato_db_table must be an object")
    unexpected = sorted(set(section.keys()) - {"tables", "continuation_tokens"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} workato_db_table has unexpected keys: {unexpected}")
    tables = section.get("tables")
    expected_tables = sorted([USAGE_TABLE_ID, CONV_TABLE_ID, SINK_TABLE_ID])
    if not isinstance(tables, dict) or sorted(tables.keys()) != expected_tables:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed tables must be exactly {expected_tables}; "
            f"got {sorted(tables.keys()) if isinstance(tables, dict) else tables}"
        )
    if tables[SINK_TABLE_ID] != []:
        raise RuntimeError(
            f"recipe {RECIPE_ID} sink table {SINK_TABLE_ID} must be seeded EMPTY "
            "(the add_record row is the observable final state)"
        )
    for table_id in (USAGE_TABLE_ID, CONV_TABLE_ID):
        rows = tables[table_id]
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise RuntimeError(f"recipe {RECIPE_ID} table {table_id} rows must be objects")
    matching = [
        row for row in tables[CONV_TABLE_ID]
        if str(row.get(GENIE_COL) or "") == genie_name
        and _row_in_period(row.get(CREATED_AT_COL), period_start)
    ]
    if not matching:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {CONV_TABLE_ID} needs >=1 row matching Genie "
            f"{genie_name!r} with Created-at >= {period_start.isoformat()}: the "
            "feedback-participation formula divides by the Conversation History size "
            "and a zero-row seed is the documented job-error path, never a pass path"
        )
    tokens = section.get("continuation_tokens")
    if tokens is not None:
        if not isinstance(tokens, dict) or not tokens:
            raise RuntimeError(f"recipe {RECIPE_ID} continuation_tokens must be a non-empty object")
        unexpected_tokens = sorted(set(tokens.keys()) - {USAGE_TABLE_ID, CONV_TABLE_ID})
        if unexpected_tokens:
            raise RuntimeError(
                f"recipe {RECIPE_ID} continuation_tokens only page the two read tables; "
                f"got {unexpected_tokens}"
            )
        for table_id, token in tokens.items():
            if not isinstance(token, str) or not token.strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} continuation token for {table_id} must be a "
                    "non-empty string (plain first-page token form)"
                )


def _row_in_period(created_at: Any, period_start: datetime.datetime) -> bool:
    if not isinstance(created_at, str) or not created_at.strip():
        return False
    try:
        parsed = datetime.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        return False
    return parsed >= period_start


def _require_expect_shape(expect: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    count = expect.get("executed_action_count")
    if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.executed_action_count must be a positive int")
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or not items:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must be a non-empty list")
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[{idx}] must be an object")
        unknown = sorted(set(item.keys()) - _EXPECT_ITEM_KEYS)
        if unknown:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] has unrecognized keys: {unknown}"
            )
        if item.get("tool") not in ALLOWED_TOOLS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}].tool must be one of "
                f"{ALLOWED_TOOLS}; got {item.get('tool')!r}"
            )
        if not any(key in item for key in _EXPECT_VALUE_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] must carry at least one "
                "value key (corpus lint)"
            )
    if items[-1].get("tool") != "workato_db_table.add_record":
        raise RuntimeError(
            f"recipe {RECIPE_ID} the final expectation must pin the add_record sink write"
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
    return ctx.tools.call("harness.workato_db_table.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
