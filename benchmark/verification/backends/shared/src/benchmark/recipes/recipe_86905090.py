from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_86905090


RECIPE_ID = '86905090'
SEED_TYPE = 'slack_bot_standup_command'
TRACK = 'live_slack_standup_post_and_reply'
TRIGGER_PROVIDER = 'slack_bot'
TRIGGER_NAME = 'bot_command_v2'
EXPECTED_ACTIONS: list[tuple[str, str]] = [('slack_bot', 'post_bot_message'), ('slack_bot', 'post_bot_reply_v2')]
ALLOWED_TOOLS: list[str] = ['slack.post_message', 'slack.post_reply']
RAW_CHECKS: list[dict[str, Any]] = []


def validate_86905090(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    for check in RAW_CHECKS:
        _raw_check(actions, check)
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


def seed_86905090(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_86905090(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    expect = _required_dict(data, "expect")
    trigger = trigger_input(ctx)
    seed_in = data.get("seed")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "expect": expect,
        "raw_validation": validation,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if isinstance(seed_in, dict):
        for key in ("workato_db_table", "lookup_table"):
            if isinstance(seed_in.get(key), dict):
                out[key] = deepcopy(seed_in[key])
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    for key in ("force_action_error", "job_context"):
        if isinstance(data.get(key), dict):
            out[key] = deepcopy(data[key])
    return attach_variant(out, ctx)


def run_86905090(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_86905090(raw)
    expect = _required_dict(seed, "expect")
    if any(tool.startswith("slack.") for tool in ALLOWED_TOOLS) and _expected_tool_count(expect) > 0:
        if not ctx.env.slack_channel_override:
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
            "expect": expect,
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_86905090(result)
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


def _raw_check(actions: list[dict[str, Any]], check: dict[str, Any]) -> None:
    index = int(check.get("action_index", 0))
    if index >= len(actions):
        raise RuntimeError(f"recipe {RECIPE_ID} raw check action_index out of range")
    raw_input = actions[index].get("input") or {}
    path = check.get("path") or []
    value: Any = raw_input
    for part in path:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            raise RuntimeError(f"recipe {RECIPE_ID} raw check path missing: {path}")
    if "equals" in check and value != check["equals"]:
        raise RuntimeError(f"recipe {RECIPE_ID} raw check failed for {path}")
    if "contains" in check and str(check["contains"]) not in str(value):
        raise RuntimeError(f"recipe {RECIPE_ID} raw check failed for {path}")


def _required_dict(container: dict[str, Any], key: str) -> dict[str, Any]:
    value = container.get(key)
    if not isinstance(value, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} missing object field: {key}")
    return deepcopy(value)


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("workato_db_table"), dict):
        out.update(ctx.tools.call("harness.workato_db_table.snapshot", {}))
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
