from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_130635347
from .salesforce_recipe_utils import collect_actions, copy_expect, replace_tokens, salesforce_refs, seed_salesforce_state


RECIPE_ID = "130635347"
SEED_TYPE = "genie_salesforce_lead_update_db_status_variant"
TRACK = "live_salesforce_workato_db_genie"
TRIGGER_PROVIDER = "workato_genie"
TRIGGER_NAME = "start_workflow"
TABLE_ID = "33476"
EXPECTED_ACTIONS = [
    ("workato_variable", "declare_variable"),
    ("salesforce", "update_sobject"),
    ("workato_db_table", "get_records"),
    ("workato_db_table", "update_record"),
    ("salesforce", "search_sobjects"),
    ("workato_genie", "workflow_return_result"),
]
EXPECTED_RAW_TOOLS = [
    "workato_runtime.declare_variable",
    "salesforce.update_record",
    "workato_db_table.get_records",
    "workato_db_table.update_record",
    "salesforce.search_records",
    "workato_genie.workflow_return_result",
]
ALLOWED_TOOLS = [
    "salesforce.update_record",
    "workato_db_table.get_records",
    "workato_db_table.update_record",
    "salesforce.search_records",
    "workato_genie.workflow_return_result",
]
# `status` is OPTIONAL (Genie schema): the falsy-render fix landed —
# `.presence` of an absent pill yields nil, nil-compacted at the SF update
# boundary; the branch-aware verify_130635347 covers both arms. A status-
# absent variant exists on the byte-twin 131787576 (variant_06).
REQUIRED_PARAMETERS = ("lead_id", "description")


def validate_130635347(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    update_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    if update_input.get("sobject_name") != "Lead" or "Description" not in update_input or "Status" not in update_input:
        raise RuntimeError(f"recipe {RECIPE_ID} Lead update mapping changed")
    search_input = actions[2].get("input") if isinstance(actions[2].get("input"), dict) else {}
    if search_input.get("table_id") != TABLE_ID or "lead_" not in str(search_input):
        raise RuntimeError(f"recipe {RECIPE_ID} Workato DB lookup mapping changed")
    db_update = actions[3].get("input") if isinstance(actions[3].get("input"), dict) else {}
    if db_update.get("table_id") != TABLE_ID or "932d5402_1239_4fbb_95de_b176a9c050c2" not in str(db_update):
        raise RuntimeError(f"recipe {RECIPE_ID} Workato DB status update mapping changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_130635347(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130635347(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    provision = seed_salesforce_state(RECIPE_ID, data, ctx)
    refs = salesforce_refs(provision)
    trigger = replace_tokens(trigger_input(ctx), refs)
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
    out = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": replace_tokens(copy_expect(data), refs),
        "raw_validation": validation,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "workato_db_table": replace_tokens(deepcopy(db_seed), refs),
        "account_properties": deepcopy(data.get("account_properties") if isinstance(data.get("account_properties"), dict) else {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_130635347(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130635347(raw)
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    cleanup_response: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
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
            "account_properties": seed.get("account_properties") if isinstance(seed.get("account_properties"), dict) else {},
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "cleanup_response": cleanup_response,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_130635347(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("salesforce_live"), dict):
        out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
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


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"number": a.get("number"), "provider": a.get("provider"), "name": a.get("name"), "as": a.get("as")} for a in actions]
