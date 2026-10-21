from __future__ import annotations

from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, require_seed_section, trigger_input, variant_data
from ..verifier import verify_50816215


RECIPE_ID = "50816215"
TABLE_ID = "1889440"


def validate_50816215(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("provider") != "namely_connector_1672048_1686316621" or raw.get("name") != "new_job_title":
        raise RuntimeError("recipe 50816215 has unexpected trigger")
    actions = _collect_actions(raw)
    names = {(action.get("provider"), action.get("name")) for action in actions}
    expected = {
        ("lookup_table", "search_entries"),
        ("lookup_table", "add_entry"),
        ("lookup_table", "update_entry"),
    }
    if not expected.issubset(names):
        raise RuntimeError("recipe 50816215 missing expected lookup-table actions")
    table_ids = {
        (action.get("input") or {}).get("lookup_table_id")
        for action in actions
        if action.get("provider") == "lookup_table"
    }
    if table_ids != {TABLE_ID}:
        raise RuntimeError("recipe 50816215 has unexpected lookup table")
    return {"actions": actions}


def seed_50816215(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    action = validate_50816215(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if not trigger:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing trigger_input")
    lookup_seed = require_seed_section(ctx, "lookup_table")
    return attach_variant({
        "recipe_id": RECIPE_ID,
        "seed_type": "namely_new_job_title_trigger",
        "trigger": trigger,
        "lookup_table": lookup_seed,
        "raw_action": action,
        "harness_tool_calls": ctx.tools.call_log(),
    }, ctx)


def run_50816215(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    action = validate_50816215(raw)
    trigger = seed.get("trigger")
    if not isinstance(trigger, dict):
        raise RuntimeError("seed file missing Namely trigger")

    expected_record = _expected_record(trigger)
    search_params = {"col1": expected_record["col1"]}
    initial_snapshot = ctx.tools.call("harness.lookup_table.snapshot", {})
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    search_call = _raw_step(raw_execution, "lookup_table.search_entries")
    add_call = _raw_step(raw_execution, "lookup_table.add_entry")
    update_call = _raw_step(raw_execution, "lookup_table.update_entry")
    write_call = add_call or update_call
    search_args = search_call.get("args") if isinstance(search_call.get("args"), dict) else {}
    search = search_call.get("result") if isinstance(search_call.get("result"), dict) else {}
    write_args = write_call.get("args") if isinstance(write_call.get("args"), dict) else {}
    write_response = write_call.get("result") if isinstance(write_call.get("result"), dict) else {}
    write_tool = str(write_call.get("tool") or "")
    final_snapshot = ctx.tools.call("harness.lookup_table.snapshot", {})

    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track="mock_lookup_table_search_then_write",
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": trigger,
            "expected_table_id": TABLE_ID,
            "search_params": search_args.get("parameters") or search_params,
            "expected_record": expected_record,
            "write_tool": write_tool,
            "write_args": write_args,
            "initial_snapshot": initial_snapshot,
            "search_response": search,
            "write_response": write_response,
            "final_snapshot": final_snapshot,
            "raw_execution": raw_execution,
            "expect": (seed.get("variant_input") or {}).get("expect") or {},
            "raw_action": action,
        },
        allowed_tools=["lookup_table.search_entries", "lookup_table.add_entry", "lookup_table.update_entry"],
    )
    result["verifier"] = verify_50816215(result)
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


def _expected_record(trigger: dict[str, Any]) -> dict[str, Any]:
    return {
        "col1": str(trigger.get("id") or ""),
        "col2": str(trigger.get("title") or ""),
        "col3": str(trigger.get("active") or ""),
    }


def _raw_step(raw_execution: dict[str, Any], tool: str) -> dict[str, Any]:
    for row in raw_execution.get("trace") or []:
        if row.get("tool") == tool:
            return row if isinstance(row, dict) else {}
    return {}
