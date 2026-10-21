from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..variant_input import variant_data, trigger_input
from ..verifier import verify_59799030
from .snowflake_live_recipe_utils import (
    run_live_snowflake_recipe,
    seed_live_snowflake,
    seed_workato_db_section,
    snowflake_seed_base,
)


RECIPE_ID = '59799030'
SEED_TYPE = 'final_state_benchmark_variant'
TRACK = 'benchmark_final_state'
TRIGGER_PROVIDER = 'clock'
TRIGGER_NAME = 'scheduled_event'
SNOWFLAKE_TABLE = 'NETSUITE.PAYMENT_TERM'
TABLE_ID = '1677'
# The raw upsert's primary_field_id is anonymized (<anon>...</anon>); the raw
# executor resolves it from dynamicPickListSelection.primary_field_id
# ("Internal ID") against the extended_input_schema, which must map to this
# parameter field.
PRIMARY_FIELD = 'e27bdcc5_8890_4cb8_a414_69d170b2e911'
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ('snowflake', 'search_rows'),
    ('workato_db_table', 'upsert_record'),
]
EXPECTED_RAW_TOOLS: list[str] = [
    'snowflake.search_rows',
    'workato_db_table.upsert_record',
]
ALLOWED_TOOLS: list[str] = [
    'snowflake.search_rows',
    'workato_db_table.upsert_record',
]


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def validate_59799030(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    search_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if str(search_input.get("table") or "") != SNOWFLAKE_TABLE:
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake source table changed: {search_input.get('table')}")
    upsert_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    if str(upsert_input.get("table_id") or "") != TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} Workato DB table id changed: {upsert_input.get('table_id')}")
    selection = actions[1].get("dynamicPickListSelection")
    selection_label = str((selection or {}).get("primary_field_id") or "") if isinstance(selection, dict) else ""
    if selection_label != "Internal ID":
        raise RuntimeError(
            f"recipe {RECIPE_ID} upsert primary field selection changed: {selection_label!r}; "
            f"the anonymized primary_field_id can no longer be resolved to {PRIMARY_FIELD}"
        )
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


def seed_59799030(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_59799030(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
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


def run_59799030(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    return run_live_snowflake_recipe(
        recipe_id=RECIPE_ID,
        track=TRACK,
        raw=raw,
        seed=seed,
        ctx=ctx,
        validation=validate_59799030(raw),
        expected_raw_tools=EXPECTED_RAW_TOOLS,
        allowed_tools=ALLOWED_TOOLS,
        verifier=verify_59799030,
        include_workato_db=True,
    )
