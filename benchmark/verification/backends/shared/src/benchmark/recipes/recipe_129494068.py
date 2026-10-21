from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_129494068


RECIPE_ID = "129494068"
SEED_TYPE = "genie_unconfigured_salesforce_license_usage_variant"
TRACK = "workato_db_genie_license_usage"
TRIGGER_PROVIDER = "workato_genie"
TRIGGER_NAME = "start_workflow"
TABLE_ID = "51602"
EXPECTED_ACTIONS = [
    ("workato_db_table", "get_records"),
    ("workato_genie", "workflow_return_result"),
    ("salesforce", "search_sobjects_soql_v2"),
    ("workato_genie", "workflow_return_result"),
    ("workato_genie", "workflow_return_result"),
]
ALLOWED_TOOLS = ["workato_db_table.get_records", "salesforce.search_records", "workato_genie.workflow_return_result"]


def validate_129494068(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    get_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if str(get_input.get("table_id") or "") != TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} Workato DB table changed")
    first_return = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    if "not configured to be optimized" not in str(first_return):
        raise RuntimeError(f"recipe {RECIPE_ID} unconfigured-app return changed")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_129494068(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_129494068(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or not isinstance(seed_in.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.workato_db_table")
    # Configured-app variants reach the live Salesforce user search; they must
    # declare the live user population explicitly (seed.salesforce, e.g. a
    # current_user declaration). Unconfigured-app variants terminate before
    # Salesforce and carry no section; running the Salesforce step without a
    # seeded section fails fast in SalesforceRun (no-fallback).
    salesforce_seed = seed_in.get("salesforce")
    salesforce_state: dict[str, Any] | None = None
    if salesforce_seed is not None:
        if not isinstance(salesforce_seed, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce must be an object")
        provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": salesforce_seed})
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
        salesforce_state = provision["state"]
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters") if isinstance(trigger.get("parameters"), dict) else None
    if not isinstance(parameters, dict) or not parameters.get("app_name"):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing parameters.app_name")
    out = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if salesforce_state is not None:
        out["salesforce_live"] = deepcopy(salesforce_state)
    return attach_variant(out, ctx)


def run_129494068(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_129494068(raw)
    initial_snapshot = ctx.tools.call("harness.workato_db_table.snapshot", {})
    salesforce_seeded = isinstance(seed.get("salesforce_live"), dict)
    salesforce_cleanup: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = ctx.tools.call("harness.workato_db_table.snapshot", {})
    finally:
        if salesforce_seeded:
            # Cleanup principle: live-Salesforce variants release owned state
            # even when the raw execution fails.
            salesforce_cleanup = ctx.tools.call("harness.salesforce.cleanup", {})
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
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
            **({"salesforce_cleanup": salesforce_cleanup} if salesforce_seeded else {}),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_129494068(result)
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


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"number": a.get("number"), "provider": a.get("provider"), "name": a.get("name"), "as": a.get("as")} for a in actions]


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
