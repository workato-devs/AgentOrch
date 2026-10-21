from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_87410086


RECIPE_ID = '87410086'
SEED_TYPE = 'final_state_benchmark_variant'
TRACK = 'benchmark_final_state'
TRIGGER_PROVIDER = 'salesforce'
TRIGGER_NAME = 'new_custom_object'
EXPECTED_ACTIONS: list[tuple[str, str]] = [('salesforce', 'search_sobjects_soql'), ('slack_bot', 'post_bot_message')]
EXPECTED_RAW_TOOLS: list[str] = ['salesforce.search_records', 'slack.post_message']
ALLOWED_TOOLS: list[str] = ['salesforce.search_records', 'slack.post_message']


def validate_87410086(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("filter") is not None:
        # The Closed-Won / Forecast_ARR__c narrowing lives in the trigger's
        # CONFIG-TIME SOQL query; a runtime filter appearing here would change
        # execution semantics and must be re-triaged.
        raise RuntimeError(f"recipe {RECIPE_ID} unexpectedly grew a runtime trigger filter")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
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


def seed_87410086(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_87410086(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "raw_validation": validation,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    refs: dict[str, str] = {}
    if isinstance(seed_in.get("salesforce"), dict):
        provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": seed_in["salesforce"]})
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
        refs = _seed_refs(provision)
        trigger = _replace_value(trigger, refs)
        out["trigger"] = trigger
        out["salesforce_live"] = deepcopy(provision["state"])
        out["salesforce_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
    if isinstance(data.get("expect"), dict):
        # The IF-true Slack alert renders the LIVE CreatedBy.Name of the
        # seeded history row; the harness creates that row as the integration
        # (current) user, so $USER_NAME threads the live name into expect.
        out["expect"] = _replace_value(deepcopy(data["expect"]), refs)
    for key, value in seed_in.items():
        if isinstance(value, dict):
            out[str(key)] = deepcopy(value)
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    for key in ("force_action_error", "job_context"):
        if isinstance(data.get(key), dict):
            out[key] = deepcopy(data[key])
    return attach_variant(out, ctx)


def run_87410086(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_87410086(raw)
    if any(tool.startswith("slack.") for tool in ALLOWED_TOOLS):
        if not ctx.env.slack_channel_override:
            raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    initial_snapshot = _snapshot(ctx, seed)
    cleanup_response: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        if isinstance(seed.get("salesforce_live"), dict):
            cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
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
            "cleanup_response": cleanup_response,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_87410086(result)
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


def _seed_refs(provision: dict[str, Any]) -> dict[str, str]:
    state = provision.get("state") if isinstance(provision.get("state"), dict) else {}
    refs: dict[str, str] = {}
    for row in state.get("read_only_records") or []:
        if not isinstance(row, dict) or str(row.get("logical_sobject") or "") != "User":
            continue
        fields = row.get("fields") if isinstance(row.get("fields"), dict) else {}
        user_id = str(row.get("id") or "")
        user_name = str(fields.get("Name") or "")
        if not user_id or not user_name:
            raise RuntimeError(f"recipe {RECIPE_ID} current-user seed returned no live id/name: {row}")
        refs["$USER_ID"] = user_id
        refs["$USER_NAME"] = user_name
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    records = ((snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}) or {}).get("records") or []
    for record in records:
        if not isinstance(record, dict) or not record.get("id") or record.get("read_only"):
            continue
        if str(record.get("sobject") or "") == "OpportunityFieldHistory":
            refs.setdefault("$HISTORY_ID", str(record.get("id") or ""))
    return refs


def _replace_value(value: Any, refs: dict[str, str]) -> Any:
    if not refs:
        return value
    if isinstance(value, dict):
        return {key: _replace_value(item, refs) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_value(item, refs) for item in value]
    if isinstance(value, str):
        out = value
        for token, replacement in refs.items():
            out = out.replace(token, replacement)
        return out
    return value


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
