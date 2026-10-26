from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_85944696


RECIPE_ID = "85944696"
SEED_TYPE = "clock_scheduled_psa_admin_reminder_broadcast_variant"
TRACK = "live_slack_scheduled_multi_reminder_broadcast"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
ADMIN_CHANNEL_PROPERTY = "Admin Channel"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("slack_bot", "post_bot_message"),
    ("slack_bot", "post_bot_message"),
    ("slack_bot", "post_bot_message"),
    ("slack_bot", "post_bot_message"),
    ("slack_bot", "post_bot_message"),
    ("slack_bot", "post_bot_message"),
    ("logger", "log_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "slack.post_message",
    "workato_runtime.log_message",
]
ALLOWED_TOOLS: list[str] = [
    "slack.post_message",
    "workato_runtime.log_message",
]


def validate_85944696(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    for idx in range(6):
        post_input = actions[idx].get("input") if isinstance(actions[idx].get("input"), dict) else {}
        channel = str(post_input.get("channel") or "")
        if ADMIN_CHANNEL_PROPERTY not in channel:
            raise RuntimeError(f"recipe {RECIPE_ID} post {idx} channel is not the Admin Channel property")
        if not isinstance(post_input.get("blocks"), list) or not post_input.get("blocks"):
            raise RuntimeError(f"recipe {RECIPE_ID} post {idx} lost its Block Kit reminder body")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_85944696(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_85944696(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    trigger = trigger_input(ctx)
    seed_in = data.get("seed") if isinstance(data.get("seed"), dict) else {}
    account_properties = seed_in.get("account_properties") if isinstance(seed_in.get("account_properties"), dict) else {}
    if ADMIN_CHANNEL_PROPERTY not in account_properties:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.account_properties['{ADMIN_CHANNEL_PROPERTY}']")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "account_properties": deepcopy(account_properties),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    for key, value in seed_in.items():
        if key == "account_properties":
            continue
        if isinstance(value, dict):
            out[str(key)] = deepcopy(value)
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    for key in ("force_action_error", "job_context"):
        if isinstance(data.get(key), dict):
            out[key] = deepcopy(data[key])
    return attach_variant(out, ctx)


def run_85944696(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_85944696(raw)
    if any(tool.startswith("slack.") for tool in ALLOWED_TOOLS) and not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
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
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_85944696(result)
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
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"number": action.get("number"), "provider": action.get("provider"), "name": action.get("name"), "as": action.get("as")}
        for action in actions
    ]
