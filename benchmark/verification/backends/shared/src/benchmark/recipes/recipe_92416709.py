from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data, variant_index
from ..verifier import verify_92416709


RECIPE_ID = "92416709"
SEED_TYPE = "slack_bot_command_delete_pending_check_variant"
TRACK = "workato_lookup_slack_delete_original"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"
LOOKUP_TABLE_ID = "2343001"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("lookup_table", "search_entries"),
    ("lookup_table", "delete_entry"),
    ("slack_bot", "post_bot_reply_v2"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "lookup_table.delete_entry",
    "slack.post_reply",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "lookup_table.delete_entry",
    "slack.post_reply",
]


def validate_92416709(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    search_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if search_input.get("lookup_table_id") != LOOKUP_TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} search lookup table changed")
    search_params = search_input.get("parameters") if isinstance(search_input.get("parameters"), dict) else {}
    if "col3" not in search_params or "col4" not in search_params:
        raise RuntimeError(f"recipe {RECIPE_ID} search parameters changed (expected col3+col4)")
    delete_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    if delete_input.get("lookup_table_id") != LOOKUP_TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} delete lookup table changed")
    reply_input = actions[2].get("input") if isinstance(actions[2].get("input"), dict) else {}
    if str(reply_input.get("delete_original")).lower() != "true":
        raise RuntimeError(f"recipe {RECIPE_ID} post_bot_reply_v2 is not delete_original=true")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_92416709(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_92416709(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    channel = ctx.env.slack_channel_override
    if not channel:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    seed_in = data.get("seed") if isinstance(data.get("seed"), dict) else {}

    # Live-seed the customer-record prompt message so the recipe has a real
    # message to delete (delete_original). Its ts is the message reference the
    # bot command targets.
    idx = variant_index(ctx)
    seed_text = f"benchmark seed for recipe {RECIPE_ID} variant {idx:02d}: pending customer-record check prompt"
    posted = ctx.tools.call("harness.slack.seed_message", {"channel": channel, "text": seed_text})
    actual_channel = str(posted.get("channel") or channel)
    ts = posted.get("ts")
    if not ts:
        raise RuntimeError(f"recipe {RECIPE_ID} Slack chat.postMessage returned no ts: {posted}")
    ts = str(ts)

    # The pending-check entry for THIS conversation+message: col3=channel, col4=ts.
    target = seed_in.get("target") if isinstance(seed_in.get("target"), dict) else {}
    target_row = {
        "col1": str(target.get("col1") or ""),
        "col2": str(target.get("col2") or ""),
        "col3": actual_channel,
        "col4": ts,
    }
    decoys = seed_in.get("decoys") if isinstance(seed_in.get("decoys"), list) else []
    rows: list[dict[str, Any]] = []
    for decoy in decoys:
        if not isinstance(decoy, dict):
            continue
        row = {str(key): str(value) for key, value in decoy.items()}
        # keep a decoy in the same live channel realistic, but never matching the
        # target message ts (so the search filter selects only the target row).
        if str(row.get("col3") or "").strip().lower() in {"", "$channel"}:
            row["col3"] = actual_channel
        if str(row.get("col4") or "") == ts:
            raise RuntimeError(f"recipe {RECIPE_ID} decoy row collides with target message ts")
        rows.append(row)
    rows.append(target_row)

    trigger = trigger_input(ctx)
    context = trigger.get("context") if isinstance(trigger.get("context"), dict) else {}
    context["channel"] = actual_channel
    trigger["context"] = context
    trigger["ts"] = ts

    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "lookup_table": {"tables": {LOOKUP_TABLE_ID: rows}},
        "message": {"channel": actual_channel, "ts": ts, "text": seed_text},
        "target_entry": {"col3": actual_channel, "col4": ts},
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_92416709(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_92416709(raw)
    if any(tool.startswith("slack.") for tool in ALLOWED_TOOLS) and not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    message = seed.get("message") if isinstance(seed.get("message"), dict) else {}
    if not message.get("channel") or not message.get("ts"):
        raise RuntimeError(f"recipe {RECIPE_ID} seed missing live message channel/ts")
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
            "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "seed_message": deepcopy(message),
            "target_entry": deepcopy(seed.get("target_entry") if isinstance(seed.get("target_entry"), dict) else {}),
            "lookup_table_id": LOOKUP_TABLE_ID,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_92416709(result)
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
    if isinstance(seed.get("lookup_table"), dict):
        return ctx.tools.call("harness.lookup_table.snapshot", {})
    return {}


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
