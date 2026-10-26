from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_124656411


RECIPE_ID = "124656411"
SEED_TYPE = "monthly_revops_two_table_purge_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "102b132e"
CLOSED_LOST_TABLE_ID = "3959191"
ADD_TABLE_ID = "4350535"
TABLE_IDS = (CLOSED_LOST_TABLE_ID, ADD_TABLE_ID)
GET_CLOSED_LOST_AS = "0245afa5"
DELETE_CLOSED_LOST_AS = "3d46f38a"
GET_ADD_AS = "14e2b445"
DELETE_ADD_AS = "b3736696"
FOREACH_CLOSED_LOST_AS = "1dcefa34"
FOREACH_ADD_AS = "199f5fa3"


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "clock", "name": "scheduled_event", "as": "102b132e", "skip": false, "input": {"days_of_month": "1", "time_unit": "months", "trigger_at": "09:00:00", "trigger_every": "1"}, "block": [{"number": 2, "keyword": "action", "provider": "lookup_table", "name": "get_entries", "as": "0245afa5", "skip": false, "input": {"lookup_table_id": "3959191"}, "block": []}, {"number": 3, "keyword": "foreach", "provider": "", "name": "", "as": "1dcefa34", "skip": false, "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"0245afa5\",\"path\":[\"entries\"]}')}"}, "repeat_mode": "simple", "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"0245afa5\",\"path\":[\"entries\"]}')}", "block": [{"number": 4, "keyword": "action", "provider": "lookup_table", "name": "delete_entry", "as": "3d46f38a", "skip": false, "input": {"id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"1dcefa34\",\"path\":[\"id\"]}')}", "ignore_not_found": "false", "lookup_table_id": "3959191"}, "block": []}]}, {"number": 5, "keyword": "action", "provider": "lookup_table", "name": "get_entries", "as": "14e2b445", "skip": false, "input": {"lookup_table_id": "4350535"}, "block": []}, {"number": 6, "keyword": "foreach", "provider": "", "name": "", "as": "199f5fa3", "skip": false, "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"14e2b445\",\"path\":[\"entries\"]}')}"}, "repeat_mode": "simple", "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"14e2b445\",\"path\":[\"entries\"]}')}", "block": [{"number": 7, "keyword": "action", "provider": "lookup_table", "name": "delete_entry", "as": "b3736696", "skip": false, "input": {"id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"199f5fa3\",\"path\":[\"id\"]}')}", "ignore_not_found": "false", "lookup_table_id": "4350535"}, "block": []}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (GET_CLOSED_LOST_AS, "lookup_table", "get_entries"),
    (DELETE_CLOSED_LOST_AS, "lookup_table", "delete_entry"),
    (GET_ADD_AS, "lookup_table", "get_entries"),
    (DELETE_ADD_AS, "lookup_table", "delete_entry"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.get_entries",
    "lookup_table.delete_entry",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.get_entries",
    "lookup_table.delete_entry",
]
ROW_COLUMNS = ("col1", "col2", "col3", "col4", "col5", "col6", "col7")
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "delete_sequence",
    "initial_table_counts",
    "final_tables",
)


def validate_124656411(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    # Semantic pins (the tree pin holds the exact bytes; these name the trap):
    # each foreach purges the SAME table its source get_entries read, and the
    # deletes stay fail-fast (ignore_not_found 'false').
    pairs = {
        GET_CLOSED_LOST_AS: (DELETE_CLOSED_LOST_AS, CLOSED_LOST_TABLE_ID),
        GET_ADD_AS: (DELETE_ADD_AS, ADD_TABLE_ID),
    }
    nodes = {str(node.get("as") or ""): node for node in _walk_nodes(raw)}
    for get_as, (delete_as, table_id) in pairs.items():
        get_table = str((nodes[get_as].get("input") or {}).get("lookup_table_id") or "")
        delete_input = nodes[delete_as].get("input") or {}
        if get_table != table_id or str(delete_input.get("lookup_table_id") or "") != table_id:
            raise RuntimeError(
                f"recipe {RECIPE_ID} get/delete table pairing changed for {get_as}/{delete_as}"
            )
        if str(delete_input.get("ignore_not_found")) != "false":
            raise RuntimeError(f"recipe {RECIPE_ID} delete {delete_as} is no longer fail-fast")
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "table_ids": list(TABLE_IDS),
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


def seed_124656411(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_124656411(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be an explicitly-empty object "
            f"(payload-less scheduler tick); got {trigger!r}"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["lookup_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the lookup_table section; "
            f"got {sorted(seed_in.keys())}"
        )
    _require_lookup_section(seed_in["lookup_table"])
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole "
            "run instead of exercising a recipe branch"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "lookup_table": deepcopy(seed_in["lookup_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_124656411(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_124656411(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
    initial_snapshot = _snapshot(ctx)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = _snapshot(ctx)
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "expect": seed.get("expect"),
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_124656411(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_lookup_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.lookup_table must be exactly {{'tables': ...}}")
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted(TABLE_IDS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must declare exactly tables "
            f"{sorted(TABLE_IDS)} (either may be an explicit empty list)"
        )
    for table_id in TABLE_IDS:
        rows = tables[table_id]
        if not isinstance(rows, list):
            raise RuntimeError(f"recipe {RECIPE_ID} table {table_id} rows must be a list")
        for idx, row in enumerate(rows):
            if not isinstance(row, dict) or sorted(row.keys()) != sorted(ROW_COLUMNS):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table_id} row {idx} must carry exactly "
                    f"columns {sorted(ROW_COLUMNS)} (Workato lookup rows always expose "
                    f"every column); got {sorted(row.keys()) if isinstance(row, dict) else row!r}"
                )
            for column, value in row.items():
                if not isinstance(value, str):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} table {table_id} row {idx}.{column} must be a string"
                    )
            if not row["col1"].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table_id} row {idx} needs a non-empty col1 "
                    "(row identity for the purge ground truth)"
                )


def _normalize_tree(node: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "number": node.get("number"),
        "keyword": node.get("keyword"),
        "provider": node.get("provider") or "",
        "name": node.get("name") or "",
        "as": node.get("as") or "",
        "skip": bool(node.get("skip")),
    }
    if not out["skip"]:
        out["input"] = node.get("input")
    if node.get("keyword") == "foreach":
        out["repeat_mode"] = node.get("repeat_mode")
        out["source"] = node.get("source")
    if isinstance(node.get("filter"), dict):
        out["filter"] = node["filter"]
    out["block"] = [
        _normalize_tree(child) for child in node.get("block") or [] if isinstance(child, dict)
    ]
    return out


def _first_tree_mismatch(actual: Any, expected: Any, path: str = "root") -> str:
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            if key not in actual:
                return f"{path}.{key}: missing in raw recipe"
            if key not in expected:
                return f"{path}.{key}: unexpected in raw recipe"
            found = _first_tree_mismatch(actual[key], expected[key], f"{path}.{key}")
            if found:
                return found
        return ""
    if isinstance(expected, list) and isinstance(actual, list):
        if len(actual) != len(expected):
            return f"{path}: length {len(actual)} != {len(expected)}"
        for idx, (act, exp) in enumerate(zip(actual, expected)):
            found = _first_tree_mismatch(act, exp, f"{path}[{idx}]")
            if found:
                return found
        return ""
    if actual != expected:
        return f"{path}: {json.dumps(actual, default=str)[:200]} != {json.dumps(expected, default=str)[:200]}"
    return ""


def _walk_nodes(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        found.append(child)
        found.extend(_walk_nodes(child))
    return found


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return ctx.tools.call("harness.lookup_table.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
