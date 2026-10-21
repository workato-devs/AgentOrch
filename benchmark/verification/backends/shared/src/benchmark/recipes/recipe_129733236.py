from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_129733236
from .salesforce_recipe_utils import collect_actions, copy_expect, replace_tokens, run_salesforce_recipe, salesforce_refs, seed_salesforce_state


RECIPE_ID = "129733236"
SEED_TYPE = "genie_salesforce_account_detail_get_variant"
TRACK = "live_salesforce_genie_account_get"
TRIGGER_PROVIDER = "workato_genie"
TRIGGER_NAME = "start_workflow"
EXPECTED_ACTIONS = [
    ("salesforce", "get_custom_object"),
    ("workato_genie", "workflow_return_result"),
]
EXPECTED_RAW_TOOLS = ["salesforce.search_records", "workato_genie.workflow_return_result"]
ALLOWED_TOOLS = ["salesforce.search_records", "workato_genie.workflow_return_result"]


def validate_129733236(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    get_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if get_input.get("sobject_name") != "Account" or "accountId" not in str(get_input.get("id") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} Account get mapping changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_129733236(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_129733236(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    provision = seed_salesforce_state(RECIPE_ID, data, ctx)
    trigger = replace_tokens(trigger_input(ctx), salesforce_refs(provision))
    parameters = trigger.get("parameters") if isinstance(trigger.get("parameters"), dict) else None
    if not isinstance(parameters, dict) or not parameters.get("accountId"):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing parameters.accountId")
    out = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": copy_expect(data),
        "raw_validation": validation,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_129733236(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    return run_salesforce_recipe(
        recipe_id=RECIPE_ID,
        track=TRACK,
        raw=raw,
        seed=seed,
        ctx=ctx,
        validation=validate_129733236(raw),
        expected_raw_tools=EXPECTED_RAW_TOOLS,
        allowed_tools=ALLOWED_TOOLS,
        verifier=verify_129733236,
    )


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"number": a.get("number"), "provider": a.get("provider"), "name": a.get("name"), "as": a.get("as")} for a in actions]
