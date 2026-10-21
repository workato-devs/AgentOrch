from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_122139155


RECIPE_ID = "122139155"
SEED_TYPE = "salesforce_opportunity_stage_history_sales_accepted_date_variant"
TRACK = "live_salesforce_opportunity_field_history_sad_sync"
TRIGGER_PROVIDER = "salesforce"
TRIGGER_NAME = "new_custom_object"
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_SF_ID_RE = re.compile(r"^[a-zA-Z0-9]{15,18}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ISO_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})$")

# salesforce.new_custom_object on OpportunityFieldHistory (as 2469a89f) --
# stage-transition history events (Field = StageName). The trigger event is a
# MOCKED payload (OpportunityFieldHistory rows are system-generated and cannot
# be inserted through the API); everything the recipe touches on Salesforce
# runs LIVE against benchmark-owned records:
#   #2  search_sobjects User where Id = trigger.CreatedById (field_list
#       TimeZoneSidKey/Id/Name/Email, limit 150) -- served from the live
#       current-user read-only row (seed.salesforce.current_user)
#   IF #3 OldValue starts_with 'S0':
#     #4  declare_variable sales_accepted_date (date, no default)
#     IF #5 Opportunity.Type.downcase contains 'renewal':
#       #6  search_sobjects_soql_v2 OpportunityFieldHistory (OUTPUT UNUSED
#           downstream; the live SOQL legitimately returns 0 rows because
#           history rows are not API-seedable -- pinned result_count 0)
#       IF #7 Type.downcase == 'renewal with upgrade':
#         IF #8 trigger Opportunity.Sales_Accepted_Date__c !=
#               CreatedDate.strftime('%Y-%m-%d'):
#           #9  update_variables sales_accepted_date =
#               CreatedDate.in_time_zone(User.TimeZoneSidKey).to_date
#           (when #8 is false NOTHING runs -- #8 carries no else of its own)
#       ELSE #10 (the else of #7: raw 'else' nodes are children of the if
#             they complement -- #10 sits in #7's block and its comment reads
#             "any other types of 'Renewals' (except Renewal with Upgrade)"):
#         IF #11 SAD blank:
#           #12 update_variables (same in_time_zone formula) -- REACHABLE via
#               plain-renewal + blank SAD (the batch triage misread #10 as the
#               else of #8 and flagged #12 dead; the raw nesting proves it live)
#         ELSE #13 (else of #11):
#           #14 logger 'Do nothing. Leave the current SAD value as is.'
#               (user_logs_enabled false; plain-renewal + present SAD)
#     IF #15 trigger Opportunity.Sales_Accepted_Date__c blank:
#       #16 update_variables sales_accepted_date (same formula as #9)
#     IF #17 variable sales_accepted_date present:
#       #18 salesforce.update_sobject Opportunity id=OpportunityId
#           Sales_Accepted_Date__c = variable -- LIVE write
#   IF #19 NewValue starts_with 'S0':
#     #20 salesforce.update_sobject Opportunity Sales_Accepted_Date__c ==clear
#         -- LIVE write (clears the date; harness maps '' -> null)
#
# Determinism: the variant pins trigger CreatedDate to a fixed 12:00:00Z
# timestamp so CreatedDate.strftime('%Y-%m-%d') and any plausible org user
# timezone (UTC-11..UTC+11) agree on the calendar date.
#
# Cleanup: the benchmark-owned Opportunity created in seed is updated by
# #18/#20 and deleted by harness.salesforce.cleanup in run_122139155's
# finally block.

# Frozen document-order structure pins (keyword/number/as/provider/name/skip +
# verbatim raw input per node, incl. the trigger field_list, the #6 SOQL, the
# #9/#12/#16 in_time_zone formula and the #20 =clear write). Any upstream
# drift fails validation instead of silently changing ground truth.
_STRUCTURE_PINS_JSON = r'''
[
 {
  "as": "2469a89f",
  "input": {
   "field_list": "OpportunityId\nOldValue\nNewValue\nField\nOpportunity$Opportunity ID.Name\nOpportunity$Opportunity ID.StageName\nOpportunity$Opportunity ID.Type\nOpportunity$Opportunity ID.IsWon\nOpportunity$Opportunity ID.IsClosed\nOpportunity$Opportunity ID.Sales_Accepted_Date__c\nCreatedDate\nOpportunity$Opportunity ID.CreatedDate\nCreatedById",
   "since_offset": "0",
   "sobject_name": "OpportunityFieldHistory",
   "table_list": "Opportunity\nUser"
  },
  "keyword": "trigger",
  "name": "new_custom_object",
  "number": 1,
  "provider": "salesforce",
  "skip": false
 },
 {
  "as": "42872a4c",
  "input": {
   "Id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2469a89f\",\"path\":[\"CreatedById\"]}')}",
   "field_list": "TimeZoneSidKey\nId\nName\nEmail",
   "limit": "150",
   "sobject_name": "User"
  },
  "keyword": "action",
  "name": "search_sobjects",
  "number": 2,
  "provider": "salesforce",
  "skip": false
 },
 {
  "as": null,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2469a89f\",\"path\":[\"OldValue\"]}')}",
     "operand": "starts_with",
     "rhs": "S0"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "keyword": "if",
  "name": null,
  "number": 3,
  "provider": null,
  "skip": false
 },
 {
  "as": "823bbdd7",
  "input": {
   "variables": {
    "schema": "[{\"name\":\"sales_accepted_date\",\"type\":\"date\",\"optional\":true,\"label\":\"Sales Accepted Date\",\"details\":{\"real_name\":\"Sales Accepted Date\"},\"control_type\":\"date\",\"parent\":[\"variables\",\"data\"]}]"
   }
  },
  "keyword": "action",
  "name": "declare_variable",
  "number": 4,
  "provider": "workato_variable",
  "skip": false
 },
 {
  "as": null,
  "input": {
   "conditions": [
    {
     "lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2469a89f\",\"path\":[\"Opportunity\",\"Type\"]}').downcase",
     "operand": "contains",
     "rhs": "renewal"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "keyword": "if",
  "name": null,
  "number": 5,
  "provider": null,
  "skip": false
 },
 {
  "as": "2159f72d",
  "input": {
   "limit": "150",
   "output_schema": "[{\"properties\":[{\"control_type\":\"text\",\"label\":\"Type\",\"type\":\"string\",\"name\":\"type\"},{\"control_type\":\"text\",\"label\":\"URL\",\"type\":\"string\",\"name\":\"url\"}],\"label\":\"Attributes\",\"type\":\"object\",\"name\":\"attributes\"},{\"control_type\":\"text\",\"label\":\"Created by ID\",\"type\":\"string\",\"name\":\"CreatedById\"},{\"type\":\"date_time\",\"name\":\"CreatedDate\",\"control_type\":\"date_time\",\"parse_output\":\"parse_iso8601_timestamp\",\"render_input\":\"render_iso8601_timestamp\",\"label\":\"Created Date\",\"custom\":false},{\"control_type\":\"text\",\"label\":\"Field\",\"type\":\"string\",\"name\":\"Field\"},{\"control_type\":\"text\",\"label\":\"New value\",\"type\":\"string\",\"name\":\"NewValue\"},{\"control_type\":\"text\",\"label\":\"Old value\",\"type\":\"string\",\"name\":\"OldValue\"},{\"control_type\":\"text\",\"label\":\"Opportunity ID\",\"type\":\"string\",\"name\":\"OpportunityId\"}]",
   "query": "SELECT CreatedById,CreatedDate,Field,NewValue,OldValue,OpportunityId \nFROM OpportunityFieldHistory \nWHERE OpportunityId = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2469a89f\",\"path\":[\"OpportunityId\"]}')}' AND Field = 'Sales_Accepted_Date__c'"
  },
  "keyword": "action",
  "name": "search_sobjects_soql_v2",
  "number": 6,
  "provider": "salesforce",
  "skip": false
 },
 {
  "as": null,
  "input": {
   "conditions": [
    {
     "lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2469a89f\",\"path\":[\"Opportunity\",\"Type\"]}').downcase",
     "operand": "equals_to",
     "rhs": "renewal with upgrade"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "keyword": "if",
  "name": null,
  "number": 7,
  "provider": null,
  "skip": false
 },
 {
  "as": null,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2469a89f\",\"path\":[\"Opportunity\", \"Sales_Accepted_Date__c\"]}')}",
     "operand": "not_equals_to",
     "rhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2469a89f\",\"path\":[\"CreatedDate\"]}').strftime(\"%Y-%m-%d\")"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "keyword": "if",
  "name": null,
  "number": 8,
  "provider": null,
  "skip": false
 },
 {
  "as": "c5d27b27",
  "input": {
   "name": "0d633c96-4bef-45ad-8ed6-a1f38af94845:823bbdd7:sales_accepted_date",
   "sales_accepted_date": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2469a89f\",\"path\":[\"CreatedDate\"]}').in_time_zone(\"#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"42872a4c\",\"path\":[\"User\",{\"path_element_type\":\"current_item\"},\"TimeZoneSidKey\"]}')}\").to_date"
  },
  "keyword": "action",
  "name": "update_variables",
  "number": 9,
  "provider": "workato_variable",
  "skip": false
 },
 {
  "as": null,
  "input": {},
  "keyword": "else",
  "name": null,
  "number": 10,
  "provider": null,
  "skip": false
 },
 {
  "as": null,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2469a89f\",\"path\":[\"Opportunity\", \"Sales_Accepted_Date__c\"]}')}",
     "operand": "blank",
     "rhs": ""
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "keyword": "if",
  "name": null,
  "number": 11,
  "provider": null,
  "skip": false
 },
 {
  "as": "3914586f",
  "input": {
   "name": "0d633c96-4bef-45ad-8ed6-a1f38af94845:823bbdd7:sales_accepted_date",
   "sales_accepted_date": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2469a89f\",\"path\":[\"CreatedDate\"]}').in_time_zone(\"#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"42872a4c\",\"path\":[\"User\",{\"path_element_type\":\"current_item\"},\"TimeZoneSidKey\"]}')}\").to_date"
  },
  "keyword": "action",
  "name": "update_variables",
  "number": 12,
  "provider": "workato_variable",
  "skip": false
 },
 {
  "as": null,
  "input": {},
  "keyword": "else",
  "name": null,
  "number": 13,
  "provider": null,
  "skip": false
 },
 {
  "as": "3e2e2096",
  "input": {
   "message": "Do nothing. Leave the current SAD value as is.",
   "user_logs_enabled": "false"
  },
  "keyword": "action",
  "name": "log_message",
  "number": 14,
  "provider": "logger",
  "skip": false
 },
 {
  "as": null,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2469a89f\",\"path\":[\"Opportunity\", \"Sales_Accepted_Date__c\"]}')}",
     "operand": "blank",
     "rhs": ""
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "keyword": "if",
  "name": null,
  "number": 15,
  "provider": null,
  "skip": false
 },
 {
  "as": "eb09b59b",
  "input": {
   "name": "0d633c96-4bef-45ad-8ed6-a1f38af94845:823bbdd7:sales_accepted_date",
   "sales_accepted_date": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2469a89f\",\"path\":[\"CreatedDate\"]}').in_time_zone(\"#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"42872a4c\",\"path\":[\"User\",{\"path_element_type\":\"current_item\"},\"TimeZoneSidKey\"]}')}\").to_date"
  },
  "keyword": "action",
  "name": "update_variables",
  "number": 16,
  "provider": "workato_variable",
  "skip": false
 },
 {
  "as": null,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"823bbdd7\",\"path\":[\"sales_accepted_date\"]}')}",
     "operand": "present",
     "rhs": ""
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "keyword": "if",
  "name": null,
  "number": 17,
  "provider": null,
  "skip": false
 },
 {
  "as": "2f06b6ad",
  "input": {
   "Sales_Accepted_Date__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"823bbdd7\",\"path\":[\"sales_accepted_date\"]}')}",
   "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2469a89f\",\"path\":[\"OpportunityId\"]}')}",
   "sobject_name": "Opportunity"
  },
  "keyword": "action",
  "name": "update_sobject",
  "number": 18,
  "provider": "salesforce",
  "skip": false
 },
 {
  "as": null,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2469a89f\",\"path\":[\"NewValue\"]}')}",
     "operand": "starts_with",
     "rhs": "S0"
    }
   ],
   "operand": "and",
   "type": "compound"
  },
  "keyword": "if",
  "name": null,
  "number": 19,
  "provider": null,
  "skip": false
 },
 {
  "as": "98ddb594",
  "input": {
   "Sales_Accepted_Date__c": "=clear",
   "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2469a89f\",\"path\":[\"OpportunityId\"]}')}",
   "sobject_name": "Opportunity"
  },
  "keyword": "action",
  "name": "update_sobject",
  "number": 20,
  "provider": "salesforce",
  "skip": false
 }
]
'''
STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_runtime.declare_variable",
    "workato_runtime.update_variables",
    "workato_runtime.log_message",
    "salesforce.update_record",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "salesforce.update_record",
]
TRIGGER_KEYS = [
    "OpportunityId",
    "OldValue",
    "NewValue",
    "Field",
    "CreatedDate",
    "CreatedById",
    "Opportunity",
]
TRIGGER_OPPORTUNITY_KEYS = [
    "Name",
    "StageName",
    "Type",
    "IsWon",
    "IsClosed",
    "Sales_Accepted_Date__c",
    "CreatedDate",
]
OPP_REF_TOKEN = "$OPP_ID"
USER_REF_TOKEN = "$USER_ID"


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


def validate_122139155(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_122139155(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_122139155(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"salesforce"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    sf_section = seed_in.get("salesforce")
    opp_fields = _require_salesforce_section(sf_section)
    _require_trigger_shape(trigger, opp_fields)
    expect = data.get("expect")
    _require_expect_shape(expect)
    provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": sf_section})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    refs = _salesforce_ref_tokens(sf_section, provision)
    trigger = _replace_value(trigger, refs)
    _require_no_tokens(trigger, "trigger")
    if not _SF_ID_RE.fullmatch(str(trigger.get("OpportunityId") or "")):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger OpportunityId did not resolve to a live Opportunity id"
        )
    if not _SF_ID_RE.fullmatch(str(trigger.get("CreatedById") or "")):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger CreatedById did not resolve to the live current user id"
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
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": refs,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_122139155(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_122139155(raw)
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
    result["verifier"] = verify_122139155(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_salesforce_section(sf_section: Any) -> dict[str, Any]:
    if not isinstance(sf_section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce")
    if sf_section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true "
            "(unsupported SOQL conditions must raise, never silently drop)"
        )
    current_user = sf_section.get("current_user")
    if not isinstance(current_user, dict) or str(current_user.get("sobject") or "") != "User":
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.current_user must be {{\"sobject\": \"User\"}} "
            "(action #2 reads the live creating user back by Id)"
        )
    schema = sf_section.get("schema")
    if not isinstance(schema, list) or not any(
        isinstance(entry, dict)
        and str(entry.get("sobject") or "") == "Opportunity"
        and str(entry.get("field") or "") == "Sales_Accepted_Date__c"
        and str(entry.get("sf_type") or "") == "Date"
        for entry in schema
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare "
            "Opportunity.Sales_Accepted_Date__c as Date (schema-in-seed via ensure_custom_field)"
        )
    records = [record for record in sf_section.get("records") or [] if isinstance(record, dict)]
    opps = [record for record in records if str(record.get("sobject") or "") == "Opportunity"]
    if len(records) != 1 or len(opps) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.records must contain exactly one Opportunity record"
        )
    opp = opps[0]
    if str(opp.get("ref") or "") != "opp":
        raise RuntimeError(f"recipe {RECIPE_ID} Opportunity seed record must carry ref 'opp'")
    fields = opp.get("fields")
    if not isinstance(fields, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} Opportunity seed record is missing fields")
    for key in ("Name", "StageName", "CloseDate", "Type"):
        if not str(fields.get(key) or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} Opportunity seed record requires explicit {key}")
    if "Sales_Accepted_Date__c" not in fields:
        raise RuntimeError(
            f"recipe {RECIPE_ID} Opportunity seed record must declare Sales_Accepted_Date__c "
            "explicitly (null for a blank initial SAD)"
        )
    sad = fields.get("Sales_Accepted_Date__c")
    if sad is not None and not (_DATE_RE.fullmatch(str(sad))):
        raise RuntimeError(
            f"recipe {RECIPE_ID} Opportunity Sales_Accepted_Date__c must be null or YYYY-MM-DD; got {sad!r}"
        )
    return fields


def _require_trigger_shape(trigger: dict[str, Any], opp_fields: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != sorted(TRIGGER_KEYS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly {TRIGGER_KEYS}; "
            f"got {sorted(trigger.keys())}"
        )
    if str(trigger.get("OpportunityId") or "") != OPP_REF_TOKEN:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.OpportunityId must be the {OPP_REF_TOKEN} seed token"
        )
    if str(trigger.get("CreatedById") or "") != USER_REF_TOKEN:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.CreatedById must be the {USER_REF_TOKEN} seed token "
            "(the live current user id is assigned at seed time)"
        )
    if str(trigger.get("Field") or "") != "StageName":
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.Field must be 'StageName' "
            "(the recipe handles stage-transition history events)"
        )
    for key in ("OldValue", "NewValue"):
        if not str(trigger.get(key) or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} trigger_input.{key} must be a non-empty stage name")
    created = str(trigger.get("CreatedDate") or "")
    if not _ISO_TS_RE.fullmatch(created):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.CreatedDate must be a fixed ISO-8601 timestamp; "
            f"got {created!r} (wall-clock time is not allowed)"
        )
    opp = trigger.get("Opportunity")
    if not isinstance(opp, dict) or sorted(opp.keys()) != sorted(TRIGGER_OPPORTUNITY_KEYS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.Opportunity must carry exactly "
            f"{TRIGGER_OPPORTUNITY_KEYS}; got {sorted(opp.keys()) if isinstance(opp, dict) else opp}"
        )
    for key in ("IsWon", "IsClosed"):
        if not isinstance(opp.get(key), bool):
            raise RuntimeError(f"recipe {RECIPE_ID} trigger_input.Opportunity.{key} must be a boolean")
    # The history event describes the just-transitioned Opportunity; pin the
    # event view to the seeded live record so a variant cannot drift into an
    # unfaithful trigger/record split.
    for key in ("Name", "StageName", "Type"):
        if opp.get(key) != opp_fields.get(key):
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger_input.Opportunity.{key} must match the seeded "
                f"Opportunity field ({opp.get(key)!r} != {opp_fields.get(key)!r})"
            )
    if str(opp.get("StageName") or "") != str(trigger.get("NewValue") or ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.Opportunity.StageName must equal NewValue "
            "(the event fires after the transition)"
        )
    trigger_sad = opp.get("Sales_Accepted_Date__c")
    seeded_sad = opp_fields.get("Sales_Accepted_Date__c")
    if (trigger_sad or "") != (seeded_sad or ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.Opportunity.Sales_Accepted_Date__c "
            f"({trigger_sad!r}) must mirror the seeded value ({seeded_sad!r}; blank == null)"
        )


def _require_expect_shape(expect: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    for key in ("tools", "executed_action_count", "sad_update_count", "logger_expected"):
        if key not in expect:
            raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required key {key!r}")
    if "final_sad" not in expect:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect must pin final_sad (the live Opportunity "
            "Sales_Accepted_Date__c after the run; null when cleared/blank)"
        )
    final_sad = expect.get("final_sad")
    if final_sad is not None and not _DATE_RE.fullmatch(str(final_sad)):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_sad must be null or YYYY-MM-DD; got {final_sad!r}"
        )
    if not isinstance(expect.get("logger_expected"), bool):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.logger_expected must be a boolean")
    if expect.get("sad_update_count") not in (0, 1):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.sad_update_count must be 0 or 1 "
            "(at most one Opportunity write per branch)"
        )


def _salesforce_ref_tokens(seed_section: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    records = [record for record in salesforce_snapshot.get("records") or [] if isinstance(record, dict)]
    owned = [record for record in records if not record.get("read_only")]
    read_only_users = [
        record for record in records
        if record.get("read_only") and str(record.get("sobject") or "") == "User"
    ]
    seed_records = [record for record in seed_section.get("records") or [] if isinstance(record, dict)]
    if len(owned) != len(seed_records):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed/snapshot record count mismatch: "
            f"{len(seed_records)} seeded vs {len(owned)} provisioned"
        )
    if len(read_only_users) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expected exactly one read-only current-user row; "
            f"got {len(read_only_users)}"
        )
    refs: dict[str, str] = {}
    for idx, record in enumerate(seed_records):
        ref = str(record.get("ref") or "").strip()
        live_id = str(owned[idx].get("id") or "")
        if not _SF_ID_RE.fullmatch(live_id):
            raise RuntimeError(f"recipe {RECIPE_ID} provisioned record id looks invalid: {live_id!r}")
        if ref:
            refs[f"${ref.upper()}_ID"] = live_id
    user_id = str(read_only_users[0].get("id") or "")
    if not _SF_ID_RE.fullmatch(user_id):
        raise RuntimeError(f"recipe {RECIPE_ID} current-user id looks invalid: {user_id!r}")
    refs[USER_REF_TOKEN] = user_id
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
    return dict(ctx.tools.call("harness.salesforce.snapshot", {}))


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
