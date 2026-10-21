from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_112451583


RECIPE_ID = "112451583"
SEED_TYPE = "workato_service_check_email_domain_variant"
TRACK = "live_salesforce_check_email_domain_service"
TRIGGER_PROVIDER = "workato_service"
TRIGGER_NAME = "receive_request"
SERVICE_NAME = "Check email domain in Salesforce"
LOOKUP_TABLE_ID = "3258396"
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")

# Callable service "Check email domain in Salesforce" (trigger as
# receive_request; POST /check_email_domain_in_salesforce; request
# {email, upsert_choice.account_id} -- only request.email is dereferenced):
#   TRY (step 2):
#     #3  logger.log_message (as 83af7689) domain =
#         request.email.split("@")[1]  -- blank email resolves MISSING -> ""
#     #4  lookup_table.search_entries (as search_entries) table 3258396
#         'Freemail providers', col1 = logger message  -- Workato-internal mock
#     IF #5 entries size > 0:
#       #6  send_reply success {domain, result: "filtered"}
#       #7  STOP (stop_with_error=false, graceful)
#     #8  salesforce.search_sobjects Domain__c (as search_sobjects) filter
#         Domain__c = logger message, limit 150 -- LIVE benchmark-owned records
#     IF #9 Domain__c size == 0:
#       #10 send_reply success {domain, result: "not found"}
#     IF #11 Domain__c size > 0:
#       #12 send_reply success {domain, message: current Account__c id,
#           result: "found", salesforce_account_name: JOIN PILL
#           get_custom_object(Account__c -> Account.id).Name}
#   CATCH (step 13, as catch, max_retry_count 0):
#     IF #14 catch.message == "'Message' must be present" AND logger blank:
#       #15 send_reply error "No email address provided. Please provide an
#           email address."
#     IF #16 catch.message != "'Message' must be present":
#       #17 send_reply error <catch.message>
#
# TWIN: byte-identical to 111350115 except lookup_table_id 3258396
# (vs 3258381); built independently with its own groundtruth.
#
# Live backend: Salesforce Domain__c custom object (DEPLOYED: Domain__c Text,
# Account__c Lookup(Account)) + benchmark-owned Account for the found-branch
# join. seed.salesforce.relationship_expansion serves the joined parent
# Account fields on read-back. The seed schema declares both custom fields for
# FLS (ensure_custom_field early-exits into the FLS grant because the fields
# already exist; sf_type is only consulted when a field is missing).
# Workato-internal (deterministic mock): lookup table 3258396, service
# replies, logger.
#
# Branch-mapping notes (variant-plan divergences, recorded per benmark_rules):
# - catch_blank_email: in real Workato a blank email makes the logger raise
#   "'Message' must be present"; the harness logger logs "" without raising,
#   so that catch branch is reachable ONLY via seed.force_action_error on
#   step_as search_entries with EXACTLY that message (batch-01 precedent for
#   forced catch branches). The logger still runs first and stays blank, so
#   IF #14 evaluates both arms faithfully.
# - catch_generic_error: force_action_error on step_as search_sobjects with a
#   custom message exercises IF #16. The failed action records no trace row
#   (fault injection precedes the adapter), so executed_action_count excludes
#   it.
# - The IF #14 combination (message == literal AND logger NOT blank) falls
#   through with no reply; it is a reachable no-op, not required coverage.
#
# Cleanup: only variants that seed live records need it; they are deleted by
# harness.salesforce.cleanup in run_112451583's finally block. Lookup-table
# state is per-run in-memory mock state, fully overwritten by every seed.

# Frozen document-order structure pins (keyword/number/as/provider/name/skip +
# verbatim raw input per node, incl. the split("@")[1] formula, the
# get_custom_object join pill and the catch literals). Any upstream drift
# fails validation instead of silently changing ground truth.
_STRUCTURE_PINS_JSON = r'''
[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "receive_request",
  "provider": "workato_service",
  "name": "receive_request",
  "skip": false,
  "input": {
   "reply_schema_json": "[\n  {\n    \"name\": \"domain\",\n    \"label\":\"Domain\",\n    \"type\": \"string\",\n    \"control_type\": \"text\"\n  },\n  {\n    \"name\": \"result\",\n    \"label\":\"Result\",\n    \"type\": \"string\",\n    \"control_type\": \"select\",\n    \"options\": [\n         [\"Filtered\",\"filtered\"],\n         [\"Found\",\"found\"],\n         [\"Not found\",\"not found\"]\n    ]\n  },\n  {\n    \"name\": \"message\",\n    \"label\":\"Message\",\n    \"type\": \"string\",\n    \"control_type\": \"text\",\n    \"optional\":true\n  },\n  {\n    \"name\": \"salesforce_account_name\",\n    \"label\":\"Salesforce Account Name\",\n    \"type\": \"string\",\n    \"control_type\": \"text\",\n    \"optional\":true\n  }\n]",
   "request_schema_json": "[\n  {\n    \"name\": \"email\",\n    \"label\":\"Email address\",\n    \"description\":\"Enter the email address to check\",\n    \"type\": \"string\",\n    \"control_type\": \"email\"\n  },\n  {\n    \"name\": \"upsert_choice\",\n    \"label\":\"Upsert domain\",\n    \"type\": \"object\",\n    \"properties\":[\n      {\n        \"name\": \"account_id\",\n        \"type\": \"string\",\n        \"label\": \"Salesforce Account ID\",\n        \"control_type\": \"text\",\n        \"optional\": true\n      }\n    ]\n  }\n]",
   "rest_request_method": "post",
   "rest_request_path": "/check_email_domain_in_salesforce",
   "service_name": "Check email domain in Salesforce"
  }
 },
 {
  "keyword": "try",
  "number": 2,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {}
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "83af7689",
  "provider": "logger",
  "name": "log_message",
  "skip": false,
  "input": {
   "message": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"receive_request\",\"path\":[\"request\",\"email\"]}').split(\"@\")[1]",
   "user_logs_enabled": "false"
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "search_entries",
  "provider": "lookup_table",
  "name": "search_entries",
  "skip": false,
  "input": {
   "lookup_table_id": "3258396",
   "parameters": {
    "col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"83af7689\",\"path\":[\"message\"]}')}"
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
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"search_entries\",\"path\":[\"entries\", {\"path_element_type\": \"size\"}]}')}",
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
  "as": "send_reply",
  "provider": "workato_service",
  "name": "send_reply",
  "skip": false,
  "input": {
   "reply": {
    "domain": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"83af7689\",\"path\":[\"message\"]}')}",
    "result": "filtered"
   },
   "reply_type": "success"
  }
 },
 {
  "keyword": "stop",
  "number": 7,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "stop_with_error": "false"
  }
 },
 {
  "keyword": "action",
  "number": 8,
  "as": "search_sobjects",
  "provider": "salesforce",
  "name": "search_sobjects",
  "skip": false,
  "input": {
   "Domain__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"83af7689\",\"path\":[\"message\"]}')}",
   "limit": "150",
   "sobject_name": "Domain__c"
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
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"search_sobjects\",\"path\":[\"Domain__c\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "equals_to",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 10,
  "as": "send_reply1",
  "provider": "workato_service",
  "name": "send_reply",
  "skip": false,
  "input": {
   "reply": {
    "domain": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"83af7689\",\"path\":[\"message\"]}')}",
    "result": "not found"
   },
   "reply_type": "success"
  }
 },
 {
  "keyword": "if",
  "number": 11,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"search_sobjects\",\"path\":[\"Domain__c\", {\"path_element_type\": \"size\"}]}')}",
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
  "number": 12,
  "as": "send_reply3",
  "provider": "workato_service",
  "name": "send_reply",
  "skip": false,
  "input": {
   "reply": {
    "domain": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"83af7689\",\"path\":[\"message\"]}')}",
    "message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"search_sobjects\",\"path\":[\"Domain__c\", {\"path_element_type\": \"current_item\"}, \"Account__c\"]}')}",
    "result": "found",
    "salesforce_account_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"search_sobjects\",\"path\":[\"Domain__c\", {\"path_element_type\": \"current_item\"}, {\"path_element_type\": \"join\", \"action\": \"get_custom_object\", \"src_key\": \"Account__c\", \"dst_key\": \"id\", \"args\": {\"sobject_name\": \"Account\"}}, \"Name\"]}')}"
   },
   "reply_type": "success"
  }
 },
 {
  "keyword": "catch",
  "number": 13,
  "as": "catch",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "max_retry_count": "0",
   "retry_interval": "2"
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
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"catch\",\"path\":[\"message\"]}')}",
     "operand": "equals_to",
     "rhs": "'Message' must be present"
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"83af7689\",\"path\":[\"message\"]}')}",
     "operand": "blank"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 15,
  "as": "send_reply__5",
  "provider": "workato_service",
  "name": "send_reply",
  "skip": false,
  "input": {
   "message": "No email address provided. Please provide an email address.",
   "reply_type": "error"
  }
 },
 {
  "keyword": "if",
  "number": 16,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"catch\",\"path\":[\"message\"]}')}",
     "operand": "not_equals_to",
     "rhs": "'Message' must be present"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 17,
  "as": "send_reply__6",
  "provider": "workato_service",
  "name": "send_reply",
  "skip": false,
  "input": {
   "message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"catch\",\"path\":[\"message\"]}')}",
   "reply_type": "error"
  }
 }
]
'''
STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.log_message",
    "lookup_table.search_entries",
    "workato_service.send_reply",
    "salesforce.search_records",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "salesforce.search_records",
    "workato_service.send_reply",
]
# Domain__c custom fields the recipe reads (schema-in-seed for the FLS grant;
# both fields are already deployed live -- Account__c is a Lookup(Account) in
# the org, the Text sf_type below is never used to create it).
REQUIRED_DOMAIN_SCHEMA: dict[str, str] = {
    "Domain__c": "Text",
    "Account__c": "Text",
}
CATCH_MESSAGE_LITERAL = "'Message' must be present"
BLANK_EMAIL_REPLY = "No email address provided. Please provide an email address."
REPLY_RESULTS = {"filtered", "found", "not found"}
FORCEABLE_STEPS = {"search_entries", "search_sobjects"}


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


def validate_112451583(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    trigger_cfg = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    if str(trigger_cfg.get("service_name") or "") != SERVICE_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger service name changed")
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
        "service_name": SERVICE_NAME,
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


def seed_112451583(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_112451583(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"lookup_table", "salesforce"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    lookup_section = seed_in.get("lookup_table")
    _require_lookup_section(lookup_section)
    sf_section = seed_in.get("salesforce")
    if sf_section is not None:
        _require_salesforce_section(sf_section)
    expect = data.get("expect")
    _require_expect_shape(expect, has_salesforce=sf_section is not None)
    _require_force_shape(data.get("force_action_error"))
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track"),
        "raw_validation": validation,
        "lookup_table": deepcopy(lookup_section),
    }
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


def run_112451583(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_112451583(raw)
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
    result["verifier"] = verify_112451583(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != ["request"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the request object"
        )
    request = trigger.get("request")
    if not isinstance(request, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input.request must be an object")
    allowed = {"email", "upsert_choice"}
    unexpected = sorted(set(request) - allowed)
    if unexpected:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger request has unexpected keys: {unexpected}"
        )
    if "email" not in request or not isinstance(request.get("email"), str):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger request.email must be an explicit string "
            "(empty string is the declared blank-email case)"
        )
    if "upsert_choice" in request:
        upsert = request.get("upsert_choice")
        if not isinstance(upsert, dict) or sorted(upsert.keys()) != ["account_id"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger request.upsert_choice must carry exactly account_id"
            )
        if not isinstance(upsert.get("account_id"), str):
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger request.upsert_choice.account_id must be a string"
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
            f"recipe {RECIPE_ID} seed.salesforce.relationship_expansion must be true "
            "(the found reply walks the Domain__c Account__c -> Account.Name join)"
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


def _require_expect_shape(expect: Any, has_salesforce: bool) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    for key in ("stopped", "reply_type", "executed_action_count", "tools", "tool_expectations"):
        if key not in expect:
            raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required key {key!r}")
    if not isinstance(expect.get("stopped"), bool):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.stopped must be a boolean")
    reply_type = str(expect.get("reply_type") or "")
    if reply_type not in {"success", "error"}:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.reply_type must be success or error")
    if expect["stopped"]:
        if expect.get("stop_step_number") != 7:
            raise RuntimeError(
                f"recipe {RECIPE_ID} stop variants must pin stop_step_number 7 "
                "(the only stop in the raw recipe)"
            )
        if reply_type != "success":
            raise RuntimeError(
                f"recipe {RECIPE_ID} the graceful stop follows the filtered success reply"
            )
    if reply_type == "error":
        if not str(expect.get("message") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} error variants must pin the exact expect.message"
            )
        if "reply" in expect:
            raise RuntimeError(
                f"recipe {RECIPE_ID} error replies carry no reply object; drop expect.reply"
            )
    else:
        reply = expect.get("reply")
        if not isinstance(reply, dict):
            raise RuntimeError(
                f"recipe {RECIPE_ID} success variants must pin the FULL expect.reply object"
            )
        result = str(reply.get("result") or "")
        if result not in REPLY_RESULTS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.reply.result must be one of {sorted(REPLY_RESULTS)}"
            )
        if result == "found":
            if sorted(reply.keys()) != ["domain", "message", "result", "salesforce_account_name"]:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} found replies pin exactly "
                    "domain/message/result/salesforce_account_name"
                )
            if not has_salesforce:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} the found branch requires a live seed.salesforce section"
                )
            if not str(reply.get("salesforce_account_name") or "").strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} found replies must pin the joined Account Name"
                )
        else:
            if sorted(reply.keys()) != ["domain", "result"]:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {result} replies pin exactly domain/result"
                )
        if not str(reply.get("domain") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} success replies must pin the exact domain")


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
