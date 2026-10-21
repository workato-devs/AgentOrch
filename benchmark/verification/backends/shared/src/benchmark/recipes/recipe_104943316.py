from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_104943316


RECIPE_ID = "104943316"
SEED_TYPE = "salesforce_campaign_activity_timezone_region_variant"
TRACK = "live_salesforce_campaign_activity_timezone_region_update"
TRIGGER_PROVIDER = "salesforce"
TRIGGER_NAME = "new_custom_object"
TRIGGER_AS = "eb620bea"
SEARCH_STEP_AS = "00734942"
LOOKUP_STEP_AS = "149f4719"
UPDATE_STEP_AS = "0acbf52d"
SOBJECT = "Campaign_Activity__c"
LOOKUP_TABLE_ID = "3817174"
CA_ID_TOKEN = "$CA_ID"
# The deliberate non-owned Campaign_Activity__c id the record_not_found
# variant sends: the harness search over owned records returns 0 matches
# DETERMINISTICALLY for it (read-only search, no ownership guard fires) --
# same NON_OWNED_ID pattern as registered recipe_88708198.
NON_OWNED_ID = "a0X000000000000AAA"

# salesforce.new_custom_object (as eb620bea, sobject Campaign_Activity__c,
# since_offset -3600, trigger field_list Id/Name/CreatedDate/Email__c/
# Browser_Timezone__c) with a TRIGGER FILTER: Browser_Timezone__c present.
# The trigger payload dereferences exactly TWO fields: Id (step-2 search
# filter) and Browser_Timezone__c (the filter condition) -- trigger_input
# carries exactly those two keys and the filter always matches (a blank
# timezone would mean the trigger simply never fires: zero actions, not a
# recipe branch).
#   2  salesforce.search_sobjects 00734942 (LIVE): Campaign_Activity__c,
#      filter Id = trigger.Id, limit 150, 38-field field_list -> engine
#      routes to salesforce.search_records {sobject, filters:[{field:'Id',
#      value}], limit '150'} (field_list is SELECT-column metadata only).
#      Result exposes rows under result['Campaign_Activity__c'] +
#      list_size (live_tools sf_search_records).
#   IF 3 (00734942.list_size greater_than '0'):
#     4  lookup_table.search_entries 149f4719 (mock table 3817174 'CA
#        Region<>Browser Timezone'): col1 = search current_item
#        Browser_Timezone__c (the LIVE re-read record's timezone, not the
#        trigger's -- variants keep them equal by seeding the record).
#     IF 5 (149f4719.entries size greater_than '0'):
#       6  salesforce.update_sobject 0acbf52d (LIVE): id = search
#          current_item Id, Region__c = entries current_item entry.col2,
#          Person_Country__c = entry.col3 -> salesforce.update_record.
#          current_item on entries OUTSIDE a foreach = FIRST entry.
# No catch -- a live failure fails the job (fail-fast; force_action_error
# is rejected).
#
# Live backend: Campaign_Activity__c EXISTS in the benchmark org (2026-07-08
# EntityDefinition probe: 47 fields). Exactly 6 of the recipe's 38 search
# fields are missing -- Worked_By__c, Opportunity__c, Manager_Notes__c,
# Meeting_Attended_At__c, Meeting_Scheduled_At__c, Opportunity_Created_At__c
# -- all plain unmanaged __c fields, re-ensured on every seed via the
# schema-in-seed ensure_custom_field path (idempotent; 8-recipe precedent
# incl. recipe_88708198). The Bizible_*__c fields here are ORDINARY custom
# fields ON Campaign_Activity__c (already present), NOT bizible2__ managed-
# package fields -- no stand-in mapping needed. The recipe never issues a
# SOQL query text (the search is an Id FILTER), so strict_soql_conditions
# is NOT seeded (it would be dead state).
# Workato-internal mock: lookup table 3817174.
# Cleanup: the seed-created Campaign_Activity__c record is benchmark-owned
# and deleted in the runner's finally; provisioned SCHEMA persists by
# design (it is schema, not data).

_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "eb620bea",
  "provider": "salesforce",
  "name": "new_custom_object",
  "skip": false,
  "input": {
   "field_list": "Id\nName\nCreatedDate\nEmail__c\nBrowser_Timezone__c",
   "since_offset": "-3600",
   "sobject_name": "Campaign_Activity__c"
  },
  "filter": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"eb620bea\",\"path\":[\"Browser_Timezone__c\"]}')}",
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
  "as": "00734942",
  "provider": "salesforce",
  "name": "search_sobjects",
  "skip": false,
  "input": {
   "Id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"eb620bea\",\"path\":[\"Id\"]}')}",
   "field_list": "Id\nOwnerId\nName\nCreatedDate\nCreatedById\nBrowser_Timezone__c\nRegion__c\nPerson_Sub_Region__c\nCategory__c\nFit__c\nWorked_By__c\nStage__c\nLead__c\nContact__c\nOpportunity__c\nCampaign__c\nNotes__c\nSDR_Notes__c\nManager_Notes__c\nUTM_Medium__c\nUTM_Source__c\nUTM_Campaign__c\nUTM_Content__c\nUTM_Term__c\nEmail__c\nMeeting_Attended_At__c\nCompany_Name__c\nMeeting_Scheduled_At__c\nOpportunity_Created_At__c\nCreative_ID__c\nLead_Gen_Form_ID__c\nForm_Type__c\nLanding_Page__c\nBizible_Landing_Page__c\nBizible_Touchpoint__c\nBizible_Form_URL__c\nBizible_Referrer_Page__c",
   "limit": "150",
   "sobject_name": "Campaign_Activity__c"
  }
 },
 {
  "keyword": "if",
  "number": 3,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"00734942\",\"path\":[\"list_size\"]}')}",
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
  "number": 4,
  "as": "149f4719",
  "provider": "lookup_table",
  "name": "search_entries",
  "skip": false,
  "input": {
   "lookup_table_id": "3817174",
   "parameters": {
    "col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"00734942\",\"path\":[\"Campaign_Activity__c\", {\"path_element_type\": \"current_item\"}, \"Browser_Timezone__c\"]}')}"
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
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"149f4719\",\"path\":[\"entries\", {\"path_element_type\": \"size\"}]}')}",
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
  "number": 6,
  "as": "0acbf52d",
  "provider": "salesforce",
  "name": "update_sobject",
  "skip": false,
  "input": {
   "Person_Country__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"149f4719\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col3\"]}')}",
   "Region__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"149f4719\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col2\"]}')}",
   "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"00734942\",\"path\":[\"Campaign_Activity__c\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}",
   "sobject_name": "Campaign_Activity__c"
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

# Schema-in-seed: the 6 recipe search fields missing from the live org's
# 47-field Campaign_Activity__c (2026-07-08 probe). ensure_custom_field is
# idempotent (re-ensures FLS, never redeploys). Types are benchmark
# stand-ins: the recipe only ever SELECTS these columns (they read back
# null); Opportunity__c/Worked_By__c would be lookups in the source org --
# a Text stand-in keeps provisioning dependency-free.
SF_SCHEMA: list[dict[str, str]] = [
    {"sobject": SOBJECT, "field": "Worked_By__c", "sf_type": "Text"},
    {"sobject": SOBJECT, "field": "Opportunity__c", "sf_type": "Text"},
    {"sobject": SOBJECT, "field": "Manager_Notes__c", "sf_type": "TextArea"},
    {"sobject": SOBJECT, "field": "Meeting_Attended_At__c", "sf_type": "DateTime"},
    {"sobject": SOBJECT, "field": "Meeting_Scheduled_At__c", "sf_type": "DateTime"},
    {"sobject": SOBJECT, "field": "Opportunity_Created_At__c", "sf_type": "DateTime"},
]
# Fields a variant may seed on the benchmark-owned record: writable plain
# columns from the recipe's search field_list (system audit fields and the
# 6 provisioned select-as-null stand-ins excluded).
ALLOWED_SEED_FIELDS = {
    "Name",
    "Browser_Timezone__c",
    "Email__c",
    "Company_Name__c",
    "Region__c",
    "Person_Country__c",
    "Person_Sub_Region__c",
    "Category__c",
    "Fit__c",
    "Stage__c",
    "Notes__c",
    "SDR_Notes__c",
    "UTM_Medium__c",
    "UTM_Source__c",
    "UTM_Campaign__c",
    "UTM_Content__c",
    "UTM_Term__c",
    "Form_Type__c",
    "Landing_Page__c",
}
EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.search_records",
    "lookup_table.search_entries",
    "salesforce.update_record",
]
ALLOWED_TOOLS: list[str] = list(EXPECTED_RAW_TOOLS)
FILTER_FALSE_CASE = "trigger_filter_false"
CASES = (
    "timezone_match_update",
    "timezone_not_in_table",
    "record_not_found",
    "multi_entry_first_wins",
    FILTER_FALSE_CASE,
)
REQUIRED_EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "search_list_size",
    "lookup_entries_count",
    "updated_fields",
    "final_record_fields",
    "record_untouched",
    "steps_absent_from_trace",
)
# trigger_filter_false never starts the job: the step-level pins
# (search/lookup/update) do not exist, only the zero-action contract and the
# untouched seeded record.
FILTER_FALSE_EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "trigger_filter_matched",
    "final_record_fields",
)
_REF_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_SF_ID_RE = re.compile(r"[a-zA-Z0-9]{15,18}")


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


def validate_104943316(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
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
    # Semantic pins on the drift-prone pieces.
    trigger_filter = raw.get("filter") or {}
    conditions = trigger_filter.get("conditions") or []
    if (
        len(conditions) != 1
        or "Browser_Timezone__c" not in str(conditions[0].get("lhs") or "")
        or str(conditions[0].get("operand") or "") != "present"
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger filter changed -- the always-matching "
            f"Browser_Timezone__c-present analysis no longer holds: {trigger_filter!r}"
        )
    update_pin = next(pin for pin in actual if pin["as"] == UPDATE_STEP_AS)
    update_fields = set(update_pin["input"]) - {"id", "sobject_name"}
    if update_fields != {"Region__c", "Person_Country__c"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} update field set changed: {sorted(update_fields)}"
        )
    lookup_pin = next(pin for pin in actual if pin["as"] == LOOKUP_STEP_AS)
    if str(lookup_pin["input"].get("lookup_table_id") or "") != LOOKUP_TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} lookup table id changed")
    actions = [pin for pin in actual if pin["keyword"] == "action"]
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "sobject": SOBJECT,
        "lookup_table_id": LOOKUP_TABLE_ID,
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


def seed_104943316(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_104943316(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: a forced action error would fail the "
            "whole run instead of exercising a recipe branch"
        )
    if data.get("job_context") is not None:
        raise RuntimeError(f"recipe {RECIPE_ID} never reads job_context (dead seed state)")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    expect = data.get("expect")
    _require_expect_common(expect)
    case = expect["case"]
    _require_trigger_shape(trigger, case)
    record_fields, lookup_rows = _require_case_seed(case, seed_in, trigger, expect)
    provision = ctx.tools.call(
        "harness.salesforce.seed_records", {"salesforce": deepcopy(seed_in["salesforce"])}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    refs = _ref_ids(provision)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": dict(refs),
        "trigger": _replace_tokens(trigger, refs),
        "expect": _replace_tokens(deepcopy(expect), refs),
    }
    _require_no_tokens(out["trigger"], "trigger")
    _require_no_tokens(out["expect"], "expect")
    if lookup_rows is not None:
        out["lookup_table"] = deepcopy(seed_in["lookup_table"])
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_104943316(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_104943316(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} every variant seeds a live Campaign_Activity__c record "
            "(non-match variants prove it untouched); missing salesforce_live state"
        )
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    raw_execution: dict[str, Any] | None = None
    cleanup: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = dict(ctx.tools.call("harness.salesforce.snapshot", {}))
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = dict(ctx.tools.call("harness.salesforce.snapshot", {}))
    finally:
        # Required cleanup: the run owns the seeded Campaign_Activity__c
        # record; delete it whether or not the run completed. Provisioned
        # schema persists by design.
        cleanup = ctx.tools.call("harness.salesforce.cleanup", {})
    details["cleanup_response"] = {"salesforce": cleanup}
    if not (cleanup or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce cleanup failed: {cleanup}")
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_104943316(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any], case: str) -> None:
    if sorted(trigger.keys()) != sorted(["Id", "Browser_Timezone__c"]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the two dereferenced "
            f"trigger fields Id + Browser_Timezone__c; got {sorted(trigger.keys())}"
        )
    tz = trigger.get("Browser_Timezone__c")
    if case == FILTER_FALSE_CASE:
        if not isinstance(tz, str) or tz.strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} {FILTER_FALSE_CASE} requires a blank "
                f"Browser_Timezone__c (blank fails the root 'present' filter); got {tz!r}"
            )
    elif not isinstance(tz, str) or not tz.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger Browser_Timezone__c must be non-empty on the "
            f"filter-matched cases (a blank value is the {FILTER_FALSE_CASE} case); got {tz!r}"
        )
    record_id = trigger.get("Id")
    if record_id not in (CA_ID_TOKEN,) and record_id != NON_OWNED_ID:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger Id must be the {CA_ID_TOKEN} seed token or the "
            f"pinned non-owned id {NON_OWNED_ID!r}; got {record_id!r}"
        )


def _require_expect_common(expect: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    if expect.get("case") not in CASES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.case must be one of {CASES}")
    required = (
        FILTER_FALSE_EXPECT_KEYS
        if expect.get("case") == FILTER_FALSE_CASE
        else REQUIRED_EXPECT_KEYS
    )
    missing = [key for key in required if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(required))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if not isinstance(expect.get("final_record_fields"), dict) or not expect["final_record_fields"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_record_fields must pin the seeded "
            "record's final live field values"
        )


def _require_salesforce_seed(section: Any, *, with_timezone: bool = True) -> dict[str, Any]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["records", "schema"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce must be exactly {{'schema': ..., "
            f"'records': ...}}; got {sorted(section.keys()) if isinstance(section, dict) else section!r}"
        )
    if section.get("schema") != SF_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must be the pinned 6-field "
            "Campaign_Activity__c schema (the org probe found exactly these missing)"
        )
    records = section.get("records")
    if not isinstance(records, list) or len(records) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.records must contain exactly one "
            "benchmark-owned Campaign_Activity__c record (current_item = FIRST search "
            "row; a second record would be dead or order-hazardous state)"
        )
    record = records[0]
    if (
        not isinstance(record, dict)
        or record.get("sobject") != SOBJECT
        or str(record.get("ref") or "") != "ca"
        or not isinstance(record.get("fields"), dict)
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed record must be {{sobject: {SOBJECT}, ref: 'ca', "
            f"fields: ...}}; got {record!r}"
        )
    fields = record["fields"]
    unknown = sorted(set(fields) - ALLOWED_SEED_FIELDS)
    if unknown:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed record carries fields outside the recipe's "
            f"writable search columns: {unknown}"
        )
    if with_timezone:
        required_keys = ("Name", "Browser_Timezone__c")
    else:
        if "Browser_Timezone__c" in fields:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {FILTER_FALSE_CASE} seeds a record WITHOUT "
                "Browser_Timezone__c (a present value would satisfy the root filter)"
            )
        required_keys = ("Name",)
    for key in required_keys:
        if not isinstance(fields.get(key), str) or not str(fields.get(key)).strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed record requires a non-empty {key}"
            )
    for key, value in fields.items():
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed record field {key} must be a non-empty "
                f"string; got {value!r}"
            )
    return fields


def _require_lookup_seed(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table must be exactly {{'tables': ...}}"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [LOOKUP_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must declare exactly table "
            f"{LOOKUP_TABLE_ID!r}"
        )
    rows = tables[LOOKUP_TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} lookup table {LOOKUP_TABLE_ID} must carry rows -- the "
            "no-match case proves the col1 filter via decoy rows, not an empty table"
        )
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != ["col1", "col2", "col3"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} lookup row {idx} must be exactly "
                f"{{col1 (timezone), col2 (region), col3 (country)}}; got {row!r}"
            )
        for key, value in row.items():
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} lookup row {idx}.{key} must be a non-empty "
                    f"string; got {value!r}"
                )
    return [dict(row) for row in rows]


def _require_case_seed(
    case: str,
    seed_in: dict[str, Any],
    trigger: dict[str, Any],
    expect: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]] | None]:
    if case == FILTER_FALSE_CASE:
        if sorted(seed_in.keys()) != ["salesforce"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} case {case!r} must seed exactly ['salesforce'] "
                f"(the job never starts; lookup rows would be dead seed state); got "
                f"{sorted(seed_in.keys())}"
            )
        record_fields = _require_salesforce_seed(seed_in["salesforce"], with_timezone=False)
        if trigger.get("Id") != CA_ID_TOKEN:
            raise RuntimeError(
                f"recipe {RECIPE_ID} case {case!r} must target the seeded record via "
                f"the {CA_ID_TOKEN} token"
            )
        derived = (
            expect.get("trigger_filter_matched") is False,
            expect.get("executed_action_count") == 0,
            expect.get("tools") == [],
            expect.get("tool_expectations") == [],
        )
        if not all(derived):
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect block is inconsistent with case {case!r} "
                f"(zero actions, no tools, trigger_filter_matched false): {expect!r}"
            )
        _require_final_fields(expect, record_fields)
        return record_fields, None
    reaches_lookup = case != "record_not_found"
    expected_sections = ["lookup_table", "salesforce"] if reaches_lookup else ["salesforce"]
    if sorted(seed_in.keys()) != expected_sections:
        raise RuntimeError(
            f"recipe {RECIPE_ID} case {case!r} must seed exactly {expected_sections} "
            f"(no dead seed state); got {sorted(seed_in.keys())}"
        )
    record_fields = _require_salesforce_seed(seed_in["salesforce"])
    lookup_rows = _require_lookup_seed(seed_in["lookup_table"]) if reaches_lookup else None
    tz = str(record_fields["Browser_Timezone__c"])
    if reaches_lookup:
        if trigger.get("Id") != CA_ID_TOKEN:
            raise RuntimeError(
                f"recipe {RECIPE_ID} case {case!r} must target the seeded record via "
                f"the {CA_ID_TOKEN} token"
            )
        if str(trigger.get("Browser_Timezone__c")) != tz:
            raise RuntimeError(
                f"recipe {RECIPE_ID} the trigger payload IS the created record: its "
                f"Browser_Timezone__c must equal the seeded field ({tz!r})"
            )
        matching = [row for row in lookup_rows if row["col1"] == tz]
        decoys = [row for row in lookup_rows if row["col1"] != tz]
        if not decoys:
            raise RuntimeError(
                f"recipe {RECIPE_ID} case {case!r} needs at least one decoy lookup row "
                "with a different col1 timezone (proves the search filters)"
            )
    else:
        matching = []
        if trigger.get("Id") != NON_OWNED_ID:
            raise RuntimeError(
                f"recipe {RECIPE_ID} record_not_found must send the pinned non-owned id "
                f"{NON_OWNED_ID!r} as trigger.Id"
            )
    if case == "timezone_match_update":
        if len(matching) != 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} timezone_match_update needs exactly ONE matching "
                f"lookup row; got {len(matching)}"
            )
        _require_case_expect(
            expect,
            search_list_size=1,
            lookup_entries_count=1,
            updated_fields={"Region__c": matching[0]["col2"], "Person_Country__c": matching[0]["col3"]},
            record_untouched=False,
            absent=[],
            tools=EXPECTED_RAW_TOOLS,
            action_count=3,
        )
    elif case == "multi_entry_first_wins":
        if len(matching) < 2:
            raise RuntimeError(
                f"recipe {RECIPE_ID} multi_entry_first_wins needs >=2 lookup rows with "
                f"the record's timezone; got {len(matching)}"
            )
        if matching[0]["col2"] == matching[1]["col2"] and matching[0]["col3"] == matching[1]["col3"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} multi_entry_first_wins rows must differ in "
                "col2/col3 (otherwise first-wins is unobservable)"
            )
        _require_case_expect(
            expect,
            search_list_size=1,
            lookup_entries_count=len(matching),
            updated_fields={"Region__c": matching[0]["col2"], "Person_Country__c": matching[0]["col3"]},
            record_untouched=False,
            absent=[],
            tools=EXPECTED_RAW_TOOLS,
            action_count=3,
        )
    elif case == "timezone_not_in_table":
        if matching:
            raise RuntimeError(
                f"recipe {RECIPE_ID} timezone_not_in_table must keep the record's "
                f"timezone OUT of the lookup col1 values; found {len(matching)} matches"
            )
        _require_case_expect(
            expect,
            search_list_size=1,
            lookup_entries_count=0,
            updated_fields=None,
            record_untouched=True,
            absent=[UPDATE_STEP_AS],
            tools=EXPECTED_RAW_TOOLS[:2],
            action_count=2,
        )
    else:  # record_not_found
        _require_case_expect(
            expect,
            search_list_size=0,
            lookup_entries_count=None,
            updated_fields=None,
            record_untouched=True,
            absent=[LOOKUP_STEP_AS, UPDATE_STEP_AS],
            tools=EXPECTED_RAW_TOOLS[:1],
            action_count=1,
        )
    _require_tool_expectations(expect, trigger, tz)
    _require_final_fields(expect, record_fields)
    return record_fields, lookup_rows


def _require_case_expect(
    expect: dict[str, Any],
    *,
    search_list_size: int,
    lookup_entries_count: int | None,
    updated_fields: dict[str, Any] | None,
    record_untouched: bool,
    absent: list[str],
    tools: list[str],
    action_count: int,
) -> None:
    checks = (
        expect.get("executed_action_count") == action_count,
        expect.get("tools") == tools,
        expect.get("search_list_size") == search_list_size,
        expect.get("lookup_entries_count") == lookup_entries_count,
        expect.get("updated_fields") == updated_fields,
        expect.get("record_untouched") is record_untouched,
        expect.get("steps_absent_from_trace") == absent,
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with case "
            f"{expect.get('case')!r} (derived: list_size {search_list_size}, entries "
            f"{lookup_entries_count}, update {updated_fields}, absent {absent}): {expect!r}"
        )


def _require_tool_expectations(
    expect: dict[str, Any],
    trigger: dict[str, Any],
    tz: str,
) -> None:
    items = expect.get("tool_expectations")
    tools = expect.get("tools") or []
    if (
        not isinstance(items, list)
        or len(items) != len(tools)
        or not all(isinstance(item, dict) for item in items)
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin every executed call"
        )
    search_item = items[0]
    checks = [
        search_item.get("tool") == "salesforce.search_records",
        search_item.get("args_contains")
        == {
            "sobject": SOBJECT,
            "limit": "150",
            "filters": [{"field": "Id", "value": trigger.get("Id")}],
        },
        search_item.get("result_count") == expect.get("search_list_size"),
    ]
    if len(items) >= 2:
        lookup_item = items[1]
        checks += [
            lookup_item.get("tool") == "lookup_table.search_entries",
            lookup_item.get("lookup_table_id") == LOOKUP_TABLE_ID,
            lookup_item.get("args_contains")
            == {"lookup_table_id": LOOKUP_TABLE_ID, "parameters": {"col1": tz}},
            lookup_item.get("result_count") == expect.get("lookup_entries_count"),
        ]
    if len(items) == 3:
        update_item = items[2]
        checks += [
            update_item.get("tool") == "salesforce.update_record",
            update_item.get("args_contains")
            == {
                "sobject": SOBJECT,
                "id": trigger.get("Id"),
                "fields": expect.get("updated_fields"),
            },
        ]
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations do not pin the derived ground truth: {items!r}"
        )


def _require_final_fields(expect: dict[str, Any], record_fields: dict[str, Any]) -> None:
    final_fields = expect.get("final_record_fields") or {}
    updated = expect.get("updated_fields") or {}
    derived = dict(record_fields)
    derived.update(updated)
    for key, value in final_fields.items():
        if key not in derived or derived[key] != value:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.final_record_fields[{key!r}] contradicts "
                f"the seeded/updated ground truth ({derived.get(key)!r} vs {value!r})"
            )
    must_pin = set(record_fields) | set(updated)
    missing = sorted(must_pin - set(final_fields))
    if missing:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_record_fields must pin every seeded and "
            f"updated field; missing {missing}"
        )


def _ref_ids(provision: dict[str, Any]) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    records = ((snapshot.get("salesforce") or {}).get("records") or [])
    owned = [record for record in records if isinstance(record, dict) and not record.get("read_only")]
    if len(owned) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expected exactly one provisioned record; got {len(owned)}"
        )
    live_id = str(owned[0].get("id") or "")
    if not _SF_ID_RE.fullmatch(live_id):
        raise RuntimeError(f"recipe {RECIPE_ID} provisioned record id looks invalid: {live_id!r}")
    return {CA_ID_TOKEN: live_id}


def _replace_tokens(value: Any, refs: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_tokens(item, refs) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_tokens(item, refs) for item in value]
    if isinstance(value, str):
        out = value
        for token, replacement in refs.items():
            out = out.replace(token, replacement)
        return out
    return value


def _require_no_tokens(value: dict[str, Any], label: str) -> None:
    leftover = _REF_TOKEN_RE.findall(json.dumps(value))
    if leftover:
        raise RuntimeError(f"recipe {RECIPE_ID} {label} has unresolved seed tokens: {leftover}")


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
