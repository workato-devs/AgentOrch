from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_84791375


RECIPE_ID = "84791375"
SEED_TYPE = "salesforce_snowflake_soft_delete_sync_variant"
TRACK = "benchmark_salesforce_snowflake_soft_delete_sync"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_variable", "declare_variable"),
    ("salesforce", "search_sobjects_soql_bulk_csv_v2"),
    ("workato_smart_list", "create_list_from_csv"),
    ("snowflake", "run_custom_sql"),
    ("workato_smart_list", "create_list"),
    ("workato_smart_list", "query_list"),
    ("snowflake", "upsert_rows_batch"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "salesforce.search_sobjects_soql_bulk_csv_v2",
    "workato_smart_list.create_list_from_csv",
    "snowflake.run_custom_sql",
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
    "snowflake.upsert_rows_batch",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "snowflake.run_custom_sql",
    "snowflake.upsert_rows_batch",
]


def validate_84791375(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
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


def seed_84791375(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_84791375(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")

    refs: dict[str, str] = {}
    trigger = trigger_input(ctx)
    snowflake_seed = deepcopy(seed_in.get("snowflake")) if isinstance(seed_in.get("snowflake"), dict) else None
    expect = deepcopy(data.get("expect")) if isinstance(data.get("expect"), dict) else None
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
        refs.update(_salesforce_ref_tokens(seed_in["salesforce"], provision))
        out["salesforce_live"] = deepcopy(provision["state"])
        out["salesforce_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})

    if refs:
        trigger = _replace_value(trigger, refs)
        snowflake_seed = _replace_value(snowflake_seed, refs)
        expect = _replace_value(expect, refs)
        out["trigger"] = trigger
        out["salesforce_ref_tokens"] = refs

    if isinstance(snowflake_seed, dict):
        out["snowflake"] = snowflake_seed
    if isinstance(expect, dict):
        out["expect"] = expect
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    for key in ("force_action_error", "job_context"):
        if isinstance(data.get(key), dict):
            out[key] = deepcopy(data[key])
    return attach_variant(out, ctx)


def run_84791375(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_84791375(raw)
    initial_snapshot = _snapshot(ctx, seed)
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        # Cleanup runs even when replay crashes: leaked benchmark-owned live
        # records would poison later runs (benchmark cleanup policy cleanup
        # principle). On success the snapshot above is captured first.
        cleanup_response = (
            ctx.tools.call("harness.salesforce.cleanup", {})
            if isinstance(seed.get("salesforce_live"), dict)
            else {"ok": True, "leftovers": []}
        )
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
    result["verifier"] = verify_84791375(result)
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


def _salesforce_ref_tokens(seed_section: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    hero_ids = [
        str(record.get("id") or "")
        for record in salesforce_snapshot.get("records") or []
        if isinstance(record, dict)
        and record.get("id")
        and str(record.get("sobject") or "") in {"vh__Hero_Activity__c", "Hero_Activity__c"}
    ]
    refs: dict[str, str] = {}
    for idx, record_id in enumerate(hero_ids):
        refs[f"$SF_HERO_{idx}_ID"] = record_id
        refs[f"$HERO_{idx}_ID"] = record_id

    hero_idx = 0
    for record in seed_section.get("records") or []:
        if not isinstance(record, dict):
            continue
        if str(record.get("sobject") or "") not in {"vh__Hero_Activity__c", "Hero_Activity__c"}:
            continue
        ref = str(record.get("ref") or "").strip()
        if ref and hero_idx < len(hero_ids):
            refs[f"${ref.upper()}_ID"] = hero_ids[hero_idx]
        hero_idx += 1
    return refs


def _replace_value(value: Any, refs: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_value(item, refs) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_value(item, refs) for item in value]
    if isinstance(value, str):
        out = value
        for token, replacement in refs.items():
            out = out.replace(token, replacement)
        return out
    return value


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("salesforce_live"), dict):
        out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
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
