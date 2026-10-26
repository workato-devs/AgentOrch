from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_59797915


RECIPE_ID = "59797915"
SEED_TYPE = "netsuite_employee_lookup_table_split_sync_variant"
TRACK = "netsuite_lookup_table_employee_sync"
TRIGGER_PROVIDER = "netsuite"
TRIGGER_NAME = "updated_object"
TABLE_IDS = ("2342993", "2342994", "2342995")
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("lookup_table", "search_entries"),
    ("lookup_table", "update_entry"),
    ("lookup_table", "add_entry"),
    ("lookup_table", "search_entries"),
    ("lookup_table", "update_entry"),
    ("lookup_table", "add_entry"),
    ("lookup_table", "search_entries"),
    ("lookup_table", "update_entry"),
    ("lookup_table", "add_entry"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "lookup_table.update_entry",
    "lookup_table.add_entry",
]
ALLOWED_TOOLS: list[str] = EXPECTED_RAW_TOOLS
REQUIRED_TRIGGER_FIELDS = (
    "internal_id",
    "entityId",
    "email",
    "firstName",
    "lastName",
    "isInactive",
    "hireDate",
    "releaseDate",
    "title",
    "supervisor",
    "department",
    "subsidiary",
    "employeeStatus",
    "location",
    "employeeType",
    "currency",
)


def validate_59797915(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    raw_input = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    if not str(raw_input.get("netsuite_object") or "").startswith("Employee"):
        raise RuntimeError(f"recipe {RECIPE_ID} NetSuite object changed")
    actions = _collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    expected_tables = [TABLE_IDS[0], TABLE_IDS[0], TABLE_IDS[0], TABLE_IDS[1], TABLE_IDS[1], TABLE_IDS[1], TABLE_IDS[2], TABLE_IDS[2], TABLE_IDS[2]]
    for action, table_id in zip(actions, expected_tables):
        action_input = action.get("input") if isinstance(action.get("input"), dict) else {}
        if str(action_input.get("lookup_table_id") or "") != table_id:
            raise RuntimeError(f"recipe {RECIPE_ID} lookup table mapping changed")
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


def seed_59797915(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_59797915(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    for field in REQUIRED_TRIGGER_FIELDS:
        if field not in trigger:
            raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing {field}")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or not isinstance(seed_in.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.lookup_table")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "lookup_table": deepcopy(seed_in["lookup_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_59797915(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_59797915(raw)
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
    result["verifier"] = verify_59797915(result)
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
    if isinstance(seed.get("lookup_table"), dict):
        return ctx.tools.call("harness.lookup_table.snapshot", {})
    return {}


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
