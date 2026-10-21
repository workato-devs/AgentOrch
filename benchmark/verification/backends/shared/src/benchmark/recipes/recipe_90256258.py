from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_90256258

RECIPE_ID = "90256258"
SEED_TYPE = "slack_bot_snowflake_phone_request_rejection_variant"
TRACK = "live_slack_live_snowflake_bot_command"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"

# Depth-first action order collected from the raw recipe (steps 3,4,5,6,8,9,10,11,13,15).
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("slack_bot", "post_bot_message"),
    ("workato_variable", "declare_variable"),
    ("snowflake", "search_rows_sql"),
    ("slack", "get_user_by_email"),
    ("slack", "get_user_by_email"),
    ("workato_list", "accumulate_list_items"),
    ("slack_bot", "post_bot_message"),
    ("snowflake", "update_rows"),
    ("slack_bot", "post_bot_message"),
    ("slack_bot", "post_bot_message"),
]

# Trace tool names each action maps to (used as the allow-set for trace tools).
# post_bot_message -> slack.post_message ; slack.get_user_by_email -> slack_bot.get_user_by_email ;
# declare_variable/accumulate_list_items are Workato-internal runtime tools (never in tool_calls).
EXPECTED_RAW_TOOLS: list[str] = [
    "slack.post_message",
    "workato_runtime.declare_variable",
    "snowflake.search_rows_sql",
    "slack_bot.get_user_by_email",
    "slack_bot.get_user_by_email",
    "workato_runtime.accumulate_list_items",
    "slack.post_message",
    "snowflake.update_rows",
    "slack.post_message",
    "slack.post_message",
]

# Unique live tool names the recipe may call (Workato-internal runtime tools excluded on purpose).
ALLOWED_TOOLS: list[str] = [
    "slack.post_message",
    "slack_bot.get_user_by_email",
    "snowflake.search_rows_sql",
    "snowflake.update_rows",
]


def validate_90256258(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual = [(a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": [
            {"number": a.get("number"), "provider": a.get("provider"), "name": a.get("name"), "as": a.get("as")}
            for a in actions
        ],
    }


def seed_90256258(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_90256258(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    seed_in = data.get("seed") if isinstance(data.get("seed"), dict) else {}
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    # LIVE Snowflake provisioning: create/replace the phone-request tables the
    # recipe reads (JOIN source under the connection schema) and writes
    # (PUBLIC.PHONE_REQ_LOG update target).
    snowflake_seed = seed_in.get("snowflake_live")
    if not isinstance(snowflake_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.snowflake_live")
    provision = ctx.tools.call("harness.snowflake_live.seed_tables", {"snowflake": snowflake_seed})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    out["snowflake_live"] = deepcopy(provision["state"])
    out["snowflake_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
    if isinstance(data.get("expect"), dict):
        out["expect"] = deepcopy(data["expect"])
    for key, value in seed_in.items():
        if key == "snowflake_live":
            continue
        if isinstance(value, dict):
            out[str(key)] = deepcopy(value)
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    for key in ("force_action_error", "job_context"):
        if isinstance(data.get(key), dict):
            out[key] = deepcopy(data[key])
    return attach_variant(out, ctx)


def run_90256258(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_90256258(raw)
    if any(t.startswith("slack.") for t in ALLOWED_TOOLS) and not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    snowflake_cleanup: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        if isinstance(seed.get("snowflake_live"), dict):
            snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
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
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "cleanup_response": {"snowflake_live": snowflake_cleanup},
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_90256258(result)
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
    if isinstance(seed.get("snowflake_live"), dict):
        out.update(ctx.tools.call("harness.snowflake.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
