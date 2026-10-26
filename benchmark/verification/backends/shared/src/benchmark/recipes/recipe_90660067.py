from __future__ import annotations

from copy import deepcopy
import json
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_90660067


RECIPE_ID = "90660067"
SEED_TYPE = "xray_access_request_approval_variant"
TRACK = "live_snowflake_lookup_slack_block_update"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"
LOOKUP_TABLE_ID = "3260814"
APPROVAL_BLOCK_ID = "request_approval_block"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("lookup_table", "get_entry"),
    ("workato_variable", "declare_variable"),
    ("snowflake", "run_custom_sql"),
    ("lookup_table", "update_entry"),
    ("snowflake", "run_custom_sql"),
    ("logger", "log_message"),
    ("lookup_table", "update_entry"),
    ("slack_bot", "update_blocks_by_block_id"),
    ("slack_bot", "post_bot_message"),
    ("slack_bot", "update_blocks_by_block_id"),
    ("slack_bot", "post_bot_message"),
    ("lookup_table", "delete_entry"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.get_entry",
    "workato_runtime.declare_variable",
    "snowflake.run_custom_sql",
    "lookup_table.update_entry",
    "workato_runtime.log_message",
    "slack.update_blocks_by_block_id",
    "slack.post_message",
    "lookup_table.delete_entry",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.get_entry",
    "snowflake.run_custom_sql",
    "lookup_table.update_entry",
    "lookup_table.delete_entry",
    "slack.update_blocks_by_block_id",
    "slack.post_message",
]


def validate_90660067(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    get_entry_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if get_entry_input.get("lookup_table_id") != LOOKUP_TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} access-control lookup table changed")
    for sql_action in (actions[2], actions[4]):
        sql_input = sql_action.get("input") if isinstance(sql_action.get("input"), dict) else {}
        if "listagg(account" not in str(sql_input.get("sql") or ""):
            raise RuntimeError(f"recipe {RECIPE_ID} accounts_accessed listagg query changed")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": _action_summary(actions),
    }


def seed_90660067(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_90660067(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")

    trigger = deepcopy(trigger_input(ctx))
    parameters = trigger.get("parameters") if isinstance(trigger.get("parameters"), dict) else {}
    if not isinstance(parameters, dict) or parameters.get("status") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing parameters.status")
    if parameters.get("requestor_email") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing parameters.requestor_email")
    if parameters.get("conversation_id") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing parameters.conversation_id")
    context = trigger.setdefault("context", {})
    if not isinstance(context, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger context must be an object")

    seed_in = data.get("seed") if isinstance(data.get("seed"), dict) else {}
    lookup_seed = seed_in.get("lookup_table")
    if not isinstance(lookup_seed, dict) or LOOKUP_TABLE_ID not in (lookup_seed.get("tables") or {}):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.lookup_table[{LOOKUP_TABLE_ID}]")

    # Seed the live Slack approval message that carries the request_approval_block
    # so update_blocks_by_block_id can edit it in place.
    seed_message = data.get("slack_seed_message") if isinstance(data.get("slack_seed_message"), dict) else {}
    original_text = str(seed_message.get("text") or f"X-Ray access request for {parameters.get('requestor_email')}")
    approval_text = str(
        seed_message.get("approval_block_text")
        or f"Access request pending approval for {parameters.get('requestor_email')}"
    )
    blocks = seed_message.get("blocks")
    if not isinstance(blocks, list):
        blocks = [
            {"type": "section", "block_id": APPROVAL_BLOCK_ID, "text": {"type": "mrkdwn", "text": approval_text}},
            {"type": "divider", "block_id": "request_divider"},
        ]
    posted = ctx.tools.call(
        "harness.slack.seed_message",
        {"channel": ctx.env.slack_channel_override, "text": original_text, "blocks": blocks},
    )
    channel = str(posted.get("channel") or ctx.env.slack_channel_override)
    ts = str(posted.get("ts") or "")
    if not ts:
        raise RuntimeError(f"recipe {RECIPE_ID} Slack seed message returned no ts: {posted}")
    context["original_message_json"] = json.dumps(
        {"channel": channel, "ts": ts, "text": original_text, "blocks": blocks},
        sort_keys=True,
    )

    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "lookup_table": deepcopy(lookup_seed),
        "seed_slack_message": {"channel": channel, "ts": ts, "text": original_text, "blocks": blocks},
        "harness_tool_calls": ctx.tools.call_log(),
    }

    # Only APPROVE variants reach the Snowflake customer-warehouse CTE, so only
    # they provision live Snowflake tables.
    snowflake_seed = seed_in.get("snowflake_live")
    if isinstance(snowflake_seed, dict):
        provision = ctx.tools.call("harness.snowflake_live.seed_tables", {"snowflake": snowflake_seed})
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
        out["snowflake_live"] = deepcopy(provision["state"])
        out["snowflake_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})

    return attach_variant(out, ctx)


def run_90660067(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_90660067(raw)
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    message = seed.get("seed_slack_message") if isinstance(seed.get("seed_slack_message"), dict) else {}
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    snowflake_cleanup: dict[str, Any] | None = None
    slack_cleanup: dict[str, Any] = {}
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        if isinstance(seed.get("snowflake_live"), dict):
            snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
        if message.get("channel") and message.get("ts"):
            slack_cleanup = ctx.tools.call(
                "slack.delete_message",
                {"channel": message["channel"], "ts": message["ts"]},
            )
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
            "cleanup_response": {"snowflake_live": snowflake_cleanup, "slack": slack_cleanup},
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_90660067(result)
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
    if isinstance(seed.get("lookup_table"), dict):
        out.update(ctx.tools.call("harness.lookup_table.snapshot", {}))
    if isinstance(seed.get("snowflake_live"), dict):
        out.update(ctx.tools.call("harness.snowflake.snapshot", {}))
    return out


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"number": a.get("number"), "provider": a.get("provider"), "name": a.get("name"), "as": a.get("as")}
        for a in actions
    ]


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
