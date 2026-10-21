from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_131131336
from .salesforce_recipe_utils import collect_actions


RECIPE_ID = "131131336"
SEED_TYPE = "genie_office_access_request_log_variant"
TRACK = "workato_db_genie_office_access_request"
TRIGGER_PROVIDER = "workato_genie"
TRIGGER_NAME = "start_workflow"
TABLE_ID = "59118"
EMAIL_FIELD = "22c716c6_913f_4ef1_b656_25fed0dbd77d"
OFFICE_FIELD = "c749a124_9318_4819_be2c_7c4f9c25af7c"
CREATED_FIELD = "a86d5a34_676f_4907_80ed_1153e53ed3c8"
STATUS_FIELD = "a8d66108_ac7e_4edb_9535_50a455e25a8b"
EXPECTED_STATUS = "Pending approval"
EXPECTED_ACTIONS = [
    ("workato_db_table", "add_record"),
    ("workato_genie", "workflow_return_result"),
]
EXPECTED_RAW_TOOLS = [
    "workato_db_table.add_record",
    "workato_genie.workflow_return_result",
]
ALLOWED_TOOLS = [
    "workato_db_table.add_record",
    "workato_genie.workflow_return_result",
]


def validate_131131336(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    add_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    parameters = add_input.get("parameters") if isinstance(add_input.get("parameters"), dict) else {}
    if add_input.get("table_id") != TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} Workato DB target table changed")
    if "parameters\", \"email" not in str(parameters.get(EMAIL_FIELD) or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} requester email mapping changed")
    if "parameters\", \"office_location_id" not in str(parameters.get(OFFICE_FIELD) or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} office location mapping changed")
    if parameters.get(CREATED_FIELD) != "=now" or parameters.get(STATUS_FIELD) != EXPECTED_STATUS:
        raise RuntimeError(f"recipe {RECIPE_ID} created date or status mapping changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_131131336(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_131131336(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters") if isinstance(trigger.get("parameters"), dict) else None
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing parameters")
    if parameters.get("email") in (None, "") or parameters.get("office_location_id") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters missing email or office_location_id")
    seed_in = data.get("seed")
    db_seed = seed_in.get("workato_db_table") if isinstance(seed_in, dict) else None
    if not isinstance(db_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.workato_db_table")
    now = data.get("now")
    if now in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} requires fixed now")
    out = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "workato_db_table": deepcopy(db_seed),
        "now": now,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_131131336(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_131131336(raw)
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
    result["verifier"] = verify_131131336(result)
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
