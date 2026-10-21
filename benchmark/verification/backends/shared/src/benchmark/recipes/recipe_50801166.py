from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_50801166


RECIPE_ID = "50801166"
SEED_TYPE = "office_locker_block_kit_variant"
TRACK = "office_locker_block_kit"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "322005c7"
# Office-bot locker recipe function (trigger as 322005c7, parameters
# {user_id, office}):
#   declare_variable 2941c512 office = parameters.office.gsub(" ", "")
#   declare_list 5164cdd3 'Final Block Kit Template'
#   lookup_table.search_entries 0d730d03 (table 1840299 'Lockers Database',
#     col1 = office)
#   IF 5 (0d730d03 entries size > 0):
#     lookup_table.search_entries a79dd4d9 (table 1840300 'Lockers Booking',
#       col1 = user_id, col3 = office, col5 = job_created_at
#       .in_time_zone("#{0d730d03.entries.first.entry.col8}").strftime("%B %Y"),
#       col6 = 'Approved')
#   IF 7 (a79dd4d9 size > 0 AND office contains a79dd4d9 first entry col3):
#     logger a4e7a1a3 '| _Locker `col4` Reserved for `col5`_'
#   insert_to_list ca9f74fb: section block referencing parameters.office AND
#     the logger a4e7a1a3 message OUTSIDE its guarding IF -> when IF 7 never
#     ran the pill renders as "" (Workato nil-render parity).
#   IF 10 (a79dd4d9 size > 0): insert 'Cancel my Locker Booking' button
#     (value cancel_locker_<gsub office>)  ELSE 12: insert 'Book a Locker'
#     button (value book_locker_<gsub office>)
#   logger 9cfd0089 = list_items.pluck('elements').smart_join(",")
#   return_result de3cfb14 {elements: 9cfd0089 message}  (step 15, terminal)
#
# When IF 5 is false the booking search a79dd4d9 NEVER runs: IF 7 / IF 10 both
# see a missing-size pill (not > 0) -> false -> Book-a-Locker path, and the
# section text renders with an empty logger pill (executed_action_count 7).
# All backends are Workato-internal (lookup tables read-only, variables,
# logger, recipe-function return): mock per backend policy, no cleanup; the
# run asserts the lookup tables are byte-identical before and after.
OFFICE_TABLE_ID = "1840299"
BOOKING_TABLE_ID = "1840300"
LOOKUP_TABLE_IDS = [OFFICE_TABLE_ID, BOOKING_TABLE_ID]
REQUIRED_TRIGGER_PARAMETERS = ("user_id", "office")
EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("2941c512", "workato_variable", "declare_variable"),
    ("5164cdd3", "workato_variable", "declare_list"),
    ("0d730d03", "lookup_table", "search_entries"),
    ("a79dd4d9", "lookup_table", "search_entries"),
    ("a4e7a1a3", "logger", "log_message"),
    ("ca9f74fb", "workato_variable", "insert_to_list"),
    ("27d09e08", "workato_variable", "insert_to_list"),
    ("bfc5bf4a", "workato_variable", "insert_to_list"),
    ("9cfd0089", "logger", "log_message"),
    ("de3cfb14", "workato_recipe_function", "return_result"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "workato_runtime.declare_list",
    "lookup_table.search_entries",
    "workato_runtime.log_message",
    "workato_runtime.insert_to_list",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "workato_recipe_function.return_result",
]

# --- Verbatim raw-recipe pin: the full normalized node tree (number, keyword,
# provider, name, as, skip, input for every node). Any upstream drift in the
# gsub/in_time_zone/pluck-smart_join formulas, the block-kit literals, the IF
# conditions or the lookup expressions fails validation instead of silently
# changing groundtruth.
_RAW_PIN_JSON = r"""{"as": "322005c7", "block": [{"as": "2941c512", "block": [], "input": {"variables": {"data": {"office": "=_('data.workato_recipe_function.322005c7.parameters.office').gsub(\" \" , \"\")"}, "schema": "[{\"name\":\"office\",\"type\":\"string\",\"optional\":true,\"label\":\"Office\",\"control_type\":\"text\"}]"}}, "keyword": "action", "name": "declare_variable", "number": 2, "provider": "workato_variable", "skip": false}, {"as": "5164cdd3", "block": [], "input": {"list_item_schema_json": "[{\"name\":\"elements\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"}]", "name": "Final Block Kit Template"}, "keyword": "action", "name": "declare_list", "number": 3, "provider": "workato_variable", "skip": false}, {"as": "0d730d03", "block": [], "input": {"lookup_table_id": "1840299", "parameters": {"col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"322005c7\",\"path\":[\"parameters\", \"office\"]}')}"}}, "keyword": "action", "name": "search_entries", "number": 4, "provider": "lookup_table", "skip": false}, {"as": "", "block": [{"as": "a79dd4d9", "block": [], "input": {"lookup_table_id": "1840300", "parameters": {"col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"322005c7\",\"path\":[\"parameters\", \"user_id\"]}')}", "col3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"322005c7\",\"path\":[\"parameters\", \"office\"]}')}", "col5": "=_('data.workato.job_context.job_created_at').in_time_zone(\"#{_('data.lookup_table.0d730d03.entries.first.entry.col8')}\").strftime(\"%B %Y\")", "col6": "Approved"}}, "keyword": "action", "name": "search_entries", "number": 6, "provider": "lookup_table", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"0d730d03\",\"path\":[\"entries\", {\"path_element_type\": \"size\"}]}')}", "operand": "greater_than", "rhs": "0"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 5, "provider": "", "skip": false}, {"as": "", "block": [{"as": "a4e7a1a3", "block": [], "input": {"message": "| _Locker `#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"a79dd4d9\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col4\"]}')}` Reserved for `#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"a79dd4d9\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col5\"]}')}`_", "user_logs_enabled": "false"}, "keyword": "action", "name": "log_message", "number": 8, "provider": "logger", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"a79dd4d9\",\"path\":[\"entries\", {\"path_element_type\": \"size\"}]}')}", "operand": "greater_than", "rhs": "0"}, {"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"322005c7\",\"path\":[\"parameters\", \"office\"]}')}", "operand": "contains", "rhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"a79dd4d9\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col3\"]}')}"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 7, "provider": "", "skip": false}, {"as": "ca9f74fb", "block": [], "input": {"list_item": {"elements": "        {\n\t\t\t\"type\": \"section\",\n\t\t\t\"text\": {\n\t\t\t\t\"type\": \"mrkdwn\",\n\t\t\t\t\"text\": \":office:  *#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"322005c7\",\"path\":[\"parameters\", \"office\"]}')} Office* #{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"a4e7a1a3\",\"path\":[\"message\"]}')}\"\n\t\t\t}\n\t\t}"}, "location": "end", "name": "52938907-11e6-43bb-9411-8a6aaefb8df1:5164cdd3"}, "keyword": "action", "name": "insert_to_list", "number": 9, "provider": "workato_variable", "skip": false}, {"as": "", "block": [{"as": "27d09e08", "block": [], "input": {"list_item": {"elements": "\t\t{\n\t\t\t\"type\": \"actions\",\n\t\t\t\"elements\": [\n\t\t\t\t{\n\t\t\t\t\t\"type\": \"button\",\n\t\t\t\t\t\"text\": {\n\t\t\t\t\t\t\"type\": \"plain_text\",\n\t\t\t\t\t\t\"text\": \"Cancel my Locker Booking\",\n\t\t\t\t\t\t\"emoji\": true\n\t\t\t\t\t},\n\t\t\t\t\t\"style\": \"danger\",\n                    \"value\": \"cancel_locker_#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2941c512\",\"path\":[\"office\"]}')}\",\n                \"url\": \"slack://app?team=T02MRTQUB&id=A014NBSUEJ0&tab=message\"\n\t\t\t\t}\n\t\t\t]\n\t\t}"}, "location": "end", "name": "52938907-11e6-43bb-9411-8a6aaefb8df1:5164cdd3"}, "keyword": "action", "name": "insert_to_list", "number": 11, "provider": "workato_variable", "skip": false}, {"as": "", "block": [{"as": "bfc5bf4a", "block": [], "input": {"list_item": {"elements": "\t\t{\n\t\t\t\"type\": \"actions\",\n\t\t\t\"elements\": [\n\t\t\t\t{\n\t\t\t\t\t\"type\": \"button\",\n\t\t\t\t\t\"text\": {\n\t\t\t\t\t\t\"type\": \"plain_text\",\n\t\t\t\t\t\t\"text\": \"Book a Locker\",\n\t\t\t\t\t\t\"emoji\": true\n\t\t\t\t\t},\n\t\t\t\t\t\"style\": \"primary\",\n\t\t\t\t\t\"value\": \"book_locker_#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2941c512\",\"path\":[\"office\"]}')}\",\n\t\t\t\t\t\"url\": \"slack://app?team=T02MRTQUB&id=A014NBSUEJ0&tab=message\"\n\t\t\t\t}\n\t\t\t]\n\t\t}"}, "location": "end", "name": "52938907-11e6-43bb-9411-8a6aaefb8df1:5164cdd3"}, "keyword": "action", "name": "insert_to_list", "number": 13, "provider": "workato_variable", "skip": false}], "input": {}, "keyword": "else", "name": "", "number": 12, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"a79dd4d9\",\"path\":[\"entries\", {\"path_element_type\": \"size\"}]}')}", "operand": "greater_than", "rhs": "0"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 10, "provider": "", "skip": false}, {"as": "9cfd0089", "block": [], "input": {"message": "=_('data.workato_variable.5164cdd3.list_items').pluck('elements').smart_join(\",\")", "user_logs_enabled": "false"}, "keyword": "action", "name": "log_message", "number": 14, "provider": "logger", "skip": false}, {"as": "de3cfb14", "block": [], "input": {"result": {"elements": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"9cfd0089\",\"path\":[\"message\"]}')}"}}, "keyword": "action", "name": "return_result", "number": 15, "provider": "workato_recipe_function", "skip": false}], "input": {"parameters_schema_json": "[{\"control_type\":\"text\",\"label\":\"User ID\",\"name\":\"user_id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Office\",\"name\":\"office\",\"type\":\"string\",\"optional\":false}]", "result_schema_json": "[{\"control_type\":\"text\",\"label\":\"Elements\",\"name\":\"elements\",\"type\":\"string\",\"optional\":false}]"}, "keyword": "trigger", "name": "execute", "number": 1, "provider": "workato_recipe_function", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)


def validate_50801166(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_50801166(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_50801166(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict) or sorted(parameters.keys()) != sorted(REQUIRED_TRIGGER_PARAMETERS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must carry exactly "
            f"{sorted(REQUIRED_TRIGGER_PARAMETERS)}; got "
            f"{sorted(parameters.keys()) if isinstance(parameters, dict) else parameters}"
        )
    for field in REQUIRED_TRIGGER_PARAMETERS:
        if not str(parameters.get(field) or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter {field!r} must be a non-empty string")
    job_context = data.get("job_context")
    if not isinstance(job_context, dict) or not str(job_context.get("job_created_at") or ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must pin job_context.job_created_at "
            "(the booking-month formula reads it; never use wall-clock time)"
        )
    seed_in = data.get("seed")
    lookup_seed = seed_in.get("lookup_table") if isinstance(seed_in, dict) else None
    tables = lookup_seed.get("tables") if isinstance(lookup_seed, dict) else None
    if not isinstance(tables, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed must define lookup_table.tables explicitly")
    if sorted(tables.keys()) != sorted(LOOKUP_TABLE_IDS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare BOTH locker lookup tables "
            f"{LOOKUP_TABLE_IDS} (an empty table still declares an explicit empty list); "
            f"got {sorted(tables.keys())}"
        )
    for table_id, rows in tables.items():
        if not isinstance(rows, list):
            raise RuntimeError(f"recipe {RECIPE_ID} lookup table {table_id} rows must be a list")
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "lookup_table": deepcopy(lookup_seed),
        "job_context": deepcopy(job_context),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_50801166(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_50801166(raw)
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
    if not isinstance(seed.get("job_context"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing job_context section")
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
    result["verifier"] = verify_50801166(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


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


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return ctx.tools.call("harness.lookup_table.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
