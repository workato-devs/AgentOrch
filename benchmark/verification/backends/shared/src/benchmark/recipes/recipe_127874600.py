from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_127874600
from .salesforce_recipe_utils import collect_actions
from .snowflake_live_recipe_utils import ground_truth


RECIPE_ID = "127874600"
SEED_TYPE = "genie_live_google_drive_lookup_table_folder_variant"
TRACK = "live_google_drive_lookup_table_genie"
TRIGGER_PROVIDER = "workato_genie"
TRIGGER_NAME = "start_workflow"
LOOKUP_TABLE_ID = "4422737"
PARENT_FOLDER_ID = "13kI3D-GiJljwndvhkDFNF0cZbyayEpHc"
EXPECTED_ACTIONS = [
    ("google_drive", "create_folder"),
    ("lookup_table", "add_entry"),
    ("workato_genie", "workflow_return_result"),
]
EXPECTED_RAW_TOOLS = ["google_drive.create_folder", "lookup_table.add_entry", "workato_genie.workflow_return_result"]
ALLOWED_TOOLS = ["google_drive.create_folder", "lookup_table.add_entry", "workato_genie.workflow_return_result"]


def validate_127874600(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    drive_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if str(drive_input.get("folderId") or "") != PARENT_FOLDER_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} Google Drive parent folder changed")
    if str((actions[1].get("input") or {}).get("lookup_table_id") or "") != LOOKUP_TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} lookup table id changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_127874600(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_127874600(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters") if isinstance(trigger.get("parameters"), dict) else None
    if not isinstance(parameters, dict) or not parameters.get("customerName"):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing parameters.customerName")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or not isinstance(seed_in.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.lookup_table")
    google_drive_seed = seed_in.get("google_drive") if isinstance(seed_in.get("google_drive"), dict) else None
    out = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "lookup_table": deepcopy(seed_in["lookup_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if google_drive_seed is not None:
        if not google_drive_seed.get("parent_folder_id"):
            raise RuntimeError(f"recipe {RECIPE_ID} seed.google_drive missing parent_folder_id")
        out["google_drive"] = deepcopy(google_drive_seed)
    return attach_variant(out, ctx)


def run_127874600(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_127874600(raw)
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    cleanup_response: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        folder_id = _created_folder_id(ctx)
        if folder_id:
            cleanup_response = ctx.tools.call("harness.google_drive.delete_file", {"id": folder_id})
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
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
            "cleanup_response": cleanup_response,
            "ground_truth": ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_127874600(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    if isinstance(seed.get("lookup_table"), dict):
        return ctx.tools.call("harness.lookup_table.snapshot", {})
    return {}


def _created_folder_id(ctx: RecipeContext) -> str:
    for call in reversed(ctx.tools.call_log()):
        if call.get("tool") == "google_drive.create_folder":
            result = call.get("result") if isinstance(call.get("result"), dict) else {}
            folder_id = str(result.get("id") or "")
            if folder_id:
                return folder_id
    return ""


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"number": a.get("number"), "provider": a.get("provider"), "name": a.get("name"), "as": a.get("as")} for a in actions]
