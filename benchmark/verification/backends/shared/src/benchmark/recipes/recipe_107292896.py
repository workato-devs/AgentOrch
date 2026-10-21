from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_107292896


RECIPE_ID = "107292896"
SEED_TYPE = "salesforce_lead_batch_freemail_filter_convert_variant"
TRACK = "live_salesforce_lead_domain_account_matching"
TRIGGER_PROVIDER = "salesforce"
TRIGGER_NAME = "sobject_batch_created"
LOOKUP_TABLE_ID = "1492777"
CALL_SERVICE_FLOW_ID = "14673208"
CATCH_STEP_AS = "58737439"
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")

# salesforce.sobject_batch_created on Lead (as sobject_created_bulk, batch
# size 100; the trigger payload is a MOCKED Lead batch -- the block
# dereferences the Lead list and per-item Id / IsConverted / Email):
#   #2  lookup_table.get_entries 1492777 'Freemail providers' (as 034f4dc9)
#   #3  declare_list 'Free Mail Domain' {domain} from entries col1 (d445e8cf)
#   #4  smart_list.create_list 'Free Mail Domain' (3d9aee30)
#   #5  declare_list 'Leads' {id,email,domain,account,domain_2,converted}
#       (bc3b39b5)
#   #6  insert_to_list_batch (c80ec445): ____source = trigger Lead list;
#       converted = IsConverted ? 1 : 0; domain / domain_2 = multi-line
#       if/else/end formulas taking the last TWO labels of the email domain
#       when it has >2 dot-labels (computed [length-2]/[length-1] subscripts),
#       else the whole domain (domain_2 has NO else arm -> engine renders "")
#   IF #7 Leads list size > 0:
#     #8  smart_list.create_list 'Leads' (as create_list, primary_index id)
#     #9  query_list (0b82595d): SELECT id,email,domain,account FROM Leads
#         WHERE converted = 0 AND NOT (domain IN (SELECT domain FROM Free
#         Mail Domain))
#     IF #10 rows size > 0:
#       #11 logger (log_message): rows.pluck('domain').uniq
#           .format_map(\'%s\').join(",")  -- feeds the live SOQL IN clause
#       #12 salesforce.search_sobjects_soql Domain__c (Domain__c/Account__c,
#           query "Domain__c IN (<logger message>)", limit 150) -- LIVE
#       IF #13 Domain__c size > 0:
#         FOREACH #14 (foreach__1) over Domain__c rows:
#           #15 query_list (query_list): UPDATE Leads SET account =
#               '<Account__c>' WHERE domain = '<Domain__c>'
#         #16 query_list (query_list__1): SELECT * FROM Leads WHERE account
#             IS NOT NULL
#         FOREACH #17 (foreach__2) over #16 rows:
#           TRY #18: #19 workato_service.call_service flow 14673208 'Convert
#               Salesforce Lead' {account_id, create_opportunity: "false",
#               lead_id} -- Workato-internal mock; reply is seeded
#               deterministic state (workato_service_replies) and unused
#           CATCH #20 (as 58737439, EMPTY, max_retry_count 0): swallows
#               conversion errors and the loop continues
#
# Live backend: Salesforce Domain__c custom object (DEPLOYED: Domain__c Text,
# Account__c Lookup(Account)) + benchmark-owned Accounts referenced by the
# seeded Domain__c rows ($REF threading). The trigger Lead batch is a mocked
# payload (leads are never live). seed.salesforce.relationship_expansion true
# for uniform owned-record read-back; seed schema declares both Domain__c
# custom fields for FLS (ensure_custom_field early-exits into the FLS grant
# because the fields are deployed).
# seed.salesforce.strict_soql_conditions stays OFF for this recipe: its only
# SOQL condition is a bare "Domain__c IN (...)" clause, which the legacy
# evaluator handles exactly (IN is not a strict-gated op); the seed shape is
# pinned to strict-off so groundtruth semantics stay byte-stable with the
# verified dry-replay.
# Workato-internal (deterministic mock): lookup table 1492777, smart lists,
# variable lists, logger, call_service reply.
#
# Branch-mapping notes (recorded per benmark_rules):
# - The domain/domain_2 length>2 arm (3-part TLD emails, e.g. *.co.uk) is
#   exercised by the dedicated three_part_tld variant (variant_06); the
#   computed-subscript formula arm runs on the arithmetic engine (the
#   bracket-index dispatch fix landed centrally in 3b7736da).
# - domain_2 divergence: Workato renders a false if-without-else as nil; the
#   engine renders "". domain_2 is never consumed downstream (only echoed in
#   the #16 SELECT * rows), so ground truth pins the engine's "".
# - call_service_error_swallowed: force_action_error on step_as call_service
#   proves the EMPTY catch swallows per-iteration errors (no call_service
#   trace rows; the run completes; the catch payload records the message).
#
# Cleanup: variants that seed live Domain__c/Account records delete them via
# harness.salesforce.cleanup in run_107292896's finally block. Lookup/smart-list
# state is per-run in-memory mock state, fully overwritten by every seed.

# Frozen document-order structure pins (keyword/number/as/provider/name/skip +
# verbatim raw input per node, incl. the #6 domain formulas, the #9/#15/#16
# SQL, the #11 format_map formula and the #12 SOQL). Any upstream drift fails
# validation instead of silently changing ground truth.
_STRUCTURE_PINS_JSON = r'''
[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "sobject_created_bulk",
  "provider": "salesforce",
  "name": "sobject_batch_created",
  "skip": false,
  "input": {
   "___poll_interval": "5",
   "batch_size": "100",
   "field_list": "Id\nIsConverted\nEmail\nCreatedBy$Created By ID.Email",
   "query": "isconverted = false AND leadsource !=null AND email != null AND CreatedBy.Email != '<anon>user@company.com</anon>'",
   "since": "<anon>2024-01-01T00:00:00-08:00</anon>",
   "sobject_name": "Lead",
   "table_list": "CreatedBy"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "034f4dc9",
  "provider": "lookup_table",
  "name": "get_entries",
  "skip": false,
  "input": {
   "lookup_table_id": "1492777"
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "d445e8cf",
  "provider": "workato_variable",
  "name": "declare_list",
  "skip": false,
  "input": {
   "list_item_schema_json": "[{\"name\":\"domain\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"}]",
   "list_items": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"034f4dc9\",\"path\":[\"entries\"]}')}",
    "domain": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"034f4dc9\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col1\"]}')}"
   },
   "name": "Free Mail Domain"
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "3d9aee30",
  "provider": "workato_smart_list",
  "name": "create_list",
  "skip": false,
  "input": {
   "list_name": "Free Mail Domain",
   "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"d445e8cf\",\"path\":[\"list_items\"]}')"
  }
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "bc3b39b5",
  "provider": "workato_variable",
  "name": "declare_list",
  "skip": false,
  "input": {
   "list_item_schema_json": "[{\"control_type\":\"text\",\"label\":\"ID\",\"name\":\"id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Email\",\"name\":\"email\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Domain\",\"name\":\"domain\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Account\",\"name\":\"account\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"domain_2\",\"name\":\"domain_2\",\"type\":\"string\",\"optional\":true},{\"name\":\"converted\",\"type\":\"number\",\"optional\":false,\"control_type\":\"number\"}]",
   "name": "Leads"
  }
 },
 {
  "keyword": "action",
  "number": 6,
  "as": "c80ec445",
  "provider": "workato_variable",
  "name": "insert_to_list_batch",
  "skip": false,
  "input": {
   "list_items": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"sobject_created_bulk\",\"path\":[\"Lead\"]}')}",
    "converted": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"sobject_created_bulk\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"IsConverted\"]}') ? 1 : 0",
    "domain": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"sobject_created_bulk\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"Email\"]}').split(\"@\").last.split(\".\").length > 2\n  _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"sobject_created_bulk\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"Email\"]}').split(\"@\").last.split(\".\")[_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"sobject_created_bulk\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"Email\"]}').split(\"@\").last.split(\".\").length - 2].to_s + \".\" + _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"sobject_created_bulk\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"Email\"]}').split(\"@\").last.split(\".\")[_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"sobject_created_bulk\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"Email\"]}').split(\"@\").last.split(\".\").length - 1].to_s\nelse\n  _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"sobject_created_bulk\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"Email\"]}').split(\"@\").last\nend",
    "domain_2": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"sobject_created_bulk\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"Email\"]}').split(\"@\").last.split(\".\").length > 2\n  _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"sobject_created_bulk\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"Email\"]}').split(\"@\").last.split(\".\")[_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"sobject_created_bulk\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"Email\"]}').split(\"@\").last.split(\".\").length - 2].to_s + \".\" + _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"sobject_created_bulk\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"Email\"]}').split(\"@\").last.split(\".\")[_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"sobject_created_bulk\",\"path\":[\"Lead\",{\"path_element_type\":\"current_item\"},\"Email\"]}').split(\"@\").last.split(\".\").length - 1].to_s\nend",
    "email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"sobject_created_bulk\",\"path\":[\"Lead\", {\"path_element_type\": \"current_item\"}, \"Email\"]}')}",
    "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"sobject_created_bulk\",\"path\":[\"Lead\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}"
   },
   "location": "end",
   "name": "92ab3113-fd0b-498b-bc05-2426457d87c5:bc3b39b5"
  }
 },
 {
  "keyword": "if",
  "number": 7,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"bc3b39b5\",\"path\":[\"list_items\", {\"path_element_type\": \"size\"}]}')}",
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
  "number": 8,
  "as": "create_list",
  "provider": "workato_smart_list",
  "name": "create_list",
  "skip": false,
  "input": {
   "list_name": "Leads",
   "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"bc3b39b5\",\"path\":[\"list_items\"]}')",
   "primary_index": "id"
  }
 },
 {
  "keyword": "action",
  "number": 9,
  "as": "0b82595d",
  "provider": "workato_smart_list",
  "name": "query_list",
  "skip": false,
  "input": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "output_schema_by": "index",
   "result_schema_json": "[{\"name\":\"id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"email\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"domain\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"account\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"}]",
   "sql": "SELECT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"create_list\",\"path\":[\"columns\", \"id\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"create_list\",\"path\":[\"columns\", \"email\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"create_list\",\"path\":[\"columns\", \"domain\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"create_list\",\"path\":[\"columns\", \"account\"]}')} FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"create_list\",\"path\":[\"list_name\"]}')} WHERE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"create_list\",\"path\":[\"columns\", \"converted\"]}')} = 0 AND NOT (#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"create_list\",\"path\":[\"columns\", \"domain\"]}')} IN (SELECT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"3d9aee30\",\"path\":[\"columns\", \"domain\"]}')} FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"3d9aee30\",\"path\":[\"list_name\"]}')}))"
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
     "lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"0b82595d\",\"path\":[\"rows\",{\"path_element_type\":\"size\"}]}')",
     "operand": "greater_than",
     "rhs": "=0"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 11,
  "as": "log_message",
  "provider": "logger",
  "name": "log_message",
  "skip": false,
  "input": {
   "message": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"0b82595d\",\"path\":[\"rows\"]}').pluck('domain').uniq.format_map('\\'%s\\'').join(\",\")",
   "user_logs_enabled": "false"
  }
 },
 {
  "keyword": "action",
  "number": 12,
  "as": "search_sobjects_soql",
  "provider": "salesforce",
  "name": "search_sobjects_soql",
  "skip": false,
  "input": {
   "field_list": "Domain__c\nAccount__c",
   "limit": "150",
   "query": "Domain__c IN (#{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"log_message\",\"path\":[\"message\"]}')})",
   "sobject_name": "Domain__c"
  }
 },
 {
  "keyword": "if",
  "number": 13,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"search_sobjects_soql\",\"path\":[\"Domain__c\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "greater_than",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "foreach",
  "number": 14,
  "as": "foreach__1",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"search_sobjects_soql\",\"path\":[\"Domain__c\"]}')}"
  },
  "repeat_mode": null,
  "batch_size": null,
  "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"search_sobjects_soql\",\"path\":[\"Domain__c\"]}')}"
 },
 {
  "keyword": "action",
  "number": 15,
  "as": "query_list",
  "provider": "workato_smart_list",
  "name": "query_list",
  "skip": false,
  "input": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "output_schema_by": "index",
   "result_schema_json": "[{\"name\":\"id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"}]",
   "sql": "UPDATE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"create_list\",\"path\":[\"list_name\"]}')}\nSET #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"create_list\",\"path\":[\"columns\", \"account\"]}')} = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"foreach__1\",\"path\":[\"Account__c\"]}')}'\nWHERE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"create_list\",\"path\":[\"columns\", \"domain\"]}')} = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"foreach__1\",\"path\":[\"Domain__c\"]}')}'"
  }
 },
 {
  "keyword": "action",
  "number": 16,
  "as": "query_list__1",
  "provider": "workato_smart_list",
  "name": "query_list",
  "skip": false,
  "input": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "output_schema_by": "index",
   "result_schema_json": "[{\"name\":\"id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"email\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"domain\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"account\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"}]",
   "sql": "SELECT *\nFROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"create_list\",\"path\":[\"list_name\"]}')}\nWHERE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"create_list\",\"path\":[\"columns\", \"account\"]}')} IS NOT NULL"
  }
 },
 {
  "keyword": "foreach",
  "number": 17,
  "as": "foreach__2",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"query_list__1\",\"path\":[\"rows\"]}')}"
  },
  "repeat_mode": "simple",
  "batch_size": null,
  "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"query_list__1\",\"path\":[\"rows\"]}')}"
 },
 {
  "keyword": "try",
  "number": 18,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {}
 },
 {
  "keyword": "action",
  "number": 19,
  "as": "call_service",
  "provider": "workato_service",
  "name": "call_service",
  "skip": false,
  "input": {
   "flow_id": "14673208",
   "request": {
    "account_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"foreach__2\",\"path\":[\"account\"]}')}",
    "create_opportunity": "false",
    "lead_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"foreach__2\",\"path\":[\"id\"]}')}"
   }
  }
 },
 {
  "keyword": "catch",
  "number": 20,
  "as": "58737439",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "max_retry_count": "0",
   "retry_interval": "2"
  }
 }
]
'''
STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.get_entries",
    "workato_runtime.declare_list",
    "workato_smart_list.create_list",
    "workato_runtime.insert_to_list_batch",
    "workato_smart_list.query_list",
    "workato_runtime.log_message",
    "salesforce.search_records",
    "workato_service.call_service",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.get_entries",
    "salesforce.search_records",
    "workato_service.call_service",
]
# Domain__c custom fields the recipe reads (schema-in-seed for the FLS grant;
# both fields are already deployed live -- Account__c is a Lookup(Account) in
# the org, the Text sf_type below is never used to create it).
REQUIRED_DOMAIN_SCHEMA: dict[str, str] = {
    "Domain__c": "Text",
    "Account__c": "Text",
}
LEAD_ROW_KEYS = ["CreatedBy", "Email", "Id", "IsConverted"]
CALL_REQUEST_KEYS = ["account_id", "create_opportunity", "lead_id"]
FORCEABLE_STEPS = {"call_service"}
OPTIONAL_EXPECT_KEYS = {
    "logger_message",
    "update_sqls",
    "leads_final_rows",
    "call_service_requests",
    "catch_swallowed_error",
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


def validate_107292896(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    trigger_cfg = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    if str(trigger_cfg.get("sobject_name") or "") != "Lead":
        raise RuntimeError(f"recipe {RECIPE_ID} trigger sobject changed")
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


def seed_107292896(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_107292896(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"lookup_table", "salesforce", "workato_service_replies"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    lookup_section = seed_in.get("lookup_table")
    _require_lookup_section(lookup_section)
    sf_section = seed_in.get("salesforce")
    if sf_section is not None:
        _require_salesforce_section(sf_section)
    replies_section = seed_in.get("workato_service_replies")
    if replies_section is not None:
        _require_replies_section(replies_section)
    expect = data.get("expect")
    force = data.get("force_action_error")
    _require_force_shape(force)
    _require_expect_shape(expect, replies_section is not None, force)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track"),
        "raw_validation": validation,
        "lookup_table": deepcopy(lookup_section),
    }
    if replies_section is not None:
        out["workato_service_replies"] = deepcopy(replies_section)
    refs: dict[str, str] = {}
    if sf_section is not None:
        provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": sf_section})
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
        refs = _salesforce_ref_tokens(sf_section, provision)
        out["salesforce_live"] = deepcopy(provision["state"])
        out["salesforce_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
        out["salesforce_ref_tokens"] = dict(refs)
    _require_no_tokens(trigger, "trigger")
    out["trigger"] = trigger
    out["expect"] = _replace_value(deepcopy(expect), refs)
    _require_no_tokens(out["expect"], "expect")
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_107292896(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_107292896(raw)
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
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
    result["verifier"] = verify_107292896(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != ["Lead"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the Lead batch list"
        )
    rows = trigger.get("Lead")
    if not isinstance(rows, list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.Lead must be a list "
            "(an explicit empty list is the declared zero-row batch case)"
        )
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != LEAD_ROW_KEYS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} Lead[{idx}] must carry exactly {LEAD_ROW_KEYS}; "
                f"got {sorted(row.keys()) if isinstance(row, dict) else row}"
            )
        if not str(row.get("Id") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} Lead[{idx}].Id must be a non-empty string")
        if not isinstance(row.get("IsConverted"), bool):
            raise RuntimeError(f"recipe {RECIPE_ID} Lead[{idx}].IsConverted must be a boolean")
        email = row.get("Email")
        if not isinstance(email, str) or "@" not in email:
            raise RuntimeError(
                f"recipe {RECIPE_ID} Lead[{idx}].Email must be an explicit address "
                "(the trigger filter guarantees email != null)"
            )
        created_by = row.get("CreatedBy")
        if not isinstance(created_by, dict) or not str(created_by.get("Email") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} Lead[{idx}].CreatedBy.Email must be a non-empty string "
                "(the trigger field_list pulls CreatedBy.Email)"
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
            f"recipe {RECIPE_ID} Freemail providers table {LOOKUP_TABLE_ID} must be a "
            "non-empty explicit list"
        )
    for row in rows:
        if not isinstance(row, dict) or not str(row.get("col1") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} Freemail providers rows must carry a non-empty col1 domain"
            )


def _require_salesforce_section(sf_section: Any) -> None:
    if not isinstance(sf_section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce must be an object")
    if sf_section.get("relationship_expansion") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.relationship_expansion must be true"
        )
    if sf_section.get("strict_soql_conditions"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} pins strict_soql_conditions OFF: its only SOQL "
            "condition is a bare 'Domain__c IN (...)' clause, which the legacy "
            "evaluator handles exactly (IN is not a strict-gated op); keep the seed "
            "shape byte-stable with the verified dry-replay"
        )
    schema = sf_section.get("schema")
    if not isinstance(schema, list) or not schema:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare the Domain__c custom "
            "fields (schema-in-seed FLS grant via ensure_custom_field)"
        )
    declared = {
        (str(entry.get("sobject") or ""), str(entry.get("field") or "")): str(entry.get("sf_type") or "")
        for entry in schema
        if isinstance(entry, dict)
    }
    for field, sf_type in REQUIRED_DOMAIN_SCHEMA.items():
        if declared.get(("Domain__c", field)) != sf_type:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed.salesforce.schema must declare Domain__c.{field} "
                f"as {sf_type}"
            )
    records = sf_section.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records must be a non-empty list")
    account_refs: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records entries must be objects")
        sobject = str(record.get("sobject") or "")
        ref = str(record.get("ref") or "").strip()
        fields = record.get("fields")
        if sobject not in {"Account", "Domain__c"}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed.salesforce.records only seeds Account/Domain__c; got {sobject!r}"
            )
        if not ref or not isinstance(fields, dict):
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded {sobject} record needs an explicit ref and fields"
            )
        if sobject == "Account":
            if not str(fields.get("Name") or "").strip():
                raise RuntimeError(f"recipe {RECIPE_ID} seeded Account requires an explicit Name")
            account_refs.add(ref)
        else:
            if not str(fields.get("Domain__c") or "").strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} seeded Domain__c requires an explicit Domain__c value"
                )
            if "Account__c" in fields:
                token = str(fields.get("Account__c") or "")
                expected_tokens = {f"${account_ref.upper()}_ID" for account_ref in account_refs}
                if token not in expected_tokens:
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} seeded Domain__c.Account__c must reference an "
                        f"earlier seeded Account ref token; got {token!r}"
                    )


def _require_replies_section(replies_section: Any) -> None:
    if not isinstance(replies_section, dict) or sorted(replies_section.keys()) != ["call_service"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_service_replies must declare exactly the "
            "'call_service' reply (deterministic Workato-internal sub-recipe state)"
        )
    reply = replies_section.get("call_service")
    if not isinstance(reply, dict) or not isinstance(reply.get("reply"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the call_service reply must be an object carrying an "
            "explicit reply payload (the recipe never dereferences it, but the seed "
            "must still be deterministic state, never a fallback)"
        )


def _require_force_shape(force: Any) -> None:
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


def _require_expect_shape(expect: Any, has_replies: bool, force: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    for key in ("executed_action_count", "tools", "tool_expectations"):
        if key not in expect:
            raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required key {key!r}")
    known = {"executed_action_count", "tools", "tool_expectations"} | OPTIONAL_EXPECT_KEYS
    unexpected = sorted(set(expect) - known)
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has unexpected keys: {unexpected}")
    requests = expect.get("call_service_requests")
    if requests is not None:
        if not isinstance(requests, list) or not requests:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.call_service_requests must be a non-empty list"
            )
        if not has_replies:
            raise RuntimeError(
                f"recipe {RECIPE_ID} variants expecting call_service invocations must seed "
                "workato_service_replies (fail-fast deterministic reply state)"
            )
        for idx, item in enumerate(requests):
            request = item.get("request") if isinstance(item, dict) else None
            if (
                not isinstance(item, dict)
                or str(item.get("flow_id") or "") != CALL_SERVICE_FLOW_ID
                or not isinstance(request, dict)
                or sorted(request.keys()) != CALL_REQUEST_KEYS
                or request.get("create_opportunity") != "false"
            ):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} expect.call_service_requests[{idx}] must pin "
                    f"flow_id {CALL_SERVICE_FLOW_ID} and a request of exactly "
                    f"{CALL_REQUEST_KEYS} with create_opportunity 'false'"
                )
    swallowed = expect.get("catch_swallowed_error")
    if swallowed is not None:
        if not isinstance(force, dict) or str(force.get("error") or "") != str(swallowed):
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.catch_swallowed_error must equal the forced "
                "call_service error message"
            )
        if requests is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} a swallowed-error variant never records call_service "
                "invocations; drop expect.call_service_requests"
            )
    elif isinstance(force, dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} forced-error variants must pin expect.catch_swallowed_error"
        )
    if expect.get("leads_final_rows") is not None and not isinstance(expect.get("leads_final_rows"), list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.leads_final_rows must be a list")
    if expect.get("update_sqls") is not None:
        update_sqls = expect.get("update_sqls")
        if not isinstance(update_sqls, list) or not all(isinstance(sql, str) and sql for sql in update_sqls):
            raise RuntimeError(f"recipe {RECIPE_ID} expect.update_sqls must be non-empty SQL strings")


def _salesforce_ref_tokens(seed_section: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    live_ids = [
        str(record.get("id") or "")
        for record in salesforce_snapshot.get("records") or []
        if isinstance(record, dict) and record.get("id") and not record.get("read_only")
    ]
    seed_records = [record for record in seed_section.get("records") or [] if isinstance(record, dict)]
    if len(live_ids) != len(seed_records):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed/snapshot record count mismatch: "
            f"{len(seed_records)} seeded vs {len(live_ids)} provisioned"
        )
    refs: dict[str, str] = {}
    for idx, record in enumerate(seed_records):
        ref = str(record.get("ref") or "").strip()
        if ref:
            refs[f"${ref.upper()}_ID"] = live_ids[idx]
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
    out.update(ctx.tools.call("harness.lookup_table.snapshot", {}))
    if isinstance(seed.get("salesforce_live"), dict):
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
