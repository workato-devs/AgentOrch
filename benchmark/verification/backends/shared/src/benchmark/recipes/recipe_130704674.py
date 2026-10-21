from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_130704674


RECIPE_ID = "130704674"
SEED_TYPE = "salesforce_campaign_activity_region_mapping_variant"
TRACK = "live_salesforce_campaign_activity_region_mapping"
TRIGGER_PROVIDER = "salesforce"
TRIGGER_NAME = "new_custom_object"
TRIGGER_AS = "ffce87c2"
CA_SOBJECT = "Campaign_Activity__c"
CAMPAIGN_FILTER_ID = "7011N000000xp4nQAA"
CA_ID_TOKEN = "$CA_ID"
NORAM_LOOKUP_ID = "3817174"
INTL_LOOKUP_ID = "3256346"
GET_ENTRY_STEP_AS = "235d3c31"
SERVICE_STEP_AS = "fdb042a9"
_REF_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_SF_ID_RE = re.compile(r"^[a-zA-Z0-9]{15,18}$")

# Salesforce new Campaign_Activity__c region-mapping recipe (trigger as
# ffce87c2, since_offset -3600, 15-field field_list) with a RUNTIME trigger
# filter the batch_B triage entry MISSED:
#   filter: trigger Campaign__c equals_to '7011N000000xp4nQAA' (or-compound
#   with a single condition) — a non-matching Campaign__c runs ZERO actions
#   (trigger_filter_matched false; covered by variant_07).
# Body:
#   2  workato_service.call_service (fdb042a9, flow 45561582 'Flexi Idler',
#      request {Secs:'360'}) — Workato-internal; the reply is deterministic
#      seed state (seed.workato_service_replies['fdb042a9'] = {}, fail-fast)
#      and nothing downstream reads it
#   3  salesforce.search_sobjects (b4c80fea: Campaign_Activity__c, Id =
#      trigger.Id, limit 150, field_list Id/Name/Region__c/
#      Person_Sub_Region__c/Browser_Timezone__c/Person_Country__c) — LIVE
#   4  IF b4c80fea CA[current_item].Browser_Timezone__c starts_with 'America'
#      AND CA[current_item].Region__c blank (current_item outside a foreach =
#      first record):
#      5  lookup_table.search_entries (ba084cef, table 3817174, col1 =
#         trigger.Browser_Timezone__c)
#      6  IF entries size > 0:
#         7  salesforce.update_sobject (6f47b815: id = trigger.Id, Region__c =
#            entries[current_item].entry.col2, Person_Country__c = entry.col3)
#      8  logger.log_message (64869195 'NORAM (US/Canada)') — "skip": true —
#         DISABLED in the raw recipe: reached-but-skipped trace marker only
#      9  STOP (no error)
#   10 TRY: 11 lookup_table.get_entry (235d3c31, table 3256346, col3 =
#      trigger.Browser_Timezone__c)
#   12 CATCH (7bc5859d, retry 0): 13 STOP (no error)
#   14 IF 235d3c31.id present:
#      15 IF b4c80fea CA[current_item].Region__c blank OR
#         CA[current_item].Person_Sub_Region__c blank:
#         16 salesforce.update_sobject (98af47c8: id = trigger.Id,
#            Person_Sub_Region__c = entry.col1, Region__c = entry.col2)
#         17 STOP (no error)
#   otherwise the recipe falls through and ends (no stop marker).
#
# SEMANTICS DIVERGENCE (pinned deliberately, per the batch_B triage flag): the
# engine's lookup get_entry returns {ok: true, entry: None} WITHOUT an id on
# no-match (lookup_table.py get_entry -> _entry_result(None)), so the
# not-found path exits via IF14-false (variant_04, expect.get_entry_no_match).
# Real Workato 'Get entry' ERRORS on not-found — that is why the raw recipe
# wraps step 11 in try/catch -> stop. Under the engine the catch branch is
# reachable only via a forced action failure (variant_05, force_action_error
# on 235d3c31). Both paths exist in the variant set; ground truth follows the
# ENGINE semantics.
#
# Live Salesforce: Campaign_Activity__c physical==logical (mdapi-deployed org
# fact; precedent recipe_118427850). Custom fields via schema-in-seed
# ensure_custom_field (REQUIRED_SCHEMA below): Browser_Timezone__c /
# Person_Sub_Region__c / Person_Country__c (+ Region__c, already ensured by
# the 118427850 seeds — declared here too so this recipe stands alone). The
# seed creates exactly ONE benchmark-owned CA record; the trigger threads its
# live id via the $CA_ID token (trigger AND expect, recipe_97967767
# precedent). Cleanup deletes owned records in finally and fails on leftovers.
# Lookup tables 3817174 / 3256346 are Workato-internal mocks seeded per
# variant and read-only.

_STRUCTURE_PINS_JSON = r'''
[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "ffce87c2",
  "provider": "salesforce",
  "name": "new_custom_object",
  "skip": false,
  "input": {
   "field_list": "Id\nOwnerId\nName\nRegion__c\nPerson_Sub_Region__c\nPerson_Country__c\nCategory__c\nFit__c\nBrowser_Timezone__c\nCampaign__c\nCampaign_Id__c\nCampaign_Member_Id__c\nExtended_Campaign_Activities__c\nPrevious_Campaign_Activity__c\nEmail__c",
   "since_offset": "-3600",
   "sobject_name": "Campaign_Activity__c"
  },
  "filter": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"ffce87c2\",\"path\":[\"Campaign__c\"]}')}",
     "operand": "equals_to",
     "rhs": "7011N000000xp4nQAA"
    }
   ],
   "operand": "or",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "fdb042a9",
  "provider": "workato_service",
  "name": "call_service",
  "skip": false,
  "input": {
   "flow_id": "45561582",
   "request": {
    "Secs": "360"
   }
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "b4c80fea",
  "provider": "salesforce",
  "name": "search_sobjects",
  "skip": false,
  "input": {
   "Id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"ffce87c2\",\"path\":[\"Id\"]}')}",
   "field_list": "Id\nName\nRegion__c\nPerson_Sub_Region__c\nBrowser_Timezone__c\nPerson_Country__c",
   "limit": "150",
   "sobject_name": "Campaign_Activity__c"
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
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"b4c80fea\",\"path\":[\"Campaign_Activity__c\", {\"path_element_type\": \"current_item\"}, \"Browser_Timezone__c\"]}')}",
     "operand": "starts_with",
     "rhs": "America"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"b4c80fea\",\"path\":[\"Campaign_Activity__c\", {\"path_element_type\": \"current_item\"}, \"Region__c\"]}')}",
     "operand": "blank",
     "rhs": ""
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "ba084cef",
  "provider": "lookup_table",
  "name": "search_entries",
  "skip": false,
  "input": {
   "lookup_table_id": "3817174",
   "parameters": {
    "col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"ffce87c2\",\"path\":[\"Browser_Timezone__c\"]}')}"
   }
  }
 },
 {
  "keyword": "if",
  "number": 6,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"ba084cef\",\"path\":[\"entries\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "greater_than",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 7,
  "as": "6f47b815",
  "provider": "salesforce",
  "name": "update_sobject",
  "skip": false,
  "input": {
   "Person_Country__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"ba084cef\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col3\"]}')}",
   "Region__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"ba084cef\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col2\"]}')}",
   "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"ffce87c2\",\"path\":[\"Id\"]}')}",
   "sobject_name": "Campaign_Activity__c"
  }
 },
 {
  "keyword": "action",
  "number": 8,
  "as": "64869195",
  "provider": "logger",
  "name": "log_message",
  "skip": true,
  "input": {
   "message": "NORAM (US/Canada)",
   "user_logs_enabled": "false"
  }
 },
 {
  "keyword": "stop",
  "number": 9,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "stop_with_error": "false"
  }
 },
 {
  "keyword": "try",
  "number": 10,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {}
 },
 {
  "keyword": "action",
  "number": 11,
  "as": "235d3c31",
  "provider": "lookup_table",
  "name": "get_entry",
  "skip": false,
  "input": {
   "lookup_table_id": "3256346",
   "parameters": {
    "col3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"ffce87c2\",\"path\":[\"Browser_Timezone__c\"]}')}"
   }
  }
 },
 {
  "keyword": "catch",
  "number": 12,
  "as": "7bc5859d",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "max_retry_count": "0",
   "retry_interval": "2"
  }
 },
 {
  "keyword": "stop",
  "number": 13,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "stop_with_error": "false"
  }
 },
 {
  "keyword": "if",
  "number": 14,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"235d3c31\",\"path\":[\"id\"]}')}",
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
  "number": 15,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"b4c80fea\",\"path\":[\"Campaign_Activity__c\", {\"path_element_type\": \"current_item\"}, \"Region__c\"]}')}",
     "operand": "blank",
     "rhs": ""
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"b4c80fea\",\"path\":[\"Campaign_Activity__c\", {\"path_element_type\": \"current_item\"}, \"Person_Sub_Region__c\"]}')}",
     "operand": "blank",
     "rhs": ""
    }
   ],
   "operand": "or",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 16,
  "as": "98af47c8",
  "provider": "salesforce",
  "name": "update_sobject",
  "skip": false,
  "input": {
   "Person_Sub_Region__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"235d3c31\",\"path\":[\"entry\", \"col1\"]}')}",
   "Region__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"235d3c31\",\"path\":[\"entry\", \"col2\"]}')}",
   "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"ffce87c2\",\"path\":[\"Id\"]}')}",
   "sobject_name": "Campaign_Activity__c"
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
   "stop_with_error": "false"
  }
 }
]
'''

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

REQUIRED_SCHEMA: list[dict[str, str]] = [
    {"sobject": CA_SOBJECT, "field": "Browser_Timezone__c", "sf_type": "Text"},
    {"sobject": CA_SOBJECT, "field": "Region__c", "sf_type": "Text"},
    {"sobject": CA_SOBJECT, "field": "Person_Sub_Region__c", "sf_type": "Text"},
    {"sobject": CA_SOBJECT, "field": "Person_Country__c", "sf_type": "Text"},
]

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_service.call_service",
    "salesforce.search_records",
    "lookup_table.search_entries",
    "lookup_table.get_entry",
    "salesforce.update_record",
]
ALLOWED_TOOLS: list[str] = [
    "workato_service.call_service",
    "salesforce.search_records",
    "lookup_table.search_entries",
    "lookup_table.get_entry",
    "salesforce.update_record",
]
SEED_SECTIONS = {"salesforce", "lookup_table", "workato_service_replies"}
EXPECT_KEYS = (
    "trigger_filter_matched",
    "tools",
    "tool_expectations",
    "executed_action_count",
    "stopped",
    "catch",
    "logger_skipped",
    "updated",
    "final_ca_fields",
    "final_ca_absent_fields",
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


def validate_130704674(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger 'as' changed: {raw.get('as')!r}")
    if not isinstance(raw.get("filter"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger runtime filter is missing")
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
                "skip": pin["skip"],
            }
            for pin in actions
        ],
    }


def seed_130704674(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130704674(raw)
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
    _require_lookup_section(seed_in.get("lookup_table"))
    _require_service_replies(seed_in.get("workato_service_replies"))
    filter_matched = expect["trigger_filter_matched"] is True
    if filter_matched:
        if str(trigger.get("Campaign__c") or "") != CAMPAIGN_FILTER_ID:
            raise RuntimeError(
                f"recipe {RECIPE_ID} filter-true variants must set trigger Campaign__c to the "
                f"raw filter id {CAMPAIGN_FILTER_ID!r} verbatim"
            )
        if str(trigger.get("Id") or "") != CA_ID_TOKEN:
            raise RuntimeError(
                f"recipe {RECIPE_ID} filter-true trigger.Id must be the {CA_ID_TOKEN} seed token "
                "(the live Campaign_Activity__c id is only known after provisioning)"
            )
        _require_salesforce_section(seed_in.get("salesforce"), trigger)
    else:
        if str(trigger.get("Campaign__c") or "") == CAMPAIGN_FILTER_ID:
            raise RuntimeError(
                f"recipe {RECIPE_ID} filter-false variants must use a Campaign__c that does NOT "
                "match the raw trigger filter"
            )
        if seed_in.get("salesforce") is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} filter-false variants must not seed live Salesforce records "
                "(the body never runs; nothing may read them)"
            )
        if _REF_TOKEN_RE.search(json.dumps(trigger)):
            raise RuntimeError(
                f"recipe {RECIPE_ID} filter-false variants have no provisioned records — the "
                "trigger must not carry seed ref tokens"
            )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "lookup_table": deepcopy(seed_in["lookup_table"]),
        "workato_service_replies": deepcopy(seed_in["workato_service_replies"]),
    }
    refs: dict[str, str] = {}
    if filter_matched:
        provision = ctx.tools.call(
            "harness.salesforce.seed_records", {"salesforce": deepcopy(seed_in["salesforce"])}
        )
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
        refs = _salesforce_ref_tokens(seed_in["salesforce"], provision)
        out["salesforce_live"] = deepcopy(provision["state"])
        out["salesforce_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
        out["salesforce_ref_tokens"] = refs
    resolved_trigger = _replace_value(deepcopy(trigger), refs)
    _require_no_tokens(resolved_trigger, "trigger_input")
    resolved_expect = _replace_value(deepcopy(expect), refs)
    _require_no_tokens(resolved_expect, "expect")
    out["trigger"] = resolved_trigger
    out["expect"] = resolved_expect
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_130704674(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130704674(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing resolved expect block")
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
    if not isinstance(seed.get("workato_service_replies"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_service_replies")
    if seed["expect"].get("trigger_filter_matched") is True and not isinstance(
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
    result["verifier"] = verify_130704674(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != sorted(["Id", "Browser_Timezone__c", "Campaign__c"]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the dereferenced trigger "
            f"fields Id/Browser_Timezone__c/Campaign__c (search filter, lookup keys, runtime "
            f"filter); got {sorted(trigger.keys())}"
        )
    for key in ("Id", "Browser_Timezone__c", "Campaign__c"):
        if not str(trigger.get(key) or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} trigger_input.{key} must be non-empty")


def _require_expect(data: dict[str, Any]) -> dict[str, Any]:
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    if not isinstance(expect.get("trigger_filter_matched"), bool):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.trigger_filter_matched must be a bool")
    tools = expect.get("tools")
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tools, list) or not isinstance(tool_expectations, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools/tool_expectations must be lists")
    if len(tools) != len(tool_expectations):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry")
    unknown_tools = sorted(set(tools) - set(ALLOWED_TOOLS))
    if unknown_tools:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools has unknown tools: {unknown_tools}")
    for key in ("stopped", "catch", "logger_skipped", "updated"):
        if not isinstance(expect.get(key), bool):
            raise RuntimeError(f"recipe {RECIPE_ID} expect.{key} must be an explicit boolean")
    if expect["stopped"] and "stop_step_number" not in expect:
        raise RuntimeError(f"recipe {RECIPE_ID} stopped variants must pin expect.stop_step_number")
    if not isinstance(expect.get("final_ca_fields"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.final_ca_fields must be an object")
    if not isinstance(expect.get("final_ca_absent_fields"), list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.final_ca_absent_fields must be a list")
    if expect["trigger_filter_matched"] is False:
        if tools or int(expect.get("executed_action_count") or 0) != 0:
            raise RuntimeError(
                f"recipe {RECIPE_ID} filter-false variants must expect zero actions and no tool calls"
            )
    else:
        if not tools or tools[0] != "workato_service.call_service" or tools[1] != "salesforce.search_records":
            raise RuntimeError(
                f"recipe {RECIPE_ID} filter-true variants always run call_service then the live "
                "CA search first"
            )
    if expect["updated"] != ("salesforce.update_record" in tools):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.updated must agree with expect.tools "
            "(exactly the variants whose branch reaches an update_sobject step)"
        )
    if expect["catch"] is True:
        if not isinstance(data.get("force_action_error"), dict):
            raise RuntimeError(
                f"recipe {RECIPE_ID} under engine get_entry semantics (entry: None on no-match) "
                "the catch branch is reachable only via force_action_error"
            )
        if str(data["force_action_error"].get("step_as") or "") != GET_ENTRY_STEP_AS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} the catch wraps only step 11 — force_action_error.step_as "
                f"must be {GET_ENTRY_STEP_AS!r}"
            )
        if not expect["stopped"] or expect.get("stop_step_number") != 13:
            raise RuntimeError(f"recipe {RECIPE_ID} the catch branch always stops at step 13")
    elif isinstance(data.get("force_action_error"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error requires expect.catch: true"
        )
    return expect


def _require_lookup_section(section: Any) -> None:
    if not isinstance(section, dict) or not isinstance(section.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.lookup_table.tables")
    if sorted(section["tables"]) != sorted([INTL_LOOKUP_ID, NORAM_LOOKUP_ID]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must declare exactly tables "
            f"{NORAM_LOOKUP_ID} and {INTL_LOOKUP_ID} (explicitly empty lists allowed)"
        )
    for table_id, cols in ((NORAM_LOOKUP_ID, ("col1", "col2", "col3")), (INTL_LOOKUP_ID, ("col1", "col2", "col3"))):
        rows = section["tables"][table_id]
        if not isinstance(rows, list):
            raise RuntimeError(f"recipe {RECIPE_ID} lookup table {table_id} must be a list")
        for row in rows:
            if not isinstance(row, dict) or any(not str(row.get(col) or "").strip() for col in cols):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} lookup {table_id} entries must set {'/'.join(cols)} "
                    "explicitly (the recipe reads all three)"
                )


def _require_service_replies(section: Any) -> None:
    if not isinstance(section, dict) or SERVICE_STEP_AS not in section:
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires seed.workato_service_replies[{SERVICE_STEP_AS!r}] "
            "(deterministic Workato-internal reply for the step-2 'Flexi Idler' call; the reply "
            "is never dereferenced — {} is the canonical seed)"
        )
    if not isinstance(section[SERVICE_STEP_AS], dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_service_replies[{SERVICE_STEP_AS!r}] must be an object"
        )


def _require_salesforce_section(section: Any, trigger: dict[str, Any]) -> None:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} filter-true variants require seed.salesforce")
    if section.get("schema") != REQUIRED_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare the canonical "
            "REQUIRED_SCHEMA verbatim (ensure_custom_field grants on every touched CA field)"
        )
    records = section.get("records")
    if not isinstance(records, list) or len(records) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.records must create exactly one "
            f"{CA_SOBJECT} record (IF4/IF15 read current_item = the FIRST searched record)"
        )
    record = records[0]
    if not isinstance(record, dict) or str(record.get("sobject") or "") != CA_SOBJECT:
        raise RuntimeError(f"recipe {RECIPE_ID} the seeded record must be a {CA_SOBJECT}")
    if str(record.get("ref") or "").strip().upper() != "CA":
        raise RuntimeError(
            f"recipe {RECIPE_ID} the seeded record ref must be 'ca' (trigger threads {CA_ID_TOKEN})"
        )
    fields = record.get("fields")
    if not isinstance(fields, dict) or not str(fields.get("Name") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} the seeded CA record must set an explicit Name")
    if str(fields.get("Browser_Timezone__c") or "") != str(trigger.get("Browser_Timezone__c") or ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the seeded CA Browser_Timezone__c must mirror the trigger "
            "payload (the IF conditions read the RE-SEARCHED record while the lookups key off "
            "the trigger pill — they must agree)"
        )
    unexpected = sorted(
        set(fields)
        - {"Name", "Browser_Timezone__c", "Region__c", "Person_Sub_Region__c", "Person_Country__c"}
    )
    if unexpected:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seeded CA record carries fields the recipe never reads: {unexpected}"
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
    leftover = sorted(set(_REF_TOKEN_RE.findall(json.dumps(value))))
    if leftover:
        raise RuntimeError(f"recipe {RECIPE_ID} {label} has unresolved seed tokens: {leftover}")


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("salesforce_live"), dict):
        out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
    out.update(ctx.tools.call("harness.lookup_table.snapshot", {}))
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
