from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_128901328


RECIPE_ID = "128901328"
SEED_TYPE = "recipe_function_workspace_id_matching_variant"
TRACK = "workato_recipe_function_smart_list_salesforce_workspace_matching"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "c3ba512c"
SF_SOBJECT = "Workato_User__c"
SF_SCHEMA_FIELDS = (
    "Account__c",
    "User_ID__c",
    "Data_Center__c",
    "Workspace_ID__c",
    "OEM_Account__c",
)
MATCHED_ROW_KEYS = {"id", "account", "workspace_id", "data_center"}
PENDING_ROW_KEYS = {"id", "federated_account_id", "data_center", "workspace_id"}
EXPECT_REQUIRED_KEYS = (
    "tools",
    "tool_expectations",
    "executed_action_count",
    "result",
    "smart_list_sqls",
)
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "workato_runtime.declare_list",
    "workato_smart_list.create_list",
    "workato_runtime.update_variables",
    "workato_smart_list.query_list",
    "workato_runtime.insert_to_list_batch",
    "salesforce.search_records",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_recipe_function.return_result",
]
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_SF_ID_RE = re.compile(r"^[a-zA-Z0-9]{15,18}$")

RAW_NODE_PINS_JSON = r"""{"as": "c3ba512c", "block": [{"as": "1d25a4fd", "input": {"variables": {"schema": "[{\"name\":\"workspace_id_query\",\"type\":\"string\",\"optional\":true,\"label\":\"Workspace ID Query\",\"control_type\":\"text\"}]"}}, "keyword": "action", "name": "declare_variable", "number": 2, "provider": "workato_variable"}, {"as": "0aa12445", "input": {"list_item_schema_json": "[{\"name\":\"id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"ID\"},{\"name\":\"account_id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Account ID\"},{\"name\":\"federated_id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Federated ID\"},{\"name\":\"data_center\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Data center\"},{\"name\":\"workspace_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Workspace ID\"},{\"name\":\"oem_account_id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Oem account ID\"}]", "name": "New Matched Workato Users"}, "keyword": "action", "name": "declare_list", "number": 3, "provider": "workato_variable"}, {"as": "0fd15d79", "input": {"variables": {"data": {"matched_workato_users_query": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"c3ba512c\",\"path\":[\"parameters\",\"matched_workato_users\"]}').pluck('id').join(\"','\")"}, "schema": "[{\"name\":\"matched_workato_users_query\",\"type\":\"string\",\"optional\":true,\"label\":\"Matched Workato Users Query\",\"control_type\":\"text\"}]"}}, "keyword": "action", "name": "declare_variable", "number": 4, "provider": "workato_variable"}, {"as": "5ffce8ff", "input": {"list_name": "pending_workato_users", "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"c3ba512c\",\"path\":[\"parameters\",\"pending_workato_users\"]}')", "primary_index": "id"}, "keyword": "action", "name": "create_list", "number": 5, "provider": "workato_smart_list"}, {"as": null, "block": [{"as": "019f6bcb", "batch_size": "500", "block": [{"as": "992eae0b", "input": {"name": "81a635c1-bac0-40ca-9d6a-f41224a22d3c:1d25a4fd:workspace_id_query", "workspace_id_query": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"019f6bcb\",\"path\":[\"batch\"]}').where(\"workspace_id !=\": nil, \"workspace_id !=\": \"\").format_map('(workspace_id = \\'%{workspace_id}\\' AND data_center = \\'%{data_center}\\')').join(\" OR \") + \" AND\""}, "keyword": "action", "name": "update_variables", "number": 8, "provider": "workato_variable"}, {"as": "af07fc80", "input": {"col_sep": "comma", "csv": "false", "headers": "false", "output_schema_by": "index", "result_schema_json": "[{\"name\":\"id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"ID\"},{\"name\":\"federated_account_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Federated account ID\"},{\"name\":\"workspace_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Workspace ID\"},{\"name\":\"data_center\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Data center\"}]", "sql": "SELECT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5ffce8ff\",\"path\":[\"columns\", \"id\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5ffce8ff\",\"path\":[\"columns\", \"federated_account_id\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5ffce8ff\",\"path\":[\"columns\", \"workspace_id\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5ffce8ff\",\"path\":[\"columns\", \"data_center\"]}')} \nFROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5ffce8ff\",\"path\":[\"list_name\"]}')}\nWHERE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"1d25a4fd\",\"path\":[\"workspace_id_query\"]}')} #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5ffce8ff\",\"path\":[\"columns\", \"id\"]}')} NOT IN ('#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"0fd15d79\",\"path\":[\"matched_workato_users_query\"]}')}')"}, "keyword": "action", "name": "query_list", "number": 9, "provider": "workato_smart_list"}, {"as": null, "block": [{"as": "b51a5bf5", "input": {"list_items": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"af07fc80\",\"path\":[\"rows\"]}')}", "account_id": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"c3ba512c\",\"path\":[\"parameters\",\"matched_workato_users\"]}').where(workspace_id: _dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"af07fc80\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"workspace_id\"]}'), data_center: _dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"af07fc80\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"data_center\"]}')).pluck('account').first", "data_center": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"af07fc80\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"data_center\"]}')}", "federated_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"af07fc80\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"federated_account_id\"]}')}", "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"af07fc80\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}", "workspace_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"af07fc80\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"workspace_id\"]}')}"}, "location": "end", "name": "b32f4956-24a2-424f-a3c6-8cd525758126:0aa12445"}, "keyword": "action", "name": "insert_to_list_batch", "number": 11, "provider": "workato_variable"}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"af07fc80\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}", "operand": "greater_than", "rhs": "0"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": null, "number": 10, "provider": null}], "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"c3ba512c\",\"path\":[\"parameters\", \"matched_workato_users\"]}')}"}, "keyword": "foreach", "name": null, "number": 7, "provider": null, "repeat_mode": "batch", "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"c3ba512c\",\"path\":[\"parameters\", \"matched_workato_users\"]}')}"}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"c3ba512c\",\"path\":[\"parameters\", \"matched_workato_users\", {\"path_element_type\": \"size\"}]}')}", "operand": "greater_than", "rhs": "0"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": null, "number": 6, "provider": null}, {"as": "0e22330c", "input": {"matched_workato_users_query": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"c3ba512c\",\"path\":[\"parameters\",\"matched_workato_users\"]}').pluck('id') + _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"0aa12445\",\"path\":[\"list_items\"]}').pluck('id')).join(\"','\")", "name": "5bca2bc9-c5e0-4b8d-8bf4-c2253d24574d:0fd15d79:matched_workato_users_query"}, "keyword": "action", "name": "update_variables", "number": 12, "provider": "workato_variable"}, {"as": "882d4b96", "input": {"col_sep": "comma", "csv": "false", "headers": "false", "output_schema_by": "index", "result_schema_json": "[{\"name\":\"workspace_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"data_center\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Data center\"}]", "sql": "SELECT DISTINCT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5ffce8ff\",\"path\":[\"columns\", \"workspace_id\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5ffce8ff\",\"path\":[\"columns\", \"data_center\"]}')}\nFROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5ffce8ff\",\"path\":[\"list_name\"]}')}\nWHERE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5ffce8ff\",\"path\":[\"columns\", \"id\"]}')} NOT IN ('#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"0fd15d79\",\"path\":[\"matched_workato_users_query\"]}')}') AND #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5ffce8ff\",\"path\":[\"columns\", \"workspace_id\"]}')} IS NOT NULL AND #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5ffce8ff\",\"path\":[\"columns\", \"workspace_id\"]}')} != ''"}, "keyword": "action", "name": "query_list", "number": 13, "provider": "workato_smart_list"}, {"as": "54bf5f72", "batch_size": "200", "block": [{"as": "47c2d0a6", "input": {"name": "81a635c1-bac0-40ca-9d6a-f41224a22d3c:1d25a4fd:workspace_id_query", "workspace_id_query": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"54bf5f72\",\"path\":[\"batch\"]}').format_map('(User_ID__c = \\'%{workspace_id}\\' AND Data_Center__c = \\'%{data_center}\\')').join(\" OR \")"}, "keyword": "action", "name": "update_variables", "number": 15, "provider": "workato_variable"}, {"as": "bf6843f0", "input": {"field_list": "Id\nAccount__c\nUser_ID__c\nData_Center__c\nWorkspace_ID__c\nOEM_Account__c", "limit": "2000", "query": "(#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"1d25a4fd\",\"path\":[\"workspace_id_query\"]}')}) AND (Account__c != null OR OEM_Account__c != null)", "sobject_name": "Workato_User__c"}, "keyword": "action", "name": "search_sobjects_soql", "number": 16, "provider": "salesforce"}, {"as": null, "block": [{"as": "d6f81205", "input": {"list_item_schema_json": "[{\"name\":\"Id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"ID\"},{\"name\":\"Account__c\",\"type\":\"string\",\"optional\":true,\"label\":\"Account\",\"control_type\":\"text\"},{\"name\":\"Data_Center__c\",\"type\":\"string\",\"optional\":true,\"label\":\"Data Center\",\"control_type\":\"text\"},{\"name\":\"OEM_Account__c\",\"type\":\"string\",\"optional\":true,\"label\":\"OEM Account\",\"control_type\":\"text\"},{\"name\":\"User_ID__c\",\"type\":\"integer\",\"optional\":true,\"label\":\"User Id\",\"control_type\":\"integer\",\"parse_output\":\"integer_conversion\",\"render_input\":\"integer_conversion\"},{\"name\":\"Workspace_ID__c\",\"type\":\"integer\",\"optional\":true,\"label\":\"Workspace Id\",\"control_type\":\"integer\",\"parse_output\":\"integer_conversion\",\"render_input\":\"integer_conversion\"}]", "list_items": {"Account__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"bf6843f0\",\"path\":[\"Workato_User__c\", {\"path_element_type\": \"current_item\"}, \"Account__c\"]}')}", "Data_Center__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"bf6843f0\",\"path\":[\"Workato_User__c\", {\"path_element_type\": \"current_item\"}, \"Data_Center__c\"]}')}", "Id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"bf6843f0\",\"path\":[\"Workato_User__c\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}", "OEM_Account__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"bf6843f0\",\"path\":[\"Workato_User__c\", {\"path_element_type\": \"current_item\"}, \"OEM_Account__c\"]}')}", "User_ID__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"bf6843f0\",\"path\":[\"Workato_User__c\", {\"path_element_type\": \"current_item\"}, \"User_ID__c\"]}')}", "Workspace_ID__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"bf6843f0\",\"path\":[\"Workato_User__c\", {\"path_element_type\": \"current_item\"}, \"Workspace_ID__c\"]}')}", "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"bf6843f0\",\"path\":[\"Workato_User__c\"]}')}"}, "name": "Workato_users"}, "keyword": "action", "name": "declare_list", "number": 18, "provider": "workato_variable"}, {"as": "6c6ea904", "input": {"input_mode": "raw", "name": "81a635c1-bac0-40ca-9d6a-f41224a22d3c:1d25a4fd:workspace_id_query", "workspace_id_query": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"d6f81205\",\"path\":[\"list_items\"]}').format_map('(workspace_id = \\'%{User_ID__c}\\' AND data_center = \\'%{Data_Center__c}\\')').join(\" OR \")"}, "keyword": "action", "name": "update_variables", "number": 19, "provider": "workato_variable"}, {"as": "e720c7be", "input": {"col_sep": "comma", "csv": "false", "headers": "false", "output_schema_by": "index", "result_schema_json": "[{\"name\":\"id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"ID\"},{\"name\":\"federated_account_id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Federated account ID\"},{\"name\":\"workspace_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Workspace ID\"},{\"name\":\"data_center\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Data center\"}]", "sql": "SELECT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5ffce8ff\",\"path\":[\"columns\", \"id\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5ffce8ff\",\"path\":[\"columns\", \"federated_account_id\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5ffce8ff\",\"path\":[\"columns\", \"workspace_id\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5ffce8ff\",\"path\":[\"columns\", \"data_center\"]}')} \nFROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5ffce8ff\",\"path\":[\"list_name\"]}')}\nWHERE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"1d25a4fd\",\"path\":[\"workspace_id_query\"]}')} AND #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5ffce8ff\",\"path\":[\"columns\", \"id\"]}')} NOT IN ('#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"0fd15d79\",\"path\":[\"matched_workato_users_query\"]}')}')"}, "keyword": "action", "name": "query_list", "number": 20, "provider": "workato_smart_list"}, {"as": "e99e89fa", "input": {"list_items": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"e720c7be\",\"path\":[\"rows\"]}')}", "account_id": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"d6f81205\",\"path\":[\"list_items\"]}').where(Workspace_ID__c: _dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"e720c7be\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"workspace_id\"]}'), Data_Center__c: _dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"e720c7be\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"data_center\"]}')).pluck('Account__c').first", "data_center": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"e720c7be\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"data_center\"]}')}", "federated_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"e720c7be\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"federated_account_id\"]}')}", "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"e720c7be\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}", "oem_account_id": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"d6f81205\",\"path\":[\"list_items\"]}').where(Workspace_ID__c: _dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"e720c7be\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"workspace_id\"]}'), Data_Center__c: _dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"e720c7be\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"data_center\"]}')).pluck('OEM_Account__c').first", "workspace_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"e720c7be\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"workspace_id\"]}')}"}, "location": "end", "name": "b32f4956-24a2-424f-a3c6-8cd525758126:0aa12445"}, "keyword": "action", "name": "insert_to_list_batch", "number": 21, "provider": "workato_variable"}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"bf6843f0\",\"path\":[\"Workato_User__c\", {\"path_element_type\": \"size\"}]}')}", "operand": "greater_than", "rhs": "0"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": null, "number": 17, "provider": null}], "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"882d4b96\",\"path\":[\"rows\"]}')}"}, "keyword": "foreach", "name": null, "number": 14, "provider": null, "repeat_mode": "batch", "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"882d4b96\",\"path\":[\"rows\"]}')}"}, {"as": "f3c139a5", "input": {"result": {"new_matched_workato_users": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"0aa12445\",\"path\":[\"list_items\"]}')}", "account_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"0aa12445\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"account_id\"]}')}", "data_center": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"0aa12445\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"data_center\"]}')}", "federated_account_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"0aa12445\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"federated_id\"]}')}", "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"0aa12445\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}", "oem_account_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"0aa12445\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"oem_account_id\"]}')}", "workspace_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"0aa12445\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"workspace_id\"]}')}"}}}, "keyword": "action", "name": "return_result", "number": 22, "provider": "workato_recipe_function"}], "input": {"parameters_schema_json": "[{\"name\":\"matched_workato_users\",\"type\":\"array\",\"of\":\"object\",\"label\":\"Matched workato users\",\"optional\":false,\"properties\":[{\"control_type\":\"text\",\"label\":\"ID\",\"name\":\"id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Account\",\"name\":\"account\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Workspace ID\",\"name\":\"workspace_id\",\"type\":\"string\",\"optional\":false},{\"name\":\"data_center\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Data center\"}]},{\"name\":\"pending_workato_users\",\"type\":\"array\",\"of\":\"object\",\"label\":\"Pending workato users\",\"optional\":false,\"properties\":[{\"control_type\":\"text\",\"label\":\"ID\",\"name\":\"id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Federated account ID\",\"name\":\"federated_account_id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Data center\",\"name\":\"data_center\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Workspace ID\",\"name\":\"workspace_id\",\"type\":\"string\",\"optional\":false}]}]", "result_schema_json": "[{\"name\":\"new_matched_workato_users\",\"type\":\"array\",\"of\":\"object\",\"label\":\"New matched workato users\",\"optional\":true,\"properties\":[{\"control_type\":\"text\",\"label\":\"ID\",\"name\":\"id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Account\",\"name\":\"account_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Federated account ID\",\"name\":\"federated_account_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Workspace ID\",\"name\":\"workspace_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Data center\",\"name\":\"data_center\",\"type\":\"string\",\"optional\":true},{\"name\":\"oem_account_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Oem account ID\"}]}]"}, "keyword": "trigger", "name": "execute", "number": 1, "provider": "workato_recipe_function", "skip": false}"""
RAW_NODE_PINS: dict[str, Any] = json.loads(RAW_NODE_PINS_JSON)


def validate_128901328(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')}")
    _require_pin(raw, RAW_NODE_PINS, "trigger#1")
    actions = _collect_actions(raw)
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": _action_summary(actions),
    }


def seed_128901328(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_128901328(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    for key in EXPECT_REQUIRED_KEYS:
        if key not in expect:
            raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required key {key!r}")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"salesforce"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    needs_salesforce = "salesforce.search_records" in (expect.get("tools") or [])
    sf_section = seed_in.get("salesforce")
    if needs_salesforce != isinstance(sf_section, dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce must be present exactly when the variant "
            f"expects a salesforce.search_records call (needs_salesforce={needs_salesforce})"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "raw_validation": validation,
        "harness_tool_calls": [],
    }
    refs: dict[str, str] = {}
    if needs_salesforce:
        _require_salesforce_section(sf_section)
        provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": sf_section})
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
        refs = _salesforce_ref_tokens(sf_section, provision)
        out["salesforce_live"] = deepcopy(provision["state"])
        out["salesforce_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
        out["salesforce_ref_tokens"] = refs
    resolved_expect = _replace_value(deepcopy(expect), refs)
    _require_no_tokens(trigger, "trigger_input")
    _require_no_tokens(resolved_expect, "expect")
    out["expect"] = resolved_expect
    out["harness_tool_calls"] = ctx.tools.call_log()
    for key in ("force_action_error", "job_context"):
        if isinstance(data.get(key), dict):
            out[key] = deepcopy(data[key])
    return attach_variant(out, ctx)


def run_128901328(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_128901328(raw)
    initial_snapshot = _snapshot(ctx, seed)
    cleanup_response: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        if isinstance(seed.get("salesforce_live"), dict):
            cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "cleanup_response": cleanup_response,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_128901328(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_pin(node: dict[str, Any], pin: dict[str, Any], path: str) -> None:
    for key in ("keyword", "number", "as", "provider", "name"):
        if node.get(key) != pin.get(key):
            raise RuntimeError(
                f"recipe {RECIPE_ID} {path} {key} changed: "
                f"expected {pin.get(key)!r}, got {node.get(key)!r}"
            )
    if node.get("skip"):
        raise RuntimeError(f"recipe {RECIPE_ID} {path} is skipped in the raw recipe")
    if node.get("input") != pin.get("input"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} {path} input changed:\n"
            f"expected: {json.dumps(pin.get('input'), sort_keys=True)}\n"
            f"actual:   {json.dumps(node.get('input'), sort_keys=True)}"
        )
    if pin.get("keyword") == "foreach":
        for key in ("repeat_mode", "batch_size", "source"):
            if node.get(key) != pin.get(key):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {path} foreach {key} changed: "
                    f"expected {pin.get(key)!r}, got {node.get(key)!r}"
                )
    expected_children = pin.get("block") or []
    actual_children = [child for child in node.get("block") or [] if isinstance(child, dict)]
    if len(actual_children) != len(expected_children):
        raise RuntimeError(
            f"recipe {RECIPE_ID} {path} block shape changed: expected "
            f"{[(c.get('keyword'), c.get('number')) for c in expected_children]}, got "
            f"{[(c.get('keyword'), c.get('number')) for c in actual_children]}"
        )
    for child, child_pin in zip(actual_children, expected_children):
        _require_pin(child, child_pin, f"{path}>{child_pin.get('keyword')}#{child_pin.get('number')}")


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"number": a.get("number"), "provider": a.get("provider"), "name": a.get("name"), "as": a.get("as")}
        for a in actions
    ]


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {"parameters"} or not isinstance(trigger.get("parameters"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'parameters': {{...}}}}"
        )
    parameters = trigger["parameters"]
    if set(parameters) != {"matched_workato_users", "pending_workato_users"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must carry exactly "
            f"matched_workato_users + pending_workato_users: {sorted(parameters)}"
        )
    matched = parameters.get("matched_workato_users")
    pending = parameters.get("pending_workato_users")
    if not isinstance(matched, list) or not isinstance(pending, list):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter lists must be arrays")
    for label, rows, keys in (
        ("matched_workato_users", matched, MATCHED_ROW_KEYS),
        ("pending_workato_users", pending, PENDING_ROW_KEYS),
    ):
        for row in rows:
            if not isinstance(row, dict) or set(row) != keys:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} trigger {label} row must carry exactly keys "
                    f"{sorted(keys)}: {row!r}"
                )
            for key, value in row.items():
                if not isinstance(value, str):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} trigger {label} row field {key!r} must be an "
                        f"explicit string (schema type string): {value!r}"
                    )
    # Every matched-user pair group must survive the recipe's #8 where filter
    # deterministically: the raw formula carries a duplicate-key Ruby hash
    # ("workspace_id !=": nil then "workspace_id !=": ""); rows with a missing/
    # nil workspace_id would behave differently under last-key-wins Ruby vs an
    # all-predicates engine, so the benchmark only admits present-or-"" values
    # (enforced above via exact string keys). A variant entering the matched
    # branch must keep at least one non-blank workspace_id or #9's WHERE would
    # degenerate to a SQL syntax error.
    if matched and any(str(row.get("workspace_id")) != "" for row in matched) is False:
        raise RuntimeError(
            f"recipe {RECIPE_ID} matched_workato_users must include at least one row with a "
            "non-blank workspace_id (an all-blank batch makes step 9's SQL unexecutable)"
        )


def _require_salesforce_section(sf_section: dict[str, Any]) -> None:
    if sf_section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true: the "
            "step-16 SOQL uses != null conditions that must never be silently dropped"
        )
    schema = sf_section.get("schema")
    if not isinstance(schema, list) or not schema:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare the {SF_SOBJECT} custom "
            "fields (schema-in-seed provisioning via ensure_custom_field)"
        )
    declared = {
        (str(entry.get("sobject") or ""), str(entry.get("field") or ""))
        for entry in schema
        if isinstance(entry, dict)
    }
    missing = [field for field in SF_SCHEMA_FIELDS if (SF_SOBJECT, field) not in declared]
    if missing:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must include {SF_SOBJECT} fields {missing}"
        )
    records = [record for record in sf_section.get("records") or [] if isinstance(record, dict)]
    if not records:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.records must seed at least one live record "
            "(decoys included); omit the section entirely when the SOQL never runs"
        )
    for record in records:
        if not str(record.get("ref") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seed.salesforce record needs an explicit ref: {record}"
            )
        if not isinstance(record.get("fields"), dict) or not record["fields"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed.salesforce record {record.get('ref')!r} is missing fields"
            )


def _salesforce_ref_tokens(seed_section: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    live_ids = [
        str(record.get("id") or "")
        for record in salesforce_snapshot.get("records") or []
        if isinstance(record, dict) and record.get("id")
    ]
    seed_records = [record for record in seed_section.get("records") or [] if isinstance(record, dict)]
    if len(live_ids) != len(seed_records):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed/snapshot record count mismatch: "
            f"{len(seed_records)} seeded vs {len(live_ids)} provisioned"
        )
    refs: dict[str, str] = {}
    for idx, record in enumerate(seed_records):
        live_id = live_ids[idx]
        if not _SF_ID_RE.fullmatch(live_id):
            raise RuntimeError(f"recipe {RECIPE_ID} provisioned record id looks invalid: {live_id!r}")
        refs[f"${str(record.get('ref')).strip().upper()}_ID"] = live_id
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


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("salesforce_live"), dict):
        out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
