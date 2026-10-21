from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_131575559


RECIPE_ID = "131575559"
SEED_TYPE = "google_sheets_referral_programme_count_variant"
TRACK = "google_sheets_trigger_referral_count_upsert"
TRIGGER_PROVIDER = "google_sheets"
TRIGGER_NAME = "updated_polling_spreadsheet_row_v4_2"
COUNT_TABLE_ID = "60578"
PROFILES_TABLE_ID = "28114"
# Sheets updated-row trigger (as 5624e739, watchfield 3 = UTM Medium) with a
# TRIGGER FILTER col_3 equals_to 'attendee-referral'. Body wrapped in TRY:
#   get_records 43bf3ae3 (table 60578 'Referral Programme Count',
#     UTM Source ID eq col_2)
#   IF records.size != '1':
#     logger.log_message 0f8004fb ('Error: <size> found, Referral number
#       <col_2>,<col_9>')
#     get_records 3bf8cc33 (table 28114 'Profiles', Record ID eq col_2)
#     add_record 5945946c (table 60578: UTM Source ID/Name/Email from the
#       Profiles first row pills, Number of Referrals Registered = '1')
#   ELSE:
#     update_record 4cf28e5c (table 60578, record_id = first matched row's
#       Record ID, Number of Referrals Registered = current + 1)
# CATCH (step 10, max_retry_count 0) -> STOP (step 11, stop_with_error false).
# Both tables are Workato-internal datatable mocks; the trigger row is a
# deterministic seeded payload (no live Sheets state is read or written).
EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("workato_db_table", "get_records", "43bf3ae3"),
    ("logger", "log_message", "0f8004fb"),
    ("workato_db_table", "get_records", "3bf8cc33"),
    ("workato_db_table", "add_record", "5945946c"),
    ("workato_db_table", "update_record", "4cf28e5c"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_runtime.log_message",
    "workato_db_table.add_record",
    "workato_db_table.update_record",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.add_record",
    "workato_db_table.update_record",
]
COL2_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"5624e739\","
    "\"path\":[\"columns\", \"col_2\"]}')}"
)
COL3_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"5624e739\","
    "\"path\":[\"columns\", \"col_3\"]}')}"
)
SIZE_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"43bf3ae3\","
    "\"path\":[\"records\", {\"path_element_type\": \"size\"}]}')}"
)
LOG_MESSAGE = (
    "Error: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"43bf3ae3\","
    "\"path\":[\"records\", {\"path_element_type\": \"size\"}]}')} found, Referral number "
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"5624e739\","
    "\"path\":[\"columns\", \"col_2\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\","
    "\"line\":\"5624e739\",\"path\":[\"columns\", \"col_9\"]}')}"
)
ADD_PARAMETERS = {
    "185f0172_31d9_44cb_9395_676c919bccb3": (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"3bf8cc33\","
        "\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"0581d990_661f_4227_b771_7356ae2cdc0f\"]}')}"
    ),
    "637c1d20_7db2_4de9_9c35_1536679ae12a": "1",
    "cc2cc48c_a3f5_46b0_8138_f463de9162f5": (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"3bf8cc33\","
        "\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\"]}')}"
    ),
    "da9d1107_3867_4b7b_8464_2f3974e15680": (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"3bf8cc33\","
        "\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"30950d95_ace6_4205_b040_8e1a791882ea\"]}')}"
    ),
}
INCREMENT_FORMULA = (
    "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"43bf3ae3\","
    "\"path\":[\"records\",{\"path_element_type\":\"current_item\"},"
    "\"637c1d20_7db2_4de9_9c35_1536679ae12a\"]}')+ 1"
)
UPDATE_RECORD_ID_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"43bf3ae3\","
    "\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\"]}')}"
)
COUNT_FILTER = {
    "field_id": "cc2cc48c-a3f5-46b0-8138-f463de9162f5",
    "op_default": "eq",
    "op_id": "eq",
    "value_default": COL2_PILL,
}
PROFILES_FILTER = {
    "field_id": "11fbe9a6-a16d-4d7e-86ea-afe42ec03005",
    "op_id": "eq",
    "value_default": COL2_PILL,
}
REQUIRED_COLUMNS = ("col_2", "col_3", "col_9")


def validate_131575559(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str((raw.get("input") or {}).get("watchfield") or "") != "3":
        raise RuntimeError(f"recipe {RECIPE_ID} trigger watchfield changed")
    trigger_filter = raw.get("filter")
    if not isinstance(trigger_filter, dict) or trigger_filter.get("type") != "compound":
        raise RuntimeError(f"recipe {RECIPE_ID} trigger filter missing")
    conditions = trigger_filter.get("conditions")
    if (
        not isinstance(conditions, list)
        or len(conditions) != 1
        or conditions[0].get("lhs") != COL3_PILL
        or conditions[0].get("operand") != "equals_to"
        or conditions[0].get("rhs") != "attendee-referral"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger filter changed: {conditions}")
    actions = _collect_keyword(raw, "action")
    actual = [(a.get("provider"), a.get("name"), a.get("as")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    count_get = _input(actions[0])
    if str(count_get.get("table_id") or "") != COUNT_TABLE_ID or count_get.get("filters") != [COUNT_FILTER]:
        raise RuntimeError(f"recipe {RECIPE_ID} count get_records changed: {count_get}")
    log_input = _input(actions[1])
    if log_input.get("message") != LOG_MESSAGE:
        raise RuntimeError(f"recipe {RECIPE_ID} log message changed: {log_input.get('message')!r}")
    profiles_get = _input(actions[2])
    if str(profiles_get.get("table_id") or "") != PROFILES_TABLE_ID or profiles_get.get("filters") != [PROFILES_FILTER]:
        raise RuntimeError(f"recipe {RECIPE_ID} profiles get_records changed: {profiles_get}")
    add_input = _input(actions[3])
    if str(add_input.get("table_id") or "") != COUNT_TABLE_ID or add_input.get("parameters") != ADD_PARAMETERS:
        raise RuntimeError(f"recipe {RECIPE_ID} add_record changed: {add_input}")
    update_input = _input(actions[4])
    if (
        str(update_input.get("table_id") or "") != COUNT_TABLE_ID
        or update_input.get("record_id") != UPDATE_RECORD_ID_PILL
        or update_input.get("parameters") != {"637c1d20_7db2_4de9_9c35_1536679ae12a": INCREMENT_FORMULA}
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} update_record changed: {update_input}")
    ifs = _collect_keyword(raw, "if")
    if len(ifs) != 1 or ifs[0].get("number") != 4:
        raise RuntimeError(f"recipe {RECIPE_ID} IF steps changed")
    if_conditions = _input(ifs[0]).get("conditions")
    if (
        not isinstance(if_conditions, list)
        or len(if_conditions) != 1
        or if_conditions[0].get("lhs") != SIZE_PILL
        or if_conditions[0].get("operand") != "not_equals_to"
        or if_conditions[0].get("rhs") != "1"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} IF condition changed: {if_conditions}")
    elses = _collect_keyword(raw, "else")
    if len(elses) != 1 or elses[0].get("number") != 8:
        raise RuntimeError(f"recipe {RECIPE_ID} ELSE block changed")
    tries = _collect_keyword(raw, "try")
    if len(tries) != 1 or tries[0].get("number") != 2:
        raise RuntimeError(f"recipe {RECIPE_ID} TRY block changed")
    catches = _collect_keyword(raw, "catch")
    if len(catches) != 1 or str(_input(catches[0]).get("max_retry_count") or "") != "0":
        raise RuntimeError(f"recipe {RECIPE_ID} catch block changed")
    stops = _collect_keyword(raw, "stop")
    if (
        len(stops) != 1
        or stops[0].get("number") != 11
        or str(_input(stops[0]).get("stop_with_error") or "") != "false"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} stop step changed: {stops}")
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


def seed_131575559(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_131575559(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    columns = trigger.get("columns")
    if not isinstance(columns, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input missing columns object")
    for col in REQUIRED_COLUMNS:
        if col not in columns:
            raise RuntimeError(f"recipe {RECIPE_ID} trigger columns missing {col}")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or not isinstance(seed_in.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.workato_db_table")
    tables = seed_in["workato_db_table"].get("tables")
    if not isinstance(tables, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed.workato_db_table missing tables")
    for table_id in (COUNT_TABLE_ID, PROFILES_TABLE_ID):
        if not isinstance(tables.get(table_id), list):
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed must define workato_db_table.tables[{table_id!r}] explicitly"
            )
    expect = data.get("expect")
    if not isinstance(expect, dict) or "trigger_filter_matched" not in expect:
        raise RuntimeError(
            f"recipe {RECIPE_ID} every variant must declare expect.trigger_filter_matched"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "expect": deepcopy(expect),
        "raw_validation": validation,
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_131575559(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_131575559(raw)
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
    result["verifier"] = verify_131575559(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _collect_keyword(node: dict[str, Any], keyword: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == keyword and not child.get("skip"):
            found.append(child)
        found.extend(_collect_keyword(child, keyword))
    return found


def _input(node: dict[str, Any]) -> dict[str, Any]:
    value = node.get("input")
    return value if isinstance(value, dict) else {}


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
