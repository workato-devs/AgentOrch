from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_122911418


RECIPE_ID = "122911418"
SEED_TYPE = "salesforce_quote_effective_date_kickoff_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "salesforce"
TRIGGER_NAME = "updated_custom_object"
TRIGGER_AS = "acd8d0f0"
TRIGGER_SOBJECT = "SBQQ__Quote__c"
LOOKUP_TABLE_ID = "4308327"
LOOKUP_TABLE_NAME = "[GTM] Quote Effective Date"
SEARCH_STEP_AS = "ac90f493"
UPDATE_SOBJECT_STEP_AS = "84251964"
UPDATE_ENTRY_STEP_AS = "a1dfb382"
ADD_ENTRY_STEP_AS = "f49793bf"
REQUIRED_SCHEMA = [
    {"sobject": "Account", "field": "Kickoff_Date__c", "sf_type": "Date"},
    {"sobject": "Account", "field": "Onboarding_Stage__c", "sf_type": "Text"},
]
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_SYNTHETIC_ACCOUNT_RE = re.compile(r"001[0-9A-Za-z]{12,15}")


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "salesforce", "name": "updated_custom_object", "as": "acd8d0f0", "skip": false, "input": {"field_list": "Id\nName\nSBQQ__Account__c\nSBCF_AccountName__c\nSBQQ__Opportunity2__r$Opportunity.Type\nSBQQ__Primary__c\nSBQQ__StartDate__c\nSBQQ__Account__r$Account.Kickoff_Date__c\nSBQQ__Account__r$Account.Onboarding_Stage__c", "since_offset": "-3600", "sobject_name": "SBQQ__Quote__c", "table_list": "Account\nOpportunity"}, "filter": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"acd8d0f0\",\"path\":[\"SBQQ__Opportunity2__r\", \"Type\"]}')}", "operand": "equals_to", "rhs": "New Logo"}, {"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"acd8d0f0\",\"path\":[\"SBQQ__StartDate__c\"]}')}", "operand": "greater_than", "rhs": "=14.days.ago"}, {"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"acd8d0f0\",\"path\":[\"SBQQ__Account__r\",\"Kickoff_Date__c\"]}').present? ? (_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"acd8d0f0\",\"path\":[\"SBQQ__Account__r\",\"Kickoff_Date__c\"]}')-14) : '1970-01-01'", "operand": "not_equals_to", "rhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"acd8d0f0\",\"path\":[\"SBQQ__StartDate__c\"]}')}"}, {"lhs": "=lookup('[GTM] Quote Effective Date', 'Quote Id': _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"acd8d0f0\",\"path\":[\"Id\"]}'))['Effective Date'].presence or '1970-01-01'", "operand": "not_equals_to", "rhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"acd8d0f0\",\"path\":[\"SBQQ__StartDate__c\"]}').to_s"}], "operand": "and", "type": "compound"}, "block": [{"number": 2, "keyword": "action", "provider": "lookup_table", "name": "search_entries", "as": "ac90f493", "skip": false, "input": {"lookup_table_id": "4308327", "parameters": {"col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"acd8d0f0\",\"path\":[\"Id\"]}')}"}}, "block": []}, {"number": 3, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"ac90f493\",\"path\":[\"entries\",{\"path_element_type\":\"current_item\"},\"entry\",\"col4\"]}').present? ? (_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"ac90f493\",\"path\":[\"entries\",{\"path_element_type\":\"current_item\"},\"entry\",\"col4\"]}').to_date+14) : _dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"acd8d0f0\",\"path\":[\"SBQQ__Account__r\",\"Kickoff_Date__c\"]}')", "operand": "equals_to", "rhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"acd8d0f0\",\"path\":[\"SBQQ__Account__r\", \"Kickoff_Date__c\"]}')}"}, {"lhs": "Completed | Canceled", "operand": "not_contains", "rhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"acd8d0f0\",\"path\":[\"SBQQ__Account__r\", \"Onboarding_Stage__c\"]}')}"}], "operand": "and", "type": "compound"}, "block": [{"number": 4, "keyword": "action", "provider": "salesforce", "name": "update_sobject", "as": "84251964", "skip": false, "input": {"Kickoff_Date__c": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"acd8d0f0\",\"path\":[\"SBQQ__StartDate__c\"]}')+14", "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"acd8d0f0\",\"path\":[\"SBQQ__Account__c\"]}')}", "sobject_name": "Account"}, "block": []}]}, {"number": 5, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "1", "operand": "equals_to", "rhs": "1"}], "operand": "and", "type": "compound"}, "block": [{"number": 6, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"ac90f493\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}", "operand": "present", "rhs": ""}], "operand": "and", "type": "compound"}, "block": [{"number": 7, "keyword": "action", "provider": "lookup_table", "name": "update_entry", "as": "a1dfb382", "skip": false, "input": {"id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"ac90f493\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}", "ignore_not_found": "false", "lookup_table_id": "4308327", "parameters": {"col10": "=today", "col2": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"acd8d0f0\",\"path\":[\"Name\"]}')}", "col3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"acd8d0f0\",\"path\":[\"SBCF_AccountName__c\"]}')}", "col4": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"acd8d0f0\",\"path\":[\"SBQQ__StartDate__c\"]}')}"}}, "block": []}, {"number": 8, "keyword": "else", "provider": "", "name": "", "as": "", "skip": false, "input": {}, "block": [{"number": 9, "keyword": "action", "provider": "lookup_table", "name": "add_entry", "as": "f49793bf", "skip": false, "input": {"lookup_table_id": "4308327", "parameters": {"col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"acd8d0f0\",\"path\":[\"Id\"]}')}", "col10": "=today", "col2": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"acd8d0f0\",\"path\":[\"Name\"]}')}", "col3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"acd8d0f0\",\"path\":[\"SBCF_AccountName__c\"]}')}", "col4": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"acd8d0f0\",\"path\":[\"SBQQ__StartDate__c\"]}')}"}}, "block": []}]}]}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (SEARCH_STEP_AS, "lookup_table", "search_entries"),
    (UPDATE_SOBJECT_STEP_AS, "salesforce", "update_sobject"),
    (UPDATE_ENTRY_STEP_AS, "lookup_table", "update_entry"),
    (ADD_ENTRY_STEP_AS, "lookup_table", "add_entry"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "salesforce.update_record",
    "lookup_table.update_entry",
    "lookup_table.add_entry",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "salesforce.update_record",
    "lookup_table.update_entry",
    "lookup_table.add_entry",
]
TRIGGER_KEYS = (
    "Id",
    "Name",
    "SBQQ__Account__c",
    "SBCF_AccountName__c",
    "SBQQ__StartDate__c",
    "SBQQ__Account__r",
    "SBQQ__Opportunity2__r",
)
ROW_COL_KEYS = ("col1", "col2", "col3", "col4", "col10")
ROW_LABEL_KEYS = ("Quote Id", "Effective Date")
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "trigger_filter_matched",
    "lookup_search_args",
    "account_update",
    "final_lookup_rows",
)
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def validate_122911418(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    if str((raw.get("input") or {}).get("sobject_name") or "") != TRIGGER_SOBJECT:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger sobject changed")
    if not isinstance(raw.get("filter"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger filter missing")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    # Semantic pins on the drift-prone formulas (the tree pin holds the exact
    # bytes; these guards name the trap when one changes).
    filter_conditions = (raw.get("filter") or {}).get("conditions") or []
    if len(filter_conditions) != 4:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger filter no longer has 4 conditions")
    if "lookup('[GTM] Quote Effective Date', 'Quote Id':" not in str(filter_conditions[3].get("lhs")):
        raise RuntimeError(f"recipe {RECIPE_ID} filter cond-4 lookup() formula changed")
    if str(filter_conditions[1].get("rhs")) != "=14.days.ago":
        raise RuntimeError(f"recipe {RECIPE_ID} filter cond-2 window changed")
    for node in _walk_nodes(raw):
        if node.get("provider") == "lookup_table":
            table = str((node.get("input") or {}).get("lookup_table_id") or "")
            if table != LOOKUP_TABLE_ID:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} lookup step {node.get('as')!r} targets table "
                    f"{table!r}, expected {LOOKUP_TABLE_ID!r}"
                )
        if str(node.get("as") or "") == UPDATE_SOBJECT_STEP_AS:
            value = str((node.get("input") or {}).get("Kickoff_Date__c") or "")
            if not value.endswith("+14") or "SBQQ__StartDate__c" not in value:
                raise RuntimeError(f"recipe {RECIPE_ID} Kickoff update formula changed: {value!r}")
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "trigger_sobject": TRIGGER_SOBJECT,
        "lookup_table_id": LOOKUP_TABLE_ID,
        "actions": [
            {
                "number": a.get("number"),
                "provider": a.get("provider"),
                "name": a.get("name"),
                "as": a.get("as"),
            }
            for a in actions
        ],
    }


def seed_122911418(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_122911418(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    if data.get("now") in (None, ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input requires a fixed 'now' "
            "(=14.days.ago filter window and =today lookup column)"
        )
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"lookup_table", "salesforce"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    _require_lookup_section(seed_in.get("lookup_table"))
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole "
            "run instead of exercising a recipe branch"
        )
    salesforce_section = seed_in.get("salesforce")
    wants_update = expect.get("account_update") is not None
    if wants_update and salesforce_section is None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.account_update requires seed.salesforce "
            "(the step-4 Account update runs LIVE)"
        )
    if not wants_update and salesforce_section is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seeds a live Account but expect.account_update is null; "
            "skip-update variants must not provision live records"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "now": data["now"],
        "lookup_table": deepcopy(seed_in["lookup_table"]),
    }
    if salesforce_section is not None:
        _require_salesforce_section(salesforce_section)
        provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": salesforce_section})
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
        refs = _salesforce_ref_tokens(salesforce_section, provision)
        trigger = _replace_value(trigger, refs)
        expect = _replace_value(deepcopy(expect), refs)
        out["salesforce_live"] = deepcopy(provision["state"])
        out["salesforce_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
        out["salesforce_ref_tokens"] = refs
    else:
        account_id = str(trigger.get("SBQQ__Account__c") or "")
        if not _SYNTHETIC_ACCOUNT_RE.fullmatch(account_id):
            raise RuntimeError(
                f"recipe {RECIPE_ID} skip-update variants need a well-formed synthetic "
                f"Account id in trigger.SBQQ__Account__c (never dereferenced): {account_id!r}"
            )
    _require_no_tokens(trigger, "trigger")
    _require_no_tokens(expect, "expect")
    out["trigger"] = trigger
    out["expect"] = deepcopy(expect)
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_122911418(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_122911418(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
    if seed.get("now") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing the fixed 'now'")
    live = isinstance(seed.get("salesforce_live"), dict)
    if seed["expect"].get("account_update") is not None and not live:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.account_update set but seed carries no live "
            "salesforce state"
        )
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect"),
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    cleanup_response: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = _snapshot(ctx, live)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx, live)
    finally:
        if live:
            # Required cleanup: the run mutates the live benchmark-owned Account.
            cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
            details["cleanup_response"] = cleanup_response
    if live and not (cleanup_response or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce cleanup failed: {cleanup_response}")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_122911418(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if tuple(sorted(trigger.keys())) != tuple(sorted(TRIGGER_KEYS)):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly {sorted(TRIGGER_KEYS)} "
            f"(the dereferenced field_list subset); got {sorted(trigger.keys())}"
        )
    for key in ("Id", "Name", "SBCF_AccountName__c"):
        if not isinstance(trigger.get(key), str) or not trigger[key].strip():
            raise RuntimeError(f"recipe {RECIPE_ID} trigger.{key} must be a non-empty string")
    if not isinstance(trigger.get("SBQQ__StartDate__c"), str) or not _DATE_RE.fullmatch(
        trigger["SBQQ__StartDate__c"]
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger.SBQQ__StartDate__c must be an ISO date "
            "(it feeds date arithmetic in the filter, IF-3 and the update value)"
        )
    account = trigger.get("SBQQ__Account__r")
    if (
        not isinstance(account, dict)
        or sorted(account.keys()) != ["Kickoff_Date__c", "Onboarding_Stage__c"]
        or not isinstance(account.get("Kickoff_Date__c"), str)
        or not isinstance(account.get("Onboarding_Stage__c"), str)
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger.SBQQ__Account__r must be exactly "
            "{'Kickoff_Date__c': <ISO date or ''>, 'Onboarding_Stage__c': <str, may be ''>}"
        )
    if account["Kickoff_Date__c"] and not _DATE_RE.fullmatch(account["Kickoff_Date__c"]):
        raise RuntimeError(f"recipe {RECIPE_ID} Kickoff_Date__c must be ISO or blank")
    opportunity = trigger.get("SBQQ__Opportunity2__r")
    if (
        not isinstance(opportunity, dict)
        or sorted(opportunity.keys()) != ["Type"]
        or not isinstance(opportunity.get("Type"), str)
        or not opportunity["Type"].strip()
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger.SBQQ__Opportunity2__r must be exactly "
            "{'Type': <non-empty str>} (filter condition 1)"
        )


def _require_lookup_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["names", "tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table must be exactly "
            "{'names': ..., 'tables': ...} (the filter lookup() resolves the table by NAME)"
        )
    if section["names"] != {LOOKUP_TABLE_NAME: LOOKUP_TABLE_ID}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.names must map "
            f"{LOOKUP_TABLE_NAME!r} -> {LOOKUP_TABLE_ID!r}"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [LOOKUP_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must declare exactly table "
            f"{LOOKUP_TABLE_ID!r} (rows may be an explicit empty list)"
        )
    rows = tables[LOOKUP_TABLE_ID]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {LOOKUP_TABLE_ID} rows must be a list")
    allowed = set(ROW_COL_KEYS) | set(ROW_LABEL_KEYS)
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table row {idx} must be an object")
        unknown = sorted(set(row.keys()) - allowed)
        if unknown:
            raise RuntimeError(f"recipe {RECIPE_ID} table row {idx} has unknown columns: {unknown}")
        for key in allowed:
            if key not in row or not isinstance(row[key], str) or not row[key].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table row {idx} requires non-empty string {key!r} "
                    "(dual-key contract: colN for the tool steps, labels for the filter lookup())"
                )
        # Dual-key coherence: the formula lookup() and the colN tool reads
        # must see the SAME quote id / effective date at seed time.
        if row["col1"] != row["Quote Id"] or row["col4"] != row["Effective Date"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} dual keys diverge: "
                f"col1={row['col1']!r} vs Quote Id={row['Quote Id']!r}, "
                f"col4={row['col4']!r} vs Effective Date={row['Effective Date']!r}"
            )
        for key in ("col4", "col10"):
            if not _DATE_RE.fullmatch(row[key]):
                raise RuntimeError(f"recipe {RECIPE_ID} table row {idx}.{key} must be an ISO date")


def _require_salesforce_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["records", "schema"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce must be exactly {{'schema': ..., 'records': ...}}"
        )
    if section["schema"] != REQUIRED_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare exactly the two Account "
            f"custom fields: {json.dumps(REQUIRED_SCHEMA)}"
        )
    records = section["records"]
    if not isinstance(records, list) or len(records) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.records must contain exactly the one "
            "Account the trigger references"
        )
    record = records[0]
    if (
        not isinstance(record, dict)
        or record.get("sobject") != "Account"
        or str(record.get("ref") or "").strip().upper() != "ACCT"
        or not isinstance(record.get("fields"), dict)
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the seeded record must be an Account with ref 'acct': {record}"
        )
    fields = record["fields"]
    required_fields = {"Name", "Kickoff_Date__c", "Onboarding_Stage__c"}
    if set(fields.keys()) != required_fields:
        raise RuntimeError(
            f"recipe {RECIPE_ID} Account fields must be exactly {sorted(required_fields)}; "
            f"got {sorted(fields.keys())}"
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


def _require_no_tokens(value: Any, label: str) -> None:
    leftover = sorted(set(_TOKEN_RE.findall(json.dumps(value))))
    if leftover:
        raise RuntimeError(f"recipe {RECIPE_ID} {label} has unresolved seed tokens: {leftover}")


def _normalize_tree(node: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "number": node.get("number"),
        "keyword": node.get("keyword"),
        "provider": node.get("provider") or "",
        "name": node.get("name") or "",
        "as": node.get("as") or "",
        "skip": bool(node.get("skip")),
    }
    if not out["skip"]:
        out["input"] = node.get("input")
    if node.get("keyword") == "foreach":
        out["repeat_mode"] = node.get("repeat_mode")
        out["source"] = node.get("source")
    if isinstance(node.get("filter"), dict):
        out["filter"] = node["filter"]
    out["block"] = [
        _normalize_tree(child) for child in node.get("block") or [] if isinstance(child, dict)
    ]
    return out


def _first_tree_mismatch(actual: Any, expected: Any, path: str = "root") -> str:
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            if key not in actual:
                return f"{path}.{key}: missing in raw recipe"
            if key not in expected:
                return f"{path}.{key}: unexpected in raw recipe"
            found = _first_tree_mismatch(actual[key], expected[key], f"{path}.{key}")
            if found:
                return found
        return ""
    if isinstance(expected, list) and isinstance(actual, list):
        if len(actual) != len(expected):
            return f"{path}: length {len(actual)} != {len(expected)}"
        for idx, (act, exp) in enumerate(zip(actual, expected)):
            found = _first_tree_mismatch(act, exp, f"{path}[{idx}]")
            if found:
                return found
        return ""
    if actual != expected:
        return f"{path}: {json.dumps(actual, default=str)[:200]} != {json.dumps(expected, default=str)[:200]}"
    return ""


def _walk_nodes(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        found.append(child)
        found.extend(_walk_nodes(child))
    return found


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _snapshot(ctx: RecipeContext, live: bool) -> dict[str, Any]:
    out: dict[str, Any] = {}
    out.update(ctx.tools.call("harness.lookup_table.snapshot", {}))
    if live:
        out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
