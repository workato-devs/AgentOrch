from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_124154895


RECIPE_ID = "124154895"
SEED_TYPE = "genie_workato_db_sales_methodology_score_variant"
TRACK = "workato_genie_workato_db_score_store"
TRIGGER_PROVIDER = "workato_genie"
TRIGGER_NAME = "start_workflow"
TABLE_ID = "35019"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_db_table", "get_records"),
    ("workato_db_table", "update_record"),
    ("workato_db_table", "add_record"),
    ("workato_genie", "workflow_return_result"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.update_record",
    "workato_db_table.add_record",
    "workato_genie.workflow_return_result",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.update_record",
    "workato_db_table.add_record",
    "workato_genie.workflow_return_result",
]
REQUIRED_PARAMETERS = (
    "customer_name",
    "source",
    "identifier",
    "average_score",
    "detailed_score_json",
)


def validate_124154895(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    for action in actions[:3]:
        raw_input = action.get("input") if isinstance(action.get("input"), dict) else {}
        if str(raw_input.get("table_id") or "") != TABLE_ID:
            raise RuntimeError(f"recipe {RECIPE_ID} Workato DB table id changed")
    return_input = actions[3].get("input") if isinstance(actions[3].get("input"), dict) else {}
    if return_input.get("result") != {"message": "Score stored"}:
        raise RuntimeError(f"recipe {RECIPE_ID} Genie return result changed")
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


def seed_124154895(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_124154895(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters") if isinstance(trigger.get("parameters"), dict) else None
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing parameters object")
    for key in REQUIRED_PARAMETERS:
        if key not in parameters:
            raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing required parameter {key}")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    workato_seed = seed_in.get("workato_db_table")
    if not isinstance(workato_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.workato_db_table")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "workato_db_table": deepcopy(workato_seed),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if isinstance(data.get("job_context"), dict):
        out["job_context"] = deepcopy(data["job_context"])
    return attach_variant(out, ctx)


def run_124154895(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_124154895(raw)
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
    result["verifier"] = verify_124154895(result)
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
