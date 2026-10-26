from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_85791701


RECIPE_ID = "85791701"
SEED_TYPE = "scheduled_connector_upgrade_digest_slack_variant"
TRACK = "controlled_workato_db_live_slack"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
CONNECTOR_TABLE_ID = "4357"
DUE_DATE_FIELD_ID = "f8fb4963-11ec-45f8-8a8b-c54926cb1b4c"

EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_db_table", "get_records"),
    ("workato_variable", "declare_variable"),
    ("workato_variable", "declare_variable"),
    ("workato_variable", "update_variables"),
    ("slack", "post_message_to_channel"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_runtime.declare_variable",
    "workato_runtime.update_variables",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "slack.post_message",
]


def validate_85791701(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    get_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if get_input.get("table_id") != CONNECTOR_TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} connector table changed")
    filters = get_input.get("filters") if isinstance(get_input.get("filters"), list) else []
    first_filter = filters[0] if filters and isinstance(filters[0], dict) else {}
    filter_value = str(first_filter.get("value_date") or "")
    if ".to_date + 3.months" not in filter_value or "scheduled_time" not in filter_value:
        raise RuntimeError(f"recipe {RECIPE_ID} due-date horizon filter changed")
    if first_filter.get("op_date") != "lte":
        raise RuntimeError(f"recipe {RECIPE_ID} due-date filter operator changed")
    header_input = _json_of(actions[1].get("input"))
    if "due for upgrade in less than 3 months" not in header_input:
        raise RuntimeError(f"recipe {RECIPE_ID} notification header changed")
    slack_input = actions[4].get("input") if isinstance(actions[4].get("input"), dict) else {}
    if "Notification" not in _json_of(slack_input):
        raise RuntimeError(f"recipe {RECIPE_ID} Slack notification body changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_85791701(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_85791701(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or not isinstance(seed_in.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.workato_db_table")
    trigger = trigger_input(ctx)
    if not isinstance(trigger.get("scheduled_time"), str) or not trigger.get("scheduled_time"):
        raise RuntimeError(f"recipe {RECIPE_ID} requires trigger_input.scheduled_time (clock horizon anchor)")
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


def run_85791701(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_85791701(raw)
    if any(tool.startswith("slack.") for tool in ALLOWED_TOOLS) and not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = _snapshot(ctx, seed)
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
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "cleanup_response": cleanup_response,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_85791701(result)
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
    if isinstance(seed.get("workato_db_table"), dict):
        return ctx.tools.call("harness.workato_db_table.snapshot", {})
    return {}


def _cleanup_slack_posts(raw_execution: dict[str, Any], ctx: RecipeContext) -> list[dict[str, Any]]:
    cleanup: list[dict[str, Any]] = []
    for row in raw_execution.get("trace") or []:
        if not isinstance(row, dict) or row.get("tool") != "slack.post_message":
            continue
        result = row.get("result") if isinstance(row.get("result"), dict) else {}
        channel = str(result.get("channel") or "")
        ts = str(result.get("ts") or "")
        if channel and ts:
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
