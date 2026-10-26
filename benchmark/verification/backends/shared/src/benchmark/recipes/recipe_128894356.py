from __future__ import annotations

import datetime
import json
import re
from copy import deepcopy
from typing import Any
from zoneinfo import ZoneInfo

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_128894356


RECIPE_ID = "128894356"
SEED_TYPE = "sheets_x_follow_quest_credit_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "google_sheets"
TRIGGER_NAME = "new_spreadsheet_row_v4"
TRIGGER_AS = "887471b0"
QUEST_GET_AS = "326a6292"
PROFILE_GET_AS = "81cd7472"
STOP_AS = "a1d17201"
ADD_AS = "f6259b09"
QUEST_TABLE = "28116"
PROFILE_TABLE = "28114"
ACTIVITY_TABLE = "28115"
QUEST_CODE_VALUE = "SOCIAL_FOLLOW_X"
CREDITED_TZ = "Asia/Tokyo"
CREDITED_FMT = "%m/%d/%Y"


_RAW_PIN_JSON = r"""{"as": "887471b0", "block": [{"as": "326a6292", "block": [], "input": {"11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "12845ae7-4502-4d82-ae72-1a498541a729": "string", "219c0b22-aec2-49c6-8e0a-c3d72ed54d05": "string", "21f15718-0e6b-4dc5-bda7-9f6042f9693e": "string", "3fe31194-805d-4246-9854-ab50c86c9335": "string", "4078529a-a6f3-47d8-a6c6-4b18a2fcbcd3": "string", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "64a44694-6402-4f3f-8e14-ba3c8d40930c": "string", "6fc4cac9-667d-4fcf-8b95-bc9f153bd894": "string", "7c5a3d20-b3fc-482a-adff-f81ac9ffbeda": "string", "8fa38c33-de3b-4b26-ba48-f97a1cb3735a": "integer", "9419ff83-3758-47d8-9fb8-921029e44da2": "string", "98a72f25-f740-4196-be2c-e2a9564c015e": "date_time", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "bf9f57b0-3c95-4ed5-8506-fbd53810c3fc": "string", "dfbaed6a-6b14-4c0c-8688-58198110c5a8": "string", "e00beaa8-ab54-4084-b92f-02f9e6619834": "string", "f25f6faa-a46d-43a0-abe0-fbdcec31a54f": "date_time", "filters": [{"field_id": "dfbaed6a-6b14-4c0c-8688-58198110c5a8", "op_default": "eq", "value_default": "SOCIAL_FOLLOW_X"}], "limit": "100", "order_direction": "asc", "table_id": "28116"}, "keyword": "action", "name": "get_records", "number": 2, "provider": "workato_db_table", "skip": false}, {"as": "81cd7472", "block": [], "input": {"0401fed3-ffdb-4fa6-af29-bad39ca1c77c": "string", "0581d990-661f-4227-b771-7356ae2cdc0f": "string", "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "30950d95-ace6-4205-b040-8e1a791882ea": "string", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "6d2ae745-a253-4612-95bc-12c77b1d6fc6": "integer", "849bb2f2-0bed-4f2d-8bd1-7ddad17d212b": "string", "928cfe04-a1da-4cb6-aecd-4ced8c098d3a": "date_time", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "cd1bee5a-435e-4d8d-a4cd-39d297e6d8c3": "string", "eda7541e-cc46-47d8-a221-aa2ff0f19a66": "string", "filters": [{"field_id": "849bb2f2-0bed-4f2d-8bd1-7ddad17d212b", "op_default": "eq", "value_default": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"887471b0\",\"path\":[\"columns\", \"col_1\"]}')}"}], "limit": "100", "order_direction": "asc", "table_id": "28114"}, "keyword": "action", "name": "get_records", "number": 3, "provider": "workato_db_table", "skip": false}, {"as": "", "block": [{"as": "a1d17201", "block": [], "input": {"stop_with_error": "false"}, "keyword": "stop", "name": "", "number": 5, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"81cd7472\",\"path\":[\"records\", {\"path_element_type\": \"size\"}]}')}", "operand": "equals_to", "rhs": "0"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 4, "provider": "", "skip": false}, {"as": "f6259b09", "block": [], "input": {"parameters": {"13b82b43_2f7a_4d98_a50d_1a5af68bc4c3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"326a6292\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"3fe31194_805d_4246_9854_ab50c86c9335\"]}')}", "3c779a6b_a7ca_44fc_acb8_69ce179d9584": "=now.in_time_zone('Asia/Tokyo').strftime('%m/%d/%Y')", "614e8425_fe37_4acd_b67b_1ed72fc8568a": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"81cd7472\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"30950d95_ace6_4205_b040_8e1a791882ea\"]}')}", "68240f61_d77a_49f4_8252_24fc373a730d": "CREDITED", "acc76697_ddd7_4d13_87fc_5a6e0b5d6860": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"326a6292\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"dfbaed6a_6b14_4c0c_8688_58198110c5a8\"]}')}"}, "table_id": "28115"}, "keyword": "action", "name": "add_record", "number": 6, "provider": "workato_db_table", "skip": false}], "input": {"sheet": "<anon>John Smith (SocialMedia)</anon>", "spreadsheet": "<anon>2AbC3DeF4GhI5JkL6MnO7PqR8StU9VwX0YzA1BcD2EfG</anon>"}, "keyword": "trigger", "name": "new_spreadsheet_row_v4", "number": 1, "provider": "google_sheets", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

QL_RECORD_ID = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
QL_QUEST_NAME = "3fe31194_805d_4246_9854_ab50c86c9335"
QL_QUEST_DESC = "219c0b22_aec2_49c6_8e0a_c3d72ed54d05"
QL_QUEST_CODE = "dfbaed6a_6b14_4c0c_8688_58198110c5a8"
QL_CAMPAIGN = "12845ae7_4502_4d82_ae72_1a498541a729"
QL_POINTS = "8fa38c33_de3b_4b26_ba48_f97a1cb3735a"
QL_STATUS = "bf9f57b0_3c95_4ed5_8506_fbd53810c3fc"
QL_LINK = "e00beaa8_ab54_4084_b92f_02f9e6619834"
QL_ETA = "9419ff83_3758_47d8_9fb8_921029e44da2"
QL_ICON = "7c5a3d20_b3fc_482a_adff_f81ac9ffbeda"
QL_NAME_EN = "21f15718_0e6b_4dc5_bda7_9f6042f9693e"
QL_BEGIN = "f25f6faa_a46d_43a0_abe0_fbdcec31a54f"
QL_END = "98a72f25_f740_4196_be2c_e2a9564c015e"
QL_TYPE = "6fc4cac9_667d_4fcf_8b95_bc9f153bd894"
QL_TRACKING = "4078529a_a6f3_47d8_a6c6_4b18a2fcbcd3"
QL_UTM = "64a44694_6402_4f3f_8e14_ba3c8d40930c"
QL_CREATED = "a5612739_5401_4ae7_bd07_782c1a6fb2d1"
QL_UPDATED = "61aae604_a95e_4519_9091_bb0bf754a67f"
QUEST_COLUMNS = (
    QL_RECORD_ID, QL_QUEST_NAME, QL_QUEST_DESC, QL_QUEST_CODE, QL_CAMPAIGN,
    QL_POINTS, QL_STATUS, QL_LINK, QL_ETA, QL_ICON, QL_NAME_EN, QL_BEGIN,
    QL_END, QL_TYPE, QL_TRACKING, QL_UTM, QL_CREATED, QL_UPDATED,
)

PR_RECORD_ID = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
PR_NAME = "0581d990_661f_4227_b771_7356ae2cdc0f"
PR_EMAIL = "30950d95_ace6_4205_b040_8e1a791882ea"
PR_POINT_TOTAL = "6d2ae745_a253_4612_95bc_12c77b1d6fc6"
PR_USERNAME = "cd1bee5a_435e_4d8d_a4cd_39d297e6d8c3"
PR_LINKEDIN = "eda7541e_cc46_47d8_a221_aa2ff0f19a66"
PR_X_HANDLE = "849bb2f2_0bed_4f2d_8bd1_7ddad17d212b"
PR_INVITE_TS = "928cfe04_a1da_4cb6_aecd_4ced8c098d3a"
PR_STATUS = "0401fed3_ffdb_4fa6_af29_bad39ca1c77c"
PR_CREATED = "a5612739_5401_4ae7_bd07_782c1a6fb2d1"
PR_UPDATED = "61aae604_a95e_4519_9091_bb0bf754a67f"
PROFILE_COLUMNS = (
    PR_RECORD_ID, PR_NAME, PR_EMAIL, PR_POINT_TOTAL, PR_USERNAME,
    PR_LINKEDIN, PR_X_HANDLE, PR_INVITE_TS, PR_STATUS, PR_CREATED, PR_UPDATED,
)

AC_RECORD_ID = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
AC_QUEST_NAME = "13b82b43_2f7a_4d98_a50d_1a5af68bc4c3"
AC_QUEST_CODE = "acc76697_ddd7_4d13_87fc_5a6e0b5d6860"
AC_STATUS = "68240f61_d77a_49f4_8252_24fc373a730d"
AC_USER_ID = "614e8425_fe37_4acd_b67b_1ed72fc8568a"
AC_POINTS = "d98a88e6_2320_492f_bd4b_eb600a86e0a1"
AC_CREDITED_DATE = "3c779a6b_a7ca_44fc_acb8_69ce179d9584"
AC_CREATED = "a5612739_5401_4ae7_bd07_782c1a6fb2d1"
AC_UPDATED = "61aae604_a95e_4519_9091_bb0bf754a67f"
ACTIVITY_COLUMNS = (
    AC_RECORD_ID, AC_QUEST_NAME, AC_QUEST_CODE, AC_STATUS, AC_USER_ID,
    AC_POINTS, AC_CREDITED_DATE, AC_CREATED, AC_UPDATED,
)
CREDITED_RECORD_KEYS = (AC_QUEST_NAME, AC_CREDITED_DATE, AC_USER_ID, AC_STATUS, AC_QUEST_CODE)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (QUEST_GET_AS, "workato_db_table", "get_records"),
    (PROFILE_GET_AS, "workato_db_table", "get_records"),
    (ADD_AS, "workato_db_table", "add_record"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.add_record",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.add_record",
]
BRANCHES = ("profile_found_credited", "profile_missing_stop", "multi_profile_first_row")
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "branch",
    "stopped",
    "credited_date",
    "credited_record",
    "initial_table_rows",
    "final_table_rows",
)
_EXPECT_ITEM_KEYS = {
    "tool", "table_id", "lookup_table_id", "match_fields", "channel",
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
}
_EXPECT_VALUE_KEYS = {
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
}

_CREDITED_DATE_FORMULA = "=now.in_time_zone('Asia/Tokyo').strftime('%m/%d/%Y')"


def validate_128894356(raw: dict[str, Any]) -> dict[str, Any]:
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
    # Semantic pins on the drift-prone load-bearing bits.
    quest_get = next(node for node in _walk_nodes(raw) if str(node.get("as") or "") == QUEST_GET_AS)
    quest_filters = (quest_get.get("input") or {}).get("filters") or []
    if (
        len(quest_filters) != 1
        or quest_filters[0].get("op_default") != "eq"
        or quest_filters[0].get("value_default") != QUEST_CODE_VALUE
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} quest-list filter changed: {quest_filters}")
    if str((quest_get.get("input") or {}).get("table_id")) != QUEST_TABLE:
        raise RuntimeError(f"recipe {RECIPE_ID} quest-list table changed")
    profile_get = next(node for node in _walk_nodes(raw) if str(node.get("as") or "") == PROFILE_GET_AS)
    profile_filters = (profile_get.get("input") or {}).get("filters") or []
    if (
        len(profile_filters) != 1
        or profile_filters[0].get("op_default") != "eq"
        or "col_1" not in str(profile_filters[0].get("value_default"))
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} profile filter changed: {profile_filters}")
    if str((profile_get.get("input") or {}).get("table_id")) != PROFILE_TABLE:
        raise RuntimeError(f"recipe {RECIPE_ID} profile table changed")
    stop = next((node for node in _walk_nodes(raw) if node.get("keyword") == "stop"), None)
    if not isinstance(stop, dict) or (stop.get("input") or {}).get("stop_with_error") != "false":
        raise RuntimeError(f"recipe {RECIPE_ID} stop step changed (non-error stop expected)")
    if str(stop.get("as") or "") != STOP_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} stop step id changed")
    add = next(node for node in _walk_nodes(raw) if str(node.get("as") or "") == ADD_AS)
    parameters = (add.get("input") or {}).get("parameters") or {}
    if sorted(parameters.keys()) != sorted(CREDITED_RECORD_KEYS):
        raise RuntimeError(f"recipe {RECIPE_ID} add_record parameters changed: {sorted(parameters.keys())}")
    if parameters.get(AC_CREDITED_DATE) != _CREDITED_DATE_FORMULA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} Credited Date formula changed (clean Asia/Tokyo zone expected): "
            f"{parameters.get(AC_CREDITED_DATE)!r}"
        )
    if parameters.get(AC_STATUS) != "CREDITED":
        raise RuntimeError(f"recipe {RECIPE_ID} Status literal changed")
    if str((add.get("input") or {}).get("table_id")) != ACTIVITY_TABLE:
        raise RuntimeError(f"recipe {RECIPE_ID} activity table changed")
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "quest_table": QUEST_TABLE,
        "profile_table": PROFILE_TABLE,
        "activity_table": ACTIVITY_TABLE,
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


def seed_128894356(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_128894356(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    handle = _require_trigger_shape(trigger)
    now = data.get("now")
    credited_date = _require_now_pin(now)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["workato_db_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the workato_db_table section; "
            f"got {sorted(seed_in.keys())}"
        )
    tables = _require_db_table_section(seed_in["workato_db_table"])
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    _require_expect_items(expect)
    branch = expect.get("branch")
    if branch not in BRANCHES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch must be one of {BRANCHES}; got {branch!r}")
    if bool(expect.get("stopped")) != (branch == "profile_missing_stop"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.stopped must be true exactly on the profile_missing_stop branch"
        )
    # Branch/seed coherence: IF-4 is decided by the seeded profile rows; the
    # credited fields by the single quest config row + the FIRST profile match.
    quest_rows = [row for row in tables[QUEST_TABLE] if str(row.get(QL_QUEST_CODE)) == QUEST_CODE_VALUE]
    if len(quest_rows) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seeds must include exactly ONE {QUEST_CODE_VALUE} quest-list "
            f"row (got {len(quest_rows)}) — the lookup is UNGUARDED and an empty match "
            "silently credits null Quest Name/Code (probe-verified)"
        )
    matching_profiles = [row for row in tables[PROFILE_TABLE] if str(row.get(PR_X_HANDLE)) == handle]
    if branch == "profile_missing_stop":
        if matching_profiles:
            raise RuntimeError(
                f"recipe {RECIPE_ID} profile_missing_stop variant seeds a profile for handle {handle!r}"
            )
        if expect.get("credited_date") is not None or expect.get("credited_record") is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} profile_missing_stop variant must pin credited_date and "
                "credited_record null"
            )
    else:
        if branch == "profile_found_credited" and len(matching_profiles) != 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} profile_found_credited variant must seed exactly ONE "
                f"matching profile (got {len(matching_profiles)})"
            )
        if branch == "multi_profile_first_row" and len(matching_profiles) < 2:
            raise RuntimeError(
                f"recipe {RECIPE_ID} multi_profile_first_row variant must seed at least TWO "
                f"matching profiles (got {len(matching_profiles)})"
            )
        if expect.get("credited_date") != credited_date:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.credited_date must be the Asia/Tokyo render of "
                f"seed.now ({credited_date!r}); got {expect.get('credited_date')!r}"
            )
        credited_record = expect.get("credited_record")
        expected_record = {
            AC_QUEST_NAME: quest_rows[0].get(QL_QUEST_NAME),
            AC_CREDITED_DATE: credited_date,
            AC_USER_ID: matching_profiles[0].get(PR_EMAIL),
            AC_STATUS: "CREDITED",
            AC_QUEST_CODE: QUEST_CODE_VALUE,
        }
        if credited_record != expected_record:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.credited_record must pin the FIRST matching "
                f"profile's email + the quest config fields: {expected_record}; got "
                f"{credited_record}"
            )
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole run"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "now": now,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_128894356(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_128894356(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
    if not str(seed.get("now") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing the pinned now")
    initial_snapshot = ctx.tools.call("harness.workato_db_table.snapshot", {})
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = ctx.tools.call("harness.workato_db_table.snapshot", {})
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "now": seed.get("now"),
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
    result["verifier"] = verify_128894356(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> str:
    if sorted(trigger.keys()) != ["columns"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'columns': ...}} — the recipe "
            f"dereferences only columns.col_1; got {sorted(trigger.keys())}"
        )
    columns = trigger["columns"]
    if not isinstance(columns, dict) or sorted(columns.keys()) != ["col_1"]:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger columns must be exactly {{'col_1': ...}}")
    handle = columns["col_1"]
    if not isinstance(handle, str) or not handle.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} columns.col_1 must be a non-empty string")
    return handle


def _require_now_pin(now: Any) -> str:
    if not isinstance(now, str) or not now.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must pin 'now' (the Credited Date formula "
            "fails fast without seed['now'] — probe-verified)"
        )
    try:
        dt = datetime.datetime.fromisoformat(now.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(f"recipe {RECIPE_ID} 'now' must be ISO-8601: {exc}") from exc
    if dt.tzinfo is None:
        raise RuntimeError(f"recipe {RECIPE_ID} 'now' must carry timezone information")
    # Same render path as the engine's strftime_seed_now_in_zone.
    return dt.astimezone(ZoneInfo(CREDITED_TZ)).strftime(CREDITED_FMT)


def _require_db_table_section(section: Any) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table must be exactly {{'tables': ...}}"
        )
    tables = section["tables"]
    expected_ids = sorted([QUEST_TABLE, PROFILE_TABLE, ACTIVITY_TABLE])
    if not isinstance(tables, dict) or sorted(tables.keys()) != expected_ids:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly tables {expected_ids} "
            "(rows may be explicit empty lists)"
        )
    for table_id, columns in (
        (QUEST_TABLE, QUEST_COLUMNS),
        (PROFILE_TABLE, PROFILE_COLUMNS),
        (ACTIVITY_TABLE, ACTIVITY_COLUMNS),
    ):
        rows = tables[table_id]
        if not isinstance(rows, list):
            raise RuntimeError(f"recipe {RECIPE_ID} table {table_id} rows must be a list")
        record_ids: set[str] = set()
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                raise RuntimeError(f"recipe {RECIPE_ID} table {table_id} row {idx} must be an object")
            unknown = sorted(set(row.keys()) - set(columns))
            if unknown:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table_id} row {idx} has unknown columns: {unknown}"
                )
            for column, value in row.items():
                if not isinstance(value, str):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} table {table_id} row {idx}.{column} must be a string "
                        "(the mock compares filter values on canonical strings)"
                    )
            record_id_col = QL_RECORD_ID  # shared Record ID column id across the tables
            if not str(row.get(record_id_col) or "").strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table_id} row {idx} requires a non-empty Record ID"
                )
            record_ids.add(str(row[record_id_col]))
        if len(record_ids) != len(rows):
            raise RuntimeError(f"recipe {RECIPE_ID} table {table_id} Record IDs must be unique")
    return tables


def _require_expect_items(expect: dict[str, Any]) -> None:
    items = expect.get("tool_expectations")
    if not isinstance(items, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must be a list")
    for idx, item in enumerate(items):
        if not isinstance(item, dict) or not item.get("tool"):
            raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[{idx}] must be an object with a tool")
        unknown = sorted(set(item.keys()) - _EXPECT_ITEM_KEYS)
        if unknown:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] has unsupported keys: {unknown}"
            )
        if not (set(item.keys()) & _EXPECT_VALUE_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] must pin at least one VALUE key "
                f"({sorted(_EXPECT_VALUE_KEYS)})"
            )
    credited_date = expect.get("credited_date")
    if credited_date is not None and not re.fullmatch(r"\d{2}/\d{2}/\d{4}", str(credited_date)):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.credited_date must render as %m/%d/%Y; got {credited_date!r}"
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


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
