from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, require_seed_section, trigger_input, variant_data
from ..verifier import verify_50807132


RECIPE_ID = "50807132"
TABLE_ID = "1879301"


def validate_50807132(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("provider") != "salesforce" or raw.get("name") != "new_outbound_message":
        raise RuntimeError("recipe 50807132 has unexpected trigger")
    blocks = raw.get("block") or []
    actions = []
    for block in blocks:
        if isinstance(block, dict):
            actions.extend(_collect_actions(block))
    names = {(action.get("provider"), action.get("name")) for action in actions}
    expected = {
        ("lookup_table", "search_entries"),
        ("lookup_table", "add_entry"),
        ("lookup_table", "update_entry"),
    }
    if not expected.issubset(names):
        raise RuntimeError("recipe 50807132 missing expected lookup-table actions")
    return {"actions": actions}


def seed_50807132(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    action = validate_50807132(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if not trigger:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing trigger_input")
    lookup_seed = require_seed_section(ctx, "lookup_table")
    return attach_variant({
        "recipe_id": RECIPE_ID,
        "seed_type": "salesforce_inactive_user_outbound_message",
        "trigger": trigger,
        "lookup_table": lookup_seed,
        "raw_action": action,
        "harness_tool_calls": ctx.tools.call_log(),
    }, ctx)


def run_50807132(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    action = validate_50807132(raw)
    trigger = seed.get("trigger")
    sobject = (trigger or {}).get("sObject") if isinstance(trigger, dict) else None
    if not isinstance(sobject, dict):
        raise RuntimeError("seed file missing Salesforce sObject trigger")

    search_params = {
        "col1": str(sobject.get("Id") or ""),
        "col2": str(sobject.get("LastModifiedDate") or ""),
        "col3": str(sobject.get("Email") or ""),
    }
    expected_record = _expected_record(sobject)
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
            "ground_truth": _ground_truth(raw_execution),
            "expect": (seed.get("variant_input") or {}).get("expect") or {},
            "raw_action": action,
        },
        allowed_tools=["lookup_table.search_entries", "lookup_table.add_entry", "lookup_table.update_entry"],
    )
    result["verifier"] = verify_50807132(result)
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


def _expected_record(sobject: dict[str, Any]) -> dict[str, Any]:
    modified = str(sobject.get("LastModifiedDate") or "")
    return {
        "col1": str(sobject.get("Id") or ""),
        "col2": modified,
        "col3": str(sobject.get("Email") or ""),
        "col4": str(sobject.get("LastModifiedById") or ""),
        "col5": _plus_14_days(modified),
    }


def _plus_14_days(value: str) -> str:
    if "T" in value:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return (dt + timedelta(days=14)).date().isoformat()
    return (date.fromisoformat(value) + timedelta(days=14)).isoformat()


def _raw_step(raw_execution: dict[str, Any], tool: str) -> dict[str, Any]:
    for row in raw_execution.get("trace") or []:
        if row.get("tool") == tool:
            return row if isinstance(row, dict) else {}
    return {}


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        if not isinstance(row, dict) or not row.get("tool"):
            continue
        by_tool.setdefault(str(row["tool"]), []).append(row)
    return {
        "by_tool": by_tool,
        "return_value": raw_execution.get("return_value"),
    }
