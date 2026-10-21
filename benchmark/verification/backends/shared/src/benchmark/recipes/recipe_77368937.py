from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_77368937


# Recipe-function "execute(quote_record_id, approval_status, opportunity_id,
# quote_number, owner_email, opportunity_name)": look up the quote owner in
# Slack by email (owner_email with ".invalid" stripped); IF the lookup returned
# an id, DM that user a Block Kit section message. The section text links the
# quote and opportunity through the 'Salesforce Base URL' account property and
# renders the approval status with the inline ternary
# `_dp(approval_status) == "Pending" ? "Submitted" : _dp(approval_status)`.
RECIPE_ID = "77368937"
SEED_TYPE = "recipe_function_quote_approval_dm_variant"
TRACK = "live_slack_recipe_function_quote_dm"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
ACCOUNT_PROPERTY = "Salesforce Base URL"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("slack_bot", "get_user_by_email"),
    ("slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "slack_bot.get_user_by_email",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "slack_bot.get_user_by_email",
    "slack.post_message",
]


def validate_77368937(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    lookup_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if '.gsub(".invalid","")' not in str(lookup_input.get("email") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} owner_email gsub formula changed")
    post_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    blocks = post_input.get("blocks") if isinstance(post_input.get("blocks"), list) else []
    if not blocks or blocks[0].get("block_type") != "section_with_text":
        raise RuntimeError(f"recipe {RECIPE_ID} post_bot_message block kit section changed")
    section_text = str(blocks[0].get("section_text") or "")
    if ACCOUNT_PROPERTY not in section_text:
        raise RuntimeError(f"recipe {RECIPE_ID} section text account property link changed")
    if '== "Pending" ? "Submitted"' not in section_text:
        raise RuntimeError(f"recipe {RECIPE_ID} approval-status ternary changed")
    guard = next(
        (child for child in raw.get("block") or [] if isinstance(child, dict) and child.get("keyword") == "if"),
        None,
    )
    guard_input = guard.get("input") if isinstance(guard, dict) and isinstance(guard.get("input"), dict) else {}
    conditions = guard_input.get("conditions") if isinstance(guard_input.get("conditions"), list) else []
    if guard is None or not conditions or conditions[0].get("operand") != "present":
        raise RuntimeError(f"recipe {RECIPE_ID} slack-id present IF guard changed")
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


def seed_77368937(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_77368937(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters") if isinstance(trigger.get("parameters"), dict) else {}
    for field in ("quote_record_id", "approval_status", "owner_email"):
        if parameters.get(field) in (None, ""):
            raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters.{field} must be non-empty")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    account_properties = seed_in.get("account_properties")
    if not isinstance(account_properties, dict) or account_properties.get(ACCOUNT_PROPERTY) in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.account_properties['{ACCOUNT_PROPERTY}']")
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


def run_77368937(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_77368937(raw)
    if any(tool.startswith("slack.") for tool in ALLOWED_TOOLS):
        if not ctx.env.slack_channel_override:
            raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    if not isinstance(seed.get("account_properties"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing account_properties")
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
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_77368937(result)
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
    if isinstance(seed.get("workato_db_table"), dict):
        out.update(ctx.tools.call("harness.workato_db_table.snapshot", {}))
    if isinstance(seed.get("lookup_table"), dict):
        out.update(ctx.tools.call("harness.lookup_table.snapshot", {}))
    if isinstance(seed.get("salesforce_live"), dict):
        out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
