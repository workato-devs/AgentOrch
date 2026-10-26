from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_86902509


RECIPE_ID = "86902509"
SEED_TYPE = "financebot_duplicate_order_acknowledge_variant"
TRACK = "live_slack_financebot_duplicate_order_acknowledge"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"

EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("slack_bot", "post_bot_message"),
    ("slack", "get_user_by_email"),
    ("workato_variable", "declare_variable"),
    ("slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "slack.post_message",
    "slack_bot.get_user_by_email",
    "workato_runtime.declare_variable",
]
ALLOWED_TOOLS: list[str] = [
    "slack.post_message",
    "slack_bot.get_user_by_email",
]

_ACK_TEXT = "Processing this!"
_NOT_PROCESSED_TEXT = "Activated Order Not Processed"


def validate_86902509(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    ack_input = _json_of(actions[0].get("input"))
    if _ACK_TEXT not in ack_input:
        raise RuntimeError(f"recipe {RECIPE_ID} acknowledgement text changed")
    final_input = _json_of(actions[3].get("input"))
    if _NOT_PROCESSED_TEXT not in final_input or "will not be created in NetSuite" not in final_input:
        raise RuntimeError(f"recipe {RECIPE_ID} final confirmation body changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_86902509(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_86902509(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    trigger = trigger_input(ctx)
    if not isinstance(trigger.get("parameters"), dict) or not trigger["parameters"]:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing parameters object")
    seed_in = data.get("seed") if isinstance(data.get("seed"), dict) else {}
    if not isinstance(seed_in.get("project_properties"), dict) or "Salesforce Environment" not in seed_in["project_properties"]:
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.project_properties['Salesforce Environment']")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "raw_validation": validation,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if isinstance(data.get("expect"), dict):
        out["expect"] = deepcopy(data["expect"])
    for key, value in seed_in.items():
        if isinstance(value, dict):
            out[str(key)] = deepcopy(value)
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    for key in ("force_action_error", "job_context"):
        if isinstance(data.get(key), dict):
            out[key] = deepcopy(data[key])
    return attach_variant(out, ctx)


def run_86902509(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_86902509(raw)
    if any(tool.startswith("slack.") for tool in ALLOWED_TOOLS) and not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    raw_execution = execute_raw_recipe(raw, seed, ctx)
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
            "cleanup_response": cleanup_response,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_86902509(result)
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


def _cleanup_slack_posts(raw_execution: dict[str, Any], ctx: RecipeContext) -> list[dict[str, Any]]:
    cleanup: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in raw_execution.get("trace") or []:
        if not isinstance(row, dict) or row.get("tool") != "slack.post_message":
            continue
        result = row.get("result") if isinstance(row.get("result"), dict) else {}
        channel = str(result.get("channel") or "")
        ts = str(result.get("ts") or "")
        if channel and ts and (channel, ts) not in seen:
            seen.add((channel, ts))
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


def _json_of(value: Any) -> str:
    import json

    try:
        return json.dumps(value, sort_keys=True, default=str)
    except (TypeError, ValueError):
        return str(value)
