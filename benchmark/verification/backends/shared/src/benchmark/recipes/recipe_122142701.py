from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_122142701


RECIPE_ID = "122142701"
SEED_TYPE = "salesforce_account_handover_outbound_message_variant"
TRACK = "live_salesforce_account_handover_enrichment"
TRIGGER_PROVIDER = "salesforce"
TRIGGER_NAME = "new_outbound_message"
TRIGGER_AS = "b8b674f7"
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_SF_ID_RE = re.compile(r"^[a-zA-Z0-9]{15,18}$")


_STRUCTURE_PINS_JSON = r'''
[
 {
  "as": "b8b674f7",
  "input": {
   "field_list": "Account__c\nRecordTypeId",
   "outbound_message_name": "New Account Owner AccountHandover",
   "sobject_name": "Account_Handover__c"
  },
  "keyword": "trigger",
  "name": "new_outbound_message",
  "number": 1,
  "provider": "salesforce",
  "skip": false
 },
 {
  "as": "1e0cdf8d",
  "input": {
   "Id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"b8b674f7\",\"path\":[\"sObject\", \"Id\"]}')}",
   "field_list": "Id\nAccount__c\nAccount__r$Account.At_Risk_Status__c\nAccount__r$Account.Website\nAccount__r$Account.Recipes_Consumed_vs_Contracted__c\nAccount__r$Account.Task_Trend__c\nAccount__r$Account.OwnerId\nAccount__r$Account.Current_ARR__c\nAccount__r$Account.Total_Account_ARR__c\nAccount__r$Account.Total_Account_ARR_USD__c",
   "limit": "150",
   "sobject_name": "Account_Handover__c",
   "table_list": "Account"
  },
  "keyword": "action",
  "name": "search_sobjects",
  "number": 2,
  "provider": "salesforce",
  "skip": false
 },
 {
  "as": "a04d55f2",
  "input": {
   "limit": "2",
   "output_schema": "[{\"properties\":[{\"control_type\":\"text\",\"label\":\"Type\",\"type\":\"string\",\"name\":\"type\"},{\"control_type\":\"text\",\"label\":\"URL\",\"type\":\"string\",\"name\":\"url\"}],\"label\":\"Attributes\",\"type\":\"object\",\"name\":\"attributes\"},{\"control_type\":\"text\",\"label\":\"Champion c\",\"type\":\"string\",\"name\":\"Champion__c\"},{\"control_type\":\"text\",\"label\":\"Economic buyer c\",\"type\":\"string\",\"name\":\"Economic_Buyer__c\"},{\"control_type\":\"text\",\"label\":\"ID\",\"type\":\"string\",\"name\":\"Id\"},{\"type\":\"date_time\",\"name\":\"CloseDate\",\"control_type\":\"date\",\"parse_output\":\"parse_iso8601_date\",\"render_input\":\"render_iso8601_date\",\"label\":\"Close Date\",\"custom\":false},{\"control_type\":\"text\",\"label\":\"Type\",\"type\":\"string\",\"name\":\"Type\"},{\"control_type\":\"text\",\"label\":\"Stage name\",\"type\":\"string\",\"name\":\"StageName\"}]",
   "query": "SELECT Champion__c,Economic_Buyer__c,Id,CloseDate,Type,StageName,FirstValue_CS_Task__c,FirstValue_CS_Task__r.fv_First_Value_Plan_URL__c FROM Opportunity WHERE AccountId = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1e0cdf8d\",\"path\":[\"Account_Handover__c\", {\"path_element_type\": \"current_item\"}, \"Account__c\"]}')}' AND (StageName = 'Closed Won' OR StageName LIKE '%S5%') ORDER By CloseDate DESC"
  },
  "keyword": "action",
  "name": "search_sobjects_soql_v2",
  "number": 3,
  "provider": "salesforce",
  "skip": false
 },
 {
  "as": "c9ce7205",
  "input": {
   "list_item_schema_json": "[{\"control_type\":\"text\",\"label\":\"Champion c\",\"type\":\"string\",\"name\":\"Champion__c\"},{\"control_type\":\"text\",\"label\":\"Economic buyer c\",\"type\":\"string\",\"name\":\"Economic_Buyer__c\"},{\"control_type\":\"text\",\"label\":\"ID\",\"type\":\"string\",\"name\":\"Id\"},{\"control_type\":\"date\",\"label\":\"Close Date\",\"render_input\":\"render_iso8601_date\",\"parse_output\":\"parse_iso8601_date\",\"type\":\"date_time\",\"name\":\"CloseDate\",\"custom\":false},{\"control_type\":\"text\",\"label\":\"Type\",\"type\":\"string\",\"name\":\"Type\"},{\"control_type\":\"text\",\"label\":\"Stage name\",\"type\":\"string\",\"name\":\"StageName\"}]",
   "list_items": {
    "Champion__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a04d55f2\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Champion__c\"]}')}",
    "CloseDate": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a04d55f2\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"CloseDate\"]}')}",
    "Economic_Buyer__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a04d55f2\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Economic_Buyer__c\"]}')}",
    "Id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a04d55f2\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}",
    "StageName": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a04d55f2\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"StageName\"]}')}",
    "Type": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a04d55f2\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Type\"]}')}",
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a04d55f2\",\"path\":[\"records\"]}')}"
   },
   "name": "List of Opportunity"
  },
  "keyword": "action",
  "name": "declare_list",
  "number": 4,
  "provider": "workato_variable",
  "skip": false
 },
 {
  "as": "0593a073",
  "input": {
   "list_name": "opportunity List",
   "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c9ce7205\",\"path\":[\"list_items\"]}')",
   "primary_index": "Id"
  },
  "keyword": "action",
  "name": "create_list",
  "number": 5,
  "provider": "workato_smart_list",
  "skip": false
 },
 {
  "as": "64e204e0",
  "input": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "output_schema_by": "index",
   "result_schema_json": "[{\"name\":\"Opportunity_Id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Opportunity ID\"}]",
   "sql": "SELECT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"0593a073\",\"path\":[\"columns\", \"Id\"]}')} FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"0593a073\",\"path\":[\"list_name\"]}')}\nWHERE (#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"0593a073\",\"path\":[\"columns\", \"StageName\"]}')} = 'Closed Won' OR #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"0593a073\",\"path\":[\"columns\", \"StageName\"]}')} LIKE '%S5%') AND #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"0593a073\",\"path\":[\"columns\", \"Type\"]}')} NOT LIKE '%Renewal%'\nORDER BY #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"0593a073\",\"path\":[\"columns\", \"CloseDate\"]}')} DESC\nLIMIT 1"
  },
  "keyword": "action",
  "name": "query_list",
  "number": 6,
  "provider": "workato_smart_list",
  "skip": false
 },
 {
  "as": "392cd281",
  "input": {
   "limit": "3",
   "output_schema": "[{\"properties\":[{\"control_type\":\"text\",\"label\":\"Type\",\"type\":\"string\",\"name\":\"type\"},{\"control_type\":\"text\",\"label\":\"URL\",\"type\":\"string\",\"name\":\"url\"}],\"label\":\"Attributes\",\"type\":\"object\",\"name\":\"attributes\"},{\"control_type\":\"text\",\"label\":\"Contact ID\",\"type\":\"string\",\"name\":\"ContactId\"},{\"properties\":[{\"properties\":[{\"control_type\":\"text\",\"label\":\"Type\",\"type\":\"string\",\"name\":\"type\"},{\"control_type\":\"text\",\"label\":\"URL\",\"type\":\"string\",\"name\":\"url\"}],\"label\":\"Attributes\",\"type\":\"object\",\"name\":\"attributes\"},{\"control_type\":\"text\",\"label\":\"Name\",\"type\":\"string\",\"name\":\"Name\"}],\"label\":\"Contact\",\"type\":\"object\",\"name\":\"Contact\"},{\"control_type\":\"text\",\"label\":\"Role\",\"type\":\"string\",\"name\":\"Role\"}]",
   "query": "SELECT ContactId,Contact.Name,Role FROM OpportunityContactRole WHERE Opportunity.AccountId = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1e0cdf8d\",\"path\":[\"Account_Handover__c\", {\"path_element_type\": \"current_item\"}, \"Account__c\"]}')}' AND (NOT Role LIKE '%Economic Buyer%') AND  (NOT Role LIKE '%Champion%') "
  },
  "keyword": "action",
  "name": "search_sobjects_soql_v2",
  "number": 7,
  "provider": "salesforce",
  "skip": false
 },
 {
  "as": "71584cce",
  "input": {
   "list_item_schema_json": "[{\"control_type\":\"text\",\"label\":\"Contact ID\",\"type\":\"string\",\"name\":\"ContactId\"},{\"control_type\":\"text\",\"label\":\"Name\",\"type\":\"string\",\"name\":\"Name\"},{\"control_type\":\"text\",\"label\":\"Role\",\"type\":\"string\",\"name\":\"Role\"},{\"name\":\"formated_contact\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Formated contact\"}]",
   "list_items": {
    "ContactId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"392cd281\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"ContactId\"]}')}",
    "Name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"392cd281\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Contact\", \"Name\"]}')}",
    "Role": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"392cd281\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Role\"]}')}",
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"392cd281\",\"path\":[\"records\"]}')}",
    "formated_contact": "<li><a href='#{_dp('{\"pill_type\":\"account_property\",\"property_name\":\"Salesforce Base URL\"}')}#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"392cd281\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"ContactId\"]}')}'>#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"392cd281\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Contact\", \"Name\"]}')}</a> (#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"392cd281\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Role\"]}')})</li>"
   },
   "name": "List of Opportunity Contacts"
  },
  "keyword": "action",
  "name": "declare_list",
  "number": 8,
  "provider": "workato_variable",
  "skip": false
 },
 {
  "as": "dad0358f",
  "input": {
   "message": "=\"<ul>#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"71584cce\",\"path\":[\"list_items\"]}').pluck('formated_contact').uniq.compact.smart_join(\"\")}</ul>\"",
   "user_logs_enabled": "false"
  },
  "keyword": "action",
  "name": "log_message",
  "number": 9,
  "provider": "logger",
  "skip": false
 },
 {
  "as": "a120169b",
  "input": {
   "limit": "150",
   "output_schema": "[{\"properties\":[{\"control_type\":\"text\",\"label\":\"Type\",\"type\":\"string\",\"name\":\"type\"},{\"control_type\":\"text\",\"label\":\"URL\",\"type\":\"string\",\"name\":\"url\"}],\"label\":\"Attributes\",\"type\":\"object\",\"name\":\"attributes\"},{\"control_type\":\"text\",\"label\":\"ID\",\"type\":\"string\",\"name\":\"Id\"},{\"control_type\":\"text\",\"label\":\"Account ID\",\"type\":\"string\",\"name\":\"AccountId\"},{\"control_type\":\"text\",\"label\":\"Status\",\"type\":\"string\",\"name\":\"Status\"}]",
   "query": "SELECT Id,AccountId,Status FROM ServiceContract WHERE Status = 'Active' AND AccountId = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1e0cdf8d\",\"path\":[\"Account_Handover__c\", {\"path_element_type\": \"current_item\"}, \"Account__c\"]}')}'"
  },
  "keyword": "action",
  "name": "search_sobjects_soql_v2",
  "number": 10,
  "provider": "salesforce",
  "skip": false
 },
 {
  "as": "878aa19f",
  "input": {
   "message": "=\"'#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1e0cdf8d\",\"path\":[\"Account_Handover__c\",{\"path_element_type\":\"current_item\"},\"Account__c\"]}')}'#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a04d55f2\",\"path\":[\"records\",{\"path_element_type\":\"size\"}]}') > 0 ? (\",#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a04d55f2\",\"path\":[\"records\"]}').pluck('Id').format_map('\\'%s\\'').smart_join(\",\")}\") : \"\"}#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a120169b\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"Id\"]}').present? ? (\",'#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a120169b\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"Id\"]}')}'\") : \"\"}\"",
   "user_logs_enabled": "false"
  },
  "keyword": "action",
  "name": "log_message",
  "number": 11,
  "provider": "logger",
  "skip": false
 },
 {
  "as": "bf92cca6",
  "input": {
   "message": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c9ce7205\",\"path\":[\"list_items\"]}').pluck('Id').uniq.format_map('\\'%s\\'').smart_join(\",\")",
   "user_logs_enabled": "false"
  },
  "keyword": "action",
  "name": "log_message",
  "number": 12,
  "provider": "logger",
  "skip": false
 },
 {
  "as": "52493c00",
  "input": {
   "limit": "5",
   "output_schema": "[{\"properties\":[{\"control_type\":\"text\",\"label\":\"Type\",\"type\":\"string\",\"name\":\"type\"},{\"control_type\":\"text\",\"label\":\"URL\",\"type\":\"string\",\"name\":\"url\"}],\"label\":\"Attributes\",\"type\":\"object\",\"name\":\"attributes\"},{\"control_type\":\"text\",\"label\":\"First value CS task c\",\"type\":\"string\",\"name\":\"FirstValue_CS_Task__c\"},{\"properties\":[{\"properties\":[{\"control_type\":\"text\",\"label\":\"Type\",\"type\":\"string\",\"name\":\"type\"},{\"control_type\":\"text\",\"label\":\"URL\",\"type\":\"string\",\"name\":\"url\"}],\"label\":\"Attributes\",\"type\":\"object\",\"name\":\"attributes\"},{\"control_type\":\"text\",\"label\":\"Fv first value plan URL c\",\"type\":\"string\",\"name\":\"fv_First_Value_Plan_URL__c\"}],\"label\":\"First value CS task r\",\"type\":\"object\",\"name\":\"FirstValue_CS_Task__r\"}]",
   "query": "SELECT FirstValue_CS_Task__c,FirstValue_CS_Task__r.fv_First_Value_Plan_URL__c FROM Opportunity WHERE FirstValue_CS_Task__c != null AND Id IN (#{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"bf92cca6\",\"path\":[\"message\"]}')})"
  },
  "keyword": "action",
  "name": "search_sobjects_soql_v2",
  "number": 13,
  "provider": "salesforce",
  "skip": false
 },
 {
  "as": "5971dce0",
  "input": {
   "list_item_schema_json": "[{\"name\":\"first_value_plan_url\",\"type\":\"string\",\"optional\":true,\"label\":\"First Value Plan URL\",\"control_type\":\"text\"}]",
   "list_items": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"52493c00\",\"path\":[\"records\"]}')}",
    "first_value_plan_url": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"52493c00\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"FirstValue_CS_Task__r\", \"fv_First_Value_Plan_URL__c\"]}')}"
   },
   "name": "CS Task First Value Plan"
  },
  "keyword": "action",
  "name": "declare_list",
  "number": 14,
  "provider": "workato_variable",
  "skip": false
 },
 {
  "as": "2e38d9ca",
  "input": {
   "field_list": "Id\nLinkedEntityId\nContentDocumentId",
   "limit": "150",
   "query": "LinkedEntityId IN (#{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"878aa19f\",\"path\":[\"message\"]}')})",
   "sobject_name": "ContentDocumentLink"
  },
  "keyword": "action",
  "name": "search_sobjects_soql",
  "number": 15,
  "provider": "salesforce",
  "skip": false
 },
 {
  "as": null,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2e38d9ca\",\"path\":[\"ContentDocumentLink\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "not_equals_to",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "keyword": "if",
  "name": null,
  "number": 16,
  "provider": null,
  "skip": false
 },
 {
  "as": "44a990b6",
  "batch_size": null,
  "input": {
   "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2e38d9ca\",\"path\":[\"ContentDocumentLink\"]}')}"
  },
  "keyword": "foreach",
  "name": null,
  "number": 17,
  "provider": null,
  "repeat_mode": "simple",
  "skip": false,
  "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2e38d9ca\",\"path\":[\"ContentDocumentLink\"]}')}"
 },
 {
  "as": null,
  "input": {},
  "keyword": "try",
  "name": null,
  "number": 18,
  "provider": null,
  "skip": false
 },
 {
  "as": "ec93084d",
  "input": {
   "ContentDocumentId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"44a990b6\",\"path\":[\"ContentDocumentId\"]}')}",
   "LinkedEntityId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"b8b674f7\",\"path\":[\"Id\"]}')}",
   "ShareType": "V",
   "Visibility": "AllUsers",
   "sobject_name": "ContentDocumentLink"
  },
  "keyword": "action",
  "name": "create_custom_object",
  "number": 19,
  "provider": "salesforce",
  "skip": false
 },
 {
  "as": "1f865b0e",
  "input": {
   "max_retry_count": "0",
   "retry_interval": "2"
  },
  "keyword": "catch",
  "name": null,
  "number": 20,
  "provider": null,
  "skip": false
 },
 {
  "as": "dd693c70",
  "input": {
   "Account_Health__c": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1e0cdf8d\",\"path\":[\"Account_Handover__c\",{\"path_element_type\":\"current_item\"},\"Account__r\",\"At_Risk_Status__c\"]}').presence or skip",
   "Account_Owner__c": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1e0cdf8d\",\"path\":[\"Account_Handover__c\",{\"path_element_type\":\"current_item\"},\"Account__r\",\"OwnerId\"]}').presence or skip",
   "Champion__c": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a04d55f2\",\"path\":[\"records\"]}')&.pluck('Champion__c')&.compact&.uniq&.first).presence or skip",
   "Economic_Buyer__c": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a04d55f2\",\"path\":[\"records\"]}')&.pluck('Economic_Buyer__c')&.compact&.uniq&.first).presence or skip",
   "First_Value_Plan_URL__c": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"5971dce0\",\"path\":[\"list_items\",{\"path_element_type\":\"size\"}]}') > 0\n_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"5971dce0\",\"path\":[\"list_items\"]}').pluck('first_value_plan_url').compact.uniq.smart_join(\"\\n\")\nelse\nskip\nend",
   "Recipes_Consumed_vs_Contracted__c": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1e0cdf8d\",\"path\":[\"Account_Handover__c\",{\"path_element_type\":\"current_item\"},\"Account__r\",\"Recipes_Consumed_vs_Contracted__c\"]}').presence or skip",
   "Related_Opportunity_Contacts__c": "=_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"dad0358f\",\"path\":[\"message\"]}').presence or skip",
   "Task_Trend__c": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1e0cdf8d\",\"path\":[\"Account_Handover__c\",{\"path_element_type\":\"current_item\"},\"Account__r\",\"Task_Trend__c\"]}').presence or skip",
   "Total_ARR__c": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1e0cdf8d\",\"path\":[\"Account_Handover__c\",{\"path_element_type\":\"current_item\"},\"Account__r\",\"Total_Account_ARR_USD__c\"]}').presence or skip",
   "Website__c": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1e0cdf8d\",\"path\":[\"Account_Handover__c\",{\"path_element_type\":\"current_item\"},\"Account__r\",\"Website\"]}').presence or skip",
   "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"b8b674f7\",\"path\":[\"sObject\", \"Id\"]}')}",
   "sobject_name": "Account_Handover__c"
  },
  "keyword": "action",
  "name": "update_sobject",
  "number": 21,
  "provider": "salesforce",
  "skip": false
 }
]
'''
STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_runtime.declare_list",
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
    "workato_runtime.log_message",
    "salesforce.create_record",
    "salesforce.update_record",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "salesforce.create_record",
    "salesforce.update_record",
]
REQUIRED_ACCOUNT_SCHEMA: dict[str, str] = {
    "At_Risk_Status__c": "Text",
    "Recipes_Consumed_vs_Contracted__c": "Text",
    "Task_Trend__c": "Text",
    "Current_ARR__c": "Number",
    "Total_Account_ARR__c": "Number",
    "Total_Account_ARR_USD__c": "Number",
}
REQUIRED_ACCOUNT_SEED_KEYS = (
    "Name",
    "OwnerId",
    "Website",
    "At_Risk_Status__c",
    "Recipes_Consumed_vs_Contracted__c",
    "Task_Trend__c",
    "Total_Account_ARR_USD__c",
)
UPDATE_FIELD_KEYS = (
    "Account_Health__c",
    "Account_Owner__c",
    "Champion__c",
    "Economic_Buyer__c",
    "First_Value_Plan_URL__c",
    "Recipes_Consumed_vs_Contracted__c",
    "Related_Opportunity_Contacts__c",
    "Task_Trend__c",
    "Total_ARR__c",
    "Website__c",
)
CREATE_STEP_AS = "ec93084d"
SEED_SECTIONS = {"account_properties", "salesforce", "salesforce_phase2"}


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


def validate_122142701(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger 'as' changed: {raw.get('as')!r}")
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


def seed_122142701(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_122142701(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - SEED_SECTIONS)
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    _require_account_properties(seed_in.get("account_properties"))
    _require_salesforce_section(seed_in.get("salesforce"))
    _require_phase2_section(seed_in.get("salesforce_phase2"), seed_in.get("salesforce"))
    expect = data.get("expect")
    _require_expect_shape(expect, seed_in, data)
    state, snapshot, refs = _provision_salesforce(ctx, seed_in)
    resolved_trigger = _replace_value(deepcopy(trigger), refs)
    _require_no_tokens(resolved_trigger, "trigger_input")
    resolved_expect = _replace_value(deepcopy(expect), refs)
    _require_no_tokens(resolved_expect, "expect")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": resolved_trigger,
        "track": data.get("track"),
        "expect": resolved_expect,
        "raw_validation": validation,
        "account_properties": deepcopy(seed_in["account_properties"]),
        "salesforce_live": state,
        "salesforce_seed_snapshot": snapshot,
        "salesforce_ref_tokens": refs,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_122142701(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_122142701(raw)
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    if not isinstance(seed.get("account_properties"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing account_properties")
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing resolved expect block")
    cleanup_response: dict[str, Any] | None = None
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect"),
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
    result["verifier"] = verify_122142701(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    top_id = trigger.get("Id")
    sobject = trigger.get("sObject")
    if not isinstance(sobject, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input must carry the sObject payload")
    if not isinstance(top_id, str) or not top_id.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input.Id must be a non-empty string")
    if sobject.get("Id") != top_id:
        # Step 19 links documents to the top-level Id while step 2 re-reads the
        # record by sObject.Id -- both must be the seeded AH record.
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.sObject.Id must equal trigger_input.Id "
            "(both are the seeded Account_Handover__c record)"
        )
    if not str(sobject.get("Account__c") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.sObject.Account__c must carry the seeded Account token"
        )


def _require_account_properties(section: Any) -> None:
    if not isinstance(section, dict) or not str(section.get("Salesforce Base URL") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires seed.account_properties['Salesforce Base URL'] "
            "(the step-8 formated_contact href prefix)"
        )


def _require_salesforce_section(sf_section: Any) -> None:
    if not isinstance(sf_section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce")
    if sf_section.get("relationship_expansion") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.relationship_expansion must be true "
            "(Account__r / FirstValue_CS_Task__r / Opportunity.AccountId walks)"
        )
    if sf_section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true "
            "(step-13 '!= null' must be evaluated, never dropped)"
        )
    current_user = sf_section.get("current_user")
    if not isinstance(current_user, dict) or str(current_user.get("sobject") or "") != "User":
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.current_user {{'sobject': 'User'}} is required "
            "(Account.OwnerId threads $USER_ID into the step-21 Account_Owner__c ground truth)"
        )
    schema = sf_section.get("schema")
    if not isinstance(schema, list) or not schema:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.schema must declare custom fields")
    declared = {
        (str(entry.get("sobject") or ""), str(entry.get("field") or "")): str(entry.get("sf_type") or "")
        for entry in schema
        if isinstance(entry, dict)
    }
    for field, sf_type in REQUIRED_ACCOUNT_SCHEMA.items():
        if declared.get(("Account", field)) != sf_type:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed.salesforce.schema must declare Account.{field} as {sf_type}"
            )
    records = sf_section.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records must be a non-empty list")
    refs_seen: set[str] = set()
    counts: dict[str, int] = {}
    close_dates: list[str] = []
    for record in records:
        if not isinstance(record, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records entries must be objects")
        sobject = str(record.get("sobject") or "")
        ref = str(record.get("ref") or "").strip()
        fields = record.get("fields")
        if not sobject or not ref or not isinstance(fields, dict):
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded record needs sobject, ref and fields; got {record}"
            )
        if ref in refs_seen:
            raise RuntimeError(f"recipe {RECIPE_ID} duplicate seed ref {ref!r}")
        refs_seen.add(ref)
        counts[sobject] = counts.get(sobject, 0) + 1
        if sobject == "Account":
            for key in REQUIRED_ACCOUNT_SEED_KEYS:
                if key not in fields:
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} seeded Account must declare {key} explicitly "
                        "(use an explicit empty string for skip-branch blanks)"
                    )
            if fields.get("OwnerId") != "$USER_ID":
                raise RuntimeError(
                    f"recipe {RECIPE_ID} seeded Account.OwnerId must be the $USER_ID token"
                )
        if sobject == "Opportunity":
            close_date = str(fields.get("CloseDate") or "")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", close_date):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} seeded Opportunity requires an explicit ISO CloseDate"
                )
            close_dates.append(close_date)
            if not str(fields.get("StageName") or "").strip():
                raise RuntimeError(f"recipe {RECIPE_ID} seeded Opportunity requires StageName")
        if sobject == "ContentVersion":
            for key in ("Title", "PathOnClient", "VersionData"):
                if not str(fields.get(key) or "").strip():
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} seeded ContentVersion requires explicit {key}"
                    )
        if sobject == "OpportunityContactRole":
            for key in ("OpportunityId", "ContactId", "Role"):
                if not str(fields.get(key) or "").strip():
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} seeded OpportunityContactRole requires explicit {key}"
                    )
        if sobject == "ContentDocumentLink":
            raise RuntimeError(
                f"recipe {RECIPE_ID} ContentDocumentLink rows belong in seed.salesforce_phase2 "
                "(they need the phase-1 ContentVersion's live ContentDocumentId)"
            )
    if counts.get("Account_Handover__c", 0) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must create exactly one Account_Handover__c trigger record"
        )
    if counts.get("Account", 0) != 1:
        raise RuntimeError(f"recipe {RECIPE_ID} seed must create exactly one Account")
    if counts.get("Opportunity", 0) < 1 or counts.get("ServiceContract", 0) < 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed needs >=1 Opportunity and >=1 ServiceContract "
            "(keeps the step-11 id concat non-degenerate)"
        )
    if close_dates != sorted(close_dates, reverse=True):
        # The live harness returns owned records in seed order while the raw
        # SOQL orders by CloseDate DESC; enforcing DESC seed order keeps the
        # live result order identical to real Salesforce.
        raise RuntimeError(
            f"recipe {RECIPE_ID} Opportunity seed rows must be ordered by CloseDate DESC: {close_dates}"
        )


def _require_phase2_section(phase2: Any, sf_section: Any) -> None:
    if phase2 is None:
        return
    if not isinstance(phase2, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce_phase2 must be an object")
    records = phase2.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce_phase2.records must be non-empty")
    content_refs = {
        str(record.get("ref") or "").strip().upper()
        for record in (sf_section or {}).get("records") or []
        if isinstance(record, dict) and str(record.get("sobject") or "") == "ContentVersion"
    }
    for record in records:
        if not isinstance(record, dict) or str(record.get("sobject") or "") != "ContentDocumentLink":
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed.salesforce_phase2 only seeds ContentDocumentLink rows"
            )
        fields = record.get("fields") if isinstance(record.get("fields"), dict) else {}
        doc_token = str(fields.get("ContentDocumentId") or "")
        expected_tokens = {f"${ref}_DOC_ID" for ref in content_refs if ref}
        if doc_token not in expected_tokens:
            raise RuntimeError(
                f"recipe {RECIPE_ID} phase-2 ContentDocumentLink.ContentDocumentId must be a "
                f"$<CVREF>_DOC_ID token for a phase-1 ContentVersion ref; got {doc_token!r}"
            )
        if not str(fields.get("LinkedEntityId") or "").startswith("$"):
            raise RuntimeError(
                f"recipe {RECIPE_ID} phase-2 ContentDocumentLink.LinkedEntityId must be a seed ref token"
            )
        if fields.get("ShareType") != "V" or fields.get("Visibility") != "AllUsers":
            raise RuntimeError(
                f"recipe {RECIPE_ID} phase-2 ContentDocumentLink rows must pin ShareType 'V' "
                "and Visibility 'AllUsers'"
            )


def _require_expect_shape(expect: Any, seed_in: dict[str, Any], data: dict[str, Any]) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    required = (
        "stopped",
        "executed_action_count",
        "tools",
        "tool_expectations",
        "update_id",
        "update_fields",
        "created_links",
        "content_links_found",
    )
    missing = [key for key in required if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    if expect["stopped"] is not False:
        raise RuntimeError(f"recipe {RECIPE_ID} has no stop step; expect.stopped must be false")
    tools = expect.get("tools")
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tools, list) or not tools or tools[-1] != "salesforce.update_record":
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools must be the allowed-tool call sequence ending in "
            "the step-21 salesforce.update_record"
        )
    if not isinstance(tool_expectations, list) or len(tool_expectations) != len(tools):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry"
        )
    update_fields = expect.get("update_fields")
    if not isinstance(update_fields, dict) or not update_fields:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.update_fields must pin the step-21 args.fields")
    unknown = sorted(set(update_fields) - set(UPDATE_FIELD_KEYS))
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.update_fields has unknown fields: {unknown}")
    created = expect.get("created_links")
    found = expect.get("content_links_found")
    if not isinstance(created, int) or not isinstance(found, int):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.created_links / expect.content_links_found must be integers"
        )
    if tools.count("salesforce.create_record") != created:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools create_record count must equal expect.created_links"
        )
    force = data.get("force_action_error")
    if isinstance(force, dict) and str(force.get("step_as") or "") == CREATE_STEP_AS:
        if created != 0:
            raise RuntimeError(
                f"recipe {RECIPE_ID} forced step-19 error variants must expect created_links 0 "
                "(the empty catch swallows every create)"
            )
    elif created != found:
        raise RuntimeError(
            f"recipe {RECIPE_ID} without a forced create error, created_links must equal "
            "content_links_found (the foreach creates one link per found row)"
        )
    phase2_rows = len(((seed_in.get("salesforce_phase2") or {}).get("records")) or [])
    if found != phase2_rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.content_links_found ({found}) must equal the number of "
            f"seeded phase-2 ContentDocumentLink rows ({phase2_rows})"
        )


def _provision_salesforce(
    ctx: RecipeContext, seed_in: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    section = deepcopy(seed_in["salesforce"])
    provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": section})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    state = deepcopy(provision["state"])
    snapshot = deepcopy(provision.get("snapshot") or {})
    refs = _salesforce_ref_tokens(section, provision)
    refs.update(_user_ref_tokens(state))
    try:
        refs.update(_resolve_content_documents(state, section.get("records") or []))
        phase2 = seed_in.get("salesforce_phase2")
        if isinstance(phase2, dict):
            section2 = _replace_value(deepcopy(phase2), refs)
            _require_no_tokens(section2, "seed.salesforce_phase2")
            provision2 = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": section2})
            if not provision2.get("ok"):
                raise RuntimeError(f"recipe {RECIPE_ID} phase-2 seed failed: {provision2}")
            state2 = deepcopy(provision2["state"])
            state["owned_records"] = list(state.get("owned_records") or []) + list(
                state2.get("owned_records") or []
            )
            state["read_only_records"] = list(state.get("read_only_records") or []) + list(
                state2.get("read_only_records") or []
            )
            state["expand_relationships"] = bool(
                state.get("expand_relationships") or state2.get("expand_relationships")
            )
            state["strict_soql_conditions"] = bool(
                state.get("strict_soql_conditions") or state2.get("strict_soql_conditions")
            )
            refs.update(_salesforce_ref_tokens(section2, provision2))
            merged_records = list((snapshot.get("salesforce") or {}).get("records") or []) + list(
                ((provision2.get("snapshot") or {}).get("salesforce") or {}).get("records") or []
            )
            snapshot = {"salesforce": {"records": merged_records}}
    except Exception:
        # Phase 2 / doc resolution failed after phase 1 committed live records:
        # remove them before failing so a rerun never sees stale benchmark state.
        from ..salesforce_live_harness import OwnedSalesforce

        OwnedSalesforce(state).delete_owned()
        raise
    return state, snapshot, refs


def _resolve_content_documents(state: dict[str, Any], records: list[Any]) -> dict[str, str]:
    """Read each phase-1 ContentVersion's live ContentDocumentId ($<REF>_DOC_ID
    tokens) and register the ContentDocument as a synthetic owned record so
    harness cleanup deletes the document (cascading versions and links)."""
    content_positions = [
        (str(record.get("ref") or "").strip(), idx)
        for idx, record in enumerate(records)
        if isinstance(record, dict) and str(record.get("sobject") or "") == "ContentVersion"
    ]
    if not content_positions:
        return {}
    owned_rows = list(state.get("owned_records") or [])
    if len(owned_rows) != len(records):
        raise RuntimeError(
            f"recipe {RECIPE_ID} owned-record/seed-record count mismatch: "
            f"{len(owned_rows)} vs {len(records)}"
        )
    refs: dict[str, str] = {}
    doc_rows: list[dict[str, Any]] = []
    simulated_document_ids = {
        str(row.get("id") or ""): str(
            (row.get("fields") or {}).get("ContentDocumentId") or ""
        )
        for row in owned_rows
        if isinstance(row, dict)
        and isinstance(row.get("fields"), dict)
    }
    needs_live_read = any(
        not _SF_ID_RE.fullmatch(
            simulated_document_ids.get(
                str(owned_rows[index].get("id") or ""),
                "",
            )
        )
        for _ref, index in content_positions
    )
    salesforce = None
    if needs_live_read:
        from ..salesforce_live_harness import OwnedSalesforce

        salesforce = OwnedSalesforce(state)
    for ref, idx in content_positions:
        row = owned_rows[idx]
        if str(row.get("physical_sobject") or "") != "ContentVersion":
            raise RuntimeError(
                f"recipe {RECIPE_ID} owned record {idx} is not the expected ContentVersion: {row}"
            )
        record_id = str(row.get("id") or "")
        doc_id = simulated_document_ids.get(record_id, "")
        if not doc_id:
            raw = salesforce._read(
                "ContentVersion",
                record_id,
                ["ContentDocumentId"],
            )
            doc_id = str((raw or {}).get("ContentDocumentId") or "")
        if not _SF_ID_RE.fullmatch(doc_id):
            raise RuntimeError(
                f"recipe {RECIPE_ID} ContentVersion {row.get('id')} has no live ContentDocumentId"
            )
        refs[f"${ref.upper()}_DOC_ID"] = doc_id
        doc_rows.append(
            {
                "id": doc_id,
                "physical_sobject": "ContentDocument",
                "logical_sobject": "ContentDocument",
                "field_names": ["Id"],
            }
        )
    state["owned_records"] = owned_rows + doc_rows
    return refs


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


def _user_ref_tokens(state: dict[str, Any]) -> dict[str, str]:
    for row in state.get("read_only_records") or []:
        if isinstance(row, dict) and str(row.get("logical_sobject") or "") == "User":
            user_id = str(row.get("id") or "")
            if not _SF_ID_RE.fullmatch(user_id):
                raise RuntimeError(f"recipe {RECIPE_ID} current-user id looks invalid: {user_id!r}")
            return {"$USER_ID": user_id}
    raise RuntimeError(f"recipe {RECIPE_ID} current_user seed produced no read-only User record")


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
    return dict(ctx.tools.call("harness.salesforce.snapshot", {}))


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
