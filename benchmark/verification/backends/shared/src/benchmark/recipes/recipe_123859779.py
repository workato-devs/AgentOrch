from __future__ import annotations

import json
import re
import time
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_123859779


RECIPE_ID = "123859779"
SEED_TYPE = "salesforce_gong_meetings_api_endpoint_variant"
TRACK = "live_salesforce_api_platform_gong_meetings"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "7c9bdd0d"
CALL_SOBJECT = "Gong__Gong_Call__c"
SEARCH_AS = "9126ea78"
RETURN_OK_AS = "a58e05ea"
STOP_AS = "e64c4396"
STOP_NUMBER = 7
CATCH_AS = "18f2fc6d"
RETURN_ERR_AS = "78bb8c52"
FORCEABLE_STEPS = {SEARCH_AS}
CREATED_DATE_SPACING_SECONDS = 1.2
REQUIRED_SCHEMA = [
    {"sobject": "Gong_Call__c", "field": "Primary_Account__c", "sf_type": "Text"},
    {"sobject": "Gong_Call__c", "field": "Call_Brief__c", "sf_type": "Text"},
    {"sobject": "Gong_Call__c", "field": "Call_Highlights_Next_Steps__c", "sf_type": "Text"},
    {"sobject": "Gong_Call__c", "field": "Call_ID__c", "sf_type": "Text"},
]
CALL_FIELD_KEYS = {
    "Name",
    "Gong__Primary_Account__c",
    "Gong__Call_Brief__c",
    "Gong__Call_Highlights_Next_Steps__c",
    "Gong__Call_ID__c",
}
GONG_URL_PREFIX = "https://app.gong.io/call?id="
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_SYNTHETIC_ACCOUNT_RE = re.compile(r"001[0-9A-Za-z]{12,15}")
_ABS_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "7c9bdd0d",
  "provider": "workato_api_platform",
  "name": "receive_request",
  "skip": false,
  "input": {
   "request": {
    "content_type": "json",
    "path_params": "[]",
    "schema": "[{\"name\":\"sfdcAccountId\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Sfdc account ID\"}]"
   },
   "response": {
    "content_type": "json",
    "responses": [
     {
      "body_schema": "[{\"name\":\"data\",\"type\":\"array\",\"of\":\"object\",\"label\":\"data\",\"properties\":[{\"control_type\":\"text\",\"label\":\"Meeting brief\",\"type\":\"string\",\"name\":\"meeting_brief\"},{\"control_type\":\"text\",\"label\":\"Next steps\",\"type\":\"string\",\"name\":\"next_steps\"}],\"optional\":true},{\"name\":\"rawSources\",\"type\":\"array\",\"of\":\"object\",\"label\":\"Raw sources\",\"properties\":[{\"control_type\":\"text\",\"label\":\"Title\",\"type\":\"string\",\"name\":\"title\"},{\"control_type\":\"text\",\"label\":\"Snippet\",\"type\":\"string\",\"name\":\"snippet\"},{\"control_type\":\"text\",\"label\":\"URL\",\"type\":\"string\",\"name\":\"url\"},{\"control_type\":\"text\",\"label\":\"Tool\",\"type\":\"string\",\"name\":\"tool\"}],\"optional\":true},{\"name\":\"error\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Error\"},{\"name\":\"success\",\"type\":\"boolean\",\"optional\":false,\"control_type\":\"checkbox\",\"label\":\"Success\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Success\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"success\",\"type\":\"boolean\",\"optional\":false}}]",
      "http_status_code": "200",
      "name": "Success"
     }
    ]
   }
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
  "as": "9126ea78",
  "provider": "salesforce",
  "name": "search_sobjects_soql",
  "skip": false,
  "input": {
   "field_list": "Gong__Primary_Account__c\nGong__Call_Brief__c\nGong__Call_Highlights_Next_Steps__c\nCreatedDate\nName\nGong__Call_ID__c",
   "limit": "20",
   "query": "Gong__Primary_Account__c = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"7c9bdd0d\",\"path\":[\"request\", \"sfdcAccountId\"]}')}' AND CreatedDate = LAST_N_DAYS:90 ORDER BY CreatedDate DESC",
   "sobject_name": "Gong__Gong_Call__c"
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
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"9126ea78\",\"path\":[\"Gong__Gong_Call__c\", {\"path_element_type\": \"size\"}]}')}",
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
  "number": 5,
  "as": "a58e05ea",
  "provider": "workato_api_platform",
  "name": "return_response",
  "skip": false,
  "input": {
   "http_status_code": "200",
   "response": {
    "data": {
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"9126ea78\",\"path\":[\"Gong__Gong_Call__c\"]}')}",
     "meeting_brief": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"9126ea78\",\"path\":[\"Gong__Gong_Call__c\", {\"path_element_type\": \"current_item\"}, \"Gong__Call_Brief__c\"]}')}",
     "next_steps": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"9126ea78\",\"path\":[\"Gong__Gong_Call__c\", {\"path_element_type\": \"current_item\"}, \"Gong__Call_Highlights_Next_Steps__c\"]}')}"
    },
    "rawSources": {
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"9126ea78\",\"path\":[\"Gong__Gong_Call__c\"]}')}",
     "snippet": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"9126ea78\",\"path\":[\"Gong__Gong_Call__c\", {\"path_element_type\": \"current_item\"}, \"Name\"]}')}",
     "title": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"9126ea78\",\"path\":[\"Gong__Gong_Call__c\", {\"path_element_type\": \"current_item\"}, \"Name\"]}')}",
     "tool": "gong_meetings",
     "url": "https://app.gong.io/call?id=#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"9126ea78\",\"path\":[\"Gong__Gong_Call__c\", {\"path_element_type\": \"current_item\"}, \"Gong__Call_ID__c\"]}')}"
    },
    "success": "true"
   }
  }
 },
 {
  "keyword": "else",
  "number": 6,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {}
 },
 {
  "keyword": "stop",
  "number": 7,
  "as": "e64c4396",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "stop_reason": "No records found",
   "stop_with_error": "true"
  }
 },
 {
  "keyword": "catch",
  "number": 8,
  "as": "18f2fc6d",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "max_retry_count": "0",
   "retry_interval": "2"
  }
 },
 {
  "keyword": "action",
  "number": 9,
  "as": "78bb8c52",
  "provider": "workato_api_platform",
  "name": "return_response",
  "skip": false,
  "input": {
   "http_status_code": "200",
   "response": {
    "error": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"18f2fc6d\",\"path\":[\"message\"]}')}",
    "success": "false"
   }
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_api_platform.return_response",
]
EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "stopped",
    "response",
)
OPTIONAL_EXPECT_KEYS = {"stop_step_as", "stop_step_number", "catch_message"}


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


def validate_123859779(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_123859779(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_123859779(raw)
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
    expect = data.get("expect")
    force = data.get("force_action_error")
    _require_force_shape(force, expect)
    salesforce_section = seed_in.get("salesforce")
    _require_expect_shape(expect, force, trigger, salesforce_section)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
    }
    if salesforce_section is not None:
        _require_salesforce_section(salesforce_section, trigger, expect)
        state, seed_snapshot, refs = _provision_salesforce_phases(ctx, salesforce_section)
        trigger = _replace_value(trigger, refs)
        expect = _replace_value(deepcopy(expect), refs)
        out["salesforce_live"] = state
        out["salesforce_seed_snapshot"] = seed_snapshot
        out["salesforce_ref_tokens"] = refs
    else:
        account_id = str((trigger.get("request") or {}).get("sfdcAccountId") or "")
        if not _SYNTHETIC_ACCOUNT_RE.fullmatch(account_id):
            raise RuntimeError(
                f"recipe {RECIPE_ID} live-less (forced-error) variants need a well-formed "
                f"synthetic Account id in trigger.request.sfdcAccountId (the forced error "
                f"raises before arg resolution, so it is never dereferenced): {account_id!r}"
            )
    _require_no_tokens(trigger, "trigger")
    _require_no_tokens(expect, "expect")
    out["trigger"] = trigger
    out["expect"] = deepcopy(expect)
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_123859779(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_123859779(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    live = isinstance(seed.get("salesforce_live"), dict)
    if "salesforce.search_records" in (expect.get("tools") or []) and not live:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    if live and not seed["salesforce_live"].get("strict_soql_conditions"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires strict_soql_conditions in the live state "
            "(the LAST_N_DAYS:90 date literal and ORDER BY CreatedDate DESC are strict-only)"
        )
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
        "force_action_error": deepcopy(seed.get("force_action_error"))
        if isinstance(seed.get("force_action_error"), dict)
        else None,
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
            # Required cleanup: owned Gong_Call__c + Account seeds must not
            # leak into later runs (the recipe itself only reads).
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
    result["verifier"] = verify_123859779(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {"request"} or not isinstance(trigger.get("request"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'request': {{...}}}}"
        )
    request = trigger["request"]
    if set(request) != {"sfdcAccountId"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger request must carry exactly sfdcAccountId "
            "(the declared request schema)"
        )
    if not isinstance(request.get("sfdcAccountId"), str) or not request["sfdcAccountId"].strip():
        raise RuntimeError(f"recipe {RECIPE_ID} trigger request.sfdcAccountId must be a non-empty string")


def _require_force_shape(force: Any, expect: Any) -> None:
    if force is None:
        return
    if not isinstance(force, dict) or str(force.get("step_as") or "") not in FORCEABLE_STEPS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} fault injection is sanctioned only on step "
            f"{sorted(FORCEABLE_STEPS)} (inside the try): {force!r}"
        )
    if not str(force.get("error") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error.error must be a non-empty message")
    if not isinstance(expect, dict) or str(expect.get("catch_message") or "") != str(force.get("error")):
        raise RuntimeError(
            f"recipe {RECIPE_ID} forced-error variants must pin expect.catch_message equal to "
            "the forced error message (the CATCH renders it into response.error)"
        )


def _require_expect_shape(
    expect: Any, force: Any, trigger: dict[str, Any], salesforce_section: Any
) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    absolute_dates = _ABS_DATE_RE.findall(json.dumps(expect))
    if absolute_dates:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect pins must never encode absolute dates "
            f"(guard (b) of the system-assigned wall-clock form: CreatedDate is "
            f"live-assigned at seed time, so a dated pin would rot): "
            f"{sorted(set(absolute_dates))}"
        )
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(set(expect) - set(EXPECT_KEYS) - OPTIONAL_EXPECT_KEYS)
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has unexpected keys: {unknown}")
    tools = expect.get("tools")
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tools, list) or not isinstance(tool_expectations, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools/tool_expectations must be lists")
    if len(tools) != len(tool_expectations):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry")
    unknown_tools = sorted(set(tools) - set(ALLOWED_TOOLS))
    if unknown_tools:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools has unknown tools: {unknown_tools}")
    if not isinstance(expect.get("stopped"), bool):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.stopped must be a bool")
    if force is not None:
        # CATCH path: the forced error raises BEFORE the search resolves its
        # args, so no salesforce call and no live seed may exist.
        if salesforce_section is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} forced-error variants must not seed salesforce "
                "(the search never executes; seeded records would be unread noise)"
            )
        if expect["stopped"] or tools != ["workato_api_platform.return_response"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} forced-error variants run exactly the CATCH "
                "return_response (no stop row)"
            )
        if expect.get("response") != {"error": str(force.get("error")), "success": False}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} forced-error variants must pin expect.response to "
                "{'error': <forced message>, 'success': false} verbatim"
            )
        return
    if "catch_message" in expect:
        raise RuntimeError(f"recipe {RECIPE_ID} only forced-error variants pin catch_message")
    if salesforce_section is None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} non-forced variants require seed.salesforce "
            "(the step-3 search runs LIVE over owned stand-in records)"
        )
    if expect["stopped"]:
        if tools != ["salesforce.search_records"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} the ELSE/STOP path runs exactly the search: {tools}"
            )
        if expect.get("response") is not None:
            raise RuntimeError(f"recipe {RECIPE_ID} stopped variants must pin expect.response null")
        if str(expect.get("stop_step_as") or "") != STOP_AS or expect.get("stop_step_number") != STOP_NUMBER:
            raise RuntimeError(
                f"recipe {RECIPE_ID} stopped variants must pin stop_step_as {STOP_AS!r} / "
                f"stop_step_number {STOP_NUMBER}"
            )
        return
    if tools != ["salesforce.search_records", "workato_api_platform.return_response"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the records-found path runs search then return_response: {tools}"
        )
    response = expect.get("response")
    if (
        not isinstance(response, dict)
        or sorted(response) != ["data", "rawSources", "success"]
        or response.get("success") is not True
        or not isinstance(response.get("data"), list)
        or not response["data"]
        or not isinstance(response.get("rawSources"), list)
        or len(response["data"]) != len(response["rawSources"])
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} records-found variants must pin expect.response "
            "{'data': [...], 'rawSources': [...], 'success': true} with matching lengths"
        )


def _matching_calls_in_phase_order(
    section: dict[str, Any], trigger: dict[str, Any]
) -> list[dict[str, Any]]:
    account_token = str((trigger.get("request") or {}).get("sfdcAccountId") or "")
    matching: list[dict[str, Any]] = []
    for phase_index, phase in enumerate(section.get("phases") or []):
        phase_matches = [
            record
            for record in phase.get("records") or []
            if isinstance(record, dict)
            and str(record.get("sobject") or "") == CALL_SOBJECT
            and str((record.get("fields") or {}).get("Gong__Primary_Account__c") or "") == account_token
        ]
        if len(phase_matches) > 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} phase {phase_index} seeds {len(phase_matches)} calls for the "
                "trigger account -- ORDER BY CreatedDate DESC needs each response record in its "
                "OWN phase (1s SF timestamp granularity; ties are nondeterministic)"
            )
        matching.extend(phase_matches)
    return matching


def _require_salesforce_section(
    section: Any, trigger: dict[str, Any], expect: dict[str, Any]
) -> None:
    if not isinstance(section, dict) or sorted(section) != ["phases", "schema", "strict_soql_conditions"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce must be exactly "
            "{'strict_soql_conditions': true, 'schema': [...], 'phases': [...]}"
        )
    if section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true "
            "(LAST_N_DAYS:90 and ORDER BY are strict-only)"
        )
    if section.get("schema") != REQUIRED_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare exactly "
            f"{json.dumps(REQUIRED_SCHEMA)} (FLS re-ensure on the mdapi stand-in columns)"
        )
    phases = section.get("phases")
    if not isinstance(phases, list) or not phases:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.phases must be a non-empty list of "
            "{'records': [...]} sections (phase order = CreatedDate order)"
        )
    account_token = str((trigger.get("request") or {}).get("sfdcAccountId") or "")
    account_refs: set[str] = set()
    for phase_index, phase in enumerate(phases):
        if not isinstance(phase, dict) or sorted(phase) != ["records"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} each salesforce phase must be exactly {{'records': [...]}}"
            )
        records = phase.get("records")
        if not isinstance(records, list) or not records:
            raise RuntimeError(f"recipe {RECIPE_ID} salesforce phase {phase_index} has no records")
        for record in records:
            if not isinstance(record, dict):
                raise RuntimeError(f"recipe {RECIPE_ID} seeded records must be objects: {record}")
            ref = str(record.get("ref") or "").strip()
            if not ref:
                raise RuntimeError(f"recipe {RECIPE_ID} every seeded record needs a 'ref': {record}")
            fields = record.get("fields")
            if not isinstance(fields, dict) or not fields:
                raise RuntimeError(f"recipe {RECIPE_ID} every seeded record needs explicit fields: {record}")
            if "CreatedDate" in fields or record.get("read_fields"):
                # Dead seed path, proven: CreatedDate is system-set (harness
                # _physical_fields fails fast on the non-createable column) --
                # the out-of-window ELSE is org-unrepresentable and must not
                # be attempted.
                raise RuntimeError(
                    f"recipe {RECIPE_ID} CreatedDate is system-set and cannot be seeded "
                    f"(read-back extras already expose it): {record}"
                )
            sobject = str(record.get("sobject") or "")
            if sobject == "Account":
                if set(fields) != {"Name"} or not str(fields.get("Name") or "").strip():
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} Account seeds carry exactly a non-empty Name: {record}"
                    )
                account_refs.add(f"${ref.upper()}_ID")
            elif sobject == CALL_SOBJECT:
                if set(fields) != CALL_FIELD_KEYS:
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} {CALL_SOBJECT} seeds must set exactly "
                        f"{sorted(CALL_FIELD_KEYS)}; got {sorted(fields)}"
                    )
                for key in CALL_FIELD_KEYS:
                    if not isinstance(fields.get(key), str) or not fields[key].strip():
                        raise RuntimeError(
                            f"recipe {RECIPE_ID} {CALL_SOBJECT} seed {key} must be a non-empty "
                            f"string: {record}"
                        )
                if fields["Gong__Primary_Account__c"] not in account_refs:
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} every seeded call must reference an earlier-seeded "
                        f"owned Account via its $REF token: {record}"
                    )
            else:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} seeded records must be Account or {CALL_SOBJECT}: {record}"
                )
    if account_token not in account_refs:
        # Even the no-records variant grounds the trigger on a real (call-less)
        # owned Account, so the SOQL equality leaf compares live ids.
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger sfdcAccountId must be a seeded Account $REF token: "
            f"{account_token!r}"
        )
    matching = _matching_calls_in_phase_order(section, trigger)
    if expect.get("stopped") is True:
        if matching:
            raise RuntimeError(
                f"recipe {RECIPE_ID} stopped variants must seed zero calls for the trigger "
                f"account; found {len(matching)}"
            )
        decoys = [
            record
            for phase in section.get("phases") or []
            for record in phase.get("records") or []
            if isinstance(record, dict) and str(record.get("sobject") or "") == CALL_SOBJECT
        ]
        if not decoys:
            raise RuntimeError(
                f"recipe {RECIPE_ID} the no-records variant must seed at least one decoy call "
                "for a DIFFERENT account (proves the live search executed and the account "
                "equality leaf bit)"
            )
        return
    if not matching:
        raise RuntimeError(
            f"recipe {RECIPE_ID} records-found variants must seed calls for the trigger account"
        )
    response = expect.get("response") or {}
    expected_data = [
        {
            "meeting_brief": record["fields"]["Gong__Call_Brief__c"],
            "next_steps": record["fields"]["Gong__Call_Highlights_Next_Steps__c"],
        }
        for record in reversed(matching)
    ]
    expected_sources = [
        {
            "snippet": record["fields"]["Name"],
            "title": record["fields"]["Name"],
            "tool": "gong_meetings",
            "url": GONG_URL_PREFIX + record["fields"]["Gong__Call_ID__c"],
        }
        for record in reversed(matching)
    ]
    if response.get("data") != expected_data or response.get("rawSources") != expected_sources:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.response must map the matching calls in REVERSE phase "
            f"order (CreatedDate DESC = later phase first):\nexpected data "
            f"{json.dumps(expected_data)}\nexpected rawSources {json.dumps(expected_sources)}"
        )
    if len(matching) < 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the records-found variant needs >= 2 matching calls in "
            "distinct phases so the DESC ordering is observable"
        )


def _provision_salesforce_phases(
    ctx: RecipeContext, section: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    phases = section["phases"]
    state: dict[str, Any] | None = None
    merged_records: list[dict[str, Any]] = []
    refs: dict[str, str] = {}
    for phase_index, phase in enumerate(phases):
        if phase_index:
            time.sleep(CREATED_DATE_SPACING_SECONDS)
        phase_section: dict[str, Any] = {
            "strict_soql_conditions": True,
            "records": _replace_value(deepcopy(phase["records"]), refs),
        }
        if phase_index == 0:
            phase_section["schema"] = deepcopy(section["schema"])
        try:
            provision = ctx.tools.call(
                "harness.salesforce.seed_records", {"salesforce": phase_section}
            )
            if not provision.get("ok"):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} Salesforce phase-{phase_index} seed failed: {provision}"
                )
        except Exception:
            if state is not None:
                # A later phase failed after earlier phases committed live
                # records: remove them before failing so a rerun never sees
                # stale benchmark state (89731033 precedent).
                from ..salesforce_live_harness import OwnedSalesforce

                OwnedSalesforce(state).delete_owned()
            raise
        refs.update(_phase_ref_tokens(phase["records"], provision))
        phase_state = deepcopy(provision["state"])
        merged_records.extend(
            deepcopy(list(((provision.get("snapshot") or {}).get("salesforce") or {}).get("records") or []))
        )
        if state is None:
            state = phase_state
        else:
            state["owned_records"] = list(state.get("owned_records") or []) + list(
                phase_state.get("owned_records") or []
            )
            state["read_only_records"] = list(state.get("read_only_records") or []) + list(
                phase_state.get("read_only_records") or []
            )
            state["strict_soql_conditions"] = bool(
                state.get("strict_soql_conditions") or phase_state.get("strict_soql_conditions")
            )
            state["expand_relationships"] = bool(
                state.get("expand_relationships") or phase_state.get("expand_relationships")
            )
    assert state is not None  # phases is validated non-empty
    return state, {"salesforce": {"records": merged_records}}, refs


def _phase_ref_tokens(
    phase_records: list[dict[str, Any]], provision: dict[str, Any]
) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    live_ids = [
        str(record.get("id") or "")
        for record in salesforce_snapshot.get("records") or []
        if isinstance(record, dict) and record.get("id")
    ]
    seed_records = [record for record in phase_records if isinstance(record, dict)]
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


def _snapshot(ctx: RecipeContext, live: bool) -> dict[str, Any]:
    if live:
        return ctx.tools.call("harness.salesforce.snapshot", {})
    return {}


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
