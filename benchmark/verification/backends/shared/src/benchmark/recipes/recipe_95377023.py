from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_95377023


RECIPE_ID = "95377023"
SEED_TYPE = "recipe_function_entity_default_apps_variant"
TRACK = "workato_recipe_function_entity_default_apps"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "5719e98e"
ENTITY_TABLE = "ENTITY"
APP_TABLE = "APP"
EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("fc223579", "workato_variable", "declare_list"),
    ("6a22d653", "snowflake", "search_rows_sql"),
    ("a8485e20", "workato_variable", "insert_to_list"),
    ("a140d0a9", "workato_variable", "declare_list"),
    ("56fca8b7", "snowflake", "search_rows_sql"),
    ("a0b09532", "workato_smart_list", "create_list"),
    ("e81c59ef", "workato_smart_list", "query_list"),
    ("e36f0750", "workato_variable", "insert_to_list"),
    ("4ec6a0f1", "workato_recipe_function", "return_result"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_list",
    "snowflake.search_rows_sql",
    "workato_runtime.insert_to_list",
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_recipe_function.return_result",
]
REQUIRED_TABLE_COLUMNS: dict[str, set[str]] = {
    ENTITY_TABLE: {"id", "name", "alpha3code", "status", "parent_id"},
    APP_TABLE: {"id", "name", "status"},
}

_RAW_PIN_JSON = r"""{"as": "5719e98e", "block": [{"as": "fc223579", "block": [], "input": {"list_item_schema_json": "[{\"control_type\":\"text\",\"label\":\"App ID\",\"name\":\"app_id\",\"type\":\"string\",\"optional\":false}]", "name": "Default App IDs"}, "keyword": "action", "name": "declare_list", "number": 2, "provider": "workato_variable", "skip": false}, {"as": "6a22d653", "block": [], "input": {"limit": "1", "output_schema": "[{\"name\":\"ENTITY_ID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"ENTITY ID\"},{\"name\":\"ENTITY_NAME\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"ENTITY NAME\"},{\"name\":\"ENTITY_ALPHA3CODE\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"ENTITY ALPHA 3 CODE\"},{\"name\":\"ENTITY_STATUS\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"ENTITY STATUS\"},{\"name\":\"PARENT_ENTITY_ID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"PARENT ENTITY ID\"},{\"name\":\"PARENT_ENTITY_NAME\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"PARENT ENTITY NAME\"}]", "parameters": {"data": {"entity_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"5719e98e\",\"path\":[\"parameters\", \"entity_id\"]}')}"}, "schema": "[{\"name\":\"entity_id\",\"type\":\"string\",\"optional\":true,\"label\":\"Entity ID\",\"control_type\":\"text\"}]"}, "sql": "SELECT\nEE.ID AS ENTITY_ID,\nEE.NAME AS ENTITY_NAME,\nEE.ALPHA3CODE AS ENTITY_ALPHA3CODE,\nEE.STATUS AS ENTITY_STATUS,\nP.ID AS PARENT_ENTITY_ID,\nP.NAME AS PARENT_ENTITY_NAME\n\nFROM ENTITY EE\nLEFT JOIN ENTITY P\nON EE.PARENT_ID = P.ID\n\nWHERE EE.ID = :entity_id"}, "keyword": "action", "name": "search_rows_sql", "number": 3, "provider": "snowflake", "skip": false}, {"as": "", "block": [{"as": "", "block": [], "input": {"stop_reason": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"6a22d653\",\"path\":[\"rows\",{\"path_element_type\":\"size\"}]}') != 1\n  \"Failed to evaluate Entity\"\nelse\n  \"Entity is not Active\"\nend", "stop_with_error": "true"}, "keyword": "stop", "name": "", "number": 5, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"6a22d653\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}", "operand": "not_equals_to", "rhs": "1"}, {"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"6a22d653\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"entity_status\"]}')}", "operand": "not_equals_to", "rhs": "Active"}], "operand": "or", "type": "compound"}, "keyword": "if", "name": "", "number": 4, "provider": "", "skip": false}, {"as": "", "block": [{"as": "a8485e20", "block": [], "input": {"list_item": {"app_id": "A212"}, "location": "end", "name": "7d8233a9-d4fa-42d4-9314-da093ed1c57a:fc223579"}, "keyword": "action", "name": "insert_to_list", "number": 7, "provider": "workato_variable", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"5719e98e\",\"path\":[\"parameters\", \"entity_id\"]}')}", "operand": "equals_to", "rhs": "E3"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 6, "provider": "", "skip": false}, {"as": "a140d0a9", "block": [], "input": {"list_item_schema_json": "[{\"control_type\":\"text\",\"label\":\"App ID\",\"name\":\"app_id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"App Name\",\"name\":\"app_name\",\"type\":\"string\",\"optional\":false}]", "name": "Final Apps List"}, "keyword": "action", "name": "declare_list", "number": 8, "provider": "workato_variable", "skip": false}, {"as": "", "block": [{"as": "56fca8b7", "block": [], "input": {"limit": "50000", "output_schema": "[{\"control_type\":\"text\",\"label\":\"APP ID\",\"name\":\"APP_ID\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"APP NAME\",\"name\":\"APP_NAME\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"STATUS\",\"name\":\"STATUS\",\"type\":\"string\",\"optional\":false}]", "sql": "SELECT\nA.ID AS APP_ID,\nA.NAME AS APP_NAME,\nA.STATUS\n\nFROM APP A"}, "keyword": "action", "name": "search_rows_sql", "number": 10, "provider": "snowflake", "skip": false}, {"as": "a0b09532", "block": [], "input": {"force": "true", "list_name": "APP_ENTITY", "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"56fca8b7\",\"path\":[\"rows\"]}')", "primary_index": "app_id"}, "keyword": "action", "name": "create_list", "number": 11, "provider": "workato_smart_list", "skip": false}, {"as": "fe33f6f6", "block": [{"as": "e81c59ef", "block": [], "input": {"col_sep": "comma", "csv": "false", "headers": "false", "output_schema_by": "index", "result_schema_json": "[{\"control_type\":\"text\",\"label\":\"App ID\",\"name\":\"app_id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"App Name\",\"name\":\"app_name\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Status\",\"name\":\"status\",\"type\":\"string\",\"optional\":false}]", "sql": "SELECT * FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"a0b09532\",\"path\":[\"list_name\"]}')}\nWHERE APP_ID = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"fe33f6f6\",\"path\":[\"app_id\"]}')}'"}, "keyword": "action", "name": "query_list", "number": 13, "provider": "workato_smart_list", "skip": false}, {"as": "", "block": [{"as": "", "block": [], "input": {"stop_reason": "Inactive app evaluated: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"e81c59ef\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"app_name\"]}')}", "stop_with_error": "true"}, "keyword": "stop", "name": "", "number": 15, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"e81c59ef\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"status\"]}')}", "operand": "not_equals_to", "rhs": "Active"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 14, "provider": "", "skip": false}, {"as": "e36f0750", "block": [], "input": {"list_item": {"app_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"e81c59ef\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"app_id\"]}')}", "app_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"e81c59ef\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"app_name\"]}')}"}, "location": "end", "name": "eaf6eed0-db75-45e2-bf41-de6c8283830f:a140d0a9"}, "keyword": "action", "name": "insert_to_list", "number": 16, "provider": "workato_variable", "skip": false}], "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"fc223579\",\"path\":[\"list_items\"]}')}"}, "keyword": "foreach", "name": "", "number": 12, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"fc223579\",\"path\":[\"list_items\", {\"path_element_type\": \"size\"}]}')}", "operand": "greater_than", "rhs": "0"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 9, "provider": "", "skip": false}, {"as": "4ec6a0f1", "block": [], "input": {"result": {"apps": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"a140d0a9\",\"path\":[\"list_items\"]}')}", "app_id": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"a140d0a9\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"app_id\"]}').presence or nil", "app_name": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"a140d0a9\",\"path\":[\"list_items\",{\"path_element_type\":\"current_item\"},\"app_name\"]}').presence or nil"}}}, "keyword": "action", "name": "return_result", "number": 17, "provider": "workato_recipe_function", "skip": false}], "input": {"parameters_schema_json": "[{\"name\":\"entity_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"}]", "result_schema_json": "[{\"name\":\"apps\",\"type\":\"array\",\"of\":\"object\",\"label\":\"Apps\",\"optional\":false,\"properties\":[{\"control_type\":\"text\",\"label\":\"App ID\",\"name\":\"app_id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"App Name\",\"name\":\"app_name\",\"type\":\"string\",\"optional\":false}]}]"}, "keyword": "trigger", "name": "execute", "number": 1, "provider": "workato_recipe_function", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)


def validate_95377023(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    schema_json = str((raw.get("input") or {}).get("parameters_schema_json") or "")
    if '"name":"entity_id"' not in schema_json:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter schema changed")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
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


def seed_95377023(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_95377023(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input requires a parameters object")
    entity_id = parameters.get("entity_id")
    if not isinstance(entity_id, str) or not entity_id.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger input requires a non-empty string parameters.entity_id"
        )
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    snowflake_seed = seed_in.get("snowflake_live")
    _require_snowflake_tables(snowflake_seed)
    provision = ctx.tools.call("harness.snowflake_live.seed_tables", {"snowflake": snowflake_seed})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "expect": deepcopy(expect),
        "raw_validation": validation,
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_95377023(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_95377023(raw)
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live section")
    initial_snapshot = ctx.tools.call("harness.snowflake.snapshot", {})
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    snowflake_cleanup: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = ctx.tools.call("harness.snowflake.snapshot", {})
    finally:
        snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
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
            "cleanup_response": {"snowflake_live": snowflake_cleanup},
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_95377023(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_snowflake_tables(snowflake_seed: Any) -> None:
    if not isinstance(snowflake_seed, dict) or not isinstance(snowflake_seed.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.snowflake_live.tables")
    tables = snowflake_seed["tables"]
    if sorted(tables.keys()) != sorted(REQUIRED_TABLE_COLUMNS.keys()):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the snowflake tables "
            f"{sorted(REQUIRED_TABLE_COLUMNS)} (exact keys); got {sorted(tables.keys())}"
        )
    for table, required_columns in REQUIRED_TABLE_COLUMNS.items():
        spec = tables.get(table)
        if not isinstance(spec, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} snowflake_live.tables[{table!r}] must be an object")
        columns = spec.get("columns")
        if not isinstance(columns, dict) or not all(
            isinstance(kind, str) and kind.strip() for kind in columns.values()
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} snowflake_live table {table} must declare explicit column types"
            )
        declared = {str(name).strip().lower() for name in columns}
        if declared != required_columns:
            raise RuntimeError(
                f"recipe {RECIPE_ID} snowflake_live table {table} must declare exactly the "
                f"columns {sorted(required_columns)} (the pinned SQL reads them); got {sorted(declared)}"
            )
        rows = spec.get("rows")
        if not isinstance(rows, list):
            raise RuntimeError(
                f"recipe {RECIPE_ID} snowflake_live table {table} must declare rows (may be empty)"
            )
        for row in rows:
            if not isinstance(row, dict):
                raise RuntimeError(f"recipe {RECIPE_ID} snowflake_live table {table} rows must be objects")
            extra = {str(key).strip().lower() for key in row} - declared
            if extra:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} snowflake_live table {table} row uses undeclared columns: {sorted(extra)}"
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


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
