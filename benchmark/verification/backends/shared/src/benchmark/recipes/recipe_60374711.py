from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_60374711
from .salesforce_recipe_utils import collect_actions
from .snowflake_live_recipe_utils import ground_truth, seed_live_snowflake


RECIPE_ID = "60374711"
SEED_TYPE = "clock_live_snowflake_employee_pub_sub_fanout_variant"
TRACK = "live_snowflake_pub_sub_fanout"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TOPIC_ID = "22071"
SQL_FRAGMENTS = (
    "SELECT EMAIL FROM EMPLOYEE",
)
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("snowflake", "search_rows_sql"),
    ("workato_pub_sub", "publish_to_topic"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_pub_sub.publish_to_topic",
]
ALLOWED_TOOLS: list[str] = EXPECTED_RAW_TOOLS


def validate_60374711(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    sql = str((actions[0].get("input") or {}).get("sql") or "")
    for fragment in SQL_FRAGMENTS:
        if fragment not in sql:
            raise RuntimeError(f"recipe {RECIPE_ID} Snowflake SQL mapping changed")
    publish_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    if str(publish_input.get("topic_id") or "") != TOPIC_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} pub_sub topic id changed")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": _action_summary(actions),
    }


def seed_60374711(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_60374711(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    provision = seed_live_snowflake(RECIPE_ID, data, ctx)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger_input(ctx),
        "track": data.get("track") or TRACK,
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "snowflake_live": deepcopy(provision["state"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_60374711(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_60374711(raw)
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    snowflake_cleanup: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        if isinstance(seed.get("snowflake_live"), dict):
            snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
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
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "cleanup_response": {"snowflake_live": snowflake_cleanup},
            "ground_truth": ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_60374711(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("snowflake_live"), dict):
        out.update(ctx.tools.call("harness.snowflake.snapshot", {}))
    return out


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"number": a.get("number"), "provider": a.get("provider"), "name": a.get("name"), "as": a.get("as")}
        for a in actions
    ]
