from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_130740169
from .salesforce_recipe_utils import collect_actions, copy_expect, replace_tokens


RECIPE_ID = "130740169"
SEED_TYPE = "recipe_function_vendor_case_slack_update_variant"
TRACK = "workato_db_live_slack_recipe_function_update"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TABLE_ID = "48621"
EXPECTED_ACTIONS = [
    ("workato_db_table", "get_records"),
    ("slack_bot", "post_bot_message"),
    ("workato_recipe_function", "return_result"),
]
EXPECTED_RAW_TOOLS = [
    "workato_db_table.get_records",
    "slack.post_message",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS = [
    "workato_db_table.get_records",
    "slack.post_message",
    "workato_recipe_function.return_result",
]
REQUIRED_PARAMETERS = ("vendor_id", "thread_id", "message_id_to_update", "message_content", "source")


def validate_130740169(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    search_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if search_input.get("table_id") != TABLE_ID or "vendor_id" not in str(search_input):
        raise RuntimeError(f"recipe {RECIPE_ID} Workato DB vendor lookup changed")
    slack_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    if "message_id_to_update" not in str(slack_input) or "message_content" not in str(slack_input):
        raise RuntimeError(f"recipe {RECIPE_ID} Slack update mapping changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_130740169(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130740169(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    seed_in = data.get("seed")
    db_seed = seed_in.get("workato_db_table") if isinstance(seed_in, dict) else None
    if not isinstance(db_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.workato_db_table")
    slack_seed = data.get("slack_seed_message") if isinstance(data.get("slack_seed_message"), dict) else {}
    seed_text = str(slack_seed.get("text") or "Benchmark vendor case update placeholder")
    posted = ctx.tools.call(
        "harness.slack.seed_message",
        {"channel": ctx.env.slack_channel_override, "text": seed_text},
    )
    channel = str(posted.get("channel") or ctx.env.slack_channel_override)
    ts = str(posted.get("ts") or "")
    if not ts:
        raise RuntimeError(f"recipe {RECIPE_ID} Slack seed message returned no ts: {posted}")
    refs = {
        "$SLACK_CHANNEL": channel,
        "$SLACK_MESSAGE_TS": ts,
        "$SLACK_THREAD_TS": ts,
    }
    trigger = replace_tokens(trigger_input(ctx), refs)
    parameters = trigger.get("parameters") if isinstance(trigger.get("parameters"), dict) else None
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing parameters object")
    for key in REQUIRED_PARAMETERS:
        if parameters.get(key) in (None, ""):
            raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter missing {key}")
    out = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": replace_tokens(copy_expect(data), refs),
        "raw_validation": validation,
        "workato_db_table": replace_tokens(deepcopy(db_seed), refs),
        "seed_slack_message": {"channel": channel, "ts": ts, "text": seed_text},
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_130740169(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130740169(raw)
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    cleanup_response: dict[str, Any] | None = None
    message = seed.get("seed_slack_message") if isinstance(seed.get("seed_slack_message"), dict) else {}
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        if message.get("channel") and message.get("ts"):
            cleanup_response = ctx.tools.call(
                "slack.delete_message",
                {"channel": message["channel"], "ts": message["ts"]},
            )
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
            "cleanup_response": cleanup_response,
            "seed_slack_message": message,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_130740169(result)
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
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"number": action.get("number"), "provider": action.get("provider"), "name": action.get("name"), "as": action.get("as")} for action in actions]
