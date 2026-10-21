from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_78751384


# Workato API-platform endpoint over live Salesforce: receive_request (the JSON
# request payload is never dereferenced) -> TRY { salesforce.search_sobjects_soql
# on pse__Time_Period__c with free-text SOQL where-clause "CreatedDate != null",
# field_list Name+Id, limit 2000 } -> IF list_size > 0 return_response 200
# {time_periods:[{id,name}]} -> ELSE return_response 204 (empty) -> CATCH (retry
# disabled) return_response 500 {message: <catch message>}.
#
# Live-org mapping (PSA stand-in object provisioned live 2026-07-06):
# pse__Time_Period__c -> physical custom object Time_Period__c via
# SALESFORCE_SOBJECT_MAP. CreatedDate is system-set on create, so in real
# Salesforce the where clause matches every existing row. The harness search
# only scans benchmark-owned records seeded for this run (deterministic against
# org leftovers); its SOQL matcher does not parse "!= null" conditions and
# falls back to term matching of the query term "createddate" against record
# field values, so the seeded Time Period names deliberately carry the
# "CreatedDate" token — live-faithful, because any existing record satisfies
# the real predicate.
RECIPE_ID = "78751384"
SEED_TYPE = "api_time_periods_search_response_variant"
TRACK = "live_salesforce_api_time_periods_response"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
SEARCH_AS = "9248345f"
SEARCH_SOBJECT = "pse__Time_Period__c"
SEARCH_QUERY = "CreatedDate != null"
SEARCH_FIELD_LIST = "Name\nId"
SEARCH_LIMIT = "2000"
RESPONSE_COLLECTION_KEY = "time_periods"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("salesforce", "search_sobjects_soql"),
    ("workato_api_platform", "return_response"),
    ("workato_api_platform", "return_response"),
    ("workato_api_platform", "return_response"),
]
EXPECTED_STATUS_CODES: list[str] = ["200", "204", "500"]
EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_api_platform.return_response",
]


def validate_78751384(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    search = actions[0]
    if str(search.get("as") or "") != SEARCH_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} search step id changed: {search.get('as')}")
    search_input = search.get("input") if isinstance(search.get("input"), dict) else {}
    if str(search_input.get("sobject_name") or "") != SEARCH_SOBJECT:
        raise RuntimeError(f"recipe {RECIPE_ID} search sobject changed: {search_input.get('sobject_name')}")
    if str(search_input.get("query") or "") != SEARCH_QUERY:
        raise RuntimeError(f"recipe {RECIPE_ID} SOQL query changed: {search_input.get('query')!r}")
    if str(search_input.get("field_list") or "") != SEARCH_FIELD_LIST:
        raise RuntimeError(f"recipe {RECIPE_ID} search field_list changed: {search_input.get('field_list')!r}")
    if str(search_input.get("limit") or "") != SEARCH_LIMIT:
        raise RuntimeError(f"recipe {RECIPE_ID} search limit changed: {search_input.get('limit')!r}")
    statuses = []
    for action in actions[1:]:
        action_input = action.get("input") if isinstance(action.get("input"), dict) else {}
        statuses.append(str(action_input.get("http_status_code") or ""))
    if statuses != EXPECTED_STATUS_CODES:
        raise RuntimeError(f"recipe {RECIPE_ID} return_response status codes changed: {statuses}")
    ok_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    ok_response = ok_input.get("response") if isinstance(ok_input.get("response"), dict) else {}
    if RESPONSE_COLLECTION_KEY not in ok_response:
        raise RuntimeError(f"recipe {RECIPE_ID} 200 response no longer maps {RESPONSE_COLLECTION_KEY}")
    error_input = actions[3].get("input") if isinstance(actions[3].get("input"), dict) else {}
    error_response = error_input.get("response") if isinstance(error_input.get("response"), dict) else {}
    if "message" not in error_response:
        raise RuntimeError(f"recipe {RECIPE_ID} 500 response no longer maps the catch message")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": [
            {
                "number": action.get("number"),
                "provider": action.get("provider"),
                "name": action.get("name"),
                "as": action.get("as"),
            }
            for action in actions
        ],
    }


def seed_78751384(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_78751384(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing required expect object")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    trigger = trigger_input(ctx)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(expect),
        "raw_validation": validation,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    salesforce_seed = seed_in.get("salesforce")
    if isinstance(salesforce_seed, dict):
        provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": salesforce_seed})
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
        out["salesforce_live"] = deepcopy(provision["state"])
        out["salesforce_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
    elif not isinstance(data.get("force_action_error"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant must seed a salesforce section (records may be an "
            "empty list) unless it forces the search action to fail"
        )
    return attach_variant(out, ctx)


def run_78751384(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_78751384(raw)
    initial_snapshot = _snapshot(ctx, seed)
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        # Cleanup runs even when replay crashes: leaked benchmark-owned live
        # records would poison later runs (benchmark cleanup policy cleanup
        # principle). On success the snapshot above is captured first.
        cleanup_response = (
            ctx.tools.call("harness.salesforce.cleanup", {})
            if isinstance(seed.get("salesforce_live"), dict)
            else {"ok": True, "leftovers": []}
        )
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
    result["verifier"] = verify_78751384(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    if isinstance(seed.get("salesforce_live"), dict):
        return dict(ctx.tools.call("harness.salesforce.snapshot", {}))
    return {}


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
