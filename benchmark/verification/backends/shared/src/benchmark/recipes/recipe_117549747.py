from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_117549747


RECIPE_ID = "117549747"
SEED_TYPE = "apps_package_release_live_slack"
TRACK = "live_slack_package_release"
TRIGGER_PROVIDER = "apps_by_workato_connector_3535597_1715273367"
TRIGGER_NAME = "new_package_release"
CHANNEL_PROPERTY = "Updates approval channel"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_variable", "declare_variable"),
    ("slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = ["slack.post_message"]


def validate_117549747(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    variable_input = actions[0].get("input") or {}
    if "smart_join" not in str(variable_input):
        raise RuntimeError(f"recipe {RECIPE_ID} release-note formatting changed")
    slack_input = actions[1].get("input") or {}
    if CHANNEL_PROPERTY not in str(slack_input.get("channel") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} Slack channel project property changed")
    if "New Package Released" not in str(slack_input):
        raise RuntimeError(f"recipe {RECIPE_ID} Slack message header changed")
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


def seed_117549747(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_117549747(raw)
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
    _require_channel_property(project_properties)
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


def run_117549747(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_117549747(raw)
    expect = _required_dict(seed, "expect")
    trigger = seed.get("trigger")
    if not isinstance(trigger, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing trigger object")
    _require_trigger(trigger)
    project_properties = seed.get("project_properties")
    if not isinstance(project_properties, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing project_properties")
    _require_channel_property(project_properties)
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
    result["verifier"] = verify_117549747(result)
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
    for key in ("package_version_id", "package_name", "version", "release_notes"):
        if key not in trigger or not isinstance(trigger.get(key), str):
            raise RuntimeError(f"recipe {RECIPE_ID} trigger missing string field {key}")
    if not trigger.get("package_version_id") or not trigger.get("package_name") or not trigger.get("version"):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger package fields must be non-empty")


def _require_channel_property(project_properties: dict[str, Any]) -> None:
    value = project_properties.get(CHANNEL_PROPERTY)
    if not isinstance(value, str) or not value or value == "-":
        raise RuntimeError(f"recipe {RECIPE_ID} project_properties.{CHANNEL_PROPERTY} must be a non-placeholder string")


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
