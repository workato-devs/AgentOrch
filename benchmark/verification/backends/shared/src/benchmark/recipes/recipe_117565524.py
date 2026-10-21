from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_117565524


RECIPE_ID = "117565524"
SEED_TYPE = "api_platform_dropdown_metadata_workato_db_variant"
TRACK = "benchmark_final_state"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TABLE_IDS = ["20687", "20686", "20688", "20689", "20690"]
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_db_table", "get_records"),
    ("workato_db_table", "get_records"),
    ("workato_db_table", "get_records"),
    ("workato_db_table", "get_records"),
    ("workato_db_table", "get_records"),
    ("workato_api_platform", "return_response"),
    ("workato_api_platform", "return_response"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_api_platform.return_response",
]


def validate_117565524(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    actual_table_ids = [str((action.get("input") or {}).get("table_id") or "") for action in actions[:5]]
    if actual_table_ids != TABLE_IDS:
        raise RuntimeError(f"recipe {RECIPE_ID} Workato DB table sequence changed: {actual_table_ids}")
    success_input = actions[5].get("input") or {}
    if str(success_input.get("http_status_code") or "") != "200":
        raise RuntimeError(f"recipe {RECIPE_ID} success response status changed")
    error_input = actions[6].get("input") or {}
    if str(error_input.get("http_status_code") or "") != "400":
        raise RuntimeError(f"recipe {RECIPE_ID} error response status changed")
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


def seed_117565524(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_117565524(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if not isinstance(seed_in.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.workato_db_table")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger_input(ctx),
        "track": data.get("track"),
        "raw_validation": validation,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if isinstance(data.get("expect"), dict):
        out["expect"] = deepcopy(data["expect"])
    for key, value in seed_in.items():
        if isinstance(value, dict):
            out[str(key)] = deepcopy(value)
    return attach_variant(out, ctx)


def run_117565524(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_117565524(raw)
    expect = seed.get("expect") if isinstance(seed.get("expect"), dict) else {}
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
            "expect": expect,
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_117565524(result)
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
