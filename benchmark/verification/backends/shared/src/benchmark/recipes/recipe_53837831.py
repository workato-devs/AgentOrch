from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, require_seed_section, trigger_input, variant_data
from ..verifier import verify_53837831


RECIPE_ID = "53837831"


def validate_53837831(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("provider") != "workato_recipe_function" or raw.get("name") != "execute":
        raise RuntimeError("recipe 53837831 has unexpected trigger")
    actions = _collect_actions(raw)
    names = {(action.get("provider"), action.get("name")) for action in actions}
    expected = {
        ("salesforce", "search_sobjects_soql_v2"),
        ("workato_recipe_function", "return_result"),
    }
    if not expected.issubset(names):
        raise RuntimeError("recipe 53837831 missing expected Salesforce/function actions")
    search = next(
        action for action in actions
        if action.get("provider") == "salesforce" and action.get("name") == "search_sobjects_soql_v2"
    )
    query = str((search.get("input") or {}).get("query") or "")
    if "FROM Task" not in query or "Hours_Spent__c" not in query or "RecordType.Name LIKE" not in query:
        raise RuntimeError("recipe 53837831 has unexpected Salesforce SOQL")
    return {"actions": actions, "search_action": search}


def seed_53837831(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    action = validate_53837831(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if not trigger:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing trigger_input")
    params = trigger.get("parameters")
    if not isinstance(params, dict) or not str(params.get("cstask_id") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} variant trigger_input missing parameters.cstask_id")
    cstask_id = str(params["cstask_id"])

    sf_seed = _prepare_salesforce_seed(
        require_seed_section(ctx, "salesforce"),
        cstask_id,
    )
    seeded = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": sf_seed})
    snapshot = seeded.get("snapshot") if isinstance(seeded.get("snapshot"), dict) else {}
    records = ((snapshot.get("salesforce") or {}).get("records") or [])
    cstask_live_id = next(
        (str(r.get("id") or "") for r in records if isinstance(r, dict) and r.get("sobject") == "Account" and r.get("id")),
        "",
    )
    if cstask_id == "$CSTASK_ID":
        if not cstask_live_id:
            raise RuntimeError(f"recipe {RECIPE_ID} seed did not provision the cstask Account record")
        cstask_id = cstask_live_id
        params["cstask_id"] = cstask_id
    return attach_variant({
        "recipe_id": RECIPE_ID,
        "seed_type": "workato_recipe_function_salesforce_time_summary",
        "trigger": trigger,
        "salesforce": sf_seed,
        "salesforce_live": seeded.get("state"),
        "salesforce_seed_snapshot": seeded.get("snapshot"),
        "raw_action": action,
        "harness_tool_calls": ctx.tools.call_log(),
    }, ctx)


def run_53837831(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    action = validate_53837831(raw)
    trigger = seed.get("trigger")
    params = (trigger or {}).get("parameters") if isinstance(trigger, dict) else None
    if not isinstance(params, dict):
        raise RuntimeError("seed file missing Workato recipe-function parameters")
    cstask_id = str(params.get("cstask_id") or "")
    if not cstask_id:
        raise RuntimeError("seed file missing cstask_id")

    expected_total = _expected_total_spent_hours(seed)
    initial_snapshot = ctx.tools.call("harness.salesforce.snapshot", {})
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        post_search_snapshot = ctx.tools.call("harness.salesforce.snapshot", {})
    finally:
        # Cleanup runs even when replay crashes: leaked benchmark-owned live
        # records would poison later runs (benchmark cleanup policy cleanup
        # principle). On success the snapshot above is captured first.
        cleanup = ctx.tools.call("harness.salesforce.cleanup", {})
    search_call = _raw_step(raw_execution, "salesforce.search_records")
    return_call = _raw_step(raw_execution, "workato_recipe_function.return_result")
    search = search_call.get("result") if isinstance(search_call.get("result"), dict) else {}
    returned = return_call.get("result") if isinstance(return_call.get("result"), dict) else {}
    # expected_query must come from the independent reconstruction, never from
    # the executed trace: deriving it from search_call.args would make the
    # verifier's search_used_expected_soql check compare the actual query
    # against itself and it could never fail.
    query = _query(cstask_id)

    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=bool(cleanup.get("ok")),
        track="live_salesforce_answer_with_mock_workato_function",
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": trigger,
            "expected_query": query,
            "expected_total_spent_hours": expected_total,
            "expected_total_source": "independent recompute from seed salesforce Task records",
            "search_response": search,
            "return_response": returned,
            "initial_snapshot": initial_snapshot,
            "post_search_snapshot": post_search_snapshot,
            "cleanup_response": cleanup,
            "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
            "raw_execution": raw_execution,
            "expect": (seed.get("variant_input") or {}).get("expect") or {},
            "raw_action": action,
        },
        allowed_tools=["salesforce.search_records", "workato_recipe_function.return_result"],
    )
    result["verifier"] = verify_53837831(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action":
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _prepare_salesforce_seed(seed: dict[str, Any], cstask_id: str) -> dict[str, Any]:
    out = deepcopy(seed or {})
    records = out.get("records") if isinstance(out.get("records"), list) else []
    if not records:
        raise RuntimeError(f"recipe {RECIPE_ID} variant seed.salesforce must define records explicitly")
    prepared: list[dict[str, Any]] = []
    for idx, record in enumerate(records):
        if not isinstance(record, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} salesforce seed record {idx} must be an object")
        rec = deepcopy(record)
        if not str(rec.get("sobject") or ""):
            raise RuntimeError(f"recipe {RECIPE_ID} salesforce seed record {idx} missing sobject")
        fields = rec.get("fields") if isinstance(rec.get("fields"), dict) else {}
        if rec.get("sobject") == "Task":
            missing = [key for key in ("Subject", "WhatId", "_filter_0", "_filter_1", "Hours_Spent__c") if key not in fields]
            if missing:
                raise RuntimeError(f"recipe {RECIPE_ID} salesforce seed record {idx} missing fields: {missing}")
            if str(fields.get("_filter_1") or "") != cstask_id:
                # The declared WhatId query filter must be the same cstask the
                # trigger passes in, otherwise the recipe's SOQL and the seeded
                # data would silently disagree.
                raise RuntimeError(
                    f"recipe {RECIPE_ID} salesforce seed record {idx} declares WhatId filter "
                    f"{fields.get('_filter_1')!r} but the trigger queries {cstask_id!r}"
                )
        prepared.append(rec)
    out["records"] = prepared
    return out



def _query(cstask_id: str) -> str:
    escaped = cstask_id.replace("\\", "\\\\").replace("'", "\\'")
    return (
        "SELECT Id,OwnerId,WhatId,RecordTypeId,Hours_Spent__c,"
        "TypeOf What WHEN Workato_Task__c THEN OwnerId END "
        f"FROM Task WHERE WhatId = '{escaped}' AND RecordType.Name LIKE '%Log Time%'"
    )


def _expected_total_spent_hours(seed: dict[str, Any]) -> str:
    """Independently derived groundtruth: sum Hours_Spent__c over the SEEDED
    Task records that satisfy the recipe query's declared filters (WhatId =
    the queried cstask, RecordType.Name LIKE '%Log Time%'). Computed from the
    seed artifact only - never from the recipe's own return - so the
    verifier's returned_expected_total_spent_hours comparison carries real
    signal."""
    sf_seed = seed.get("salesforce") if isinstance(seed.get("salesforce"), dict) else {}
    records = sf_seed.get("records") if isinstance(sf_seed.get("records"), list) else []
    matching: list[dict[str, Any]] = []
    for pos, record in enumerate(records):
        if not isinstance(record, dict) or record.get("sobject") != "Task":
            continue
        fields = record.get("fields") if isinstance(record.get("fields"), dict) else {}
        pattern = str(fields.get("_filter_0") or "")
        if not (pattern.startswith("%") and pattern.endswith("%") and pattern.strip("%")):
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed Task record {pos} declares an unsupported "
                f"record-type LIKE pattern {pattern!r}"
            )
        record_type = str(fields.get("RecordTypeId") or "")
        if not record_type.startswith("$RECORD_TYPE:"):
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed Task record {pos} RecordTypeId must be a "
                f"$RECORD_TYPE token for the independent recompute: {record_type!r}"
            )
        if str(fields.get("WhatId") or "") != str(fields.get("_filter_1") or ""):
            continue  # decoy: not attached to the queried cstask
        if pattern.strip("%") not in record_type.rsplit(":", 1)[-1]:
            continue  # decoy: record type outside the LIKE filter
        matching.append(fields)
    if not matching:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed contains no Task records matching the recipe "
            "query filters; cannot derive an expected total"
        )
    return _format_decimal(_total_hours(matching))


def _total_hours(records: list[dict[str, Any]]) -> Decimal:
    total = Decimal("0")
    for record in records:
        fields = record.get("fields") if isinstance(record.get("fields"), dict) else record
        value = fields.get("Hours_Spent__c") if isinstance(fields, dict) else None
        if value in (None, ""):
            continue
        try:
            total += Decimal(str(value))
        except (InvalidOperation, ValueError):
            continue
    return total


def _format_decimal(value: Decimal) -> str:
    if value == value.to_integral_value():
        return str(value.quantize(Decimal("1")))
    text = format(value.normalize(), "f")
    return text.rstrip("0").rstrip(".")


def _raw_step(raw_execution: dict[str, Any], tool: str) -> dict[str, Any]:
    for row in raw_execution.get("trace") or []:
        if row.get("tool") == tool:
            return row if isinstance(row, dict) else {}
    return {}
