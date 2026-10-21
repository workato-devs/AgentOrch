from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_86735426


RECIPE_ID = "86735426"
SEED_TYPE = "pod_issues_logs_service_variant"
TRACK = "pod_issues_logs_service"
TRIGGER_PROVIDER = "workato_service"
TRIGGER_NAME = "receive_request"
# All non-skip actions collected structurally (across every branch), in
# raw-summary order: create (add_entry + reply), read (get_entry + reply),
# update (get_entry + update_entry + reply), and the catch branch which calls
# an escalation sub-recipe then replies with an error.
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("lookup_table", "add_entry"),
    ("workato_service", "send_reply"),
    ("lookup_table", "get_entry"),
    ("workato_service", "send_reply"),
    ("lookup_table", "get_entry"),
    ("lookup_table", "update_entry"),
    ("workato_service", "send_reply"),
    ("workato_service", "call_service"),
    ("workato_service", "send_reply"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.add_entry",
    "workato_service.send_reply",
    "lookup_table.get_entry",
    "workato_service.send_reply",
    "lookup_table.get_entry",
    "lookup_table.update_entry",
    "workato_service.send_reply",
    "workato_service.call_service",
    "workato_service.send_reply",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.add_entry",
    "lookup_table.get_entry",
    "lookup_table.update_entry",
    "workato_service.send_reply",
    "workato_service.call_service",
]


def validate_86735426(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual = [(a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": [
            {
                "number": a.get("number"),
                "provider": a.get("provider"),
                "name": a.get("name"),
                "as": a.get("as"),
            }
            for a in actions
        ],
    }


def seed_86735426(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_86735426(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    request = trigger.get("request") if isinstance(trigger.get("request"), dict) else None
    if not isinstance(request, dict) or request.get("request_id") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing request.request_id")
    if request.get("request_type") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing request.request_type")
    seed_in = data.get("seed") if isinstance(data.get("seed"), dict) else {}
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


def run_86735426(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_86735426(raw)
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
    result["verifier"] = verify_86735426(result)
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
    if isinstance(seed.get("workato_db_table"), dict):
        out.update(ctx.tools.call("harness.workato_db_table.snapshot", {}))
    if isinstance(seed.get("lookup_table"), dict):
        out.update(ctx.tools.call("harness.lookup_table.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
