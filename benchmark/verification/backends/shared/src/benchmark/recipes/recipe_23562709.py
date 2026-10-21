from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_23562709


RECIPE_ID = "23562709"
SEED_TYPE = "recipe_function_app_status_lookup_variant"
TRACK = "workato_recipe_function_app_status_lookup"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
APP_TABLE = "PUBLIC.APP"
# Callable recipe function (trigger as b9a23d4f, parameters.manager_id). The
# whole body is wrapped in TRY (step 2):
#   declare_list "Default App IDs" (step 3, as 5c31546c)
#   IF manager_id == "1" (step 4) -> insert_to_list {app_id: "A106"} (step 5)
#   declare_list "Final List of Apps" (step 6, as a9191425)
#   snowflake.search_rows PUBLIC.APP ID/NAME/STATUS limit 50000 (step 7, as 8f08fd02)
#   workato_smart_list.create_list "APP" from the snowflake rows (step 8, as 761b6972)
#   FOREACH Default App IDs (step 9, as 9cde7fd6):
#     workato_smart_list.query_list SELECT * FROM APP WHERE ID = '<app_id>' (step 10, as 11cd7cad)
#     IF status != "Active" (step 11) -> STOP with error
#       "Inactive app evaluated: <name>" (step 12)
#     insert_to_list {app_id, app_name} into Final List of Apps (step 13)
#   return_result {apps: Final List of Apps} (step 14)
# CATCH (step 15, as 62efc5a7) -> STOP with error = catch message (step 16).
# Snowflake runs LIVE; variable lists / smart list / recipe-function return are
# deterministic Workato-internal mocks.
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_variable", "declare_list"),
    ("workato_variable", "insert_to_list"),
    ("workato_variable", "declare_list"),
    ("snowflake", "search_rows"),
    ("workato_smart_list", "create_list"),
    ("workato_smart_list", "query_list"),
    ("workato_variable", "insert_to_list"),
    ("workato_recipe_function", "return_result"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_list",
    "workato_runtime.insert_to_list",
    "workato_runtime.declare_list",
    "snowflake.search_rows",
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
    "workato_runtime.insert_to_list",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows",
    "workato_recipe_function.return_result",
]


def validate_23562709(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    search_input = actions[3].get("input") if isinstance(actions[3].get("input"), dict) else {}
    if search_input.get("table") != APP_TABLE:
        raise RuntimeError(f"recipe {RECIPE_ID} snowflake search table changed: {search_input}")
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


def seed_23562709(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_23562709(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict) or not str(parameters.get("manager_id") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input requires a non-empty parameters.manager_id")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    snowflake_seed = seed_in.get("snowflake")
    snowflake_tables = snowflake_seed.get("tables") if isinstance(snowflake_seed, dict) else None
    if not isinstance(snowflake_tables, dict) or APP_TABLE not in snowflake_tables:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must define snowflake.tables[{APP_TABLE!r}] explicitly "
            "(explicit columns; empty tables still declare columns)"
        )
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
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    for key in ("force_action_error", "job_context"):
        if isinstance(data.get(key), dict):
            out[key] = deepcopy(data[key])
    return attach_variant(out, ctx)


def run_23562709(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_23562709(raw)
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
    result["verifier"] = verify_23562709(result)
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
