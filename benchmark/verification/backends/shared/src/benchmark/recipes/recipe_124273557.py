from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_124273557


RECIPE_ID = "124273557"
SEED_TYPE = "recipe_function_demo_request_slack_channel_router_variant"
TRACK = "live_salesforce_recipe_function_demo_request_router"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "baa609ea"
DB_TABLE_ID = "15930"
CHANNEL_LOOKUP_TABLE_ID = "4003733"
CONFIG_LOOKUP_TABLE_ID = "3821345"


DB_FIELD_REQUEST_NO = "de93e19e_b27d_4c9f_b4b3_669de8f5edb2"
DB_FIELD_SFDC_ID = "6ca0921b_9ea9_4c0d_9656_0b0764c8ffa6"
DB_FIELD_EMAIL = "539fb3da_1c0a_4a76_9a21_a2e284cf90e0"
DB_FIELD_TZ = "cc7288a2_7248_4719_b2a4_97356d388269"
DB_FIELD_PAGE = "f0613599_b3fc_4ee2_8834_4470f9a4e8a8"
DB_FIELD_SOURCE = "6d114605_5746_49d3_9a17_b2603d5e241e"
DB_SEED_FIELD_IDS = [
    DB_FIELD_REQUEST_NO,
    DB_FIELD_SFDC_ID,
    DB_FIELD_EMAIL,
    DB_FIELD_TZ,
    DB_FIELD_PAGE,
    DB_FIELD_SOURCE,
]

CHANNEL_NAMES = [
    "#demorequest-strategic",
    "#demo_request_report",
    "#demo_request_rpt_smb",
    "#anz_demo_request_all",
    "#japan_demo_request_all",
    "#asia_demo_request_all",
    "#asia_demo_request_smb",
    "#demo_request_rpt_emea",
    "#demo_request_report_israel",
    "#request_trial_leads",
]

SF_SCHEMA_PIN: list[dict[str, str]] = [
    {"sobject": "Account", "field": "Cat_Company_Size__c", "sf_type": "Text"},
    {"sobject": "Lead", "field": "Cat_Company_Size__c", "sf_type": "Text"},
    {"sobject": "Lead", "field": "Verified_Phone__c", "sf_type": "Phone"},
    {"sobject": "Lead", "field": "Company_Phone__c", "sf_type": "Phone"},
    {"sobject": "Contact", "field": "Verified_Phone__c", "sf_type": "Phone"},
]

CONTACT_REF_TOKEN = "$CONTACT_ID"
ACCOUNT_REF_TOKEN = "$ACCOUNT_ID"
LEAD_REF_TOKEN = "$LEAD_ID"
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_SF_ID_RE = re.compile(r"^[a-zA-Z0-9]{15,18}$")

DEAD_NODE_NUMBERS = list(range(28, 42))

EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_variable", "declare_variable"),  # 2 bca111ab
    ("workato_variable", "declare_list"),  # 3 435d85e7
    ("lookup_table", "get_entries"),  # 4 a9ca0afe
    ("workato_db_table", "get_records"),  # 5 c786cec4
    ("salesforce", "search_sobjects"),  # 7 7518c989 (Contact)
    ("salesforce", "search_sobjects"),  # 9 991904b6 (Lead)
    ("workato_variable", "update_variables"),  # 11 e8296571
    ("workato_variable", "insert_to_list"),  # 14 ade57d56 strategic
    ("workato_variable", "insert_to_list"),  # 16 ffff2e0e report
    ("workato_variable", "insert_to_list"),  # 18 5b8fa90d smb
    ("logger", "log_message"),  # 19 1cd98d30 (EMEA CSV, real data)
    ("logger", "log_message"),  # 21 1843e57b (unused)
    ("workato_variable", "insert_to_list"),  # 23 be5dc2a4 anz
    ("workato_variable", "insert_to_list"),  # 25 84df4b64 japan
    ("workato_variable", "insert_to_list"),  # 27 29c43a97 asia
    ("workato_variable", "insert_to_list"),  # 44 7f60a4d9 emea (mismatched id)
    ("workato_variable", "insert_to_list"),  # 46 e73cfaf6 israel
    ("workato_variable", "insert_to_list"),  # 48 dbb21dbb trial
    ("workato_recipe_function", "return_result"),  # 49 bf501b1d
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "workato_runtime.declare_list",
    "lookup_table.get_entries",
    "workato_db_table.get_records",
    "salesforce.search_records",
    "workato_runtime.update_variables",
    "workato_runtime.insert_to_list",
    "workato_runtime.log_message",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.get_entries",
    "workato_db_table.get_records",
    "salesforce.search_records",
    "lookup_table.get_entry",
    "workato_recipe_function.return_result",
]
EXPECT_REQUIRED_KEYS = (
    "case",
    "tools",
    "executed_action_count",
    "tool_expectations",
    "return_result",
    "boomi_takedown",
    "slack_channels",
)

_RAW_PIN_JSON = r"""{"as": "baa609ea", "block": [{"as": "bca111ab", "block": [], "input": {"variables": {"data": {"Boomi_takedown": "false"}, "schema": "[{\"control_type\":\"checkbox\",\"label\":\"Boomi_takedown\",\"render_input\":{},\"parse_output\":{},\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Boomi_takedown\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"Boomi_takedown\",\"type\":\"boolean\",\"optional\":true,\"parent\":[\"variables\",\"data\"]},\"name\":\"Boomi_takedown\",\"type\":\"boolean\",\"optional\":true,\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"text\",\"label\":\"slack_channel\",\"name\":\"slack_channel\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"slack_channel\"},\"parent\":[\"variables\",\"data\"],\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true},{\"control_type\":\"text\",\"label\":\"apj_sub_channels\",\"name\":\"apj_sub_channels\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"apj_sub_channels\"},\"parent\":[\"variables\",\"data\"],\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true},{\"name\":\"apj_emea_channels\",\"type\":\"string\",\"optional\":true,\"label\":\"apj_emea_channels\",\"details\":{\"real_name\":\"apj_emea_channels\"},\"control_type\":\"text\",\"parent\":[\"variables\",\"data\"]}]"}}, "keyword": "action", "name": "declare_variable", "number": 2, "provider": "workato_variable", "skip": false}, {"as": "435d85e7", "block": [], "input": {"list_item_schema_json": "[{\"name\":\"channel_id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Channel ID\"},{\"name\":\"channel_name\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Channel name\"}]", "name": "Slack_channels"}, "keyword": "action", "name": "declare_list", "number": 3, "provider": "workato_variable", "skip": false}, {"as": "a9ca0afe", "block": [], "input": {"lookup_table_id": "3821345"}, "keyword": "action", "name": "get_entries", "number": 4, "provider": "lookup_table", "skip": false}, {"as": "c786cec4", "block": [], "input": {"0108ecdf-2bfe-461b-be2a-820ead325e55": "string", "016ed1c6-3f52-4d5c-ab25-b59842a6fd4f": "string", "01c64377-d549-41db-9008-8d6947b0fbcf": "boolean", "09093c2b-5359-466d-9984-0f73f7cd2f8c": "string", "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "1438cbe8-dd28-406c-92d2-baa594404938": "string", "2864938c-9653-4cb6-91f6-b9d2db7286d2": "string", "2bc8bc9c-2ef8-45ac-b2ae-84feea12ea23": "string", "355999bc-d3b0-409a-b777-82e6bfe01c82": "string", "3b367595-a4e6-47ff-ba6d-871542d2c02e": "string", "3c0188b0-e51b-468f-b36c-d101b44b392c": "string", "539fb3da-1c0a-4a76-9a21-a2e284cf90e0": "string", "5d2b5774-b63e-448a-9b45-4cd88bad0357": "string", "5fb0247e-f342-4576-87bc-9cfdf5ff12b0": "string", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "680d58fb-536a-4f67-aa18-0f97a6127a40": "string", "6ca0921b-9ea9-4c0d-9656-0b0764c8ffa6": "string", "6d114605-5746-49d3-9a17-b2603d5e241e": "string", "6eb2dbc9-d2d1-47c1-8839-58cb877ca989": "string", "7022d43c-2630-4cdd-81e4-9e2e16139ce2": "string", "736d369c-b310-4153-b2be-715d2a9a7b1a": "string", "7421b7d8-f81e-4538-ae3e-85db050129a0": "string", "758a6686-7362-4f1a-b8d4-48c585935e94": "string", "7deb6030-748c-4bfa-ae62-7a835bd7c128": "string", "88c3923a-6604-4235-b308-16f8f06e6243": "string", "a1644d79-b3f1-4dcf-b390-c143737df1ab": "string", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "bb683397-77eb-4708-932e-101647b46c7e": "string", "bdeb6bb4-b60b-4da6-bbac-48d0ee986af0": "string", "c7ff7c43-79b5-4db7-9b3b-fcdf2ed3e579": "string", "cbfc4750-940b-484e-983b-8caec32a6add": "string", "cc7288a2-7248-4719-b2a4-97356d388269": "string", "d147a4fc-8434-4f17-83d7-91ca4f409c9e": "date_time", "d1e75dc4-24ec-4450-845e-a2c27e0da8c4": "string", "d7d5dcfb-500a-4b19-9062-ac5730cd115d": "string", "d9c03d92-b074-4a37-bb01-d6776f9e8531": "string", "dc145385-3732-4d8c-a167-885a1816ae45": "string", "dcaebbb9-9f64-482b-9634-0795fdd45dad": "string", "dcc5185f-2da8-41fa-a057-248480311faf": "string", "de93e19e-b27d-4c9f-b4b3-669de8f5edb2": "integer", "dfe15926-198b-4811-a4c2-e55fd5fd4cfd": "string", "e43710c9-3bf9-4fbf-ada9-bab2ae1f9947": "string", "e986c745-2ec4-4a7f-ac67-7de076fe55e7": "boolean", "ecb7f64c-9e99-49ca-9443-f52a69a5cfef": "boolean", "f0613599-b3fc-4ee2-8834-4470f9a4e8a8": "string", "f0dbce22-8093-4f74-ac70-5d470f7f7414": "string", "f26da13d-697f-4edb-ad22-125f5a14aaf4": "string", "fb69143f-a7a3-4b65-8715-ecf1201ee04e": "string", "filters": [{"field_id": "de93e19e-b27d-4c9f-b4b3-669de8f5edb2", "op_integer": "eq", "value_integer": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"baa609ea\",\"path\":[\"parameters\", \"request_no\"]}')}"}], "limit": "100", "order_direction": "asc", "table_id": "15930"}, "keyword": "action", "name": "get_records", "number": 5, "provider": "workato_db_table", "skip": false}, {"as": "", "block": [{"as": "7518c989", "block": [], "input": {"Id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"6ca0921b_9ea9_4c0d_9656_0b0764c8ffa6\"]}')}", "field_list": "Id\nAccount$Account ID.Cat_Company_Size__c\nAccount$Account ID.NumberOfEmployees\nAccount$Account ID.AnnualRevenue\npse__Revenue__c\nPhone\nValid_Phone__c\nVerified_Phone__c\nMobilePhone", "limit": "150", "sobject_name": "Contact", "table_list": "Account"}, "keyword": "action", "name": "search_sobjects", "number": 7, "provider": "salesforce", "skip": false}, {"as": "", "block": [{"as": "991904b6", "block": [], "input": {"Email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"539fb3da_1c0a_4a76_9a21_a2e284cf90e0\"]}')}", "field_list": "NumberOfEmployees\nCat_Company_Size__c\nId\nAnnual_Revenue__c\nAnnualRevenue\nPhone\nMobilePhone\nVerified_Phone__c\nCompany_Phone__c", "limit": "150", "sobject_name": "Lead"}, "keyword": "action", "name": "search_sobjects", "number": 9, "provider": "salesforce", "skip": false}], "input": {}, "keyword": "else", "name": "", "number": 8, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"6ca0921b_9ea9_4c0d_9656_0b0764c8ffa6\"]}')}", "operand": "starts_with", "rhs": "003"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 6, "provider": "", "skip": false}, {"as": "", "block": [{"as": "e8296571", "block": [], "input": {"Boomi_takedown": "true", "name": "2aa4b621-c467-46c4-96b0-a9f8f581caf1:bca111ab:Boomi_takedown"}, "keyword": "action", "name": "update_variables", "number": 11, "provider": "workato_variable", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"f0613599_b3fc_4ee2_8834_4470f9a4e8a8\"]}')}", "operand": "contains", "rhs": "boomi"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 10, "provider": "", "skip": false}, {"as": "", "block": [{"as": "", "block": [{"as": "ade57d56", "block": [], "input": {"list_item": {"channel_id": "=lookup('4003733', channel_name: '#demorequest-strategic')['channel_id']", "channel_name": "#demorequest-strategic"}, "location": "end", "name": "02ec5e69-9335-45f1-9b4f-81370bf8262f:435d85e7"}, "keyword": "action", "name": "insert_to_list", "number": 14, "provider": "workato_variable", "skip": false}, {"as": "", "block": [{"as": "ffff2e0e", "block": [], "input": {"list_item": {"channel_id": "=lookup('4003733', channel_name: '#demo_request_report')['channel_id']", "channel_name": "#demo_request_report"}, "location": "end", "name": "02ec5e69-9335-45f1-9b4f-81370bf8262f:435d85e7"}, "keyword": "action", "name": "insert_to_list", "number": 16, "provider": "workato_variable", "skip": false}], "input": {}, "keyword": "else", "name": "", "number": 15, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"991904b6\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"AnnualRevenue\"]}').presence or _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"7518c989\",\"path\":[\"Contact\",{\"path_element_type\":\"current_item\"},\"Account\",\"AnnualRevenue\"]}').presence", "operand": "present"}, {"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"7518c989\",\"path\":[\"Contact\",{\"path_element_type\":\"current_item\"},\"Account\",\"AnnualRevenue\"]}').presence or _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"991904b6\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"AnnualRevenue\"]}').presence", "operand": "greater_than", "rhs": "=2500000000"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 13, "provider": "", "skip": false}, {"as": "", "block": [{"as": "5b8fa90d", "block": [], "input": {"list_item": {"channel_id": "=lookup('4003733', channel_name: '#demo_request_rpt_smb')['channel_id']", "channel_name": "#demo_request_rpt_smb"}, "location": "end", "name": "02ec5e69-9335-45f1-9b4f-81370bf8262f:435d85e7"}, "keyword": "action", "name": "insert_to_list", "number": 18, "provider": "workato_variable", "skip": false}], "input": {}, "keyword": "else", "name": "", "number": 17, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "=((_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"991904b6\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"NumberOfEmployees\"]}').presence or _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"7518c989\",\"path\":[\"Contact\",{\"path_element_type\":\"current_item\"},\"Account\",\"NumberOfEmployees\"]}').presence).present?? ( (_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"991904b6\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"NumberOfEmployees\"]}').presence or _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"7518c989\",\"path\":[\"Contact\",{\"path_element_type\":\"current_item\"},\"Account\",\"NumberOfEmployees\"]}').presence) > 100) : false) or ((_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"991904b6\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"Cat_Company_Size__c\"]}').presence or _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"7518c989\",\"path\":[\"Contact\",{\"path_element_type\":\"current_item\"},\"Account\",\"Cat_Company_Size__c\"]}').presence)&.match?(/(^A|^B|^C|^D)/).is_not_true? and (_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"991904b6\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"Cat_Company_Size__c\"]}').presence or _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"7518c989\",\"path\":[\"Contact\",{\"path_element_type\":\"current_item\"},\"Account\",\"Cat_Company_Size__c\"]}').presence).present?)", "operand": "is_true", "rhs": "100"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 12, "provider": "", "skip": false}, {"as": "1cd98d30", "block": [], "input": {"message": "Asia/Dubai,Asia/Baghdad,Asia/Istanbul,Asia/Qatar,Asia/Tehran,Asia/Tel_Aviv,Asia/Kabul,Asia/Kuwait,Asia/Muscat,Asia/Riyadh,Asia/Aden,Asia/Almaty,Asia/Amman,Asia/Aqtau,Asia/Aqtobe,Asia/Ashgabat,Asia/Atyrau,Asia/Bahrain,Asia/Damascus,Asia/Dushanbe,Asia/Famagusta,Asia/Gaza,Asia/Hebron,Asia/Samarkand,Asia/Jerusalem", "user_logs_enabled": "false"}, "keyword": "action", "name": "log_message", "number": 19, "provider": "logger", "skip": false}, {"as": "", "block": [{"as": "1843e57b", "block": [], "input": {"message": " Australia/Adelaide\n• Australia/Brisbane\n• Australia/Darwin\n• Australia/Hobart\n• Australia/Melbourne\n• Australia/Perth\n• Australia/Sydney\n• Pacific/Auckland", "user_logs_enabled": "false"}, "keyword": "action", "name": "log_message", "number": 21, "provider": "logger", "skip": false}, {"as": "", "block": [{"as": "be5dc2a4", "block": [], "input": {"list_item": {"channel_id": "=lookup('4003733', channel_name: '#anz_demo_request_all')['channel_id']", "channel_name": "#anz_demo_request_all"}, "location": "end", "name": "02ec5e69-9335-45f1-9b4f-81370bf8262f:435d85e7"}, "keyword": "action", "name": "insert_to_list", "number": 23, "provider": "workato_variable", "skip": false}], "input": {"conditions": [{"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"cc7288a2_7248_4719_b2a4_97356d388269\"]}').downcase", "operand": "contains", "rhs": "australia"}, {"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"cc7288a2_7248_4719_b2a4_97356d388269\"]}').downcase", "operand": "contains", "rhs": "pacific/auckland"}, {"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"539fb3da_1c0a_4a76_9a21_a2e284cf90e0\"]}').present? ? (_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"539fb3da_1c0a_4a76_9a21_a2e284cf90e0\"]}').split(\".\").last) : \"no email\"", "operand": "contains", "rhs": ".co.nz"}, {"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"7518c989\",\"path\":[\"Contact\",{\"path_element_type\":\"current_item\"},\"Phone\"]}').presence or _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"7518c989\",\"path\":[\"Contact\",{\"path_element_type\":\"current_item\"},\"MobilePhone\"]}').presence or _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"7518c989\",\"path\":[\"Contact\",{\"path_element_type\":\"current_item\"},\"Verified_Phone__c\"]}').presence or _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"991904b6\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"Phone\"]}').presence or _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"991904b6\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"MobilePhone\"]}').presence or _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"991904b6\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"Company_Phone__c\"]}').presence or _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"991904b6\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"Verified_Phone__c\"]}').presence or \"\"", "operand": "contains", "rhs": "+61"}, {"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"7518c989\",\"path\":[\"Contact\",{\"path_element_type\":\"current_item\"},\"Phone\"]}').presence or _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"7518c989\",\"path\":[\"Contact\",{\"path_element_type\":\"current_item\"},\"MobilePhone\"]}').presence or _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"7518c989\",\"path\":[\"Contact\",{\"path_element_type\":\"current_item\"},\"Verified_Phone__c\"]}').presence or _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"991904b6\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"Phone\"]}').presence or _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"991904b6\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"MobilePhone\"]}').presence or _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"991904b6\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"Company_Phone__c\"]}').presence or _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"991904b6\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"Verified_Phone__c\"]}').presence or \"\"", "operand": "contains", "rhs": "+64"}], "operand": "or", "type": "compound"}, "keyword": "if", "name": "", "number": 22, "provider": "", "skip": false}, {"as": "", "block": [{"as": "84df4b64", "block": [], "input": {"list_item": {"channel_id": "=lookup('4003733', channel_name: '#japan_demo_request_all')['channel_id']", "channel_name": "#japan_demo_request_all"}, "location": "end", "name": "02ec5e69-9335-45f1-9b4f-81370bf8262f:435d85e7"}, "keyword": "action", "name": "insert_to_list", "number": 25, "provider": "workato_variable", "skip": false}], "input": {"conditions": [{"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"cc7288a2_7248_4719_b2a4_97356d388269\"]}').downcase", "operand": "contains", "rhs": "tokyo"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 24, "provider": "", "skip": false}, {"as": "", "block": [{"as": "29c43a97", "block": [], "input": {"list_item": {"channel_id": "=lookup('4003733', channel_name: '#asia_demo_request_all')['channel_id']", "channel_name": "#asia_demo_request_all"}, "location": "end", "name": "02ec5e69-9335-45f1-9b4f-81370bf8262f:435d85e7"}, "keyword": "action", "name": "insert_to_list", "number": 27, "provider": "workato_variable", "skip": false}], "input": {"conditions": [{"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"cc7288a2_7248_4719_b2a4_97356d388269\"]}').downcase", "operand": "contains", "rhs": "asia"}, {"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"cc7288a2_7248_4719_b2a4_97356d388269\"]}').downcase", "operand": "not_contains", "rhs": "tokyo"}, {"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"cc7288a2_7248_4719_b2a4_97356d388269\"]}').downcase", "operand": "not_contains", "rhs": "jerusalem"}, {"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"cc7288a2_7248_4719_b2a4_97356d388269\"]}').downcase", "operand": "not_contains", "rhs": "istanbul"}, {"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"cc7288a2_7248_4719_b2a4_97356d388269\"]}').downcase", "operand": "not_contains", "rhs": "tel_aviv"}, {"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"cc7288a2_7248_4719_b2a4_97356d388269\"]}').downcase", "operand": "not_contains", "rhs": "riyadh"}, {"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"cc7288a2_7248_4719_b2a4_97356d388269\"]}').downcase", "operand": "not_contains", "rhs": "qatar"}, {"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"cc7288a2_7248_4719_b2a4_97356d388269\"]}').downcase", "operand": "not_contains", "rhs": "tehran"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 26, "provider": "", "skip": false}, {"as": "", "block": [{"as": "", "block": [{"as": "42c79179", "block": [], "keyword": "action", "name": "insert_to_list", "number": 30, "provider": "workato_variable", "skip": true}, {"as": "0f900f7b", "block": [], "keyword": "action", "name": "insert_to_list", "number": 31, "provider": "workato_variable", "skip": true}], "keyword": "if", "name": "", "number": 29, "provider": "", "skip": true}, {"as": "", "block": [{"as": "f4503945", "block": [], "keyword": "action", "name": "insert_to_list", "number": 33, "provider": "workato_variable", "skip": true}, {"as": "8abbb320", "block": [], "keyword": "action", "name": "insert_to_list", "number": 34, "provider": "workato_variable", "skip": true}], "keyword": "if", "name": "", "number": 32, "provider": "", "skip": true}, {"as": "", "block": [{"as": "", "block": [{"as": "8b7abf99", "block": [], "keyword": "action", "name": "insert_to_list", "number": 37, "provider": "workato_variable", "skip": true}, {"as": "29684175", "block": [], "keyword": "action", "name": "insert_to_list", "number": 38, "provider": "workato_variable", "skip": true}], "keyword": "if", "name": "", "number": 36, "provider": "", "skip": true}, {"as": "", "block": [{"as": "bd5f31f4", "block": [], "keyword": "action", "name": "insert_to_list", "number": 40, "provider": "workato_variable", "skip": true}, {"as": "f2e7d563", "block": [], "keyword": "action", "name": "insert_to_list", "number": 41, "provider": "workato_variable", "skip": true}], "keyword": "if", "name": "", "number": 39, "provider": "", "skip": true}], "keyword": "else", "name": "", "number": 35, "provider": "", "skip": true}], "keyword": "if", "name": "", "number": 28, "provider": "", "skip": true}, {"as": "", "block": [{"as": "", "block": [{"as": "7f60a4d9", "block": [], "input": {"list_item": {"channel_id": "=lookup('4003733', channel_name: '#asia_demo_request_smb')['channel_id']", "channel_name": "#demo_request_rpt_emea"}, "location": "end", "name": "02ec5e69-9335-45f1-9b4f-81370bf8262f:435d85e7"}, "keyword": "action", "name": "insert_to_list", "number": 44, "provider": "workato_variable", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"cc7288a2_7248_4719_b2a4_97356d388269\"]}')}", "operand": "contains", "rhs": "Africa"}, {"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"cc7288a2_7248_4719_b2a4_97356d388269\"]}')}", "operand": "contains", "rhs": "Europe"}, {"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"1cd98d30\",\"path\":[\"message\"]}').split(\",\").include?(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"cc7288a2_7248_4719_b2a4_97356d388269\"]}'))", "operand": "is_true"}], "operand": "or", "type": "compound"}, "keyword": "if", "name": "", "number": 43, "provider": "", "skip": false}, {"as": "", "block": [{"as": "e73cfaf6", "block": [], "input": {"list_item": {"channel_id": "=lookup('4003733', channel_name: '#demo_request_report_israel')['channel_id']", "channel_name": "#demo_request_report_israel"}, "location": "end", "name": "02ec5e69-9335-45f1-9b4f-81370bf8262f:435d85e7"}, "keyword": "action", "name": "insert_to_list", "number": 46, "provider": "workato_variable", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"cc7288a2_7248_4719_b2a4_97356d388269\"]}')}", "operand": "contains", "rhs": "Asia/Jerusalem"}, {"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"cc7288a2_7248_4719_b2a4_97356d388269\"]}')}", "operand": "contains", "rhs": "Asia/Tel_Aviv"}], "operand": "or", "type": "compound"}, "keyword": "if", "name": "", "number": 45, "provider": "", "skip": false}], "input": {}, "keyword": "else", "name": "", "number": 42, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "=[\"Asia\",\"Australia\",\"Pacific\"]", "operand": "contains", "rhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"cc7288a2_7248_4719_b2a4_97356d388269\"]}').split(\"/\").first"}, {"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"1cd98d30\",\"path\":[\"message\"]}').split(\",\").include?(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"cc7288a2_7248_4719_b2a4_97356d388269\"]}'))", "operand": "is_not_true", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 20, "provider": "", "skip": false}, {"as": "", "block": [{"as": "dbb21dbb", "block": [], "input": {"list_item": {"channel_id": "=lookup('4003733', channel_name: '#request_trial_leads')['channel_id']", "channel_name": "#request_trial_leads"}, "location": "end", "name": "02ec5e69-9335-45f1-9b4f-81370bf8262f:435d85e7"}, "keyword": "action", "name": "insert_to_list", "number": 48, "provider": "workato_variable", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c786cec4\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"6d114605_5746_49d3_9a17_b2603d5e241e\"]}')}", "operand": "equals_to", "rhs": "homepage_trial"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 47, "provider": "", "skip": false}, {"as": "bf501b1d", "block": [], "input": {"result": {"boomi_takedown": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"bca111ab\",\"path\":[\"Boomi_takedown\"]}')}", "slack_channels": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"435d85e7\",\"path\":[\"list_items\"]}')}", "slack_channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"435d85e7\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"channel_name\"]}')}", "slack_channel_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"435d85e7\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"channel_id\"]}')}"}}}, "keyword": "action", "name": "return_result", "number": 49, "provider": "workato_recipe_function", "skip": false}], "input": {"parameters_schema_json": "[{\"name\":\"request_no\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Request no\"}]", "result_schema_json": "[{\"name\":\"boomi_takedown\",\"type\":\"boolean\",\"optional\":true,\"control_type\":\"checkbox\",\"label\":\"Boomi takedown\",\"render_input\":{},\"parse_output\":{},\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Boomi takedown\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"boomi_takedown\",\"type\":\"boolean\",\"optional\":true}},{\"name\":\"slack_channels\",\"type\":\"array\",\"optional\":true,\"properties\":[{\"name\":\"slack_channel\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Slack channel\"},{\"name\":\"slack_channel_id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Slack channel ID\"}],\"of\":\"object\",\"label\":\"Slack channels\"}]"}, "keyword": "trigger", "name": "execute", "number": 1, "provider": "workato_recipe_function", "skip": false}"""
_EXPECTED_TREE: dict[str, Any] = json.loads(_RAW_PIN_JSON)


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


def validate_124273557(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')}")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    # Dead-code proof: nodes 28-41 must remain skip=true (the raw executor
    # skips them); if any becomes live the pin above already failed, but keep
    # the explicit assertion as documentation-grade evidence.
    dead = {node["number"]: node["skip"] for node in _walk_nodes(raw) if node.get("number") in DEAD_NODE_NUMBERS}
    if sorted(dead) != DEAD_NODE_NUMBERS or not all(dead.values()):
        raise RuntimeError(f"recipe {RECIPE_ID} dead nodes 28-41 changed: {dead}")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
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


def seed_124273557(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_124273557(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    request_no = _require_request_no(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"workato_db_table", "lookup_table", "salesforce"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    db_section = seed_in.get("workato_db_table")
    db_row = _require_db_row(db_section, request_no)
    lookup_section = seed_in.get("lookup_table")
    _require_lookup_tables(lookup_section)
    sf_section = seed_in.get("salesforce")
    if not isinstance(sf_section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce (live seed)")
    _require_sf_schema(sf_section)
    is_contact_variant = str(db_row.get(DB_FIELD_SFDC_ID) or "") == CONTACT_REF_TOKEN
    _require_sf_records(sf_section, is_contact_variant)
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    for key in EXPECT_REQUIRED_KEYS:
        if key not in expect:
            raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required key {key!r}")
    if expect.get("return_result") != {
        "boomi_takedown": expect.get("boomi_takedown"),
        "slack_channels": expect.get("slack_channels"),
    }:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.return_result must equal the "
            "boomi_takedown/slack_channels pins (single source of truth)"
        )
    provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": sf_section})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    refs = _live_refs(provision, is_contact_variant)
    resolved_db = _replace_value(deepcopy(db_section), refs)
    _require_no_tokens(resolved_db, "seed.workato_db_table")
    resolved_expect = _replace_value(deepcopy(expect), refs)
    _require_no_tokens(resolved_expect, "expect")
    if is_contact_variant:
        resolved_sfdc = str(resolved_db["tables"][DB_TABLE_ID][0].get(DB_FIELD_SFDC_ID) or "")
        if not resolved_sfdc.startswith("003"):
            raise RuntimeError(
                f"recipe {RECIPE_ID} live Contact id does not start with '003' "
                f"(IF#6 routing would break): {resolved_sfdc!r}"
            )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": resolved_expect,
        "raw_validation": validation,
        "workato_db_table": resolved_db,
        "lookup_table": deepcopy(lookup_section),
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": refs,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_124273557(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_124273557(raw)
    for key in ("workato_db_table", "lookup_table", "salesforce_live"):
        if not isinstance(seed.get(key), dict):
            raise RuntimeError(f"recipe {RECIPE_ID} seed file missing section {key!r}")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    cleanup_response: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = _snapshot(ctx)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx)
    finally:
        # Live cleanup AFTER the final snapshot: delete the benchmark-owned
        # Salesforce records seeded for this run (the recipe itself is
        # read-only on Salesforce; fail-fast on leftovers via the verifier).
        cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
    details["cleanup_response"] = cleanup_response
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_124273557(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _walk_nodes(node: dict[str, Any]) -> list[dict[str, Any]]:
    found = [node]
    for child in node.get("block") or []:
        if isinstance(child, dict):
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


def _require_request_no(trigger: dict[str, Any]) -> str:
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict) or sorted(parameters.keys()) != ["request_no"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.parameters must carry exactly request_no; got "
            f"{sorted(parameters.keys()) if isinstance(parameters, dict) else parameters}"
        )
    request_no = str(parameters.get("request_no") or "")
    if not request_no.isdigit():
        raise RuntimeError(f"recipe {RECIPE_ID} trigger request_no must be a digit string: {request_no!r}")
    return request_no


def _require_db_row(db_section: Any, request_no: str) -> dict[str, Any]:
    tables = db_section.get("tables") if isinstance(db_section, dict) else None
    if not isinstance(tables, dict) or sorted(tables.keys()) != [DB_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table.tables must declare exactly table {DB_TABLE_ID}"
        )
    rows = tables.get(DB_TABLE_ID)
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} db table {DB_TABLE_ID} must seed exactly one record "
            "(records.current_item resolves to the first record; request_no is unique)"
        )
    row = rows[0]
    if sorted(row.keys()) != sorted(DB_SEED_FIELD_IDS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} db record must carry exactly the six dereferenced field ids "
            f"{sorted(DB_SEED_FIELD_IDS)}; got {sorted(row.keys())}"
        )
    if not isinstance(row.get(DB_FIELD_REQUEST_NO), int) or str(row[DB_FIELD_REQUEST_NO]) != request_no:
        raise RuntimeError(
            f"recipe {RECIPE_ID} db record request_no must be the integer form of the trigger "
            f"request_no {request_no}; got {row.get(DB_FIELD_REQUEST_NO)!r}"
        )
    for field_id in (DB_FIELD_SFDC_ID, DB_FIELD_EMAIL, DB_FIELD_TZ, DB_FIELD_PAGE, DB_FIELD_SOURCE):
        if not str(row.get(field_id) or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} db record field {field_id} must be non-empty")
    return row


def _require_lookup_tables(lookup_section: Any) -> None:
    tables = lookup_section.get("tables") if isinstance(lookup_section, dict) else None
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted(
        [CHANNEL_LOOKUP_TABLE_ID, CONFIG_LOOKUP_TABLE_ID]
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must declare exactly tables "
            f"{CHANNEL_LOOKUP_TABLE_ID} (channel map) and {CONFIG_LOOKUP_TABLE_ID} (get_entries step)"
        )
    channels = tables.get(CHANNEL_LOOKUP_TABLE_ID)
    if not isinstance(channels, list) or [
        row.get("channel_name") for row in channels if isinstance(row, dict)
    ] != CHANNEL_NAMES:
        raise RuntimeError(
            f"recipe {RECIPE_ID} lookup table {CHANNEL_LOOKUP_TABLE_ID} must seed the ten channel "
            f"rows {CHANNEL_NAMES} in order (named columns channel_name/channel_id)"
        )
    for row in channels:
        if sorted(row.keys()) != ["channel_id", "channel_name"] or not str(row.get("channel_id") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} lookup table {CHANNEL_LOOKUP_TABLE_ID} rows must be "
                f"{{channel_name, channel_id}} with non-empty ids; got {row}"
            )
    config_rows = tables.get(CONFIG_LOOKUP_TABLE_ID)
    if not isinstance(config_rows, list) or not config_rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} lookup table {CONFIG_LOOKUP_TABLE_ID} must seed at least one row "
            "(step 4 get_entries executes even though its output is unused)"
        )


def _require_sf_schema(sf_section: dict[str, Any]) -> None:
    if sf_section.get("schema") != SF_SCHEMA_PIN:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must pin exactly the five dereferenced "
            f"custom fields {SF_SCHEMA_PIN} (ensure_custom_field schema-in-seed)"
        )


def _require_sf_records(sf_section: dict[str, Any], is_contact_variant: bool) -> None:
    records = [record for record in sf_section.get("records") or [] if isinstance(record, dict)]
    by_sobject: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_sobject.setdefault(str(record.get("sobject") or ""), []).append(record)
    if any(len(rows) > 1 for rows in by_sobject.values()):
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce must have at most one record per sobject")
    if is_contact_variant:
        if not sf_section.get("relationship_expansion"):
            raise RuntimeError(
                f"recipe {RECIPE_ID} contact variants require seed.salesforce.relationship_expansion "
                "(pills walk Contact.current_item.Account.*)"
            )
        if sorted(by_sobject.keys()) != ["Account", "Contact"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} contact variants must seed exactly one Account and one Contact; "
                f"got {sorted(by_sobject.keys())}"
            )
        account, contact = by_sobject["Account"][0], by_sobject["Contact"][0]
        if [str(account.get("ref") or ""), str(contact.get("ref") or "")] != ["account", "contact"]:
            raise RuntimeError(f"recipe {RECIPE_ID} Account/Contact seed records must carry refs account/contact")
        if records[0] is not account:
            raise RuntimeError(f"recipe {RECIPE_ID} the Account record must precede the Contact ($REF threading)")
        account_fields = account.get("fields") if isinstance(account.get("fields"), dict) else {}
        contact_fields = contact.get("fields") if isinstance(contact.get("fields"), dict) else {}
        if not str(account_fields.get("Name") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} Account seed requires explicit Name")
        if not str(contact_fields.get("LastName") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} Contact seed requires explicit LastName")
        if contact_fields.get("AccountId") != ACCOUNT_REF_TOKEN:
            raise RuntimeError(
                f"recipe {RECIPE_ID} Contact.AccountId must be the {ACCOUNT_REF_TOKEN} token "
                "(owned parent Account threading)"
            )
    else:
        if sorted(by_sobject.keys()) != ["Lead"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} lead variants must seed exactly one Lead record "
                f"(a non-matching decoy proves zero-result searches); got {sorted(by_sobject.keys())}"
            )
        lead_fields = by_sobject["Lead"][0].get("fields") if isinstance(by_sobject["Lead"][0].get("fields"), dict) else {}
        for key in ("LastName", "Company", "Email"):
            if not str(lead_fields.get(key) or "").strip():
                raise RuntimeError(f"recipe {RECIPE_ID} Lead seed requires explicit {key}")


def _live_refs(provision: dict[str, Any], is_contact_variant: bool) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    ids: dict[str, str] = {}
    for record in salesforce.get("records") or []:
        if not isinstance(record, dict):
            continue
        sobject = str(record.get("sobject") or "")
        live_id = str(record.get("id") or "")
        if not _SF_ID_RE.fullmatch(live_id):
            raise RuntimeError(f"recipe {RECIPE_ID} provisioned {sobject} id looks invalid: {live_id!r}")
        if sobject in ids:
            raise RuntimeError(f"recipe {RECIPE_ID} expected at most one provisioned {sobject} record")
        ids[sobject] = live_id
    expected = {"Account", "Contact"} if is_contact_variant else {"Lead"}
    if set(ids) != expected:
        raise RuntimeError(f"recipe {RECIPE_ID} provisioned sobjects {sorted(ids)} != expected {sorted(expected)}")
    refs = {f"${sobject.upper()}_ID": live_id for sobject, live_id in ids.items()}
    return refs


def _replace_value(value: Any, refs: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_value(item, refs) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_value(item, refs) for item in value]
    if isinstance(value, str):
        out = value
        for token, replacement in refs.items():
            out = out.replace(token, replacement)
        return out
    return value


def _require_no_tokens(value: Any, label: str) -> None:
    leftover = sorted(set(_TOKEN_RE.findall(json.dumps(value))))
    if leftover:
        raise RuntimeError(f"recipe {RECIPE_ID} {label} has unresolved seed tokens: {leftover}")


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return {
        "salesforce": ctx.tools.call("harness.salesforce.snapshot", {}),
        "workato_db_table": ctx.tools.call("harness.workato_db_table.snapshot", {}),
        "lookup_table": ctx.tools.call("harness.lookup_table.snapshot", {}),
    }


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
