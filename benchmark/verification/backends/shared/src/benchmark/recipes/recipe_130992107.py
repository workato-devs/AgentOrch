from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_130992107


RECIPE_ID = "130992107"
SEED_TYPE = "genie_salesforce_past_primary_sc_lookup_variant"
TRACK = "salesforce_lookup_answer"
TRIGGER_PROVIDER = "workato_genie"
TRIGGER_NAME = "start_workflow"
LOOKUP_TABLE_ID = "4492245"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("salesforce", "search_sobjects_soql_v2"),
    ("workato_variable", "declare_list"),
    ("salesforce", "search_sobjects"),
    ("lookup_table", "search_entries"),
    ("workato_variable", "insert_to_list"),
    ("workato_genie", "workflow_return_result"),
    ("workato_genie", "workflow_return_result"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_runtime.declare_list",
    "lookup_table.search_entries",
    "workato_runtime.insert_to_list",
    "workato_genie.workflow_return_result",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "lookup_table.search_entries",
    "workato_genie.workflow_return_result",
]


def validate_130992107(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    disabled = [
        node
        for node in _walk_nodes(raw)
        if node.get("number") in {11, 12, 13}
    ]
    if len(disabled) != 3 or any(node.get("skip") is not True for node in disabled):
        raise RuntimeError(
            f"recipe {RECIPE_ID} undefined no-user return branch is no longer disabled"
        )
    soql_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    query = str(soql_input.get("query") or "")
    if "FROM Opportunity" not in query or "PrimarySC__c" not in query:
        raise RuntimeError(f"recipe {RECIPE_ID} opportunity SOQL changed")
    lookup_input = actions[3].get("input") if isinstance(actions[3].get("input"), dict) else {}
    if str(lookup_input.get("lookup_table_id") or "") != LOOKUP_TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} lookup table changed")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": _action_summary(actions),
    }


def seed_130992107(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130992107(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "raw_validation": validation,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if isinstance(seed_in.get("salesforce"), dict):
        provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": seed_in["salesforce"]})
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
        out["salesforce_live"] = deepcopy(provision["state"])
        out["salesforce_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
        trigger = _replace_snapshot_tokens(trigger, provision.get("snapshot") or {})
        out["trigger"] = trigger
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


def run_130992107(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130992107(raw)
    initial_snapshot = _snapshot(ctx, seed)
    cleanup_response: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        if isinstance(seed.get("salesforce_live"), dict):
            cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
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
            "cleanup_response": cleanup_response,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_130992107(result)
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
    if isinstance(seed.get("workato_db_table"), dict):
        out.update(ctx.tools.call("harness.workato_db_table.snapshot", {}))
    if isinstance(seed.get("lookup_table"), dict):
        out.update(ctx.tools.call("harness.lookup_table.snapshot", {}))
    if isinstance(seed.get("salesforce_live"), dict):
        out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
    return out


def _action_summary(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"number": a.get("number"), "provider": a.get("provider"), "name": a.get("name"), "as": a.get("as")}
        for a in actions
    ]


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}


def _replace_snapshot_tokens(value: Any, snapshot: dict[str, Any]) -> Any:
    records = ((snapshot.get("salesforce") or {}).get("records") or [])
    replacements: dict[str, str] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        sobject = str(record.get("sobject") or "")
        record_id = str(record.get("id") or "")
        if sobject and record_id:
            replacements.setdefault(f"${sobject.upper()}_ID", record_id)
    def _walk(node: Any) -> Any:
        if isinstance(node, dict):
            return {key: _walk(item) for key, item in node.items()}
        if isinstance(node, list):
            return [_walk(item) for item in node]
        if isinstance(node, str):
            out = node
            for token, replacement in replacements.items():
                out = out.replace(token, replacement)
            return out
        return node
    return _walk(value)
