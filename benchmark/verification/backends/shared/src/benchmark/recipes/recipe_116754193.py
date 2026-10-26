from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_116754193


RECIPE_ID = "116754193"
SEED_TYPE = "recipe_function_business_process_upsert_variant"
TRACK = "workato_recipe_function_db_table_business_process_upsert"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TABLE_PROCESS_TYPES = "20690"
TABLE_AUTOMATION_LEVELS = "20687"
TABLE_INTEGRATION_LEVELS = "20686"
TABLE_AI_INVOLVEMENT_LEVELS = "20688"
TABLE_AI_IMPACT_LEVELS = "20689"
TABLE_BUSINESS_PROCESS = "22921"
REQUIRED_SEED_TABLES = (
    TABLE_PROCESS_TYPES,
    TABLE_AUTOMATION_LEVELS,
    TABLE_INTEGRATION_LEVELS,
    TABLE_AI_INVOLVEMENT_LEVELS,
    TABLE_AI_IMPACT_LEVELS,
    TABLE_BUSINESS_PROCESS,
)
UPSERT_PRIMARY_FIELD_ID = "44514d76-840b-46ce-9587-bc68f5de863b"
REQUIRED_TRIGGER_PARAMETERS = (
    "business_unit_code",
    "row_number",
    "process_name",
    "process_hierarchy_level",
    "status",
)
OPTIONAL_TRIGGER_PARAMETERS = (
    "current_automation_level_name",
    "workato_integration_level_name",
    "target_automation_level_name",
    "current_ai_involvement_level_name",
    "ai_impact_level_name",
    "project_page_url",
)
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_db_table", "get_records"),      # 2  process types
    ("workato_db_table", "get_records"),      # 8  current automation level
    ("workato_db_table", "get_records"),      # 12 workato integration level
    ("workato_db_table", "get_records"),      # 16 target automation level
    ("workato_db_table", "get_records"),      # 20 current AI involvement level
    ("workato_db_table", "get_records"),      # 24 AI impact level
    ("workato_db_table", "upsert_record"),    # 27 business process master
    ("workato_recipe_function", "return_result"),  # 28
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.upsert_record",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.upsert_record",
    "workato_recipe_function.return_result",
]
EXPECTED_GET_STEPS: list[tuple[int, str, str, str, str]] = [
    (2, "9863f1f6", TABLE_PROCESS_TYPES, "54a5b952-caba-4bc4-8f47-58798ec6e8f2", "process_hierarchy_level"),
    (8, "eed748db", TABLE_AUTOMATION_LEVELS, "ec706781-ea7e-4000-aed0-5e448031ae56", "current_automation_level_name"),
    (12, "37e44cee", TABLE_INTEGRATION_LEVELS, "595299b9-812f-497c-b041-d43e6172fa67", "workato_integration_level_name"),
    (16, "3e5c56ce", TABLE_AUTOMATION_LEVELS, "ec706781-ea7e-4000-aed0-5e448031ae56", "target_automation_level_name"),
    (20, "e51f429d", TABLE_AI_INVOLVEMENT_LEVELS, "e31c020f-d50c-4fe5-a0db-fb4a3cb3b25d", "current_ai_involvement_level_name"),
    (24, "58f0cc3d", TABLE_AI_IMPACT_LEVELS, "018b63d6-d871-4a1f-8572-a3b251f95164", "ai_impact_level_name"),
]
EXPECTED_STOP_REASONS: dict[int, str] = {
    4: "'Process Hierarchy Level' not found: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"d3f421ab\",\"path\":[\"parameters\", \"process_hierarchy_level\"]}')}",
    6: "Key attributes for a Level 3 item is missing. Please set values accordingly.\n\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"d3f421ab\",\"path\":[\"parameters\", \"business_unit_code\"]}')}-#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"d3f421ab\",\"path\":[\"parameters\", \"row_number\"]}')}\nItem Name: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"d3f421ab\",\"path\":[\"parameters\", \"process_name\"]}')}",
    10: "'Automation Level' not found: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"d3f421ab\",\"path\":[\"parameters\", \"current_automation_level_name\"]}')}",
    14: "'Workato Integration Level' not found: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"d3f421ab\",\"path\":[\"parameters\", \"workato_integration_level_name\"]}')}",
    18: "'Automation Level' not found: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"d3f421ab\",\"path\":[\"parameters\", \"target_automation_level_name\"]}')}",
    22: "'AI Involvement' level not found: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"d3f421ab\",\"path\":[\"parameters\", \"current_ai_involvement_level_name\"]}')}",
    26: "'AI Impact Level' not found: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"d3f421ab\",\"path\":[\"parameters\", \"ai_impact_level_name\"]}')}",
}
LEVEL3_BLANK_CHAIN_FORMULA = (
    "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"d3f421ab\",\"path\":[\"parameters\",\"current_automation_level_name\"]}').blank? "
    "|| _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"d3f421ab\",\"path\":[\"parameters\",\"workato_integration_level_name\"]}').blank? "
    "|| _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"d3f421ab\",\"path\":[\"parameters\",\"target_automation_level_name\"]}').blank? "
    "|| _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"d3f421ab\",\"path\":[\"parameters\",\"current_ai_involvement_level_name\"]}').blank? "
    "|| _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"d3f421ab\",\"path\":[\"parameters\",\"ai_impact_level_name\"]}').blank? "
    "|| _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"d3f421ab\",\"path\":[\"parameters\",\"status\"]}').blank?"
)
EXPECTED_UPSERT_PARAMETERS: dict[str, str] = {
    "00a309e4_fa30_4e54_9bd7_75f2708eeacb": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"d3f421ab\",\"path\":[\"parameters\", \"row_number\"]}')}",
    "19f02441_97bd_4c5e_afda_a7f1674832ea": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"3e5c56ce\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"513681c9_cff7_4ff6_94a3_85465d2633cc\"]}').presence || skip",
    "1d650ff2_1eb3_4ef9_9ba7_d800fad60f74": "=skip",
    "2ecc8301_ecd5_478f_8fe8_e9a209caa9f8": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"9863f1f6\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"54a5b952_caba_4bc4_8f47_58798ec6e8f2\"]}')}",
    "44514d76_840b_46ce_9587_bc68f5de863b": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"d3f421ab\",\"path\":[\"parameters\", \"business_unit_code\"]}')}-#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"d3f421ab\",\"path\":[\"parameters\", \"row_number\"]}')}",
    "4f328a9b_f560_4581_9c2c_01047c1f3ce7": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"58f0cc3d\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"e302176c_7d95_448f_b80f_5f1019e184b9\"]}').presence || skip",
    "4f4cb4f2_aa18_4930_be36_fc8af618acf8": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"d3f421ab\",\"path\":[\"parameters\", \"process_name\"]}')}",
    "5196061d_bf89_43f6_8d72_ea53934f86af": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"d3f421ab\",\"path\":[\"parameters\", \"status\"]}')}",
    "a4053dc5_a3a5_4d8a_bcfd_662becc5526d": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"d3f421ab\",\"path\":[\"parameters\", \"business_unit_code\"]}')}",
    "c6fb6351_f1cf_4454_b244_4ffcc30a2f1b": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"37e44cee\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"8389efac_4a35_447b_a378_8152c43250c4\"]}').presence || skip",
    "d66ec714_c0f2_4d22_ba0a_84faab01b441": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"e51f429d\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"ce41f61c_390e_4509_98a0_a012c176fab2\"]}').presence || skip",
    "ddd23900_8e43_4617_85cc_99e69a7c95c0": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"d3f421ab\",\"path\":[\"parameters\",\"project_page_url\"]}').presence || skip",
    "ebae6352_c8d6_46d1_9fbd_129eba8574ac": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"eed748db\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"513681c9_cff7_4ff6_94a3_85465d2633cc\"]}').presence || skip",
}


def validate_116754193(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != "d3f421ab":
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')}")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    gets = actions[:6]
    for get_action, (number, step_as, table_id, filter_field, parameter) in zip(gets, EXPECTED_GET_STEPS):
        get_input = get_action.get("input") if isinstance(get_action.get("input"), dict) else {}
        if get_action.get("number") != number or str(get_action.get("as") or "") != step_as:
            raise RuntimeError(
                f"recipe {RECIPE_ID} get_records step layout changed at step {number}: "
                f"{get_action.get('number')}/{get_action.get('as')}"
            )
        if str(get_input.get("table_id") or "") != table_id:
            raise RuntimeError(f"recipe {RECIPE_ID} step {number} table id changed: {get_input.get('table_id')}")
        filters = get_input.get("filters") if isinstance(get_input.get("filters"), list) else []
        if len(filters) != 1 or not isinstance(filters[0], dict):
            raise RuntimeError(f"recipe {RECIPE_ID} step {number} filter layout changed: {filters}")
        if str(filters[0].get("field_id") or "") != filter_field:
            raise RuntimeError(f"recipe {RECIPE_ID} step {number} filter field changed: {filters[0]}")
        filter_value = str(filters[0].get("value_integer") or filters[0].get("value_default") or "")
        if "_dp(" not in filter_value or f'"{parameter}"' not in filter_value:
            raise RuntimeError(f"recipe {RECIPE_ID} step {number} filter no longer reads parameters.{parameter}")
    upsert = actions[6]
    upsert_input = upsert.get("input") if isinstance(upsert.get("input"), dict) else {}
    if str(upsert_input.get("table_id") or "") != TABLE_BUSINESS_PROCESS:
        raise RuntimeError(f"recipe {RECIPE_ID} upsert table id changed: {upsert_input.get('table_id')}")
    if str(upsert_input.get("primary_field_id") or "") != UPSERT_PRIMARY_FIELD_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} upsert primary field changed: {upsert_input.get('primary_field_id')}")
    upsert_parameters = upsert_input.get("parameters") if isinstance(upsert_input.get("parameters"), dict) else {}
    if upsert_parameters != EXPECTED_UPSERT_PARAMETERS:
        raise RuntimeError(f"recipe {RECIPE_ID} upsert field mapping changed: {upsert_parameters}")
    return_input = actions[7].get("input")
    if return_input not in ({}, None):
        raise RuntimeError(f"recipe {RECIPE_ID} return_result is no longer empty: {return_input}")
    stops = _collect_stops(raw)
    actual_reasons = {
        node.get("number"): str((node.get("input") or {}).get("stop_reason") or "")
        for node in stops
    }
    if actual_reasons != EXPECTED_STOP_REASONS:
        raise RuntimeError(f"recipe {RECIPE_ID} stop reasons changed: {actual_reasons}")
    for node in stops:
        if str((node.get("input") or {}).get("stop_with_error") or "") != "true":
            raise RuntimeError(f"recipe {RECIPE_ID} stop {node.get('number')} is no longer stop_with_error")
    level3_if = _find_node(raw, 5, "if")
    conditions = ((level3_if or {}).get("input") or {}).get("conditions") or []
    if (
        len(conditions) != 2
        or str(conditions[0].get("rhs") or "") != "3"
        or str(conditions[0].get("operand") or "") != "equals_to"
        or str(conditions[1].get("operand") or "") != "is_true"
        or str(conditions[1].get("lhs") or "") != LEVEL3_BLANK_CHAIN_FORMULA
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} level-3 guard condition changed: {conditions}")
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


def seed_116754193(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_116754193(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input requires a parameters object")
    for key in REQUIRED_TRIGGER_PARAMETERS:
        if str(parameters.get(key) if parameters.get(key) is not None else "").strip() == "":
            raise RuntimeError(f"recipe {RECIPE_ID} trigger input requires non-blank parameters.{key}")
    for key in OPTIONAL_TRIGGER_PARAMETERS:
        if key not in parameters:
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger input must declare parameters.{key} explicitly "
                "(use \"\" for a deliberately blank optional value)"
            )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    db_seed = seed_in.get("workato_db_table")
    tables = db_seed.get("tables") if isinstance(db_seed, dict) else None
    if not isinstance(tables, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed must define seed.workato_db_table.tables")
    for table_id in REQUIRED_SEED_TABLES:
        if not isinstance(tables.get(table_id), list):
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed must declare workato_db_table.tables[{table_id!r}] "
                "explicitly (an empty table is an explicit [])"
            )
    expect = data.get("expect")
    if not isinstance(expect, dict) or "stopped" not in expect:
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must carry an expect object that declares "
            "expect.stopped explicitly"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(expect),
        "raw_validation": validation,
        "workato_db_table": deepcopy(db_seed),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_116754193(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_116754193(raw)
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = _snapshot(ctx, seed)
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
    result["verifier"] = verify_116754193(result)
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


def _collect_stops(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "stop" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_stops(child))
    return found


def _find_node(node: dict[str, Any], number: int, keyword: str) -> dict[str, Any] | None:
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("number") == number and child.get("keyword") == keyword:
            return child
        found = _find_node(child, number, keyword)
        if found is not None:
            return found
    return None


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("workato_db_table"), dict):
        out.update(ctx.tools.call("harness.workato_db_table.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
