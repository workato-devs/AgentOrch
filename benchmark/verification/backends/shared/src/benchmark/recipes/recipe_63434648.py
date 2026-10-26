from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_63434648
from .salesforce_recipe_utils import (
    collect_actions,
    copy_expect,
    replace_tokens,
    run_salesforce_recipe,
    salesforce_refs,
    seed_salesforce_state,
)


RECIPE_ID = "63434648"
SEED_TYPE = "salesforce_opportunity_limit_override_slack_alert_variant"
TRACK = "live_salesforce_slack_limit_override_alert"
TRIGGER_PROVIDER = "salesforce"
TRIGGER_NAME = "new_custom_object"
TRIGGER_SOBJECT = "OpportunityFieldHistory"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("salesforce", "search_sobjects"),
    ("slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS = ["salesforce.search_records", "slack.post_message"]
ALLOWED_TOOLS = ["salesforce.search_records", "slack.post_message"]


def validate_63434648(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    raw_input = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    if raw_input.get("sobject_name") != TRIGGER_SOBJECT:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger object changed")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    search_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if search_input.get("sobject_name") != "Opportunity" or "OpportunityId" not in str(search_input):
        raise RuntimeError(f"recipe {RECIPE_ID} Opportunity search changed")
    slack_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    if "KLA Notification Channel" not in str(slack_input):
        raise RuntimeError(f"recipe {RECIPE_ID} Slack channel property changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_63434648(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_63434648(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    provision = seed_salesforce_state(RECIPE_ID, data, ctx)
    trigger = replace_tokens(trigger_input(ctx), salesforce_refs(provision))
    if not trigger.get("OpportunityId"):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing OpportunityId")
    account_properties = data.get("account_properties")
    if not isinstance(account_properties, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires account_properties")
    for key in ("Salesforce Base URL", "KLA Notification Channel"):
        if not account_properties.get(key):
            raise RuntimeError(f"recipe {RECIPE_ID} account_properties missing {key}")
    out = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": copy_expect(data),
        "account_properties": deepcopy(account_properties),
        "raw_validation": validation,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_63434648(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    if not ctx.env.slack_channel_override:
        raise RuntimeError(f"recipe {RECIPE_ID} requires SLACK_CHANNEL_OVERRIDE for the live Slack alert")
    return run_salesforce_recipe(
        recipe_id=RECIPE_ID,
        track=TRACK,
        raw=raw,
        seed=seed,
        ctx=ctx,
        validation=validate_63434648(raw),
        expected_raw_tools=EXPECTED_RAW_TOOLS,
        allowed_tools=ALLOWED_TOOLS,
        verifier=verify_63434648,
    )


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"number": action.get("number"), "provider": action.get("provider"), "name": action.get("name"), "as": action.get("as")} for action in actions]
