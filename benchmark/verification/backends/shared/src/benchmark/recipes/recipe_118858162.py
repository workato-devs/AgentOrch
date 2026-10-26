from __future__ import annotations

import datetime as _dt
import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_118858162


RECIPE_ID = "118858162"
SEED_TYPE = "sheets_slack_support_schedule_windows_variant"
TRACK = "live_sheets_slack_support_schedule_windows"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"
TRIGGER_AS = "50e6cbe9"
SEARCH_AS = "1804d2b6"
ACCUMULATE_AS = "0e9ea905"
POST_APJ_AS = "6b5dd0a2"
POST_EMEA_AS = "7a997dd6"
POST_US_AS = "5036f918"
SHEET_HEADERS = [
    "col_APJ TIME",
    "col_EMEA TIME",
    "col_US TIME",
    "col_WEEK NO",
    "col_DATE",
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
ACCUMULATED_ITEM_KEYS = (
    "time_now",
    "apj_start",
    "apj_end",
    "us_start",
    "us_end",
    "emea_start",
    "emea_end",
)
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")


_STRUCTURE_PINS_JSON = r"""[{"as": "50e6cbe9", "input": {"allow_dialog": "false", "domain": "firefighter", "hide_from_help": "false", "name": "bt_support", "scope": "schedule", "slash_command": {"enable": "true", "name": "/supportschedule"}}, "keyword": "trigger", "name": "bot_command_v2", "number": 1, "provider": "slack_bot", "skip": false}, {"as": "f4b4ac8a", "input": {"variables": {"data": {"week": "=now.in_time_zone(\"Asia/Singapore\").yweek"}, "schema": "[{\"name\":\"week\",\"type\":\"string\",\"optional\":true,\"label\":\"week_no\",\"control_type\":\"text\"}]"}}, "keyword": "action", "name": "declare_variable", "number": 2, "provider": "workato_variable", "skip": false}, {"as": "1804d2b6", "input": {"count": "200", "data": {"col_WEEK NO": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"f4b4ac8a\",\"path\":[\"week\"]}')}"}, "sheet": "<anon>2024</anon>", "spreadsheet": "<anon>2AbC3DeF4GhI5JkL6MnO7PqR8StU9VwX0YzA1BcD2EfG</anon>", "team_drives": "my_drive"}, "keyword": "action", "name": "search_spreadsheet_rows_v4_new", "number": 3, "provider": "google_sheets", "skip": false}, {"as": "0e9ea905", "input": {"list_item": {"data": {"apj_end": "=(((_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_APJ TIME\"]}').split(\"-\").last.strip.to_time).strftime(\"%H\").to_i) * 60) + (((_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_APJ TIME\"]}').split(\"-\").last.strip.to_time).strftime(\"%M\").to_i))", "apj_start": "=(((_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_APJ TIME\"]}').split(\"-\").first.strip.to_time).strftime(\"%H\").to_i) * 60) + (((\n_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_APJ TIME\"]}').split(\"-\").first.strip.to_time).strftime(\"%M\").to_i))", "emea_end": "=(((_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_EMEA TIME\"]}').split(\"-\").last.strip.to_time).strftime(\"%H\").to_i) * 60) + (((_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_EMEA TIME\"]}').split(\"-\").last.strip.to_time).strftime(\"%M\").to_i))", "emea_start": "=(((_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_EMEA TIME\"]}').split(\"-\").first.strip.to_time).strftime(\"%H\").to_i) * 60) + (((_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_EMEA TIME\"]}').split(\"-\").first.strip.to_time).strftime(\"%M\").to_i))", "time_now": "=((now.in_time_zone(\"Asia/Singapore\").strftime(\"%H\").to_i) * 60) + ((now.in_time_zone(\"Asia/Singapore\").strftime(\"%M\").to_i))", "us_end": "=(((_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_US TIME\"]}').split(\"-\").last.strip.to_time).strftime(\"%H\").to_i) * 60) + (((_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_US TIME\"]}').split(\"-\").last.strip.to_time).strftime(\"%M\").to_i))", "us_start": "=(((_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_US TIME\"]}').split(\"-\").first.strip.to_time).strftime(\"%H\").to_i) * 60) + (((_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_US TIME\"]}').split(\"-\").first.strip.to_time).strftime(\"%M\").to_i))"}, "schema": "[{\"name\":\"time_now\",\"type\":\"string\",\"optional\":true,\"label\":\"time_now\",\"control_type\":\"text\"},{\"name\":\"apj_start\",\"type\":\"string\",\"optional\":true,\"label\":\"apj_start\",\"control_type\":\"text\"},{\"name\":\"apj_end\",\"type\":\"string\",\"optional\":true,\"label\":\"apj_end\",\"control_type\":\"text\"},{\"name\":\"us_start\",\"type\":\"string\",\"optional\":true,\"label\":\"us_start\",\"control_type\":\"text\"},{\"name\":\"us_end\",\"type\":\"string\",\"optional\":true,\"label\":\"us_end\",\"control_type\":\"text\"},{\"name\":\"emea_start\",\"type\":\"string\",\"optional\":true,\"label\":\"emea_start\",\"control_type\":\"text\"},{\"name\":\"emea_end\",\"type\":\"string\",\"optional\":true,\"label\":\"emea_end\",\"control_type\":\"text\"}]"}, "name": "Visibility_Test"}, "keyword": "action", "name": "accumulate_list_items", "number": 4, "provider": "workato_list", "skip": false}, {"as": "51bc22c0", "input": {"variables": {"data": {"us_shift_period": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_D-US-Alt\"]}').present?\n  \"#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_D-US\"]}')}\\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_D-US-Alt\"]}')}\"\nelse\n  _dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_D-US\"]}')\nend", "us_support": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_BT US 2\"]}') == \"-\"\n  \"`#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_BT US 1\"]}')}`\"\nelse\n  \"`#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_BT US 1\"]}')}` & `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_BT US 2\"]}')}`\"\nend", "us_support_online": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_BT US 2\"]}') == \"-\"\n  \"_#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_BT US 1\"]}')}_\"\nelse\n  \"_#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_BT US 1\"]}')}_ & _#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"col_BT US 2\"]}')}_\"\nend"}, "schema": "[{\"control_type\":\"text\",\"label\":\"US Support\",\"name\":\"us_support\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"US Support\"},\"parent\":[\"variables\",\"data\"],\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true},{\"control_type\":\"text\",\"label\":\"US Shift Period\",\"name\":\"us_shift_period\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"US Shift Period\"},\"parent\":[\"variables\",\"data\"],\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true},{\"name\":\"us_support_online\",\"type\":\"string\",\"optional\":true,\"label\":\"US Support Online\",\"details\":{\"real_name\":\"US Support Online\"},\"control_type\":\"text\",\"parent\":[\"variables\",\"data\"]}]"}}, "keyword": "action", "name": "declare_variable", "number": 5, "provider": "workato_variable", "skip": false}, {"as": null, "input": {"conditions": [{"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"time_now\"]}').to_i >= _dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"apj_start\"]}').to_i", "operand": "is_true", "rhs": ""}, {"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"time_now\"]}').to_i <= _dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"apj_end\"]}').to_i\n", "operand": "is_true", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "if", "name": null, "number": 6, "provider": null, "skip": false}, {"as": "6b5dd0a2", "input": {"blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": ":online: _#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT APJ\"]}')}_ is `Online` to help you now!\n\n:firefighter_workato: Good day,\nHere's the *BT Operations* On-Duty for Week #{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_WEEK NO\"]}')} (#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_DATE\"]}')}):\n\n*APJ* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT APJ\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-APJ\"]}')}\n\n*EMEA* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT EMEA\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-EMEA\"]}')}\n\n*US* - #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"51bc22c0\",\"path\":[\"us_support\"]}')} :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"51bc22c0\",\"path\":[\"us_shift_period\"]}')}\n\n*Escalation* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT FLEXI\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-Flexi\"]}')}"}], "ephemeral_message": "true"}, "keyword": "action", "name": "post_bot_reply_v2", "number": 7, "provider": "slack_bot", "skip": false}, {"as": null, "input": {"conditions": [{"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"time_now\"]}').to_i >= _dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"emea_start\"]}').to_i", "operand": "is_true", "rhs": ""}, {"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"time_now\"]}').to_i < _dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"emea_end\"]}').to_i", "operand": "is_true", "rhs": ""}], "operand": "or", "type": "compound"}, "keyword": "if", "name": null, "number": 8, "provider": null, "skip": false}, {"as": "7a997dd6", "input": {"blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": ":online: _#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT EMEA\"]}')}_ is `Online` to help you now!\n\n:firefighter_workato: Good day,\nHere's the *BT Operations* On-Duty for Week #{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_WEEK NO\"]}')} (#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_DATE\"]}')}):\n\n*APJ* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT APJ\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-APJ\"]}')}\n\n*EMEA* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT EMEA\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-EMEA\"]}')}\n\n*US* - #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"51bc22c0\",\"path\":[\"us_support\"]}')} :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"51bc22c0\",\"path\":[\"us_shift_period\"]}')}\n\n*Escalation* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT FLEXI\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-Flexi\"]}')}"}], "ephemeral_message": "true"}, "keyword": "action", "name": "post_bot_reply_v2", "number": 9, "provider": "slack_bot", "skip": false}, {"as": null, "input": {"conditions": [{"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"time_now\"]}').to_i >= _dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"us_start\"]}').to_i", "operand": "is_true", "rhs": ""}, {"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"time_now\"]}').to_i <= _dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"0e9ea905\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"us_end\"]}').to_i", "operand": "is_true", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "if", "name": null, "number": 10, "provider": null, "skip": false}, {"as": "5036f918", "input": {"blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": ":online: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"51bc22c0\",\"path\":[\"us_support_online\"]}')} is `Online` to help you now!\n\n:firefighter_workato: Good day,\nHere's the *BT Operations* On-Duty for Week #{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_WEEK NO\"]}')} (#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_DATE\"]}')}):\n\n*APJ* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT APJ\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-APJ\"]}')}\n\n*EMEA* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT EMEA\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-EMEA\"]}')}\n\n*US* - #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"51bc22c0\",\"path\":[\"us_support\"]}')} :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"51bc22c0\",\"path\":[\"us_shift_period\"]}')}\n\n*Escalation* - `#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_BT FLEXI\"]}')}` :firefighter_6:\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"1804d2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_D-Flexi\"]}')}"}], "ephemeral_message": "true"}, "keyword": "action", "name": "post_bot_reply_v2", "number": 11, "provider": "slack_bot", "skip": false}]"""

STRUCTURE_PINS: list[dict] = json.loads(_STRUCTURE_PINS_JSON)

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
EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "week",
    "accumulated_item",
    "slack_posts",
)


def _structure(node: dict[str, Any]) -> list[dict[str, Any]]:
    pin: dict[str, Any] = {
        "keyword": node.get("keyword"),
        "number": node.get("number"),
        "as": node.get("as"),
        "provider": node.get("provider"),
        "name": node.get("name"),
        "skip": bool(node.get("skip")),
        "input": node.get("input") or {},
    }
    if node.get("keyword") == "foreach":
        pin["repeat_mode"] = node.get("repeat_mode")
        pin["source"] = node.get("source")
    if isinstance(node.get("filter"), dict):
        pin["filter"] = node["filter"]
    out = [pin]
    for child in node.get("block") or []:
        if isinstance(child, dict):
            out.extend(_structure(child))
    return out


def validate_118858162(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger 'as' changed: {raw.get('as')!r}")
    actual = _structure(raw)
    if len(actual) != len(STRUCTURE_PINS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} node count changed: {len(actual)} != {len(STRUCTURE_PINS)}"
        )
    for idx, (got, expected) in enumerate(zip(actual, STRUCTURE_PINS)):
        if got != expected:
            raise RuntimeError(
                f"recipe {RECIPE_ID} node {idx} (step {expected.get('number')}) changed:\n"
                f"expected: {json.dumps(expected, sort_keys=True)}\n"
                f"actual:   {json.dumps(got, sort_keys=True)}"
            )
    actions = [pin for pin in actual if pin["keyword"] == "action"]
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": [
            {
                "number": pin["number"],
                "provider": pin["provider"],
                "name": pin["name"],
                "as": pin["as"],
            }
            for pin in actions
        ],
    }


def seed_118858162(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118858162(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    now = data.get("now")
    if not isinstance(now, str) or not now.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input requires a fixed 'now' (yweek + the SGT "
            "minutes-of-day comparisons are wall-clock formulas)"
        )
    try:
        _dt.datetime.fromisoformat(now.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(f"recipe {RECIPE_ID} 'now' must be an ISO timestamp: {now!r}") from exc
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"sheets"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    expect = data.get("expect")
    _require_expect_shape(expect)
    _require_sheets_section(seed_in.get("sheets"), expect)
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole "
            "run instead of exercising a recipe branch"
        )
    seed_response = ctx.tools.call(
        "harness.google_sheets.seed_rows", {"sheets": deepcopy(seed_in["sheets"])}
    )
    if not seed_response.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Google Sheets seed failed: {seed_response}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "now": now,
        "trigger": trigger,
        "expect": deepcopy(expect),
        "sheets": deepcopy(seed_in["sheets"]),
        "sheets_seed_response": deepcopy(seed_response),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_118858162(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118858162(raw)
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    if seed.get("now") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing the fixed 'now'")
    if not isinstance(seed.get("sheets"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing the sheets section")
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    initial_snapshot = ctx.tools.call("harness.google_sheets.snapshot", {})
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = ctx.tools.call("harness.google_sheets.snapshot", {})
    # No cleanup: the sheet seed fully overwrites the redirected tab on every
    # seed (replace_rows) and the Slack replies are terminal observables that
    # are never re-read (cleanup principle).
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "expect": expect,
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "expected_channel": ctx.env.slack_channel_override,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
            "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_118858162(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {"channel"} or not isinstance(trigger.get("channel"), str):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'channel': <str>}} -- the "
            "recipe dereferences nothing else from the trigger and the harness routes "
            "replies to SLACK_CHANNEL_OVERRIDE (118864889 precedent)"
        )


def _require_sheets_section(section: Any, expect: dict[str, Any]) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["headers", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets must be exactly {{'headers': ..., 'rows': ...}}"
        )
    if section["headers"] != SHEET_HEADERS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets.headers must be the LITERAL col_-prefixed "
            f"17-column schedule schema {SHEET_HEADERS} (datapills walk these exact keys)"
        )
    rows = section["rows"]
    if not isinstance(rows, list) or len(rows) < 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets.rows needs the matching-week row plus at "
            "least one different-week decoy row"
        )
    week = str(expect.get("week"))
    matching = 0
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} sheet row {idx} must be an object")
        unknown = sorted(set(row) - set(SHEET_HEADERS))
        if unknown:
            raise RuntimeError(f"recipe {RECIPE_ID} sheet row {idx} has unknown columns: {unknown}")
        for key in SHEET_HEADERS:
            if key not in row or not isinstance(row[key], str):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} sheet row {idx} must carry every column as a "
                    f"string (missing/non-string {key!r})"
                )
        if row["col_WEEK NO"] == week:
            matching += 1
    if matching != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} exactly ONE seeded row may match WEEK NO {week!r} (the "
            "sheet-row pills read OUTSIDE any foreach with first-row semantics; "
            f"got {matching} matches)"
        )


def _require_expect_shape(expect: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(set(expect) - set(EXPECT_KEYS))
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has unexpected keys: {unknown}")
    if not isinstance(expect.get("week"), str) or not expect["week"].strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.week must pin the rendered ISO week string "
            "(yweek of the pinned now in Asia/Singapore)"
        )
    item = expect.get("accumulated_item")
    if not isinstance(item, dict) or tuple(sorted(item)) != tuple(sorted(ACCUMULATED_ITEM_KEYS)):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.accumulated_item must pin exactly "
            f"{sorted(ACCUMULATED_ITEM_KEYS)} (the engine-canonical renderings: "
            "time_now is an int, the window bounds are minute STRINGS)"
        )
    if not isinstance(item.get("time_now"), int):
        raise RuntimeError(
            f"recipe {RECIPE_ID} accumulated_item.time_now must be the SGT minutes-of-day int"
        )
    for key in ACCUMULATED_ITEM_KEYS:
        if key == "time_now":
            continue
        if not isinstance(item.get(key), str) or not item[key].isdigit():
            raise RuntimeError(
                f"recipe {RECIPE_ID} accumulated_item.{key} must be the engine-canonical "
                f"minute STRING (e.g. '540'): {item.get(key)!r}"
            )
    posts = expect.get("slack_posts")
    if not isinstance(posts, list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.slack_posts must be a list ([] is the "
            "all-windows-closed silent branch: the accumulated_item pin plus the "
            "search result_count still prove the data flowed and every IF was false)"
        )
    for post in posts:
        if (
            not isinstance(post, dict)
            or set(post) != {"step_as", "text"}
            or post.get("step_as") not in {POST_APJ_AS, POST_EMEA_AS, POST_US_AS}
            or not isinstance(post.get("text"), str)
            or not post["text"].strip()
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} every slack_posts entry must pin "
                f"{{step_as in [{POST_APJ_AS}, {POST_EMEA_AS}, {POST_US_AS}], text}}: {post}"
            )
    if expect.get("executed_action_count") != 4 + len(posts):
        raise RuntimeError(
            f"recipe {RECIPE_ID} executed_action_count must be 4 + posts "
            f"(declare+search+accumulate+declare then one reply per open window)"
        )
    tools = expect.get("tools")
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tools, list) or not isinstance(tool_expectations, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools/tool_expectations must be lists")
    if len(tools) != len(tool_expectations):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry"
        )
    expected_tools = ["google_sheets.search_spreadsheet_rows_v4_new"] + ["slack.post_reply"] * len(posts)
    if tools != expected_tools:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools must be {expected_tools} (search then one "
            f"reply per pinned post): {tools}"
        )


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
