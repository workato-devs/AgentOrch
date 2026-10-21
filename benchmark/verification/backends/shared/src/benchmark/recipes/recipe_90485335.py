from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_90485335


RECIPE_ID = "90485335"
SEED_TYPE = "salesforce_partner_customer_linker_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "salesforce"
TRIGGER_NAME = "new_custom_object"
TRIGGER_AS = "2ac33b95"
TRIGGER_SOBJECT = "Account"
TRIGGER_FIELD_LIST = "Customer_is_a_Partner__c\nName\nRecordTypeId\nId"
TRIGGER_ROW_KEYS = {"Customer_is_a_Partner__c", "Id", "Name", "RecordTypeId"}
# Source-org record type ids hardcoded in the raw recipe. Record type ids are
# ORG-GENERATED: they cannot be chosen, re-created, or assigned in the
# benchmark org (Salesforce rejects a foreign RecordTypeId with
# INVALID_CROSS_REFERENCE_KEY on create), so no live Account can ever carry
# either value.
CUSTOMER_RT_ID = "012o0000000teVpAAI"  # trigger IF-2 rhs + ELSE-arm search filter
PARTNER_RT_ID = "012o0000000tYvxAAE"  # IF-arm search filter
NAME_SUFFIX = " - Partner"
CUSTOMER_STOP = {"number": 5, "as": "c8723ba4"}
PARTNER_STOP = {"number": 10, "as": "e28e0a52"}
TRIGGER_ID_TOKEN = "$TRIGGER_ACCOUNT_ID"
# Schema-in-seed contract (128901328 precedent): the trigger field_list and
# both (dead) update steps reference Account.Customer_is_a_Partner__c, so the
# field is provisioned once as real org schema (never data; cleanup keeps it).
REQUIRED_SCHEMA = [
    {"sobject": "Account", "field": "Customer_is_a_Partner__c", "sf_type": "Text"},
]
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")

# salesforce.new_custom_object on Account (as 2ac33b95, since_offset no_limit,
# field_list Customer_is_a_Partner__c/Name/RecordTypeId/Id), replayed as a
# deterministic seeded payload (101641436 / 64106452 precedent). Body:
#   2  IF trigger.RecordTypeId == '012o0000000teVpAAI' (customer arm):
#      3  salesforce.search_sobjects 01b64088 Account:
#         Name = '#{trigger.Name} - Partner' AND RecordTypeId =
#         '012o0000000tYvxAAE', limit 150
#      4  IF 01b64088.Account.size == 0 -> 5 STOP c8723ba4 (no error)
#      6  salesforce.update_sobject d81f9ae2: id = trigger.Id,
#         Customer_is_a_Partner__c = first matched partner's Id
#   7  ELSE (partner arm):
#      8  salesforce.search_sobjects dce8845f Account:
#         Name = trigger.Name.gsub(" - Partner", "") AND RecordTypeId =
#         '012o0000000teVpAAI', limit 150
#      9  IF dce8845f.Account.size == 0 -> 10 STOP e28e0a52 (no error)
#      11 salesforce.update_sobject 96cd9744: id = first matched customer's
#         Id, Customer_is_a_Partner__c = trigger.Id
#
# DEAD LIVE BRANCHES (coordinator decision: faithful 2-variant build).
# Both update steps (6 and 11) are provably unreachable in the benchmark org:
# each sits behind a search whose field filters include a RecordTypeId
# EQUALITY against a source-org id ('012o0000000tYvxAAE' / '012o0000000teVpAAI'
# -- pinned verbatim in STRUCTURE_PINS). Record type ids are org-generated;
# Salesforce rejects INVALID_CROSS_REFERENCE_KEY when creating a record with a
# foreign RecordTypeId, and the benchmark org's own Accounts read back with
# null/its-own RT ids -- so both searches return size 0 on every live run and
# every reachable path ends at a clean STOP (same class as the 85944334
# recordtype_skip and 59346468 dead-app-loop findings). The two stop variants
# below are therefore the COMPLETE reachable coverage:
# - variant_00 customer_arm_no_partner_stop: IF arm -> search 3 -> 0 rows ->
#   STOP 5.
# - variant_01 partner_arm_no_customer_stop: ELSE arm (gsub name strip) ->
#   search 8 -> 0 rows -> STOP 10.
# The counterfactual (offline stub serving a record that carries the foreign
# RT id) executes the update arm fine, proving the dead code is a LIVE-DATA
# impossibility, not an engine gap.
#
# Zero-match honesty: every variant live-seeds a DECOY Account whose Name
# equals the search's exact Name filter, with RecordTypeId in read_fields so
# the search compares the decoy's REAL live RT value against the hardcoded
# source-org id. The 0-result is thereby attributable to the RecordTypeId
# filter, never to a trivially empty org.
#
# Trigger payload / live-record tension (triage-flagged): the seeded trigger
# payload carries the source-org RecordTypeId as REPLAYED TRIGGER DATA while
# trigger.Id/Name are the live seeded Account's real values ($TRIGGER_ACCOUNT_ID
# threading) -- the live record itself cannot carry that RT id, which is
# exactly the dead-branch proof above.
#
# Backends: salesforce LIVE (benchmark-owned Accounts; Customer_is_a_Partner__c
# via schema-in-seed). Cleanup: required (live records) -- harness cleanup in a
# finally block; both variants must leave Customer_is_a_Partner__c null on
# both accounts (the dead updates never fire), pinned via
# expect.final_fields_by_name.

_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "2ac33b95",
  "provider": "salesforce",
  "name": "new_custom_object",
  "skip": false,
  "input": {
   "field_list": "Customer_is_a_Partner__c\nName\nRecordTypeId\nId",
   "since_offset": "no_limit",
   "sobject_name": "Account"
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
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2ac33b95\",\"path\":[\"RecordTypeId\"]}')}",
     "operand": "equals_to",
     "rhs": "012o0000000teVpAAI"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "01b64088",
  "provider": "salesforce",
  "name": "search_sobjects",
  "skip": false,
  "input": {
   "Name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2ac33b95\",\"path\":[\"Name\"]}')} - Partner",
   "RecordTypeId": "012o0000000tYvxAAE",
   "field_list": "Name\nId\nRecordTypeId",
   "limit": "150",
   "sobject_name": "Account"
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
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"01b64088\",\"path\":[\"Account\", {\"path_element_type\": \"size\"}]}')}",
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
  "as": "c8723ba4",
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
  "as": "d81f9ae2",
  "provider": "salesforce",
  "name": "update_sobject",
  "skip": false,
  "input": {
   "Customer_is_a_Partner__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"01b64088\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}",
   "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2ac33b95\",\"path\":[\"Id\"]}')}",
   "sobject_name": "Account"
  }
 },
 {
  "keyword": "else",
  "number": 7,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {}
 },
 {
  "keyword": "action",
  "number": 8,
  "as": "dce8845f",
  "provider": "salesforce",
  "name": "search_sobjects",
  "skip": false,
  "input": {
   "Name": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2ac33b95\",\"path\":[\"Name\"]}').gsub(\" - Partner\", \"\")",
   "RecordTypeId": "012o0000000teVpAAI",
   "field_list": "Id\nName\nRecordTypeId",
   "limit": "150",
   "sobject_name": "Account"
  }
 },
 {
  "keyword": "if",
  "number": 9,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"dce8845f\",\"path\":[\"Account\", {\"path_element_type\": \"size\"}]}')}",
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
  "number": 10,
  "as": "e28e0a52",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "stop_with_error": "false"
  }
 },
 {
  "keyword": "action",
  "number": 11,
  "as": "96cd9744",
  "provider": "salesforce",
  "name": "update_sobject",
  "skip": false,
  "input": {
   "Customer_is_a_Partner__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2ac33b95\",\"path\":[\"Id\"]}')}",
   "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"dce8845f\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}",
   "sobject_name": "Account"
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.search_records",
]
# The update_sobject steps are provably dead live (see above); only the search
# is ever executed/exposed (59346468 dead-branch precedent).
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
]
EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "stopped",
    "stop_step_number",
    "stop_step_as",
    "arm",
    "searched_name",
    "rt_filter_id",
    "final_fields_by_name",
)
OPTIONAL_EXPECT_KEYS = {"case"}


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


def validate_90485335(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger 'as' changed: {raw.get('as')!r}")
    trigger_cfg = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    if str(trigger_cfg.get("sobject_name") or "") != TRIGGER_SOBJECT:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger sobject changed")
    if str(trigger_cfg.get("field_list") or "") != TRIGGER_FIELD_LIST:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger field list changed")
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
    # The dead-branch proof rests on these exact source-org RT filters; scream
    # if they ever drift (redundant with the full pins, but load-bearing).
    by_as = {pin["as"]: pin for pin in actual if pin.get("as")}
    if by_as["01b64088"]["input"].get("RecordTypeId") != PARTNER_RT_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} IF-arm search RT filter changed")
    if by_as["dce8845f"]["input"].get("RecordTypeId") != CUSTOMER_RT_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} ELSE-arm search RT filter changed")
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


def seed_90485335(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_90485335(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    arm, searched_name, rt_filter_id, stop_pin = _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"salesforce"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    salesforce_section = seed_in.get("salesforce")
    _require_salesforce_section(salesforce_section, trigger, searched_name)
    expect = data.get("expect")
    _require_expect_shape(expect, arm, searched_name, rt_filter_id, stop_pin, trigger)
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole "
            "run instead of exercising a recipe branch"
        )
    provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": salesforce_section})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    refs = _salesforce_ref_tokens(salesforce_section, provision)
    trigger = _replace_value(trigger, refs)
    _require_resolved(trigger, "trigger")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": _replace_value(deepcopy(expect), refs),
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": refs,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    _require_resolved(out["expect"], "expect")
    return attach_variant(out, ctx)


def run_90485335(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_90485335(raw)
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    cleanup_response: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = _snapshot(ctx)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx)
    finally:
        # Required cleanup: this run live-seeds benchmark-owned Accounts.
        cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
        details["cleanup_response"] = cleanup_response
    if not cleanup_response.get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce cleanup failed: {cleanup_response}")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_90485335(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> tuple[str, str, str, dict[str, Any]]:
    if set(trigger) != TRIGGER_ROW_KEYS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the trigger field_list "
            f"keys {sorted(TRIGGER_ROW_KEYS)}: {sorted(trigger)}"
        )
    if trigger.get("Customer_is_a_Partner__c") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger Customer_is_a_Partner__c must be null (a newly "
            "created Account is not linked yet)"
        )
    if trigger.get("Id") != TRIGGER_ID_TOKEN:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger Id must be the {TRIGGER_ID_TOKEN} token (the live "
            f"seeded trigger Account): {trigger.get('Id')!r}"
        )
    name = trigger.get("Name")
    if not isinstance(name, str) or not name.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} trigger Name must be a non-empty string")
    rt = trigger.get("RecordTypeId")
    if rt not in {CUSTOMER_RT_ID, PARTNER_RT_ID}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger RecordTypeId must be one of the recipe's two "
            f"source-org ids (replayed trigger data): {rt!r}"
        )
    if rt == CUSTOMER_RT_ID:
        # IF arm: a customer Account fires the trigger; search '<Name> - Partner'.
        if NAME_SUFFIX in name:
            raise RuntimeError(
                f"recipe {RECIPE_ID} customer-arm trigger Name must not contain "
                f"{NAME_SUFFIX!r} (that suffix marks partner accounts): {name!r}"
            )
        return "customer_if", f"{name}{NAME_SUFFIX}", PARTNER_RT_ID, CUSTOMER_STOP
    # ELSE arm: a partner Account fires the trigger; search the gsub-stripped name.
    if not name.endswith(NAME_SUFFIX):
        raise RuntimeError(
            f"recipe {RECIPE_ID} partner-arm trigger Name must end with {NAME_SUFFIX!r} "
            f"so the gsub strip is actually exercised: {name!r}"
        )
    return "partner_else", name.replace(NAME_SUFFIX, ""), CUSTOMER_RT_ID, PARTNER_STOP


def _require_salesforce_section(section: Any, trigger: dict[str, Any], searched_name: str) -> None:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce")
    unexpected = sorted(set(section) - {"schema", "records"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce has unexpected keys: {unexpected}")
    if section.get("schema") != REQUIRED_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare exactly "
            f"{json.dumps(REQUIRED_SCHEMA)}"
        )
    records = section.get("records")
    if not isinstance(records, list) or len(records) != 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.records must contain exactly the trigger "
            "Account and the name-matching decoy Account"
        )
    by_ref: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} seeded record must be an object: {record}")
        if record.get("sobject") != "Account":
            raise RuntimeError(f"recipe {RECIPE_ID} seeded records must be Accounts: {record}")
        if record.get("read_fields") != ["RecordTypeId"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded Account must declare read_fields "
                f"['RecordTypeId'] so the searches compare the REAL live record type "
                f"value against the hardcoded source-org id: {record}"
            )
        fields = record.get("fields")
        if not isinstance(fields, dict) or set(fields) != {"Name"}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seeded Account fields must be exactly {{'Name'}} "
                f"(RecordTypeId cannot be written -- INVALID_CROSS_REFERENCE_KEY -- and "
                f"Customer_is_a_Partner__c must start null): {record}"
            )
        by_ref[str(record.get("ref") or "")] = record
    if set(by_ref) != {"trigger_account", "decoy_account"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seeded record refs must be exactly "
            f"{{'trigger_account', 'decoy_account'}}: {sorted(by_ref)}"
        )
    if by_ref["trigger_account"]["fields"]["Name"] != trigger.get("Name"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the live trigger Account's Name must equal the trigger "
            f"payload Name: {by_ref['trigger_account']['fields']['Name']!r} != "
            f"{trigger.get('Name')!r}"
        )
    if by_ref["decoy_account"]["fields"]["Name"] != searched_name:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the decoy Account's Name must equal the search's exact "
            f"Name filter {searched_name!r} (zero-match honesty): "
            f"{by_ref['decoy_account']['fields']['Name']!r}"
        )


def _require_expect_shape(
    expect: Any,
    arm: str,
    searched_name: str,
    rt_filter_id: str,
    stop_pin: dict[str, Any],
    trigger: dict[str, Any],
) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(set(expect) - set(EXPECT_KEYS) - OPTIONAL_EXPECT_KEYS)
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has unexpected keys: {unknown}")
    if expect.get("arm") != arm:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.arm must be {arm!r}: {expect.get('arm')!r}")
    if expect.get("stopped") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} every reachable path ends at a clean STOP (the update "
            "arms are dead live); expect.stopped must be true"
        )
    if expect.get("stop_step_number") != stop_pin["number"] or expect.get("stop_step_as") != stop_pin["as"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the {arm} arm stops at step {stop_pin['number']} "
            f"({stop_pin['as']}): {expect.get('stop_step_number')!r}/{expect.get('stop_step_as')!r}"
        )
    if expect.get("searched_name") != searched_name:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.searched_name must be {searched_name!r}: "
            f"{expect.get('searched_name')!r}"
        )
    if expect.get("rt_filter_id") != rt_filter_id:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.rt_filter_id must be {rt_filter_id!r}: "
            f"{expect.get('rt_filter_id')!r}"
        )
    if expect.get("executed_action_count") != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} every reachable path executes exactly the one search "
            "action before stopping"
        )
    if expect.get("tools") != ["salesforce.search_records"]:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools must be ['salesforce.search_records']")
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or len(items) != 1 or not isinstance(items[0], dict):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must pin the single search")
    item = items[0]
    expected_args = {
        "sobject": "Account",
        "query": "",
        "limit": "150",
        "filters": [
            {"field": "Name", "value": searched_name},
            {"field": "RecordTypeId", "value": rt_filter_id},
        ],
    }
    if item.get("tool") != "salesforce.search_records" or item.get("args_contains") != expected_args:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0] must pin the resolved search args "
            f"exactly {json.dumps(expected_args)}: {json.dumps(item.get('args_contains'))}"
        )
    if item.get("result_count") != 0:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0].result_count must be 0 (the "
            "source-org RT filter can never match a live record)"
        )
    final_fields = expect.get("final_fields_by_name")
    expected_names = {trigger.get("Name"), searched_name}
    if (
        not isinstance(final_fields, dict)
        or set(final_fields) != expected_names
        or any(fields != {"Customer_is_a_Partner__c": None} for fields in final_fields.values())
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_fields_by_name must pin "
            "Customer_is_a_Partner__c null for BOTH live Accounts (the dead updates "
            f"never fire): {json.dumps(final_fields)}"
        )


def _salesforce_ref_tokens(seed_section: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    live_ids = [
        str(record.get("id") or "")
        for record in salesforce_snapshot.get("records") or []
        if isinstance(record, dict) and record.get("id")
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


def _require_resolved(value: dict[str, Any], label: str) -> None:
    leftover = _TOKEN_RE.findall(json.dumps(value))
    if leftover:
        raise RuntimeError(f"recipe {RECIPE_ID} {label} has unresolved seed tokens: {leftover}")


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return ctx.tools.call("harness.salesforce.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
