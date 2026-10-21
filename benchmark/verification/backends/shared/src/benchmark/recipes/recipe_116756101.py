from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_116756101


RECIPE_ID = "116756101"
SEED_TYPE = "pubsub_customer_story_snowflake_load_variant"
TRACK = "benchmark_final_state"
TRIGGER_PROVIDER = "workato_pub_sub"
TRIGGER_NAME = "batch_subscribe_to_topic"
TOPIC_ID = "33189"
SNOWFLAKE_TABLE = "WALNUTIQ.CUSTOMER_STORY_PROD"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_variable", "declare_variable"),
    ("snowflake", "upsert_rows_batch"),
    ("snowflake", "update_rows"),
    ("logger", "log_message"),
    ("logger", "log_message"),
    ("slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "snowflake.upsert_rows_batch",
    "snowflake.update_rows",
    "workato_runtime.log_message",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.upsert_rows_batch",
    "snowflake.update_rows",
    "slack.post_message",
]


def validate_116756101(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    raw_input = raw.get("input") or {}
    if str(raw_input.get("topic_id") or "") != TOPIC_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} pubsub topic changed")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    upsert_input = actions[1].get("input") or {}
    if str(upsert_input.get("table") or "") != SNOWFLAKE_TABLE:
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake upsert table changed")
    if str(upsert_input.get("key_columns") or "") != "uniqueId":
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake key column changed")
    update_input = actions[2].get("input") or {}
    if str(update_input.get("table") or "") != SNOWFLAKE_TABLE:
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake update table changed")
    if '"uniqueId"' not in str(update_input.get("where") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake update where clause changed")
    slack_input = actions[5].get("input") or {}
    message = slack_input.get("message") if isinstance(slack_input.get("message"), dict) else {}
    if message.get("title") != "Story Load Error":
        raise RuntimeError(f"recipe {RECIPE_ID} Slack error alert title changed")
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


def seed_116756101(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_116756101(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    messages = trigger.get("messages")
    if not isinstance(messages, list):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing messages list")
    for idx, message in enumerate(messages):
        if not isinstance(message, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} message {idx} is not an object")
        if message.get("unique_id") in (None, ""):
            raise RuntimeError(f"recipe {RECIPE_ID} message {idx} missing unique_id")
        if message.get("correlId") in (None, ""):
            raise RuntimeError(f"recipe {RECIPE_ID} message {idx} missing correlId")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    expect = data.get("expect") if isinstance(data.get("expect"), dict) else {}
    expected_tools = expect.get("tools") if isinstance(expect.get("tools"), list) else []
    if "slack.post_message" in expected_tools:
        account_properties = seed_in.get("account_properties")
        if not isinstance(account_properties, dict) or "WIQ.ADMIN.CHANNEL" not in account_properties:
            raise RuntimeError(f"recipe {RECIPE_ID} Slack error variant missing WIQ.ADMIN.CHANNEL account property")
        job_context = seed_in.get("job_context")
        if not isinstance(job_context, dict) or not job_context.get("job_url"):
            raise RuntimeError(f"recipe {RECIPE_ID} Slack error variant missing job_context.job_url")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "raw_validation": validation,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if expect:
        out["expect"] = deepcopy(expect)
    for key, value in seed_in.items():
        if isinstance(value, dict):
            out[str(key)] = deepcopy(value)
    return attach_variant(out, ctx)


def run_116756101(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_116756101(raw)
    expect = seed.get("expect") if isinstance(seed.get("expect"), dict) else {}
    expected_tools = expect.get("tools") if isinstance(expect.get("tools"), list) else []
    if "slack.post_message" in expected_tools and not ctx.env.slack_channel_override:
        raise RuntimeError(f"recipe {RECIPE_ID} requires SLACK_CHANNEL_OVERRIDE for the live Slack error variant")
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
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_116756101(result)
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
    out: dict[str, Any] = {}
    if isinstance(seed.get("snowflake"), dict):
        out.update(ctx.tools.call("harness.snowflake.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
