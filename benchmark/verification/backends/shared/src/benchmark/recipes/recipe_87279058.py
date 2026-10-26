from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_87279058


RECIPE_ID = "87279058"
SEED_TYPE = "answer_benchmark_variant"
TRACK = "benchmark_answer"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "dynamic_menu"
TRIGGER_AS = "b3cc7c5d"
SEARCH_AS = "c5308321"
MENU_AS = "53a73e47"
FOREIGN_RT_ID = "012o0000000tYvxAAE"
EMPTY_REASONS = {"foreign_record_type", "no_name_match"}
ACCOUNT_READ_FIELDS = ["RecordTypeId"]
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_TYPEAHEAD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 .\-]*")


_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "b3cc7c5d",
  "provider": "slack_bot",
  "name": "dynamic_menu",
  "skip": false,
  "input": {
   "dynamic_menu_name": "Find Partner Account",
   "parameters": "[]"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "c5308321",
  "provider": "salesforce",
  "name": "search_sobjects_soql",
  "skip": false,
  "input": {
   "field_list": "Name\nRecordTypeId\nPartner_Status__c\nPartner_Manager_Name__c\ncam_email__c\nPartner_type__c\nFocus_Partner__c\nRecordType$Record Type ID.Name\nId",
   "limit": "150",
   "query": "NAME LIKE '%#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"b3cc7c5d\",\"path\":[\"typeahead\", \"value\"]}')}%' AND RecordTypeId = '012o0000000tYvxAAE'",
   "sobject_name": "Account",
   "table_list": "RecordType"
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "53a73e47",
  "provider": "slack_bot",
  "name": "generate_menu_options",
  "skip": false,
  "input": {
   "options": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"c5308321\",\"path\":[\"Account\"]}')}",
    "label": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"c5308321\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"Name\"]}')}",
    "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"c5308321\",\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}"
   }
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.search_records",
    "slack_bot.generate_menu_options",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "slack_bot.generate_menu_options",
]
EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "menu_options",
    "empty_reason",
    "decoy_accounts",
)


def _resolved_query(typeahead: str) -> str:
    return f"NAME LIKE '%{typeahead}%' AND RecordTypeId = '{FOREIGN_RT_ID}'"


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


def validate_87279058(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_87279058(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_87279058(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    typeahead = _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"salesforce"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    seeded_names = _require_salesforce_section(seed_in.get("salesforce"))
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole "
            "run instead of exercising a recipe branch"
        )
    expect = data.get("expect")
    _require_expect_shape(expect, typeahead, seeded_names)
    _require_no_tokens(trigger)
    _require_no_tokens(expect)
    provision = ctx.tools.call(
        "harness.salesforce.seed_records", {"salesforce": deepcopy(seed_in["salesforce"])}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": deepcopy(expect),
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_87279058(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_87279058(raw)
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    if not seed["salesforce_live"].get("strict_soql_conditions"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires strict_soql_conditions in the live state "
            "(the LIKE + RecordTypeId equality arms are strict-only; without the flag "
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
        # Required cleanup: the decoy Account seeds must not leak into later
        # runs (the recipe itself only reads).
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
    result["verifier"] = verify_87279058(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> str:
    if set(trigger) != {"typeahead"} or not isinstance(trigger.get("typeahead"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'typeahead': {{'value': ...}}}} "
            "(the menu declares zero parameters; only typeahead.value is dereferenced)"
        )
    typeahead_obj = trigger["typeahead"]
    if set(typeahead_obj) != {"value"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger typeahead must carry exactly 'value': {typeahead_obj!r}"
        )
    typeahead = typeahead_obj.get("value")
    if not isinstance(typeahead, str) or not _TYPEAHEAD_RE.fullmatch(typeahead):
        raise RuntimeError(
            f"recipe {RECIPE_ID} typeahead.value must be a non-empty string of "
            "[A-Za-z0-9 .-] (no SOQL quotes or LIKE wildcards, so the resolved-query "
            f"pin and the substring attestation are exact): {typeahead!r}"
        )
    return typeahead


def _require_salesforce_section(section: Any) -> list[str]:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce")
    if sorted(section) != ["records", "strict_soql_conditions"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce must be exactly "
            "{'strict_soql_conditions': true, 'records': [...]}"
        )
    if section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true"
        )
    records = section.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.records must be a non-empty list "
            "(zero-match honesty: every variant seeds at least one decoy Account)"
        )
    names: list[str] = []
    for record in records:
        if not isinstance(record, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} seeded record must be an object: {record}")
        if str(record.get("sobject") or "") != "Account":
            raise RuntimeError(
                f"recipe {RECIPE_ID} seeded records must all be Account decoys: {record}"
            )
        if not str(record.get("ref") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded Salesforce record needs a 'ref': {record}"
            )
        fields = record.get("fields")
        if not isinstance(fields, dict) or set(fields) != {"Name"} or not str(fields.get("Name") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} Account decoys carry exactly a non-empty Name: {record}"
            )
        if record.get("read_fields") != ACCOUNT_READ_FIELDS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} every decoy Account must declare read_fields "
                f"{ACCOUNT_READ_FIELDS} so the strict WHERE and the snapshot evaluate the "
                f"REAL live RecordTypeId read-back: {record}"
            )
        name = str(fields["Name"])
        if name in names:
            raise RuntimeError(
                f"recipe {RECIPE_ID} decoy Account Names must be unique (the attestation "
                f"matches decoys by Name): {name!r}"
            )
        names.append(name)
    return names


def _require_expect_shape(expect: Any, typeahead: str, seeded_names: list[str]) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(set(expect) - set(EXPECT_KEYS))
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has unexpected keys: {unknown}")
    if expect.get("executed_action_count") != 2:
        raise RuntimeError(f"recipe {RECIPE_ID} the linear body always executes both actions")
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
    if not isinstance(args, dict) or args.get("sobject") != "Account" or args.get("limit") != "150":
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0].args_contains must pin sobject "
            f"'Account' and limit '150': {args!r}"
        )
    if args.get("query") != _resolved_query(typeahead):
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0] must pin the resolved SOQL verbatim "
            f"(typeahead interpolated between LIKE quotes + the foreign RT equality): "
            f"expected {_resolved_query(typeahead)!r}, got {args.get('query')!r}"
        )
    if search_item.get("result_count") != 0:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0].result_count must be 0: the foreign "
            "RecordTypeId equality never matches a live record (dead query)"
        )
    menu_item = tool_expectations[1]
    if not isinstance(menu_item, dict) or menu_item.get("tool") != "slack_bot.generate_menu_options":
        raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[1] must pin the menu options step")
    if menu_item.get("args_contains") != {"options": []}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[1].args_contains must pin options [] "
            "exactly (the ____source list is always empty)"
        )
    if menu_item.get("result_count") != 0:
        raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[1].result_count must be 0")
    if expect.get("menu_options") != []:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.menu_options must be exactly [] -- every reachable "
            "path renders an empty menu"
        )
    if expect.get("empty_reason") not in EMPTY_REASONS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.empty_reason must be one of {sorted(EMPTY_REASONS)}"
        )
    decoys = expect.get("decoy_accounts")
    if not isinstance(decoys, list) or not decoys:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.decoy_accounts must pin every seeded decoy Account "
            "(dead-branch attestation for the verifier)"
        )
    decoy_names: list[str] = []
    any_name_match = False
    for decoy in decoys:
        if not isinstance(decoy, dict) or set(decoy) != {"Name", "name_matches_typeahead"}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} each decoy_accounts entry must be "
                "{'Name': <seeded name>, 'name_matches_typeahead': <bool>}: "
                f"{decoy!r}"
            )
        name = str(decoy.get("Name") or "")
        declared = decoy.get("name_matches_typeahead")
        if not isinstance(declared, bool):
            raise RuntimeError(
                f"recipe {RECIPE_ID} decoy name_matches_typeahead must be a bool: {decoy!r}"
            )
        actual_match = typeahead.lower() in name.lower()
        if declared != actual_match:
            raise RuntimeError(
                f"recipe {RECIPE_ID} decoy {name!r} mis-declares the LIKE arm: "
                f"'%{typeahead}%' containment is {actual_match}, declared {declared}"
            )
        any_name_match = any_name_match or actual_match
        decoy_names.append(name)
    if sorted(decoy_names) != sorted(seeded_names):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.decoy_accounts must pin EXACTLY the seeded Account "
            f"Names: seeded {sorted(seeded_names)}, pinned {sorted(decoy_names)}"
        )
    computed_reason = "foreign_record_type" if any_name_match else "no_name_match"
    if expect["empty_reason"] != computed_reason:
        raise RuntimeError(
            f"recipe {RECIPE_ID} empty_reason must attribute the empty result honestly: "
            "'foreign_record_type' iff at least one decoy passes the LIKE arm (leaving "
            "the RT equality as the sole excluder), 'no_name_match' iff none does: "
            f"declared {expect['empty_reason']!r}, computed {computed_reason!r}"
        )


def _require_no_tokens(value: Any) -> None:
    leftover = _TOKEN_RE.findall(json.dumps(value))
    if leftover:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger/expect must not carry $<REF> tokens (no "
            f"run-generated id ever renders in this recipe): {sorted(set(leftover))}"
        )


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
