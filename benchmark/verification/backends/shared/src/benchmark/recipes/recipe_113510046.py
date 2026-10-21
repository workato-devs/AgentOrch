from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_113510046


RECIPE_ID = "113510046"
SEED_TYPE = "live_salesforce_benchmark_variant"
TRACK = "live_salesforce"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_variable", "declare_variable"),
    ("workato_variable", "update_variables"),
    ("workato_variable", "declare_variable"),
    ("salesforce", "search_sobjects"),
    ("workato_variable", "update_variables"),
    ("salesforce", "search_sobjects"),
    ("workato_recipe_function", "return_result"),
    ("workato_recipe_function", "return_result"),
    ("workato_variable", "declare_variable"),
    ("workato_variable", "update_variables"),
    ("salesforce", "search_sobjects_soql"),
    ("workato_recipe_function", "return_result"),
    ("workato_recipe_function", "return_result"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "workato_runtime.update_variables",
    "workato_runtime.declare_variable",
    "salesforce.search_records",
    "workato_runtime.update_variables",
    "salesforce.search_records",
    "workato_recipe_function.return_result",
    "workato_recipe_function.return_result",
    "workato_runtime.declare_variable",
    "workato_runtime.update_variables",
    "salesforce.search_records",
    "workato_recipe_function.return_result",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = ["salesforce.search_records", "workato_recipe_function.return_result"]


def validate_113510046(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
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


def seed_113510046(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_113510046(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    salesforce_seed = seed_in.get("salesforce")
    if not isinstance(salesforce_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires a salesforce seed object")
    provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": salesforce_seed})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    snapshot = deepcopy(provision.get("snapshot") or {})
    replacements = _snapshot_replacements(snapshot)
    trigger = _replace_tokens(trigger_input(ctx), replacements)
    _require_no_tokens(trigger)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") or {}),
        "raw_validation": validation,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": snapshot,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_113510046(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_113510046(raw)
    initial_snapshot = ctx.tools.call("harness.salesforce.snapshot", {})
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = ctx.tools.call("harness.salesforce.snapshot", {})
    finally:
        # Cleanup runs even when replay crashes: leaked benchmark-owned live
        # records would poison later runs (benchmark cleanup policy cleanup
        # principle). On success the snapshot above is captured first.
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
    result["verifier"] = verify_113510046(result)
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


def _snapshot_replacements(snapshot: dict[str, Any]) -> dict[str, str]:
    replacements: dict[str, str] = {}
    first_user = _first_record(snapshot, "User")
    if first_user:
        fields = first_user.get("fields") if isinstance(first_user.get("fields"), dict) else {}
        replacements["$USER_ID"] = str(first_user.get("id") or fields.get("Id") or "")
        replacements["$USER_EMAIL"] = str(fields.get("Email") or fields.get("Username") or "")
    first_opportunity = _first_record(snapshot, "Opportunity")
    if first_opportunity:
        fields = first_opportunity.get("fields") if isinstance(first_opportunity.get("fields"), dict) else {}
        replacements["$OPPORTUNITY_ID"] = str(first_opportunity.get("id") or fields.get("Id") or "")
        replacements["$OPPORTUNITY_NAME"] = str(fields.get("Name") or "")
    first_account = _first_record(snapshot, "Account")
    if first_account:
        fields = first_account.get("fields") if isinstance(first_account.get("fields"), dict) else {}
        replacements["$ACCOUNT_ID"] = str(first_account.get("id") or fields.get("Id") or "")
    return replacements


def _first_record(snapshot: dict[str, Any], sobject: str) -> dict[str, Any] | None:
    records = ((snapshot.get("salesforce") or {}).get("records") or [])
    for record in records:
        if isinstance(record, dict) and record.get("sobject") == sobject:
            return record
    return None


def _replace_tokens(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_tokens(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_tokens(item, replacements) for item in value]
    if isinstance(value, str):
        out = value
        for token, replacement in replacements.items():
            out = out.replace(token, replacement)
        return out
    return value


def _require_no_tokens(value: Any) -> None:
    if isinstance(value, dict):
        for item in value.values():
            _require_no_tokens(item)
        return
    if isinstance(value, list):
        for item in value:
            _require_no_tokens(item)
        return
    if isinstance(value, str) and "$" in value:
        raise RuntimeError(f"recipe {RECIPE_ID} unresolved trigger token: {value}")


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
