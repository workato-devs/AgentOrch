from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_89584039


RECIPE_ID = "89584039"
SEED_TYPE = "sfdc_picklist_sync_lookup_variant"
TRACK = "workato_service_call_service"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "timer"
# 5-minute clock timer -> six independent try/catch blocks. Each block calls a
# callable recipe (flow 45626516) that returns a Salesforce picklist as
# `reply.picklist_value`, then searches a shared Workato lookup table (id
# 3298524) by a config key (col1). When a matching entry exists the block
# UPDATES its col2 with the (optionally .where(...)-filtered) picklist JSON;
# otherwise it ADDS a new entry. On any error the block's catch invokes an
# error-notification callable (flow 45626497). The callable replies are
# deterministic Workato-internal seed state (seed.workato_service_replies keyed
# by each call step's `as` id, since several steps share flow 45626516). The
# lookup table is a Workato-internal mock seeded per variant.
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_service", "call_service"),
    ("lookup_table", "search_entries"),
    ("lookup_table", "update_entry"),
    ("lookup_table", "add_entry"),
    ("lookup_table", "search_entries"),
    ("lookup_table", "update_entry"),
    ("lookup_table", "add_entry"),
    ("lookup_table", "search_entries"),
    ("lookup_table", "update_entry"),
    ("lookup_table", "add_entry"),
    ("workato_service", "call_service"),
    ("workato_service", "call_service"),
    ("lookup_table", "search_entries"),
    ("lookup_table", "update_entry"),
    ("lookup_table", "add_entry"),
    ("workato_service", "call_service"),
    ("workato_service", "call_service"),
    ("lookup_table", "search_entries"),
    ("lookup_table", "update_entry"),
    ("lookup_table", "add_entry"),
    ("workato_service", "call_service"),
    ("workato_service", "call_service"),
    ("lookup_table", "search_entries"),
    ("lookup_table", "update_entry"),
    ("lookup_table", "add_entry"),
    ("workato_service", "call_service"),
    ("workato_service", "call_service"),
    ("lookup_table", "search_entries"),
    ("lookup_table", "update_entry"),
    ("lookup_table", "add_entry"),
    ("workato_service", "call_service"),
    ("workato_service", "call_service"),
    ("lookup_table", "search_entries"),
    ("lookup_table", "update_entry"),
    ("lookup_table", "add_entry"),
    ("workato_service", "call_service"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_service.call_service",
    "lookup_table.search_entries",
    "lookup_table.update_entry",
    "lookup_table.add_entry",
]
ALLOWED_TOOLS: list[str] = [
    "workato_service.call_service",
    "lookup_table.search_entries",
    "lookup_table.update_entry",
    "lookup_table.add_entry",
]


def validate_89584039(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual = [(a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": [
            {
                "number": a.get("number"),
                "provider": a.get("provider"),
                "name": a.get("name"),
                "as": a.get("as"),
            }
            for a in actions
        ],
    }


def seed_89584039(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_89584039(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    seed_in = data.get("seed") if isinstance(data.get("seed"), dict) else {}
    if not isinstance(seed_in.get("workato_service_replies"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires seed.workato_service_replies for the call_service steps"
        )
    if not isinstance(seed_in.get("lookup_table"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires seed.lookup_table (Workato-internal lookup mock)"
        )
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


def run_89584039(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_89584039(raw)
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
    result["verifier"] = verify_89584039(result)
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
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
