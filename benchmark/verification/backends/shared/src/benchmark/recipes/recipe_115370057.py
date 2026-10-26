from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_115370057


RECIPE_ID = "115370057"
SEED_TYPE = "workato_genie_error_live_slack"
TRACK = "live_slack_genie_error_alert"
TRIGGER_PROVIDER = "work_genie_connector_3535597_1715305794"
TRIGGER_NAME = "new_error_trigger"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_variable", "declare_list"),
    ("workato_variable", "insert_to_list"),
    ("workato_variable", "insert_to_list"),
    ("workato_variable", "insert_to_list"),
    ("workato_variable", "insert_to_list"),
    ("workato_variable", "insert_to_list"),
    ("workato_variable", "insert_to_list"),
    ("slack_bot", "post_bot_message"),
    ("slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_list",
    "workato_runtime.insert_to_list",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = ["slack.post_message"]


def validate_115370057(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    root_filter = raw.get("filter") if isinstance(raw.get("filter"), dict) else {}
    if "error_channel_id" not in str(root_filter):
        raise RuntimeError(f"recipe {RECIPE_ID} root filter no longer checks error_channel_id")
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


def seed_115370057(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_115370057(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    expect = _required_dict(data, "expect")
    trigger = trigger_input(ctx)
    _require_trigger(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    project_properties = seed_in.get("project_properties")
    if not isinstance(project_properties, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.project_properties")
    _require_error_channel_property(project_properties)
    return attach_variant(
        {
            "recipe_id": RECIPE_ID,
            "seed_type": SEED_TYPE,
            "trigger": trigger,
            "expect": expect,
            "track": data.get("track"),
            "project_properties": deepcopy(project_properties),
            "raw_validation": validation,
            "harness_tool_calls": ctx.tools.call_log(),
        },
        ctx,
    )


def run_115370057(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_115370057(raw)
    expect = _required_dict(seed, "expect")
    trigger = seed.get("trigger")
    if not isinstance(trigger, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing trigger object")
    _require_trigger(trigger)
    project_properties = seed.get("project_properties")
    if not isinstance(project_properties, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing project_properties")
    _require_error_channel_property(project_properties)
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
            "trigger": trigger,
            "expect": expect,
            "project_properties": deepcopy(project_properties),
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_115370057(result)
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


def _require_trigger(trigger: dict[str, Any]) -> None:
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger.parameters must be an object")
    error = parameters.get("error")
    if not isinstance(error, str) or not error:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger.parameters.error must be a non-empty string")


def _require_error_channel_property(project_properties: dict[str, Any]) -> None:
    # Both trigger-filter outcomes are benchmarked: a real channel id runs the
    # alert-post path, and "-" is the recipe's own explicit disabled sentinel
    # (root filter: present AND not_equals_to "-") for the verified zero-action
    # trigger-filter-false path. Only a missing/empty value is invalid input.
    value = project_properties.get("error_channel_id")
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"recipe {RECIPE_ID} project_properties.error_channel_id must be a non-empty string")


def _required_dict(container: dict[str, Any], key: str) -> dict[str, Any]:
    value = container.get(key)
    if not isinstance(value, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} missing object field: {key}")
    return deepcopy(value)


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
