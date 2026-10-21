from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from .salesforce_recipe_utils import replace_tokens


Verifier = Callable[[dict[str, Any]], dict[str, Any]]


def seed_live_snowflake(recipe_id: str, data: dict[str, Any], ctx: RecipeContext, refs: dict[str, str] | None = None) -> dict[str, Any]:
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {recipe_id} variant input missing seed object")
    snowflake_seed = seed_in.get("snowflake_live")
    if not isinstance(snowflake_seed, dict):
        raise RuntimeError(f"recipe {recipe_id} requires seed.snowflake_live")
    if refs:
        snowflake_seed = replace_tokens(deepcopy(snowflake_seed), refs)
    provision = ctx.tools.call("harness.snowflake_live.seed_tables", {"snowflake": snowflake_seed})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {recipe_id} live Snowflake seed failed: {provision}")
    return provision


def seed_workato_db_section(recipe_id: str, data: dict[str, Any]) -> dict[str, Any]:
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or not isinstance(seed_in.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {recipe_id} variant input missing seed.workato_db_table")
    return deepcopy(seed_in["workato_db_table"])


def snowflake_seed_base(
    *,
    recipe_id: str,
    seed_type: str,
    track: str,
    validation: dict[str, Any],
    ctx: RecipeContext,
    snowflake_state: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {recipe_id} requires explicit benchmark-local variant input")
    out: dict[str, Any] = {
        "recipe_id": recipe_id,
        "seed_type": seed_type,
        "trigger": trigger_input(ctx),
        "track": data.get("track") or track,
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "snowflake_live": deepcopy(snowflake_state),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if extra:
        out.update(extra)
    return attach_variant(out, ctx)


def run_live_snowflake_recipe(
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
    include_workato_db: bool = False,
    include_salesforce: bool = False,
) -> dict[str, Any]:
    initial_snapshot = _snapshot(ctx, seed, include_workato_db, include_salesforce)
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    snowflake_cleanup: dict[str, Any] | None = None
    salesforce_cleanup: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed, include_workato_db, include_salesforce)
    finally:
        if isinstance(seed.get("snowflake_live"), dict):
            snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
        if include_salesforce and isinstance(seed.get("salesforce_live"), dict):
            salesforce_cleanup = ctx.tools.call("harness.salesforce.cleanup", {})
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
            "cleanup_response": {
                "snowflake_live": snowflake_cleanup,
                "salesforce": salesforce_cleanup,
            },
            "ground_truth": ground_truth(raw_execution),
        },
        allowed_tools=allowed_tools,
    )
    result["verifier"] = verifier(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}


def _snapshot(ctx: RecipeContext, seed: dict[str, Any], include_workato_db: bool, include_salesforce: bool) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("snowflake_live"), dict):
        out.update(ctx.tools.call("harness.snowflake.snapshot", {}))
    if include_workato_db and isinstance(seed.get("workato_db_table"), dict):
        out.update(ctx.tools.call("harness.workato_db_table.snapshot", {}))
    if include_salesforce and isinstance(seed.get("salesforce_live"), dict):
        out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
    return out
