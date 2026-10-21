from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_117564615


RECIPE_ID = "117564615"
SEED_TYPE = "api_platform_business_process_snowflake_query_variant"
TRACK = "benchmark_final_state"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
SNOWFLAKE_TABLE = "AUTOMATION_COMPASS.BUSINESS_PROCESS_DASHBOARD"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("snowflake", "search_rows"),
    ("snowflake", "search_rows_sql"),
    ("workato_api_platform", "return_response"),
    ("workato_api_platform", "return_response"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows",
    "snowflake.search_rows_sql",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows",
    "snowflake.search_rows_sql",
    "workato_api_platform.return_response",
]


def validate_117564615(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    search_input = actions[0].get("input") or {}
    if str(search_input.get("table") or "") != SNOWFLAKE_TABLE:
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake search table changed")
    if str(search_input.get("where") or "") != "PROCESS_ID = :processId":
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake search where clause changed")
    child_input = actions[1].get("input") or {}
    if SNOWFLAKE_TABLE not in str(child_input.get("sql") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} child-process SQL table changed")
    if "PARENT_PROCESS_ID = :processId" not in str(child_input.get("sql") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} child-process SQL where clause changed")
    success_input = actions[2].get("input") or {}
    if str(success_input.get("http_status_code") or "") != "200":
        raise RuntimeError(f"recipe {RECIPE_ID} success response status changed")
    error_input = actions[3].get("input") or {}
    if str(error_input.get("http_status_code") or "") != "400":
        raise RuntimeError(f"recipe {RECIPE_ID} error response status changed")
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


def seed_117564615(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_117564615(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if not isinstance(seed_in.get("snowflake"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.snowflake")
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
    return attach_variant(out, ctx)


def run_117564615(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_117564615(raw)
    trigger = seed.get("trigger")
    if not isinstance(trigger, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing trigger object")
    _require_trigger(trigger)
    expect = seed.get("expect") if isinstance(seed.get("expect"), dict) else {}
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
            "trigger": trigger,
            "track": seed.get("track"),
            "expect": expect,
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_117564615(result)
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


def _require_trigger(trigger: dict[str, Any]) -> None:
    request = trigger.get("request")
    if not isinstance(request, dict) or not request.get("processId"):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger request.processId must be non-empty")


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
