from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..variant_input import trigger_input, variant_data
from ..verifier import verify_127614095
from .salesforce_recipe_utils import collect_actions
from .snowflake_live_recipe_utils import run_live_snowflake_recipe, seed_live_snowflake, seed_workato_db_section, snowflake_seed_base


RECIPE_ID = "127614095"
SEED_TYPE = "genie_live_snowflake_account_search_log_variant"
TRACK = "live_snowflake_workato_db_genie"
TRIGGER_PROVIDER = "workato_genie"
TRIGGER_NAME = "start_workflow"
TABLE_ID = "38746"
EXPECTED_ACTIONS = [
    ("snowflake", "search_rows"),
    ("workato_db_table", "add_record"),
    ("workato_genie", "workflow_return_result"),
]
EXPECTED_RAW_TOOLS = ["snowflake.search_rows", "workato_db_table.add_record", "workato_genie.workflow_return_result"]
ALLOWED_TOOLS = ["snowflake.search_rows", "workato_db_table.add_record", "workato_genie.workflow_return_result"]


def validate_127614095(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    if str((actions[1].get("input") or {}).get("table_id") or "") != TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} Workato DB table id changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_127614095(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_127614095(raw)
    data = variant_data(ctx)
    provision = seed_live_snowflake(RECIPE_ID, data, ctx)
    extra: dict[str, Any] = {
        "trigger": trigger_input(ctx),
        "workato_db_table": seed_workato_db_section(RECIPE_ID, data),
    }
    if isinstance(data.get("job_context"), dict):
        extra["job_context"] = deepcopy(data["job_context"])
    return snowflake_seed_base(
        recipe_id=RECIPE_ID,
        seed_type=SEED_TYPE,
        track=TRACK,
        validation=validation,
        ctx=ctx,
        snowflake_state=provision["state"],
        extra=extra,
    )


def run_127614095(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    return run_live_snowflake_recipe(
        recipe_id=RECIPE_ID,
        track=TRACK,
        raw=raw,
        seed=seed,
        ctx=ctx,
        validation=validate_127614095(raw),
        expected_raw_tools=EXPECTED_RAW_TOOLS,
        allowed_tools=ALLOWED_TOOLS,
        verifier=verify_127614095,
        include_workato_db=True,
    )


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"number": a.get("number"), "provider": a.get("provider"), "name": a.get("name"), "as": a.get("as")} for a in actions]
