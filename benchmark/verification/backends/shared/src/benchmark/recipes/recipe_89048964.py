from __future__ import annotations

from typing import Any

from ..context import RecipeContext
from ..variant_input import variant_data
from ..verifier import verify_89048964
from .salesforce_recipe_utils import collect_actions
from .snowflake_live_recipe_utils import run_live_snowflake_recipe, seed_live_snowflake, snowflake_seed_base


RECIPE_ID = "89048964"
SEED_TYPE = "clock_live_snowflake_rpa_queue_requeue_variant"
TRACK = "live_snowflake_update"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
SNOWFLAKE_TABLE = "RPA.QUEUE"
STALLED_WHERE = "TIMEDIFF(MINUTES, RAN_AT, CURRENT_TIMESTAMP) > 20 AND STATUS = 'In Progress'"
ERROR_WHERE = "STATUS = 'Error: RPA'"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("snowflake", "update_rows"),
    ("snowflake", "update_rows"),
]
EXPECTED_RAW_TOOLS: list[str] = ["snowflake.update_rows", "snowflake.update_rows"]
ALLOWED_TOOLS: list[str] = ["snowflake.update_rows"]


def validate_89048964(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    stalled_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if str(stalled_input.get("table") or "") != SNOWFLAKE_TABLE:
        raise RuntimeError(f"recipe {RECIPE_ID} stalled-update table changed")
    if str(stalled_input.get("where") or "") != STALLED_WHERE:
        raise RuntimeError(f"recipe {RECIPE_ID} stalled-update where clause changed")
    error_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    if str(error_input.get("table") or "") != SNOWFLAKE_TABLE:
        raise RuntimeError(f"recipe {RECIPE_ID} error-update table changed")
    if str(error_input.get("where") or "") != ERROR_WHERE:
        raise RuntimeError(f"recipe {RECIPE_ID} error-update where clause changed")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": _action_summary(actions),
    }


def seed_89048964(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_89048964(raw)
    data = variant_data(ctx)
    provision = seed_live_snowflake(RECIPE_ID, data, ctx)
    return snowflake_seed_base(
        recipe_id=RECIPE_ID,
        seed_type=SEED_TYPE,
        track=TRACK,
        validation=validation,
        ctx=ctx,
        snowflake_state=provision["state"],
    )


def run_89048964(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    return run_live_snowflake_recipe(
        recipe_id=RECIPE_ID,
        track=TRACK,
        raw=raw,
        seed=seed,
        ctx=ctx,
        validation=validate_89048964(raw),
        expected_raw_tools=EXPECTED_RAW_TOOLS,
        allowed_tools=ALLOWED_TOOLS,
        verifier=verify_89048964,
    )


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"number": a.get("number"), "provider": a.get("provider"), "name": a.get("name"), "as": a.get("as")}
        for a in actions
    ]
