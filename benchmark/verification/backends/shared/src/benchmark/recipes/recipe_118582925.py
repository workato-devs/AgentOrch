from __future__ import annotations

import datetime
import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_118582925


RECIPE_ID = "118582925"
TWIN_ID = "118578229"  # byte-identical raw recipe except the two table ids
SEED_TYPE = "itgenie_monthly_process_metrics_variant"
TRACK = "mock_workato_db_usage_metrics_rollup"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "01defda5"
USAGE_TABLE_ID = "11618"  # 'ITGenie | Usage Metrics' (read)
METRICS_TABLE_ID = "11617"  # 'ITGenie | Process Metrics' (write)
CREATED_AT_FIELD = "a5612739_5401_4ae7_bd07_782c1a6fb2d1"
PROCESS_ID_FIELD = "211810bd_e2db_4feb_b058_41337cb362a1"
CATEGORY_FIELD = "921f48e9_6692_4c1f_93ae_19d2c3a2237b"
RESOLUTION_FIELD = "351b4fb5_864b_47da_89e6_30433d1ecc70"
EXECUTION_FIELD = "7a290ed0_4881_4521_b5cb_e17c7894b11f"


_RAW_PIN_JSON = r"""{"as": "01defda5", "block": [{"as": "dda3ad96", "block": [], "input": {"variables": {"data": {"period_end": "=1.days.ago", "period_start": "=1.months.ago"}, "schema": "[{\"control_type\":\"text\",\"label\":\"period_start\",\"name\":\"period_start\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"period_start\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"text\",\"label\":\"period_end\",\"name\":\"period_end\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"period_end\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"name\":\"next_token\",\"type\":\"string\",\"optional\":true,\"label\":\"next_token\",\"details\":{\"real_name\":\"next_token\"},\"control_type\":\"text\",\"parent\":[\"variables\",\"data\"]}]"}}, "keyword": "action", "name": "declare_variable", "number": 2, "provider": "workato_variable", "skip": false}, {"as": "d8e2644f", "block": [], "input": {"list_item_schema_json": "[{\"name\":\"process_id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Process ID\"},{\"name\":\"action_category\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Action category\"},{\"name\":\"ticket_resolution_time\",\"type\":\"integer\",\"optional\":true,\"control_type\":\"integer\",\"label\":\"Ticket resolution time\",\"parse_output\":\"integer_conversion\"},{\"name\":\"process_execution_time\",\"type\":\"integer\",\"optional\":true,\"control_type\":\"integer\",\"label\":\"Process execution time\",\"parse_output\":\"integer_conversion\"}]", "name": "usage_metrics_list"}, "keyword": "action", "name": "declare_list", "number": 3, "provider": "workato_variable", "skip": false}, {"as": "15d1c62b", "block": [{"as": "e9a69756", "block": [], "input": {"0104b7ef-de3c-4a5f-ba6b-c1ddc4bc6f17": "string", "045d2afd-0012-4bbc-a53d-b4008c51179b": "string", "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "211810bd-e2db-4feb-b058-41337cb362a1": "string", "21ea8e76-5bd7-4fa1-b70b-0fef13c05193": "string", "265ff871-ab3e-4c7d-9e1a-31c20636a96c": "string", "3323868d-d1f3-4ff1-8b8e-35aed4265162": "boolean", "351b4fb5-864b-47da-89e6-30433d1ecc70": "integer", "4c816268-1553-4ec9-a667-6322dd4cbc9e": "string", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "69527934-bfb0-4080-a583-b2c931c8c6f4": "boolean", "7469ad3d-9dd3-48cc-b2dd-4c3b5c4afa10": "string", "77394afc-f172-4058-86ed-5a786c86d4bb": "string", "7a290ed0-4881-4521-b5cb-e17c7894b11f": "integer", "921f48e9-6692-4c1f-93ae-19d2c3a2237b": "string", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "c0d9f3e8-f181-429f-858e-53b43d3a9d39": "string", "continuation_token": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"dda3ad96\",\"path\":[\"next_token\"]}').presence", "dcca5c9e-25f1-46c6-ae80-ec07f872e9a6": "string", "filters": [{"field_id": "a5612739-5401-4ae7-bd07-782c1a6fb2d1", "op_date_time": "gte", "value_date_time": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"dda3ad96\",\"path\":[\"period_start\"]}')"}], "limit": "200", "order_direction": "asc", "table_id": "11618"}, "keyword": "action", "name": "get_records", "number": 5, "provider": "workato_db_table", "skip": false}, {"as": "4e440342", "block": [], "input": {"list_items": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"e9a69756\",\"path\":[\"records\"]}')}", "action_category": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"e9a69756\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"921f48e9_6692_4c1f_93ae_19d2c3a2237b\"]}')}", "process_execution_time": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"e9a69756\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"7a290ed0_4881_4521_b5cb_e17c7894b11f\"]}')", "process_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"e9a69756\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"211810bd_e2db_4feb_b058_41337cb362a1\"]}')}", "ticket_resolution_time": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"e9a69756\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"351b4fb5_864b_47da_89e6_30433d1ecc70\"]}')"}, "location": "end", "name": "da12955a-a570-4b7d-a402-090a03f38e12:d8e2644f"}, "keyword": "action", "name": "insert_to_list_batch", "number": 6, "provider": "workato_variable", "skip": false}, {"as": "58e05796", "block": [], "input": {"name": "3d84fc22-12da-448e-8313-54473d672c2e:dda3ad96:next_token", "next_token": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"e9a69756\",\"path\":[\"continuation_token\"]}').presence"}, "keyword": "action", "name": "update_variables", "number": 7, "provider": "workato_variable", "skip": false}, {"as": "", "block": [], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"e9a69756\",\"path\":[\"continuation_token\"]}')}", "operand": "present", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "while_condition", "name": "", "number": 8, "provider": "", "skip": false}], "input": {}, "keyword": "repeat", "name": "", "number": 4, "provider": "", "skip": false}, {"as": "2286b831", "block": [], "input": {"variables": {"data": {"average_ticket_resolution_time": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"d8e2644f\",\"path\":[\"list_items\"]}').where(\"ticket_resolution_time !=\": null).pluck(:ticket_resolution_time).length > 0 ? _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"d8e2644f\",\"path\":[\"list_items\"]}').where(\"ticket_resolution_time !=\": null).pluck(:ticket_resolution_time).sum/_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"d8e2644f\",\"path\":[\"list_items\"]}').where(\"ticket_resolution_time !=\": null).pluck(:ticket_resolution_time).length : skip", "ticketing_processes_count": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"d8e2644f\",\"path\":[\"list_items\"]}').where(action_category: \"ticketing\").pluck(:process_id).uniq.length", "total_processes_count": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"d8e2644f\",\"path\":[\"list_items\"]}').pluck(:process_id).uniq.length"}, "schema": "[{\"control_type\":\"integer\",\"label\":\"total_processes_count\",\"parse_output\":\"integer_conversion\",\"name\":\"total_processes_count\",\"type\":\"integer\",\"optional\":true,\"details\":{\"real_name\":\"total_processes_count\"}},{\"control_type\":\"integer\",\"label\":\"ticketing_processes_count\",\"parse_output\":\"integer_conversion\",\"name\":\"ticketing_processes_count\",\"type\":\"integer\",\"optional\":true,\"details\":{\"real_name\":\"ticketing_processes_count\"}},{\"name\":\"average_ticket_resolution_time\",\"type\":\"string\",\"optional\":true,\"label\":\"average_ticket_resolution_time\",\"details\":{\"real_name\":\"average_ticket_resolution_time\"},\"control_type\":\"text\"}]"}}, "keyword": "action", "name": "declare_variable", "number": 9, "provider": "workato_variable", "skip": false}, {"as": "cc1734de", "block": [], "input": {"variables": {"data": {"non_ticketing_processes_count": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"total_processes_count\"]}') - _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"ticketing_processes_count\"]}')"}, "schema": "[{\"name\":\"non_ticketing_processes_count\",\"type\":\"integer\",\"optional\":true,\"label\":\"non_ticketing_processes_count\",\"details\":{\"real_name\":\"non_ticketing_processes_count\"},\"control_type\":\"integer\"}]"}}, "keyword": "action", "name": "declare_variable", "number": 10, "provider": "workato_variable", "skip": false}, {"as": "48f84dd7", "block": [], "input": {"variables": {"data": {"ticket_deflection_rate": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"total_processes_count\"]}') != 0 ? (_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"cc1734de\",\"path\":[\"non_ticketing_processes_count\"]}')*100/_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"total_processes_count\"]}')).to_i : skip"}, "schema": "[{\"name\":\"ticket_deflection_rate\",\"type\":\"string\",\"optional\":true,\"label\":\"ticket_deflection_rate\",\"details\":{\"real_name\":\"ticket_deflection_rate\"},\"control_type\":\"text\"}]"}}, "keyword": "action", "name": "declare_variable", "number": 11, "provider": "workato_variable", "skip": false}, {"as": "1cbc5c22", "block": [], "input": {"parameters": {"41d1a848_0abd_47b4_9ff3_457bce148aa9": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"total_processes_count\"]}')}", "522be3c0_cd38_4168_9076_5583ffeea86c": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"average_ticket_resolution_time\"]}').present? ? (_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"average_ticket_resolution_time\"]}') * _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"cc1734de\",\"path\":[\"non_ticketing_processes_count\"]}')) / 3600000 : skip", "6a482238_5023_41fb_9b9d_687c23e2c5ca": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"cc1734de\",\"path\":[\"non_ticketing_processes_count\"]}')}", "7bf0cddb_eb7f_463f_9cff_046f3f2aa754": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"ticketing_processes_count\"]}')}", "7f9d71ad_4816_4554_87d6_8b0a1d3cada8": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"48f84dd7\",\"path\":[\"ticket_deflection_rate\"]}')}", "b650960e_fab7_433e_a684_9f093f8820a9": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"dda3ad96\",\"path\":[\"period_start\"]}')}", "ff6aefdb_b233_47a1_9896_7092bacef527": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"dda3ad96\",\"path\":[\"period_end\"]}')}"}, "table_id": "11617"}, "keyword": "action", "name": "add_record", "number": 12, "provider": "workato_db_table", "skip": false}], "input": {"days_of_month": "1", "time_unit": "months", "trigger_at": "00:00:00", "trigger_every": "1"}, "keyword": "trigger", "name": "scheduled_event", "number": 1, "provider": "clock", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

_PERIOD_DATA = {"period_end": "=1.days.ago", "period_start": "=1.months.ago"}
_LIST_PILL = (
    "_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\","
    "\"line\":\"d8e2644f\",\"path\":[\"list_items\"]}')"
)
_RES_PLUCK = _LIST_PILL + '.where("ticket_resolution_time !=": null).pluck(:ticket_resolution_time)'
_AVG_FORMULA = (
    "=" + _RES_PLUCK + ".length > 0 ? " + _RES_PLUCK + ".sum/" + _RES_PLUCK + ".length : skip"
)
_TICKETING_FORMULA = "=" + _LIST_PILL + '.where(action_category: "ticketing").pluck(:process_id).uniq.length'
_TOTAL_FORMULA = "=" + _LIST_PILL + ".pluck(:process_id).uniq.length"
_TOTAL_PILL = (
    "_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\","
    "\"line\":\"2286b831\",\"path\":[\"total_processes_count\"]}')"
)
_TICKETING_PILL = (
    "_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\","
    "\"line\":\"2286b831\",\"path\":[\"ticketing_processes_count\"]}')"
)
_NON_TICKETING_FORMULA = "=" + _TOTAL_PILL + " - " + _TICKETING_PILL
_NON_TICKETING_PILL = (
    "_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\","
    "\"line\":\"cc1734de\",\"path\":[\"non_ticketing_processes_count\"]}')"
)
_DEFLECTION_FORMULA = (
    "=" + _TOTAL_PILL + " != 0 ? (" + _NON_TICKETING_PILL + "*100/" + _TOTAL_PILL + ").to_i : skip"
)
_AVG_PILL = (
    "_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\","
    "\"line\":\"2286b831\",\"path\":[\"average_ticket_resolution_time\"]}')"
)
_HOURS_FORMULA = (
    "=" + _AVG_PILL + ".present? ? (" + _AVG_PILL + " * " + _NON_TICKETING_PILL + ") / 3600000 : skip"
)
_FILTER_VALUE_FORMULA = (
    "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\","
    "\"line\":\"dda3ad96\",\"path\":[\"period_start\"]}')"
)
_CONTINUATION_FORMULA = (
    "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\","
    "\"line\":\"dda3ad96\",\"path\":[\"next_token\"]}').presence"
)
_NEXT_TOKEN_FORMULA = (
    "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\","
    "\"line\":\"e9a69756\",\"path\":[\"continuation_token\"]}').presence"
)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("dda3ad96", "workato_variable", "declare_variable"),
    ("d8e2644f", "workato_variable", "declare_list"),
    ("e9a69756", "workato_db_table", "get_records"),
    ("4e440342", "workato_variable", "insert_to_list_batch"),
    ("58e05796", "workato_variable", "update_variables"),
    ("2286b831", "workato_variable", "declare_variable"),
    ("cc1734de", "workato_variable", "declare_variable"),
    ("48f84dd7", "workato_variable", "declare_variable"),
    ("1cbc5c22", "workato_db_table", "add_record"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "workato_runtime.declare_list",
    "workato_db_table.get_records",
    "workato_runtime.insert_to_list_batch",
    "workato_runtime.update_variables",
    "workato_db_table.add_record",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.add_record",
]
REQUIRED_ROW_FIELDS = (CREATED_AT_FIELD, PROCESS_ID_FIELD, CATEGORY_FIELD)


def validate_118582925(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    trigger_cfg = raw.get("input") or {}
    if (
        str(trigger_cfg.get("time_unit") or "") != "months"
        or str(trigger_cfg.get("trigger_every") or "") != "1"
        or str(trigger_cfg.get("days_of_month") or "") != "1"
        or str(trigger_cfg.get("trigger_at") or "") != "00:00:00"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger schedule changed: {trigger_cfg}")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    by_as = {str(a.get("as")): a for a in actions}
    if by_as["dda3ad96"]["input"]["variables"]["data"] != _PERIOD_DATA:
        raise RuntimeError(f"recipe {RECIPE_ID} period declaration drifted")
    get_input = by_as["e9a69756"]["input"]
    if str(get_input.get("table_id") or "") != USAGE_TABLE_ID:
        raise RuntimeError(
            f"recipe {RECIPE_ID} usage table changed: {get_input.get('table_id')!r} "
            f"(this twin reads {USAGE_TABLE_ID}; twin {TWIN_ID} differs only in table ids)"
        )
    filters = get_input.get("filters") or []
    if filters != [
        {
            "field_id": "a5612739-5401-4ae7-bd07-782c1a6fb2d1",
            "op_date_time": "gte",
            "value_date_time": _FILTER_VALUE_FORMULA,
        }
    ]:
        raise RuntimeError(f"recipe {RECIPE_ID} Created-at gte filter drifted: {filters!r}")
    if str(get_input.get("limit") or "") != "200":
        raise RuntimeError(f"recipe {RECIPE_ID} get_records limit drifted")
    if get_input.get("continuation_token") != _CONTINUATION_FORMULA:
        raise RuntimeError(f"recipe {RECIPE_ID} continuation_token formula drifted")
    if by_as["58e05796"]["input"]["next_token"] != _NEXT_TOKEN_FORMULA:
        raise RuntimeError(f"recipe {RECIPE_ID} next_token update formula drifted")
    metrics_data = by_as["2286b831"]["input"]["variables"]["data"]
    if metrics_data != {
        "average_ticket_resolution_time": _AVG_FORMULA,
        "ticketing_processes_count": _TICKETING_FORMULA,
        "total_processes_count": _TOTAL_FORMULA,
    }:
        raise RuntimeError(f"recipe {RECIPE_ID} metrics declaration drifted: {metrics_data!r}")
    if by_as["cc1734de"]["input"]["variables"]["data"] != {
        "non_ticketing_processes_count": _NON_TICKETING_FORMULA
    }:
        raise RuntimeError(f"recipe {RECIPE_ID} non-ticketing declaration drifted")
    if by_as["48f84dd7"]["input"]["variables"]["data"] != {
        "ticket_deflection_rate": _DEFLECTION_FORMULA
    }:
        raise RuntimeError(f"recipe {RECIPE_ID} deflection declaration drifted")
    add_input = by_as["1cbc5c22"]["input"]
    if str(add_input.get("table_id") or "") != METRICS_TABLE_ID:
        raise RuntimeError(
            f"recipe {RECIPE_ID} metrics table changed: {add_input.get('table_id')!r}"
        )
    if add_input["parameters"]["522be3c0_cd38_4168_9076_5583ffeea86c"] != _HOURS_FORMULA:
        raise RuntimeError(f"recipe {RECIPE_ID} Hours Saved formula drifted")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "usage_table_id": USAGE_TABLE_ID,
        "metrics_table_id": METRICS_TABLE_ID,
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


def seed_118582925(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118582925(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger is payload-less (scheduler tick); trigger_input must "
            f"be an explicit empty object, got {trigger!r}"
        )
    now = data.get("now")
    if not isinstance(now, str) or not now.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires a fixed 'now' (drives =1.months.ago / =1.days.ago)"
        )
    try:
        parsed_now = datetime.datetime.fromisoformat(now.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(f"recipe {RECIPE_ID} 'now' is not ISO-8601: {now!r}") from exc
    if parsed_now.tzinfo is None:
        raise RuntimeError(f"recipe {RECIPE_ID} 'now' must carry an explicit UTC offset")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["workato_db_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the workato_db_table section; "
            f"got {sorted(seed_in.keys())}"
        )
    _require_db_section(seed_in["workato_db_table"])
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
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "now": now,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_118582925(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118582925(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
    if seed.get("now") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing fixed 'now'")
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
    result["verifier"] = verify_118582925(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_db_section(section: Any) -> None:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed.workato_db_table must be an object")
    unknown = sorted(set(section.keys()) - {"tables"})
    if unknown:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table has unknown keys: {unknown} "
            "(continuation_tokens are forbidden: the loop is pinned single-page)"
        )
    tables = section.get("tables")
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted([USAGE_TABLE_ID, METRICS_TABLE_ID]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly tables {USAGE_TABLE_ID!r} (read) "
            f"and {METRICS_TABLE_ID!r} (write)"
        )
    if tables[METRICS_TABLE_ID] != []:
        raise RuntimeError(
            f"recipe {RECIPE_ID} metrics table {METRICS_TABLE_ID!r} must be seeded EMPTY "
            "(the add_record row is the per-variant observable artifact)"
        )
    rows = tables[USAGE_TABLE_ID]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} usage table seed must be a row list")
    resolution_values: list[int] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} usage row {idx} must be an object")
        for field in REQUIRED_ROW_FIELDS:
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} usage row {idx} requires non-empty string {field!r} "
                    "(Created-at feeds the gte filter; process id/category feed the rollup)"
                )
        for field in (RESOLUTION_FIELD, EXECUTION_FIELD):
            if field not in row or not (row[field] is None or isinstance(row[field], int)):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} usage row {idx} must carry {field!r} explicitly "
                    "as an integer or null (integer-typed columns; null exercises the "
                    "resolution-time where-filter)"
                )
        if isinstance(row[RESOLUTION_FIELD], int):
            resolution_values.append(row[RESOLUTION_FIELD])
    # Divisions must stay exact so the (still-Decimal) engine division agrees
    # with Ruby Integer#/ -- checked over ALL seeded resolution times; the
    # per-variant expect pins the filtered-subset arithmetic byte-exactly.
    if resolution_values and sum(resolution_values) % len(resolution_values) != 0:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seeded resolution times must sum-divide exactly "
            f"(sum {sum(resolution_values)} % count {len(resolution_values)} != 0); "
            "inexact division would pin engine-Decimal values that diverge from Ruby floor"
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
    return ctx.tools.call("harness.workato_db_table.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
