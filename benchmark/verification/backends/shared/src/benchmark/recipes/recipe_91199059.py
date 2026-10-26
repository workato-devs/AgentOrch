from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_91199059


RECIPE_ID = "91199059"
TWIN_ID = "91199062"  # byte-identical raw recipe except trigger watchfield
SEED_TYPE = "sheets_review_lookup_sync_variant"
TRACK = "mock_lookup_table_customer_name_sync"
TRIGGER_PROVIDER = "google_sheets"
TRIGGER_NAME = "updated_polling_spreadsheet_row_v4_2"
TRIGGER_AS = "525668d3"
WATCHFIELD = "4"  # column 4 'PROPOSED NAME'
LOOKUP_TABLE_ID = "3256641"
TRIGGER_COLUMNS = ("col_1", "col_2", "col_3", "col_4", "col_5", "col_6", "col_7")


_RAW_PIN_JSON = r"""{"as": "525668d3", "block": [{"as": "", "block": [{"as": "88689055", "block": [], "input": {"lookup_table_id": "3256641", "parameters": {"col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"525668d3\",\"path\":[\"columns\", \"col_1\"]}')}"}}, "keyword": "action", "name": "search_entries", "number": 3, "provider": "lookup_table", "skip": false}, {"as": "5979d6fb", "block": [], "input": {"variables": {"data": {"in_lookup_table1": "=_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"88689055\",\"path\":[\"entries\",{\"path_element_type\":\"size\"}]}') == 0 ? false : true"}, "schema": "[{\"control_type\":\"text\",\"label\":\"final_proposed_name\",\"name\":\"final_proposed_name\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"final_proposed_name\"}},{\"control_type\":\"checkbox\",\"label\":\"in_lookup_table\",\"render_input\":{},\"parse_output\":{},\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"in_lookup_table\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"in_lookup_table1\",\"type\":\"boolean\",\"optional\":true,\"details\":{\"real_name\":\"in_lookup_table\"}},\"name\":\"in_lookup_table1\",\"type\":\"boolean\",\"optional\":true,\"details\":{\"real_name\":\"in_lookup_table\"}}]"}}, "keyword": "action", "name": "declare_variable", "number": 4, "provider": "workato_variable", "skip": false}, {"as": "9b7cd5e3", "block": [], "input": {"final_proposed_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"525668d3\",\"path\":[\"columns\", \"col_4\"]}')}", "name": "<anon>aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee</anon>:5979d6fb:final_proposed_name"}, "keyword": "action", "name": "update_variables", "number": 5, "provider": "workato_variable", "skip": false}, {"as": "", "block": [{"as": "714f4f35", "block": [], "input": {"id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"88689055\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}", "ignore_not_found": "false", "lookup_table_id": "3256641", "parameters": {"col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"525668d3\",\"path\":[\"columns\", \"col_1\"]}')}", "col3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"525668d3\",\"path\":[\"columns\", \"col_6\"]}')}", "col4": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"525668d3\",\"path\":[\"columns\", \"col_2\"]}')}", "col5": "=_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"525668d3\",\"path\":[\"columns\",\"col_2\"]}') == _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"5979d6fb\",\"path\":[\"final_proposed_name\"]}') ? \"\" : \"FLAGGED\"", "col6": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"5979d6fb\",\"path\":[\"final_proposed_name\"]}')}"}}, "keyword": "action", "name": "update_entry", "number": 7, "provider": "lookup_table", "skip": false}, {"as": "", "block": [{"as": "0fe2cc33", "block": [], "input": {"lookup_table_id": "3256641", "parameters": {"col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"525668d3\",\"path\":[\"columns\", \"col_1\"]}')}", "col3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"525668d3\",\"path\":[\"columns\", \"col_6\"]}')}", "col4": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"525668d3\",\"path\":[\"columns\", \"col_2\"]}')}", "col5": "=_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"525668d3\",\"path\":[\"columns\",\"col_2\"]}') == _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"5979d6fb\",\"path\":[\"final_proposed_name\"]}') ? \"\" : \"FLAGGED\"", "col6": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"5979d6fb\",\"path\":[\"final_proposed_name\"]}')}"}}, "keyword": "action", "name": "add_entry", "number": 9, "provider": "lookup_table", "skip": false}], "input": {}, "keyword": "else", "name": "", "number": 8, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"5979d6fb\",\"path\":[\"in_lookup_table1\"]}')}", "operand": "is_true", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 6, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"525668d3\",\"path\":[\"columns\",\"col_5\"]}').downcase", "operand": "equals_to", "rhs": "true"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 2, "provider": "", "skip": false}], "input": {"___poll_interval": "5", "sheet": "Sheet1", "spreadsheet": "<anon>2AbC3DeF4GhI5JkL6MnO7PqR8StU9VwX0YzA1BcD2EfG</anon>", "watchfield": "4"}, "keyword": "trigger", "name": "updated_polling_spreadsheet_row_v4_2", "number": 1, "provider": "google_sheets", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

_IF2_LHS = (
    "=_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\","
    "\"line\":\"525668d3\",\"path\":[\"columns\",\"col_5\"]}').downcase"
)
_DECLARE_IN_LOOKUP = (
    "=_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\","
    "\"line\":\"88689055\",\"path\":[\"entries\",{\"path_element_type\":\"size\"}]}')"
    " == 0 ? false : true"
)
_COL5_TERNARY = (
    "=_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\","
    "\"line\":\"525668d3\",\"path\":[\"columns\",\"col_2\"]}') == "
    "_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\","
    "\"line\":\"5979d6fb\",\"path\":[\"final_proposed_name\"]}') ? \"\" : \"FLAGGED\""
)
_UPDATE_VARIABLES_TARGET = "<anon>aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee</anon>:5979d6fb:final_proposed_name"

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("88689055", "lookup_table", "search_entries"),
    ("5979d6fb", "workato_variable", "declare_variable"),
    ("9b7cd5e3", "workato_variable", "update_variables"),
    ("714f4f35", "lookup_table", "update_entry"),
    ("0fe2cc33", "lookup_table", "add_entry"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "workato_runtime.declare_variable",
    "workato_runtime.update_variables",
    "lookup_table.update_entry",
    "lookup_table.add_entry",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "lookup_table.update_entry",
    "lookup_table.add_entry",
]


def validate_91199059(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    trigger_cfg = raw.get("input") or {}
    if str(trigger_cfg.get("watchfield") or "") != WATCHFIELD:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger watchfield changed: {trigger_cfg.get('watchfield')!r} "
            f"(this twin watches column {WATCHFIELD}; twin {TWIN_ID} differs only here)"
        )
    if str(trigger_cfg.get("sheet") or "") != "Sheet1":
        raise RuntimeError(f"recipe {RECIPE_ID} trigger sheet changed: {trigger_cfg.get('sheet')!r}")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    by_as = {str(a.get("as")): a for a in actions}
    if by_as["88689055"]["input"]["lookup_table_id"] != LOOKUP_TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} search lookup table changed")
    declared = by_as["5979d6fb"]["input"]["variables"]["data"]
    if declared != {"in_lookup_table1": _DECLARE_IN_LOOKUP}:
        raise RuntimeError(f"recipe {RECIPE_ID} declare_variable data drifted: {declared!r}")
    if by_as["9b7cd5e3"]["input"]["name"] != _UPDATE_VARIABLES_TARGET:
        raise RuntimeError(f"recipe {RECIPE_ID} update_variables target drifted")
    for write_as in ("714f4f35", "0fe2cc33"):
        params = by_as[write_as]["input"]["parameters"]
        if params["col5"] != _COL5_TERNARY:
            raise RuntimeError(f"recipe {RECIPE_ID} step {write_as} col5 ternary drifted: {params['col5']!r}")
        if by_as[write_as]["input"]["lookup_table_id"] != LOOKUP_TABLE_ID:
            raise RuntimeError(f"recipe {RECIPE_ID} step {write_as} lookup table changed")
    if by_as["714f4f35"]["input"]["ignore_not_found"] != "false":
        raise RuntimeError(f"recipe {RECIPE_ID} update_entry ignore_not_found drifted")
    blocks = raw.get("block") or []
    if_two = blocks[0] if blocks else {}
    conditions = ((if_two.get("input") or {}).get("conditions") or [{}])
    if (
        if_two.get("keyword") != "if"
        or conditions[0].get("lhs") != _IF2_LHS
        or conditions[0].get("operand") != "equals_to"
        or conditions[0].get("rhs") != "true"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} approval IF condition drifted: {conditions!r}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "watchfield": WATCHFIELD,
        "lookup_table_id": LOOKUP_TABLE_ID,
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


def seed_91199059(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_91199059(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["lookup_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the lookup_table section; "
            f"got {sorted(seed_in.keys())}"
        )
    _require_lookup_section(seed_in["lookup_table"])
    if data.get("now") not in (None, ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} reads no clock; variants must not pin 'now'"
        )
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
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


def run_91199059(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_91199059(raw)
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
    result["verifier"] = verify_91199059(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != ["columns"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the columns object; "
            f"got {sorted(trigger.keys())}"
        )
    columns = trigger["columns"]
    if not isinstance(columns, dict) or sorted(columns.keys()) != sorted(TRIGGER_COLUMNS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger columns must pin exactly col_1..col_7; "
            f"got {sorted(columns.keys()) if isinstance(columns, dict) else columns!r}"
        )
    for col in TRIGGER_COLUMNS:
        if not isinstance(columns[col], str):
            raise RuntimeError(f"recipe {RECIPE_ID} trigger column {col} must be a string")
    if not columns["col_5"].strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger col_5 (Reviewed?) must be an explicit string "
            "('TRUE'/'FALSE'/... -- never blank, the recipe downcases it)"
        )


def _require_lookup_section(section: Any) -> None:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed.lookup_table must be an object")
    unknown = sorted(set(section.keys()) - {"tables"})
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.lookup_table has unknown keys: {unknown}")
    tables = section.get("tables")
    if not isinstance(tables, dict) or sorted(tables.keys()) != [LOOKUP_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must declare exactly table {LOOKUP_TABLE_ID!r}"
        )
    rows = tables[LOOKUP_TABLE_ID]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} lookup table seed must be a row list")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} lookup row {idx} must be an object")
        if not isinstance(row.get("_row_id"), int):
            raise RuntimeError(
                f"recipe {RECIPE_ID} lookup row {idx} must pin an explicit integer _row_id "
                "(update_entry threads entries.first.id deterministically)"
            )
        if not isinstance(row.get("col1"), str) or not row["col1"].strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} lookup row {idx} requires non-empty string col1 "
                "(ACCOUNT ID search key)"
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
        return (
            f"{path}: {json.dumps(actual, default=str)[:200]} != "
            f"{json.dumps(expected, default=str)[:200]}"
        )
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


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return ctx.tools.call("harness.lookup_table.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
