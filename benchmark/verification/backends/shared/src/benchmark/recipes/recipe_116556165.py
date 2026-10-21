from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_116556165


RECIPE_ID = "116556165"
SEED_TYPE = "sheets_process_hierarchy_upsert_variant"
TRACK = "benchmark_final_state"
TRIGGER_PROVIDER = "google_sheets"
TRIGGER_NAME = "updated_spreadsheet_row_v4_2"
WORKATO_TABLE_ID = "20690"
SNOWFLAKE_TABLE = "AUTOMATION_COMPASS.PROCESS_HIERARCHY"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_db_table", "upsert_record"),
    ("snowflake", "upsert_rows_batch"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.upsert_record",
    "snowflake.upsert_rows_batch",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.upsert_record",
    "snowflake.upsert_rows_batch",
]


def validate_116556165(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    first_input = actions[0].get("input") or {}
    if str(first_input.get("table_id") or "") != WORKATO_TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} Workato DB table id changed")
    selection = actions[0].get("dynamicPickListSelection") or {}
    if not isinstance(selection, dict) or selection.get("primary_field_id") != "Level":
        raise RuntimeError(f"recipe {RECIPE_ID} Workato DB primary field label changed")
    second_input = actions[1].get("input") or {}
    if str(second_input.get("table") or "") != SNOWFLAKE_TABLE:
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake table changed")
    if str(second_input.get("key_columns") or "") != "LEVEL":
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake key column changed")
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


def seed_116556165(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_116556165(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    columns = trigger.get("columns")
    if not isinstance(columns, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing columns object")
    for key in ("col_1", "col_2"):
        if columns.get(key) in (None, ""):
            raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing required column {key}")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
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
    return attach_variant(out, ctx)


def run_116556165(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_116556165(raw)
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
    result["verifier"] = verify_116556165(result)
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
    if isinstance(seed.get("snowflake"), dict):
        out.update(ctx.tools.call("harness.snowflake.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
