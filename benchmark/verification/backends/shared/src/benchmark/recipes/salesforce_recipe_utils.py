from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result


Verifier = Callable[[dict[str, Any]], dict[str, Any]]


def collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(collect_actions(child))
    return found


def seed_salesforce_state(recipe_id: str, data: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {recipe_id} variant input missing seed object")
    salesforce_seed = seed_in.get("salesforce")
    if not isinstance(salesforce_seed, dict):
        raise RuntimeError(f"recipe {recipe_id} requires seed.salesforce")
    provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": salesforce_seed})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {recipe_id} Salesforce seed failed: {provision}")
    return provision


def salesforce_refs(provision: dict[str, Any]) -> dict[str, str]:
    refs: dict[str, str] = {}
    records = ((provision.get("snapshot") or {}).get("salesforce") or {}).get("records") or []
    for row in records:
        if not isinstance(row, dict):
            continue
        sobject = str(row.get("sobject") or "").upper()
        record_id = str(row.get("id") or "")
        if sobject and record_id:
            refs.setdefault(f"${sobject}_ID", record_id)
            refs.setdefault("$RECORD_ID", record_id)
        fields = row.get("fields") if isinstance(row.get("fields"), dict) else {}
        email = str(fields.get("Email") or fields.get("Username") or "")
        if sobject == "USER":
            refs.setdefault("$USER_ID", record_id)
            refs.setdefault("$CURRENT_USER_ID", record_id)
            if email:
                refs.setdefault("$USER_EMAIL", email)
                refs.setdefault("$CURRENT_USER_EMAIL", email)
    return refs


def replace_tokens(value: Any, refs: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: replace_tokens(item, refs) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_tokens(item, refs) for item in value]
    if isinstance(value, str):
        out = value
        for token, replacement in refs.items():
            out = out.replace(token, replacement)
        return out
    return value


def snapshot_salesforce(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    if isinstance(seed.get("salesforce_live"), dict):
        return ctx.tools.call("harness.salesforce.snapshot", {})
    return {}


def ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}


def run_salesforce_recipe(
    *,
    recipe_id: str,
    track: str,
    raw: dict[str, Any],
    seed: dict[str, Any],
    ctx: RecipeContext,
    validation: dict[str, Any],
    expected_raw_tools: list[str],
    allowed_tools: list[str],
    verifier: Verifier,
) -> dict[str, Any]:
    initial_snapshot = snapshot_salesforce(ctx, seed)
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    cleanup_response: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = snapshot_salesforce(ctx, seed)
    finally:
        cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
    if raw_execution is None:
        raise RuntimeError(f"recipe {recipe_id} raw execution did not complete")
    result = recipe_result(
        recipe_id=recipe_id,
        ok=True,
        track=track,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": expected_raw_tools,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "cleanup_response": cleanup_response,
            "account_properties": seed.get("account_properties") if isinstance(seed.get("account_properties"), dict) else {},
            "ground_truth": ground_truth(raw_execution),
        },
        allowed_tools=allowed_tools,
    )
    result["verifier"] = verifier(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def copy_expect(data: dict[str, Any]) -> dict[str, Any]:
    return deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {})
