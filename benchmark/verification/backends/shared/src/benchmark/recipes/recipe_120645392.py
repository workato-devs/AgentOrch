from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_120645392


RECIPE_ID = "120645392"
SEED_TYPE = "workflow_task_profile_social_credit_variant"
TRACK = "mock_workato_workflow_task_workato_db"
TRIGGER_PROVIDER = "workato_workflow_task"
TRIGGER_NAME = "new_requests_realtime"
PROFILE_TABLE_ID = "27942"
PROFILE_URL_TABLE_ID = "25464"
URL_TYPE_TABLE_ID = "26391"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_db_table", "get_records"),
    ("workato_db_table", "upsert_record"),
    ("workato_db_table", "get_records"),
    ("workato_db_table", "get_records"),
    ("workato_db_table", "add_record"),
    ("workato_db_table", "get_records"),
    ("workato_db_table", "add_record"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.upsert_record",
    "workato_db_table.get_records",
    "workato_db_table.get_records",
    "workato_db_table.add_record",
    "workato_db_table.get_records",
    "workato_db_table.add_record",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.add_record",
    "workato_db_table.get_records",
    "workato_db_table.upsert_record",
]


def validate_120645392(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    table_ids = [str((action.get("input") or {}).get("table_id") or "") for action in actions]
    expected_table_ids = [
        PROFILE_TABLE_ID,
        PROFILE_TABLE_ID,
        PROFILE_URL_TABLE_ID,
        URL_TYPE_TABLE_ID,
        PROFILE_URL_TABLE_ID,
        URL_TYPE_TABLE_ID,
        PROFILE_URL_TABLE_ID,
    ]
    if table_ids != expected_table_ids:
        raise RuntimeError(f"recipe {RECIPE_ID} table sequence changed: {table_ids}")
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


def seed_120645392(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_120645392(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    workato_seed = seed_in.get("workato_db_table")
    if not isinstance(workato_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.workato_db_table")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger_input(ctx),
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "workato_db_table": deepcopy(workato_seed),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    return attach_variant(out, ctx)


def run_120645392(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_120645392(raw)
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
    result["verifier"] = verify_120645392(result)
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
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
