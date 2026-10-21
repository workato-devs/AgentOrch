from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_103988401


RECIPE_ID = "103988401"
SEED_TYPE = "salesforce_recipe_function_ytd_average_nps_variant"
TRACK = "live_salesforce_recipe_function_ytd_average_nps"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "aa5f65a9"
SEARCH_AS = "e88d464c"
SR_SOBJECT = "Survey_Response__c"
NPS_STATUS = "Survey Completed"
TRIGGER_ROW_KEYS = {"AccountID", "AccountName"}
# Schema-in-seed contract: Survey_Response__c was mdapi-deployed 2026-07-06/07
# (94001408 precedent) with Account__c / Score__c Text(255) and
# Survey_Response_Date__c Date; mdapi fields are describe-INVISIBLE until FLS
# is granted, so the seed re-ensures FLS every run. Status__c is NOT part of
# the deploy: ensure_custom_field Tooling-creates it as Text on first seed
# (the established custom-FIELD path -- only custom OBJECTS are banned from
# self-serve creation). Score__c is TEXT in the org, so seeds carry numeric
# STRINGS; the harness AVG parses them as Decimals.
REQUIRED_SCHEMA = [
    {"sobject": SR_SOBJECT, "field": "Account__c", "sf_type": "Text"},
    {"sobject": SR_SOBJECT, "field": "Score__c", "sf_type": "Text"},
    {"sobject": SR_SOBJECT, "field": "Status__c", "sf_type": "Text"},
    {"sobject": SR_SOBJECT, "field": "Survey_Response_Date__c", "sf_type": "Date"},
]
SR_FIELD_KEYS_WITH_DATE = {"Name", "Account__c", "Status__c", "Score__c", "Survey_Response_Date__c"}
SR_FIELD_KEYS_NO_DATE = {"Name", "Account__c", "Status__c", "Score__c"}
# Survey_Response_Date__c seeds are RELATIVE-date tokens resolved at seed time
# against UTC wall-clock — the ONLY sanctioned wall-clock exception to the
# fixed-timestamp rule (benmark_rules 'Simulated input variant rule'), applied
# deliberately here:
# - The SOQL arm 'Survey_Response_Date__c = LAST_N_DAYS:365' is a RELATIVE
#   date literal that live Salesforce — and the in-tree strict evaluator
#   (salesforce_live_harness LAST_N_DAYS branch, datetime.now(timezone.utc))
#   — evaluates against REAL now AT RUN TIME. That coupling cannot be pinned.
# - A pinned anchor would make the variants deterministic but NOT
#   live-rerunnable indefinitely: an inside row seeded at anchor-N days
#   (N <= 300) rots out of the live 365-day window once real time passes
#   anchor + (365 - N) days; the tightest allowed offset dies at anchor+65d.
# - Deriving seed dates from run-time now keeps every OBSERVABLE
#   deterministic instead: no expect pin may encode an absolute date
#   (enforced in _require_expect_shape), inside rows sit well inside the
#   window (<= 300 days), excluded rows well outside (>= 370), and the run
#   fail-fasts when the seed->run gap leaves the [0, 65]-day range where
#   that in/out classification is guaranteed (guard in run_103988401).
_DATE_TOKEN_RE = re.compile(r"^\$TODAY_MINUS_(\d+)D$")
_ABS_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
INSIDE_MAX_DAYS = 300
OUTSIDE_MIN_DAYS = 370
# Widest seed->run gap for which every inside token (<= 300d) is still inside
# LAST_N_DAYS:365 at run time; outside tokens (>= 370d) can never re-enter.
MAX_SEED_RUN_GAP_DAYS = 365 - INSIDE_MAX_DAYS
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_SCORE_RE = re.compile(r"-?\d+(?:\.\d+)?")

# workato_recipe_function.execute (as aa5f65a9; parameters.AccountList[]
# {AccountID, AccountName}; [] is the in-contract empty input). Linear body,
# no if/foreach/try -- FAMILY sibling (not byte twin: own as ids/uuids) of
# registered 118290293/103988481 and 103939956/98802887 (same AccountList ->
# ids-string -> SOQL aggregate -> return template skeleton). Was NEEDS-ENGINE
# at triage; AVG aggregate LANDED at HEAD 07af31c2 (type-aware, NULL on
# all-null groups) and re-probed verbatim 2026-07-08 (15/15).
#   2  workato_variable.declare_variable 2f1abaa7: account_ids_string =
#      AccountList&.pluck("AccountID").join("','").
#   3  salesforce.search_sobjects_soql_v2 e88d464c (LIVE, limit 2000):
#      SELECT Account__c, AVG(Score__c) avg_nps FROM Survey_Response__c
#      WHERE IsDeleted = FALSE AND Name LIKE '%NPS%' AND Status__c =
#      'Survey Completed' AND Survey_Response_Date__c != null AND
#      Survey_Response_Date__c = LAST_N_DAYS:365 AND Account__c IN ('<ids>')
#      GROUP BY Account__c -- all six arms strict-evaluated over live
#      read-back owned rows; AVG is typed per group: plain int when the
#      Decimal average is exactly integral (8,6,7 -> 7), float otherwise
#      (8,7 -> 7.5), SF NULL when every contributing Score__c is null
#      (probe P15 -- no variant pins that shape: a None avg would hit the
#      OPEN falsy-render family at the return template, documented below).
#      Every seed declares read_fields ['IsDeleted'] so the strict boolean
#      leaf evaluates the LIVE read-back false (103939956/118905064
#      precedent -- WITHOUT it the row is silently rejected, probe P16).
#   4  workato_recipe_function.return_result ab1b884e (TERMINAL):
#      result.YTDAverageNPSList ____source-mapped over the aggregate records
#      {AccountID<-Account__c, YTDAverageNPS<-avg_nps}.
#
# FALSY-RENDER NOTE (documented OPEN family): an all-null-score group would
# put avg_nps None through the single-pill '#{...}' return template; the
# render of nil there is the standing OPEN falsy-render gap, so the build
# deliberately keeps every qualifying group's scores non-null and the seeder
# requires Score__c on every seeded row.
#
# Branch mapping (linear recipe: coverage = 6 WHERE arms x group shapes x
# AVG result typing; probe-verified end-to-end offline 2026-07-08):
# - variant_00 multi_response_integral_avg: one account, 3 completed NPS
#   responses (8, 6, 7) inside the window -> one group, avg_nps int 7.
# - variant_01 arm_exclusions_fractional_avg: qualifying 8 + 7 -> 7.5
#   (float) while four decoys are excluded one arm at a time: Name without
#   'NPS', Status__c 'Survey Sent', Survey_Response_Date__c ~400d old
#   (LAST_N_DAYS arm), and a response on an account outside AccountList.
# - variant_02 two_accounts_grouped: two accounts with different averages
#   (9,8 -> 8.5 float; 6,6 -> 6 int) -> two grouped rows, mixed types.
# - variant_03 zero_match: only non-qualifying rows (status decoy + a
#   NULL-date decoy proving the 'Survey_Response_Date__c != null' arm) ->
#   records [] -> YTDAverageNPSList [].
# - variant_04 empty_account_list: AccountList [] -> ids string '' (probe
#   P4) -> Account__c IN ('') matches nothing; a fully-qualifying seeded
#   response proves the exclusion is the IN filter.
#
# GROUP BY output order = owned-record iteration order in the harness
# (insertion-ordered dict, 103939956 precedent): seed qualifying responses
# grouped by account in the order the expected rows are pinned. Backends:
# salesforce LIVE (benchmark-owned Account + Survey_Response__c records;
# schema-in-seed FLS re-ensure; cleanup deletes owned seeds in a finally
# block -- read-only recipe, but owned records must not leak);
# workato_variable / workato_recipe_function are Workato-internal in-process.

_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "aa5f65a9",
  "provider": "workato_recipe_function",
  "name": "execute",
  "skip": false,
  "input": {
   "parameters_schema_json": "[{\"name\":\"AccountList\",\"type\":\"array\",\"optional\":false,\"properties\":[{\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account ID\"},{\"name\":\"AccountName\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account name\"}],\"of\":\"object\",\"label\":\"Account list\"}]",
   "result_schema_json": "[{\"name\":\"YTDAverageNPSList\",\"type\":\"array\",\"optional\":false,\"label\":\"YTD average\",\"properties\":[{\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account ID\"},{\"name\":\"YTDAverageNPS\",\"type\":\"number\",\"optional\":true,\"control_type\":\"number\",\"label\":\"YTD average NPS\",\"parse_output\":\"float_conversion\"}],\"of\":\"object\"}]"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "2f1abaa7",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "account_ids_string": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"aa5f65a9\",\"path\":[\"parameters\",\"AccountList\"]}')&.pluck(\"AccountID\").join(\"','\")"
    },
    "schema": "[{\"control_type\":\"text\",\"label\":\"account_ids_string\",\"name\":\"account_ids_string\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"account_ids_string\"}}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "e88d464c",
  "provider": "salesforce",
  "name": "search_sobjects_soql_v2",
  "skip": false,
  "input": {
   "limit": "2000",
   "output_schema": "[{\"control_type\":\"text\",\"label\":\"Account ID\",\"name\":\"Account__c\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"number\",\"label\":\"avg_nps\",\"parse_output\":\"float_conversion\",\"name\":\"avg_nps\",\"type\":\"number\",\"optional\":false}]",
   "query": "SELECT Account__c,\n       AVG(Score__c) avg_nps\n  FROM Survey_Response__c\n WHERE IsDeleted = FALSE\n   AND Name LIKE '%NPS%'\n   AND Status__c = 'Survey Completed'\n   AND Survey_Response_Date__c != null\n   AND Survey_Response_Date__c = LAST_N_DAYS:365\n   AND Account__c IN ('#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2f1abaa7\",\"path\":[\"account_ids_string\"]}')}')\n GROUP BY Account__c   "
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "ab1b884e",
  "provider": "workato_recipe_function",
  "name": "return_result",
  "skip": false,
  "input": {
   "result": {
    "YTDAverageNPSList": {
     "AccountID": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"e88d464c\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Account__c\"]}')}",
     "YTDAverageNPS": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"e88d464c\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"avg_nps\"]}')}",
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"e88d464c\",\"path\":[\"records\"]}')}"
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


def validate_103988401(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_103988401(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_103988401(raw)
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
    _require_expect_shape(expect)
    salesforce_section, date_resolution = _resolve_date_tokens(deepcopy(seed_in["salesforce"]))
    provision = ctx.tools.call(
        "harness.salesforce.seed_records", {"salesforce": salesforce_section}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    refs = _salesforce_ref_tokens(salesforce_section, provision)
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
        # Expected SOQL text / result AccountIDs are this run's live seeded
        # Account ids, threaded via the same $REF_ID tokens as the trigger
        # (103939956 precedent).
        "expect": resolved_expect,
        # Sanctioned wall-clock exception audit trail: when the relative date
        # tokens were resolved and to what — the run bounds the seed->run gap
        # against this so the LAST_N_DAYS classification can never drift.
        "date_resolution": date_resolution,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": refs,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_103988401(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_103988401(raw)
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    if not seed["salesforce_live"].get("strict_soql_conditions"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires strict_soql_conditions in the live state "
            "(IsDeleted = FALSE / LIKE / != null / LAST_N_DAYS / IN are strict-only)"
        )
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    date_resolution = seed.get("date_resolution")
    if not isinstance(date_resolution, dict) or not str(
        date_resolution.get("resolved_on_utc_date") or ""
    ).strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed file missing date_resolution — re-seed "
            "(relative date tokens resolve at seed time; the run must bound the "
            "seed->run gap against the recorded resolution day)"
        )
    resolved_on = date.fromisoformat(str(date_resolution["resolved_on_utc_date"]))
    gap_days = (datetime.now(timezone.utc).date() - resolved_on).days
    if not 0 <= gap_days <= MAX_SEED_RUN_GAP_DAYS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} stale seed: {gap_days} day(s) since date-token "
            f"resolution ({resolved_on.isoformat()}) is outside the "
            f"[0, {MAX_SEED_RUN_GAP_DAYS}]-day range where every seeded date's "
            f"LAST_N_DAYS:365 in/out classification is guaranteed — re-seed"
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
    cleanup_response: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = _snapshot(ctx)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx)
    finally:
        # Required cleanup: owned Account + Survey_Response__c seed records
        # must not leak into later runs (the recipe itself only reads).
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
    result["verifier"] = verify_103988401(result)
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
    if sorted(section) != ["records", "schema", "strict_soql_conditions"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce must be exactly "
            "{'strict_soql_conditions': true, 'schema': [...], 'records': [...]}"
        )
    if section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true "
            "(IsDeleted = FALSE / LIKE / != null / LAST_N_DAYS / IN are strict-only)"
        )
    if section.get("schema") != REQUIRED_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare exactly "
            f"{json.dumps(REQUIRED_SCHEMA)} (mdapi fields are describe-invisible until "
            "FLS -- re-ensure every run; Status__c Tooling-creates on first seed)"
        )
    records = section.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records must be a non-empty list")
    account_refs_seen: set[str] = set()
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
        if sobject != SR_SOBJECT:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seeded records must be Account or {SR_SOBJECT}: {record}"
            )
        keys = set(fields)
        if keys not in (SR_FIELD_KEYS_WITH_DATE, SR_FIELD_KEYS_NO_DATE):
            raise RuntimeError(
                f"recipe {RECIPE_ID} {SR_SOBJECT} seeds carry exactly "
                f"{sorted(SR_FIELD_KEYS_WITH_DATE)} (Survey_Response_Date__c may be "
                f"OMITTED to exercise the '!= null' arm): {record}"
            )
        if record.get("read_fields") != ["IsDeleted"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} every {SR_SOBJECT} seed must declare read_fields "
                "['IsDeleted'] (the strict 'IsDeleted = FALSE' leaf evaluates the live "
                "read-back; without it the row is SILENTLY rejected -- probe P16): "
                f"{record}"
            )
        if not str(fields.get("Name") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} {SR_SOBJECT} seeds need a non-empty Name: {record}")
        if not str(fields.get("Status__c") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} {SR_SOBJECT} seeds need Status__c: {record}")
        account_token = str(fields.get("Account__c") or "")
        account_ref = (
            account_token[1:-3].lower()
            if account_token.startswith("$") and account_token.endswith("_ID")
            else ""
        )
        if not account_ref or account_ref not in account_refs_seen:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {SR_SOBJECT} Account__c must be the $<REF>_ID token "
                f"of an Account seeded EARLIER in the records list: {record}"
            )
        score = str(fields.get("Score__c") or "")
        if not _SCORE_RE.fullmatch(score):
            raise RuntimeError(
                f"recipe {RECIPE_ID} Score__c must be a numeric STRING (the org field is "
                f"Text; AVG parses it as a Decimal; all-null groups are deliberately "
                f"unrepresented -- falsy-render family): {record}"
            )
        if "Survey_Response_Date__c" in fields:
            token = str(fields.get("Survey_Response_Date__c") or "")
            match = _DATE_TOKEN_RE.fullmatch(token)
            if not match:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} Survey_Response_Date__c must be a "
                    f"$TODAY_MINUS_<N>D token (LAST_N_DAYS:365 evaluates run wall-clock; "
                    f"static dates rot out of the window): {record}"
                )
            days = int(match.group(1))
            if not (days <= INSIDE_MAX_DAYS or days >= OUTSIDE_MIN_DAYS):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} date tokens must sit clearly inside "
                    f"(<= {INSIDE_MAX_DAYS}d) or outside (>= {OUTSIDE_MIN_DAYS}d) the "
                    f"365-day window (rerun determinism): {record}"
                )


def _require_expect_shape(expect: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    absolute_dates = _ABS_DATE_RE.findall(json.dumps(expect))
    if absolute_dates:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect pins must never encode absolute dates "
            f"(precondition of the sanctioned wall-clock exception: seed dates "
            f"resolve at seed time, so a dated pin would rot): "
            f"{sorted(set(absolute_dates))}"
        )
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
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tool_expectations, list) or len(tool_expectations) != len(ALLOWED_TOOLS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry"
        )
    search_item = tool_expectations[0]
    if not isinstance(search_item, dict) or search_item.get("tool") != "salesforce.search_records":
        raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[0] must pin the SOQL search")
    args = search_item.get("args_contains")
    if (
        not isinstance(args, dict)
        or args.get("sobject") != SR_SOBJECT
        or args.get("limit") != "2000"
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0].args_contains must pin sobject "
            f"'{SR_SOBJECT}' and limit '2000': {args!r}"
        )
    query = str(args.get("query") or "")
    if (
        "AVG(Score__c) avg_nps" not in query
        or "Survey_Response_Date__c = LAST_N_DAYS:365" not in query
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0] must pin the resolved SOQL verbatim "
            f"(AVG alias + LAST_N_DAYS arm): {query!r}"
        )
    if not isinstance(search_item.get("result_count"), int):
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0].result_count must pin the grouped "
            "row count (0 on the empty branches)"
        )
    final_result = expect.get("final_result")
    if not isinstance(final_result, dict) or set(final_result) != {"YTDAverageNPSList"} or not isinstance(
        final_result.get("YTDAverageNPSList"), list
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_result must pin exactly "
            "{'YTDAverageNPSList': [...]} ([] on the empty branches)"
        )
    for row in final_result["YTDAverageNPSList"]:
        if not isinstance(row, dict) or set(row) != {"AccountID", "YTDAverageNPS"}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} YTDAverageNPSList rows carry exactly "
                f"AccountID + YTDAverageNPS: {row!r}"
            )
        avg = row.get("YTDAverageNPS")
        if isinstance(avg, bool) or not isinstance(avg, (int, float)):
            raise RuntimeError(
                f"recipe {RECIPE_ID} YTDAverageNPS must be numeric (typed AVG): {row!r}"
            )
        if isinstance(avg, float) and avg.is_integer():
            raise RuntimeError(
                f"recipe {RECIPE_ID} integral averages are plain INTS (AVG typing: "
                f"int-if-integral else float) -- pin {int(avg)} not {avg}: {row!r}"
            )
    if search_item["result_count"] != len(final_result["YTDAverageNPSList"]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the ____source mapping is 1:1 -- result_count must equal "
            "the pinned YTDAverageNPSList row count"
        )


def _resolve_date_tokens(section: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Replace $TODAY_MINUS_<N>D tokens with concrete UTC dates at SEED time.

    Run-time wall-clock here is the sanctioned exception to the
    fixed-timestamp rule (see the module comment above _DATE_TOKEN_RE):
    LAST_N_DAYS:365 evaluates against real now at run time in live Salesforce
    and in the strict harness evaluator, so the seeded dates must stay coupled
    to it. Every observable (expect pins, SOQL text, verifier checks) is
    date-free, so the outcome stays deterministic. The resolution day and the
    resolved token map are returned for the seed record so the run can bound
    the seed->run gap."""
    today = datetime.now(timezone.utc).date()
    tokens: dict[str, str] = {}

    def walk(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: walk(item) for key, item in value.items()}
        if isinstance(value, list):
            return [walk(item) for item in value]
        if isinstance(value, str):
            match = _DATE_TOKEN_RE.fullmatch(value)
            if match:
                resolved = (today - timedelta(days=int(match.group(1)))).isoformat()
                tokens[value] = resolved
                return resolved
        return value

    resolved_section = walk(section)
    return resolved_section, {
        "resolved_on_utc_date": today.isoformat(),
        "date_tokens": tokens,
    }


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
