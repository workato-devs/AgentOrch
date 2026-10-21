from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_128892154


RECIPE_ID = "128892154"
SEED_TYPE = "slack_timesheet_reminder_lookup_variant"
TRACK = "mock_lookup_then_live_slack"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("lookup_table", "search_entries"),
    ("slack_bot", "get_user_by_email"),
    ("slack_bot", "post_bot_message"),
    ("slack_bot", "post_bot_message"),
    ("slack_bot", "post_bot_reply_v2"),
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "slack_bot.get_user_by_email",
    "slack.post_message",
    "slack.post_reply",
    # Raw step 9 (post_bot_reply_v2 with delete_original=true) executes as a
    # live slack.delete_message of the original button message.
    "slack.delete_message",
]

# Variant trigger inputs on the delete_original branch bind the live seeded
# message via these tokens (the clicked message's ts/channel ARE the lookup
# search keys and the delete target in the raw recipe).
_SEED_MESSAGE_TOKEN_PREFIX = "$SEED_MESSAGE_"
_SEED_MESSAGE_TOKENS = {"$SEED_MESSAGE_TS": "ts", "$SEED_MESSAGE_CHANNEL": "channel"}


def validate_128892154(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    first_input = actions[0].get("input") if actions else {}
    if not isinstance(first_input, dict) or str(first_input.get("lookup_table_id")) != "2937665":
        raise RuntimeError(f"recipe {RECIPE_ID} lookup table id changed")
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


def seed_128892154(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_128892154(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    expect = _required_dict(data, "expect")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or not isinstance(seed_in.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.lookup_table")
    message = _seed_slack_message(seed_in, ctx)
    trigger = trigger_input(ctx)
    if message is not None:
        trigger = _replace_message_tokens(trigger, message)
    elif _SEED_MESSAGE_TOKEN_PREFIX in json.dumps(trigger):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger input references {_SEED_MESSAGE_TOKEN_PREFIX}* "
            "but the variant seed has no slack_message section"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": expect,
        "raw_validation": validation,
        "lookup_table": deepcopy(seed_in["lookup_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if message is not None:
        out["message"] = message
    return attach_variant(out, ctx)


def _seed_slack_message(seed_in: dict[str, Any], ctx: RecipeContext) -> dict[str, Any] | None:
    """Post the live original message (the manager's button message) that the
    delete_original branch acts on. Absent section = variant never reaches the
    delete step."""
    section = seed_in.get("slack_message")
    if section is None:
        return None
    if not isinstance(section, dict) or not str(section.get("text") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} seed.slack_message requires a non-empty text")
    channel = ctx.env.slack_channel_override
    if not channel:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    posted = ctx.tools.call("harness.slack.seed_message", {"channel": channel, "text": str(section["text"])})
    ts = posted.get("ts")
    if not ts:
        raise RuntimeError(f"Slack chat.postMessage returned no ts: {posted}")
    return {
        "channel": str(posted.get("channel") or channel),
        "ts": str(ts),
        "text": str(section["text"]),
    }


def _replace_message_tokens(value: Any, message: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_message_tokens(item, message) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_message_tokens(item, message) for item in value]
    if isinstance(value, str):
        out = value
        for token, key in _SEED_MESSAGE_TOKENS.items():
            out = out.replace(token, str(message[key]))
        if _SEED_MESSAGE_TOKEN_PREFIX in out:
            raise RuntimeError(f"recipe {RECIPE_ID} unknown seed-message token in trigger input: {value!r}")
        return out
    return value


def run_128892154(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_128892154(raw)
    expect = _required_dict(seed, "expect")
    if _expected_tool_count(expect) > 0 and not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")

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
            "expect": expect,
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_128892154(result)
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


def _required_dict(container: dict[str, Any], key: str) -> dict[str, Any]:
    value = container.get(key)
    if not isinstance(value, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} missing object field: {key}")
    return deepcopy(value)


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("lookup_table"), dict):
        out.update(ctx.tools.call("harness.lookup_table.snapshot", {}))
    return out


def _expected_tool_count(expect: dict[str, Any]) -> int:
    if isinstance(expect.get("tools"), list):
        return len(expect["tools"])
    return int(expect.get("executed_action_count") or 0)


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
