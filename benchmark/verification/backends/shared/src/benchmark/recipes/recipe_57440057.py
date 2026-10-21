from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data, variant_index
from ..verifier import verify_57440057


RECIPE_ID = "57440057"
SEED_TYPE = "slack_bot_command_rerun_variant"
TRACK = "live_slack_bot_delete_and_rerun"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"
# 'firefighter rerun' bot command (scope job, required parameters recipe_id +
# job_id). IF the trigger ts is present the recipe deletes the original
# command message (post_bot_reply_v2 delete_original=true, live Slack), then
# workato_app.rerun_jobs (controlled Workato-internal mock) ALWAYS runs.
# The ts-present variant seeds a live Slack message and threads its real
# ts/channel into the trigger; a ts is never fabricated.
SEED_TS_TOKEN = "$SEED_MESSAGE_TS"
SEED_CHANNEL_TOKEN = "$SEED_MESSAGE_CHANNEL"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("slack_bot", "post_bot_reply_v2"),
    ("workato_app", "rerun_jobs"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "slack.post_reply",
    "workato_app.rerun_jobs",
]
ALLOWED_TOOLS: list[str] = [
    "slack.post_reply",
    "workato_app.rerun_jobs",
]


def validate_57440057(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    inp = raw.get("input") or {}
    if inp.get("domain") != "firefighter" or inp.get("name") != "rerun" or inp.get("scope") != "job":
        raise RuntimeError(f"recipe {RECIPE_ID} is not the expected 'firefighter rerun' bot command")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    if (actions[0].get("input") or {}).get("delete_original") != "true":
        raise RuntimeError(f"recipe {RECIPE_ID} reply action is not delete_original=true")
    guard = (raw.get("block") or [None])[0]
    if not isinstance(guard, dict) or guard.get("keyword") != "if":
        raise RuntimeError(f"recipe {RECIPE_ID} delete action is no longer guarded by the IF block")
    conditions = ((guard.get("input") or {}).get("conditions") or [])
    if len(conditions) != 1 or conditions[0].get("operand") != "present":
        raise RuntimeError(f"recipe {RECIPE_ID} IF guard is no longer a single ts-present condition")
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


def seed_57440057(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_57440057(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters")
    if (
        not isinstance(parameters, dict)
        or not str(parameters.get("recipe_id") or "")
        or not str(parameters.get("job_id") or "")
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} bot command requires parameters.recipe_id and parameters.job_id"
        )
    expect = data.get("expect") if isinstance(data.get("expect"), dict) else {}
    wants_delete = "slack.post_reply" in (expect.get("tools") or [])
    has_ts_token = trigger.get("ts") == SEED_TS_TOKEN
    if wants_delete != has_ts_token:
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant is inconsistent: the delete_original path requires "
            f"trigger ts == {SEED_TS_TOKEN!r} and expect.tools containing slack.post_reply"
        )
    message: dict[str, Any] | None = None
    if has_ts_token:
        channel = ctx.env.slack_channel_override
        if not channel:
            raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
        idx = variant_index(ctx)
        seed_text = f"benchmark seed for recipe {RECIPE_ID} variant {idx:02d}: firefighter rerun command message"
        posted = ctx.tools.call("harness.slack.seed_message", {"channel": channel, "text": seed_text})
        ts = str(posted.get("ts") or "")
        if not ts:
            raise RuntimeError(f"Slack chat.postMessage returned no ts: {posted}")
        actual_channel = str(posted.get("channel") or channel)
        trigger["ts"] = ts
        if trigger.get("channel") == SEED_CHANNEL_TOKEN:
            trigger["channel"] = actual_channel
        message = {
            "channel": actual_channel,
            "ts": ts,
            "text": seed_text,
        }
    elif trigger.get("ts") not in (None, ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger ts must be the {SEED_TS_TOKEN!r} token or absent; "
            "never fabricate a live Slack ts"
        )
    if trigger.get("channel") == SEED_CHANNEL_TOKEN:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger channel token {SEED_CHANNEL_TOKEN!r} requires the ts-present seed"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(expect),
        "raw_validation": validation,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if message is not None:
        out["message"] = message
    return attach_variant(out, ctx)


def run_57440057(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_57440057(raw)
    if any(tool.startswith("slack.") for tool in ALLOWED_TOOLS):
        if not ctx.env.slack_channel_override:
            raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    expect = seed.get("expect") if isinstance(seed.get("expect"), dict) else {}
    message = seed.get("message")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    if "slack.post_reply" in (expect.get("tools") or []):
        if not isinstance(message, dict):
            raise RuntimeError(
                f"recipe {RECIPE_ID} delete_original variant requires a live seeded Slack message"
            )
        actual_channel = str(message.get("channel") or "")
        ts = str(message.get("ts") or "")
        if not actual_channel or not ts:
            raise RuntimeError("seed file missing Slack channel or ts")
        details["seed_message"] = {
            "channel": actual_channel,
            "ts": ts,
            "text": message.get("text"),
        }
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    details["raw_execution"] = raw_execution
    details["ground_truth"] = _ground_truth(raw_execution)
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_57440057(result)
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
