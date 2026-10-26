from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_89648194


RECIPE_ID = "89648194"
SEED_TYPE = "slack_dynamic_menu_persona_list_variant"
TRACK = "workato_internal_dynamic_menu_persona_list"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "dynamic_menu"
TRIGGER_AS = "0b7d4ee2"
DYNAMIC_MENU_NAME = "Persona List X-Ray"
TABLE_ID = "6258"
GET_STEP_AS = "def244aa"
LIST_STEP_AS = "a75ef396"
INSERT_STEP_AS = "6e2a450c"
MENU_STEP_AS = "c4692198"
FOREACH_AS = "0fcffae4"
RECORD_ID_FIELD = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
PERSONA_FIELD = "4e0b03d5_c280_4c9c_8cec_90f04ab70632"
CREATED_AT_FIELD = "a5612739_5401_4ae7_bd07_782c1a6fb2d1"
UPDATED_AT_FIELD = "61aae604_a95e_4519_9091_bb0bf754a67f"
ROW_FIELDS = (RECORD_ID_FIELD, PERSONA_FIELD, CREATED_AT_FIELD, UPDATED_AT_FIELD)


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "slack_bot", "name": "dynamic_menu", "as": "0b7d4ee2", "skip": false, "input": {"dynamic_menu_name": "Persona List X-Ray", "parameters": "[\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Persona Input\",\n    \"name\": \"persona_input\",\n    \"type\": \"string\",\n    \"optional\": true\n  }\n]"}, "block": [{"number": 2, "keyword": "action", "provider": "workato_db_table", "name": "get_records", "as": "def244aa", "skip": false, "input": {"11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "4e0b03d5-c280-4c9c-8cec-90f04ab70632": "string", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "filters": [{"field_id": "4e0b03d5-c280-4c9c-8cec-90f04ab70632", "op_default": "isnotnull"}], "limit": "200", "order_direction": "asc", "table_id": "6258"}, "block": []}, {"number": 3, "keyword": "action", "provider": "workato_variable", "name": "declare_list", "as": "a75ef396", "skip": false, "input": {"list_item_schema_json": "[{\"name\":\"persona_type\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Persona type\"}]", "name": "Persona"}, "block": []}, {"number": 4, "keyword": "foreach", "provider": "", "name": "", "as": "0fcffae4", "skip": false, "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"def244aa\",\"path\":[\"records\"]}')}"}, "repeat_mode": "simple", "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"def244aa\",\"path\":[\"records\"]}')}", "block": [{"number": 5, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "=_('data.foreach.0fcffae4.4e0b03d5_c280_4c9c_8cec_90f04ab70632').downcase", "operand": "contains", "rhs": "=_('data.slack_bot.0b7d4ee2.typeahead.value').downcase"}], "operand": "and", "type": "compound"}, "block": [{"number": 6, "keyword": "action", "provider": "workato_variable", "name": "insert_to_list", "as": "6e2a450c", "skip": false, "input": {"list_item": {"persona_type": "=_('data.foreach.0fcffae4.4e0b03d5_c280_4c9c_8cec_90f04ab70632')"}, "location": "end", "name": "b4cd73d3-a40c-4d76-9336-739ad0a1f9f4:a75ef396"}, "block": []}]}]}, {"number": 7, "keyword": "action", "provider": "slack_bot", "name": "generate_menu_options", "as": "c4692198", "skip": false, "input": {"option_groups": [{}], "options": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"a75ef396\",\"path\":[\"list_items\"]}')}", "label": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"a75ef396\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"persona_type\"]}')}", "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"a75ef396\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"persona_type\"]}')}"}, "use_option_groups": "false"}, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (GET_STEP_AS, "workato_db_table", "get_records"),
    (LIST_STEP_AS, "workato_variable", "declare_list"),
    (INSERT_STEP_AS, "workato_variable", "insert_to_list"),
    (MENU_STEP_AS, "slack_bot", "generate_menu_options"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_runtime.declare_list",
    "workato_runtime.insert_to_list",
    "slack_bot.generate_menu_options",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "slack_bot.generate_menu_options",
]
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "filtered_personas",
    "inserted_items",
    "menu_options",
)


def validate_89648194(raw: dict[str, Any]) -> dict[str, Any]:
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
    # Semantic pins on the drift-prone bits (the tree pin holds the exact
    # bytes; these name the trap when one changes).
    get_node = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == GET_STEP_AS),
        None,
    )
    if not isinstance(get_node, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} get_records step {GET_STEP_AS} missing")
    get_input = get_node.get("input") or {}
    if str(get_input.get("table_id") or "") != TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} get_records table changed")
    filters = get_input.get("filters")
    if filters != [{"field_id": "4e0b03d5-c280-4c9c-8cec-90f04ab70632", "op_default": "isnotnull"}]:
        raise RuntimeError(f"recipe {RECIPE_ID} isnotnull Persona filter changed: {filters!r}")
    menu = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == MENU_STEP_AS),
        None,
    )
    if not isinstance(menu, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} menu step {MENU_STEP_AS} missing")
    menu_input = menu.get("input") or {}
    if menu_input.get("option_groups") != [{}] or menu_input.get("use_option_groups") != "false":
        raise RuntimeError(
            f"recipe {RECIPE_ID} menu step no longer carries the vestigial "
            "option_groups [{}] + use_option_groups 'false' shape"
        )
    insert = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == INSERT_STEP_AS),
        None,
    )
    if not isinstance(insert, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} insert step {INSERT_STEP_AS} missing")
    target = str((insert.get("input") or {}).get("name") or "")
    if target.split(":")[1:] != [LIST_STEP_AS]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} insert no longer targets the declared list step "
            f"{LIST_STEP_AS!r}: {target!r}"
        )
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "dynamic_menu_name": DYNAMIC_MENU_NAME,
        "table_id": TABLE_ID,
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


def seed_89648194(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_89648194(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["workato_db_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the workato_db_table section; "
            f"got {sorted(seed_in.keys())}"
        )
    _require_db_table_section(seed_in["workato_db_table"])
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the "
            "whole run instead of exercising a recipe branch"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_89648194(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_89648194(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
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
    result["verifier"] = verify_89648194(result)
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
            f"recipe {RECIPE_ID} trigger_input.typeahead must be {{'value': <str>}} — "
            "ALWAYS seed it explicitly ('' allowed: contains('') admits every row); "
            "an absent typeahead would leak the missing-pill sentinel into .downcase"
        )
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input.parameters must be an object")
    unknown = sorted(set(parameters.keys()) - {"persona_input"})
    if unknown:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters may only carry the declared optional "
            f"persona_input (unused by the recipe); got {unknown}"
        )
    for key, value in parameters.items():
        if not isinstance(value, str):
            raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters.{key} must be a string")


def _require_db_table_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table must be exactly {{'tables': ...}}"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table.tables must declare exactly table "
            f"{TABLE_ID!r} (rows may be an explicit empty list)"
        )
    rows = tables[TABLE_ID]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {TABLE_ID} rows must be a list")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table row {idx} must be an object")
        unknown = sorted(set(row.keys()) - set(ROW_FIELDS))
        if unknown:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} has unknown columns: {unknown} "
                f"(seed the UNDERSCORE-normalized field ids)"
            )
        if not isinstance(row.get(RECORD_ID_FIELD), str) or not row[RECORD_ID_FIELD].strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} requires a non-empty Record ID "
                f"({RECORD_ID_FIELD})"
            )
        # Persona may be a non-empty string, null, or ABSENT: null and missing
        # keys are both dropped by the isnotnull filter (probed) and are the
        # seedable counterfactuals for that branch.
        if PERSONA_FIELD in row:
            persona = row[PERSONA_FIELD]
            if persona is not None and (not isinstance(persona, str) or not persona.strip()):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table row {idx} Persona must be a non-empty "
                    f"string, null, or absent; got {persona!r} (the mock treats '' as "
                    "null — seed null explicitly so intent stays readable)"
                )
        for field in (CREATED_AT_FIELD, UPDATED_AT_FIELD):
            if field in row and not isinstance(row[field], str):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table row {idx} {field} must be a string timestamp"
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
    return ctx.tools.call("harness.workato_db_table.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
