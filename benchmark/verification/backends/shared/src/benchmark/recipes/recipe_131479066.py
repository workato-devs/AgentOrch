from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_131479066
from .salesforce_recipe_utils import collect_actions


RECIPE_ID = "131479066"
SEED_TYPE = "genie_conversation_metadata_create_variant"
TRACK = "workato_db_genie_conversation_metadata"
TRIGGER_PROVIDER = "workato_genie"
TRIGGER_NAME = "start_workflow"
TABLE_ID = "57271"
CONVERSATION_FIELD = "d604313d_e3c6_4a86_85ff_3a97b924b3ca"
EMAIL_FIELD = "b47404bb_9577_4d4c_b539_a1782afe4473"
NAME_FIELD = "ef2d896c_c20d_49a0_a03f_4f05061cc279"
EXPECTED_ACTIONS = [
    ("workato_db_table", "get_records"),
    ("workato_genie", "workflow_return_result"),
    ("workato_db_table", "add_record"),
    ("workato_genie", "workflow_return_result"),
]
EXPECTED_RAW_TOOLS = [
    "workato_db_table.get_records",
    "workato_db_table.add_record",
    "workato_genie.workflow_return_result",
]
ALLOWED_TOOLS = [
    "workato_db_table.get_records",
    "workato_db_table.add_record",
    "workato_genie.workflow_return_result",
]


def validate_131479066(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    search_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    add_input = actions[2].get("input") if isinstance(actions[2].get("input"), dict) else {}
    if search_input.get("table_id") != TABLE_ID or CONVERSATION_FIELD.replace("_", "-") not in str(search_input):
        raise RuntimeError(f"recipe {RECIPE_ID} Workato DB search mapping changed")
    if add_input.get("table_id") != TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} Workato DB add table changed")
    parameters = add_input.get("parameters") if isinstance(add_input.get("parameters"), dict) else {}
    if CONVERSATION_FIELD not in parameters or EMAIL_FIELD not in parameters or NAME_FIELD not in parameters:
        raise RuntimeError(f"recipe {RECIPE_ID} metadata add fields changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_131479066(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_131479066(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    context = trigger.get("context") if isinstance(trigger.get("context"), dict) else None
    if not isinstance(context, dict) or context.get("conversation_id") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing context.conversation_id")
    if context.get("user_email") in (None, "") or context.get("user_name") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing user context")
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
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_131479066(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_131479066(raw)
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
    result["verifier"] = verify_131479066(result)
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
