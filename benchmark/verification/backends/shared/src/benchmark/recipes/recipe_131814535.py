from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_131814535
from .salesforce_recipe_utils import collect_actions


RECIPE_ID = "131814535"
SEED_TYPE = "genie_actions_taken_csm_status_update_variant"
TRACK = "workato_db_genie_actions_taken_status_update"
TRIGGER_PROVIDER = "workato_genie"
TRIGGER_NAME = "start_workflow"
TABLE_ID = "58841"
SUGGESTED_ACTION_FIELD_HYPHEN = "9ae0e725-382f-4b9d-886f-db38b8f76e11"
STATUS_FIELD = "d2c98f1f_c05a_4959_8138_6f708b4e4c8b"
STATUS_REASON_FIELD = "262c62d6_980a_45aa_8140_6b89e63e11ec"
STATUS_UPDATE_DATE_FIELD = "edc17279_57dd_44bf_b73c_a51e5e616379"
EXPECTED_ACTIONS = [
    ("workato_db_table", "get_records"),
    ("workato_db_table", "update_record"),
    ("workato_genie", "workflow_return_result"),
]
EXPECTED_RAW_TOOLS = [
    "workato_db_table.get_records",
    "workato_db_table.update_record",
    "workato_genie.workflow_return_result",
]
ALLOWED_TOOLS = [
    "workato_db_table.get_records",
    "workato_db_table.update_record",
    "workato_genie.workflow_return_result",
]


def validate_131814535(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    search_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if search_input.get("table_id") != TABLE_ID or SUGGESTED_ACTION_FIELD_HYPHEN not in str(search_input):
        raise RuntimeError(f"recipe {RECIPE_ID} Actions Taken lookup mapping changed")
    update_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    parameters = update_input.get("parameters") if isinstance(update_input.get("parameters"), dict) else {}
    for field in (STATUS_FIELD, STATUS_REASON_FIELD, STATUS_UPDATE_DATE_FIELD):
        if field not in parameters:
            raise RuntimeError(f"recipe {RECIPE_ID} Actions Taken update field {field} missing")
    if update_input.get("table_id") != TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} Actions Taken update table changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_131814535(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_131814535(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    if data.get("now") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} requires fixed now for date formula")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters") if isinstance(trigger.get("parameters"), dict) else None
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing parameters object")
    for key in ("Suggested_Action", "CSM_Status_Update", "CSM_Status_Reason"):
        if parameters.get(key) in (None, ""):
            raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter missing {key}")
    seed_in = data.get("seed")
    db_seed = seed_in.get("workato_db_table") if isinstance(seed_in, dict) else None
    if not isinstance(db_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.workato_db_table")
    out = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "workato_db_table": deepcopy(db_seed),
        "now": data["now"],
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_131814535(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_131814535(raw)
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
    result["verifier"] = verify_131814535(result)
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
