from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, variant_data
from ..verifier import verify_130359991
from .salesforce_recipe_utils import collect_actions, copy_expect


RECIPE_ID = "130359991"
SEED_TYPE = "scheduled_stale_channel_tracking_slack_variant"
TRACK = "controlled_workato_db_live_slack"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TABLE_ID = "47089"
EXPECTED_ACTIONS = [
    ("workato_db_table", "get_records"),
    ("workato_db_table", "update_record"),
    ("slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS = [
    "workato_db_table.get_records",
    "workato_db_table.update_record",
    "slack.post_message",
]
ALLOWED_TOOLS = [
    "workato_db_table.get_records",
    "workato_db_table.update_record",
    "slack.post_message",
]


def validate_130359991(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    search_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if search_input.get("table_id") != TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} Workato DB table changed")
    if "=now - 2.months" not in str(search_input.get("filters") or []):
        raise RuntimeError(f"recipe {RECIPE_ID} stale activity filter changed")
    slack_input = actions[2].get("input") if isinstance(actions[2].get("input"), dict) else {}
    if "Sales-Opportunity Genie has stopped tracking it" not in str(slack_input):
        raise RuntimeError(f"recipe {RECIPE_ID} Slack notification body changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_130359991(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130359991(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or not isinstance(seed_in.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.workato_db_table")
    out = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": deepcopy(data.get("trigger_input") if isinstance(data.get("trigger_input"), dict) else {}),
        "track": data.get("track"),
        "expect": copy_expect(data),
        "raw_validation": validation,
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "now": data.get("now"),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if out["now"] in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} requires fixed now")
    return attach_variant(out, ctx)


def run_130359991(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130359991(raw)
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = _snapshot(ctx, seed)
    cleanup_response = _cleanup_slack_posts(raw_execution, ctx)
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
            "expected_channel": ctx.env.slack_channel_override,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "cleanup_response": cleanup_response,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_130359991(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    if isinstance(seed.get("workato_db_table"), dict):
        return ctx.tools.call("harness.workato_db_table.snapshot", {})
    return {}


def _cleanup_slack_posts(raw_execution: dict[str, Any], ctx: RecipeContext) -> list[dict[str, Any]]:
    cleanup: list[dict[str, Any]] = []
    for row in raw_execution.get("trace") or []:
        if not isinstance(row, dict) or row.get("tool") != "slack.post_message":
            continue
        result = row.get("result") if isinstance(row.get("result"), dict) else {}
        channel = str(result.get("channel") or "")
        ts = str(result.get("ts") or "")
        if channel and ts:
            cleanup.append(ctx.tools.call("slack.delete_message", {"channel": channel, "ts": ts}))
    return cleanup


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"number": a.get("number"), "provider": a.get("provider"), "name": a.get("name"), "as": a.get("as")} for a in actions]
