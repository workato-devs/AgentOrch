from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_130842923
from .salesforce_recipe_utils import collect_actions


RECIPE_ID = "130842923"
SEED_TYPE = "genie_presales_assignment_request_upsert_variant"
TRACK = "workato_db_genie_presales_assignment_request"
TRIGGER_PROVIDER = "workato_genie"
TRIGGER_NAME = "start_workflow"
TABLE_ID = "39797"
PRIMARY_FIELD_ID = "4c129933-9d4b-4b15-b348-4747b59a71e4"
STATUS_FIELD_ID = "c89ca82c_a4a5_4a41_997e_bb51e7095c50"
EXPECTED_ACTIONS = [
    ("workato_db_table", "get_records"),
    ("workato_genie", "workflow_return_result"),
    ("workato_db_table", "upsert_record"),
    ("workato_variable", "declare_variable"),
    ("workato_genie", "workflow_return_result"),
]
EXPECTED_RAW_TOOLS = [
    "workato_db_table.get_records",
    "workato_db_table.upsert_record",
    "workato_runtime.declare_variable",
    "workato_genie.workflow_return_result",
]
ALLOWED_TOOLS = [
    "workato_db_table.get_records",
    "workato_db_table.upsert_record",
    "workato_genie.workflow_return_result",
]
REQUIRED_PARAMETERS = ("opp_id", "opp_name", "opp_owner")


def validate_130842923(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    search_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if search_input.get("table_id") != TABLE_ID or PRIMARY_FIELD_ID not in str(search_input.get("filters") or []):
        raise RuntimeError(f"recipe {RECIPE_ID} Workato DB search mapping changed")
    upsert_input = actions[2].get("input") if isinstance(actions[2].get("input"), dict) else {}
    if upsert_input.get("table_id") != TABLE_ID or upsert_input.get("primary_field_id") != PRIMARY_FIELD_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} Workato DB upsert mapping changed")
    if STATUS_FIELD_ID not in str(upsert_input) or "New" not in str(upsert_input):
        raise RuntimeError(f"recipe {RECIPE_ID} assignment status mapping changed")
    variable_input = actions[3].get("input") if isinstance(actions[3].get("input"), dict) else {}
    if "SFDC_Base_URL" not in str(variable_input) or "missing key fields" not in str(variable_input):
        raise RuntimeError(f"recipe {RECIPE_ID} response variable mapping changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_130842923(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130842923(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters") if isinstance(trigger.get("parameters"), dict) else None
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing parameters object")
    for key in REQUIRED_PARAMETERS:
        if parameters.get(key) in (None, ""):
            raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter missing {key}")
    seed_in = data.get("seed")
    db_seed = seed_in.get("workato_db_table") if isinstance(seed_in, dict) else None
    if not isinstance(db_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.workato_db_table")
    project_properties = data.get("project_properties") if isinstance(data.get("project_properties"), dict) else {}
    if not project_properties.get("SFDC_Base_URL"):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing project_properties.SFDC_Base_URL")
    out = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "workato_db_table": deepcopy(db_seed),
        "project_properties": deepcopy(project_properties),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_130842923(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130842923(raw)
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
    result["verifier"] = verify_130842923(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    if isinstance(seed.get("workato_db_table"), dict):
        return ctx.tools.call("harness.workato_db_table.snapshot", {})
    return {}


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"number": action.get("number"), "provider": action.get("provider"), "name": action.get("name"), "as": action.get("as")} for action in actions]
