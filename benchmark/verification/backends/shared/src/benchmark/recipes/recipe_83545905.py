from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_83545905
from .salesforce_recipe_utils import replace_tokens

RECIPE_ID = "83545905"
SEED_TYPE = "salesforce_campaign_activity_unqualify_try_catch_variant"
TRACK = "live_salesforce_slack_bot_try_catch"
TRIGGER_PROVIDER = "salesforce"
TRIGGER_NAME = "new_custom_object"
SOBJECT = "Campaign_Activity__c"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("clock", "wait_for_interval"),
    ("salesforce", "update_sobject"),
    ("slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "clock.wait_for_interval",
    "salesforce.update_record",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "clock.wait_for_interval",
    "salesforce.update_record",
    "slack.post_message",
]


def validate_83545905(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual = [(a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    update_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    if str(update_input.get("sobject_name") or "") != SOBJECT or str(update_input.get("Stage__c") or "") != "Unqualified":
        raise RuntimeError(f"recipe {RECIPE_ID} update mapping changed: {update_input}")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME,
            "actions": [{"number": a.get("number"), "provider": a.get("provider"),
                         "name": a.get("name"), "as": a.get("as")} for a in actions]}


def seed_83545905(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_83545905(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    trigger = trigger_input(ctx)
    seed_in = data.get("seed") if isinstance(data.get("seed"), dict) else {}
    if not isinstance(seed_in.get("salesforce"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce")
    provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": seed_in["salesforce"]})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    # Explicit seed-reference binding ($<REF>_ID, recipe_122139155/62905310
    # precedent): the variant input must carry the token itself — no implicit
    # overwrite of a placeholder trigger field.
    refs = _seed_ref_tokens(seed_in["salesforce"], provision)
    parent = trigger.get("Parent") if isinstance(trigger.get("Parent"), dict) else {}
    parent_token = str(parent.get("Id") or "")
    if not (parent_token.startswith("$") and parent_token.endswith("_ID")):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger Parent.Id must be an explicit $<REF>_ID "
            f"seed-reference token, got {parent_token!r}"
        )
    if parent_token not in refs:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger Parent.Id token {parent_token!r} has no "
            f"seeded record ref; available tokens: {sorted(refs)}"
        )
    trigger = replace_tokens(trigger, refs)
    if trigger.get("NewValue") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing NewValue (region filter)")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID, "seed_type": SEED_TYPE, "trigger": trigger,
        "track": data.get("track"), "raw_validation": validation,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if isinstance(data.get("expect"), dict):
        out["expect"] = deepcopy(data["expect"])
    if isinstance(data.get("force_action_error"), dict):
        out["force_action_error"] = deepcopy(data["force_action_error"])
    return attach_variant(out, ctx)


def run_83545905(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_83545905(raw)
    if any(t.startswith("slack.") for t in ALLOWED_TOOLS) and not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    initial_snapshot = _snapshot(ctx, seed)
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        if isinstance(seed.get("salesforce_live"), dict):
            ctx.tools.call("harness.salesforce.cleanup", {})
    result = recipe_result(
        recipe_id=RECIPE_ID, ok=True, track=TRACK, ctx=ctx,
        details={"seed_type": seed.get("seed_type"), "trigger": seed.get("trigger"),
                 "track": seed.get("track"),
                 "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
                 "raw_validation": validation, "raw_execution": raw_execution,
                 "expected_raw_tools": EXPECTED_RAW_TOOLS,
                 "initial_snapshot": initial_snapshot, "final_snapshot": final_snapshot,
                 "ground_truth": _ground_truth(raw_execution)},
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_83545905(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _seed_ref_tokens(salesforce_seed: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    """$<REF>_ID tokens for every seeded record carrying a ref name, zipped
    seed-order to provisioned snapshot order (recipe_122139155/62905310
    precedent). Fail-fast on any seed/snapshot mismatch — a silent partial map
    would let a variant pin the wrong live id."""
    seed_records = [record for record in salesforce_seed.get("records") or [] if isinstance(record, dict)]
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    owned = [
        record for record in salesforce_snapshot.get("records") or []
        if isinstance(record, dict) and not record.get("read_only")
    ]
    if len(owned) != len(seed_records):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed/snapshot record count mismatch: "
            f"{len(seed_records)} seeded vs {len(owned)} provisioned"
        )
    refs: dict[str, str] = {}
    for seed_record, live in zip(seed_records, owned):
        ref = str(seed_record.get("ref") or "").strip()
        live_id = str(live.get("id") or "")
        if ref and not live_id:
            raise RuntimeError(f"recipe {RECIPE_ID} provisioned record for ref {ref!r} has no live id")
        if ref:
            refs[f"${ref.upper()}_ID"] = live_id
    return refs


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
    if isinstance(seed.get("salesforce_live"), dict):
        out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
