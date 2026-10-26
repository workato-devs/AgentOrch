from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_111146863


RECIPE_ID = '111146863'
SEED_TYPE = 'live_salesforce_live_slack_benchmark_variant'
TRACK = 'live_salesforce_live_slack'
TRIGGER_PROVIDER = 'salesforce'
TRIGGER_NAME = 'new_custom_object'
EXPECTED_ACTIONS: list[tuple[str, str]] = [('salesforce', 'search_sobjects_soql'),
 ('slack_bot', 'post_bot_message'),
 ('logger', 'log_message')]
EXPECTED_RAW_TOOLS: list[str] = ['salesforce.search_records', 'slack.post_message', 'workato_runtime.log_message']
ALLOWED_TOOLS: list[str] = ['salesforce.search_records', 'slack.post_message']


def validate_111146863(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
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


def seed_111146863(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_111146863(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    salesforce_seed = seed_in.get("salesforce")
    if not isinstance(salesforce_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires a salesforce seed object")
    provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": salesforce_seed})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    opportunity = _first_seed_record(provision, "Opportunity")
    trigger = _replace_tokens(
        trigger_input(ctx),
        {
            "$OPPORTUNITY_ID": str(opportunity.get("id") or opportunity.get("Id") or ""),
            "$OPPORTUNITY_NAME": str((opportunity.get("fields") or {}).get("Name") or ""),
        },
    )
    if not ((trigger.get("Parent") or {}).get("pse__Opportunity__c")):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger missing seeded opportunity id")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") or {}),
        "raw_validation": validation,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    for key in ("account_properties", "project_properties"):
        if isinstance(seed_in.get(key), dict):
            out[key] = deepcopy(seed_in[key])
    if isinstance(data.get("force_action_error"), dict):
        out["force_action_error"] = deepcopy(data["force_action_error"])
    return attach_variant(out, ctx)


def run_111146863(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_111146863(raw)
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
    finally:
        # Cleanup runs even when replay crashes: leaked benchmark-owned live
        # records would poison later runs (benchmark cleanup policy cleanup
        # principle).
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
            "cleanup_response": cleanup_response,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_111146863(result)
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


def _first_seed_record(provision: dict[str, Any], sobject: str) -> dict[str, Any]:
    records = (((provision.get("snapshot") or {}).get("salesforce") or {}).get("records") or [])
    for record in records:
        if isinstance(record, dict) and record.get("sobject") == sobject:
            return record
    raise RuntimeError(f"recipe {RECIPE_ID} did not seed a live {sobject} record")


def _replace_tokens(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_tokens(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_tokens(item, replacements) for item in value]
    if isinstance(value, str):
        out = value
        for token, replacement in replacements.items():
            out = out.replace(token, replacement)
        return out
    return value


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
