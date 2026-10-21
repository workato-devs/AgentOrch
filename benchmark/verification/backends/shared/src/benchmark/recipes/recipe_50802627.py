from __future__ import annotations

from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, require_seed_section, trigger_input, variant_data
from ..verifier import verify_50802627


RECIPE_ID = "50802627"
EXPENSE_TABLE_ID = "1840273"
BENEFITS_TABLE_ID = "1840262"


def validate_50802627(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("provider") != "workato_recipe_function" or raw.get("name") != "execute":
        raise RuntimeError("recipe 50802627 has unexpected trigger")
    blocks = raw.get("block") or []
    if len(blocks) != 2 or blocks[0].get("keyword") != "if":
        raise RuntimeError("recipe 50802627 has unexpected control flow")
    update_blocks = _collect_actions(blocks[0])
    update_ids = {
        (block.get("input") or {}).get("lookup_table_id")
        for block in update_blocks
        if block.get("provider") == "lookup_table" and block.get("name") == "update_entry"
    }
    if update_ids != {EXPENSE_TABLE_ID, BENEFITS_TABLE_ID}:
        raise RuntimeError("recipe 50802627 missing expected lookup-table updates")
    if blocks[1].get("provider") != "workato_recipe_function" or blocks[1].get("name") != "return_result":
        raise RuntimeError("recipe 50802627 missing return_result action")
    return {"branch": blocks[0], "return": blocks[1]}


def seed_50802627(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    action = validate_50802627(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if not trigger:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing trigger_input")
    lookup_seed = require_seed_section(ctx, "lookup_table")
    return attach_variant({
        "recipe_id": RECIPE_ID,
        "seed_type": "workato_recipe_function_claim_update",
        "trigger": trigger,
        "lookup_table": lookup_seed,
        "raw_action": action,
        "harness_tool_calls": ctx.tools.call_log(),
    }, ctx)


def run_50802627(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    action = validate_50802627(raw)
    trigger = seed.get("trigger")
    if not isinstance(trigger, dict) or not isinstance(trigger.get("parameters"), dict):
        raise RuntimeError("seed file missing trigger parameters")
    params = trigger["parameters"]

    initial_snapshot = ctx.tools.call("harness.lookup_table.snapshot", {})
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    update_call = _raw_step(raw_execution, "lookup_table.update_entry")
    update_args = update_call.get("args") if isinstance(update_call.get("args"), dict) else {}
    updated = update_call.get("result") if isinstance(update_call.get("result"), dict) else {}
    final_snapshot = ctx.tools.call("harness.lookup_table.snapshot", {})
    updated_entry = updated.get("entry") if isinstance(updated.get("entry"), dict) else {}
    returned_result = raw_execution.get("return_value") if isinstance(raw_execution.get("return_value"), dict) else {}
    table_id = str(update_args.get("lookup_table_id") or "")
    entry_id = str(update_args.get("id") or params.get("entry_id") or "")

    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track="mock_lookup_table_update",
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": trigger,
            "selected_table_id": table_id,
            "untouched_table_id": BENEFITS_TABLE_ID if table_id == EXPENSE_TABLE_ID else EXPENSE_TABLE_ID,
            "entry_id": entry_id,
            "expected_update": update_args.get("parameters") or _update_params(params),
            "expected_entry": updated_entry,
            "returned_result": returned_result,
            "initial_snapshot": initial_snapshot,
            "update_response": updated,
            "final_snapshot": final_snapshot,
            "raw_execution": raw_execution,
            "expect": (seed.get("variant_input") or {}).get("expect") or {},
            "raw_action": action,
        },
        allowed_tools=["lookup_table.update_entry", "workato_recipe_function.return_result"],
    )
    result["verifier"] = verify_50802627(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action":
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _update_params(params: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "channel_permalink": "col10",
        "remarks": "col2",
        "final_approved_amt": "col6",
        "status": "col7",
        "receipt_link": "col8",
    }
    out: dict[str, Any] = {}
    for source, target in mapping.items():
        value = params.get(source)
        if value not in (None, ""):
            out[target] = value
    return out


def _raw_step(raw_execution: dict[str, Any], tool: str) -> dict[str, Any]:
    for row in raw_execution.get("trace") or []:
        if row.get("tool") == tool:
            return row if isinstance(row, dict) else {}
    return {}
