from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_127706060


RECIPE_ID = "127706060"
SEED_TYPE = "slack_dynamic_menu_job_titles_variant"
TRACK = "workato_internal_dynamic_menu_job_titles"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "dynamic_menu"
TRIGGER_AS = "a0a517ed"
DYNAMIC_MENU_NAME = "List of Job Titles"
LOOKUP_TABLE_ID = "3127963"
# TWIN NOTE: 127703856 is an exact twin of this recipe (diff verified against
# both raw_recipe.md files): only the lookup_table_id (3110102 there vs 3127963
# here), flow metadata and the trigger `parameters` JSON whitespace differ.
# Each module pins ITS OWN table id and verbatim raw tree so twin drift between
# the two deployed recipes is caught by validation, never papered over.

# slack_bot.dynamic_menu 'List of Job Titles' (trigger as a0a517ed; payload
# carries typeahead.value + parameters {return (required 'title'|'id'),
# status?, job_family_group_name?}):
#   2  declare_list 101b8c3e 'Job Titles' (job_title_id, job_title, status)
#   IF 3 (formula lhs '=_dp(parameters)' present -- {} is NOT present):
#     4  lookup_table.search_entries bd56b813 table 3127963
#        col3 = parameters.status.presence or skip
#        col5 = parameters.job_family_group_name.presence or skip
#        (both skipped -> the SEARCH returns the whole table; this is still
#        the search branch, distinct from the parameters-absent fallback)
#     IF 5 (search entries size > 0; NO else of its own -- a 0-hit search
#           inserts NOTHING and the recipe ends after the lookups):
#       6  insert_to_list_batch 1ce145fe (job_title_id=col1, job_title=col2,
#          status=col3 -- CORRECT col1 mapping on this branch)
#   ELSE 7 (else OF IF 3, i.e. parameters ABSENT -- the raw JSON nests every
#           else inside its OWNING if's block; verified corpus-wide: all 184
#           else nodes are direct children of if nodes, so the triage's
#           reading of this else as IF 5's search-empty fallback was wrong):
#     8  lookup_table.get_entries b7e70bfd (full table 3127963)
#     IF 9 (get entries size > 0):
#       10 insert_to_list_batch a0a73f92 -- RAW-RECIPE AUTHOR BUG replayed
#          verbatim: job_title_id is mapped from entry col2 (the job TITLE,
#          same source as job_title), not col1. Observable in the final list
#          state (job_title_id == job_title); on this parameters-absent path
#          parameters.return is unreadable (MISSING != 'id') so the menu
#          value formula always takes the title arm. Pinned in validation and
#          in the per-variant expects; DO NOT FIX.
#   IF 11 (101b8c3e list size > 0):
#     12 workato_smart_list.create_list 06c4d839 JOB_TITLES force=true
#        primary_index=job_title_id, source = variable list
#     13 query_list bc713a22: SELECT DISTINCT * FROM <list_name>
#        WHERE LOWER(JOB_TITLE) LIKE LOWER('%<typeahead.value>%')
#        ORDER BY JOB_TITLE ASC
#     14 slack_bot.generate_menu_options f17938bf (options ____source = query
#        rows; label = job_title; value = multiline Ruby if/else/end:
#        parameters.return == "id" ? row.job_title_id : row.job_title)
#
# All backends are Workato-internal (lookup table read-only + smart list +
# variable list + deterministic menu payload): mock per backend policy, no
# cleanup (every variant seeds table 3127963 explicitly and the recipe never
# writes to it).

_RAW_PIN_JSON = r"""{"as": "a0a517ed", "block": [{"as": "101b8c3e", "block": [], "input": {"list_item_schema_json": "[{\"name\":\"job_title_id\",\"type\":\"string\",\"optional\":false,\"label\":\"Job Title ID\",\"control_type\":\"text\"},{\"name\":\"job_title\",\"type\":\"string\",\"optional\":false,\"label\":\"Job Title\",\"control_type\":\"text\"},{\"name\":\"status\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Status\"}]", "name": "Job Titles"}, "keyword": "action", "name": "declare_list", "number": 2, "provider": "workato_variable", "skip": false}, {"as": "", "block": [{"as": "bd56b813", "block": [], "input": {"lookup_table_id": "3127963", "parameters": {"col3": "=_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"a0a517ed\",\"path\":[\"parameters\",\"status\"]}').presence or skip", "col5": "=_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"a0a517ed\",\"path\":[\"parameters\",\"job_family_group_name\"]}').presence or skip"}}, "keyword": "action", "name": "search_entries", "number": 4, "provider": "lookup_table", "skip": false}, {"as": "", "block": [{"as": "1ce145fe", "block": [], "input": {"list_items": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"bd56b813\",\"path\":[\"entries\"]}')}", "job_title": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"bd56b813\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col2\"]}')}", "job_title_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"bd56b813\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col1\"]}')}", "status": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"bd56b813\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col3\"]}')}"}, "location": "end", "name": "ff628842-cdb8-44ce-818e-6caae7d5b490:101b8c3e"}, "keyword": "action", "name": "insert_to_list_batch", "number": 6, "provider": "workato_variable", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"bd56b813\",\"path\":[\"entries\", {\"path_element_type\": \"size\"}]}')}", "operand": "greater_than", "rhs": "0"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 5, "provider": "", "skip": false}, {"as": "", "block": [{"as": "b7e70bfd", "block": [], "input": {"lookup_table_id": "3127963"}, "keyword": "action", "name": "get_entries", "number": 8, "provider": "lookup_table", "skip": false}, {"as": "", "block": [{"as": "a0a73f92", "block": [], "input": {"list_items": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"b7e70bfd\",\"path\":[\"entries\"]}')}", "job_title": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"b7e70bfd\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col2\"]}')}", "job_title_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"b7e70bfd\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col2\"]}')}", "status": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"b7e70bfd\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col3\"]}')}"}, "location": "end", "name": "ff628842-cdb8-44ce-818e-6caae7d5b490:101b8c3e"}, "keyword": "action", "name": "insert_to_list_batch", "number": 10, "provider": "workato_variable", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"b7e70bfd\",\"path\":[\"entries\", {\"path_element_type\": \"size\"}]}')}", "operand": "greater_than", "rhs": "0"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 9, "provider": "", "skip": false}], "input": {}, "keyword": "else", "name": "", "number": 7, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"a0a517ed\",\"path\":[\"parameters\"]}')", "operand": "present", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 3, "provider": "", "skip": false}, {"as": "", "block": [{"as": "06c4d839", "block": [], "input": {"force": "true", "list_name": "JOB_TITLES", "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"101b8c3e\",\"path\":[\"list_items\"]}')", "primary_index": "job_title_id"}, "keyword": "action", "name": "create_list", "number": 12, "provider": "workato_smart_list", "skip": false}, {"as": "bc713a22", "block": [], "input": {"col_sep": "comma", "csv": "false", "headers": "false", "output_schema_by": "index", "result_schema_json": "[{\"name\":\"job_title_id\",\"type\":\"string\",\"optional\":false,\"label\":\"Job Title ID\",\"control_type\":\"text\"},{\"name\":\"job_title\",\"type\":\"string\",\"optional\":false,\"label\":\"Job Title\",\"control_type\":\"text\"},{\"name\":\"status\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Status\"}]", "sql": "SELECT DISTINCT * FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"06c4d839\",\"path\":[\"list_name\"]}')}\nWHERE LOWER(JOB_TITLE) LIKE LOWER('%#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"a0a517ed\",\"path\":[\"typeahead\", \"value\"]}')}%')\n\nORDER BY JOB_TITLE ASC"}, "keyword": "action", "name": "query_list", "number": 13, "provider": "workato_smart_list", "skip": false}, {"as": "f17938bf", "block": [], "input": {"options": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"bc713a22\",\"path\":[\"rows\"]}')}", "label": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"bc713a22\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"job_title\"]}')}", "value": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"a0a517ed\",\"path\":[\"parameters\",\"return\"]}') == \"id\"\n  _dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"bc713a22\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"job_title_id\"]}')\nelse\n  _dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"bc713a22\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"job_title\"]}')\nend"}, "use_option_groups": "false"}, "keyword": "action", "name": "generate_menu_options", "number": 14, "provider": "slack_bot", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"101b8c3e\",\"path\":[\"list_items\", {\"path_element_type\": \"size\"}]}')}", "operand": "greater_than", "rhs": "0"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 11, "provider": "", "skip": false}], "input": {"dynamic_menu_name": "List of Job Titles", "parameters": "[\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Return\",\n    \"name\": \"return\",\n    \"type\": \"string\",\n    \"optional\": false,\n    \"hint\": \"<b>title</b> or <b>id</b> only\"\n  },\n  {\n    \"name\": \"status\",\n    \"type\": \"string\",\n    \"optional\": true,\n    \"label\": \"Status\",\n    \"control_type\": \"text\"\n  },\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Job Family Group Name\",\n    \"name\": \"job_family_group_name\",\n    \"type\": \"string\",\n    \"optional\": true\n  }\n]"}, "keyword": "trigger", "name": "dynamic_menu", "number": 1, "provider": "slack_bot", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

FALLBACK_INSERT_AS = "a0a73f92"
EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("101b8c3e", "workato_variable", "declare_list"),
    ("bd56b813", "lookup_table", "search_entries"),
    ("1ce145fe", "workato_variable", "insert_to_list_batch"),
    ("b7e70bfd", "lookup_table", "get_entries"),
    ("a0a73f92", "workato_variable", "insert_to_list_batch"),
    ("06c4d839", "workato_smart_list", "create_list"),
    ("bc713a22", "workato_smart_list", "query_list"),
    ("f17938bf", "slack_bot", "generate_menu_options"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_list",
    "lookup_table.search_entries",
    "workato_runtime.insert_to_list_batch",
    "lookup_table.get_entries",
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
    "slack_bot.generate_menu_options",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "lookup_table.get_entries",
    "slack_bot.generate_menu_options",
]
ROW_COLUMNS = ("col1", "col2", "col3", "col4", "col5", "col6")
REQUIRED_ROW_COLUMNS = ("col1", "col2", "col3")
PARAMETER_KEYS = ("return", "status", "job_family_group_name")


def validate_127706060(raw: dict[str, Any]) -> dict[str, Any]:
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
    # Twin-drift guard: BOTH lookup reads must target THIS recipe's table id
    # (the 127703856 twin differs only here).
    for node in _walk_nodes(raw):
        if node.get("provider") == "lookup_table":
            table = str((node.get("input") or {}).get("lookup_table_id") or "")
            if table != LOOKUP_TABLE_ID:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} lookup step {node.get('as')!r} targets table "
                    f"{table!r}, expected {LOOKUP_TABLE_ID!r} (twin drift?)"
                )
    # Author-bug pin (replayed verbatim, never fixed): the get_entries fallback
    # insert maps job_title_id from entry col2 -- identical to the job_title
    # mapping -- so fallback 'id' menu values equal the titles.
    fallback = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == FALLBACK_INSERT_AS),
        None,
    )
    if not isinstance(fallback, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} fallback insert step {FALLBACK_INSERT_AS} missing")
    mapping = ((fallback.get("input") or {}).get("list_items") or {})
    if (
        '"col2"' not in str(mapping.get("job_title_id"))
        or mapping.get("job_title_id") != mapping.get("job_title")
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} fallback col2-as-id author bug changed: "
            f"{mapping.get('job_title_id')!r} vs {mapping.get('job_title')!r}"
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


def seed_127706060(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_127706060(raw)
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


def run_127706060(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_127706060(raw)
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
    result["verifier"] = verify_127706060(result)
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
        or not typeahead["value"].strip()
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.typeahead must be {{'value': <non-empty str>}} "
            "(it drives the LIKE filter in the smart-list query)"
        )
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.parameters must be an object "
            "(an explicitly-empty {} exercises the outer-IF-false branch)"
        )
    if not parameters:
        return
    unknown = sorted(set(parameters.keys()) - set(PARAMETER_KEYS))
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters has unknown keys: {unknown}")
    if parameters.get("return") not in ("title", "id"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} non-empty trigger parameters require return 'title'|'id'; "
            f"got {parameters.get('return')!r}"
        )
    for key, value in parameters.items():
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger parameters.{key} must be a non-empty string; "
                "omit optional keys instead of blanking them ('.presence or skip')"
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
        for column in REQUIRED_ROW_COLUMNS:
            if not isinstance(row.get(column), str) or not row[column].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table row {idx} requires non-empty string {column} "
                    "(id/title/status feed the list mappings)"
                )
        for column, value in row.items():
            if not isinstance(value, str):
                raise RuntimeError(f"recipe {RECIPE_ID} table row {idx}.{column} must be a string")


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
