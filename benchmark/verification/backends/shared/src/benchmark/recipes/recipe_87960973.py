from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_87960973


RECIPE_ID = "87960973"
SEED_TYPE = "salesforce_ocr_contact_account_match_variant"
TRACK = "live_salesforce_ocr_contact_account_reassignment"
TRIGGER_PROVIDER = "salesforce"
TRIGGER_NAME = "new_custom_object"
TRIGGER_AS = "62aa61de"
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_SF_ID_RE = re.compile(r"^[a-zA-Z0-9]{15,18}$")

# Salesforce new_custom_object trigger on OpportunityContactRole with a RUNTIME
# compound trigger filter (all three must hold or the body never runs):
#   [1] trigger Contact.AccountId not_equals_to trigger Opportunity.AccountId
#   [2] Role.blank? or (Role.include?("Partner") ? false : true) is_true
#   [3] trigger Contact.Email present
# Body (11 actions):
#   2  declare_variable (c6f09d95): contact_domain = Contact.Email.split("@")
#      .last.split(".").first, plus account/contact/opportunity id echoes
#   3  search_sobjects_soql (771169ef): Contact WHERE AccountId = trigger
#      Opportunity.AccountId, limit 150, field_list Email + Account.Website --
#      the nested Account.Website read-back REQUIRES seed.salesforce.
#      relationship_expansion: true with an OWNED parent Account
#   4  smart_list create_list 'contact_emails' (primary_index Email) from the
#      step-3 Contact rows; declared schema columns keep the SQLite table
#      creatable even for an EMPTY result (zero-contacts variant)
#   5  query_list: SELECT COUNT(Email) ... WHERE Email LIKE '%<domain>%'
#   6  query_list: SELECT COUNT(Email) ... WHERE Email NOT LIKE '%<domain>%'
#      (COUNT aggregate + NOT LIKE on the SQLite engine -- the batch-02 gaps,
#      fixed and probe-verified)
#   7  update_variables (0b31ab84) MULTI-TARGET (newline-joined name; engine
#      fix edd3ccc8, probe-verified with this exact node): sames/different
#      counts ('.presence or 0') + account_website = step-3 Contact
#      current_item Account.Website (current_item OUTSIDE foreach = first row;
#      empty result -> MISSING -> None)
#   8  IF sames > different (ternary formula) -> 9 set
#      contact_matched_account_contacts = "true"
#   10 IF step-3 Contact current_item Account.Website contains contact_domain
#      -> 11 set contact_matched_account_website = "true"
#   12 IF both flags is_true (either missing flag renders "" -> false) ->
#      13 salesforce.update_sobject Contact id=contact_id set AccountId =
#         opportunity account (live update of the benchmark-owned trigger
#         Contact)
#      14 lookup_table.add_entry 3236786 audit row col1..col9 (col9 =
#         now.strftime("%Y-%m-%dT%H:%M:%S%:z") -- variant MUST pin data.now)
#      15 google_sheets.add_spreadsheet_row_v4 -- DISABLED IN THE RAW RECIPE
#         ("skip": true on the deployed step): Workato never executes it, so
#         the benchmark involves NO Google Sheets backend. The executor
#         faithfully records a reached-but-skipped trace marker when the
#         write branch runs; the verifier pins that marker so the dead step
#         is proven reached, never silently dropped.
#
# Trigger ids thread $REF tokens: OpportunityId/$OPP, ContactId/$CON_TRIG,
# Contact.AccountId/$ACC_PREV, Opportunity.AccountId/$ACC_OPP resolve to the
# live seeded record ids at seed time (and inside expect), so the step-3 SOQL,
# the step-13 update target and every audit column are real live identifiers.
#
# Cleanup: every live Salesforce object is benchmark-owned (seeded);
# run_87960973 calls harness.salesforce.cleanup in finally and fails on
# leftovers. The lookup table is a seeded Workato-internal mock. now is pinned
# via variant data.now (fail-fast in the engine when read without a seed).

_STRUCTURE_PINS_JSON = r'''
[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "62aa61de",
  "provider": "salesforce",
  "name": "new_custom_object",
  "skip": false,
  "input": {
   "field_list": "OpportunityId\nContactId\nRole\nIsPrimary\nContact$Contact ID.Email\nContact$Contact ID.AccountId\nOpportunity$Opportunity ID.AccountId\nOpportunity$Opportunity ID.Name",
   "since_offset": "-3600",
   "sobject_name": "OpportunityContactRole",
   "table_list": "Opportunity\nContact"
  },
  "filter": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"62aa61de\",\"path\":[\"Contact\", \"AccountId\"]}')}",
     "operand": "not_equals_to",
     "rhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"62aa61de\",\"path\":[\"Opportunity\", \"AccountId\"]}')}"
    },
    {
     "lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"62aa61de\",\"path\":[\"Role\"]}').blank? or (_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"62aa61de\",\"path\":[\"Role\"]}').include?(\"Partner\") ? false : true)",
     "operand": "is_true",
     "rhs": ""
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"62aa61de\",\"path\":[\"Contact\", \"Email\"]}')}",
     "operand": "present",
     "rhs": ""
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "c6f09d95",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "account_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"62aa61de\",\"path\":[\"Opportunity\", \"AccountId\"]}')}",
     "contact_domain": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"62aa61de\",\"path\":[\"Contact\",\"Email\"]}').split(\"@\").last.split(\".\").first",
     "contact_email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"62aa61de\",\"path\":[\"Contact\", \"Email\"]}')}",
     "contact_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"62aa61de\",\"path\":[\"ContactId\"]}')}",
     "opportunity_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"62aa61de\",\"path\":[\"OpportunityId\"]}')}",
     "previous_account_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"62aa61de\",\"path\":[\"Contact\", \"AccountId\"]}')}"
    },
    "schema": "[{\"name\":\"contact_domain\",\"type\":\"string\",\"optional\":true,\"label\":\"contact_domain\",\"control_type\":\"text\"},{\"name\":\"sames_domain_account_contacts\",\"type\":\"number\",\"optional\":true,\"label\":\"same_email_domain_account_contacts\",\"control_type\":\"number\"},{\"name\":\"different_email_domain_account_contacts\",\"type\":\"number\",\"optional\":true,\"label\":\"different_email_domain_account_contacts\",\"control_type\":\"number\"},{\"name\":\"account_website\",\"type\":\"string\",\"optional\":true,\"label\":\"account_website\",\"control_type\":\"text\"},{\"name\":\"account_domain\",\"type\":\"string\",\"optional\":true,\"label\":\"account_domain\",\"control_type\":\"text\"},{\"name\":\"contact_matched_account_contacts\",\"type\":\"boolean\",\"optional\":true,\"label\":\"contact_matched_account_contacts\",\"control_type\":\"checkbox\"},{\"name\":\"contact_matched_account_website\",\"type\":\"boolean\",\"optional\":true,\"label\":\"contact_matched_account_website\",\"control_type\":\"checkbox\"},{\"name\":\"contact_id\",\"type\":\"string\",\"optional\":true,\"label\":\"contact_id\",\"control_type\":\"text\"},{\"name\":\"account_id\",\"type\":\"string\",\"optional\":true,\"label\":\"oppportunity_account_id\",\"control_type\":\"text\"},{\"name\":\"opportunity_id\",\"type\":\"string\",\"optional\":true,\"label\":\"opportunity_id\",\"control_type\":\"text\"},{\"name\":\"contact_email\",\"type\":\"string\",\"optional\":true,\"label\":\"contact_email\",\"control_type\":\"text\"},{\"name\":\"previous_account_id\",\"type\":\"string\",\"optional\":true,\"label\":\"contact_account_id\",\"control_type\":\"text\"}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "771169ef",
  "provider": "salesforce",
  "name": "search_sobjects_soql",
  "skip": false,
  "input": {
   "field_list": "Email\nAccount$Account ID.Website",
   "limit": "150",
   "query": "AccountId = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"62aa61de\",\"path\":[\"Opportunity\", \"AccountId\"]}')}'",
   "sobject_name": "Contact",
   "table_list": "Account"
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "6d019ae1",
  "provider": "workato_smart_list",
  "name": "create_list",
  "skip": false,
  "input": {
   "list_name": "contact_emails",
   "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"771169ef\",\"path\":[\"Contact\"]}')",
   "primary_index": "Email"
  }
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "838e59b5",
  "provider": "workato_smart_list",
  "name": "query_list",
  "skip": false,
  "input": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "result_schema_json": "[{\"name\":\"no_of_contacts_with_same_email\",\"type\":\"number\",\"optional\":false,\"control_type\":\"number\"}]",
   "sql": "SELECT COUNT(#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"6d019ae1\",\"path\":[\"columns\", \"Email\"]}')}) FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"6d019ae1\",\"path\":[\"list_name\"]}')} WHERE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"6d019ae1\",\"path\":[\"columns\", \"Email\"]}')} LIKE '%#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c6f09d95\",\"path\":[\"contact_domain\"]}')}%'"
  }
 },
 {
  "keyword": "action",
  "number": 6,
  "as": "cca10bb2",
  "provider": "workato_smart_list",
  "name": "query_list",
  "skip": false,
  "input": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "result_schema_json": "[{\"name\":\"no_of_contacts_with_different_domain\",\"type\":\"number\",\"optional\":false,\"control_type\":\"number\"}]",
   "sql": "SELECT COUNT(#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"6d019ae1\",\"path\":[\"columns\", \"Email\"]}')}) FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"6d019ae1\",\"path\":[\"list_name\"]}')} WHERE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"6d019ae1\",\"path\":[\"columns\", \"Email\"]}')} NOT LIKE '%#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c6f09d95\",\"path\":[\"contact_domain\"]}')}%'"
  }
 },
 {
  "keyword": "action",
  "number": 7,
  "as": "0b31ab84",
  "provider": "workato_variable",
  "name": "update_variables",
  "skip": false,
  "input": {
   "account_website": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"771169ef\",\"path\":[\"Contact\", {\"path_element_type\": \"current_item\"}, \"Account\", \"Website\"]}')}",
   "different_email_domain_account_contacts": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"cca10bb2\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"no_of_contacts_with_different_domain\"]}').presence or 0",
   "name": "146a08ea-499d-474b-9cb4-066ebbddae70:c6f09d95:different_email_domain_account_contacts\n146a08ea-499d-474b-9cb4-066ebbddae70:c6f09d95:sames_domain_account_contacts\n146a08ea-499d-474b-9cb4-066ebbddae70:c6f09d95:account_website",
   "sames_domain_account_contacts": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"838e59b5\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"no_of_contacts_with_same_email\"]}').presence or 0"
  }
 },
 {
  "keyword": "if",
  "number": 8,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c6f09d95\",\"path\":[\"sames_domain_account_contacts\"]}') > _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c6f09d95\",\"path\":[\"different_email_domain_account_contacts\"]}') ? true : false",
     "operand": "is_true",
     "rhs": ""
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 9,
  "as": "eef02ac4",
  "provider": "workato_variable",
  "name": "update_variables",
  "skip": false,
  "input": {
   "contact_matched_account_contacts": "true",
   "name": "146a08ea-499d-474b-9cb4-066ebbddae70:c6f09d95:contact_matched_account_contacts"
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
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"771169ef\",\"path\":[\"Contact\", {\"path_element_type\": \"current_item\"}, \"Account\", \"Website\"]}')}",
     "operand": "contains",
     "rhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c6f09d95\",\"path\":[\"contact_domain\"]}')}"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 11,
  "as": "97f79031",
  "provider": "workato_variable",
  "name": "update_variables",
  "skip": false,
  "input": {
   "contact_matched_account_website": "true",
   "name": "146a08ea-499d-474b-9cb4-066ebbddae70:c6f09d95:contact_matched_account_website"
  }
 },
 {
  "keyword": "if",
  "number": 12,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c6f09d95\",\"path\":[\"contact_matched_account_contacts\"]}')}",
     "operand": "is_true",
     "rhs": ""
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c6f09d95\",\"path\":[\"contact_matched_account_website\"]}')}",
     "operand": "is_true",
     "rhs": ""
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 13,
  "as": "57e22d3b",
  "provider": "salesforce",
  "name": "update_sobject",
  "skip": false,
  "input": {
   "AccountId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c6f09d95\",\"path\":[\"account_id\"]}')}",
   "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c6f09d95\",\"path\":[\"contact_id\"]}')}",
   "sobject_name": "Contact"
  }
 },
 {
  "keyword": "action",
  "number": 14,
  "as": "e7c6c9fa",
  "provider": "lookup_table",
  "name": "add_entry",
  "skip": false,
  "input": {
   "lookup_table_id": "3236786",
   "parameters": {
    "col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c6f09d95\",\"path\":[\"opportunity_id\"]}')}",
    "col2": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c6f09d95\",\"path\":[\"contact_id\"]}')}",
    "col3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c6f09d95\",\"path\":[\"contact_email\"]}')}",
    "col4": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c6f09d95\",\"path\":[\"previous_account_id\"]}')}",
    "col5": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c6f09d95\",\"path\":[\"account_id\"]}')}",
    "col6": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c6f09d95\",\"path\":[\"sames_domain_account_contacts\"]}')}",
    "col7": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c6f09d95\",\"path\":[\"different_email_domain_account_contacts\"]}')}",
    "col8": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c6f09d95\",\"path\":[\"account_website\"]}')}",
    "col9": "=now.strftime(\"%Y-%m-%dT%H:%M:%S%:z\")"
   }
  }
 },
 {
  "keyword": "action",
  "number": 15,
  "as": "7a0b3861",
  "provider": "google_sheets",
  "name": "add_spreadsheet_row_v4",
  "skip": true,
  "input": {
   "data": {
    "col_1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"62aa61de\",\"path\":[\"OpportunityId\"]}')}",
    "col_2": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"62aa61de\",\"path\":[\"ContactId\"]}')}",
    "col_3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"62aa61de\",\"path\":[\"Contact\", \"Email\"]}')}",
    "col_4": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"62aa61de\",\"path\":[\"Contact\", \"AccountId\"]}')}",
    "col_5": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"62aa61de\",\"path\":[\"Opportunity\", \"AccountId\"]}')}",
    "col_6": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c6f09d95\",\"path\":[\"sames_domain_account_contacts\"]}')}",
    "col_7": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c6f09d95\",\"path\":[\"different_email_domain_account_contacts\"]}')}",
    "col_8": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c6f09d95\",\"path\":[\"account_website\"]}')}",
    "col_9": "=now.strftime(\"%Y-%m-%dT%H:%M:%S%:z\")"
   },
   "is_top_left": "false",
   "sheet": "Sheet1",
   "spreadsheet": "<anon>2AbC3DeF4GhI5JkL6MnO7PqR8StU9VwX0YzA1BcD2EfG</anon>",
   "team_drives": "my_drive"
  }
 }
]
'''

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "salesforce.search_records",
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
    "workato_runtime.update_variables",
    "salesforce.update_record",
    "lookup_table.add_entry",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "salesforce.update_record",
    "lookup_table.add_entry",
]
LOOKUP_TABLE_ID = "3236786"
# Step 15 (google_sheets.add_spreadsheet_row_v4) is DISABLED in the raw recipe
# ("skip": true); it is pinned in STRUCTURE_PINS and proven reached-but-skipped
# via the trace marker, but no sheets backend/seed/tool is ever involved.
SKIPPED_SHEETS_STEP_NUMBER = 15
SEED_SECTIONS = {"salesforce", "lookup_table"}
EXPECT_KEYS = (
    "trigger_filter_matched",
    "tools",
    "tool_expectations",
    "executed_action_count",
    "smart_list_sqls",
    "variable_updates",
    "lookup_final_tables",
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


def validate_87960973(raw: dict[str, Any]) -> dict[str, Any]:
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
            }
            for pin in actions
        ],
    }


def seed_87960973(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_87960973(raw)
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
    _require_expect_shape(expect, data)
    _require_lookup_section(seed_in.get("lookup_table"))
    sf_section = seed_in.get("salesforce")
    if expect["trigger_filter_matched"] is True:
        _require_salesforce_section(sf_section, trigger)
    elif sf_section is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} filter-false variants must not seed live Salesforce records "
            "(the body never runs; nothing may read them)"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "lookup_table": deepcopy(seed_in["lookup_table"]),
    }
    refs: dict[str, str] = {}
    if isinstance(sf_section, dict):
        provision = ctx.tools.call(
            "harness.salesforce.seed_records", {"salesforce": deepcopy(sf_section)}
        )
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
        refs = _salesforce_ref_tokens(sf_section, provision)
        out["salesforce_live"] = deepcopy(provision["state"])
        out["salesforce_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
        out["salesforce_ref_tokens"] = refs
    resolved_trigger = _replace_value(deepcopy(trigger), refs)
    _require_no_tokens(resolved_trigger, "trigger_input")
    resolved_expect = _replace_value(deepcopy(expect), refs)
    _require_no_tokens(resolved_expect, "expect")
    out["trigger"] = resolved_trigger
    out["expect"] = resolved_expect
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_87960973(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_87960973(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing resolved expect block")
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
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
    result["verifier"] = verify_87960973(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    for key in ("OpportunityId", "ContactId"):
        if not str(trigger.get(key) or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} trigger_input.{key} must be non-empty")
    if not isinstance(trigger.get("Role"), str):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.Role must be an explicit string "
            "(may be empty -- the filter's Role.blank? arm)"
        )
    contact = trigger.get("Contact")
    opportunity = trigger.get("Opportunity")
    if not isinstance(contact, dict) or not isinstance(opportunity, dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input requires Contact and Opportunity objects "
            "(the runtime filter and step 2 dereference them)"
        )
    email = str(contact.get("Email") or "")
    if "@" not in email or "." not in email.split("@")[-1]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.Contact.Email must be a real address "
            "(contact_domain = email.split('@').last.split('.').first)"
        )
    for parent, key in ((contact, "AccountId"), (opportunity, "AccountId")):
        if not str(parent.get(key) or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} trigger_input Contact/Opportunity.{key} required")
    if not str(opportunity.get("Name") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input.Opportunity.Name must be explicit")


def _require_expect_shape(expect: Any, data: dict[str, Any]) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    matched = expect.get("trigger_filter_matched")
    if not isinstance(matched, bool):
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
    if not isinstance(expect.get("smart_list_sqls"), list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.smart_list_sqls must be a list")
    if not isinstance(expect.get("variable_updates"), list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.variable_updates must be a list")
    if not isinstance(expect.get("lookup_final_tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.lookup_final_tables must pin the audit table")
    if matched is False:
        if tools or int(expect.get("executed_action_count") or 0) != 0:
            raise RuntimeError(
                f"recipe {RECIPE_ID} filter-false variants must expect zero actions and no tool calls"
            )
        if expect["smart_list_sqls"] or expect["variable_updates"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} filter-false variants must expect no smart-list/variable activity"
            )
        return
    if not tools or tools[0] != "salesforce.search_records":
        raise RuntimeError(
            f"recipe {RECIPE_ID} filter-true variants always run the step-3 Contact search first"
        )
    if len(expect["smart_list_sqls"]) != 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} filter-true variants must pin BOTH resolved COUNT SQLs"
        )
    if not isinstance(expect.get("declared_variables"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} filter-true variants must pin expect.declared_variables (step 2)"
        )
    write_tools = {"salesforce.update_record", "lookup_table.add_entry"}
    present = [tool for tool in tools if tool in write_tools]
    if present and set(present) != write_tools:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the step-12 write branch always performs BOTH live writes "
            f"(step 15 is disabled in the raw recipe); got {present}"
        )
    if present:
        if data.get("now") in (None, ""):
            raise RuntimeError(
                f"recipe {RECIPE_ID} write variants must pin data.now "
                "(the step-14 audit col9 renders now.strftime('%Y-%m-%dT%H:%M:%S%:z'))"
            )
        if expect.get("sheets_step_skipped") is not True:
            raise RuntimeError(
                f"recipe {RECIPE_ID} write variants must assert expect.sheets_step_skipped: true "
                "(the disabled step-15 sheets action is reached but never executed)"
            )
    if not present and expect.get("salesforce_unchanged") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} read-only variants must assert expect.salesforce_unchanged: true"
        )


def _require_lookup_section(section: Any) -> None:
    if not isinstance(section, dict) or not isinstance(section.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.lookup_table.tables")
    if sorted(section["tables"]) != [LOOKUP_TABLE_ID] or section["tables"][LOOKUP_TABLE_ID] != []:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must be exactly "
            f"{{{LOOKUP_TABLE_ID!r}: []}} (the audit table starts empty)"
        )


def _require_salesforce_section(sf_section: Any, trigger: dict[str, Any]) -> None:
    if not isinstance(sf_section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} filter-true variants require seed.salesforce")
    if sf_section.get("relationship_expansion") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.relationship_expansion must be true "
            "(step-3 Contact -> Account.Website nested read-back)"
        )
    records = sf_section.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records must be a non-empty list")
    refs_seen: set[str] = set()
    counts: dict[str, int] = {}
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
            for key in ("Name", "Website"):
                if not str(fields.get(key) or "").strip():
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} seeded Account requires explicit {key} "
                        "(Website drives the step-10 contains check)"
                    )
        if sobject == "Contact":
            for key in ("LastName", "Email", "AccountId"):
                if not str(fields.get(key) or "").strip():
                    raise RuntimeError(f"recipe {RECIPE_ID} seeded Contact requires explicit {key}")
        if sobject == "Opportunity":
            for key in ("Name", "StageName", "CloseDate", "AccountId"):
                if not str(fields.get(key) or "").strip():
                    raise RuntimeError(f"recipe {RECIPE_ID} seeded Opportunity requires explicit {key}")
    if counts.get("Account", 0) < 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed needs the opportunity Account AND the contact's previous "
            "Account (the trigger filter requires them to differ)"
        )
    if counts.get("Opportunity", 0) != 1 or counts.get("Contact", 0) < 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed needs exactly one Opportunity and the trigger Contact"
        )
    token_map = {
        "OpportunityId": str(trigger.get("OpportunityId") or ""),
        "ContactId": str(trigger.get("ContactId") or ""),
        "Contact.AccountId": str((trigger.get("Contact") or {}).get("AccountId") or ""),
        "Opportunity.AccountId": str((trigger.get("Opportunity") or {}).get("AccountId") or ""),
    }
    expected_tokens = {f"${ref.upper()}_ID" for ref in refs_seen}
    for label, token in token_map.items():
        if token not in expected_tokens:
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger_input.{label} must be a $<REF>_ID token of a seeded "
                f"record (got {token!r}); live ids are only known after provisioning"
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


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("salesforce_live"), dict):
        out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
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
