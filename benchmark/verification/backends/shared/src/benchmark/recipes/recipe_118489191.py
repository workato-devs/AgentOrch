from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_118489191


RECIPE_ID = "118489191"
SEED_TYPE = "webhook_registrant_sheets_slack_review_variant"
TRACK = "live_google_sheets_slack_webhook_event_registration"
TRIGGER_PROVIDER = "workato_webhooks"
TRIGGER_NAME = "new_event"
TRIGGER_AS = "a933e72a"
LOOKUP_TABLE_ID = "4195320"
CATCH_STEP_AS = "36d3b7d0"
GRACEFUL_STOP_STEP = 5
ERROR_STOP_STEP = 17
FORCEABLE_STEPS = {"4cd73a31"}
SERVICE_REPLY_STEPS = {"33035003", "f865207a", "50073cae"}
# The 13 raw column headers, exactly as the search/update/add steps declare
# them in column_headers (the benchmark tab is seeded with these).
SHEET_HEADERS = [
    "Company",
    "First Name",
    "Last Name",
    "Job Title",
    "Email Address",
    "Phone",
    "Dietary Restrictions",
    "ID",
    "Cal Invite Sent?",
    'If Dietary Restriction is "Other"',
    "Type",
    "Notes",
    "Status",
]
PAYLOAD_KEYS = (
    "firstname", "lastname", "email", "company", "campaign_id",
    "phone", "comments", "time_zone", "leadid", "sfdcid",
)

# workato_webhooks.new_event (as a933e72a): payload {firstname, lastname,
# email, company, campaign_id, phone, comments, time_zone, leadid, sfdcid
# [, joinURL]}. Body (one big TRY):
#   3  lookup_table.search_entries 4f1286a3 table 4195320 col3 =
#      payload.campaign_id (Workato-internal mock; col2 event name, col4/col5
#      spreadsheet/sheet [redirected to the benchmark tab], col6 slack
#      channel, col7 bot command)
#   4  IF entries size == 0 -> 5 STOP (stop_with_error=false, graceful)
#   6  google_sheets.search_spreadsheet_rows_v4_new 4cd73a31 (LIVE):
#      col_'Email Address' = payload.email, count 400
#   7  workato_service.call_service 33035003 flow 45178540 {lead_id} ->
#      reply.{Lead, Company, MKTO, SFDC} (deterministic seeded reply)
#   8  workato_service.call_service f865207a flow 45178537
#      {account_id, contact_id, lead_id from #7 SFDC} -> reply.record_type
#   9  declare_variable 46e3f07e account_type = reply.record_type .presence
#      or "New Lead"
#   10 IF #6 rows size != 0 -> 11 update_row_v4_new fb8e9257 (row_number from
#      the first matched row; 11 label-mapped columns incl. static Status
#      'Waitlisted' + Cal Invite Sent? 'Sent (If Accepted)')
#   12 ELSE -> 13 add_spreadsheet_row_v4 98f30966 (12 columns incl. col_ID =
#      payload.leadid; sheet_name pill reads 4cd73a31['sheet'])
#   14 slack_bot.post_bot_message 35a6b894 (LIVE; channel = LT col6 ->
#      SLACK_CHANNEL_OVERRIDE; rendered text = title 'New Registrant for
#      #{col2}' + 5 attachment_fields; buttons/title_link are metadata)
#   CATCH 36d3b7d0 (max_retry 3/10s; the engine runs the try body once and
#   the catch once -- retry config pinned at validate time only):
#   16 call_service 50073cae flow 45178280 {error_message '(first last -
#      email)#{catch.message}', job_id/job_url/recipe_id job_context pills,
#      stop_recipe 'false'} -> 17 STOP stop_with_error=true
#
# Branch-mapping notes (recorded per benmark_rules):
# - variant_00 campaign_not_found_stop: LT search misses -> graceful STOP 5
#   after exactly one action.
# - variant_01 existing_row_update: the seeded registrant row matches the
#   email -> IF-10 update path + slack post.
# - variant_02 new_row_add_new_lead: no matching row -> ELSE add path;
#   f865207a.record_type '' -> account_type 'New Lead' (presence-or arm).
# - variant_03 catch_error_notify_stop: forced error on the 4cd73a31 sheets
#   search -> catch call_service (error_message interpolation + pinned
#   job_context) -> STOP 17 with error.
#
# FLAGGED ENGINE GAPS (probe-proven, /tmp/probe_118489191.py) -- live-green
# for variants 01/02 is blocked on two shared-file fixes:
# - F1 (triage-flagged): the live sheets search result carries 'tab' but NOT
#   the 'sheet' output field the raw extended_output_schema declares, so the
#   ELSE add-row sheet_name pill resolves to the MISSING sentinel inside
#   args['sheet'] (non-JSON-serializable trace). Fix: emit 'sheet' alias in
#   GoogleSheetsLiveClient.search_rows.
# - F2 (new): google_sheets_search_rows passes filter keys through RAW
#   ('col_Email Address') while live rows are keyed by the actual headers
#   ('Email Address'), so the search NEVER matches and the IF-10 update path
#   is unreachable live. Fix: label-map the filter keys like the update/add
#   adapters (or col_-strip matching in the live client).
#
# Backends: google_sheets LIVE (env-redirected benchmark tab; the seed fully
# overwrites the tab per run -> deterministic reruns, no cleanup needed);
# slack LIVE (ordinary observable post, never re-read -> no cleanup per the
# cleanup principle); lookup_table + workato_service are Workato-internal
# deterministic mocks (replies keyed by step as-id, fail-fast when absent).

_STRUCTURE_PINS_JSON = r'''
[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "a933e72a",
  "provider": "workato_webhooks",
  "name": "new_event",
  "skip": false,
  "input": {
   "request": {
    "headers_schema": "[{\"control_type\":\"text\",\"label\":\"Accept\",\"type\":\"string\",\"name\":\"accept\"},{\"control_type\":\"text\",\"label\":\"Accept encoding\",\"type\":\"string\",\"name\":\"accept_encoding\"},{\"control_type\":\"text\",\"label\":\"Connection\",\"type\":\"string\",\"name\":\"connection\"},{\"control_type\":\"text\",\"label\":\"Content length\",\"type\":\"string\",\"name\":\"content_length\"},{\"control_type\":\"text\",\"label\":\"Content type\",\"type\":\"string\",\"name\":\"content_type\"},{\"control_type\":\"text\",\"label\":\"User agent\",\"type\":\"string\",\"name\":\"user_agent\"},{\"control_type\":\"text\",\"label\":\"X amzn trace ID\",\"type\":\"string\",\"name\":\"x_amzn_trace_id\"},{\"control_type\":\"text\",\"label\":\"X correlation ID\",\"type\":\"string\",\"name\":\"x_correlation_id\"},{\"control_type\":\"text\",\"label\":\"X forwarded for\",\"type\":\"string\",\"name\":\"x_forwarded_for\"},{\"control_type\":\"text\",\"label\":\"X forwarded port\",\"type\":\"string\",\"name\":\"x_forwarded_port\"},{\"control_type\":\"text\",\"label\":\"X forwarded proto\",\"type\":\"string\",\"name\":\"x_forwarded_proto\"},{\"control_type\":\"text\",\"label\":\"X request ID\",\"type\":\"string\",\"name\":\"x_request_id\"}]",
    "payload_schema": "[{\"control_type\":\"text\",\"label\":\"Firstname\",\"name\":\"firstname\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Lastname\",\"name\":\"lastname\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Email\",\"name\":\"email\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Company\",\"name\":\"company\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Campaign ID\",\"parse_output\":\"integer_conversion\",\"name\":\"campaign_id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Phone\",\"name\":\"phone\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Comments\",\"name\":\"comments\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Time Zone\",\"name\":\"time_zone\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Leadid\",\"name\":\"leadid\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Sfdcid\",\"name\":\"sfdcid\",\"type\":\"string\",\"optional\":false},{\"name\":\"joinURL\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Join URL\"}]",
    "webhook_type": "json"
   },
   "webhook_suffix": "formfills-apj"
  }
 },
 {
  "keyword": "try",
  "number": 2,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {}
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "4f1286a3",
  "provider": "lookup_table",
  "name": "search_entries",
  "skip": false,
  "input": {
   "lookup_table_id": "4195320",
   "parameters": {
    "col3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"campaign_id\"]}')}"
   }
  }
 },
 {
  "keyword": "if",
  "number": 4,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"4f1286a3\",\"path\":[\"entries\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "equals_to",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "stop",
  "number": 5,
  "as": "94bcf104",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "stop_with_error": "false"
  }
 },
 {
  "keyword": "action",
  "number": 6,
  "as": "4cd73a31",
  "provider": "google_sheets",
  "name": "search_spreadsheet_rows_v4_new",
  "skip": false,
  "input": {
   "column_headers": "Company\nFirst Name\nLast Name\nJob Title\nEmail Address\nPhone\nDietary Restrictions\nID\nCal Invite Sent?\nIf Dietary Restriction is \"Other\"\nType\nNotes\nStatus",
   "count": "400",
   "data": {
    "col_Email Address": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"email\"]}')}"
   },
   "sheet_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"4f1286a3\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col5\"]}')}",
   "spreadsheet_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"4f1286a3\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col4\"]}')}",
   "team_drives": "0AI0ByO7dMypuUk9PVA/0AI0ByO7dMypuUk9PVA"
  }
 },
 {
  "keyword": "action",
  "number": 7,
  "as": "33035003",
  "provider": "workato_service",
  "name": "call_service",
  "skip": false,
  "input": {
   "flow_id": "45178540",
   "request": {
    "lead_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"leadid\"]}')}"
   }
  }
 },
 {
  "keyword": "action",
  "number": 8,
  "as": "f865207a",
  "provider": "workato_service",
  "name": "call_service",
  "skip": false,
  "input": {
   "flow_id": "45178537",
   "request": {
    "account_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"33035003\",\"path\":[\"reply\", \"SFDC\", \"account_id\"]}')}",
    "contact_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"33035003\",\"path\":[\"reply\", \"SFDC\", \"contact_id\"]}')}",
    "lead_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"33035003\",\"path\":[\"reply\", \"SFDC\", \"lead_id\"]}')}"
   }
  }
 },
 {
  "keyword": "action",
  "number": 9,
  "as": "46e3f07e",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "account_type": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"f865207a\",\"path\":[\"reply\",\"record_type\"]}').presence or \"New Lead\""
    },
    "schema": "[{\"name\":\"account_type\",\"type\":\"string\",\"optional\":true,\"label\":\"Account Type\",\"details\":{\"real_name\":\"Account Type\"},\"control_type\":\"text\"}]"
   }
  }
 },
 {
  "keyword": "if",
  "number": 10,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"4cd73a31\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}",
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
  "number": 11,
  "as": "fb8e9257",
  "provider": "google_sheets",
  "name": "update_row_v4_new",
  "skip": false,
  "input": {
   "column_headers": "Company\nFirst Name\nLast Name\nJob Title\nEmail Address\nPhone\nDietary Restrictions\nID\nCal Invite Sent?\nIf Dietary Restriction is \"Other\"\nType\nNotes\nStatus",
   "data": {
    "col_Cal Invite Sent?": "Sent (If Accepted)",
    "col_Company": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"33035003\",\"path\":[\"reply\", \"Company\", \"company\"]}')}",
    "col_Dietary Restrictions": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"33035003\",\"path\":[\"reply\", \"MKTO\", \"dietary_restrictions\"]}')}",
    "col_Email Address": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"email\"]}')}",
    "col_First Name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"firstname\"]}')}",
    "col_If Dietary Restriction is \"Other\"": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"33035003\",\"path\":[\"reply\", \"Lead\", \"form_response\"]}')}",
    "col_Job Title": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"33035003\",\"path\":[\"reply\", \"Lead\", \"job_title\"]}')}",
    "col_Last Name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"lastname\"]}')}",
    "col_Phone": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"33035003\",\"path\":[\"reply\", \"Lead\", \"phone\"]}')}",
    "col_Status": "Waitlisted",
    "col_Type": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"46e3f07e\",\"path\":[\"account_type\"]}')}"
   },
   "row_number": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"4cd73a31\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"row_number\"]}')}",
   "sheet_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"4cd73a31\",\"path\":[\"sheet\"]}')}",
   "spreadsheet_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"4cd73a31\",\"path\":[\"spreadsheet_id\"]}')}",
   "team_drives": "0AI0ByO7dMypuUk9PVA/0AI0ByO7dMypuUk9PVA"
  }
 },
 {
  "keyword": "else",
  "number": 12,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {}
 },
 {
  "keyword": "action",
  "number": 13,
  "as": "98f30966",
  "provider": "google_sheets",
  "name": "add_spreadsheet_row_v4",
  "skip": false,
  "input": {
   "column_headers": "Company\nFirst Name\nLast Name\nJob Title\nEmail Address\nPhone\nDietary Restrictions\nID\nCal Invite Sent?\nIf Dietary Restriction is \"Other\"\nType\nNotes\nStatus",
   "columns": {
    "col_Cal Invite Sent?": "Sent (If Accepted)",
    "col_Company": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"33035003\",\"path\":[\"reply\", \"Company\", \"company\"]}')}",
    "col_Dietary Restrictions": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"33035003\",\"path\":[\"reply\", \"MKTO\", \"dietary_restrictions\"]}')}",
    "col_Email Address": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"email\"]}')}",
    "col_First Name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"firstname\"]}')}",
    "col_ID": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"leadid\"]}')}",
    "col_If Dietary Restriction is \"Other\"": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"33035003\",\"path\":[\"reply\", \"Lead\", \"form_response\"]}')}",
    "col_Job Title": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"33035003\",\"path\":[\"reply\", \"Lead\", \"job_title\"]}')}",
    "col_Last Name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"lastname\"]}')}",
    "col_Phone": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"33035003\",\"path\":[\"reply\", \"Lead\", \"phone\"]}')}",
    "col_Status": "Waitlisted",
    "col_Type": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"46e3f07e\",\"path\":[\"account_type\"]}')}"
   },
   "is_top_left": "false",
   "sheet_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"4cd73a31\",\"path\":[\"sheet\"]}')}",
   "spreadsheet_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"4cd73a31\",\"path\":[\"spreadsheet_id\"]}')}",
   "team_drives": "0AI0ByO7dMypuUk9PVA/0AI0ByO7dMypuUk9PVA"
  }
 },
 {
  "keyword": "action",
  "number": 14,
  "as": "35a6b894",
  "provider": "slack_bot",
  "name": "post_bot_message",
  "skip": false,
  "input": {
   "attachment_buttons": [
    {
     "bot_command": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"4f1286a3\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col7\"]}')}",
     "params": "operation: Registered leadid: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"leadid\"]}')} email: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"email\"]}')}",
     "title": "Accept"
    },
    {
     "bot_command": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"4f1286a3\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col7\"]}')}",
     "params": "operation: Rejected leadid: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"leadid\"]}')} email: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"email\"]}')}",
     "title": "Reject"
    }
   ],
   "attachment_fields": [
    {
     "title": "Name",
     "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"firstname\"]}')} #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"lastname\"]}')}"
    },
    {
     "title": "Email",
     "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"email\"]}')}"
    },
    {
     "title": "Company Name",
     "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"33035003\",\"path\":[\"reply\", \"Company\", \"company\"]}')}"
    },
    {
     "title": "Job Title",
     "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"33035003\",\"path\":[\"reply\", \"Lead\", \"job_title\"]}')}"
    },
    {
     "title": "Phone Number",
     "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"33035003\",\"path\":[\"reply\", \"Lead\", \"phone\"]}')}"
    }
   ],
   "channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"4f1286a3\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col6\"]}')}",
   "message": {
    "color": "good",
    "title": "New Registrant for #{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"4f1286a3\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col2\"]}')}",
    "title_link": "https://docs.google.com/spreadsheets/d/#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"4cd73a31\",\"path\":[\"spreadsheet_id\"]}')}/edit#gid=0"
   }
  }
 },
 {
  "keyword": "catch",
  "number": 15,
  "as": "36d3b7d0",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "max_retry_count": "3",
   "retry_interval": "10"
  }
 },
 {
  "keyword": "action",
  "number": 16,
  "as": "50073cae",
  "provider": "workato_service",
  "name": "call_service",
  "skip": false,
  "input": {
   "flow_id": "45178280",
   "request": {
    "error_message": "(#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"firstname\"]}')} #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"lastname\"]}')} - #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"email\"]}')})#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"36d3b7d0\",\"path\":[\"message\"]}')}",
    "job_id": "#{_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_id\"]}')}",
    "job_url": "#{_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_url\"]}')}",
    "recipe_id": "#{_dp('{\"pill_type\":\"job_context\",\"path\":[\"recipe_id\"]}')}",
    "stop_recipe": "false"
   }
  }
 },
 {
  "keyword": "stop",
  "number": 17,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "stop_reason": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"36d3b7d0\",\"path\":[\"message\"]}')}",
   "stop_with_error": "true"
  }
 }
]
'''

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "google_sheets.search_spreadsheet_rows_v4_new",
    "workato_service.call_service",
    "workato_runtime.declare_variable",
    "google_sheets.update_row_v4_new",
    "google_sheets.add_spreadsheet_row_v4",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "google_sheets.search_spreadsheet_rows_v4_new",
    "workato_service.call_service",
    "google_sheets.update_row_v4_new",
    "google_sheets.add_spreadsheet_row_v4",
    "slack.post_message",
]
SEED_SECTIONS = {"lookup_table", "sheets", "workato_service_replies"}
EXPECT_KEYS = ("executed_action_count", "tools", "tool_expectations", "stopped")
OPTIONAL_EXPECT_KEYS = {
    "case",
    "stop_step_number",
    "account_type",
    "slack_text",
    "final_sheet_rows",
    "catch_message",
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
    if isinstance(node.get("filter"), dict):
        pin["filter"] = node["filter"]
    out = [pin]
    for child in node.get("block") or []:
        if isinstance(child, dict):
            out.extend(_structure(child))
    return out


def validate_118489191(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_118489191(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118489191(raw)
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
    expect = data.get("expect")
    force = data.get("force_action_error")
    _require_force_shape(force, data)
    _require_expect_shape(expect, force)
    _require_lookup_section(seed_in.get("lookup_table"))
    tools_expected = expect.get("tools") or []
    needs_sheets = "google_sheets.search_spreadsheet_rows_v4_new" in tools_expected
    sheets_section = seed_in.get("sheets")
    if needs_sheets != isinstance(sheets_section, dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets must be present exactly when the variant "
            f"expects the sheets search to execute (needs_sheets={needs_sheets})"
        )
    replies_section = seed_in.get("workato_service_replies")
    needs_replies = "workato_service.call_service" in tools_expected
    if needs_replies != isinstance(replies_section, dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_service_replies must be present exactly when "
            f"the variant expects call_service to execute (needs_replies={needs_replies})"
        )
    if replies_section is not None:
        _require_replies_section(replies_section, force)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": deepcopy(expect),
        "lookup_table": deepcopy(seed_in["lookup_table"]),
    }
    if isinstance(sheets_section, dict):
        _require_sheets_section(sheets_section, trigger, expect)
        if not ctx.env.sheets_spreadsheet_id or not ctx.env.sheets_tab:
            raise RuntimeError("missing SHEETS_SPREADSHEET_ID / SHEETS_TAB; refusing to guess")
        seed_response = ctx.tools.call("harness.google_sheets.seed_rows", {"sheets": sheets_section})
        if not seed_response.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Google Sheets seed failed: {seed_response}")
        out["sheets"] = deepcopy(sheets_section)
        out["sheets_seed_response"] = seed_response
    if replies_section is not None:
        out["workato_service_replies"] = deepcopy(replies_section)
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_118489191(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118489191(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
    if "slack.post_message" in (seed["expect"].get("tools") or []) and not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect"),
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    details["initial_snapshot"] = _snapshot(ctx, seed)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    details["raw_execution"] = raw_execution
    details["ground_truth"] = _ground_truth(raw_execution)
    details["final_snapshot"] = _snapshot(ctx, seed)
    # Cleanup per the cleanup principle: the seed fully overwrites the
    # benchmark tab on every run and the Slack post is an ordinary observable
    # post that is never re-read, deleted, or verified live afterwards -- no
    # cleanup step is required for deterministic reruns.
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_118489191(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {"payload"} or not isinstance(trigger.get("payload"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'payload': {{...}}}}"
        )
    payload = trigger["payload"]
    extra = sorted(set(payload) - set(PAYLOAD_KEYS) - {"joinURL"})
    if extra:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger payload has undeclared fields: {extra}")
    for key in PAYLOAD_KEYS:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger payload.{key} must be a non-empty string "
                "(the payload schema marks every field required)"
            )
    if "@" not in str(payload.get("email")):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger payload.email must be a real address")


def _require_lookup_section(section: Any) -> None:
    if not isinstance(section, dict) or not isinstance(section.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.lookup_table.tables")
    if sorted(section["tables"]) != [LOOKUP_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must declare exactly table {LOOKUP_TABLE_ID}"
        )
    rows = section["tables"][LOOKUP_TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the events table {LOOKUP_TABLE_ID} must be a non-empty "
            "explicit list (a zero-match variant seeds non-matching rows, never an "
            "implicit empty table)"
        )
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} lookup rows must be objects")
        for col in ("col2", "col3", "col6", "col7"):
            if not str(row.get(col) or "").strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} lookup row needs a non-empty {col} "
                    "(event name / campaign id / slack channel / bot command)"
                )
        for col in ("col4", "col5"):
            if not isinstance(row.get(col), str):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} lookup row needs an explicit string {col} "
                    "(spreadsheet id / sheet name; live calls are env-redirected)"
                )


def _require_sheets_section(section: dict[str, Any], trigger: dict[str, Any], expect: dict[str, Any]) -> None:
    if section.get("headers") != SHEET_HEADERS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets.headers must pin the 13 raw column headers "
            f"exactly: {SHEET_HEADERS}"
        )
    rows = section.get("rows")
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} seed.sheets.rows must be an explicit list")
    email = str(trigger["payload"].get("email"))
    matches = 0
    for row in rows:
        if not isinstance(row, dict) or not set(row) <= set(SHEET_HEADERS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed.sheets rows must only use the declared headers: {row!r}"
            )
        if not str(row.get("Email Address") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded sheet row needs an explicit Email Address "
                "(the search key column)"
            )
        if str(row.get("Email Address")) == email:
            matches += 1
    update_expected = "google_sheets.update_row_v4_new" in (expect.get("tools") or [])
    if update_expected and matches == 0:
        raise RuntimeError(
            f"recipe {RECIPE_ID} update variants must seed the registrant row "
            f"(no seeded row carries Email Address {email!r})"
        )
    if not update_expected and matches:
        raise RuntimeError(
            f"recipe {RECIPE_ID} add variants must not seed a row matching the "
            f"registrant email {email!r}"
        )


def _require_replies_section(section: dict[str, Any], force: Any) -> None:
    unexpected = sorted(set(section) - SERVICE_REPLY_STEPS)
    if unexpected:
        raise RuntimeError(
            f"recipe {RECIPE_ID} workato_service_replies must be keyed by the call_service "
            f"step as-ids {sorted(SERVICE_REPLY_STEPS)}; got extra {unexpected}"
        )
    if force is not None:
        if sorted(section) != ["50073cae"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} forced-error variants seed exactly the 50073cae catch "
                f"notifier reply; got {sorted(section)}"
            )
        if not isinstance(section["50073cae"], dict):
            raise RuntimeError(f"recipe {RECIPE_ID} the 50073cae reply must be an object")
        return
    if sorted(section) != ["33035003", "f865207a"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} happy-path variants seed exactly the 33035003 + f865207a "
            f"replies; got {sorted(section)}"
        )
    lead_reply = section["33035003"]
    if not isinstance(lead_reply, dict) or not {"Lead", "Company", "MKTO", "SFDC"} <= set(lead_reply):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the 33035003 reply must carry Lead/Company/MKTO/SFDC objects"
        )
    sfdc = lead_reply.get("SFDC")
    if not isinstance(sfdc, dict) or not {"account_id", "contact_id", "lead_id"} <= set(sfdc):
        raise RuntimeError(
            f"recipe {RECIPE_ID} 33035003 reply.SFDC must carry account_id/contact_id/lead_id "
            "(the f865207a request dereferences them)"
        )
    lead = lead_reply.get("Lead")
    if not isinstance(lead, dict) or not {"form_response", "job_title", "phone"} <= set(lead):
        raise RuntimeError(
            f"recipe {RECIPE_ID} 33035003 reply.Lead must carry form_response/job_title/phone"
        )
    if not isinstance(lead_reply.get("Company"), dict) or "company" not in lead_reply["Company"]:
        raise RuntimeError(f"recipe {RECIPE_ID} 33035003 reply.Company must carry company")
    if not isinstance(lead_reply.get("MKTO"), dict) or "dietary_restrictions" not in lead_reply["MKTO"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} 33035003 reply.MKTO must carry dietary_restrictions"
        )
    record_reply = section["f865207a"]
    if not isinstance(record_reply, dict) or "record_type" not in record_reply or not isinstance(
        record_reply["record_type"], str
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the f865207a reply must carry an explicit string record_type "
            "('' exercises the presence-or 'New Lead' arm)"
        )


def _require_force_shape(force: Any, data: dict[str, Any]) -> None:
    if force is None:
        return
    if not isinstance(force, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error must be an object")
    if str(force.get("step_as") or "") not in FORCEABLE_STEPS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error.step_as must be one of {sorted(FORCEABLE_STEPS)}"
        )
    if not str(force.get("error") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error.error must be a non-empty message")
    job_context = data.get("job_context")
    if not isinstance(job_context, dict) or not all(
        str(job_context.get(key) or "").strip() for key in ("job_id", "job_url", "recipe_id")
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} forced-error variants must pin job_context "
            "job_id/job_url/recipe_id (the catch notifier dereferences all three)"
        )


def _require_expect_shape(expect: Any, force: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(set(expect) - set(EXPECT_KEYS) - OPTIONAL_EXPECT_KEYS)
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has unexpected keys: {unknown}")
    tools = expect.get("tools")
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tools, list) or not isinstance(tool_expectations, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools/tool_expectations must be lists")
    if len(tools) != len(tool_expectations):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry"
        )
    unknown_tools = sorted(set(tools) - set(ALLOWED_TOOLS))
    if unknown_tools:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools has unknown tools: {unknown_tools}")
    if not isinstance(expect.get("stopped"), bool):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.stopped must be a bool")
    if not tools or tools[0] != "lookup_table.search_entries":
        raise RuntimeError(f"recipe {RECIPE_ID} every path starts with the step-3 lookup search")
    if expect["stopped"]:
        if str(expect.get("stop_step_number")) not in {str(GRACEFUL_STOP_STEP), str(ERROR_STOP_STEP)}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} stopped variants must pin stop_step_number "
                f"{GRACEFUL_STOP_STEP} (graceful) or {ERROR_STOP_STEP} (error)"
            )
    elif "stop_step_number" in expect:
        raise RuntimeError(f"recipe {RECIPE_ID} non-stopped variants must not pin stop_step_number")
    if force is not None:
        if not expect["stopped"] or str(expect.get("stop_step_number")) != str(ERROR_STOP_STEP):
            raise RuntimeError(
                f"recipe {RECIPE_ID} forced-error variants stop with error at step {ERROR_STOP_STEP}"
            )
        if str(expect.get("catch_message") or "") != str(force.get("error")):
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.catch_message must equal the forced error message"
            )
    elif "catch_message" in expect:
        raise RuntimeError(f"recipe {RECIPE_ID} only forced-error variants pin catch_message")
    slack_expected = "slack.post_message" in tools
    if slack_expected != bool(str(expect.get("slack_text") or "")):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.slack_text must pin the exact rendered message "
            "exactly when the slack post executes"
        )
    write_expected = (
        "google_sheets.update_row_v4_new" in tools
        or "google_sheets.add_spreadsheet_row_v4" in tools
    )
    if write_expected:
        if not isinstance(expect.get("final_sheet_rows"), list) or not expect["final_sheet_rows"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} sheet-writing variants must pin expect.final_sheet_rows "
                "(the exact FORMATTED read-back of the whole benchmark tab)"
            )
        if not isinstance(expect.get("account_type"), str) or not expect["account_type"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} sheet-writing variants must pin expect.account_type "
                "(the step-9 presence-or result)"
            )


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "lookup_table": (ctx.tools.call("harness.lookup_table.snapshot", {}) or {}).get("lookup_table"),
    }
    if isinstance(seed.get("sheets"), dict):
        out["google_sheets"] = ctx.tools.call("harness.google_sheets.snapshot", {})
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
