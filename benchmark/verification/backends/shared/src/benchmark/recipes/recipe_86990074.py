from __future__ import annotations

import json
from typing import Any

from ..context import RecipeContext
from ..variant_input import trigger_input, variant_data
from ..verifier import verify_86990074
from .snowflake_live_recipe_utils import (
    run_live_snowflake_recipe,
    seed_live_snowflake,
    seed_workato_db_section,
    snowflake_seed_base,
)


RECIPE_ID = "86990074"
SEED_TYPE = "scheduled_snowflake_app_access_level_dt_upsert_variant"
TRACK = "live_snowflake_workato_db_upsert"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "b46dd68f"
SEARCH_AS = "d1dbd7b0"
FOREACH_AS = "a4327fb6"
UPSERT_AS = "330069fa"
SNOWFLAKE_TABLE = "PUBLIC.FULL_APP_ACCESS_LEVEL"
TABLE_ID = "4326"
PRIMARY_FIELD_ID = "6dce61e4-27e7-4174-9d3f-e15ae3665454"
PRIMARY_COLUMN = "6dce61e4_27e7_4174_9d3f_e15ae3665454"

# Daily 00:00 clock trigger (payload-less, seed.trigger = {}):
#   2  snowflake.search_rows (LIVE) d1dbd7b0: FULL-TABLE read of
#      PUBLIC.FULL_APP_ACCESS_LEVEL (text-toggled table name, NO where) ->
#      'select * from <SNOWFLAKE_DATABASE>.PUBLIC.FULL_APP_ACCESS_LEVEL
#      limit 50000' (offset '0' dropped by _append_limit_offset — re-probed
#      verbatim on HEAD 07af31c2). _fetch_rows adds lowercase aliases of the
#      UPPERCASE physical columns, which is what the foreach pills resolve.
#   3  FOREACH a4327fb6 over rows (repeat_mode simple; zero rows -> zero
#      iterations):
#   4    workato_db_table.upsert_record 330069fa (Workato-internal MOCK per
#        backend policy) table 4326 '[APPS] Snowflake: APP_ACCESS_LEVEL',
#        primary_field_id 6dce61e4-27e7-…-e15ae3665454 (DASHED — the mock's
#        _primary_keys normalizes it against the UNDERSCORED record keys,
#        re-probed insert->update on HEAD), 12 parameters all foreach pills.
# Mock write semantics (documented + re-probed): _clean STRINGIFIES
# non-strings (True->'true', 129.5->'129.5') and DROPS None params — a NULL
# snowflake cell never reaches the stored record on insert, and on the update
# arm the absent key LEAVES the previous value in place.
# The full-table SELECT has no ORDER BY: multi-row variants pin upserts and
# the final table as MULTISETS keyed by the App Access Level ID (batch-07
# no-ORDER-BY rule); _row_id assignment order is NOT contractual, so
# final_table_records exclude _row_id (the fragment separately requires
# unique sequential-range row ids).
# SEED-AUTHORING CONSTRAINT: app_license_cost seeds must be NULL or a
# NON-INTEGRAL float — Snowflake FLOAT returns 40.0 for an integral seed and
# the mock would store '40.0' while a naive expect pins '40'; fractional
# costs keep the string form deterministic end-to-end.

_RAW_PIN_JSON = r"""{"as": "b46dd68f", "block": [{"as": "d1dbd7b0", "block": [], "input": {"limit": "50000", "offset": "0", "table": "PUBLIC.FULL_APP_ACCESS_LEVEL"}, "keyword": "action", "name": "search_rows", "number": 2, "provider": "snowflake", "skip": false}, {"as": "a4327fb6", "block": [{"as": "330069fa", "block": [], "input": {"parameters": {"038c9907_fec3_4f50_abd8_fd0fbdcc1383": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a4327fb6\",\"path\":[\"status\"]}')}", "1aa5554d_f5ab_4703_9d6e_faf816041d56": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a4327fb6\",\"path\":[\"description\"]}')}", "2918db41_4973_448b_b3c0_22d2c18387cf": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a4327fb6\",\"path\":[\"can_hold_multiple_licenses\"]}')}", "3a9d89c8_8fe5_480f_af01_69b15d6fef4c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a4327fb6\",\"path\":[\"app_access_level_name\"]}')}", "4c661a35_02f5_4626_8c4b_88d5fa865568": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a4327fb6\",\"path\":[\"app_name\"]}')}", "6dce61e4_27e7_4174_9d3f_e15ae3665454": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a4327fb6\",\"path\":[\"app_access_level_id\"]}')}", "7e31c8cc_d936_453f_85d4_c07efd9245d7": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a4327fb6\",\"path\":[\"app_id\"]}')}", "99d52e63_5600_4199_807b_113cbb58a12a": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a4327fb6\",\"path\":[\"can_have_multiple_access_levels\"]}')}", "ac088077_a942_4bd8_90f5_990ba4664e1a": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a4327fb6\",\"path\":[\"app_license_id\"]}')}", "c3fbbb1b_7687_40e8_8c44_ded6586ca043": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a4327fb6\",\"path\":[\"app_license_cost\"]}')}", "c54daf0a_6d98_4515_a065_d7e5b20bceed": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a4327fb6\",\"path\":[\"app_license_name\"]}')}", "da068f90_734d_42fc_b7a3_f06db43c9bda": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"a4327fb6\",\"path\":[\"access_inherent\"]}')}"}, "primary_field_id": "6dce61e4-27e7-4174-9d3f-e15ae3665454", "table_id": "4326"}, "keyword": "action", "name": "upsert_record", "number": 4, "provider": "workato_db_table", "skip": false}], "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"d1dbd7b0\",\"path\":[\"rows\"]}')}"}, "keyword": "foreach", "name": "", "number": 3, "provider": "", "repeat_mode": "simple", "skip": false, "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"d1dbd7b0\",\"path\":[\"rows\"]}')}"}], "input": {"time_unit": "days", "trigger_at": "00:00:00", "trigger_every": "1"}, "keyword": "trigger", "name": "scheduled_event", "number": 1, "provider": "clock", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

# upsert parameter uuid -> snowflake column (lowercase pill alias).
PARAM_TO_COLUMN = {
    "038c9907_fec3_4f50_abd8_fd0fbdcc1383": "status",
    "1aa5554d_f5ab_4703_9d6e_faf816041d56": "description",
    "2918db41_4973_448b_b3c0_22d2c18387cf": "can_hold_multiple_licenses",
    "3a9d89c8_8fe5_480f_af01_69b15d6fef4c": "app_access_level_name",
    "4c661a35_02f5_4626_8c4b_88d5fa865568": "app_name",
    "6dce61e4_27e7_4174_9d3f_e15ae3665454": "app_access_level_id",
    "7e31c8cc_d936_453f_85d4_c07efd9245d7": "app_id",
    "99d52e63_5600_4199_807b_113cbb58a12a": "can_have_multiple_access_levels",
    "ac088077_a942_4bd8_90f5_990ba4664e1a": "app_license_id",
    "c3fbbb1b_7687_40e8_8c44_ded6586ca043": "app_license_cost",
    "c54daf0a_6d98_4515_a065_d7e5b20bceed": "app_license_name",
    "da068f90_734d_42fc_b7a3_f06db43c9bda": "access_inherent",
}
BOOLEAN_COLUMNS = (
    "access_inherent",
    "can_have_multiple_access_levels",
    "can_hold_multiple_licenses",
)
FLOAT_COLUMN = "app_license_cost"
SNOWFLAKE_COLUMNS = {
    column: (
        "boolean" if column in BOOLEAN_COLUMNS
        else "float" if column == FLOAT_COLUMN
        else "string"
    )
    for column in sorted(PARAM_TO_COLUMN.values())
}

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (SEARCH_AS, "snowflake", "search_rows"),
    (UPSERT_AS, "workato_db_table", "upsert_record"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows",
    "workato_db_table.upsert_record",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows",
    "workato_db_table.upsert_record",
]
BRANCHES = ("fresh_insert_all", "update_existing_by_primary", "zero_rows")
REQUIRED_EXPECT_KEYS = (
    "branch",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "sql_row_count",
    "upsert_records",
    "created_by_primary",
    "initial_table_rows",
    "final_table_records",
)


def validate_86990074(raw: dict[str, Any]) -> dict[str, Any]:
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
    search_input = actions[0].get("input") or {}
    if (
        str(search_input.get("table") or "") != SNOWFLAKE_TABLE
        or str(search_input.get("limit") or "") != "50000"
        or str(search_input.get("offset") or "") != "0"
        or "where" in search_input
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} full-table search config changed: {search_input}")
    upsert_input = actions[1].get("input") or {}
    if (
        str(upsert_input.get("table_id") or "") != TABLE_ID
        or upsert_input.get("primary_field_id") != PRIMARY_FIELD_ID
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} upsert target changed: {upsert_input}")
    parameters = upsert_input.get("parameters") or {}
    if sorted(parameters.keys()) != sorted(PARAM_TO_COLUMN.keys()):
        raise RuntimeError(f"recipe {RECIPE_ID} upsert parameters changed: {sorted(parameters.keys())}")
    for uuid, column in PARAM_TO_COLUMN.items():
        if f'\\"path\\":[\\"{column}\\"]' not in json.dumps(parameters.get(uuid) or ""):
            raise RuntimeError(f"recipe {RECIPE_ID} upsert pill for {column} changed")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "snowflake_table": SNOWFLAKE_TABLE,
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


def seed_86990074(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_86990074(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (payload-less scheduler tick)"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["snowflake_live", "workato_db_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly snowflake_live + workato_db_table; "
            f"got {sorted(seed_in.keys()) if isinstance(seed_in, dict) else seed_in!r}"
        )
    snowflake_rows = _require_snowflake_section(seed_in["snowflake_live"])
    dt_rows = _require_db_table_section(seed_in["workato_db_table"])
    _require_expect_coherence(data, snowflake_rows, dt_rows)
    if data.get("force_action_error") is not None:
        raise RuntimeError(f"recipe {RECIPE_ID} has no catch: forced action errors would fail the run")
    provision = seed_live_snowflake(RECIPE_ID, data, ctx)
    return snowflake_seed_base(
        recipe_id=RECIPE_ID,
        seed_type=SEED_TYPE,
        track=TRACK,
        validation=validation,
        ctx=ctx,
        snowflake_state=provision["state"],
        extra={
            "trigger": trigger,
            "workato_db_table": seed_workato_db_section(RECIPE_ID, data),
        },
    )


def run_86990074(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
    return run_live_snowflake_recipe(
        recipe_id=RECIPE_ID,
        track=TRACK,
        raw=raw,
        seed=seed,
        ctx=ctx,
        validation=validate_86990074(raw),
        expected_raw_tools=EXPECTED_RAW_TOOLS,
        allowed_tools=ALLOWED_TOOLS,
        verifier=verify_86990074,
        include_workato_db=True,
    )


def _require_snowflake_section(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}}")
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [SNOWFLAKE_TABLE]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed must declare exactly Snowflake table {SNOWFLAKE_TABLE}")
    spec = tables[SNOWFLAKE_TABLE]
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(f"recipe {RECIPE_ID} snowflake table must declare exactly columns + rows")
    if spec["columns"] != SNOWFLAKE_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} snowflake columns must be exactly {SNOWFLAKE_COLUMNS} "
            "(booleans/float typed so the pill values round-trip deterministically)"
        )
    rows = spec["rows"]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} snowflake rows must be a list")
    primaries: set[str] = set()
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} snowflake row {idx} must be an object")
        unknown = sorted(set(row.keys()) - set(SNOWFLAKE_COLUMNS))
        if unknown:
            raise RuntimeError(f"recipe {RECIPE_ID} snowflake row {idx} has unknown columns: {unknown}")
        for column, value in row.items():
            if value is None:
                continue
            if column in BOOLEAN_COLUMNS:
                if not isinstance(value, bool):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} snowflake row {idx}.{column} must be a bool or null"
                    )
            elif column == FLOAT_COLUMN:
                if isinstance(value, bool) or not isinstance(value, float) or value == int(value):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} snowflake row {idx}.{column} must be null or a "
                        "NON-INTEGRAL float (integral floats round-trip as '40.0' vs '40' — "
                        "see module header)"
                    )
            elif not isinstance(value, str):
                raise RuntimeError(f"recipe {RECIPE_ID} snowflake row {idx}.{column} must be a string or null")
        primary = row.get("app_access_level_id")
        if not isinstance(primary, str) or not primary.strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} snowflake row {idx} requires a non-empty app_access_level_id "
                "(the upsert primary)"
            )
        primaries.add(primary)
    if len(primaries) != len(rows):
        raise RuntimeError(
            f"recipe {RECIPE_ID} snowflake app_access_level_id values must be unique "
            "(duplicate primaries would chain insert->update inside one run)"
        )
    return rows


def _require_db_table_section(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.workato_db_table must be exactly {{'tables': ...}}")
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [TABLE_ID]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed must declare exactly db table {TABLE_ID}")
    rows = tables[TABLE_ID]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} db table rows must be a list")
    primaries: set[str] = set()
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} db table row {idx} must be an object")
        unknown = sorted(set(row.keys()) - set(PARAM_TO_COLUMN.keys()))
        if unknown:
            raise RuntimeError(f"recipe {RECIPE_ID} db table row {idx} has unknown columns: {unknown}")
        for column, value in row.items():
            if not isinstance(value, str):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} db table row {idx}.{column} must be a string "
                    "(the mock stores canonical strings)"
                )
        primary = row.get(PRIMARY_COLUMN)
        if not isinstance(primary, str) or not primary.strip():
            raise RuntimeError(f"recipe {RECIPE_ID} db table row {idx} requires the primary column")
        primaries.add(primary)
    if len(primaries) != len(rows):
        raise RuntimeError(f"recipe {RECIPE_ID} db table primary values must be unique")
    return rows


def _typed_record(row: dict[str, Any]) -> dict[str, Any]:
    return {uuid: row.get(column) for uuid, column in PARAM_TO_COLUMN.items()}


def _clean_record(record: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in record.items():
        if value is None:
            continue
        if isinstance(value, bool):
            out[key] = "true" if value else "false"
        else:
            out[key] = value if isinstance(value, str) else str(value)
    return out


def _require_expect_coherence(
    data: dict[str, Any],
    snowflake_rows: list[dict[str, Any]],
    dt_rows: list[dict[str, Any]],
) -> None:
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    branch = expect.get("branch")
    if branch not in BRANCHES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch must be one of {BRANCHES}; got {branch!r}")
    seeded_by_primary = {row[PRIMARY_COLUMN]: row for row in dt_rows}
    expected_upserts = {row["app_access_level_id"]: _typed_record(row) for row in snowflake_rows}
    expected_created = {
        primary: primary not in seeded_by_primary for primary in expected_upserts
    }
    if expect.get("upsert_records") != expected_upserts:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.upsert_records must map each app_access_level_id to the "
            f"TYPED 12-key record (None for NULL cells): {expected_upserts}"
        )
    if expect.get("created_by_primary") != expected_created:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.created_by_primary incoherent with the seeded table "
            f"(primary match -> update, created=false): {expected_created}"
        )
    if expect.get("sql_row_count") != len(snowflake_rows):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.sql_row_count must be {len(snowflake_rows)}")
    if branch == "fresh_insert_all" and (dt_rows or not snowflake_rows or any(not c for c in expected_created.values())):
        raise RuntimeError(
            f"recipe {RECIPE_ID} fresh_insert_all requires an EMPTY table {TABLE_ID} and >=1 "
            "snowflake row (all inserts)"
        )
    if branch == "update_existing_by_primary" and (
        not any(not created for created in expected_created.values())
        or not any(created for created in expected_created.values())
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} update_existing_by_primary must exercise BOTH arms: at least "
            "one primary match (update) and one miss (insert)"
        )
    if branch == "zero_rows" and (snowflake_rows or not dt_rows):
        raise RuntimeError(
            f"recipe {RECIPE_ID} zero_rows requires an EMPTY snowflake table and a non-empty "
            f"db table (proving it stays untouched)"
        )
    normalized_initial = [
        {"_row_id": idx, "_created_by": "seed", **row} for idx, row in enumerate(dt_rows)
    ]
    if expect.get("initial_table_rows") != normalized_initial:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.initial_table_rows must be the seeded rows with "
            f"bookkeeping, byte-exact: {normalized_initial}"
        )
    expected_final: list[dict[str, Any]] = []
    for row in dt_rows:
        primary = row[PRIMARY_COLUMN]
        if primary in expected_upserts:
            expected_final.append(
                {"_created_by": "seed", **row, **_clean_record(expected_upserts[primary]),
                 "_modified_by": "agent"}
            )
        else:
            expected_final.append({"_created_by": "seed", **row})
    for primary, record in expected_upserts.items():
        if primary not in seeded_by_primary:
            expected_final.append({"_created_by": "agent", **_clean_record(record)})
    sort_key = lambda item: (str(item.get(PRIMARY_COLUMN)), json.dumps(item, sort_keys=True))
    if sorted(expect.get("final_table_records") or [], key=sort_key) != sorted(expected_final, key=sort_key):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_table_records must be the derived post-run "
            f"multiset (updates overlay stringified values in place and gain _modified_by, "
            f"inserts carry _created_by 'agent', _row_id excluded): {expected_final}"
        )
    expected_tools = ["snowflake.search_rows"] + ["workato_db_table.upsert_record"] * len(snowflake_rows)
    if expect.get("tools") != expected_tools or expect.get("executed_action_count") != len(expected_tools):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools/executed_action_count incoherent; expected {expected_tools}"
        )
    # tool_expectations carries ONLY the search pin: the generic index-aligned
    # db-write check compares the FULL args record against the final row,
    # which cannot express the update-arm None-drop semantics (a NULL pill
    # leaves the OLD stored value in place). The fragment pins every upsert
    # order-insensitively (typed record + created flag + final multiset).
    items = expect.get("tool_expectations")
    if (
        not isinstance(items, list)
        or len(items) != 1
        or not isinstance(items[0], dict)
        or items[0].get("tool") != "snowflake.search_rows"
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin exactly the snowflake search "
            "(upsert pinning lives in the verifier fragment, order-insensitive)"
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


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found
