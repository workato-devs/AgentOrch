from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_127811469


RECIPE_ID = "127811469"
SEED_TYPE = "recipe_function_unmatched_domain_sf_contact_matcher_variant"
TRACK = "live_salesforce_recipe_function_domain_contact_matching"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
LOOKUP_TABLE_ID = "1492777"
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_SF_ID_RE = re.compile(r"^[a-zA-Z0-9]{15,18}$")


_STRUCTURE_PINS_JSON = r'''
[
 {
  "as": "74feff40",
  "input": {
   "parameters_schema_json": "[{\"name\":\"unmatched_list\",\"type\":\"array\",\"of\":\"object\",\"label\":\"Unmatched list\",\"optional\":true,\"properties\":[{\"control_type\":\"text\",\"label\":\"Domain\",\"name\":\"domain\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Record ID\",\"name\":\"record_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"integer\",\"label\":\"User ID\",\"name\":\"user_id\",\"type\":\"integer\",\"optional\":true,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"text\",\"label\":\"Email\",\"name\":\"email\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Data center\",\"name\":\"data_center\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Account\",\"name\":\"account\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Oem ID\",\"name\":\"oem_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Federated account ID\",\"name\":\"federated_account_id\",\"type\":\"string\",\"optional\":true},{\"name\":\"workspace_id\",\"type\":\"integer\",\"optional\":true,\"control_type\":\"integer\",\"label\":\"Workspace ID\",\"parse_output\":\"integer_conversion\"}]}]",
   "result_schema_json": "[{\"name\":\"matched_list\",\"type\":\"array\",\"of\":\"object\",\"label\":\"Matched list\",\"optional\":true,\"properties\":[{\"control_type\":\"text\",\"label\":\"Domain\",\"name\":\"domain\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Account ID\",\"name\":\"account_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Count contacts\",\"name\":\"count_contacts\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Account name\",\"name\":\"account_name\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"integer\",\"label\":\"Curent arr\",\"parse_output\":\"integer_conversion\",\"name\":\"curent_arr\",\"type\":\"integer\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Current plan\",\"name\":\"current_plan\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"checkbox\",\"label\":\"Active subscription\",\"render_input\":{},\"parse_output\":{},\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Active subscription\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"active_subscription\",\"type\":\"boolean\",\"optional\":true},\"name\":\"active_subscription\",\"type\":\"boolean\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Record ID\",\"name\":\"record_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"User ID\",\"name\":\"user_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Email\",\"name\":\"email\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Data center\",\"name\":\"data_center\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Oem ID\",\"name\":\"oem_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Federated account ID\",\"name\":\"federated_account_id\",\"type\":\"string\",\"optional\":true},{\"name\":\"workspace_id\",\"type\":\"integer\",\"optional\":true,\"control_type\":\"integer\",\"label\":\"Workspace ID\",\"parse_output\":\"integer_conversion\"},{\"name\":\"no_of_account_contacts\",\"type\":\"integer\",\"optional\":true,\"control_type\":\"integer\",\"label\":\"No of account contacts\",\"parse_output\":\"integer_conversion\"}]}]"
  },
  "keyword": "trigger",
  "name": "execute",
  "number": 1,
  "provider": "workato_recipe_function",
  "skip": false
 },
 {
  "as": "8264cace",
  "input": {
   "list_item_schema_json": "[{\"control_type\":\"text\",\"label\":\"Domain\",\"name\":\"domain\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Record ID\",\"name\":\"record_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"integer\",\"label\":\"User ID\",\"name\":\"user_id\",\"type\":\"integer\",\"optional\":true,\"parse_output\":\"integer_conversion\"},{\"control_type\":\"text\",\"label\":\"Email\",\"name\":\"email\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Data center\",\"name\":\"data_center\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Account\",\"name\":\"account\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Oem ID\",\"name\":\"oem_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Federated account ID\",\"name\":\"federated_account_id\",\"type\":\"string\",\"optional\":true},{\"name\":\"workspace_id\",\"type\":\"integer\",\"optional\":true,\"control_type\":\"integer\",\"label\":\"Workspace ID\",\"parse_output\":\"integer_conversion\"}]",
   "list_items": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"74feff40\",\"path\":[\"parameters\", \"unmatched_list\"]}')}",
    "account": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"74feff40\",\"path\":[\"parameters\",\"unmatched_list\",{\"path_element_type\":\"current_item\"},\"account\"]}')",
    "data_center": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"74feff40\",\"path\":[\"parameters\", \"unmatched_list\", {\"path_element_type\": \"current_item\"}, \"data_center\"]}')}",
    "domain": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"74feff40\",\"path\":[\"parameters\",\"unmatched_list\",{\"path_element_type\":\"current_item\"},\"domain\"]}')",
    "email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"74feff40\",\"path\":[\"parameters\", \"unmatched_list\", {\"path_element_type\": \"current_item\"}, \"email\"]}')}",
    "federated_account_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"74feff40\",\"path\":[\"parameters\", \"unmatched_list\", {\"path_element_type\": \"current_item\"}, \"federated_account_id\"]}')}",
    "oem_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"74feff40\",\"path\":[\"parameters\", \"unmatched_list\", {\"path_element_type\": \"current_item\"}, \"oem_id\"]}')}",
    "record_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"74feff40\",\"path\":[\"parameters\", \"unmatched_list\", {\"path_element_type\": \"current_item\"}, \"record_id\"]}')}",
    "user_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"74feff40\",\"path\":[\"parameters\", \"unmatched_list\", {\"path_element_type\": \"current_item\"}, \"user_id\"]}')}",
    "workspace_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"74feff40\",\"path\":[\"parameters\", \"unmatched_list\", {\"path_element_type\": \"current_item\"}, \"workspace_id\"]}')}"
   },
   "name": "Input_list"
  },
  "keyword": "action",
  "name": "declare_list",
  "number": 2,
  "provider": "workato_variable",
  "skip": false
 },
 {
  "as": "70054386",
  "input": {
   "list_name": "input",
   "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"8264cace\",\"path\":[\"list_items\"]}')",
   "primary_index": "record_id"
  },
  "keyword": "action",
  "name": "create_list",
  "number": 3,
  "provider": "workato_smart_list",
  "skip": false
 },
 {
  "as": "598dc941",
  "input": {
   "list_item_schema_json": "[{\"name\":\"Domain\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Domain\"},{\"name\":\"Account_id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Account ID\"},{\"name\":\"current_arr\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Current arr\"},{\"name\":\"current_plan\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Current plan\"},{\"name\":\"account_name\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Account name\"},{\"name\":\"id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"ID\"},{\"name\":\"active_subscription\",\"type\":\"boolean\",\"optional\":true,\"control_type\":\"checkbox\",\"label\":\"Active subscription\",\"render_input\":{},\"parse_output\":{},\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Active subscription\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"active_subscription\",\"type\":\"boolean\",\"optional\":true}}]",
   "name": "Contact_List"
  },
  "keyword": "action",
  "name": "declare_list",
  "number": 4,
  "provider": "workato_variable",
  "skip": false
 },
 {
  "as": "089cd342",
  "input": {
   "lookup_table_id": "1492777"
  },
  "keyword": "action",
  "name": "get_entries",
  "number": 5,
  "provider": "lookup_table",
  "skip": false
 },
 {
  "as": "ef2514c0",
  "input": {
   "list_item_schema_json": "[{\"name\":\"Domain\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Domain\"}]",
   "list_items": {
    "Domain": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"089cd342\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col1\"]}')}",
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"089cd342\",\"path\":[\"entries\"]}')}"
   },
   "name": "free_email_domain"
  },
  "keyword": "action",
  "name": "declare_list",
  "number": 6,
  "provider": "workato_variable",
  "skip": false
 },
 {
  "as": "008ce4d7",
  "input": {
   "list_name": "Free_domains",
   "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"ef2514c0\",\"path\":[\"list_items\"]}')"
  },
  "keyword": "action",
  "name": "create_list",
  "number": 7,
  "provider": "workato_smart_list",
  "skip": false
 },
 {
  "as": "3ea250c1",
  "input": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "output_schema_by": "index",
   "result_schema_json": "[{\"name\":\"domain\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Domain\"}]",
   "sql": "SELECT DISTINCT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"70054386\",\"path\":[\"columns\", \"domain\"]}')} FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"70054386\",\"path\":[\"list_name\"]}')} WHERE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"70054386\",\"path\":[\"columns\", \"domain\"]}')} NOT IN (SELECT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"008ce4d7\",\"path\":[\"columns\", \"Domain\"]}')} from #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"008ce4d7\",\"path\":[\"list_name\"]}')})"
  },
  "keyword": "action",
  "name": "query_list",
  "number": 8,
  "provider": "workato_smart_list",
  "skip": false
 },
 {
  "as": "9b27509b",
  "batch_size": "15",
  "input": {
   "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"3ea250c1\",\"path\":[\"rows\"]}')}"
  },
  "keyword": "foreach",
  "name": null,
  "number": 9,
  "provider": null,
  "repeat_mode": "batch",
  "skip": false,
  "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"3ea250c1\",\"path\":[\"rows\"]}')}"
 },
 {
  "as": "efefd811",
  "input": {
   "variables": {
    "data": {
     "Syntax": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9b27509b\",\"path\":[\"batch\"]}')&.where('domain': /^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$/)&.pluck('domain')&.compact&.uniq&.format_map('Email LIKE \\'?%s?\\'')&.smart_join(\" or \").gsub(/\\?/,\"%\")"
    },
    "schema": "[{\"name\":\"Syntax\",\"type\":\"string\",\"optional\":true,\"label\":\"Syntax\",\"details\":{\"real_name\":\"Syntax\"},\"control_type\":\"text\"}]"
   }
  },
  "keyword": "action",
  "name": "declare_variable",
  "number": 10,
  "provider": "workato_variable",
  "skip": false
 },
 {
  "as": "a363938d",
  "input": {
   "field_list": "AccountId\nAccount$Account ID.Name\nAccount$Account ID.Current_ARR__c\nAccount$Account ID.Current_Plan__c\nEmail\nId\nAccount$Account ID.Active_Subscription__c",
   "limit": "2000",
   "query": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"efefd811\",\"path\":[\"Syntax\"]}')}",
   "sobject_name": "Contact",
   "table_list": "Account"
  },
  "keyword": "action",
  "name": "search_sobjects_soql",
  "number": 11,
  "provider": "salesforce",
  "skip": false
 },
 {
  "as": null,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a363938d\",\"path\":[\"list_size\"]}')}",
     "operand": "not_equals_to",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "keyword": "if",
  "name": null,
  "number": 12,
  "provider": null,
  "skip": false
 },
 {
  "as": "e5047fa7",
  "input": {
   "list_items": {
    "Account_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a363938d\",\"path\":[\"Contact\", {\"path_element_type\": \"current_item\"}, \"AccountId\"]}')}",
    "Domain": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a363938d\",\"path\":[\"Contact\",{\"path_element_type\":\"current_item\"},\"Email\"]}').split(\"@\").last",
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a363938d\",\"path\":[\"Contact\"]}')}",
    "account_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a363938d\",\"path\":[\"Contact\", {\"path_element_type\": \"current_item\"}, \"Account\", \"Name\"]}')}",
    "active_subscription": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a363938d\",\"path\":[\"Contact\", {\"path_element_type\": \"current_item\"}, \"Account\", \"Active_Subscription__c\"]}')}",
    "current_arr": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a363938d\",\"path\":[\"Contact\", {\"path_element_type\": \"current_item\"}, \"Account\", \"Current_ARR__c\"]}')}",
    "current_plan": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a363938d\",\"path\":[\"Contact\", {\"path_element_type\": \"current_item\"}, \"Account\", \"Current_Plan__c\"]}')}",
    "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a363938d\",\"path\":[\"Contact\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}"
   },
   "location": "end",
   "name": "ee758be5-68e3-4a82-922f-6cd7e0ebc2b9:598dc941"
  },
  "keyword": "action",
  "name": "insert_to_list_batch",
  "number": 13,
  "provider": "workato_variable",
  "skip": false
 },
 {
  "as": null,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"598dc941\",\"path\":[\"list_items\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "equals_to",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "keyword": "if",
  "name": null,
  "number": 14,
  "provider": null,
  "skip": false
 },
 {
  "as": "8dcbf652",
  "input": {
   "stop_with_error": "false"
  },
  "keyword": "stop",
  "name": null,
  "number": 15,
  "provider": null,
  "skip": false
 },
 {
  "as": "c71a1bf7",
  "input": {
   "list_name": "contact_list",
   "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"598dc941\",\"path\":[\"list_items\"]}')",
   "primary_index": "Account_id"
  },
  "keyword": "action",
  "name": "create_list",
  "number": 16,
  "provider": "workato_smart_list",
  "skip": false
 },
 {
  "as": "a185c2d5",
  "input": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "output_schema_by": "index",
   "result_schema_json": "[{\"name\":\"domain\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Domain\"},{\"name\":\"account_id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Account ID\"},{\"name\":\"count_contacts\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Count contacts\"},{\"name\":\"account_name\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Account name\"},{\"name\":\"curent_arr\",\"type\":\"integer\",\"optional\":true,\"control_type\":\"integer\",\"label\":\"Curent arr\",\"parse_output\":\"integer_conversion\"},{\"name\":\"current_plan\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Current plan\"}]",
   "sql": "    SELECT \n        #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"c71a1bf7\",\"path\":[\"columns\", \"Domain\"]}')} as contact_domain, \n        #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"c71a1bf7\",\"path\":[\"columns\", \"Account_id\"]}')} as contact_account_id, \n        COUNT(#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"c71a1bf7\",\"path\":[\"columns\", \"id\"]}')}) AS num_contacts\n    FROM \n        #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"c71a1bf7\",\"path\":[\"list_name\"]}')}\n    GROUP BY \n        #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"c71a1bf7\",\"path\":[\"columns\", \"Domain\"]}')}, \n        #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"c71a1bf7\",\"path\":[\"columns\", \"Account_id\"]}')}\nORDER BY num_contacts DESC"
  },
  "keyword": "action",
  "name": "query_list",
  "number": 17,
  "provider": "workato_smart_list",
  "skip": false
 },
 {
  "as": "7919520c",
  "input": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "output_schema_by": "index",
   "result_schema_json": "[{\"control_type\":\"text\",\"label\":\"Domain\",\"name\":\"domain\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Account ID\",\"name\":\"account_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Count contacts\",\"name\":\"count_contacts\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Account name\",\"name\":\"account_name\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"integer\",\"label\":\"Curent arr\",\"parse_output\":\"integer_conversion\",\"name\":\"curent_arr\",\"type\":\"integer\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Current plan\",\"name\":\"current_plan\",\"type\":\"string\",\"optional\":true},{\"name\":\"active_subscription\",\"type\":\"boolean\",\"optional\":true,\"control_type\":\"checkbox\",\"label\":\"Active subscription\",\"render_input\":{},\"parse_output\":{},\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Active subscription\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"active_subscription\",\"type\":\"boolean\",\"optional\":true}},{\"control_type\":\"text\",\"label\":\"Record ID\",\"name\":\"record_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"User ID\",\"name\":\"user_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Email\",\"name\":\"email\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Data center\",\"name\":\"data_center\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Oem ID\",\"name\":\"oem_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Federated account ID\",\"name\":\"federated_account_id\",\"type\":\"string\",\"optional\":true},{\"name\":\"workspace_id\",\"type\":\"integer\",\"optional\":true,\"control_type\":\"integer\",\"label\":\"Workspace ID\",\"parse_output\":\"integer_conversion\"},{\"name\":\"no_of_account_contacts\",\"type\":\"integer\",\"optional\":true,\"control_type\":\"integer\",\"label\":\"No of account contacts\",\"parse_output\":\"integer_conversion\"}]",
   "sql": "WITH contact_counts AS (\n    SELECT \n        #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"c71a1bf7\",\"path\":[\"columns\", \"Domain\"]}')} as contact_domain, \n        #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"c71a1bf7\",\"path\":[\"columns\", \"Account_id\"]}')} as contact_account_id, \n        COUNT(#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"c71a1bf7\",\"path\":[\"columns\", \"id\"]}')}) AS num_contacts,\n        #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"c71a1bf7\",\"path\":[\"columns\", \"account_name\"]}')} as account_name,\n        #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"c71a1bf7\",\"path\":[\"columns\", \"current_arr\"]}')} as contact_current_arr,\n        #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"c71a1bf7\",\"path\":[\"columns\", \"current_plan\"]}')} as contact_current_plan,\n\t\tSUM(CASE WHEN #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"c71a1bf7\",\"path\":[\"columns\", \"active_subscription\"]}')} = 'true' THEN 1 ELSE 0 END) AS contact_active_subs\n    FROM \n        #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"c71a1bf7\",\"path\":[\"list_name\"]}')}\n    GROUP BY \n        #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"c71a1bf7\",\"path\":[\"columns\", \"Domain\"]}')}, \n        #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"c71a1bf7\",\"path\":[\"columns\", \"Account_id\"]}')}\n),\nmax_counts AS (\n    SELECT \n        contact_domain,\n        MAX(num_contacts) as max_contacts\n    FROM \n        contact_counts\n  WHERE \n    (contact_active_subs = 0 AND num_contacts = (\n        SELECT MAX(num_contacts) FROM contact_counts)) OR\n    (contact_active_subs = 0 AND num_contacts = (\n        SELECT MAX(num_contacts) FROM contact_counts )) OR \n     (contact_active_subs > 0) \n       \n    GROUP BY \n        contact_domain\n)\nSELECT \n    cc.contact_domain,\n    cc.contact_account_id,\n    cc.num_contacts,\n    cc.account_name,\n    cc.contact_current_arr,\n    cc.contact_current_plan,\n    cc.contact_active_subs,\n    input.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"70054386\",\"path\":[\"columns\", \"record_id\"]}')},\n    input.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"70054386\",\"path\":[\"columns\", \"user_id\"]}')},\n    input.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"70054386\",\"path\":[\"columns\", \"email\"]}')},\n    input.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"70054386\",\"path\":[\"columns\", \"data_center\"]}')},\n    input.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"70054386\",\"path\":[\"columns\", \"oem_id\"]}')},\n    input.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"70054386\",\"path\":[\"columns\", \"federated_account_id\"]}')},\n    input.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"70054386\",\"path\":[\"columns\", \"workspace_id\"]}')},\n    mc.max_contacts\nFROM \n    contact_counts cc\nJOIN #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"70054386\",\"path\":[\"list_name\"]}')} as input\nON cc.contact_domain = input.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"70054386\",\"path\":[\"columns\", \"domain\"]}')}\nJOIN \n    max_counts mc\nON \n    cc.contact_domain = mc.contact_domain\n    AND cc.num_contacts = mc.max_contacts\nWHERE ((input.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"70054386\",\"path\":[\"columns\", \"oem_id\"]}')} != \"\" AND cc.account_name LIKE '% - Embedded%')OR (input.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"70054386\",\"path\":[\"columns\", \"oem_id\"]}')} = \"\" AND cc.account_name NOT LIKE '% - Embedded%')) \nAND cc.contact_account_id != \"\" AND cc.num_contacts > 1 AND cc.contact_domain NOT IN (SELECT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"008ce4d7\",\"path\":[\"columns\", \"Domain\"]}')} FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"008ce4d7\",\"path\":[\"list_name\"]}')})\nORDER BY cc.num_contacts DESC"
  },
  "keyword": "action",
  "name": "query_list",
  "number": 18,
  "provider": "workato_smart_list",
  "skip": false
 },
 {
  "as": "c9df84a1",
  "input": {
   "result": {
    "matched_list": {
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"7919520c\",\"path\":[\"rows\"]}')}",
     "account_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"7919520c\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"account_id\"]}')}",
     "account_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"7919520c\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"account_name\"]}')}",
     "active_subscription": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"7919520c\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"active_subscription\"]}').present?\n(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"7919520c\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"active_subscription\"]}') > 0).is_true?\nelse \nfalse\nend",
     "count_contacts": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"7919520c\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"count_contacts\"]}')}",
     "curent_arr": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"7919520c\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"curent_arr\"]}')}",
     "current_plan": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"7919520c\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"current_plan\"]}')}",
     "data_center": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"7919520c\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"data_center\"]}')}",
     "domain": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"7919520c\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"domain\"]}')}",
     "email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"7919520c\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"email\"]}')}",
     "federated_account_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"7919520c\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"federated_account_id\"]}')}",
     "no_of_account_contacts": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"7919520c\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"no_of_account_contacts\"]}')}",
     "oem_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"7919520c\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"oem_id\"]}')}",
     "record_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"7919520c\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"record_id\"]}')}",
     "user_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"7919520c\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"user_id\"]}')}",
     "workspace_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"7919520c\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"workspace_id\"]}')}"
    }
   }
  },
  "keyword": "action",
  "name": "return_result",
  "number": 19,
  "provider": "workato_recipe_function",
  "skip": false
 }
]
'''
STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_list",
    "workato_smart_list.create_list",
    "lookup_table.get_entries",
    "workato_smart_list.query_list",
    "workato_runtime.declare_variable",
    "salesforce.search_records",
    "workato_runtime.insert_to_list_batch",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.get_entries",
    "salesforce.search_records",
    "workato_recipe_function.return_result",
]
UNMATCHED_ROW_KEYS = [
    "domain",
    "record_id",
    "user_id",
    "email",
    "data_center",
    "account",
    "oem_id",
    "federated_account_id",
    "workspace_id",
]
REQUIRED_ACCOUNT_SCHEMA: dict[str, str] = {
    "Current_ARR__c": "Text",
    "Current_Plan__c": "Text",
    "Active_Subscription__c": "Checkbox",
}


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
        pin["batch_size"] = node.get("batch_size")
        pin["source"] = node.get("source")
    out = [pin]
    for child in node.get("block") or []:
        if isinstance(child, dict):
            out.extend(_structure(child))
    return out


def validate_127811469(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actual = _structure(raw)
    if len(actual) != len(STRUCTURE_PINS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} node count changed: "
            f"{len(actual)} != {len(STRUCTURE_PINS)}"
        )
    for idx, (got, expected) in enumerate(zip(actual, STRUCTURE_PINS)):
        if got != expected:
            raise RuntimeError(
                f"recipe {RECIPE_ID} node {idx} "
                f"(step {expected.get('number')}) changed:\n"
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


def seed_127811469(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_127811469(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"salesforce", "lookup_table"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    sf_section = seed_in.get("salesforce")
    _require_salesforce_section(sf_section)
    lookup_section = seed_in.get("lookup_table")
    _require_lookup_section(lookup_section)
    expect = data.get("expect")
    _require_expect_shape(expect)
    provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": sf_section})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    refs = _salesforce_ref_tokens(sf_section, provision)
    leftover_trigger = sorted(set(_TOKEN_RE.findall(json.dumps(trigger))))
    if leftover_trigger:
        # The trigger carries workspace metadata only; live SF ids never
        # belong in it for this recipe.
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must not carry seed tokens: {leftover_trigger}"
        )
    resolved_expect = _replace_value(deepcopy(expect), refs)
    _require_no_tokens(resolved_expect, "expect")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": resolved_expect,
        "raw_validation": validation,
        "lookup_table": deepcopy(lookup_section),
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": refs,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_127811469(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_127811469(raw)
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    cleanup_response: dict[str, Any] | None = None
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    try:
        details["initial_snapshot"] = _snapshot(ctx)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx)
    finally:
        cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
        details["cleanup_response"] = cleanup_response
    if not cleanup_response.get("ok"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} Salesforce cleanup left live records: {cleanup_response}"
        )
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_127811469(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict) or sorted(parameters.keys()) != ["unmatched_list"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.parameters must carry exactly unmatched_list"
        )
    rows = parameters.get("unmatched_list")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"recipe {RECIPE_ID} unmatched_list must be a non-empty list")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(UNMATCHED_ROW_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} unmatched_list[{idx}] must carry exactly "
                f"{UNMATCHED_ROW_KEYS}; got {sorted(row.keys()) if isinstance(row, dict) else row}"
            )
        for key in ("user_id", "workspace_id"):
            if isinstance(row.get(key), bool) or not isinstance(row.get(key), int):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} unmatched_list[{idx}].{key} must be an integer"
                )
        for key in ("domain", "record_id", "email"):
            if not str(row.get(key) or "").strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} unmatched_list[{idx}].{key} must be a non-empty string"
                )
        for key in ("data_center", "account", "oem_id", "federated_account_id"):
            if not isinstance(row.get(key), str):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} unmatched_list[{idx}].{key} must be a string "
                    "(empty string is a valid explicit value)"
                )


def _require_salesforce_section(sf_section: Any) -> None:
    if not isinstance(sf_section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce")
    if sf_section.get("relationship_expansion") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.relationship_expansion must be true "
            "(the SOQL walks Contact.Account.* relationship fields)"
        )
    if sf_section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true "
            "(unsupported SOQL conditions must raise, never silently drop)"
        )
    schema = sf_section.get("schema")
    if not isinstance(schema, list) or not schema:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare the Account custom "
            "fields (schema-in-seed provisioning via ensure_custom_field)"
        )
    declared = {
        (str(entry.get("sobject") or ""), str(entry.get("field") or "")): str(entry.get("sf_type") or "")
        for entry in schema
        if isinstance(entry, dict)
    }
    for field, sf_type in REQUIRED_ACCOUNT_SCHEMA.items():
        if declared.get(("Account", field)) != sf_type:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed.salesforce.schema must declare Account.{field} "
                f"as {sf_type}"
            )
    records = sf_section.get("records")
    if not isinstance(records, list):
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records must be a list")
    account_refs: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records entries must be objects")
        sobject = str(record.get("sobject") or "")
        ref = str(record.get("ref") or "").strip()
        fields = record.get("fields")
        if sobject not in {"Account", "Contact"}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed.salesforce.records only seeds Account/Contact; got {sobject!r}"
            )
        if not ref or not isinstance(fields, dict):
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded {sobject} record needs an explicit ref and fields"
            )
        if sobject == "Account":
            if not str(fields.get("Name") or "").strip():
                raise RuntimeError(f"recipe {RECIPE_ID} seeded Account requires an explicit Name")
            for field in REQUIRED_ACCOUNT_SCHEMA:
                if field not in fields:
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} seeded Account requires explicit {field}"
                    )
            if not isinstance(fields.get("Active_Subscription__c"), bool):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} seeded Account.Active_Subscription__c must be a boolean"
                )
            account_refs.add(ref)
        else:
            for key in ("LastName", "Email"):
                if not str(fields.get(key) or "").strip():
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} seeded Contact requires explicit {key}"
                    )
            account_token = str(fields.get("AccountId") or "")
            expected_tokens = {f"${account_ref.upper()}_ID" for account_ref in account_refs}
            if account_token not in expected_tokens:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} seeded Contact.AccountId must reference an earlier "
                    f"seeded Account ref token; got {account_token!r}"
                )


def _require_lookup_section(lookup_section: Any) -> None:
    if not isinstance(lookup_section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.lookup_table (Workato-internal mock)")
    tables = lookup_section.get("tables")
    if not isinstance(tables, dict) or sorted(tables.keys()) != [LOOKUP_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must declare exactly table {LOOKUP_TABLE_ID}"
        )
    rows = tables[LOOKUP_TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} Freemail providers table {LOOKUP_TABLE_ID} must be a non-empty list"
        )
    for row in rows:
        if not isinstance(row, dict) or not str(row.get("col1") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} Freemail providers rows must carry a non-empty col1 domain"
            )


def _require_expect_shape(expect: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    for key in ("tools", "executed_action_count", "stopped"):
        if key not in expect:
            raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required key {key!r}")
    if not isinstance(expect.get("stopped"), bool):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.stopped must be a boolean")
    if expect["stopped"]:
        if expect.get("stop_step_number") != 15:
            raise RuntimeError(
                f"recipe {RECIPE_ID} stop variants must pin stop_step_number 15 "
                "(the only stop in the raw recipe)"
            )
        if "matched_list" in expect:
            raise RuntimeError(
                f"recipe {RECIPE_ID} stop variants never reach return_result; "
                "drop expect.matched_list"
            )
    else:
        if not isinstance(expect.get("matched_list"), list) or not expect["matched_list"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} non-stop variants must pin the exact non-empty "
                "expect.matched_list returned by step 19"
            )


def _salesforce_ref_tokens(seed_section: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    live_records = [
        record
        for record in salesforce_snapshot.get("records") or []
        if isinstance(record, dict) and record.get("id") and not record.get("read_only")
    ]
    seed_records = [record for record in seed_section.get("records") or [] if isinstance(record, dict)]
    if len(live_records) != len(seed_records):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed/snapshot record count mismatch: "
            f"{len(seed_records)} seeded vs {len(live_records)} provisioned"
        )
    refs: dict[str, str] = {}
    for idx, record in enumerate(seed_records):
        ref = str(record.get("ref") or "").strip()
        live_id = str(live_records[idx].get("id") or "")
        if not _SF_ID_RE.fullmatch(live_id):
            raise RuntimeError(f"recipe {RECIPE_ID} provisioned record id looks invalid: {live_id!r}")
        if ref:
            refs[f"${ref.upper()}_ID"] = live_id
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
    out: dict[str, Any] = {}
    out.update(ctx.tools.call("harness.lookup_table.snapshot", {}))
    out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
