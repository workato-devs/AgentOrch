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
from ..verifier import verify_118554940


RECIPE_ID = "118554940"
SEED_TYPE = "bt_support_schedule_on_demand_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"
TRIGGER_AS = "50e6cbe9"


_RAW_PIN_JSON = r"""{"as": "50e6cbe9", "block": [{"as": "f4b4ac8a", "block": [], "input": {"variables": {"data": {"week": "=now.in_time_zone(\"Asia/Singapore\").yweek"}, "schema": "[{\"name\":\"week\",\"type\":\"string\",\"optional\":true,\"label\":\"week_no\",\"control_type\":\"text\"}]"}}, "keyword": "action", "name": "declare_variable", "number": 2, "provider": "workato_variable", "skip": false}, {"as": "1804d2b6", "block": [], "input": {"count": "200", "data": {"col_WEEK NO": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"f4b4ac8a\",\"path\":[\"week\"]}')}"}, "sheet": "<anon>2024</anon>", "spreadsheet": "<anon>2AbC3DeF4GhI5JkL6MnO7PqR8StU9VwX0YzA1BcD2EfG</anon>", "team_drives": "my_drive"}, "keyword": "action", "name": "search_spreadsheet_rows_v4_new", "number": 3, "provider": "google_sheets", "skip": false}, {"as": "0e9ea905", "block": [], "input": {"list_item": {"data": {"apj_end": "=(((_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_APJ TIME\"]}').split(\"-\").last.strip.to_time).strftime(\"%H\").to_i) * 60) + (((_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_APJ TIME\"]}').split(\"-\").last.strip.to_time).strftime(\"%M\").to_i))", "apj_start": "=(((_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_APJ TIME\"]}').split(\"-\").first.strip.to_time).strftime(\"%H\").to_i) * 60) + (((\n_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_APJ TIME\"]}').split(\"-\").first.strip.to_time).strftime(\"%M\").to_i))", "emea_end": "=(((_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_EMEA TIME\"]}').split(\"-\").last.strip.to_time).strftime(\"%H\").to_i) * 60) + (((_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_EMEA TIME\"]}').split(\"-\").last.strip.to_time).strftime(\"%M\").to_i))", "emea_start": "=(((_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_EMEA TIME\"]}').split(\"-\").first.strip.to_time).strftime(\"%H\").to_i) * 60) + (((_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_EMEA TIME\"]}').split(\"-\").first.strip.to_time).strftime(\"%M\").to_i))", "time_now": "=((now.in_time_zone(\"Asia/Singapore\").strftime(\"%H\").to_i) * 60) + ((now.in_time_zone(\"Asia/Singapore\").strftime(\"%M\").to_i))", "us_end": "=(((_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_US TIME\"]}').split(\"-\").last.strip.to_time).strftime(\"%H\").to_i) * 60) + (((_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_US TIME\"]}').split(\"-\").last.strip.to_time).strftime(\"%M\").to_i))", "us_start": "=(((_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_US TIME\"]}').split(\"-\").first.strip.to_time).strftime(\"%H\").to_i) * 60) + (((_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_US TIME\"]}').split(\"-\").first.strip.to_time).strftime(\"%M\").to_i))"}, "schema": "[{\"name\":\"time_now\",\"type\":\"string\",\"optional\":true,\"label\":\"time_now\",\"control_type\":\"text\"},{\"name\":\"apj_start\",\"type\":\"string\",\"optional\":true,\"label\":\"apj_start\",\"control_type\":\"text\"},{\"name\":\"apj_end\",\"type\":\"string\",\"optional\":true,\"label\":\"apj_end\",\"control_type\":\"text\"},{\"name\":\"us_start\",\"type\":\"string\",\"optional\":true,\"label\":\"us_start\",\"control_type\":\"text\"},{\"name\":\"us_end\",\"type\":\"string\",\"optional\":true,\"label\":\"us_end\",\"control_type\":\"text\"},{\"name\":\"emea_start\",\"type\":\"string\",\"optional\":true,\"label\":\"emea_start\",\"control_type\":\"text\"},{\"name\":\"emea_end\",\"type\":\"string\",\"optional\":true,\"label\":\"emea_end\",\"control_type\":\"text\"}]"}, "name": "Visibility_Test"}, "keyword": "action", "name": "accumulate_list_items", "number": 4, "provider": "workato_list", "skip": false}, {"as": "51bc22c0", "block": [], "input": {"variables": {"data": {"us_shift_period": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_D-US-Alt\"]}').present?\n  \"#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_D-US\"]}')}\\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_D-US-Alt\"]}')}\"\nelse\n  _dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_D-US\"]}')\nend", "us_support": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_BT US 2\"]}') == \"-\"\n  \"`#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_BT US 1\"]}')}`\"\nelse\n  \"`#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_BT US 1\"]}')}` & `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_BT US 2\"]}')}`\"\nend", "us_support_online": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_BT US 2\"]}') == \"-\"\n  \"_#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_BT US 1\"]}')}_\"\nelse\n  \"_#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_BT US 1\"]}')}_ & _#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_BT US 2\"]}')}_\"\nend"}, "schema": "[{\"control_type\":\"text\",\"label\":\"US Support\",\"name\":\"us_support\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"US Support\"},\"parent\":[\"variables\",\"data\"],\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true},{\"control_type\":\"text\",\"label\":\"US Shift Period\",\"name\":\"us_shift_period\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"US Shift Period\"},\"parent\":[\"variables\",\"data\"],\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true},{\"name\":\"us_support_online\",\"type\":\"string\",\"optional\":true,\"label\":\"US Support Online\",\"details\":{\"real_name\":\"US Support Online\"},\"control_type\":\"text\",\"parent\":[\"variables\",\"data\"]}]"}}, "keyword": "action", "name": "declare_variable", "number": 5, "provider": "workato_variable", "skip": false}, {"as": "", "block": [{"as": "6b5dd0a2", "block": [], "input": {"blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": ":online: _#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT APJ\"]}')}_ is `Online` to help you now!\n\n:firefighter_workato: Good day,\nHere's the *BT Operations* On-Duty for Week #{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_WEEK NO\"]}')} (#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_DATE\"]}')}):\n\n*APJ* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT APJ\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-APJ\"]}')}\n\n*EMEA* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT EMEA\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-EMEA\"]}')}\n\n*US* - #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"51bc22c0\",\"path\":[\"us_support\"]}')} :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"51bc22c0\",\"path\":[\"us_shift_period\"]}')}\n\n*Escalation* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT FLEXI\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-Flexi\"]}')}"}], "ephemeral_message": "true"}, "keyword": "action", "name": "post_bot_reply_v2", "number": 7, "provider": "slack_bot", "skip": false}], "input": {"conditions": [{"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"time_now\"]}').to_i >= _dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"apj_start\"]}').to_i", "operand": "is_true", "rhs": ""}, {"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"time_now\"]}').to_i <= _dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"apj_end\"]}').to_i\n", "operand": "is_true", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 6, "provider": "", "skip": false}, {"as": "", "block": [{"as": "7a997dd6", "block": [], "input": {"blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": ":online: _#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT EMEA\"]}')}_ is `Online` to help you now!\n\n:firefighter_workato: Good day,\nHere's the *BT Operations* On-Duty for Week #{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_WEEK NO\"]}')} (#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_DATE\"]}')}):\n\n*APJ* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT APJ\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-APJ\"]}')}\n\n*EMEA* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT EMEA\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-EMEA\"]}')}\n\n*US* - #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"51bc22c0\",\"path\":[\"us_support\"]}')} :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"51bc22c0\",\"path\":[\"us_shift_period\"]}')}\n\n*Escalation* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT FLEXI\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-Flexi\"]}')}"}], "ephemeral_message": "true"}, "keyword": "action", "name": "post_bot_reply_v2", "number": 9, "provider": "slack_bot", "skip": false}], "input": {"conditions": [{"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"time_now\"]}').to_i >= _dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"emea_start\"]}').to_i", "operand": "is_true", "rhs": ""}, {"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"time_now\"]}').to_i < _dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"emea_end\"]}').to_i", "operand": "is_true", "rhs": ""}], "operand": "or", "type": "compound"}, "keyword": "if", "name": "", "number": 8, "provider": "", "skip": false}, {"as": "", "block": [{"as": "5036f918", "block": [], "input": {"blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": ":online: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"51bc22c0\",\"path\":[\"us_support_online\"]}')} is `Online` to help you now!\n\n:firefighter_workato: Good day,\nHere's the *BT Operations* On-Duty for Week #{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_WEEK NO\"]}')} (#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_DATE\"]}')}):\n\n*APJ* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT APJ\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-APJ\"]}')}\n\n*EMEA* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT EMEA\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-EMEA\"]}')}\n\n*US* - #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"51bc22c0\",\"path\":[\"us_support\"]}')} :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"51bc22c0\",\"path\":[\"us_shift_period\"]}')}\n\n*Escalation* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT FLEXI\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-Flexi\"]}')}"}], "ephemeral_message": "true"}, "keyword": "action", "name": "post_bot_reply_v2", "number": 11, "provider": "slack_bot", "skip": false}], "input": {"conditions": [{"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"time_now\"]}').to_i >= _dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"us_start\"]}').to_i", "operand": "is_true", "rhs": ""}, {"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"time_now\"]}').to_i <= _dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"us_end\"]}').to_i", "operand": "is_true", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 10, "provider": "", "skip": false}], "input": {"allow_dialog": "false", "domain": "firefighter", "hide_from_help": "false", "name": "bt_support", "scope": "schedule", "slash_command": {"enable": "true", "name": "/supportschedule"}}, "keyword": "trigger", "name": "bot_command_v2", "number": 1, "provider": "slack_bot", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

SHEET_HEADERS: list[str] = [
    "col_WEEK NO",
    "col_DATE",
    "col_APJ TIME",
    "col_EMEA TIME",
    "col_US TIME",
    "col_START TIME",
    "col_END TIME",
    "col_BT APJ",
    "col_BT EMEA",
    "col_BT US 1",
    "col_BT US 2",
    "col_BT FLEXI",
    "col_D-APJ",
    "col_D-EMEA",
    "col_D-US",
    "col_D-US-Alt",
    "col_D-Flexi",
]
TIME_RANGE_HEADERS = ("col_APJ TIME", "col_EMEA TIME", "col_US TIME")
_TIME_RANGE_RE = re.compile(r"^([01]?\d|2[0-3]):[0-5]\d\s*-\s*([01]?\d|2[0-3]):[0-5]\d$")
_TS_RE = re.compile(r"^\d+\.\d+$")

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("f4b4ac8a", "workato_variable", "declare_variable"),
    ("1804d2b6", "google_sheets", "search_spreadsheet_rows_v4_new"),
    ("0e9ea905", "workato_list", "accumulate_list_items"),
    ("51bc22c0", "workato_variable", "declare_variable"),
    ("6b5dd0a2", "slack_bot", "post_bot_reply_v2"),
    ("7a997dd6", "slack_bot", "post_bot_reply_v2"),
    ("5036f918", "slack_bot", "post_bot_reply_v2"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "google_sheets.search_spreadsheet_rows_v4_new",
    "workato_runtime.accumulate_list_items",
    "slack.post_reply",
]
ALLOWED_TOOLS: list[str] = [
    "google_sheets.search_spreadsheet_rows_v4_new",
    "slack.post_reply",
]
EXPECTED_TRIGGER_KEYS = {
    "allow_dialog": "false",
    "domain": "firefighter",
    "hide_from_help": "false",
    "name": "bt_support",
    "scope": "schedule",
}
EXPECTED_SLASH_COMMAND = {"enable": "true", "name": "/supportschedule"}


def validate_118554940(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    trigger_config = raw.get("input") or {}
    for key, value in EXPECTED_TRIGGER_KEYS.items():
        if str(trigger_config.get(key) or "") != value:
            raise RuntimeError(f"recipe {RECIPE_ID} trigger {key} changed: {trigger_config}")
    if trigger_config.get("slash_command") != EXPECTED_SLASH_COMMAND:
        raise RuntimeError(f"recipe {RECIPE_ID} slash command changed: {trigger_config}")
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


def seed_118554940(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118554940(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    now = data.get("now")
    if not isinstance(now, str) or not now.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} variant input must pin now (time-driven recipe)")
    parsed = datetime.datetime.fromisoformat(now)
    if parsed.tzinfo is None:
        raise RuntimeError(f"recipe {RECIPE_ID} now must carry an explicit UTC offset: {now!r}")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["google_sheets"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the google_sheets section; "
            f"got {sorted(seed_in.keys())}"
        )
    sheets_section = _require_sheets_section(seed_in["google_sheets"])
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    provision = ctx.tools.call("harness.google_sheets.seed_rows", {"sheets": sheets_section})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Google Sheets seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "now": now,
        "expect": deepcopy(expect),
        "google_sheets": deepcopy(sheets_section),
        "sheets_seed_response": deepcopy(provision),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_118554940(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118554940(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("google_sheets"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing google_sheets section")
    if not str(seed.get("now") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing pinned now")
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
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
    result["verifier"] = verify_118554940(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != ["channel", "message_ts"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly channel + message_ts "
            f"(the bot replies thread on them); got {sorted(trigger.keys())}"
        )
    channel = trigger.get("channel")
    if not isinstance(channel, str) or not channel.startswith("C"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.channel must be a C... channel id; got {channel!r}"
        )
    ts = trigger.get("message_ts")
    if not isinstance(ts, str) or not _TS_RE.fullmatch(ts):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.message_ts must look like a Slack ts; got {ts!r}"
        )


def _require_sheets_section(section: Any) -> dict[str, Any]:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed.google_sheets must be an object")
    unknown = sorted(set(section.keys()) - {"rows", "headers"})
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.google_sheets has unknown keys: {unknown}")
    if section.get("headers") != SHEET_HEADERS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.google_sheets.headers must be exactly the 17 literal "
            "col_-prefixed schedule headers in canonical order"
        )
    rows = section.get("rows")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.google_sheets.rows must be a non-empty list")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} sheet row {idx} must be an object")
        if sorted(row.keys()) != sorted(SHEET_HEADERS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} sheet row {idx} must carry exactly the 17 col_ headers; "
                f"got {sorted(row.keys())}"
            )
        for key, value in row.items():
            if not isinstance(value, str):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} sheet row {idx} {key!r} must be a string "
                    "(rendered-form pinning)"
                )
        for key in TIME_RANGE_HEADERS:
            if not _TIME_RANGE_RE.fullmatch(row[key]):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} sheet row {idx} {key!r} must be 'HH:MM - HH:MM' with "
                    f"00-23 hours (the engine's .to_time rejects '24:00'); got {row[key]!r}"
                )
        if not row["col_WEEK NO"].isdigit():
            raise RuntimeError(
                f"recipe {RECIPE_ID} sheet row {idx} col_'WEEK NO' must be a digit string"
            )
    return {"rows": deepcopy(rows), "headers": list(SHEET_HEADERS)}


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
    snapshot = ctx.tools.call("harness.google_sheets.snapshot", {})
    return {"google_sheets": snapshot}


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
