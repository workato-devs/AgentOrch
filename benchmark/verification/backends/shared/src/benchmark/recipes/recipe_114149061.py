from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_114149061


RECIPE_ID = "114149061"
SEED_TYPE = "webhook_on_demand_view_slack_notify_variant"
TRACK = "live_salesforce_slack_webhook_on_demand_view"
TRIGGER_PROVIDER = "workato_webhooks"
TRIGGER_NAME = "new_event"
TRIGGER_AS = "a933e72a"
LOOKUP_TABLE_ID = "4088652"
CA_SOBJECT = "Campaign_Activity__c"
CATCH_STEP_AS = "36d3b7d0"
GRACEFUL_STOP_STEP = 3
ERROR_STOP_STEP = 12
FORCEABLE_STEPS = {"e9c58b87"}
SERVICE_REPLY_STEPS = {"313a1274", "503c4462", "50073cae"}
IDLER_STEP_AS = "313a1274"
COLLAB_STEP_AS = "503c4462"
ERROR_NOTIFIER_STEP_AS = "50073cae"
SLACK_TITLE_PREFIX = "New On-Demand View for "
# The 20 hardcoded MKTO campaign ids of the trigger's runtime OR-filter
# (raw trigger "filter"; the batch_B triage entry MISSED this filter — same
# situation as the recipe_130704674 precedent). A payload campaign_id outside
# this list runs ZERO actions (trigger_filter_matched false; variant_00).
CAMPAIGN_FILTER_IDS = (
    "36346", "36335", "36337", "36334", "36338", "36344", "36336", "36341",
    "36333", "36339", "36331", "36345", "36342", "36343", "36348", "36329",
    "36330", "36332", "36340", "36347",
)
PAYLOAD_KEYS = (
    "firstname", "lastname", "email", "company", "campaign_id",
    "phone", "comments", "time_zone", "leadid", "sfdcid",
)
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")

# workato_webhooks.new_event (as a933e72a, webhook_suffix 'formfills-apj',
# JSON payload firstname/lastname/email/company/campaign_id/phone/comments/
# time_zone/leadid/sfdcid [, joinURL]) with a runtime trigger filter:
# payload.campaign_id equals one of the 20 CAMPAIGN_FILTER_IDS (or-compound).
# Body:
#   2  IF payload.email contains '@workato.com' OR contains 'test.com'
#      -> 3 STOP (as b3655a16, stop_with_error false) — internal/test
#      registrations are dropped gracefully.
#   4  TRY:
#      5  workato_service.call_service 313a1274 (flow 45178314 'Flexi Idler',
#         request {Secs:'480'}) — Workato-internal; reply is deterministic
#         seed state (production waits 480s; the seeded reply {secs_waited:
#         480.0} returns instantly and is never dereferenced downstream)
#      6  lookup_table.search_entries a45d596c (table 4088652 'JPN Automate
#         On-Demand Lookup': col1 SFDC Campaign ID, col2 SFDC/MKTO Camp.
#         Name, col3 MKTO Campaign ID) by col3 = payload.campaign_id
#      7  salesforce.search_sobjects e9c58b87 (LIVE): Campaign_Activity__c,
#         field_list Id, limit 200, field filters Campaign__c =
#         a45d596c.entries[current_item].entry.col1 (current_item outside a
#         foreach = FIRST entry), Email__c = payload.email
#      8  workato_service.call_service 503c4462 (flow 45178540 'Get
#         Collaboration Tools', request {lead_id: payload.leadid}) -> reply
#         {Lead:{first_name,last_name,email,job_title,...},
#          Company:{company,...}}
#      9  slack_bot.post_bot_message 35a6b894 (LIVE; channel literal
#         'C02GPT83HAT' -> SLACK_CHANNEL_OVERRIDE). Rendered text = title
#         'New On-Demand View for #{a45d596c col2} <@U05KPK5L8MS>' + four
#         'Title: value' attachment-field lines (Name/Email/Company Name/
#         Job Title from the 503c4462 reply). message.color and
#         message.title_link are metadata slack_text does NOT render — the
#         title_link (the ONLY consumer of the e9c58b87 output) affects no
#         observable text, but the SF search still executes live for a
#         faithful trace.
#   10 CATCH 36d3b7d0 (max_retry_count 3, retry_interval 10 — the engine
#      executes the try body once and the catch once; NO retried attempts
#      appear in the trace, retry config is pinned at validate time only):
#      11 workato_service.call_service 50073cae (flow 45178280, request
#         {error_message '(#{firstname} #{lastname} - #{email})#{catch
#         .message}', job_id/job_url/recipe_id job_context pills,
#         stop_recipe 'false'})
#      12 STOP stop_with_error true, stop_reason = catch.message
#
# Branch-mapping notes (recorded per benmark_rules):
# - variant_00 trigger_filter_no_match: campaign_id '40399' is outside the
#   20-id runtime filter -> trigger_filter_matched false, ZERO actions, no
#   stop row (the body never starts).
# - variant_01 internal_email_stop: email contains '@workato.com' (OR leg 1)
#   -> graceful STOP 3 after zero actions.
# - variant_02 testcom_stop: email contains 'test.com' (OR leg 2, distinct
#   domain proves the second leg alone) -> same graceful STOP 3.
# - variant_03 happy_path_post: both service replies seeded, lookup row
#   matches campaign_id 36335, ONE benchmark-owned live Campaign_Activity__c
#   matches both field filters (result_count 1), slack post to the override
#   channel with the exact rendered text.
# - variant_04 catch_error_service_stop: forced action error on e9c58b87
#   (raised BEFORE arg resolution, so no salesforce trace row and no live SF
#   seed is needed) -> catch 36d3b7d0 -> error-notifier call_service with the
#   '(first last - email)<catch message>' interpolation + pinned job_context
#   -> STOP 12 with error.
#
# Backends: salesforce LIVE (Campaign_Activity__c physical==logical, mdapi
# org fact; custom fields via schema-in-seed ensure_custom_field; the owned
# record is deleted in finally and leftovers fail the run); slack LIVE
# (ordinary observable post, never re-read -> no cleanup per the cleanup
# principle); lookup_table + workato_service are Workato-internal
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
    "payload_schema": "[{\"control_type\":\"text\",\"label\":\"Firstname\",\"name\":\"firstname\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Lastname\",\"name\":\"lastname\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Email\",\"name\":\"email\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Company\",\"name\":\"company\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Campaign ID\",\"parse_output\":\"integer_conversion\",\"name\":\"campaign_id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Phone\",\"name\":\"phone\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Comments\",\"name\":\"comments\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Time Zone\",\"name\":\"time_zone\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Leadid\",\"name\":\"leadid\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Sfdcid\",\"name\":\"sfdcid\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Join URL\",\"name\":\"joinURL\",\"type\":\"string\",\"optional\":true}]",
    "webhook_type": "json"
   },
   "webhook_suffix": "formfills-apj"
  },
  "filter": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"campaign_id\"]}')}",
     "operand": "equals_to",
     "rhs": "36346"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"campaign_id\"]}')}",
     "operand": "equals_to",
     "rhs": "36335"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"campaign_id\"]}')}",
     "operand": "equals_to",
     "rhs": "36337"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"campaign_id\"]}')}",
     "operand": "equals_to",
     "rhs": "36334"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"campaign_id\"]}')}",
     "operand": "equals_to",
     "rhs": "36338"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"campaign_id\"]}')}",
     "operand": "equals_to",
     "rhs": "36344"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"campaign_id\"]}')}",
     "operand": "equals_to",
     "rhs": "36336"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"campaign_id\"]}')}",
     "operand": "equals_to",
     "rhs": "36341"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"campaign_id\"]}')}",
     "operand": "equals_to",
     "rhs": "36333"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"campaign_id\"]}')}",
     "operand": "equals_to",
     "rhs": "36339"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"campaign_id\"]}')}",
     "operand": "equals_to",
     "rhs": "36331"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"campaign_id\"]}')}",
     "operand": "equals_to",
     "rhs": "36345"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"campaign_id\"]}')}",
     "operand": "equals_to",
     "rhs": "36342"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"campaign_id\"]}')}",
     "operand": "equals_to",
     "rhs": "36343"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"campaign_id\"]}')}",
     "operand": "equals_to",
     "rhs": "36348"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"campaign_id\"]}')}",
     "operand": "equals_to",
     "rhs": "36329"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"campaign_id\"]}')}",
     "operand": "equals_to",
     "rhs": "36330"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"campaign_id\"]}')}",
     "operand": "equals_to",
     "rhs": "36332"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"campaign_id\"]}')}",
     "operand": "equals_to",
     "rhs": "36340"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"campaign_id\"]}')}",
     "operand": "equals_to",
     "rhs": "36347"
    }
   ],
   "operand": "or",
   "type": "compound"
  }
 },
 {
  "keyword": "if",
  "number": 2,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"email\"]}')}",
     "operand": "contains",
     "rhs": "@workato.com"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"email\"]}')}",
     "operand": "contains",
     "rhs": "test.com"
    }
   ],
   "operand": "or",
   "type": "compound"
  }
 },
 {
  "keyword": "stop",
  "number": 3,
  "as": "b3655a16",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "stop_with_error": "false"
  }
 },
 {
  "keyword": "try",
  "number": 4,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {}
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "313a1274",
  "provider": "workato_service",
  "name": "call_service",
  "skip": false,
  "input": {
   "flow_id": "45178314",
   "request": {
    "Secs": "480"
   }
  }
 },
 {
  "keyword": "action",
  "number": 6,
  "as": "a45d596c",
  "provider": "lookup_table",
  "name": "search_entries",
  "skip": false,
  "input": {
   "lookup_table_id": "4088652",
   "parameters": {
    "col3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"campaign_id\"]}')}"
   }
  }
 },
 {
  "keyword": "action",
  "number": 7,
  "as": "e9c58b87",
  "provider": "salesforce",
  "name": "search_sobjects",
  "skip": false,
  "input": {
   "Campaign__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"a45d596c\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col1\"]}')}",
   "Email__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\",\"path\":[\"payload\", \"email\"]}')}",
   "field_list": "Id",
   "limit": "200",
   "sobject_name": "Campaign_Activity__c"
  }
 },
 {
  "keyword": "action",
  "number": 8,
  "as": "503c4462",
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
  "number": 9,
  "as": "35a6b894",
  "provider": "slack_bot",
  "name": "post_bot_message",
  "skip": false,
  "input": {
   "attachment_fields": [
    {
     "title": "Name",
     "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"503c4462\",\"path\":[\"reply\", \"Lead\", \"first_name\"]}')} #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"503c4462\",\"path\":[\"reply\", \"Lead\", \"last_name\"]}')}"
    },
    {
     "title": "Email",
     "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"503c4462\",\"path\":[\"reply\", \"Lead\", \"email\"]}')}"
    },
    {
     "title": "Company Name",
     "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"503c4462\",\"path\":[\"reply\", \"Company\", \"company\"]}')}"
    },
    {
     "title": "Job Title",
     "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"503c4462\",\"path\":[\"reply\", \"Lead\", \"job_title\"]}')}"
    }
   ],
   "channel": "C02GPT83HAT",
   "message": {
    "color": "good",
    "title": "New On-Demand View for #{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"a45d596c\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col2\"]}')} <@U05KPK5L8MS>",
    "title_link": "https://workato.lightning.force.com/lightning/r/Campaign_Activity__c/#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"e9c58b87\",\"path\":[\"Campaign_Activity__c\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}/view"
   }
  }
 },
 {
  "keyword": "catch",
  "number": 10,
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
  "number": 11,
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
  "number": 12,
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

REQUIRED_SCHEMA: list[dict[str, str]] = [
    {"sobject": CA_SOBJECT, "field": "Campaign__c", "sf_type": "Text"},
    {"sobject": CA_SOBJECT, "field": "Email__c", "sf_type": "Text"},
]

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_service.call_service",
    "lookup_table.search_entries",
    "salesforce.search_records",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "workato_service.call_service",
    "lookup_table.search_entries",
    "salesforce.search_records",
    "slack.post_message",
]
SEED_SECTIONS = {"lookup_table", "workato_service_replies", "salesforce"}
EXPECT_KEYS = (
    "trigger_filter_matched",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "stopped",
)
OPTIONAL_EXPECT_KEYS = {"case", "stop_step_number", "catch_message", "slack_text"}


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


def validate_114149061(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger 'as' changed: {raw.get('as')!r}")
    if not isinstance(raw.get("filter"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger runtime filter is missing")
    filter_rhs = [
        str(cond.get("rhs"))
        for cond in raw["filter"].get("conditions") or []
        if isinstance(cond, dict)
    ]
    if filter_rhs != list(CAMPAIGN_FILTER_IDS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger filter campaign ids changed: {filter_rhs}"
        )
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


def seed_114149061(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_114149061(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    if _TOKEN_RE.search(json.dumps(trigger)):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input must not carry seed ref tokens")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - SEED_SECTIONS)
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    expect = data.get("expect")
    force = data.get("force_action_error")
    _require_force_shape(force, data)
    _require_expect_shape(expect, force, trigger)
    if _TOKEN_RE.search(json.dumps(expect)):
        raise RuntimeError(f"recipe {RECIPE_ID} expect must not carry seed ref tokens")
    _require_lookup_section(seed_in.get("lookup_table"), expect)
    _require_replies_section(seed_in.get("workato_service_replies"), expect, force)
    salesforce_section = seed_in.get("salesforce")
    needs_salesforce = "salesforce.search_records" in (expect.get("tools") or [])
    if needs_salesforce != isinstance(salesforce_section, dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce must be present exactly when the variant "
            f"expects the live Campaign_Activity__c search to execute "
            f"(needs_salesforce={needs_salesforce})"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": deepcopy(expect),
        "lookup_table": deepcopy(seed_in["lookup_table"]),
    }
    if isinstance(seed_in.get("workato_service_replies"), dict):
        out["workato_service_replies"] = deepcopy(seed_in["workato_service_replies"])
    if isinstance(salesforce_section, dict):
        _require_salesforce_section(salesforce_section, trigger, seed_in, expect)
        provision = ctx.tools.call(
            "harness.salesforce.seed_records", {"salesforce": deepcopy(salesforce_section)}
        )
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
        out["salesforce_live"] = deepcopy(provision["state"])
        out["salesforce_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_114149061(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_114149061(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
    if "slack.post_message" in (seed["expect"].get("tools") or []) and not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    if "salesforce.search_records" in (seed["expect"].get("tools") or []) and not isinstance(
        seed.get("salesforce_live"), dict
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
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
        details["initial_snapshot"] = _snapshot(ctx, seed)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx, seed)
    finally:
        if isinstance(seed.get("salesforce_live"), dict):
            cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
            details["cleanup_response"] = cleanup_response
    if isinstance(seed.get("salesforce_live"), dict) and not (cleanup_response or {}).get("ok"):
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
    result["verifier"] = verify_114149061(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {"payload"} or not isinstance(trigger.get("payload"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input must be exactly {{'payload': {{...}}}}")
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
    # payload.campaign_id must be the exact string the lookup col3 key uses
    # (the payload schema carries parse_output integer_conversion, but trigger
    # replay does not re-convert; digits-only avoids '12345' vs 12345 drift).
    if not str(payload.get("campaign_id")).isdigit():
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger payload.campaign_id must be a digits-only string"
        )


def _email_matches_stop_filter(email: str) -> bool:
    return "@workato.com" in email or "test.com" in email


def _require_expect_shape(expect: Any, force: Any, trigger: dict[str, Any]) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(set(expect) - set(EXPECT_KEYS) - OPTIONAL_EXPECT_KEYS)
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has unexpected keys: {unknown}")
    if not isinstance(expect.get("trigger_filter_matched"), bool):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.trigger_filter_matched must be a bool")
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
    payload = trigger["payload"]
    campaign_in_filter = str(payload.get("campaign_id")) in CAMPAIGN_FILTER_IDS
    if expect["trigger_filter_matched"] != campaign_in_filter:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.trigger_filter_matched must agree with the payload "
            f"campaign_id vs the 20-id runtime filter (in_filter={campaign_in_filter})"
        )
    email_stopped = _email_matches_stop_filter(str(payload.get("email")))
    if not expect["trigger_filter_matched"]:
        if tools or int(expect.get("executed_action_count") or 0) != 0 or expect["stopped"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} filter-false variants run zero actions and never stop"
            )
        return
    if expect["stopped"]:
        if str(expect.get("stop_step_number")) not in {str(GRACEFUL_STOP_STEP), str(ERROR_STOP_STEP)}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} stopped variants must pin stop_step_number "
                f"{GRACEFUL_STOP_STEP} (email filter) or {ERROR_STOP_STEP} (catch error)"
            )
    elif "stop_step_number" in expect:
        raise RuntimeError(f"recipe {RECIPE_ID} non-stopped variants must not pin stop_step_number")
    if email_stopped != (expect["stopped"] and str(expect.get("stop_step_number")) == str(GRACEFUL_STOP_STEP)):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the graceful STOP {GRACEFUL_STOP_STEP} fires exactly when the "
            "payload email contains '@workato.com' or 'test.com'"
        )
    if email_stopped and tools:
        raise RuntimeError(f"recipe {RECIPE_ID} email-stop variants run zero actions")
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
    if slack_expected and not str(expect["slack_text"]).startswith(SLACK_TITLE_PREFIX):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.slack_text must start with the rendered title "
            f"{SLACK_TITLE_PREFIX!r}"
        )
    if not email_stopped and (not tools or tools[0] != "workato_service.call_service"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} every try-body path starts with the step-5 'Flexi Idler' call"
        )


def _require_lookup_section(section: Any, expect: dict[str, Any]) -> None:
    if not isinstance(section, dict) or not isinstance(section.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.lookup_table.tables")
    if sorted(section["tables"]) != [LOOKUP_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must declare exactly table {LOOKUP_TABLE_ID}"
        )
    rows = section["tables"][LOOKUP_TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the on-demand lookup table {LOOKUP_TABLE_ID} must be a "
            "non-empty explicit list"
        )
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} lookup rows must be objects")
        for col in ("col1", "col2", "col3"):
            if not str(row.get(col) or "").strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} lookup row needs a non-empty {col} "
                    "(SFDC campaign id / campaign name / MKTO campaign id)"
                )


def _require_replies_section(section: Any, expect: dict[str, Any], force: Any) -> None:
    expected_calls = [tool for tool in expect.get("tools") or [] if tool == "workato_service.call_service"]
    if not expected_calls:
        if section is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} variants that never reach a call_service must not seed "
                "workato_service_replies"
            )
        return
    if not isinstance(section, dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} variants reaching call_service must seed workato_service_replies"
        )
    unexpected = sorted(set(section) - SERVICE_REPLY_STEPS)
    if unexpected:
        raise RuntimeError(
            f"recipe {RECIPE_ID} workato_service_replies must be keyed by the call_service "
            f"step as-ids {sorted(SERVICE_REPLY_STEPS)}; got extra {unexpected}"
        )
    if force is not None:
        if sorted(section) != sorted([IDLER_STEP_AS, ERROR_NOTIFIER_STEP_AS]):
            raise RuntimeError(
                f"recipe {RECIPE_ID} forced-error variants seed exactly the {IDLER_STEP_AS} idler "
                f"+ {ERROR_NOTIFIER_STEP_AS} error-notifier replies; got {sorted(section)}"
            )
    else:
        if sorted(section) != sorted([IDLER_STEP_AS, COLLAB_STEP_AS]):
            raise RuntimeError(
                f"recipe {RECIPE_ID} happy-path variants seed exactly the {IDLER_STEP_AS} idler "
                f"+ {COLLAB_STEP_AS} collaboration-tools replies; got {sorted(section)}"
            )
        collab = section[COLLAB_STEP_AS]
        if not isinstance(collab, dict) or not isinstance(collab.get("Lead"), dict) or not isinstance(
            collab.get("Company"), dict
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} the {COLLAB_STEP_AS} reply must carry Lead and Company objects"
            )
        for key in ("first_name", "last_name", "email", "job_title"):
            if not str(collab["Lead"].get(key) or "").strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} the {COLLAB_STEP_AS} reply.Lead needs a non-empty {key} "
                    "(the slack attachment fields dereference it)"
                )
        if not str(collab["Company"].get("company") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} the {COLLAB_STEP_AS} reply.Company needs a non-empty company"
            )
    idler = section[IDLER_STEP_AS]
    if not isinstance(idler, dict) or idler.get("secs_waited") != 480.0:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the {IDLER_STEP_AS} 'Flexi Idler' reply must be "
            "{'secs_waited': 480.0} verbatim (production waits 480s; the seeded reply returns "
            "instantly)"
        )


def _require_salesforce_section(
    section: dict[str, Any], trigger: dict[str, Any], seed_in: dict[str, Any], expect: dict[str, Any]
) -> None:
    if section.get("schema") != REQUIRED_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare the canonical "
            "REQUIRED_SCHEMA verbatim (ensure_custom_field on Campaign__c/Email__c)"
        )
    unexpected = sorted(set(section) - {"schema", "records"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce has unexpected keys: {unexpected}")
    records = section.get("records")
    if not isinstance(records, list) or len(records) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.records must create exactly one owned "
            f"{CA_SOBJECT} record (the happy path pins result_count 1)"
        )
    lookup_rows = seed_in["lookup_table"]["tables"][LOOKUP_TABLE_ID]
    campaign_id = str(trigger["payload"].get("campaign_id"))
    matched = [row for row in lookup_rows if str(row.get("col3")) == campaign_id]
    if len(matched) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} live-search variants must seed exactly one lookup row whose "
            f"col3 matches payload.campaign_id {campaign_id!r} (the SF filter reads its col1)"
        )
    record = records[0]
    if not isinstance(record, dict) or str(record.get("sobject") or "") != CA_SOBJECT:
        raise RuntimeError(f"recipe {RECIPE_ID} the seeded record must be a {CA_SOBJECT}")
    fields = record.get("fields")
    if not isinstance(fields, dict) or not str(fields.get("Name") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} the seeded CA record must set an explicit Name")
    if str(fields.get("Campaign__c") or "") != str(matched[0].get("col1")):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the seeded CA Campaign__c must equal the matched lookup row's "
            "col1 (the step-7 field filter reads it)"
        )
    if str(fields.get("Email__c") or "") != str(trigger["payload"].get("email")):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the seeded CA Email__c must equal payload.email "
            "(the step-7 field filter reads it)"
        )
    extra_fields = sorted(set(fields) - {"Name", "Campaign__c", "Email__c"})
    if extra_fields:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seeded CA record carries fields the recipe never reads: {extra_fields}"
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


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "lookup_table": (ctx.tools.call("harness.lookup_table.snapshot", {}) or {}).get("lookup_table"),
    }
    if isinstance(seed.get("salesforce_live"), dict):
        salesforce_snapshot = ctx.tools.call("harness.salesforce.snapshot", {})
        out["salesforce"] = salesforce_snapshot.get("salesforce")
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
