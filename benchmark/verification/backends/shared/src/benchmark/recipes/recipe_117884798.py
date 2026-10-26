from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_117884798


RECIPE_ID = "117884798"
SEED_TYPE = "renewal_opp_contact_role_sync_variant"
TRACK = "live_salesforce_renewal_ocr_sync"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "360e48d3"
ORIGINAL_SEARCH_AS = "6837086a"
PER_CONTACT_SEARCH_AS = "ae5aa3ed"
CREATE_AS = "52a4cce3"
UPDATE_AS = "3c411ced"
CATCH_AS = "29f2788f"
NURTURE_SCHEMA: list[dict[str, str]] = [
    {"sobject": "OpportunityContactRole", "field": "Nurture__c", "sf_type": "Checkbox"},
    {"sobject": "OpportunityContactRole", "field": "Nurture_End_Date__c", "sf_type": "Date"},
    {"sobject": "OpportunityContactRole", "field": "Nurture_Reminder_Cadence__c", "sf_type": "Text"},
    {"sobject": "OpportunityContactRole", "field": "Nurture_Status__c", "sf_type": "Text"},
    {"sobject": "OpportunityContactRole", "field": "Nurture_Last_Email_Sent_del__c", "sf_type": "Date"},
]
EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("e1f1c45c", "workato_variable", "declare_list"),
    ("acdf275f", "workato_variable", "declare_list"),
    ("6837086a", "salesforce", "search_sobjects"),
    ("ae5aa3ed", "salesforce", "search_sobjects"),
    ("52a4cce3", "salesforce", "create_custom_object"),
    ("3c411ced", "salesforce", "update_sobject"),
    ("2a4c8b74", "workato_variable", "insert_to_list"),
    ("87ffaec9", "workato_variable", "insert_to_list"),
    ("98e6d4e7", "workato_recipe_function", "return_result"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_list",
    "salesforce.search_records",
    "salesforce.create_record",
    "salesforce.update_record",
    "workato_runtime.insert_to_list",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "salesforce.create_record",
    "salesforce.update_record",
    "workato_recipe_function.return_result",
]
_EXPECT_ITEM_KEYS = {
    "tool", "table_id", "lookup_table_id", "match_fields", "channel",
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
}
_EXPECT_VALUE_KEYS = {
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
}
_SF_ID_RE = re.compile(r"[a-zA-Z0-9]{15,18}")
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*_ID")

_RAW_PIN_JSON = r"""{"as": "360e48d3", "block": [{"as": "e1f1c45c", "block": [], "input": {"list_item_schema_json": "[{\"name\":\"contact_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Contact ID\"},{\"control_type\":\"text\",\"label\":\"Contact Name\",\"name\":\"contact_name\",\"type\":\"string\",\"optional\":false},{\"name\":\"contact_email\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Contact Email\"},{\"control_type\":\"text\",\"label\":\"Opportunity Contact Role\",\"name\":\"opportunity_contact_role\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Error Message\",\"name\":\"error_message\",\"type\":\"string\",\"optional\":false}]", "name": "failed_list"}, "keyword": "action", "name": "declare_list", "number": 2, "provider": "workato_variable", "skip": false}, {"as": "acdf275f", "block": [], "input": {"list_item_schema_json": "[{\"name\":\"opportunity_contact_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Opportunity contact ID\"},{\"name\":\"contact_email\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Contact email\"}]", "name": "successful_list"}, "keyword": "action", "name": "declare_list", "number": 3, "provider": "workato_variable", "skip": false}, {"as": "6837086a", "block": [], "input": {"OpportunityId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"360e48d3\",\"path\":[\"parameters\", \"original_opp_id\"]}')}", "field_list": "ContactId\nRole\nIsPrimary\nCurrencyIsoCode\nNurture__c\nNurture_End_Date__c\nNurture_Reminder_Cadence__c\nNurture_Status__c\nNurture_Last_Email_Sent_del__c\nContact$Contact ID.Email\nContact$Contact ID.Name", "limit": "150", "sobject_name": "OpportunityContactRole", "table_list": "Contact"}, "keyword": "action", "name": "search_sobjects", "number": 4, "provider": "salesforce", "skip": false}, {"as": "f9528993", "block": [{"as": "ae5aa3ed", "block": [], "input": {"ContactId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"ContactId\"]}')}", "OpportunityId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"360e48d3\",\"path\":[\"parameters\", \"renewal_opp_id\"]}')}", "limit": "150", "sobject_name": "OpportunityContactRole"}, "keyword": "action", "name": "search_sobjects", "number": 6, "provider": "salesforce", "skip": false}, {"as": "", "block": [{"as": "", "block": [{"as": "52a4cce3", "block": [], "input": {"ContactId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"ContactId\"]}')}", "CurrencyIsoCode": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"CurrencyIsoCode\"]}')}", "IsPrimary": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"IsPrimary\"]}') or skip", "Nurture_End_Date__c": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"Nurture_End_Date__c\"]}') or skip", "Nurture_Last_Email_Sent_del__c": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"Nurture_Last_Email_Sent_del__c\"]}') or skip", "Nurture_Reminder_Cadence__c": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"Nurture_Reminder_Cadence__c\"]}') or skip", "Nurture_Status__c": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"Nurture_Status__c\"]}') or skip", "Nurture__c": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"Nurture__c\"]}') or skip", "OpportunityId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"360e48d3\",\"path\":[\"parameters\", \"renewal_opp_id\"]}')}", "Role": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"Role\"]}') or skip", "sobject_name": "OpportunityContactRole"}, "keyword": "action", "name": "create_custom_object", "number": 9, "provider": "salesforce", "skip": false}, {"as": "", "block": [{"as": "3c411ced", "block": [], "input": {"CurrencyIsoCode": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"CurrencyIsoCode\"]}')}", "IsPrimary": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"IsPrimary\"]}') or skip", "Nurture_End_Date__c": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"Nurture_End_Date__c\"]}') or skip", "Nurture_Last_Email_Sent_del__c": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"Nurture_Last_Email_Sent_del__c\"]}') or skip", "Nurture_Reminder_Cadence__c": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"Nurture_Reminder_Cadence__c\"]}') or skip", "Nurture_Status__c": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"Nurture_Status__c\"]}') or skip", "Nurture__c": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"Nurture__c\"]}') or skip", "Role": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"Role\"]}') or skip", "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"ae5aa3ed\",\"path\":[\"OpportunityContactRole\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}", "sobject_name": "OpportunityContactRole"}, "keyword": "action", "name": "update_sobject", "number": 11, "provider": "salesforce", "skip": false}], "input": {}, "keyword": "else", "name": "", "number": 10, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"ae5aa3ed\",\"path\":[\"OpportunityContactRole\", {\"path_element_type\": \"size\"}]}')}", "operand": "equals_to", "rhs": "0"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 8, "provider": "", "skip": false}, {"as": "2a4c8b74", "block": [], "input": {"list_item": {"contact_email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"Contact\", \"Email\"]}')}", "opportunity_contact_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"52a4cce3\",\"path\":[\"id\"]}')}"}, "location": "end", "name": "ecbe3b1f-2ccc-4507-9a2c-63d539a160fd:acdf275f"}, "keyword": "action", "name": "insert_to_list", "number": 12, "provider": "workato_variable", "skip": false}, {"as": "29f2788f", "block": [{"as": "87ffaec9", "block": [], "input": {"list_item": {"contact_email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"Contact\", \"Email\"]}')}", "contact_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"ContactId\"]}')}", "contact_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"Contact\", \"Name\"]}')}", "error_message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"29f2788f\",\"path\":[\"message\"]}')}", "opportunity_contact_role": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f9528993\",\"path\":[\"Role\"]}')}"}, "location": "end", "name": "f8664472-cd34-4426-aa8f-29f1b33256bb:e1f1c45c"}, "keyword": "action", "name": "insert_to_list", "number": 14, "provider": "workato_variable", "skip": false}], "input": {"max_retry_count": "3", "retry_interval": "5"}, "keyword": "catch", "name": "", "number": 13, "provider": "", "skip": false}], "input": {}, "keyword": "try", "name": "", "number": 7, "provider": "", "skip": false}], "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"6837086a\",\"path\":[\"OpportunityContactRole\"]}')}"}, "keyword": "foreach", "name": "", "number": 5, "provider": "", "repeat_mode": "simple", "skip": false, "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"6837086a\",\"path\":[\"OpportunityContactRole\"]}')}"}, {"as": "98e6d4e7", "block": [], "input": {"result": {"failed_list": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"e1f1c45c\",\"path\":[\"list_items\"]}')}", "contact_email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"e1f1c45c\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"contact_email\"]}')}", "contact_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"e1f1c45c\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"contact_id\"]}')}", "contact_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"e1f1c45c\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"contact_name\"]}')}", "error_message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"e1f1c45c\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"error_message\"]}')}", "opportunity_contact_role": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"e1f1c45c\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"opportunity_contact_role\"]}')}"}, "sucessful_list": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"acdf275f\",\"path\":[\"list_items\"]}')}", "contact_email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"acdf275f\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"contact_email\"]}')}", "opportunity_contact_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"acdf275f\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"opportunity_contact_id\"]}')}"}}}, "keyword": "action", "name": "return_result", "number": 15, "provider": "workato_recipe_function", "skip": false}], "input": {"parameters_schema_json": "[{\"name\":\"original_opp_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Original Opp ID\"},{\"name\":\"renewal_opp_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Renewal opp ID\"}]", "result_schema_json": "[{\"name\":\"failed_list\",\"type\":\"array\",\"optional\":false,\"properties\":[{\"name\":\"contact_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Contact ID\"},{\"name\":\"contact_name\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Contact Name\"},{\"name\":\"contact_email\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Contact Email\"},{\"name\":\"opportunity_contact_role\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Opportunity Contact Role\"},{\"name\":\"error_message\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Error message\"}],\"of\":\"object\",\"label\":\"Failed list\"},{\"name\":\"sucessful_list\",\"type\":\"array\",\"optional\":false,\"properties\":[{\"name\":\"opportunity_contact_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Opportunity contact ID\"},{\"name\":\"contact_email\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Contact email\"}],\"of\":\"object\",\"label\":\"Sucessful list\"}]"}, "keyword": "trigger", "name": "execute", "number": 1, "provider": "workato_recipe_function", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)


def validate_117884798(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": [
            {"number": a.get("number"), "provider": a.get("provider"),
             "name": a.get("name"), "as": a.get("as")}
            for a in actions
        ],
    }


def seed_117884798(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_117884798(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["salesforce"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the salesforce section; "
            f"got {sorted(seed_in.keys()) if isinstance(seed_in, dict) else seed_in}"
        )
    sf_section = seed_in["salesforce"]
    refs_declared = _require_salesforce_section(sf_section)
    _require_trigger_shape(trigger, refs_declared)
    expect = data.get("expect")
    force = data.get("force_action_error")
    _require_expect_shape(expect, sf_section, trigger, force)
    provision = ctx.tools.call(
        "harness.salesforce.seed_records", {"salesforce": deepcopy(sf_section)}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    refs = _salesforce_ref_tokens(sf_section, provision)
    resolved_trigger = _replace_value(deepcopy(trigger), refs)
    _require_no_tokens(resolved_trigger, "trigger_input")
    resolved_expect = _replace_value(deepcopy(expect), refs)
    _require_no_tokens(resolved_expect, "expect")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": resolved_trigger,
        "track": data.get("track") or TRACK,
        "expect": resolved_expect,
        "raw_validation": validation,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": refs,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_117884798(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_117884798(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing resolved expect block")
    if not isinstance(seed.get("salesforce_live"), dict):
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
        details["initial_snapshot"] = ctx.tools.call("harness.salesforce.snapshot", {})
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = ctx.tools.call("harness.salesforce.snapshot", {})
    finally:
        cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
        details["cleanup_response"] = cleanup_response
    if not (cleanup_response or {}).get("ok"):
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
    result["verifier"] = verify_117884798(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any], refs_declared: set[str]) -> None:
    if sorted(trigger.keys()) != ["parameters"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the parameters object; "
            f"got {sorted(trigger.keys())}"
        )
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict) or sorted(parameters.keys()) != [
        "original_opp_id", "renewal_opp_id"
    ]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must be exactly original_opp_id + "
            f"renewal_opp_id; got {parameters}"
        )
    for key in ("original_opp_id", "renewal_opp_id"):
        token = str(parameters.get(key) or "")
        if token not in refs_declared:
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger parameters.{key} must be a $<REF>_ID token of a "
                f"seeded Opportunity (live ids exist only after provisioning); got {token!r}"
            )


def _require_salesforce_section(sf_section: Any) -> set[str]:
    if not isinstance(sf_section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce must be an object")
    unexpected = sorted(set(sf_section.keys()) - {"schema", "relationship_expansion", "records"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce has unexpected keys: {unexpected}")
    if sf_section.get("relationship_expansion") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.relationship_expansion must be true "
            "(foreach Contact.Email/Contact.Name read the expanded parent)"
        )
    if sf_section.get("schema") != NURTURE_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare exactly the 5 Nurture "
            f"OpportunityContactRole custom fields {NURTURE_SCHEMA} (schema-in-seed "
            "ensure_custom_field; FIRST OCR-custom-field use, Tooling API fails fast if the "
            "org rejects them)"
        )
    records = sf_section.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records must be a non-empty list")
    refs_seen: set[str] = set()
    opp_refs: set[str] = set()
    contact_refs: set[str] = set()
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
        if sobject == "Opportunity":
            opp_refs.add(f"${ref.upper()}_ID")
            for key in ("Name", "StageName", "CloseDate"):
                if not str(fields.get(key) or "").strip():
                    raise RuntimeError(f"recipe {RECIPE_ID} seeded Opportunity requires explicit {key}")
        if sobject == "Contact":
            contact_refs.add(f"${ref.upper()}_ID")
            for key in ("FirstName", "LastName", "Email"):
                if not str(fields.get(key) or "").strip():
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} seeded Contact requires explicit {key} "
                        "(Contact.Name = 'First Last' feeds failed_list.contact_name)"
                    )
        if sobject == "OpportunityContactRole":
            if "CurrencyIsoCode" in fields:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} NEVER seed CurrencyIsoCode on an OCR: it is a "
                    "multicurrency-only field; the pill must resolve MISSING so create/update "
                    "DROP it (single-currency bench org)"
                )
            for key in ("OpportunityId", "ContactId"):
                if not str(fields.get(key) or "").strip():
                    raise RuntimeError(f"recipe {RECIPE_ID} seeded OCR requires explicit {key}")
            if not str(fields.get("Role") or "").strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} seeded OCR requires an explicit Role (it feeds the "
                    "create/update Role pill and failed_list.opportunity_contact_role)"
                )
    if len(opp_refs) != 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed needs exactly the original AND renewal Opportunities; "
            f"got {sorted(opp_refs)}"
        )
    for record in records:
        if str(record.get("sobject") or "") != "OpportunityContactRole":
            continue
        fields = record.get("fields") or {}
        if str(fields.get("OpportunityId") or "") not in opp_refs:
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded OCR must reference a seeded Opportunity "
                f"token; got {fields.get('OpportunityId')!r}"
            )
        if str(fields.get("ContactId") or "") not in contact_refs:
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded OCR must reference a seeded Contact token; "
                f"got {fields.get('ContactId')!r}"
            )
    return {f"${ref.upper()}_ID" for ref in refs_seen}


def _require_expect_shape(
    expect: Any,
    sf_section: dict[str, Any],
    trigger: dict[str, Any],
    force: Any,
) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    count = expect.get("executed_action_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 4:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.executed_action_count must be an int >= 4 "
            "(2 declares + original search + return always run)"
        )
    for key in ("successful_count", "failed_count"):
        value = expect.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise RuntimeError(f"recipe {RECIPE_ID} expect.{key} must be a non-negative int")
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or not items:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must be a non-empty list")
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[{idx}] must be an object")
        unknown = sorted(set(item.keys()) - _EXPECT_ITEM_KEYS)
        if unknown:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] has unrecognized keys: {unknown}"
            )
        if item.get("tool") not in ALLOWED_TOOLS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}].tool must be one of "
                f"{ALLOWED_TOOLS}; got {item.get('tool')!r}"
            )
        if not any(key in item for key in _EXPECT_VALUE_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] must carry at least one value "
                "key (corpus lint)"
            )
        fields = (item.get("args_contains") or {}).get("fields")
        if isinstance(fields, dict) and "CurrencyIsoCode" in fields:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] must not pin CurrencyIsoCode "
                "(the pill resolves MISSING and the field is dropped)"
            )
    if items[0].get("tool") != "salesforce.search_records":
        raise RuntimeError(
            f"recipe {RECIPE_ID} the first expectation is always the original-opp OCR search"
        )
    if items[-1].get("tool") != "workato_recipe_function.return_result":
        raise RuntimeError(
            f"recipe {RECIPE_ID} the final expectation must pin the return_result payload"
        )
    result_contains = items[-1].get("result_contains")
    if not isinstance(result_contains, dict) or sorted(result_contains.keys()) != [
        "failed_list", "sucessful_list"
    ]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the return expectation must pin BOTH failed_list and "
            "sucessful_list (raw 'sucessful' typo verbatim)"
        )
    ocr_count = sum(
        1 for record in sf_section.get("records") or []
        if str(record.get("sobject") or "") == "OpportunityContactRole"
        and str((record.get("fields") or {}).get("OpportunityId") or "")
        == str((trigger.get("parameters") or {}).get("original_opp_id") or "")
    )
    if force is not None:
        if not isinstance(force, dict) or str(force.get("step_as") or "") != CREATE_AS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} force_action_error must target the create step "
                f"{CREATE_AS!r} (the catch branch is only reachable via forced error)"
            )
        if not str(force.get("error") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} force_action_error requires an explicit error string")
        if ocr_count != 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} forced-error variants must seed exactly ONE original-opp "
                "OCR (force_action_error is step-scoped and fails EVERY iteration)"
            )
        if expect.get("successful_count") != 0 or expect.get("failed_count") != ocr_count:
            raise RuntimeError(
                f"recipe {RECIPE_ID} forced-error variants fail every iteration: expect "
                f"successful_count 0 and failed_count {ocr_count}"
            )
    if expect.get("stale_pill_equals_first_create") not in (None, True):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.stale_pill_equals_first_create must be true when present"
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


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
