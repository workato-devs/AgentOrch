from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_59346468


RECIPE_ID = "59346468"
SEED_TYPE = "recipe_function_office_location_default_apps_variant"
TRACK = "workato_recipe_function_office_location_default_apps"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
OFFICE_TABLE = "PUBLIC.OFFICE_LOCATION"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_variable", "declare_list"),
    ("snowflake", "search_rows_sql"),
    ("workato_variable", "declare_list"),
    ("workato_recipe_function", "return_result"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_list",
    "snowflake.search_rows_sql",
    "workato_runtime.declare_list",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_recipe_function.return_result",
]
EXPECTED_STOP_STEPS: list[int] = [5]


def validate_59346468(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    office_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    office_sql = str(office_input.get("sql") or "")
    if "FROM OFFICE_LOCATION" not in office_sql or "WHERE OL.ID = :office_location_id" not in office_sql:
        raise RuntimeError(f"recipe {RECIPE_ID} OFFICE_LOCATION SQL mapping changed: {office_sql!r}")
    if str(office_input.get("limit") or "") != "1":
        raise RuntimeError(f"recipe {RECIPE_ID} OFFICE_LOCATION query limit changed")
    office_parameters = office_input.get("parameters") if isinstance(office_input.get("parameters"), dict) else {}
    office_bind = str((office_parameters.get("data") or {}).get("office_location_id") or "")
    if "fda95828" not in office_bind or "office_location_id" not in office_bind:
        raise RuntimeError(f"recipe {RECIPE_ID} bind parameter no longer maps the trigger parameter")
    # The default-app branch is intentionally disabled: its source list is
    # always empty and the imported branch did not define a caller-visible
    # result. Keep every node in that branch skip:true and validate it below
    # instead of pretending those actions are executable ground truth.
    disabled_numbers = {7, 8, 9, 11, 12, 13, 14}
    disabled = {
        int(node.get("number")): node
        for node in _walk_nodes(raw)
        if node.get("number") in disabled_numbers
    }
    if set(disabled) != disabled_numbers or any(
        node.get("skip") is not True for node in disabled.values()
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} unreachable default-app branch is no longer fully disabled"
        )
    stops = _collect_stops(raw)
    if [stop.get("number") for stop in stops] != EXPECTED_STOP_STEPS:
        raise RuntimeError(f"recipe {RECIPE_ID} stop steps changed: {stops}")
    for stop in stops:
        if str((stop.get("input") or {}).get("stop_with_error") or "") != "true":
            raise RuntimeError(f"recipe {RECIPE_ID} stop step {stop.get('number')} is no longer stop_with_error")
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


def seed_59346468(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_59346468(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict) or not str(parameters.get("office_location_id") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger input requires a non-empty parameters.office_location_id"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    snowflake_seed = seed_in.get("snowflake")
    snowflake_tables = snowflake_seed.get("tables") if isinstance(snowflake_seed, dict) else None
    if not isinstance(snowflake_tables, dict) or OFFICE_TABLE not in snowflake_tables:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must define snowflake.tables[{OFFICE_TABLE!r}] explicitly "
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


def run_59346468(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_59346468(raw)
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
    result["verifier"] = verify_59346468(result)
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


def _collect_stops(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "stop" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_stops(child))
    return found


def _walk_nodes(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        found.append(child)
        found.extend(_walk_nodes(child))
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
