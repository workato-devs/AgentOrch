from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_125214871


RECIPE_ID = "125214871"
SEED_TYPE = "salesforce_recipe_function_last_gears_meeting_variant"
TRACK = "live_salesforce_recipe_function_last_gears_meeting"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "35a0e063"
SEARCH_AS = "2fc09276"
# Source-org Event record type id hardcoded in the raw SOQL as a WHERE
# equality. Record type ids are ORG-GENERATED: they cannot be chosen,
# re-created, or imported into the benchmark org, and benchmark-org Event
# rows read back with the org's OWN RecordTypeId (or none) -- so the strict
# equality NEVER matches a live record (90485335/110005007 dead-query
# precedent; rewriting the literal to a visible org RT is BANNED as a
# matcher hack).
FOREIGN_RT_ID = "012o0000000tRwxAAE"
GEARS_TYPE = "GEARS"
TRIGGER_ROW_KEYS = {"AccountID", "AccountName", "SuccessOwner_UserID"}
EVENT_SEED_FIELD_KEYS = {"Subject", "Type", "StartDateTime", "EndDateTime", "WhatId"}
# The decoy Event's live read-back must expose every WHERE-arm field: the
# derived AccountId (from WhatId), the org-assigned OwnerId (the API user),
# the real RecordTypeId (org value or none -- never the foreign literal),
# IsDeleted, and the derived EndDate (from EndDateTime).
EVENT_READ_FIELDS = ["IsDeleted", "RecordTypeId", "AccountId", "OwnerId", "EndDate"]
EMPTY_REASONS = {"foreign_record_type", "empty_in_list"}
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")

# workato_recipe_function.execute (as 35a0e063; parameters.AccountList[]
# {AccountID, AccountName, SuccessOwner_UserID}). Linear body, no
# if/foreach/try -- 35a0e063-family sibling (all as ids shared with
# registered 118290293 and 103988481; own CSV identity). Closest twin:
# 103988481 (same Event + MAX(EndDate) + foreign-RT shape; deltas = Type IN
# ('GEARS') vs the 13-type list, aggregate alias last_gears_meeting, result
# key LastGEARSMeetings).
#   2  workato_variable.declare_variable 64a4fa81: account_ids_string =
#      AccountList&.pluck("AccountID").join("','"); owner_ids_string =
#      AccountList&.pluck('SuccessOwner_UserID').uniq.join("','") -- BOTH
#      feed the SOQL (probe: uniq collapses a shared owner to one id).
#   3  salesforce.search_sobjects_soql_v2 2fc09276 (LIVE, limit 2000):
#      SELECT AccountId, MAX(EndDate) last_gears_meeting FROM Event WHERE
#      IsDeleted = FALSE AND RecordTypeId = '012o0000000tRwxAAE' AND Type IN
#      ('GEARS') AND OwnerId IN ('<owners>') AND AccountId IN ('<ids>')
#      GROUP BY AccountId.
#   4  workato_recipe_function.return_result 0d2e8b10 (TERMINAL):
#      result.LastGEARSMeetings ____source-mapped over the records.
#
# DEAD QUERY (org-capability, faithful build -- 90485335/110005007
# precedent): the RecordTypeId equality against the source-org literal can
# never match in this org, so the search returns [] and LastGEARSMeetings is
# [] on EVERY input, forever. Probe-verified on HEAD 07af31c2 (2026-07-08):
# - P12: a decoy Event whose read-back matches EVERY other arm (IsDeleted
#   false, Type 'GEARS', OwnerId in the owner list, AccountId in the account
#   list) still returns 0 records.
# - P11b/P11c (shared family probes): the counterfactual foreign-RT read-back
#   matches with the MAX alias evaluated, and arm isolation shows only the RT
#   equality is False -- live-data impossibility, not an engine gap.
# Zero-match honesty: every variant live-seeds a DECOY Event satisfying every
# seedable arm (Type='GEARS', WhatId=a listed Account, OwnerId=the API user
# threaded via $USER_ID) so the 0-result is attributable to the RT filter
# (or, on the empty-list variant, to the IN ('') arms), never to an empty org.
#
# Branch mapping (single linear path; observable dimensions = the declare
# derivations flowing into the resolved SOQL text + the always-empty result;
# probe-verified end-to-end offline 2026-07-08):
# - variant_00 dead_rt_multi_account: 2 accounts, distinct-owner join arms
#   exercised with the decoy on account A (owner $USER_ID) -> 0 records ->
#   LastGEARSMeetings [].
# - variant_01 single_account: 1-element AccountList -> join produces the
#   bare id (no quote-comma pair, probe P5) -> [].
# - variant_02 duplicate_owner_uniq: two accounts SHARING $USER_ID ->
#   owner_ids_string uniq collapses to ONE id in the resolved SOQL -> [].
# - variant_03 empty_account_list: AccountList [] -> both strings '' ->
#   OwnerId IN ('') / AccountId IN ('') match nothing (empty_reason
#   empty_in_list; a decoy Event still proves rows existed).
# The >0-records branch is ORG-UNREACHABLE and therefore not represented
# (documented, not forced); registered byte-twin-head 118290293 covers this
# skeleton's live aggregate/group shapes.
#
# Backends: salesforce LIVE (benchmark-owned Account + Event records +
# read-only current-user row for $USER_ID threading; no custom fields --
# Event/EndDate/Type are standard; cleanup deletes owned seeds in a finally
# block); workato_variable / workato_recipe_function are Workato-internal
# in-process.

_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "35a0e063",
  "provider": "workato_recipe_function",
  "name": "execute",
  "skip": false,
  "input": {
   "parameters_schema_json": "[{\"name\":\"AccountList\",\"type\":\"array\",\"optional\":false,\"properties\":[{\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account ID\"},{\"name\":\"AccountName\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account name\"},{\"name\":\"SuccessOwner_UserID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Success owner user ID\"}],\"of\":\"object\",\"label\":\"Account list\"}]",
   "result_schema_json": "[{\"name\":\"LastGEARSMeetings\",\"type\":\"array\",\"optional\":false,\"label\":\"Last GEARS Meetings\",\"properties\":[{\"control_type\":\"text\",\"label\":\"Account ID\",\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"date\",\"label\":\"Last GEARS Meeting\",\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\",\"name\":\"LastGEARSMeeting\",\"type\":\"date_time\",\"optional\":false}],\"of\":\"object\"}]"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "64a4fa81",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "account_ids_string": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"35a0e063\",\"path\":[\"parameters\",\"AccountList\"]}')&.pluck(\"AccountID\").join(\"','\")",
     "owner_ids_string": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"35a0e063\",\"path\":[\"parameters\",\"AccountList\"]}')&.pluck('SuccessOwner_UserID').uniq.join(\"','\")"
    },
    "schema": "[{\"control_type\":\"text\",\"label\":\"account_ids_string\",\"name\":\"account_ids_string\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"account_ids_string\"}},{\"name\":\"owner_ids_string\",\"type\":\"string\",\"optional\":true,\"label\":\"owner_ids_string\",\"details\":{\"real_name\":\"owner_ids_string\"},\"control_type\":\"text\"}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "2fc09276",
  "provider": "salesforce",
  "name": "search_sobjects_soql_v2",
  "skip": false,
  "input": {
   "limit": "2000",
   "output_schema": "[{\"control_type\":\"text\",\"label\":\"Account ID\",\"name\":\"AccountId\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"date\",\"label\":\"last_gears_meeting\",\"name\":\"last_gears_meeting\",\"type\":\"date_time\",\"optional\":false,\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\"}]",
   "query": "SELECT AccountId,\n       MAX(EndDate) last_gears_meeting\n  FROM Event\n WHERE IsDeleted = FALSE\n   AND RecordTypeId = '012o0000000tRwxAAE'\n   AND Type IN ('GEARS')\n   AND OwnerId IN ('#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"64a4fa81\",\"path\":[\"owner_ids_string\"]}')}')\n   AND AccountId IN ('#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"64a4fa81\",\"path\":[\"account_ids_string\"]}')}')\n GROUP BY AccountId"
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "0d2e8b10",
  "provider": "workato_recipe_function",
  "name": "return_result",
  "skip": false,
  "input": {
   "result": {
    "LastGEARSMeetings": {
     "AccountID": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2fc09276\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"AccountId\"]}')}",
     "LastGEARSMeeting": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2fc09276\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"last_gears_meeting\"]}')}",
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2fc09276\",\"path\":[\"records\"]}')}"
    }
   }
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "salesforce.search_records",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_recipe_function.return_result",
]
EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "final_result",
    "empty_reason",
    "decoy_events",
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


def validate_125214871(raw: dict[str, Any]) -> dict[str, Any]:
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
    # The dead-query proof rests on this exact source-org RT equality; scream
    # if it ever drifts (redundant with the full pins, but load-bearing --
    # 90485335 precedent).
    by_as = {pin["as"]: pin for pin in actual if pin.get("as")}
    if f"RecordTypeId = '{FOREIGN_RT_ID}'" not in str(by_as[SEARCH_AS]["input"].get("query") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} foreign RecordTypeId WHERE equality changed")
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


def seed_125214871(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_125214871(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"salesforce"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    _require_salesforce_section(seed_in.get("salesforce"))
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole "
            "run instead of exercising a recipe branch"
        )
    expect = data.get("expect")
    _require_expect_shape(expect, trigger)
    provision = ctx.tools.call(
        "harness.salesforce.seed_records", {"salesforce": deepcopy(seed_in["salesforce"])}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    refs = _salesforce_ref_tokens(seed_in["salesforce"], provision)
    trigger = _replace_value(trigger, refs)
    _require_resolved(trigger)
    resolved_expect = _replace_value(deepcopy(expect), refs)
    _require_resolved(resolved_expect)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": resolved_expect,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": refs,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_125214871(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_125214871(raw)
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    if not seed["salesforce_live"].get("strict_soql_conditions"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires strict_soql_conditions in the live state "
            "(the RecordTypeId equality / IN arms are strict-only; without the flag "
            "the dead-query semantics would be silently wrong)"
        )
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
        # Required cleanup: owned Account + decoy Event seed records must not
        # leak into later runs (the recipe itself only reads).
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
    result["verifier"] = verify_125214871(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {"parameters"} or not isinstance(trigger.get("parameters"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'parameters': {{...}}}}"
        )
    parameters = trigger["parameters"]
    if set(parameters) != {"AccountList"} or not isinstance(parameters.get("AccountList"), list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must carry exactly AccountList "
            "(a list; [] is the empty-input branch)"
        )
    for row in parameters["AccountList"]:
        if not isinstance(row, dict) or set(row) != TRIGGER_ROW_KEYS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} every AccountList row must carry exactly "
                f"{sorted(TRIGGER_ROW_KEYS)} (the trigger parameters schema): {row!r}"
            )
        for key in TRIGGER_ROW_KEYS:
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} AccountList row {key} must be a non-empty string: {row!r}"
                )
        if not row["AccountID"].startswith("$"):
            raise RuntimeError(
                f"recipe {RECIPE_ID} AccountID must be a $<REF>_ID token for a seeded "
                f"Account (live ids are run-generated): {row!r}"
            )


def _require_salesforce_section(section: Any) -> None:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce")
    if sorted(section) != ["current_user", "records", "strict_soql_conditions"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce must be exactly "
            "{'strict_soql_conditions': true, 'current_user': {}, 'records': [...]}"
        )
    if section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true"
        )
    if section.get("current_user") != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.current_user must be {{}} (registers the "
            "read-only live API user row and the $USER_ID token for owner threading)"
        )
    records = section.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records must be a non-empty list")
    account_refs_seen: set[str] = set()
    decoy_count = 0
    for record in records:
        if not isinstance(record, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} seeded record must be an object: {record}")
        ref = str(record.get("ref") or "").strip()
        if not ref:
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded Salesforce record needs a 'ref': {record}"
            )
        fields = record.get("fields")
        if not isinstance(fields, dict) or not fields:
            raise RuntimeError(f"recipe {RECIPE_ID} every seeded record needs explicit fields: {record}")
        sobject = str(record.get("sobject") or "")
        if sobject == "Account":
            if set(fields) != {"Name"} or not str(fields.get("Name") or "").strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} Account seeds carry exactly a non-empty Name: {record}"
                )
            account_refs_seen.add(ref.lower())
            continue
        if sobject != "Event":
            raise RuntimeError(
                f"recipe {RECIPE_ID} seeded records must be Account or Event: {record}"
            )
        decoy_count += 1
        if set(fields) != EVENT_SEED_FIELD_KEYS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} decoy Event seeds carry exactly "
                f"{sorted(EVENT_SEED_FIELD_KEYS)}: {record}"
            )
        if record.get("read_fields") != EVENT_READ_FIELDS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} every decoy Event must declare read_fields "
                f"{EVENT_READ_FIELDS} so the strict WHERE arms evaluate the REAL live "
                f"read-back (derived AccountId/EndDate, org OwnerId/RecordTypeId): {record}"
            )
        if fields.get("Type") != GEARS_TYPE:
            raise RuntimeError(
                f"recipe {RECIPE_ID} decoy Event Type must be 'GEARS' so the Type IN "
                f"('GEARS') arm passes on the decoy: {record}"
            )
        what_id = str(fields.get("WhatId") or "")
        what_ref = what_id[1:-3].lower() if what_id.startswith("$") and what_id.endswith("_ID") else ""
        if not what_ref or what_ref not in account_refs_seen:
            raise RuntimeError(
                f"recipe {RECIPE_ID} decoy Event WhatId must be the $<REF>_ID token of an "
                f"Account seeded EARLIER in the records list: {record}"
            )
        if not str(fields.get("Subject") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} decoy Event needs a non-empty Subject: {record}")
        for key in ("StartDateTime", "EndDateTime"):
            if not str(fields.get(key) or "").strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} decoy Event needs explicit {key} (EndDate derives "
                    f"from EndDateTime): {record}"
                )
    if decoy_count < 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} every variant must seed at least one decoy Event "
            "(zero-match honesty: the empty result must be attributable to the WHERE, "
            "never to an empty org)"
        )


def _require_expect_shape(expect: Any, trigger: dict[str, Any]) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(set(expect) - set(EXPECT_KEYS))
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has unexpected keys: {unknown}")
    if expect.get("executed_action_count") != 3:
        raise RuntimeError(f"recipe {RECIPE_ID} the linear body always executes all 3 actions")
    if expect.get("tools") != ALLOWED_TOOLS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools must be exactly {ALLOWED_TOOLS}: "
            f"{expect.get('tools')!r}"
        )
    if expect.get("empty_reason") not in EMPTY_REASONS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.empty_reason must be one of {sorted(EMPTY_REASONS)}"
        )
    account_list = (trigger.get("parameters") or {}).get("AccountList") or []
    if (expect["empty_reason"] == "empty_in_list") != (account_list == []):
        raise RuntimeError(
            f"recipe {RECIPE_ID} empty_reason 'empty_in_list' is exactly the "
            "AccountList [] branch (IN ('') matches nothing before the RT arm even "
            f"applies); non-empty lists pin 'foreign_record_type': {expect['empty_reason']!r}"
        )
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tool_expectations, list) or len(tool_expectations) != len(ALLOWED_TOOLS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry"
        )
    search_item = tool_expectations[0]
    if not isinstance(search_item, dict) or search_item.get("tool") != "salesforce.search_records":
        raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[0] must pin the SOQL search")
    args = search_item.get("args_contains")
    if not isinstance(args, dict) or args.get("sobject") != "Event" or args.get("limit") != "2000":
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0].args_contains must pin sobject "
            f"'Event' and limit '2000': {args!r}"
        )
    query = str(args.get("query") or "")
    if f"RecordTypeId = '{FOREIGN_RT_ID}'" not in query or "MAX(EndDate) last_gears_meeting" not in query:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0] must pin the resolved SOQL verbatim "
            f"(foreign RT equality + MAX alias): {query!r}"
        )
    if search_item.get("result_count") != 0:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0].result_count must be 0: the foreign "
            "RecordTypeId equality never matches a live record (dead query)"
        )
    if expect.get("final_result") != {"LastGEARSMeetings": []}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_result must be exactly "
            "{'LastGEARSMeetings': []} -- every reachable path returns the empty list"
        )
    decoys = expect.get("decoy_events")
    if not isinstance(decoys, list) or not decoys:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.decoy_events must pin every seeded decoy Event "
            "(dead-branch attestation for the verifier)"
        )
    trigger_rows = ((trigger.get("parameters") or {}).get("AccountList")) or []
    rows_by_account = {
        str(row.get("AccountID") or ""): row for row in trigger_rows if isinstance(row, dict)
    }
    for decoy in decoys:
        if (
            not isinstance(decoy, dict)
            or set(decoy) != {"AccountId", "OwnerId", "Type"}
            or decoy.get("Type") != GEARS_TYPE
            or not str(decoy.get("AccountId") or "").strip()
            or decoy.get("OwnerId") != "$USER_ID"
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} each decoy_events entry must be "
                "{'AccountId': '$<REF>_ID', 'OwnerId': '$USER_ID', 'Type': 'GEARS'}: "
                f"{decoy!r}"
            )
        if expect["empty_reason"] == "foreign_record_type":
            # Dead-branch honesty: the decoy must pass EVERY seedable arm, so
            # its account must be in AccountList and that row's owner must be
            # the API user ($USER_ID) whom Salesforce assigns as the Event's
            # OwnerId -- leaving the RT equality as the sole excluder.
            row = rows_by_account.get(str(decoy.get("AccountId") or ""))
            if not row or row.get("SuccessOwner_UserID") != "$USER_ID":
                raise RuntimeError(
                    f"recipe {RECIPE_ID} foreign_record_type variants must list the "
                    "decoy's account in AccountList with SuccessOwner_UserID "
                    f"'$USER_ID' (arm isolation): {decoy!r}"
                )


def _salesforce_ref_tokens(seed_section: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    owned_ids: list[str] = []
    user_id = ""
    for record in salesforce_snapshot.get("records") or []:
        if not isinstance(record, dict) or not record.get("id"):
            continue
        if record.get("read_only"):
            if str(record.get("sobject") or "") == "User":
                user_id = str(record.get("id") or "")
            continue
        owned_ids.append(str(record.get("id") or ""))
    seed_records = [record for record in seed_section.get("records") or [] if isinstance(record, dict)]
    if len(owned_ids) != len(seed_records):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed/snapshot record count mismatch: "
            f"{len(seed_records)} seeded vs {len(owned_ids)} provisioned"
        )
    if not user_id:
        raise RuntimeError(
            f"recipe {RECIPE_ID} current_user row missing from the seed snapshot "
            "($USER_ID threading requires it)"
        )
    refs: dict[str, str] = {"$USER_ID": user_id}
    for idx, record in enumerate(seed_records):
        ref = str(record.get("ref") or "").strip()
        if ref:
            refs[f"${ref.upper()}_ID"] = owned_ids[idx]
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


def _require_resolved(value: Any) -> None:
    leftover = _TOKEN_RE.findall(json.dumps(value))
    if leftover:
        raise RuntimeError(f"recipe {RECIPE_ID} unresolved seed tokens remain: {sorted(set(leftover))}")


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
