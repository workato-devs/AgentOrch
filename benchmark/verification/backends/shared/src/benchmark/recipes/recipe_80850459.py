from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data, variant_index
from ..verifier import verify_80850459


RECIPE_ID = "80850459"
SEED_TYPE = "slack_bot_command_rerun_job_delete_original_variant"
TRACK = "live_slack_workato_rerun_delete_original"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"
COMMAND_NAME = "rerun_job"
RERUN_RECIPE_ID = "24999439"
SEED_MESSAGE_CHANNEL_TOKEN = "$SEED_MESSAGE_CHANNEL"
SEED_MESSAGE_TS_TOKEN = "$SEED_MESSAGE_TS"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_app", "rerun_jobs"),
    ("slack_bot", "post_bot_reply_v2"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_app.rerun_jobs",
    "slack.post_reply",
]
ALLOWED_TOOLS: list[str] = [
    "workato_app.rerun_jobs",
    "slack.post_reply",
]


def validate_80850459(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    trigger_in = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    if trigger_in.get("name") != COMMAND_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} is not the expected `{COMMAND_NAME}` bot command")
    actions = _collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    rerun_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if str(rerun_input.get("recipe_id") or "") != RERUN_RECIPE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} rerun target recipe changed")
    jobs = rerun_input.get("jobs") if isinstance(rerun_input.get("jobs"), dict) else {}
    if "job_id" not in jobs:
        raise RuntimeError(f"recipe {RECIPE_ID} rerun jobs.job_id binding changed")
    reply_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    if str(reply_input.get("delete_original")).lower() != "true":
        raise RuntimeError(f"recipe {RECIPE_ID} post_bot_reply_v2 is not delete_original=true")
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


def seed_80850459(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_80850459(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    channel = ctx.env.slack_channel_override
    if not channel:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters") if isinstance(trigger.get("parameters"), dict) else {}
    if parameters.get("job_id") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters.job_id must be non-empty")

    # Live-seed the original interactive command message so the recipe has a
    # real Slack message to delete (delete_original). Its ts is threaded into
    # the trigger as the message reference the bot command targets.
    idx = variant_index(ctx)
    seed_text = (
        f"benchmark seed for recipe {RECIPE_ID} variant {idx:02d}: "
        f"rerun_job command prompt for job {parameters.get('job_id')}"
    )
    posted = ctx.tools.call("harness.slack.seed_message", {"channel": channel, "text": seed_text})
    actual_channel = str(posted.get("channel") or channel)
    ts = posted.get("ts")
    if not ts:
        raise RuntimeError(f"recipe {RECIPE_ID} Slack chat.postMessage returned no ts: {posted}")
    ts = str(ts)
    trigger["channel"] = actual_channel
    trigger["message_ts"] = ts
    expect = _replace_value(
        deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        {
            SEED_MESSAGE_CHANNEL_TOKEN: actual_channel,
            SEED_MESSAGE_TS_TOKEN: ts,
        },
    )

    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": expect,
        "raw_validation": validation,
        "message": {"channel": actual_channel, "ts": ts, "text": seed_text},
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_80850459(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_80850459(raw)
    if any(tool.startswith("slack.") for tool in ALLOWED_TOOLS) and not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    message = seed.get("message") if isinstance(seed.get("message"), dict) else {}
    if not message.get("channel") or not message.get("ts"):
        raise RuntimeError(f"recipe {RECIPE_ID} seed missing live message channel/ts")
    raw_execution = execute_raw_recipe(raw, seed, ctx)
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
            "seed_message": deepcopy(message),
            "rerun_recipe_id": RERUN_RECIPE_ID,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_80850459(result)
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


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}


def _replace_value(value: Any, refs: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_value(item, refs) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_value(item, refs) for item in value]
    if isinstance(value, str):
        out = value
        for token, replacement in refs.items():
            out = out.replace(token, replacement)
        return out
    return value
