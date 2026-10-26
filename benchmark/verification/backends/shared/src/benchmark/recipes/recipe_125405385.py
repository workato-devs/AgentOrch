from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_125405385
from .salesforce_recipe_utils import (
    collect_actions,
    copy_expect,
    replace_tokens,
    run_salesforce_recipe,
    salesforce_refs,
    seed_salesforce_state,
)


RECIPE_ID = "125405385"
SEED_TYPE = "genie_salesforce_opportunity_wss_update_variant"
TRACK = "live_salesforce_genie_update"
TRIGGER_PROVIDER = "workato_genie"
TRIGGER_NAME = "start_workflow"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("salesforce", "update_sobject"),
    ("workato_genie", "workflow_return_result"),
]
EXPECTED_RAW_TOOLS = ["salesforce.update_record", "workato_genie.workflow_return_result"]
ALLOWED_TOOLS = ["salesforce.update_record", "workato_genie.workflow_return_result"]
REQUIRED_PARAMETERS = (
    "opportunity_id",
    "current_state",
    "quantified_negative_effects",
    "desired_state",
    "quantified_business_outcomes",
    "metrics",
    "solution_requirements",
    "how_workato_does_it_better",
)


def validate_125405385(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    update_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if str(update_input.get("sobject_name") or "") != "Opportunity":
        raise RuntimeError(f"recipe {RECIPE_ID} update sobject changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_125405385(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_125405385(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    provision = seed_salesforce_state(RECIPE_ID, data, ctx)
    trigger = replace_tokens(trigger_input(ctx), salesforce_refs(provision))
    parameters = trigger.get("parameters") if isinstance(trigger.get("parameters"), dict) else None
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing parameters object")
    for key in REQUIRED_PARAMETERS:
        if key not in parameters:
            raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter missing {key}")
    out = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": copy_expect(data),
        "raw_validation": validation,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "account_properties": deepcopy(data.get("account_properties") if isinstance(data.get("account_properties"), dict) else {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_125405385(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    return run_salesforce_recipe(
        recipe_id=RECIPE_ID,
        track=TRACK,
        raw=raw,
        seed=seed,
        ctx=ctx,
        validation=validate_125405385(raw),
        expected_raw_tools=EXPECTED_RAW_TOOLS,
        allowed_tools=ALLOWED_TOOLS,
        verifier=verify_125405385,
    )


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"number": a.get("number"), "provider": a.get("provider"), "name": a.get("name"), "as": a.get("as")} for a in actions]
