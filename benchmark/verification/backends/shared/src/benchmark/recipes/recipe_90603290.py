from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_90603290


RECIPE_ID = "90603290"
SEED_TYPE = "api_meeting_window_report_variant"
TRACK = "workato_api_dbtable_smartlist_meeting_report"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "f6585b3d"


_STRUCTURE_PINS_JSON = r'''
[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "f6585b3d",
  "provider": "workato_api_platform",
  "name": "receive_request",
  "skip": false,
  "input": {
   "request": {
    "content_type": "json",
    "schema": "[{\"name\":\"Input\",\"type\":\"array\",\"optional\":false,\"properties\":[{\"name\":\"email\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Email\"},{\"name\":\"start_date\",\"type\":\"date_time\",\"optional\":false,\"control_type\":\"date\",\"label\":\"Start Date Filter\",\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\"},{\"name\":\"end_date\",\"type\":\"date_time\",\"optional\":false,\"label\":\"End Date Filter\",\"control_type\":\"date\",\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\"}],\"of\":\"object\",\"label\":\"Input\"}]"
   },
   "response": {
    "content_type": "json",
    "responses": [
     {
      "body_schema": "[{\"name\":\"meetings\",\"type\":\"array\",\"of\":\"object\",\"label\":\"Meetings\",\"optional\":true,\"properties\":[{\"control_type\":\"text\",\"label\":\"Email\",\"name\":\"email\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Name\",\"name\":\"name\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Time Zone\",\"name\":\"timezone\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Meeting ID\",\"name\":\"meeting_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Meeting Summary\",\"name\":\"meting_summary\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Meeting Description\",\"name\":\"meting_description\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"date_time\",\"label\":\"Scheduled Start Time\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"name\":\"meeting_starttime\",\"type\":\"date_time\",\"optional\":true},{\"control_type\":\"date_time\",\"label\":\"Scheduled End Time\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"name\":\"meeting_endtime\",\"type\":\"date_time\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Attendees\",\"name\":\"attendees\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Meeting link\",\"name\":\"meeting_link\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Host email\",\"name\":\"host_email\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Meeting status\",\"name\":\"meeting_status\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Meeting location\",\"name\":\"meeting_location\",\"type\":\"string\",\"optional\":true}]}]",
      "http_status_code": "200",
      "name": "Results"
     }
    ]
   }
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "349d413d",
  "provider": "workato_db_table",
  "name": "get_records",
  "skip": false,
  "input": {
   "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id",
   "1366db46-c8b2-4d57-8c21-9d8d924e331f": "string",
   "22fbd5bf-3852-40e8-a929-6afaaed93689": "string",
   "3415b075-e307-42e5-95b3-2e793b28b43f": "string",
   "40461582-85ed-4ec7-9a9d-1e0b7ac07e43": "string",
   "47dafb22-0211-4e6d-b82e-fe3a97e98de8": "date_time",
   "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time",
   "6323aa9b-bc51-42c0-bdd2-3bdfa57a4dfa": "string",
   "64c4fc18-e525-44c3-8be5-1d300231c2ec": "string",
   "7346615c-5923-4f01-9ae8-be63ef61859a": "string",
   "7cd7c272-18a5-476b-a6b7-c3e238e1b7a8": "string",
   "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time",
   "b2abd0ea-7c99-4adf-af90-9dcaf4209971": "string",
   "c1b372e8-2721-407a-a4f4-346b04521a1c": "date_time",
   "cbbd08a9-9991-4ee3-9362-031b4e723af2": "string",
   "fb4ed4e5-183f-4e10-bccc-bdce5d3a325b": "string",
   "filters": [
    {
     "field_id": "cbbd08a9-9991-4ee3-9362-031b4e723af2",
     "op_default": "eq",
     "value_default": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"f6585b3d\",\"path\":[\"request\", \"Input\", {\"path_element_type\": \"current_item\"}, \"email\"]}')}"
    },
    {
     "field_id": "c1b372e8-2721-407a-a4f4-346b04521a1c",
     "op_date_time": "gt",
     "value_date_time": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"f6585b3d\",\"path\":[\"request\",\"Input\",{\"path_element_type\":\"current_item\"},\"start_date\"]}').to_date()"
    },
    {
     "field_id": "47dafb22-0211-4e6d-b82e-fe3a97e98de8",
     "op_date_time": "lte",
     "value_date_time": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"f6585b3d\",\"path\":[\"request\",\"Input\",{\"path_element_type\":\"current_item\"},\"end_date\"]}').to_date()"
    }
   ],
   "limit": "200",
   "order_direction": "asc",
   "table_id": "4508"
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "543c4d86",
  "provider": "workato_variable",
  "name": "declare_list",
  "skip": false,
  "input": {
   "list_item_schema_json": "[{\"control_type\":\"text\",\"label\":\"Email\",\"name\":\"email\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Name\",\"name\":\"name\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Time Zone\",\"name\":\"timezone\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Meeting ID\",\"name\":\"meeting_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Meeting Summary\",\"name\":\"meting_summary\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Meeting Description\",\"name\":\"meting_description\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Attendees\",\"name\":\"meeting_attendees\",\"type\":\"string\",\"optional\":true},{\"label\":\"Scheduled Start Time\",\"name\":\"meeting_starttime\",\"type\":\"date_time\",\"optional\":true,\"control_type\":\"date_time\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\"},{\"label\":\"Scheduled End Time\",\"name\":\"meeting_endtime\",\"type\":\"date_time\",\"optional\":true,\"control_type\":\"date_time\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\"},{\"control_type\":\"text\",\"label\":\"Attendees\",\"name\":\"attendees\",\"type\":\"string\",\"optional\":true},{\"name\":\"meeting_link\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Meeting link\"},{\"name\":\"host_email\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Host email\"},{\"name\":\"meeting_status\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Meeting status\"},{\"name\":\"meeting_location\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Meeting location\"}]",
   "list_items": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"349d413d\",\"path\":[\"records\"]}')}",
    "attendees": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"349d413d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"b2abd0ea_7c99_4adf_af90_9dcaf4209971\"]}')}",
    "email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"349d413d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"cbbd08a9_9991_4ee3_9362_031b4e723af2\"]}')}",
    "host_email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"349d413d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"7346615c_5923_4f01_9ae8_be63ef61859a\"]}')}",
    "meeting_attendees": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"349d413d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"b2abd0ea_7c99_4adf_af90_9dcaf4209971\"]}')}",
    "meeting_endtime": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"349d413d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"47dafb22_0211_4e6d_b82e_fe3a97e98de8\"]}')}",
    "meeting_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"349d413d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"40461582_85ed_4ec7_9a9d_1e0b7ac07e43\"]}')}",
    "meeting_link": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"349d413d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"64c4fc18_e525_44c3_8be5_1d300231c2ec\"]}')}",
    "meeting_location": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"349d413d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"1366db46_c8b2_4d57_8c21_9d8d924e331f\"]}')}",
    "meeting_starttime": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"349d413d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"c1b372e8_2721_407a_a4f4_346b04521a1c\"]}')}",
    "meeting_status": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"349d413d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"fb4ed4e5_183f_4e10_bccc_bdce5d3a325b\"]}')}",
    "meting_description": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"349d413d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"22fbd5bf_3852_40e8_a929_6afaaed93689\"]}')}",
    "meting_summary": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"349d413d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"6323aa9b_bc51_42c0_bdd2_3bdfa57a4dfa\"]}')}",
    "name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"349d413d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"3415b075_e307_42e5_95b3_2e793b28b43f\"]}')}",
    "timezone": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"349d413d\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"7cd7c272_18a5_476b_a6b7_c3e238e1b7a8\"]}')}"
   },
   "name": "Filter"
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "0ad61b9f",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "next_page_token": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"349d413d\",\"path\":[\"continuation_token\"]}').presence"
    },
    "schema": "[{\"name\":\"next_page_token\",\"type\":\"string\",\"optional\":true,\"label\":\"next_page_token\",\"details\":{\"real_name\":\"next_page_token\"},\"control_type\":\"text\"}]"
   }
  }
 },
 {
  "keyword": "if",
  "number": 5,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"0ad61b9f\",\"path\":[\"next_page_token\"]}')}",
     "operand": "present",
     "rhs": ""
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "repeat",
  "number": 6,
  "as": "8976b691",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {}
 },
 {
  "keyword": "action",
  "number": 7,
  "as": "c5f39c40",
  "provider": "workato_db_table",
  "name": "get_records",
  "skip": false,
  "input": {
   "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id",
   "1366db46-c8b2-4d57-8c21-9d8d924e331f": "string",
   "22fbd5bf-3852-40e8-a929-6afaaed93689": "string",
   "3415b075-e307-42e5-95b3-2e793b28b43f": "string",
   "40461582-85ed-4ec7-9a9d-1e0b7ac07e43": "string",
   "47dafb22-0211-4e6d-b82e-fe3a97e98de8": "date_time",
   "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time",
   "6323aa9b-bc51-42c0-bdd2-3bdfa57a4dfa": "string",
   "64c4fc18-e525-44c3-8be5-1d300231c2ec": "string",
   "7346615c-5923-4f01-9ae8-be63ef61859a": "string",
   "7cd7c272-18a5-476b-a6b7-c3e238e1b7a8": "string",
   "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time",
   "b2abd0ea-7c99-4adf-af90-9dcaf4209971": "string",
   "c1b372e8-2721-407a-a4f4-346b04521a1c": "date_time",
   "cbbd08a9-9991-4ee3-9362-031b4e723af2": "string",
   "continuation_token": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"0ad61b9f\",\"path\":[\"next_page_token\"]}')}",
   "fb4ed4e5-183f-4e10-bccc-bdce5d3a325b": "string",
   "filters": [
    {
     "field_id": "cbbd08a9-9991-4ee3-9362-031b4e723af2",
     "op_default": "eq",
     "value_default": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"f6585b3d\",\"path\":[\"request\", \"Input\", {\"path_element_type\": \"current_item\"}, \"email\"]}')}"
    },
    {
     "field_id": "c1b372e8-2721-407a-a4f4-346b04521a1c",
     "op_date_time": "gt",
     "value_date_time": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"f6585b3d\",\"path\":[\"request\",\"Input\",{\"path_element_type\":\"current_item\"},\"start_date\"]}').to_date()"
    },
    {
     "field_id": "47dafb22-0211-4e6d-b82e-fe3a97e98de8",
     "op_date_time": "lte",
     "value_date_time": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"f6585b3d\",\"path\":[\"request\",\"Input\",{\"path_element_type\":\"current_item\"},\"end_date\"]}').to_date()"
    }
   ],
   "limit": "200",
   "order_direction": "asc",
   "table_id": "4508"
  }
 },
 {
  "keyword": "action",
  "number": 8,
  "as": "d5bc84e8",
  "provider": "workato_variable",
  "name": "insert_to_list_batch",
  "skip": false,
  "input": {
   "list_items": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c5f39c40\",\"path\":[\"records\"]}')}",
    "attendees": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c5f39c40\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"b2abd0ea_7c99_4adf_af90_9dcaf4209971\"]}')}",
    "email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c5f39c40\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"cbbd08a9_9991_4ee3_9362_031b4e723af2\"]}')}",
    "host_email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c5f39c40\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"7346615c_5923_4f01_9ae8_be63ef61859a\"]}')}",
    "meeting_attendees": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c5f39c40\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"b2abd0ea_7c99_4adf_af90_9dcaf4209971\"]}')}",
    "meeting_endtime": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c5f39c40\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"47dafb22_0211_4e6d_b82e_fe3a97e98de8\"]}')}",
    "meeting_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c5f39c40\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"40461582_85ed_4ec7_9a9d_1e0b7ac07e43\"]}')}",
    "meeting_link": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c5f39c40\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"64c4fc18_e525_44c3_8be5_1d300231c2ec\"]}')}",
    "meeting_location": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c5f39c40\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"1366db46_c8b2_4d57_8c21_9d8d924e331f\"]}')}",
    "meeting_starttime": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c5f39c40\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"c1b372e8_2721_407a_a4f4_346b04521a1c\"]}')}",
    "meeting_status": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c5f39c40\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"fb4ed4e5_183f_4e10_bccc_bdce5d3a325b\"]}')}",
    "meting_description": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c5f39c40\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"22fbd5bf_3852_40e8_a929_6afaaed93689\"]}')}",
    "meting_summary": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c5f39c40\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"6323aa9b_bc51_42c0_bdd2_3bdfa57a4dfa\"]}')}",
    "name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c5f39c40\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"3415b075_e307_42e5_95b3_2e793b28b43f\"]}')}",
    "timezone": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c5f39c40\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"7cd7c272_18a5_476b_a6b7_c3e238e1b7a8\"]}')}"
   },
   "location": "end",
   "name": "c8fc471c-0398-4713-8cda-7b275e22e79c:543c4d86"
  }
 },
 {
  "keyword": "action",
  "number": 9,
  "as": "c580508f",
  "provider": "workato_variable",
  "name": "update_variables",
  "skip": false,
  "input": {
   "name": "863b0f39-f224-4941-a3d2-82276c1396b9:0ad61b9f:next_page_token",
   "next_page_token": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"c5f39c40\",\"path\":[\"continuation_token\"]}').presence or clear"
  }
 },
 {
  "keyword": "while_condition",
  "number": 10,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"0ad61b9f\",\"path\":[\"next_page_token\"]}')}",
     "operand": "present",
     "rhs": ""
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "if",
  "number": 11,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"543c4d86\",\"path\":[\"list_items\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "not_equals_to",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 12,
  "as": "e841d3ba",
  "provider": "workato_smart_list",
  "name": "create_list",
  "skip": false,
  "input": {
   "force": "false",
   "list_name": "MEETING_RECORDS",
   "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"543c4d86\",\"path\":[\"list_items\"]}')",
   "primary_index": "meeting_id"
  }
 },
 {
  "keyword": "action",
  "number": 13,
  "as": "195c0463",
  "provider": "workato_smart_list",
  "name": "query_list",
  "skip": false,
  "input": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "output_schema_by": "index",
   "result_schema_json": "[{\"control_type\":\"text\",\"label\":\"Email\",\"name\":\"email\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Name\",\"name\":\"name\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Time Zone\",\"name\":\"timezone\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Meeting ID\",\"name\":\"meeting_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Meeting Summary\",\"name\":\"meting_summary\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Meeting Description\",\"name\":\"meting_description\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Attendees\",\"name\":\"meeting_attendees\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"date_time\",\"label\":\"Scheduled Start Time\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"name\":\"meeting_starttime\",\"type\":\"date_time\",\"optional\":true},{\"control_type\":\"date_time\",\"label\":\"Scheduled End Time\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"name\":\"meeting_endtime\",\"type\":\"date_time\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Attendees\",\"name\":\"attendees\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Meeting link\",\"name\":\"meeting_link\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Host email\",\"name\":\"host_email\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Meeting status\",\"name\":\"meeting_status\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Meeting location\",\"name\":\"meeting_location\",\"type\":\"string\",\"optional\":true}]",
   "sql": "SELECT * FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"e841d3ba\",\"path\":[\"list_name\"]}')}"
  }
 },
 {
  "keyword": "action",
  "number": 14,
  "as": "5ce4c025",
  "provider": "workato_api_platform",
  "name": "return_response",
  "skip": false,
  "input": {
   "http_status_code": "200",
   "response": {
    "meetings": {
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"195c0463\",\"path\":[\"rows\"]}')}",
     "attendees": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"195c0463\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"meeting_attendees\"]}')}",
     "email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"195c0463\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"email\"]}')}",
     "host_email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"195c0463\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"host_email\"]}')}",
     "meeting_endtime": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"195c0463\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"meeting_endtime\"]}')}",
     "meeting_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"195c0463\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"meeting_id\"]}')}",
     "meeting_link": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"195c0463\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"meeting_link\"]}')}",
     "meeting_location": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"195c0463\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"meeting_location\"]}')}",
     "meeting_starttime": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"195c0463\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"meeting_starttime\"]}')}",
     "meeting_status": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"195c0463\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"meeting_status\"]}')}",
     "meting_description": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"195c0463\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"meting_description\"]}')}",
     "meting_summary": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"195c0463\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"meting_summary\"]}')}",
     "name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"195c0463\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"name\"]}')}",
     "timezone": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"195c0463\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"timezone\"]}')}"
    }
   }
  }
 }
]
'''

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

TABLE_ID = "4508"
EMAIL_COL = "cbbd08a9_9991_4ee3_9362_031b4e723af2"
START_COL = "c1b372e8_2721_407a_a4f4_346b04521a1c"
END_COL = "47dafb22_0211_4e6d_b82e_fe3a97e98de8"
RECORD_ID_COL = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
SOURCE_COLS = (
    "7cd7c272_18a5_476b_a6b7_c3e238e1b7a8",  # Time Zone
    "3415b075_e307_42e5_95b3_2e793b28b43f",  # Name
    EMAIL_COL,                                # Email
    "40461582_85ed_4ec7_9a9d_1e0b7ac07e43",  # Meeting ID
    "6323aa9b_bc51_42c0_bdd2_3bdfa57a4dfa",  # Meeting Summary
    "22fbd5bf_3852_40e8_a929_6afaaed93689",  # Meeting Description
    START_COL,                                # Start
    END_COL,                                  # End
    "b2abd0ea_7c99_4adf_af90_9dcaf4209971",  # Attendees
    "64c4fc18_e525_44c3_8be5_1d300231c2ec",  # meeting_link
    "7346615c_5923_4f01_9ae8_be63ef61859a",  # host_email
    "fb4ed4e5_183f_4e10_bccc_bdce5d3a325b",  # meeting_status
    "1366db46_c8b2_4d57_8c21_9d8d924e331f",  # meeting_location
)

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_runtime.declare_list",
    "workato_runtime.declare_variable",
    "workato_runtime.insert_to_list_batch",
    "workato_runtime.update_variables",
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_api_platform.return_response",
]
SEED_SECTIONS = {"workato_db_table"}
EXPECT_KEYS = (
    "tools",
    "tool_expectations",
    "executed_action_count",
    "api_response",
    "meetings_count",
    "paginated",
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
        pin["batch_size"] = node.get("batch_size")
        pin["source"] = node.get("source")
    if isinstance(node.get("filter"), dict):
        pin["filter"] = node["filter"]
    out = [pin]
    for child in node.get("block") or []:
        if isinstance(child, dict):
            out.extend(_structure(child))
    return out


def validate_90603290(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_90603290(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_90603290(raw)
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
    expect = _require_expect(data)
    _require_db_table_section(seed_in.get("workato_db_table"), expect)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": deepcopy(trigger),
        "expect": deepcopy(expect),
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
    }
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_90603290(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_90603290(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
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
    result["verifier"] = verify_90603290(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != ["request"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the API request object; "
            f"got {sorted(trigger.keys())}"
        )
    request = trigger.get("request")
    if not isinstance(request, dict) or sorted(request.keys()) != ["Input"]:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input.request must carry exactly 'Input'")
    entries = request.get("Input")
    if not isinstance(entries, list) or len(entries) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} request.Input must be a single-element array — the recipe only "
            "ever reads Input.current_item (the first element); extra elements would imply "
            "multi-element semantics the recipe does not have"
        )
    entry = entries[0]
    if not isinstance(entry, dict) or sorted(entry.keys()) != ["email", "end_date", "start_date"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} Input[0] must carry exactly email/start_date/end_date"
        )
    for key in ("email", "start_date", "end_date"):
        if not str(entry.get(key) or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} Input[0].{key} must be non-empty")
    for key in ("start_date", "end_date"):
        value = str(entry[key])
        if len(value) != 10 or value[4] != "-" or value[7] != "-":
            raise RuntimeError(
                f"recipe {RECIPE_ID} Input[0].{key} must be an explicit YYYY-MM-DD date "
                "(the filters render '=….to_date()')"
            )


def _require_expect(data: dict[str, Any]) -> dict[str, Any]:
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    tools = expect.get("tools")
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tools, list) or not isinstance(tool_expectations, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools/tool_expectations must be lists")
    if len(tools) != len(tool_expectations):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry")
    unknown_tools = sorted(set(tools) - set(ALLOWED_TOOLS))
    if unknown_tools:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools has unknown tools: {unknown_tools}")
    if not isinstance(expect.get("paginated"), bool):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.paginated must be an explicit boolean")
    api_response = expect.get("api_response")
    if (
        not isinstance(api_response, dict)
        or str(api_response.get("http_status_code") or "") != "200"
        or not isinstance(api_response.get("response"), dict)
        or not isinstance(api_response["response"].get("meetings"), list)
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.api_response must pin the exact 200 response body "
            "({'meetings': [...]})"
        )
    if len(api_response["response"]["meetings"]) != int(expect.get("meetings_count") or 0):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.meetings_count must equal the pinned meetings length"
        )
    expected_pages = 2 if expect["paginated"] else 1
    if tools != ["workato_db_table.get_records"] * expected_pages + ["workato_api_platform.return_response"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools must be {expected_pages}x get_records followed by "
            "the terminal return_response"
        )
    return expect


def _require_db_table_section(section: Any, expect: dict[str, Any]) -> None:
    if not isinstance(section, dict) or not isinstance(section.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.workato_db_table.tables")
    if sorted(section["tables"]) != [TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table.tables must declare exactly table {TABLE_ID}"
        )
    rows = section["tables"][TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {TABLE_ID} must seed at least one explicit row (empty-"
            "result variants must prove the FILTERS excluded real rows, not an empty table)"
        )
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table {TABLE_ID} rows must be objects")
        if not str(row.get(RECORD_ID_COL) or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} every Sales Meetings row needs {RECORD_ID_COL}")
        missing = [col for col in SOURCE_COLS if not str(row.get(col) or "").strip()]
        if missing:
            raise RuntimeError(
                f"recipe {RECIPE_ID} Sales Meetings rows must set every ____source-mapped column "
                f"explicitly (missing {missing}) — a hole would silently become a null meeting field"
            )
    tokens = section.get("continuation_tokens")
    if expect.get("paginated") is True:
        if not isinstance(tokens, dict) or not str(tokens.get(TABLE_ID) or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} paginated variants must seed a plain continuation token "
                f"under seed.workato_db_table.continuation_tokens[{TABLE_ID!r}]"
            )
    elif tokens is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} non-paginated variants must not seed continuation tokens"
        )


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    out = dict(ctx.tools.call("harness.workato_db_table.snapshot", {}))
    out.pop("ok", None)
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
