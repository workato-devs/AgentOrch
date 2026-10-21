from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_124859961


RECIPE_ID = "124859961"
SEED_TYPE = "slack_dynamic_menu_project_configurations_variant"
TRACK = "workato_internal_dynamic_menu_project_configurations"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "dynamic_menu"
TRIGGER_AS = "4cb4b049"
DYNAMIC_MENU_NAME = "Project Configurations"
LOOKUP_TABLE_ID = "4075676"
SEARCH_STEP_AS = "7a232762"
LIST_STEP_AS = "6542744e"
PARSE_STEP_AS = "40ba5cbd"
INSERT_STEP_AS = "dc53ac23"
MENU_STEP_AS = "b71c5543"
FOREACH_AS = "d2a427df"
# TWIN NOTE: 124862303 is an exact twin of this recipe (diff verified against
# both raw_recipe.md files): only the lookup_table_id (4079230 there vs
# 4075676 here), flow metadata and the trigger `parameters` JSON whitespace
# differ. Each module pins ITS OWN table id and verbatim raw tree so twin
# drift between the two deployed recipes is caught by validation, never
# papered over.

# slack_bot.dynamic_menu 'Project Configurations' (trigger as 4cb4b049; the
# payload carries typeahead.value + required parameters {asset_env,
# asset_type}):
#   2  lookup_table.search_entries 7a232762 table 4075676
#      'CICD | LT | Project Configuration' (col1 Id, col2 Project Name,
#      col3 Asset Environment, col4 Asset Id, col5 Asset Type, col6 Project
#      Context JSON, col7 Notification Settings, col8 Dependencies, col9
#      Target Folder Details, col10 Last Updated) with col3 = asset_env and
#      col5 = asset_type -- the search NARROWS the table before any matching.
#   3  workato_variable.declare_list 6542744e 'project_list'
#      {project_name, id}
#   IF 4 (typeahead.value present -- a blank typeahead SKIPS the whole scan):
#     FOREACH 5 (as d2a427df) over the search entries, repeat_mode simple:
#       6  json_parser.parse_json 40ba5cbd, document = entry col6 (the
#          'Project Context' JSON string, schema {release_name}) -- parse
#          runs for EVERY narrowed entry, matching or not; empty/invalid
#          col6 errors the job exactly like Workato.
#       IF 7 (compound OR): col2.downcase contains typeahead.downcase OR
#          (release_name.present? ? release_name.downcase : "") contains
#          typeahead.downcase:
#         8  workato_variable.insert_to_list dc53ac23 into project_list:
#            id = entry col1, project_name = release_name.present? ?
#            "#{release_name} (project: #{col2})"[0...70] : col2 -- the
#            label ternary keys on release PRESENCE (not on which OR arm
#            matched) and the true arm is an interpolated-string literal
#            sliced with Ruby EXCLUSIVE range [0...70] (max 70 chars).
#   9  slack_bot.generate_menu_options b71c5543 (ALWAYS runs): options
#      ____source = project_list items, label = project_name, value = id;
#      an empty list is a valid [] options payload.
#
# All backends are Workato-internal (lookup table read-only + variable list +
# json_parser + deterministic menu payload): mock per backend policy, no
# cleanup (every variant seeds table 4075676 explicitly and the recipe
# never writes to it).

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "slack_bot", "name": "dynamic_menu", "as": "4cb4b049", "skip": false, "input": {"dynamic_menu_name": "Project Configurations", "parameters": "[{\"name\":\"asset_env\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Asset env\"},{\"name\":\"asset_type\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Asset type\"}]"}, "block": [{"number": 2, "keyword": "action", "provider": "lookup_table", "name": "search_entries", "as": "7a232762", "skip": false, "input": {"lookup_table_id": "4075676", "parameters": {"col3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"4cb4b049\",\"path\":[\"parameters\", \"asset_env\"]}')}", "col5": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"4cb4b049\",\"path\":[\"parameters\", \"asset_type\"]}')}"}}, "block": []}, {"number": 3, "keyword": "action", "provider": "workato_variable", "name": "declare_list", "as": "6542744e", "skip": false, "input": {"list_item_schema_json": "[{\"name\":\"project_name\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Project name\"},{\"name\":\"id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"ID\"}]", "name": "project_list"}, "block": []}, {"number": 4, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"4cb4b049\",\"path\":[\"typeahead\", \"value\"]}')}", "operand": "present", "rhs": ""}], "operand": "and", "type": "compound"}, "block": [{"number": 5, "keyword": "foreach", "provider": "", "name": "", "as": "d2a427df", "skip": false, "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"7a232762\",\"path\":[\"entries\"]}')}"}, "repeat_mode": "simple", "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"7a232762\",\"path\":[\"entries\"]}')}", "block": [{"number": 6, "keyword": "action", "provider": "json_parser", "name": "parse_json", "as": "40ba5cbd", "skip": false, "input": {"document": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"d2a427df\",\"path\":[\"entry\", \"col6\"]}')}", "sample_document": "{\"release_name\":\"\"}"}, "block": []}, {"number": 7, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"d2a427df\",\"path\":[\"entry\",\"col2\"]}').downcase", "operand": "contains", "rhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"4cb4b049\",\"path\":[\"typeahead\",\"value\"]}').downcase"}, {"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"json_parser\",\"line\":\"40ba5cbd\",\"path\":[\"document\",\"release_name\"]}').present? ? _dp('{\"pill_type\":\"output\",\"provider\":\"json_parser\",\"line\":\"40ba5cbd\",\"path\":[\"document\",\"release_name\"]}').downcase : \"\"", "operand": "contains", "rhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"4cb4b049\",\"path\":[\"typeahead\",\"value\"]}').downcase"}], "operand": "or", "type": "compound"}, "block": [{"number": 8, "keyword": "action", "provider": "workato_variable", "name": "insert_to_list", "as": "dc53ac23", "skip": false, "input": {"list_item": {"id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"d2a427df\",\"path\":[\"entry\", \"col1\"]}')}", "project_name": "=_dp('{\"pill_type\":\"output\",\"provider\":\"json_parser\",\"line\":\"40ba5cbd\",\"path\":[\"document\",\"release_name\"]}').present? ? \"#{_dp('{\"pill_type\":\"output\",\"provider\":\"json_parser\",\"line\":\"40ba5cbd\",\"path\":[\"document\",\"release_name\"]}')} (project: #{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"d2a427df\",\"path\":[\"entry\",\"col2\"]}')})\"[0...70] : _dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"d2a427df\",\"path\":[\"entry\",\"col2\"]}')"}, "location": "end", "name": "2d44bf57-2877-4a8e-8d84-8f9918ed193e:6542744e"}, "block": []}]}]}]}, {"number": 9, "keyword": "action", "provider": "slack_bot", "name": "generate_menu_options", "as": "b71c5543", "skip": false, "input": {"options": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"6542744e\",\"path\":[\"list_items\"]}')}", "label": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"6542744e\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"project_name\"]}')}", "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"6542744e\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}"}, "use_option_groups": "false"}, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (SEARCH_STEP_AS, "lookup_table", "search_entries"),
    (LIST_STEP_AS, "workato_variable", "declare_list"),
    (PARSE_STEP_AS, "json_parser", "parse_json"),
    (INSERT_STEP_AS, "workato_variable", "insert_to_list"),
    (MENU_STEP_AS, "slack_bot", "generate_menu_options"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "workato_runtime.declare_list",
    "workato_runtime.parse_json",
    "workato_runtime.insert_to_list",
    "slack_bot.generate_menu_options",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "slack_bot.generate_menu_options",
]
ROW_COLUMNS = ("col1", "col2", "col3", "col4", "col5", "col6", "col7", "col8", "col9", "col10")
REQUIRED_ROW_COLUMNS = ("col1", "col2", "col3", "col5", "col6")
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "lookup_call_args",
    "parsed_documents",
    "final_list_items",
    "menu_options",
)


def validate_124859961(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    if str((raw.get("input") or {}).get("dynamic_menu_name") or "") != DYNAMIC_MENU_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} dynamic menu name changed")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    # Twin-drift guard: the lookup search must target THIS recipe's table id
    # (the 124862303 twin differs only here).
    for node in _walk_nodes(raw):
        if node.get("provider") == "lookup_table":
            table = str((node.get("input") or {}).get("lookup_table_id") or "")
            if table != LOOKUP_TABLE_ID:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} lookup step {node.get('as')!r} targets table "
                    f"{table!r}, expected {LOOKUP_TABLE_ID!r} (twin drift?)"
                )
    # Semantic pin on the label formula: the true arm must stay the
    # interpolated-string literal with the EXCLUSIVE [0...70] range slice and
    # the false arm the bare col2 pill (the tree pin holds the exact bytes;
    # this guard names the trap when it drifts).
    insert = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == INSERT_STEP_AS),
        None,
    )
    if not isinstance(insert, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} insert step {INSERT_STEP_AS} missing")
    label_formula = str(((insert.get("input") or {}).get("list_item") or {}).get("project_name") or "")
    if (
        "[0...70]" not in label_formula
        or ".present? ?" not in label_formula
        or " (project: " not in label_formula
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} project_name label ternary changed: {label_formula!r}"
        )
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "dynamic_menu_name": DYNAMIC_MENU_NAME,
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


def seed_124859961(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_124859961(raw)
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
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is missing required keys: {missing}"
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


def run_124859961(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_124859961(raw)
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
    result["verifier"] = verify_124859961(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != ["parameters", "typeahead"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly typeahead + parameters; "
            f"got {sorted(trigger.keys())}"
        )
    typeahead = trigger.get("typeahead")
    if (
        not isinstance(typeahead, dict)
        or sorted(typeahead.keys()) != ["value"]
        or not isinstance(typeahead.get("value"), str)
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.typeahead must be {{'value': <str>}} "
            "(an explicitly-blank value exercises the IF-4-false skip branch)"
        )
    parameters = trigger.get("parameters")
    if (
        not isinstance(parameters, dict)
        or sorted(parameters.keys()) != ["asset_env", "asset_type"]
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.parameters must carry exactly asset_env + "
            f"asset_type (both required by the dynamic-menu schema); got {parameters!r}"
        )
    for key in ("asset_env", "asset_type"):
        if not isinstance(parameters.get(key), str) or not parameters[key].strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger parameters.{key} must be a non-empty string "
                "(it feeds the col3/col5 lookup search verbatim)"
            )


def _require_lookup_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.lookup_table must be exactly {{'tables': ...}}")
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [LOOKUP_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must declare exactly table "
            f"{LOOKUP_TABLE_ID!r} (rows may be an explicit empty list)"
        )
    rows = tables[LOOKUP_TABLE_ID]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {LOOKUP_TABLE_ID} rows must be a list")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table row {idx} must be an object")
        unknown = sorted(set(row.keys()) - set(ROW_COLUMNS))
        if unknown:
            raise RuntimeError(f"recipe {RECIPE_ID} table row {idx} has unknown columns: {unknown}")
        for column, value in row.items():
            if not isinstance(value, str):
                raise RuntimeError(f"recipe {RECIPE_ID} table row {idx}.{column} must be a string")
        for column in REQUIRED_ROW_COLUMNS:
            if not isinstance(row.get(column), str) or not row[column].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table row {idx} requires non-empty string {column} "
                    "(id/name/env/type/context feed the search + list mappings)"
                )
        # Fail-fast on unparseable Project Context: the recipe json-parses col6
        # for EVERY entry the foreach touches, and Workato errors the job on
        # empty/invalid JSON. Every seeded row must be parse-safe with a string
        # release_name so which rows get scanned stays behavior, not seed luck.
        try:
            document = json.loads(row["col6"])
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx}.col6 must be a valid JSON document: {exc}"
            ) from exc
        if not isinstance(document, dict) or not isinstance(document.get("release_name"), str):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx}.col6 must be a JSON object with a "
                f"string release_name (may be blank); got {row['col6']!r}"
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
