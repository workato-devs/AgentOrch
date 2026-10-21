from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_88707765


RECIPE_ID = "88707765"
SEED_TYPE = "api_platform_campaign_activity_batch_variant"
TRACK = "live_salesforce_campaign_activity_batch_api"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "5d8cbd3f"
# API endpoint: request {Input[] of {unqualified_reason, campaign_activity_id}};
# JSON response {status, sucess_records[], failed_records[]} (the
# "sucess_records" typo is verbatim in the raw recipe and kept everywhere).
#
#   TRY (2):
#     workato_variable.declare_list 'Success Records' (3, fb87693f) and
#     'Failed Records' (4, 92de3914).
#     IF (5) request.Input size > 10:
#       FOREACH Input (6, 609a8aab, simple):
#         TRY (7): salesforce.update_sobject Campaign_Activity__c
#           {id: item.campaign_activity_id, Unqualified_Reason__c:
#           item.unqualified_reason} (8, 1d614d89) -> insert_to_list Success
#           (9, 09ad599c, results "Success").
#         CATCH (10, 8e2e16ca, max_retry 0): insert_to_list Failed
#           (11, 9d314b1d, results "Failed.\nError Message:\n<catch message>")
#           -> the loop continues with the next item.
#     ELSE (12):
#       FOREACH Input (13, 3cab382e, repeat_mode=batch, batch_size 20; ZERO
#         iterations on an empty Input):
#         salesforce.composite_update_sobject (14, fa2c6ecd, allOrNone=false)
#           records ____source = the batch pill.
#         FOREACH successRecords (15, 28037b9f) -> insert Success (16, 47b1e527).
#         FOREACH failedRecords (17, 209619fe) -> insert Failed (18, cbc67c9e;
#           raw-recipe quirk: the "error message" is the Id pill again).
#     workato_api_platform.return_response (19, 69f53081) 200
#       {status: "Success", sucess_records <- Success list,
#        failed_records <- Failed list} - TERMINAL.
#   CATCH (20, f5053b8f, max_retry 0): return_response (21, 22787640) 200
#     {status: "Failed.\nError message: <catch message>",
#      sucess_records <- Success list} - the API answers 200 even on failure.
#
# Live backend: Salesforce custom object Campaign_Activity__c with custom field
# Unqualified_Reason__c (deployed; the seed schema section re-ensures the field
# + FLS on every run). Workato-internal (deterministic mock): variable lists,
# API-platform response.
#
# seed.composite_update_extended_output is set unconditionally by the seeder:
# Workato's composite update always exposes successRecords/failedRecords, so
# the faithful result shape for THIS recipe requires the opt-in executor flag.
# Engine fix 3b7736da (2026-07-07): under that flag the success/failed items
# ECHO the input record's fields ({Id, Unqualified_Reason__c, success} /
# +errors[]), and allOrNone=false collects per-record failures (a bad record
# fails only its own slot; the composite trace row then reports ok=false,
# which verify_88707765 admits ONLY via the explicit
# expect.composite_failed_count opt-in).
#
# Raw-recipe quirks pinned by the <=10 variants:
# - the response's top-level status stays the literal "Success" even when
#   failed_records is non-empty (only the outer catch changes it);
# - the failedRecords insert (step 18) builds its results text as
#   "Failed\nError Mesage:\n<Id>" - sic: misspelled "Mesage" and the Id pill
#   reused as the error message, so the response's failed row status carries
#   the record id, not the Salesforce error.

EXPECTED_ACTIONS: list[tuple[int, str, str, str]] = [
    (3, 'fb87693f', 'workato_variable', 'declare_list'),
    (4, '92de3914', 'workato_variable', 'declare_list'),
    (8, '1d614d89', 'salesforce', 'update_sobject'),
    (9, '09ad599c', 'workato_variable', 'insert_to_list'),
    (11, '9d314b1d', 'workato_variable', 'insert_to_list'),
    (14, 'fa2c6ecd', 'salesforce', 'composite_update_sobject'),
    (16, '47b1e527', 'workato_variable', 'insert_to_list'),
    (18, 'cbc67c9e', 'workato_variable', 'insert_to_list'),
    (19, '69f53081', 'workato_api_platform', 'return_response'),
    (21, '22787640', 'workato_api_platform', 'return_response'),
]
ACTION_INPUTS: dict[str, dict[str, Any]] = {
    'fb87693f': {'list_item_schema_json': '[{"control_type":"text","label":"Campaign activity '
                              'ID","name":"campaign_activity_id","type":"string","optional":true},{"control_type":"text","label":"Unqualified '
                              'reason","name":"unqualified_reason","type":"string","optional":true},{"control_type":"text","label":"Results","name":"results","type":"string","optional":true}]',
     'name': 'Success Records'},
    '92de3914': {'list_item_schema_json': '[{"control_type":"text","label":"Campaign activity '
                              'ID","name":"campaign_activity_id","type":"string","optional":true},{"control_type":"text","label":"Unqualified '
                              'reason","name":"unqualified_reason","type":"string","optional":true},{"control_type":"text","label":"Results","name":"results","type":"string","optional":true}]',
     'name': 'Failed Records'},
    '1d614d89': {'Unqualified_Reason__c': '#{_dp(\'{"pill_type":"output","provider":"foreach","line":"609a8aab","path":["unqualified_reason"]}\')}',
     'id': '#{_dp(\'{"pill_type":"output","provider":"foreach","line":"609a8aab","path":["campaign_activity_id"]}\')}',
     'sobject_name': 'Campaign_Activity__c'},
    '09ad599c': {'list_item': {'campaign_activity_id': '#{_dp(\'{"pill_type":"output","provider":"foreach","line":"609a8aab","path":["campaign_activity_id"]}\')}',
                   'results': 'Success',
                   'unqualified_reason': '#{_dp(\'{"pill_type":"output","provider":"foreach","line":"609a8aab","path":["unqualified_reason"]}\')}'},
     'location': 'end',
     'name': '3043a813-4162-4bc8-938a-8bde687fd6f6:fb87693f'},
    '9d314b1d': {'list_item': {'campaign_activity_id': '#{_dp(\'{"pill_type":"output","provider":"foreach","line":"609a8aab","path":["campaign_activity_id"]}\')}',
                   'results': 'Failed.\n'
                              'Error Message:\n'
                              '#{_dp(\'{"pill_type":"output","provider":"catch","line":"8e2e16ca","path":["message"]}\')}',
                   'unqualified_reason': '#{_dp(\'{"pill_type":"output","provider":"foreach","line":"609a8aab","path":["unqualified_reason"]}\')}'},
     'location': 'end',
     'name': '13e9c50a-47ef-4479-819e-f249e753800e:92de3914'},
    'fa2c6ecd': {'advanced_configuration': {'allOrNone': 'false'},
     'batch_size': '20',
     'records': {'Id': '#{_dp(\'{"pill_type":"output","provider":"foreach","line":"3cab382e","path":["batch", '
                       '{"path_element_type": "current_item"}, "campaign_activity_id"]}\')}',
                 'Unqualified_Reason__c': '#{_dp(\'{"pill_type":"output","provider":"foreach","line":"3cab382e","path":["batch", '
                                          '{"path_element_type": "current_item"}, '
                                          '"unqualified_reason"]}\')}',
                 '____source': '#{_dp(\'{"pill_type":"output","provider":"foreach","line":"3cab382e","path":["batch"]}\')}',
                 'attributes': {'Campaign_Activity__c': 'Campaign_Activity__c'}},
     'sobject_name': 'Campaign_Activity__c'},
    '47b1e527': {'list_item': {'campaign_activity_id': '#{_dp(\'{"pill_type":"output","provider":"foreach","line":"28037b9f","path":["Id"]}\')}',
                   'results': 'Success',
                   'unqualified_reason': '#{_dp(\'{"pill_type":"output","provider":"foreach","line":"28037b9f","path":["Unqualified_Reason__c"]}\')}'},
     'location': 'end',
     'name': '3043a813-4162-4bc8-938a-8bde687fd6f6:fb87693f'},
    'cbc67c9e': {'list_item': {'campaign_activity_id': '#{_dp(\'{"pill_type":"output","provider":"foreach","line":"209619fe","path":["Id"]}\')}',
                   'results': 'Failed\n'
                              'Error Mesage:\n'
                              '#{_dp(\'{"pill_type":"output","provider":"foreach","line":"209619fe","path":["Id"]}\')}',
                   'unqualified_reason': '#{_dp(\'{"pill_type":"output","provider":"foreach","line":"209619fe","path":["Unqualified_Reason__c"]}\')}'},
     'location': 'end',
     'name': '13e9c50a-47ef-4479-819e-f249e753800e:92de3914'},
    '69f53081': {'http_status_code': '200',
     'response': {'failed_records': {'____source': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"92de3914","path":["list_items"]}\')}',
                                     'campaign_activity_id': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"92de3914","path":["list_items", '
                                                             '{"path_element_type": '
                                                             '"current_item"}, '
                                                             '"campaign_activity_id"]}\')}',
                                     'status': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"92de3914","path":["list_items", '
                                               '{"path_element_type": "current_item"}, '
                                               '"results"]}\')}',
                                     'unqualified_reason': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"92de3914","path":["list_items", '
                                                           '{"path_element_type": "current_item"}, '
                                                           '"unqualified_reason"]}\')}'},
                  'status': 'Success',
                  'sucess_records': {'____source': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"fb87693f","path":["list_items"]}\')}',
                                     'campaign_activity_id': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"fb87693f","path":["list_items", '
                                                             '{"path_element_type": '
                                                             '"current_item"}, '
                                                             '"campaign_activity_id"]}\')}',
                                     'status': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"fb87693f","path":["list_items", '
                                               '{"path_element_type": "current_item"}, '
                                               '"results"]}\')}',
                                     'unqualified_reason': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"fb87693f","path":["list_items", '
                                                           '{"path_element_type": "current_item"}, '
                                                           '"unqualified_reason"]}\')}'}}},
    '22787640': {'http_status_code': '200',
     'response': {'status': 'Failed.\n'
                            'Error message: '
                            '#{_dp(\'{"pill_type":"output","provider":"catch","line":"f5053b8f","path":["message"]}\')}',
                  'sucess_records': {'____source': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"fb87693f","path":["list_items"]}\')}',
                                     'campaign_activity_id': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"fb87693f","path":["list_items", '
                                                             '{"path_element_type": '
                                                             '"current_item"}, '
                                                             '"campaign_activity_id"]}\')}',
                                     'status': 'Success',
                                     'unqualified_reason': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"fb87693f","path":["list_items", '
                                                           '{"path_element_type": "current_item"}, '
                                                           '"unqualified_reason"]}\')}'}}},
}
IF_CONDITIONS: dict[int, dict[str, Any]] = {
    5: {'conditions': [{'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"5d8cbd3f","path":["request", '
                            '"Input", {"path_element_type": "size"}]}\')}',
                     'operand': 'greater_than',
                     'rhs': '10'}],
     'operand': 'and',
     'type': 'compound'},
}
FOREACH_NODES: dict[int, dict[str, Any]] = {
    6: {'as': '609a8aab', 'repeat_mode': 'simple', 'source': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"5d8cbd3f","path":["request", "Input"]}\')}'},
    13: {'as': '3cab382e', 'repeat_mode': 'batch', 'source': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"5d8cbd3f","path":["request", "Input"]}\')}'},
    15: {'as': '28037b9f', 'repeat_mode': 'simple', 'source': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"fa2c6ecd","path":["successRecords"]}\')}'},
    17: {'as': '209619fe', 'repeat_mode': 'simple', 'source': '#{_dp(\'{"pill_type":"output","provider":"salesforce","line":"fa2c6ecd","path":["failedRecords"]}\')}'},
}
TRY_NUMBERS: list[int] = [2, 7]
ELSE_NUMBERS: list[int] = [12]
CATCH_NODES: list[tuple[int, str, dict[str, Any]]] = [(10, '8e2e16ca', {'max_retry_count': '0', 'retry_interval': '2'}), (20, 'f5053b8f', {'max_retry_count': '0', 'retry_interval': '2'})]
TRIGGER_INPUT_CFG: dict[str, Any] = {'request': {'content_type': 'json',
             'schema': '[{"name":"Input","type":"array","optional":true,"properties":[{"name":"unqualified_reason","type":"string","optional":true,"control_type":"text"},{"name":"campaign_activity_id","type":"string","optional":true,"control_type":"text"}]}]'},
 'response': {'content_type': 'json',
              'responses': [{'body_schema': '[{"control_type":"text","label":"Status","name":"status","type":"string","optional":true},{"name":"sucess_records","type":"array","of":"object","label":"Sucess '
                                            'records","optional":true,"properties":[{"control_type":"text","label":"Campaign '
                                            'activity '
                                            'ID","name":"campaign_activity_id","type":"string","optional":true},{"control_type":"text","label":"Unqualified '
                                            'Reason","name":"unqualified_reason","type":"string","optional":true},{"control_type":"text","label":"Status","name":"status","type":"string","optional":true}]},{"name":"failed_records","type":"array","of":"object","label":"Failed '
                                            'records","optional":true,"properties":[{"control_type":"text","label":"Campaign '
                                            'activity '
                                            'ID","name":"campaign_activity_id","type":"string","optional":true},{"control_type":"text","label":"Unqualified '
                                            'Reason","name":"unqualified_reason","type":"string","optional":true},{"control_type":"text","label":"Status","name":"status","type":"string","optional":true}]}]',
                             'http_status_code': '200',
                             'name': 'Result'}]}}

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_list",
    "salesforce.update_record",
    "workato_runtime.insert_to_list",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.update_record",
    "workato_api_platform.return_response",
]
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")


def validate_88707765(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed")
    if raw.get("input") != TRIGGER_INPUT_CFG:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger configuration changed: {raw.get('input')!r}")
    actions = _collect_actions(raw)
    actual = [
        (a.get("number"), str(a.get("as")), str(a.get("provider")), str(a.get("name")))
        for a in actions
    ]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    for action in actions:
        step_as = str(action.get("as"))
        if action.get("input") != ACTION_INPUTS[step_as]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} action {step_as} input changed: {action.get('input')!r}"
            )
    control = _collect_control_nodes(raw)
    if_numbers = sorted(number for keyword, number in control if keyword == "if")
    if if_numbers != sorted(IF_CONDITIONS):
        raise RuntimeError(f"recipe {RECIPE_ID} if-node numbers changed: {if_numbers}")
    for number, conditions in IF_CONDITIONS.items():
        if control[("if", number)].get("input") != conditions:
            raise RuntimeError(f"recipe {RECIPE_ID} if {number} conditions changed")
    foreach_numbers = sorted(number for keyword, number in control if keyword == "foreach")
    if foreach_numbers != sorted(FOREACH_NODES):
        raise RuntimeError(f"recipe {RECIPE_ID} foreach numbers changed: {foreach_numbers}")
    for number, spec in FOREACH_NODES.items():
        node = control[("foreach", number)]
        node_input = node.get("input") if isinstance(node.get("input"), dict) else {}
        if (
            str(node.get("as") or "") != spec["as"]
            or node.get("repeat_mode") != spec["repeat_mode"]
            or node_input.get("source") != spec["source"]
        ):
            raise RuntimeError(f"recipe {RECIPE_ID} foreach {number} changed")
    if FOREACH_NODES[13]["repeat_mode"] != "batch":
        raise RuntimeError(f"recipe {RECIPE_ID} batch foreach lost its repeat_mode")
    try_numbers = sorted(number for keyword, number in control if keyword == "try")
    if try_numbers != TRY_NUMBERS:
        raise RuntimeError(f"recipe {RECIPE_ID} try numbers changed: {try_numbers}")
    else_numbers = sorted(number for keyword, number in control if keyword == "else")
    if else_numbers != ELSE_NUMBERS:
        raise RuntimeError(f"recipe {RECIPE_ID} else numbers changed: {else_numbers}")
    catch_actual = [
        (number, str(control[("catch", number)].get("as") or ""), control[("catch", number)].get("input"))
        for keyword, number in sorted(control)
        if keyword == "catch"
    ]
    if catch_actual != CATCH_NODES:
        raise RuntimeError(f"recipe {RECIPE_ID} catch nodes changed: {catch_actual!r}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": [
            {"number": a.get("number"), "provider": a.get("provider"), "name": a.get("name"), "as": a.get("as")}
            for a in actions
        ],
    }


def seed_88707765(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88707765(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    request = trigger.get("request")
    if not isinstance(request, dict) or not isinstance(request.get("Input"), list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger input must carry request.Input as an explicit list "
            "(empty list for the zero-batch branch)"
        )
    for item in request["Input"]:
        if not isinstance(item, dict) or "campaign_activity_id" not in item or "unqualified_reason" not in item:
            raise RuntimeError(
                f"recipe {RECIPE_ID} every request.Input item needs explicit "
                f"campaign_activity_id and unqualified_reason: {item!r}"
            )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if not isinstance(data.get("expect"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track"),
        "raw_validation": validation,
        # Workato's composite update always exposes successRecords/failedRecords;
        # this recipe's size<=10 branch dereferences them, so the faithful
        # executor shape is opted in for every variant.
        "composite_update_extended_output": True,
    }
    refs: dict[str, str] = {}
    if "salesforce" in seed_in:
        if not isinstance(seed_in.get("salesforce"), dict):
            raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce must be an object")
        provision = ctx.tools.call(
            "harness.salesforce.seed_records", {"salesforce": deepcopy(seed_in["salesforce"])}
        )
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
        out["salesforce_live"] = deepcopy(provision["state"])
        out["salesforce_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
        refs = _salesforce_ref_tokens(seed_in["salesforce"], provision)
        out["salesforce_ref_tokens"] = dict(refs)
    out["trigger"] = _replace_value(trigger, refs)
    _require_resolved(out["trigger"], "trigger")
    out["expect"] = _replace_value(deepcopy(data["expect"]), refs)
    _require_resolved(out["expect"], "expect")
    for key, value in seed_in.items():
        if isinstance(value, dict):
            out[str(key)] = deepcopy(value)
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    for key in ("force_action_error", "job_context"):
        if isinstance(data.get(key), dict):
            out[key] = deepcopy(data[key])
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_88707765(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88707765(raw)
    if seed.get("composite_update_extended_output") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must carry composite_update_extended_output: true "
            "(faithful composite result shape)"
        )
    initial_snapshot = _snapshot(ctx, seed)
    cleanup_response: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        if isinstance(seed.get("salesforce_live"), dict):
            cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "cleanup_response": cleanup_response,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_88707765(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


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


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _collect_control_nodes(raw: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    control: dict[tuple[str, int], dict[str, Any]] = {}

    def walk(node: dict[str, Any]) -> None:
        for child in node.get("block") or []:
            if not isinstance(child, dict):
                continue
            keyword = str(child.get("keyword") or "")
            if keyword in {"if", "stop", "foreach", "catch", "try", "else"}:
                control[(keyword, int(child.get("number") or 0))] = child
            walk(child)

    walk(raw)
    return control


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("salesforce_live"), dict):
        out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
