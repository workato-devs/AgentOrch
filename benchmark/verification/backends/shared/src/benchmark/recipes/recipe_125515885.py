from __future__ import annotations

from copy import deepcopy
import json
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_125515885
from .salesforce_recipe_utils import collect_actions, copy_expect


RECIPE_ID = "125515885"
SEED_TYPE = "slack_block_update_workato_db_variant"
TRACK = "live_slack_block_update"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"
EXPECTED_ACTIONS = [
    ("workato_db_table", "get_records"),
    ("slack_bot", "update_blocks_by_block_id"),
    ("workato_db_table", "update_record"),
]
EXPECTED_RAW_TOOLS = [
    "workato_db_table.get_records",
    "slack.update_blocks_by_block_id",
    "workato_db_table.update_record",
]
ALLOWED_TOOLS = [
    "workato_db_table.get_records",
    "slack.update_blocks_by_block_id",
    "workato_db_table.update_record",
]


def validate_125515885(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    update_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    if update_input.get("surface") != "message" or "original_message_json" not in str(update_input):
        raise RuntimeError(f"recipe {RECIPE_ID} Slack block update mapping changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_125515885(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_125515885(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or not isinstance(seed_in.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.workato_db_table")
    trigger = deepcopy(trigger_input(ctx))
    context = trigger.setdefault("context", {})
    if not isinstance(context, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger context must be an object")
    seed_message = data.get("slack_seed_message") if isinstance(data.get("slack_seed_message"), dict) else {}
    text = str(seed_message.get("text") or "Benchmark renewal approval message")
    blocks = seed_message.get("blocks")
    if not isinstance(blocks, list):
        raise RuntimeError(f"recipe {RECIPE_ID} requires slack_seed_message.blocks")
    posted = ctx.tools.call(
        "harness.slack.seed_message",
        {"channel": ctx.env.slack_channel_override, "text": text, "blocks": blocks},
    )
    channel = str(posted.get("channel") or ctx.env.slack_channel_override)
    ts = str(posted.get("ts") or "")
    if not ts:
        raise RuntimeError(f"recipe {RECIPE_ID} Slack seed message returned no ts: {posted}")
    context["original_message_json"] = json.dumps(
        {
            "channel": channel,
            "ts": ts,
            "text": text,
            "blocks": blocks,
        },
        sort_keys=True,
    )
    context.setdefault("user", str(data.get("slack_user_id") or "U0B973TLN7N"))
    out = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": copy_expect(data),
        "raw_validation": validation,
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "seed_slack_message": {"channel": channel, "ts": ts, "text": text, "blocks": blocks},
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_125515885(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_125515885(raw)
    message = seed.get("seed_slack_message") if isinstance(seed.get("seed_slack_message"), dict) else {}
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = _snapshot(ctx, seed)
    cleanup_response = {}
    if message.get("channel") and message.get("ts"):
        cleanup_response = ctx.tools.call(
            "slack.delete_message",
            {"channel": message["channel"], "ts": message["ts"]},
        )
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
            "cleanup_response": cleanup_response,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_125515885(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    if isinstance(seed.get("workato_db_table"), dict):
        return ctx.tools.call("harness.workato_db_table.snapshot", {})
    return {}


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
