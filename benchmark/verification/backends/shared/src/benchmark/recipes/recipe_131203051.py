from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_131203051
from .salesforce_recipe_utils import collect_actions


RECIPE_ID = "131203051"
SEED_TYPE = "skilljar_course_completion_progress_add_variant"
TRACK = "workato_db_skilljar_course_completion_progress"
TRIGGER_PROVIDER = "skilljar_connector_748504_1680078639"
TRIGGER_NAME = "new_event"
TABLE_ID = "53673"
DOMAIN_NAME_FRAGMENT = "<anon>academy.example.com</anon>"
COURSE_FIELD = "10ad021a_3b0e_4e2e_8bfd_dfd718accbfc"
SKILLJAR_FIELD = "41c1a194_d15e_4f54_bef8_fce24eb5c14d"
NAME_FIELD = "71357431_f64f_413a_ad46_172438d8a9d7"
COMPLETED_AT_FIELD = "cb269f17_e706_44d4_8ef0_a41a09444c58"
STUDENT_FIELD = "dbf89d9a_cf2f_484a_9f26_632b74d06e23"
EXPECTED_ACTIONS = [
    ("workato_db_table", "get_records"),
    ("workato_db_table", "add_record"),
    ("workato_db_table", "update_record"),
]
EXPECTED_RAW_TOOLS = [
    "workato_db_table.get_records",
    "workato_db_table.add_record",
    "workato_db_table.update_record",
]
ALLOWED_TOOLS = [
    "workato_db_table.get_records",
    "workato_db_table.add_record",
    "workato_db_table.update_record",
]


def validate_131203051(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if DOMAIN_NAME_FRAGMENT not in str(raw.get("filter") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} domain filter changed")
    actions = collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    table_ids = [str((action.get("input") or {}).get("table_id") or "") for action in actions]
    if table_ids != [TABLE_ID, TABLE_ID, TABLE_ID]:
        raise RuntimeError(f"recipe {RECIPE_ID} Workato DB table sequence changed: {table_ids}")
    search_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if COURSE_FIELD.replace("_", "-") not in str(search_input) or STUDENT_FIELD.replace("_", "-") not in str(search_input):
        raise RuntimeError(f"recipe {RECIPE_ID} lookup filters changed")
    add_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    add_params = add_input.get("parameters") if isinstance(add_input.get("parameters"), dict) else {}
    for field in (COURSE_FIELD, SKILLJAR_FIELD, NAME_FIELD, COMPLETED_AT_FIELD, STUDENT_FIELD):
        if field not in add_params:
            raise RuntimeError(f"recipe {RECIPE_ID} add-record field mapping changed: {field}")
    return {"trigger_provider": TRIGGER_PROVIDER, "trigger_name": TRIGGER_NAME, "actions": _action_summary(actions)}


def seed_131203051(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_131203051(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    domain = trigger.get("domain") if isinstance(trigger.get("domain"), dict) else {}
    course = trigger.get("course") if isinstance(trigger.get("course"), dict) else {}
    user = trigger.get("user") if isinstance(trigger.get("user"), dict) else {}
    progress = trigger.get("course_progress") if isinstance(trigger.get("course_progress"), dict) else {}
    if str(domain.get("name") or "") == "":
        # Both trigger-filter outcomes are benchmarked: a domain name matching
        # DOMAIN_NAME_FRAGMENT runs the progress-tracking path, any other
        # domain is the verified zero-action trigger-filter-false path. Only a
        # missing/blank domain name is invalid input.
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing domain.name")
    for key, value in {
        "course.id": course.get("id"),
        "user.id": user.get("id"),
        "user.first_name": user.get("first_name"),
        "user.last_name": user.get("last_name"),
        "course_progress.completed_at": progress.get("completed_at"),
    }.items():
        if value in (None, ""):
            raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing {key}")
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


def run_131203051(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_131203051(raw)
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
    result["verifier"] = verify_131203051(result)
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
