from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_128764529
from .salesforce_recipe_utils import collect_actions, copy_expect, replace_tokens, run_salesforce_recipe, salesforce_refs, seed_salesforce_state


RECIPE_ID = "128764529"
SEED_TYPE = "salesforce_campaign_member_slack_alert_variant"
TRACK = "live_salesforce_slack_alert"
TRIGGER_PROVIDER = "salesforce"
TRIGGER_NAME = "new_custom_object"
EXPECTED_ACTIONS = [
    ("salesforce", "search_sobjects"),
    ("salesforce", "search_sobjects"),
    ("slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS = ["salesforce.search_records", "salesforce.search_records", "slack.post_message"]
ALLOWED_TOOLS = ["salesforce.search_records", "slack.post_message"]


def validate_128764529(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    raw_filter = raw.get("filter") if isinstance(raw.get("filter"), dict) else {}
    if "701PV00002B2qEbYAJ" not in str(raw_filter):
        raise RuntimeError(f"recipe {RECIPE_ID} Campaign filter changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_128764529(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_128764529(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    provision = seed_salesforce_state(RECIPE_ID, data, ctx)
    trigger = replace_tokens(trigger_input(ctx), salesforce_refs(provision))
    if not str(trigger.get("CampaignId") or "") or "ContactId" not in trigger:
        # Both trigger-filter outcomes are benchmarked: CampaignId
        # 701PV00002B2qEbYAJ runs the lead-alert path, any other campaign id
        # is the verified zero-action trigger-filter-false path. Only a
        # missing/blank CampaignId or absent ContactId is invalid input.
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing CampaignId/ContactId")
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


def run_128764529(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    return run_salesforce_recipe(
        recipe_id=RECIPE_ID,
        track=TRACK,
        raw=raw,
        seed=seed,
        ctx=ctx,
        validation=validate_128764529(raw),
        expected_raw_tools=EXPECTED_RAW_TOOLS,
        allowed_tools=ALLOWED_TOOLS,
        verifier=verify_128764529,
    )


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"number": a.get("number"), "provider": a.get("provider"), "name": a.get("name"), "as": a.get("as")} for a in actions]
