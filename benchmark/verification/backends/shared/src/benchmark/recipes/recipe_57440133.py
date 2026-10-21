from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_57440133


# Slack bot dynamic menu "List of Employees" (optional parameter status,
# typeahead.value): try { IF status present -> snowflake.search_rows on
# PUBLIC.EMPLOYEE filtered by STATUS + email LIKE typeahead ->
# generate_menu_options(email as label+value); ELSE -> search_rows filtered by
# email LIKE typeahead only -> generate_menu_options } catch { EMPTY block —
# errors are swallowed and the run completes without executing any action }.
RECIPE_ID = "57440133"
SEED_TYPE = "dynamic_menu_snowflake_employee_list_variant"
TRACK = "live_snowflake_slack_dynamic_menu"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "dynamic_menu"
MENU_NAME = "List of Employees"
SNOWFLAKE_TABLE = "PUBLIC.EMPLOYEE"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("snowflake", "search_rows"),
    ("slack_bot", "generate_menu_options"),
    ("snowflake", "search_rows"),
    ("slack_bot", "generate_menu_options"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows",
    "slack_bot.generate_menu_options",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows",
    "slack_bot.generate_menu_options",
]


def validate_57440133(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    trigger_in = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    if trigger_in.get("dynamic_menu_name") != MENU_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} dynamic menu name changed")
    actions = _collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    if_search = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    else_search = actions[2].get("input") if isinstance(actions[2].get("input"), dict) else {}
    for label, search_input in (("status-filtered", if_search), ("unfiltered", else_search)):
        if str(search_input.get("table") or "") != SNOWFLAKE_TABLE:
            raise RuntimeError(f"recipe {RECIPE_ID} {label} search table changed")
        if str(search_input.get("output_columns") or "") != "EMAIL":
            raise RuntimeError(f"recipe {RECIPE_ID} {label} search output columns changed")
    if not str(if_search.get("where") or "").startswith("STATUS = '"):
        raise RuntimeError(f"recipe {RECIPE_ID} status-filtered WHERE clause changed")
    if "LOWER(EMAIL) LIKE LOWER(" not in str(if_search.get("where") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} status-filtered typeahead LIKE changed")
    else_where = str(else_search.get("where") or "")
    if "STATUS" in else_where or "LOWER(EMAIL) LIKE LOWER(" not in else_where:
        raise RuntimeError(f"recipe {RECIPE_ID} unfiltered WHERE clause changed")
    catch_node = _find_catch(raw)
    if catch_node is None:
        raise RuntimeError(f"recipe {RECIPE_ID} try/catch structure changed: no catch block")
    if catch_node.get("block"):
        raise RuntimeError(f"recipe {RECIPE_ID} catch block is no longer empty")
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


def seed_57440133(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_57440133(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    typeahead = trigger.get("typeahead") if isinstance(trigger.get("typeahead"), dict) else {}
    if typeahead.get("value") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger typeahead.value must be non-empty")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    snowflake_seed = seed_in.get("snowflake_live")
    if not isinstance(snowflake_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.snowflake_live")
    tables = snowflake_seed.get("tables") if isinstance(snowflake_seed.get("tables"), dict) else {}
    if SNOWFLAKE_TABLE not in tables:
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.snowflake_live.tables['{SNOWFLAKE_TABLE}']")
    provision = ctx.tools.call("harness.snowflake_live.seed_tables", {"snowflake": snowflake_seed})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "snowflake_live": deepcopy(provision["state"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    for key in ("force_action_error", "job_context"):
        if isinstance(data.get(key), dict):
            out[key] = deepcopy(data[key])
    return attach_variant(out, ctx)


def run_57440133(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_57440133(raw)
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    cleanup: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        if isinstance(seed.get("snowflake_live"), dict):
            cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
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
            "cleanup_response": {"snowflake_live": cleanup},
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_57440133(result)
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


def _find_catch(node: dict[str, Any]) -> dict[str, Any] | None:
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "catch":
            return child
        nested = _find_catch(child)
        if nested is not None:
            return nested
    return None


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("snowflake_live"), dict):
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
