from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_124269371
from .salesforce_recipe_utils import (
    collect_actions,
    copy_expect,
    replace_tokens,
    run_salesforce_recipe,
    salesforce_refs,
    seed_salesforce_state,
)


RECIPE_ID = "124269371"
SEED_TYPE = "slack_dynamic_menu_live_salesforce_direct_account_lookup"
TRACK = "live_salesforce_slack_dynamic_menu"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "dynamic_menu"
EXPECTED_ACTIONS = [
    ("salesforce", "search_sobjects_soql"),
    ("slack_bot", "generate_menu_options"),
]
EXPECTED_RAW_TOOLS = [
    "salesforce.search_records",
    "slack_bot.generate_menu_options",
]
ALLOWED_TOOLS = [
    "salesforce.search_records",
    "slack_bot.generate_menu_options",
]


def validate_124269371(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    search_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    query = str(search_input.get("query") or "")
    lowered = query.lower()
    if "name like" not in lowered:
        raise RuntimeError(f"recipe {RECIPE_ID} Account typeahead query changed")
    if "current_arr__c" not in lowered or "> 0" not in lowered:
        raise RuntimeError(f"recipe {RECIPE_ID} Account ARR filter changed")
    if str(search_input.get("sobject_name") or "") != "Account":
        raise RuntimeError(f"recipe {RECIPE_ID} search object changed")
    menu_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    options = str(menu_input.get("options") or "")
    for token in ("Name", "Post_Sales_CS_Pod__r", "Owner", "Id"):
        if token not in options:
            raise RuntimeError(f"recipe {RECIPE_ID} menu option mapping changed (missing {token})")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_124269371(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_124269371(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    provision = seed_salesforce_state(RECIPE_ID, data, ctx)
    refs = salesforce_refs(provision)
    trigger = replace_tokens(trigger_input(ctx), refs)
    if (trigger.get("typeahead") or {}).get("value") is None:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger missing typeahead.value")
    out = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": replace_tokens(copy_expect(data), refs),
        "raw_validation": validation,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_124269371(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_124269371(raw)
    return run_salesforce_recipe(
        recipe_id=RECIPE_ID,
        track=TRACK,
        raw=raw,
        seed=seed,
        ctx=ctx,
        validation=validation,
        expected_raw_tools=EXPECTED_RAW_TOOLS,
        allowed_tools=ALLOWED_TOOLS,
        verifier=verify_124269371,
    )


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"number": action.get("number"), "provider": action.get("provider"), "name": action.get("name"), "as": action.get("as")} for action in actions]
