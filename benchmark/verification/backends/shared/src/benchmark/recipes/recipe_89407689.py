from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data, variant_index
from ..verifier import verify_89407689


RECIPE_ID = "89407689"
SEED_TYPE = "slack_bot_command_confirm_notes_threaded_post_variant"
TRACK = "live_slack_bot_command_threaded_confirmation"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"
ACCOUNT_PROPERTY = "Gong Demo Slack ID"
CONFIRMATION_TEXT = "Thank you for confirming, the notes are now updated in Salesforce :Salesforce:"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("slack_bot", "get_user_by_email"),
    ("slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "slack_bot.get_user_by_email",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "slack_bot.get_user_by_email",
    "slack.post_message",
]


def validate_89407689(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    post_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    if str(post_input.get("text") or "") != CONFIRMATION_TEXT:
        raise RuntimeError(f"recipe {RECIPE_ID} confirmation text changed")
    fields = post_input.get("attachment_fields") if isinstance(post_input.get("attachment_fields"), list) else []
    titles = [str(field.get("title") or "") for field in fields if isinstance(field, dict)]
    if titles != ["Summarized Main Points", "Next Steps"]:
        raise RuntimeError(f"recipe {RECIPE_ID} attachment fields changed: {titles}")
    advanced = post_input.get("advanced") if isinstance(post_input.get("advanced"), dict) else {}
    if "thread_ts" not in advanced:
        raise RuntimeError(f"recipe {RECIPE_ID} lost threaded reply (advanced.thread_ts)")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_89407689(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_89407689(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    channel = ctx.env.slack_channel_override
    if not channel:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    trigger = trigger_input(ctx)
    context = trigger.get("context") if isinstance(trigger.get("context"), dict) else {}
    if not context.get("user_email"):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing context.user_email")
    parameters = trigger.get("parameters") if isinstance(trigger.get("parameters"), dict) else {}
    if not parameters.get("email_recap") or not parameters.get("email_next_steps"):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing email_recap/email_next_steps")

    # Live-seed the original call-notes message so the confirmation reply can
    # thread under a real message (invalid thread_ts is rejected by Slack).
    idx = variant_index(ctx)
    original_text = f"benchmark seed for recipe {RECIPE_ID} variant {idx:02d}: call notes awaiting confirmation"
    posted = ctx.tools.call("harness.slack.seed_message", {"channel": channel, "text": original_text})
    actual_channel = str(posted.get("channel") or channel)
    ts = posted.get("ts")
    if not ts:
        raise RuntimeError(f"recipe {RECIPE_ID} Slack chat.postMessage returned no ts: {posted}")
    ts = str(ts)
    parameters["message_id"] = ts
    trigger["parameters"] = parameters
    trigger["context"] = context

    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        # The account's "Gong Demo Slack ID" resolves to the live benchmark
        # channel the follow-up post lands in (harness routes non-user ids to the
        # channel override).
        "account_properties": {ACCOUNT_PROPERTY: actual_channel},
        "original_message": {"channel": actual_channel, "ts": ts, "text": original_text},
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_89407689(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_89407689(raw)
    if any(tool.startswith("slack.") for tool in ALLOWED_TOOLS) and not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    original = seed.get("original_message") if isinstance(seed.get("original_message"), dict) else {}
    if not original.get("ts"):
        raise RuntimeError(f"recipe {RECIPE_ID} seed missing live original message ts")
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = _snapshot(ctx, seed)
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
            "original_message": deepcopy(original),
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_89407689(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("lookup_table"), dict):
        out.update(ctx.tools.call("harness.lookup_table.snapshot", {}))
    if isinstance(seed.get("workato_db_table"), dict):
        out.update(ctx.tools.call("harness.workato_db_table.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"number": action.get("number"), "provider": action.get("provider"), "name": action.get("name"), "as": action.get("as")}
        for action in actions
    ]
