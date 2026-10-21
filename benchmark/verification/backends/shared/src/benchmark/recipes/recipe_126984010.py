from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..variant_input import trigger_input, variant_data
from ..verifier import verify_126984010
from .salesforce_recipe_utils import collect_actions, salesforce_refs, seed_salesforce_state
from .snowflake_live_recipe_utils import run_live_snowflake_recipe, seed_live_snowflake, snowflake_seed_base


RECIPE_ID = "126984010"
SEED_TYPE = "scheduled_live_snowflake_salesforce_success_owner_clear_variant"
TRACK = "live_snowflake_live_salesforce_update"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
EXPECTED_ACTIONS = [
    ("snowflake", "search_rows_sql"),
    ("salesforce", "composite_update_sobject"),
]
EXPECTED_RAW_TOOLS = ["snowflake.search_rows_sql", "salesforce.update_record"]
ALLOWED_TOOLS = ["snowflake.search_rows_sql", "salesforce.update_record"]


def validate_126984010(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    sql = str((actions[0].get("input") or {}).get("sql") or "")
    if "WORKATO_BUSINESS_SYSTEMS.SALESFORCE.ACCOUNT" not in sql or "Expansion_CSM__c" not in str(actions[1]):
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake/Salesforce mapping changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_126984010(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_126984010(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    salesforce_provision = seed_salesforce_state(RECIPE_ID, data, ctx)
    snowflake_provision = seed_live_snowflake(RECIPE_ID, data, ctx, salesforce_refs(salesforce_provision))
    trigger = trigger_input(ctx)
    return snowflake_seed_base(
        recipe_id=RECIPE_ID,
        seed_type=SEED_TYPE,
        track=TRACK,
        validation=validation,
        ctx=ctx,
        snowflake_state=snowflake_provision["state"],
        extra={
            "trigger": trigger,
            "project_properties": deepcopy(
                data.get("project_properties") or {}
            ),
            "salesforce_live": deepcopy(salesforce_provision["state"]),
            "salesforce_seed_snapshot": deepcopy(salesforce_provision.get("snapshot") or {}),
        },
    )


def run_126984010(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    return run_live_snowflake_recipe(
        recipe_id=RECIPE_ID,
        track=TRACK,
        raw=raw,
        seed=seed,
        ctx=ctx,
        validation=validate_126984010(raw),
        expected_raw_tools=EXPECTED_RAW_TOOLS,
        allowed_tools=ALLOWED_TOOLS,
        verifier=verify_126984010,
        include_salesforce=True,
    )


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"number": a.get("number"), "provider": a.get("provider"), "name": a.get("name"), "as": a.get("as")} for a in actions]
