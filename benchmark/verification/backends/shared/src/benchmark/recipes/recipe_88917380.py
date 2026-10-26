from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_88917380


RECIPE_ID = "88917380"
SEED_TYPE = "bizible_touchpoint_tagging_variant"
TRACK = "workato_service_bizible_touchpoint_tagging"
TRIGGER_PROVIDER = "workato_service"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "b68b1cac"
SERVICE_NAME = "Bizible Touchpoint Tagging"
MAPPING_TABLE_ID = "3256253"  # "Bizible/Salesforce Mapping Updated": col1 SF campaign, col2 Bizible campaign, col3 Bizible UTM campaign, col4 SF campaign id
OTHER_CAMPAIGNS_TABLE_ID = "3256252"  # "Bizible Lookup Table (Other campaigns)": col1 SF campaign name, col2 SF campaign id
REPLY_LIST_KEYS = (
    "campaign_activities_to_create",
    "campaign_activities_to_update",
    "unhandled_bizible_touchpoints",
    "leads_to_update",
    "contacts_to_update",
)

EXPECTED_ACTIONS: list[tuple[str, str, str, int]] = [
    ("workato_variable", "declare_list", "e4f7ec4f", 3),
    ("workato_variable", "declare_list", "a1bce0af", 4),
    ("workato_variable", "declare_list", "0ed5ac74", 5),
    ("workato_variable", "declare_list", "769b83f8", 6),
    ("workato_variable", "declare_list", "56d83f6f", 7),
    ("workato_smart_list", "create_list", "19924381", 8),
    ("workato_smart_list", "create_list", "b1b52805", 9),
    ("workato_smart_list", "query_list", "db451e5b", 10),
    ("workato_smart_list", "query_list", "ffb8e037", 12),
    ("lookup_table", "search_entries", "d02c897e", 14),
    ("lookup_table", "search_entries", "e3c578c8", 16),
    ("lookup_table", "search_entries", "e1220bd5", 18),
    ("workato_variable", "insert_to_list", "79129f95", 22),
    ("workato_smart_list", "query_list", "2dd33149", 24),
    ("workato_variable", "insert_to_list", "15c7052c", 26),
    ("workato_smart_list", "query_list", "8013b3f6", 28),
    ("workato_variable", "insert_to_list", "8280c99c", 30),
    ("workato_smart_list", "query_list", "8fb36d29", 32),
    ("workato_variable", "insert_to_list", "99b690d2", 34),
    ("lookup_table", "get_entries", "9ec76c54", 35),
    ("logger", "log_message", "23068836", 36),
    ("workato_smart_list", "query_list", "e32ca8c6", 37),
    ("workato_smart_list", "query_list", "3264bba7", 39),
    ("workato_variable", "insert_to_list", "0737710e", 41),
    ("logger", "log_message", "b0643132", 43),
    ("workato_variable", "insert_to_list", "fcb733d8", 45),
    ("workato_variable", "insert_to_list", "677ff1fc", 47),
    ("workato_service", "send_reply", "066db276", 48),
    ("workato_service", "send_reply", "d865b3a4", 50),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_list",
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
    "lookup_table.search_entries",
    "workato_runtime.insert_to_list",
    "lookup_table.get_entries",
    "workato_runtime.log_message",
    "workato_service.send_reply",
]
ALLOWED_TOOLS: list[str] = [
    "workato_runtime.declare_list",
    "workato_runtime.insert_to_list",
    "workato_runtime.log_message",
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
    "lookup_table.search_entries",
    "lookup_table.get_entries",
    "workato_service.send_reply",
]

_PINNED_RAW_JSON = r'''{
 "action_inputs": {
  "066db276": {
   "reply": {
    "campaign_activities_to_create": {
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"e4f7ec4f\",\"path\":[\"list_items\"]}')}",
     "activityCreatedDate": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"e4f7ec4f\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"activityCreatedDate\"]}').in_time_zone(\"America/Los_Angeles\")",
     "campaignId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"e4f7ec4f\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"campaignId\"]}')}",
     "contactId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"e4f7ec4f\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"contactId\"]}')}",
     "leadId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"e4f7ec4f\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"leadId\"]}')}"
    },
    "campaign_activities_to_update": {
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"a1bce0af\",\"path\":[\"list_items\"]}')}",
     "bizible_touchpoint_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"a1bce0af\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"bizible_touchpoint_id\"]}')}",
     "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"a1bce0af\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}"
    },
    "contacts_to_update": {
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"56d83f6f\",\"path\":[\"list_items\"]}')}",
     "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"56d83f6f\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}",
     "leadSource": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"56d83f6f\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"leadSource\"]}')}"
    },
    "leads_to_update": {
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"769b83f8\",\"path\":[\"list_items\"]}')}",
     "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"769b83f8\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}",
     "leadSource": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"769b83f8\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"leadSource\"]}')}"
    },
    "unhandled_bizible_touchpoints": {
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"0ed5ac74\",\"path\":[\"list_items\"]}')}",
     "ad_campaign_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"0ed5ac74\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"ad_campaign_name\"]}')}",
     "marketing_channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"0ed5ac74\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"marketing_channel\"]}')}",
     "utm_medium": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"0ed5ac74\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"utm_medium\"]}')}"
    }
   },
   "reply_type": "success"
  },
  "0737710e": {
   "list_item": {
    "bizible_touchpoint_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"3264bba7\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}",
    "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"8b82d936\",\"path\":[\"id\"]}')}"
   },
   "location": "end",
   "name": "a5c949bb-9b4b-403a-8bc0-6ca0ee8a21b0:a1bce0af"
  },
  "0ed5ac74": {
   "list_item_schema_json": "[{\"name\":\"utm_medium\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"ad_campaign_name\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"marketing_channel\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"}]",
   "name": "Unhandled Bizible Touchpoints"
  },
  "15c7052c": {
   "list_item": {
    "activityCreatedDate": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"touchpoint_datetime\"]}').to_time",
    "campaignId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"e1220bd5\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col4\"]}')}",
    "contactId": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"contact_lead_id\"]}')&.starts_with?(\"003\") ? _dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"contact_lead_id\"]}') : skip",
    "leadId": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"contact_lead_id\"]}')&.starts_with?(\"00Q\") ? _dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"contact_lead_id\"]}') : skip"
   },
   "location": "end",
   "name": "5764e886-7eb7-4f4b-b6c2-e9091c82dce5:e4f7ec4f"
  },
  "19924381": {
   "list_name": "Bizible Touchpoints",
   "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"b68b1cac\",\"path\":[\"request\",\"bizible_touchpoints\"]}')",
   "primary_index": "id"
  },
  "23068836": {
   "message": "=_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"9ec76c54\",\"path\":[\"entries\"]}').pluck(['entry','col1']).format_map('\\'%s\\'').join(\",\")"
  },
  "2dd33149": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "result_schema_json": "[{\"name\":\"id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"}]",
   "sql": "SELECT id FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"list_name\"]}')} WHERE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"columns\", \"campaign_id\"]}')} = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"e1220bd5\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col4\"]}')}' AND #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"columns\", \"contact_lead_id\"]}')} = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"contact_lead_id\"]}')}' AND #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"columns\", \"activity_created_at\"]}')} = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"touchpoint_datetime\"]}')}'"
  },
  "3264bba7": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "result_schema_json": "[{\"control_type\":\"text\",\"label\":\"ID\",\"name\":\"id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Touchpoint datetime\",\"name\":\"touchpoint_datetime\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Marketing channel\",\"name\":\"marketing_channel\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Medium\",\"name\":\"medium\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Email\",\"name\":\"email\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Contact lead ID\",\"name\":\"contact_lead_id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Ad campaign name\",\"name\":\"ad_campaign_name\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Lead source\",\"name\":\"leadSource\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Touchpoint source\",\"name\":\"touchpoint_source\",\"type\":\"string\",\"optional\":false}]",
   "sql": "SELECT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"id\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"touchpoint_datetime\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"marketing_channel\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"medium\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"email\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"contact_lead_id\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"ad_campaign_name\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"leadSource\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"touchpoint_source\"]}')} FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"list_name\"]}')} WHERE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"email\"]}')} = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"c963603d\",\"path\":[\"Email\"]}')}' AND (#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"marketing_channel\"]}')} IN ('Paid Search','Paid Social') OR #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"medium\"]}')} = 'CPC' OR #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"medium\"]}')} = 'adwords') AND (JULIANDAY(#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"touchpoint_datetime\"]}')}) -  JULIANDAY('#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"8b82d936\",\"path\":[\"activity_created_at\"]}')}') <= 180 AND #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"touchpoint_datetime\"]}')} < '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"8b82d936\",\"path\":[\"activity_created_at\"]}')}')  ORDER BY #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"touchpoint_datetime\"]}')} ASC"
  },
  "56d83f6f": {
   "list_item_schema_json": "[{\"name\":\"id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"leadSource\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"}]",
   "name": "Contacts to Update"
  },
  "677ff1fc": {
   "list_item": {
    "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"3264bba7\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"contact_lead_id\"]}')}",
    "leadSource": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"b0643132\",\"path\":[\"message\"]}')}"
   },
   "location": "end",
   "name": "2f08583a-e279-4fb2-bf1a-926284d6286f:769b83f8"
  },
  "769b83f8": {
   "list_item_schema_json": "[{\"name\":\"id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"leadSource\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"}]",
   "name": "Leads to Update"
  },
  "79129f95": {
   "list_item": {
    "ad_campaign_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"ad_campaign_name\"]}')}",
    "marketing_channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"marketing_channel\"]}')}",
    "utm_medium": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"medium\"]}')}"
   },
   "location": "end",
   "name": "70649475-e0c4-4fa4-92a8-47afed957053:0ed5ac74"
  },
  "8013b3f6": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "result_schema_json": "[{\"name\":\"id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"}]",
   "sql": "SELECT id FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"list_name\"]}')} WHERE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"columns\", \"campaign_id\"]}')} = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"e3c578c8\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col4\"]}')}' AND #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"columns\", \"contact_lead_id\"]}')} = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"contact_lead_id\"]}')}' AND #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"columns\", \"activity_created_at\"]}')} = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"touchpoint_datetime\"]}')}'"
  },
  "8280c99c": {
   "list_item": {
    "activityCreatedDate": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"touchpoint_datetime\"]}').to_time",
    "campaignId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"e3c578c8\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col4\"]}')}",
    "contactId": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"contact_lead_id\"]}')&.starts_with?(\"003\") ? _dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"contact_lead_id\"]}') : skip",
    "leadId": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"contact_lead_id\"]}')&.starts_with?(\"00Q\") ? _dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"contact_lead_id\"]}') : skip"
   },
   "location": "end",
   "name": "5764e886-7eb7-4f4b-b6c2-e9091c82dce5:e4f7ec4f"
  },
  "8fb36d29": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "result_schema_json": "[{\"name\":\"id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"}]",
   "sql": "SELECT id FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"list_name\"]}')} WHERE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"columns\", \"campaign_id\"]}')} = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"d02c897e\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col4\"]}')}' AND #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"columns\", \"contact_lead_id\"]}')} = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"contact_lead_id\"]}')}' AND #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"columns\", \"activity_created_at\"]}')} = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"touchpoint_datetime\"]}')}'"
  },
  "99b690d2": {
   "list_item": {
    "activityCreatedDate": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"touchpoint_datetime\"]}').to_time",
    "campaignId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"d02c897e\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col4\"]}')}",
    "contactId": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"contact_lead_id\"]}')&.starts_with?(\"003\") ? _dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"contact_lead_id\"]}') : skip",
    "leadId": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"contact_lead_id\"]}')&.starts_with?(\"00Q\") ? _dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"contact_lead_id\"]}') : skip"
   },
   "location": "end",
   "name": "5764e886-7eb7-4f4b-b6c2-e9091c82dce5:e4f7ec4f"
  },
  "9ec76c54": {
   "lookup_table_id": "3256252"
  },
  "a1bce0af": {
   "list_item_schema_json": "[{\"name\":\"id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"bizible_touchpoint_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"}]",
   "name": "Campaign Activities to Update"
  },
  "b0643132": {
   "message": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"3264bba7\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"touchpoint_source\"]}') == 'Google AdWords'\n  \"Inbound Paid Advertising\"\nelsif _dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"3264bba7\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"touchpoint_source\"]}') == 'LinkedIn'\n  \"LinkedIn Paid Advertising\"\nelse\n  \"Inbound Paid Advertising\"\nend"
  },
  "b1b52805": {
   "list_name": "Campaign Activities",
   "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"b68b1cac\",\"path\":[\"request\",\"campaign_activities\"]}')",
   "primary_index": "id"
  },
  "d02c897e": {
   "lookup_table_id": "3256253",
   "parameters": {
    "col2": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"ad_campaign_name\"]}')}"
   }
  },
  "d865b3a4": {
   "message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"bf97d947\",\"path\":[\"message\"]}')}",
   "reply_type": "error"
  },
  "db451e5b": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "result_schema_json": "[{\"name\":\"Email\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"}]",
   "sql": "SELECT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"email\"]}')} FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"list_name\"]}')} \nUNION \nSELECT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"columns\", \"email\"]}')} FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"list_name\"]}')}"
  },
  "e1220bd5": {
   "lookup_table_id": "3256253",
   "parameters": {
    "col3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"ad_campaign_name\"]}')}"
   }
  },
  "e32ca8c6": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "result_schema_json": "[{\"control_type\":\"text\",\"label\":\"ID\",\"name\":\"id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Activity created at\",\"name\":\"activity_created_at\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Bizible touchpoint ID\",\"name\":\"bizible_touchpoint_id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Email\",\"name\":\"email\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Contact lead ID\",\"name\":\"contact_lead_id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Touchpoint datetime\",\"name\":\"touchpoint_datetime\",\"type\":\"string\",\"optional\":false}]",
   "sql": "SELECT cA.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"columns\", \"id\"]}')},cA.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"columns\", \"activity_created_at\"]}')},cA.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"columns\", \"bizible_touchpoint_id\"]}')},cA.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"columns\", \"email\"]}')},cA.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"columns\", \"contact_lead_id\"]}')},bTP.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"touchpoint_datetime\"]}')} FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"list_name\"]}')} cA LEFT JOIN #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"list_name\"]}')} bTP ON cA.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"columns\", \"bizible_touchpoint_id\"]}')} = bTP.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"id\"]}')} WHERE cA.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"columns\", \"email\"]}')} = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"c963603d\",\"path\":[\"Email\"]}')}' AND cA.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b1b52805\",\"path\":[\"columns\", \"campaign_name\"]}')} IN (#{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"23068836\",\"path\":[\"message\"]}')})"
  },
  "e3c578c8": {
   "lookup_table_id": "3256253",
   "parameters": {
    "col3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"medium\"]}')}"
   }
  },
  "e4f7ec4f": {
   "list_item_schema_json": "[{\"name\":\"campaignId\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"leadId\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"contactId\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"activityCreatedDate\",\"type\":\"date_time\",\"optional\":false}]",
   "name": "Campaign Activities to Create"
  },
  "fcb733d8": {
   "list_item": {
    "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"3264bba7\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"contact_lead_id\"]}')}",
    "leadSource": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"b0643132\",\"path\":[\"message\"]}')}"
   },
   "location": "end",
   "name": "61a8fca3-9d9e-49a8-a35f-670fa5a9e72b:56d83f6f"
  },
  "ffb8e037": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "result_schema_json": "[{\"control_type\":\"text\",\"label\":\"ID\",\"name\":\"id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Touchpoint datetime\",\"name\":\"touchpoint_datetime\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Marketing channel\",\"name\":\"marketing_channel\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Medium\",\"name\":\"medium\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Email\",\"name\":\"email\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Contact lead ID\",\"name\":\"contact_lead_id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Ad campaign name\",\"name\":\"ad_campaign_name\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Lead source\",\"name\":\"leadSource\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Touchpoint source\",\"name\":\"touchpoint_source\",\"type\":\"string\",\"optional\":false}]",
   "sql": "SELECT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"id\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"touchpoint_datetime\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"marketing_channel\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"medium\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"email\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"contact_lead_id\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"ad_campaign_name\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"leadSource\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"touchpoint_source\"]}')} FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"list_name\"]}')} WHERE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"email\"]}')} = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"c963603d\",\"path\":[\"Email\"]}')}' AND (#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"marketing_channel\"]}')} IN ('Paid Search','Paid Social') OR #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"medium\"]}')} = 'CPC' OR #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"19924381\",\"path\":[\"columns\", \"medium\"]}')} = 'adwords')"
  }
 },
 "catch": [
  {
   "as": "bf97d947",
   "input": {
    "max_retry_count": "0",
    "retry_interval": "2"
   },
   "number": 49
  }
 ],
 "else_numbers": [
  21,
  23,
  27,
  31,
  46
 ],
 "foreach": {
  "8b82d936": {
   "number": 38,
   "repeat_mode": "simple",
   "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"e32ca8c6\",\"path\":[\"rows\"]}')}"
  },
  "9f06623b": {
   "number": 13,
   "repeat_mode": "simple",
   "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"ffb8e037\",\"path\":[\"rows\"]}')}"
  },
  "c963603d": {
   "number": 11,
   "repeat_mode": "simple",
   "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"db451e5b\",\"path\":[\"rows\"]}')}"
  }
 },
 "if_inputs": {
  "15": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"d02c897e\",\"path\":[\"entries\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "equals_to",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "17": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"e3c578c8\",\"path\":[\"entries\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "equals_to",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "19": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"e1220bd5\",\"path\":[\"entries\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "equals_to",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "20": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"9f06623b\",\"path\":[\"touchpoint_source\"]}')}",
     "operand": "contains",
     "rhs": "interview"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "25": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"2dd33149\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "equals_to",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "29": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"8013b3f6\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "equals_to",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "33": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"8fb36d29\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "equals_to",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "40": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"3264bba7\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "greater_than",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "42": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"3264bba7\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"leadSource\"]}')}",
     "operand": "not_equals_to",
     "rhs": "Inbound Paid Advertising"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"3264bba7\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"leadSource\"]}')}",
     "operand": "not_equals_to",
     "rhs": "LinkedIn Paid Advertising"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "44": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"3264bba7\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"contact_lead_id\"]}')}",
     "operand": "starts_with",
     "rhs": "003"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 "trigger_input": {
  "reply_schema_json": "[{\"name\":\"campaign_activities_to_create\",\"type\":\"array\",\"of\":\"object\",\"label\":\"Campaign activities to create\",\"optional\":false,\"properties\":[{\"control_type\":\"text\",\"label\":\"Campaign ID\",\"name\":\"campaignId\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Lead ID\",\"name\":\"leadId\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Contact ID\",\"name\":\"contactId\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"date_time\",\"label\":\"Activity created date\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"name\":\"activityCreatedDate\",\"type\":\"date_time\",\"optional\":false}]},{\"name\":\"campaign_activities_to_update\",\"type\":\"array\",\"of\":\"object\",\"label\":\"Campaign activities to update\",\"optional\":false,\"properties\":[{\"control_type\":\"text\",\"label\":\"ID\",\"name\":\"id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Bizible touchpoint ID\",\"name\":\"bizible_touchpoint_id\",\"type\":\"string\",\"optional\":false}]},{\"name\":\"unhandled_bizible_touchpoints\",\"type\":\"array\",\"of\":\"object\",\"label\":\"Unhandled bizible touchpoints\",\"optional\":false,\"properties\":[{\"control_type\":\"text\",\"label\":\"Utm medium\",\"name\":\"utm_medium\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Ad campaign name\",\"name\":\"ad_campaign_name\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Marketing channel\",\"name\":\"marketing_channel\",\"type\":\"string\",\"optional\":false}]},{\"name\":\"leads_to_update\",\"type\":\"array\",\"of\":\"object\",\"label\":\"Leads to update\",\"optional\":false,\"properties\":[{\"control_type\":\"text\",\"label\":\"ID\",\"name\":\"id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Lead source\",\"name\":\"leadSource\",\"type\":\"string\",\"optional\":false}]},{\"name\":\"contacts_to_update\",\"type\":\"array\",\"of\":\"object\",\"label\":\"Contacts to update\",\"optional\":false,\"properties\":[{\"control_type\":\"text\",\"label\":\"ID\",\"name\":\"id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Lead source\",\"name\":\"leadSource\",\"type\":\"string\",\"optional\":false}]}]",
  "request_schema_json": "[{\"name\":\"bizible_touchpoints\",\"type\":\"array\",\"of\":\"object\",\"label\":\"Bizible touchpoints\",\"optional\":false,\"properties\":[{\"control_type\":\"text\",\"label\":\"ID\",\"name\":\"id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Touchpoint datetime\",\"name\":\"touchpoint_datetime\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Marketing channel\",\"name\":\"marketing_channel\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Medium\",\"name\":\"medium\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Email\",\"name\":\"email\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Contact lead ID\",\"name\":\"contact_lead_id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Ad campaign name\",\"name\":\"ad_campaign_name\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Lead source\",\"name\":\"leadSource\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Touchpoint source\",\"name\":\"touchpoint_source\",\"type\":\"string\",\"optional\":true}]},{\"name\":\"campaign_activities\",\"type\":\"array\",\"of\":\"object\",\"label\":\"Campaign activities\",\"optional\":false,\"properties\":[{\"control_type\":\"text\",\"label\":\"ID\",\"name\":\"id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Activity created at\",\"name\":\"activity_created_at\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Bizible touchpoint ID\",\"name\":\"bizible_touchpoint_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Email\",\"name\":\"email\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Contact lead ID\",\"name\":\"contact_lead_id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Campaign ID\",\"name\":\"campaign_id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Campaign name\",\"name\":\"campaign_name\",\"type\":\"string\",\"optional\":false}]}]",
  "service_name": "Bizible Touchpoint Tagging"
 },
 "try_numbers": [
  2
 ]
}'''
PINNED_RAW: dict[str, Any] = json.loads(_PINNED_RAW_JSON)
_TOUCHPOINT_DATETIME_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\","
    "\"line\":\"19924381\",\"path\":[\"columns\", \"touchpoint_datetime\"]}')}"
)
_ACTIVITY_CREATED_AT_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\","
    "\"line\":\"8b82d936\",\"path\":[\"activity_created_at\"]}')}"
)
_OLD_WINDOW = (
    f"JULIANDAY({_TOUCHPOINT_DATETIME_PILL}) -  "
    f"JULIANDAY('{_ACTIVITY_CREATED_AT_PILL}')"
)
_CORRECTED_WINDOW = (
    f"JULIANDAY('{_ACTIVITY_CREATED_AT_PILL}') - "
    f"JULIANDAY({_TOUCHPOINT_DATETIME_PILL})"
)
_WINDOW_SQL = str(PINNED_RAW["action_inputs"]["3264bba7"]["sql"])
if _WINDOW_SQL.count(_OLD_WINDOW) != 1:
    raise RuntimeError("recipe 88917380 temporal-window source pin changed unexpectedly")
PINNED_RAW["action_inputs"]["3264bba7"]["sql"] = _WINDOW_SQL.replace(
    _OLD_WINDOW,
    _CORRECTED_WINDOW,
)

TOUCHPOINT_REQUIRED_FIELDS = ("id", "touchpoint_datetime", "email", "contact_lead_id", "leadSource")
TOUCHPOINT_OPTIONAL_FIELDS = ("marketing_channel", "medium", "ad_campaign_name", "touchpoint_source")
ACTIVITY_REQUIRED_FIELDS = ("id", "activity_created_at", "email", "contact_lead_id", "campaign_id", "campaign_name")
ACTIVITY_OPTIONAL_FIELDS = ("bizible_touchpoint_id",)
MAPPING_TABLE_COLUMNS = ("col1", "col2", "col3", "col4")
OTHER_CAMPAIGNS_TABLE_COLUMNS = ("col1", "col2")


def validate_88917380(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    if _input(raw) != PINNED_RAW["trigger_input"]:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input changed: {_input(raw)!r}")
    actions = _collect_keyword(raw, "action")
    actual = [(a.get("provider"), a.get("name"), a.get("as"), a.get("number")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    for action in actions:
        step_as = str(action.get("as"))
        if _input(action) != PINNED_RAW["action_inputs"][step_as]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} action {step_as} input changed: {_input(action)!r}"
            )
    ifs = _collect_keyword(raw, "if")
    actual_ifs = {str(node.get("number")): _input(node) for node in ifs}
    if actual_ifs != PINNED_RAW["if_inputs"]:
        raise RuntimeError(f"recipe {RECIPE_ID} IF conditions changed: {actual_ifs!r}")
    elses = [node.get("number") for node in _collect_keyword(raw, "else")]
    if elses != PINNED_RAW["else_numbers"]:
        raise RuntimeError(f"recipe {RECIPE_ID} ELSE steps changed: {elses}")
    foreachs = _collect_keyword(raw, "foreach")
    actual_foreach = {
        str(node.get("as")): {
            "number": node.get("number"),
            "repeat_mode": node.get("repeat_mode"),
            "source": _input(node).get("source"),
        }
        for node in foreachs
    }
    if actual_foreach != PINNED_RAW["foreach"]:
        raise RuntimeError(f"recipe {RECIPE_ID} foreach blocks changed: {actual_foreach!r}")
    tries = [node.get("number") for node in _collect_keyword(raw, "try")]
    if tries != PINNED_RAW["try_numbers"]:
        raise RuntimeError(f"recipe {RECIPE_ID} try blocks changed: {tries}")
    catches = _collect_keyword(raw, "catch")
    actual_catch = [
        {"as": node.get("as"), "number": node.get("number"), "input": _input(node)}
        for node in catches
    ]
    if actual_catch != PINNED_RAW["catch"]:
        raise RuntimeError(f"recipe {RECIPE_ID} catch block changed: {actual_catch!r}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "service_name": SERVICE_NAME,
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


def seed_88917380(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88917380(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    request = trigger.get("request")
    if not isinstance(request, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input requires a request object")
    unknown_request_keys = set(request) - {"bizible_touchpoints", "campaign_activities"}
    if unknown_request_keys:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger request has undeclared keys: {sorted(unknown_request_keys)}"
        )
    touchpoints = request.get("bizible_touchpoints")
    activities = request.get("campaign_activities")
    if not isinstance(touchpoints, list) or not isinstance(activities, list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger request requires bizible_touchpoints and "
            "campaign_activities arrays (explicit, possibly empty)"
        )
    _require_rows(
        "request.bizible_touchpoints", touchpoints,
        TOUCHPOINT_REQUIRED_FIELDS, TOUCHPOINT_OPTIONAL_FIELDS,
    )
    _require_rows(
        "request.campaign_activities", activities,
        ACTIVITY_REQUIRED_FIELDS, ACTIVITY_OPTIONAL_FIELDS,
    )
    _require_unique_ids("request.bizible_touchpoints", touchpoints)
    _require_unique_ids("request.campaign_activities", activities)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    lookup_section = seed_in.get("lookup_table")
    if not isinstance(lookup_section, dict) or not isinstance(lookup_section.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed requires lookup_table.tables")
    tables = lookup_section["tables"]
    unknown_tables = set(tables) - {MAPPING_TABLE_ID, OTHER_CAMPAIGNS_TABLE_ID}
    if unknown_tables:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed declares undeclared lookup tables: {sorted(unknown_tables)}"
        )
    _require_lookup_rows(MAPPING_TABLE_ID, tables.get(MAPPING_TABLE_ID), MAPPING_TABLE_COLUMNS)
    _require_lookup_rows(
        OTHER_CAMPAIGNS_TABLE_ID, tables.get(OTHER_CAMPAIGNS_TABLE_ID), OTHER_CAMPAIGNS_TABLE_COLUMNS
    )
    expect = data.get("expect")
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input requires an expect object")
    if not isinstance(expect.get("tools"), list) or not isinstance(expect.get("tool_expectations"), list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect must pin tools and tool_expectations explicitly"
        )
    if not isinstance(expect.get("executed_action_count"), int):
        raise RuntimeError(f"recipe {RECIPE_ID} expect must pin executed_action_count")
    _require_reply_outcome(expect.get("reply_outcome"))
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "lookup_table": deepcopy(lookup_section),
        "expect": deepcopy(expect),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_88917380(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88917380(raw)
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed is missing the lookup_table section")
    # All backends are deterministic Workato-internal mocks reconstructed from
    # the seed on every run; the recipe never writes to the lookup tables, so
    # no cleanup is required for deterministic reruns (cleanup principle).
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = _snapshot(ctx, seed)
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
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_88917380(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_rows(
    label: str,
    rows: list[Any],
    required: tuple[str, ...],
    optional: tuple[str, ...],
) -> None:
    allowed = set(required) | set(optional)
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} {label}[{idx}] must be an object")
        unknown = set(row) - allowed
        if unknown:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {label}[{idx}] has undeclared fields: {sorted(unknown)}"
            )
        for field in required:
            value = row.get(field)
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {label}[{idx}] requires a non-empty string {field!r}"
                )
        for field in optional:
            if field in row and not isinstance(row.get(field), str):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {label}[{idx}] optional field {field!r} must be a string"
                )
        for field, value in row.items():
            if isinstance(value, str) and "'" in value:
                # Every request field is interpolated into smart-list SQL string
                # literals; an apostrophe would silently corrupt the query.
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {label}[{idx}].{field} must not contain an apostrophe"
                )


def _require_unique_ids(label: str, rows: list[Any]) -> None:
    ids = [str(row.get("id")) for row in rows if isinstance(row, dict)]
    if len(ids) != len(set(ids)):
        raise RuntimeError(f"recipe {RECIPE_ID} {label} ids must be unique (primary_index id)")


def _require_lookup_rows(table_id: str, rows: Any, columns: tuple[str, ...]) -> None:
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed lookup_table.tables[{table_id!r}] must be a non-empty list"
        )
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(
                f"recipe {RECIPE_ID} lookup_table {table_id} row {idx} must be an object"
            )
        unknown = set(row) - set(columns) - {"id"}
        if unknown:
            raise RuntimeError(
                f"recipe {RECIPE_ID} lookup_table {table_id} row {idx} has undeclared "
                f"columns: {sorted(unknown)}"
            )
        for column in columns:
            value = row.get(column)
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} lookup_table {table_id} row {idx} requires a "
                    f"non-empty string {column!r}"
                )
            if "'" in value:
                # col4 / col1 values are interpolated into smart-list SQL.
                raise RuntimeError(
                    f"recipe {RECIPE_ID} lookup_table {table_id} row {idx}.{column} must "
                    "not contain an apostrophe"
                )


def _require_reply_outcome(outcome: Any) -> None:
    if not isinstance(outcome, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} expect must declare a reply_outcome object")
    reply_type = outcome.get("reply_type")
    if reply_type == "success":
        reply = outcome.get("reply")
        if not isinstance(reply, dict) or set(reply) != set(REPLY_LIST_KEYS) or not all(
            isinstance(reply[key], list) for key in REPLY_LIST_KEYS
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} success reply_outcome must pin all five reply lists"
            )
        if "message" in outcome:
            raise RuntimeError(
                f"recipe {RECIPE_ID} success reply_outcome must not carry a message"
            )
        return
    if reply_type == "error":
        if not isinstance(outcome.get("message"), str) or not outcome["message"].strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} error reply_outcome must pin the exact catch message"
            )
        if outcome.get("reply") != {}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} error reply_outcome must pin reply == {{}}"
            )
        return
    raise RuntimeError(
        f"recipe {RECIPE_ID} reply_outcome.reply_type must be 'success' or 'error'"
    )


def _collect_keyword(node: dict[str, Any], keyword: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == keyword and not child.get("skip"):
            found.append(child)
        found.extend(_collect_keyword(child, keyword))
    return found


def _input(node: dict[str, Any]) -> dict[str, Any]:
    value = node.get("input")
    return value if isinstance(value, dict) else {}


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("lookup_table"), dict):
        out.update(ctx.tools.call("harness.lookup_table.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
