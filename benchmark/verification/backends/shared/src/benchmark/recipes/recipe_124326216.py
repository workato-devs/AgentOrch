from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_124326216


RECIPE_ID = "124326216"
SEED_TYPE = "live_slack_genie_unanswered_query_variant"
TRACK = "live_slack_workato_genie"
TRIGGER_PROVIDER = "workato_genie"
TRIGGER_NAME = "start_workflow"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("slack_bot", "get_user_by_email"),
    ("slack_bot", "post_bot_message"),
    ("workato_genie", "workflow_return_result"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "slack_bot.get_user_by_email",
    "slack.post_message",
    "workato_genie.workflow_return_result",
]
ALLOWED_TOOLS: list[str] = [
    "slack_bot.get_user_by_email",
    "slack.post_message",
    "workato_genie.workflow_return_result",
]


def validate_124326216(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    lookup_input = actions[0].get("input") or {}
    post_input = actions[1].get("input") or {}
    return_input = actions[2].get("input") or {}
    if "context" not in str(lookup_input.get("email") or "") or "user_email" not in str(lookup_input.get("email") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} Slack user lookup source changed")
    message = post_input.get("message") if isinstance(post_input.get("message"), dict) else {}
    if "parameters" not in str(post_input.get("channel") or "") or "channel_id" not in str(post_input.get("channel") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} Slack channel source changed")
    if "have an unanswered query" not in str(post_input.get("text") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} Slack text changed")
    if "user_query" not in str(message.get("attachment_text") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} Slack attachment source changed")
    result = return_input.get("result") if isinstance(return_input.get("result"), dict) else {}
    if "successfully directed" not in str(result.get("output_message") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} Genie return message changed")
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


def seed_124326216(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_124326216(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    expect = data.get("expect")
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    trigger = trigger_input(ctx)
    context = trigger.get("context") if isinstance(trigger.get("context"), dict) else {}
    parameters = trigger.get("parameters") if isinstance(trigger.get("parameters"), dict) else {}
    if not context.get("user_email"):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger missing context.user_email")
    if not parameters.get("user_query") or not parameters.get("channel_id"):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger missing parameters.user_query/channel_id")
    return attach_variant(
        {
            "recipe_id": RECIPE_ID,
            "seed_type": SEED_TYPE,
            "trigger": trigger,
            "track": data.get("track"),
            "expect": deepcopy(expect),
            "raw_validation": validation,
            "harness_tool_calls": ctx.tools.call_log(),
        },
        ctx,
    )


def run_124326216(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_124326216(raw)
    if not ctx.env.slack_channel_override:
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
            "expected_channel": ctx.env.slack_channel_override,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_124326216(result)
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
