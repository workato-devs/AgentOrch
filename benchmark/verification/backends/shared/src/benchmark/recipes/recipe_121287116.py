from __future__ import annotations

import json
from typing import Any

from ..context import RecipeContext
from ..variant_input import trigger_input, variant_data
from ..verifier import verify_121287116
from .snowflake_live_recipe_utils import (
    run_live_snowflake_recipe,
    seed_live_snowflake,
    seed_workato_db_section,
    snowflake_seed_base,
)


RECIPE_ID = "121287116"
SEED_TYPE = "scheduled_snowflake_churn_tracking_dt_upsert_variant"
TRACK = "live_snowflake_workato_db_upsert"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "923e5d87"
SEARCH_AS = "0fc36612"
FOREACH_AS = "e421eda4"
UPSERT_AS = "34efd203"
TABLE_ID = "29282"
PRIMARY_FIELD_ID = "7282605a-5019-4d32-9bca-ad22eee221a6"
PRIMARY_COLUMN = "7282605a_5019_4d32_9bca_ad22eee221a6"
OPPORTUNITY_TABLE = "salesforce.opportunity"
ACCOUNT_TABLE = "salesforce.account"
USER_TABLE = "salesforce.user"
SEED_TABLES = [OPPORTUNITY_TABLE, ACCOUNT_TABLE, USER_TABLE]


SQL = (
    "SELECT\nO.ID AS OPPTY_ID,\nO.NAME AS OPPTY_NAME,\nO.STAGENAME AS OPPTY_STAGE,\n"
    "A.ID AS ACCOUNT_ID,\nA.NAME AS ACCOUNT_NAME,\nA.SALES_TEAM__C AS SALES_TEAM,\n"
    "O.SAVE_OUTREACH__C AS SAVE_OUTREACH,\nO.DAYS_PAST_DUE__C AS DAYS_PAST_DUE,\n"
    "AO.NAME AS ACCOUNT_OWNER_NAME,\nAO.EMAIL AS ACCOUNT_OWNER_EMAIL,\n"
    "SO.EMAIL AS SUCCESS_OWNER_EMAIL\n\n"
    "FROM SALESFORCE.OPPORTUNITY O\nJOIN SALESFORCE.ACCOUNT A\nON O.ACCOUNTID = A.ID\n\n"
    "LEFT JOIN SALESFORCE.USER AO\nON A.OWNERID = AO.ID\n\n"
    "LEFT JOIN SALESFORCE.USER SO\nON A.EXPANSION_CSM__C = SO.ID\n\n"
    "WHERE O.TYPE = 'Churn'\nAND O.CHURN_TYPE__C = 'Non Payment'"
)

_RAW_PIN_JSON = r"""{"as": "923e5d87", "block": [{"as": "0fc36612", "block": [], "input": {"limit": "50000", "output_schema": "[{\"name\":\"OPPTY_ID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"OPPTY ID\"},{\"name\":\"OPPTY_NAME\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"OPPTY NAME\"},{\"name\":\"OPPTY_STAGE\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"OPPTY STAGE\"},{\"name\":\"ACCOUNT_ID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"ACCOUNT ID\"},{\"name\":\"ACCOUNT_NAME\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"ACCOUNT NAME\"},{\"name\":\"SALES_TEAM\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"SALES TEAM\"},{\"name\":\"SAVE_OUTREACH\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"SAVE OUTREACH\"},{\"name\":\"DAYS_PAST_DUE\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"DAYS PAST DUE\",\"parse_output\":\"integer_conversion\"},{\"name\":\"ACCOUNT_OWNER_NAME\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"ACCOUNT OWNER NAME\"},{\"name\":\"ACCOUNT_OWNER_EMAIL\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"ACCOUNT OWNER EMAIL\"},{\"name\":\"SUCCESS_OWNER_EMAIL\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"SUCCESS OWNER EMAIL\"}]", "sql": "SELECT\nO.ID AS OPPTY_ID,\nO.NAME AS OPPTY_NAME,\nO.STAGENAME AS OPPTY_STAGE,\nA.ID AS ACCOUNT_ID,\nA.NAME AS ACCOUNT_NAME,\nA.SALES_TEAM__C AS SALES_TEAM,\nO.SAVE_OUTREACH__C AS SAVE_OUTREACH,\nO.DAYS_PAST_DUE__C AS DAYS_PAST_DUE,\nAO.NAME AS ACCOUNT_OWNER_NAME,\nAO.EMAIL AS ACCOUNT_OWNER_EMAIL,\nSO.EMAIL AS SUCCESS_OWNER_EMAIL\n\nFROM SALESFORCE.OPPORTUNITY O\nJOIN SALESFORCE.ACCOUNT A\nON O.ACCOUNTID = A.ID\n\nLEFT JOIN SALESFORCE.USER AO\nON A.OWNERID = AO.ID\n\nLEFT JOIN SALESFORCE.USER SO\nON A.EXPANSION_CSM__C = SO.ID\n\nWHERE O.TYPE = 'Churn'\nAND O.CHURN_TYPE__C = 'Non Payment'"}, "keyword": "action", "name": "search_rows_sql", "number": 2, "provider": "snowflake", "skip": false}, {"as": "e421eda4", "block": [{"as": "34efd203", "block": [], "input": {"parameters": {"7282605a_5019_4d32_9bca_ad22eee221a6": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"e421eda4\",\"path\":[\"oppty_id\"]}')}", "7886e8f6_1cb4_408a_9f96_933976459847": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"e421eda4\",\"path\":[\"account_owner_email\"]}')}", "7e5da151_7500_495d_beba_04a2d895478d": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"e421eda4\",\"path\":[\"oppty_name\"]}')}", "9f4dbf40_39f9_4855_9e54_00b0867ffa0a": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"e421eda4\",\"path\":[\"account_owner_name\"]}')}", "a5d268ff_d69a_4e5f_b76d_64dc19c4fdc3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"e421eda4\",\"path\":[\"days_past_due\"]}')}", "c47d31af_656f_4ec0_bbaf_6def70bf4931": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"e421eda4\",\"path\":[\"sales_team\"]}')}", "c8e6f121_228e_41a6_8c7b_ba124d427f7a": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"e421eda4\",\"path\":[\"account_name\"]}')}", "ce590e2a_eec4_4dc2_bde2_321f102f3b1d": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"e421eda4\",\"path\":[\"oppty_stage\"]}')}", "d4bf8c6b_fdad_492d_a51e_de59b8bb7896": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"e421eda4\",\"path\":[\"save_outreach\"]}')}", "fc98a645_e702_48a3_9d7c_8a15be5b5b61": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"e421eda4\",\"path\":[\"success_owner_email\"]}')}"}, "primary_field_id": "7282605a-5019-4d32-9bca-ad22eee221a6", "table_id": "29282"}, "keyword": "action", "name": "upsert_record", "number": 4, "provider": "workato_db_table", "skip": false}], "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"0fc36612\",\"path\":[\"rows\"]}')}"}, "keyword": "foreach", "name": "", "number": 3, "provider": "", "repeat_mode": "simple", "skip": false, "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"0fc36612\",\"path\":[\"rows\"]}')}"}], "input": {"time_unit": "days", "timezone": "<anon>Europe/London</anon>", "trigger_at": "07:00:00", "trigger_every": "1"}, "keyword": "trigger", "name": "scheduled_event", "number": 1, "provider": "clock", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

PARAM_TO_ALIAS = {
    "7282605a_5019_4d32_9bca_ad22eee221a6": "oppty_id",
    "7886e8f6_1cb4_408a_9f96_933976459847": "account_owner_email",
    "7e5da151_7500_495d_beba_04a2d895478d": "oppty_name",
    "9f4dbf40_39f9_4855_9e54_00b0867ffa0a": "account_owner_name",
    "a5d268ff_d69a_4e5f_b76d_64dc19c4fdc3": "days_past_due",
    "c47d31af_656f_4ec0_bbaf_6def70bf4931": "sales_team",
    "c8e6f121_228e_41a6_8c7b_ba124d427f7a": "account_name",
    "ce590e2a_eec4_4dc2_bde2_321f102f3b1d": "oppty_stage",
    "d4bf8c6b_fdad_492d_a51e_de59b8bb7896": "save_outreach",
    "fc98a645_e702_48a3_9d7c_8a15be5b5b61": "success_owner_email",
}
MESSAGE_ID_COLUMN = "6b92357c_3529_4d85_be67_0b6a76b54ab2"  # recipe never writes it
DT_COLUMNS = tuple(sorted([*PARAM_TO_ALIAS.keys(), MESSAGE_ID_COLUMN]))

OPPORTUNITY_COLUMNS = {
    "id": "string",
    "name": "string",
    "stagename": "string",
    "accountid": "string",
    "type": "string",
    "churn_type__c": "string",
    "save_outreach__c": "string",
    "days_past_due__c": "integer",
}
ACCOUNT_COLUMNS = {
    "id": "string",
    "name": "string",
    "sales_team__c": "string",
    "ownerid": "string",
    "expansion_csm__c": "string",
}
USER_COLUMNS = {
    "id": "string",
    "name": "string",
    "email": "string",
}
TABLE_COLUMN_SPECS = {
    OPPORTUNITY_TABLE: OPPORTUNITY_COLUMNS,
    ACCOUNT_TABLE: ACCOUNT_COLUMNS,
    USER_TABLE: USER_COLUMNS,
}

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (SEARCH_AS, "snowflake", "search_rows_sql"),
    (UPSERT_AS, "workato_db_table", "upsert_record"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_db_table.upsert_record",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_db_table.upsert_record",
]
BRANCHES = (
    "churn_rows_insert",
    "update_existing_opp",
    "left_join_null_emails",
    "where_arms_zero",
)
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


def validate_121287116(raw: dict[str, Any]) -> dict[str, Any]:
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
    trigger_config = raw.get("input") or {}
    if trigger_config.get("timezone") != "<anon>Europe/London</anon>":
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger timezone changed (anon-tagged schedule-only config): "
            f"{trigger_config.get('timezone')!r}"
        )
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    search_input = actions[0].get("input") or {}
    if search_input.get("sql") != SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} SQL changed: {search_input.get('sql')!r}")
    if str(search_input.get("limit") or "") != "50000":
        raise RuntimeError(f"recipe {RECIPE_ID} search limit changed")
    upsert_input = actions[1].get("input") or {}
    if (
        str(upsert_input.get("table_id") or "") != TABLE_ID
        or upsert_input.get("primary_field_id") != PRIMARY_FIELD_ID
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} upsert target changed: {upsert_input}")
    parameters = upsert_input.get("parameters") or {}
    if sorted(parameters.keys()) != sorted(PARAM_TO_ALIAS.keys()):
        raise RuntimeError(f"recipe {RECIPE_ID} upsert parameters changed: {sorted(parameters.keys())}")
    for uuid, alias in PARAM_TO_ALIAS.items():
        if f'\\"path\\":[\\"{alias}\\"]' not in json.dumps(parameters.get(uuid) or ""):
            raise RuntimeError(f"recipe {RECIPE_ID} upsert pill for {alias} changed")
    foreachs = _collect_keyword(raw, "foreach")
    if (
        len(foreachs) != 1
        or str(foreachs[0].get("as") or "") != FOREACH_AS
        or foreachs[0].get("repeat_mode") != "simple"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} foreach changed")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
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


def seed_121287116(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_121287116(raw)
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
    snowflake_tables = _require_snowflake_section(seed_in["snowflake_live"])
    dt_rows = _require_db_table_section(seed_in["workato_db_table"])
    _require_expect_coherence(data, snowflake_tables, dt_rows)
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


def run_121287116(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
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
        validation=validate_121287116(raw),
        expected_raw_tools=EXPECTED_RAW_TOOLS,
        allowed_tools=ALLOWED_TOOLS,
        verifier=verify_121287116,
        include_workato_db=True,
    )


def _require_snowflake_section(section: Any) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}}")
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted(SEED_TABLES):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly Snowflake tables {sorted(SEED_TABLES)}"
        )
    out: dict[str, list[dict[str, Any]]] = {}
    for table, columns in TABLE_COLUMN_SPECS.items():
        spec = tables[table]
        if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} snowflake table {table} must declare exactly columns + rows"
            )
        if spec["columns"] != columns:
            raise RuntimeError(
                f"recipe {RECIPE_ID} snowflake table {table} columns must be exactly {columns}"
            )
        rows = spec["rows"]
        if not isinstance(rows, list):
            raise RuntimeError(f"recipe {RECIPE_ID} snowflake table {table} rows must be a list")
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                raise RuntimeError(f"recipe {RECIPE_ID} snowflake table {table} row {idx} must be an object")
            unknown = sorted(set(row.keys()) - set(columns))
            if unknown:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} snowflake table {table} row {idx} has unknown columns: {unknown}"
                )
            for column, value in row.items():
                if value is None:
                    continue
                if column == "days_past_due__c":
                    if isinstance(value, bool) or not isinstance(value, int):
                        raise RuntimeError(
                            f"recipe {RECIPE_ID} {table} row {idx}.{column} must be an int or "
                            "null (integer column: the mock stores '12', never '12.0')"
                        )
                elif not isinstance(value, str):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} {table} row {idx}.{column} must be a string or null"
                    )
            if not str(row.get("id") or "").strip():
                raise RuntimeError(f"recipe {RECIPE_ID} {table} row {idx} requires a non-empty id")
        ids = [row["id"] for row in rows]
        if len(set(ids)) != len(ids):
            raise RuntimeError(f"recipe {RECIPE_ID} {table} ids must be unique (join keys)")
        out[table] = rows
    return out


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
        unknown = sorted(set(row.keys()) - set(DT_COLUMNS))
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
            raise RuntimeError(f"recipe {RECIPE_ID} db table row {idx} requires the Opp ID primary column")
        primaries.add(primary)
    if len(primaries) != len(rows):
        raise RuntimeError(f"recipe {RECIPE_ID} db table Opp ID values must be unique")
    return rows


def _derive_query_rows(snowflake_tables: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    accounts = {row["id"]: row for row in snowflake_tables[ACCOUNT_TABLE]}
    users = {row["id"]: row for row in snowflake_tables[USER_TABLE]}
    out: list[dict[str, Any]] = []
    for opp in snowflake_tables[OPPORTUNITY_TABLE]:
        if opp.get("type") != "Churn" or opp.get("churn_type__c") != "Non Payment":
            continue
        account = accounts.get(opp.get("accountid"))
        if account is None:
            continue  # INNER JOIN
        owner = users.get(account.get("ownerid")) if account.get("ownerid") is not None else None
        csm = users.get(account.get("expansion_csm__c")) if account.get("expansion_csm__c") is not None else None
        out.append({
            "oppty_id": opp.get("id"),
            "oppty_name": opp.get("name"),
            "oppty_stage": opp.get("stagename"),
            "account_name": account.get("name"),
            "sales_team": account.get("sales_team__c"),
            "save_outreach": opp.get("save_outreach__c"),
            "days_past_due": opp.get("days_past_due__c"),
            "account_owner_name": owner.get("name") if owner else None,
            "account_owner_email": owner.get("email") if owner else None,
            "success_owner_email": csm.get("email") if csm else None,
        })
    return out


def _clean_record(record: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in record.items():
        if value is None:
            continue
        out[key] = value if isinstance(value, str) else str(value)
    return out


def _require_expect_coherence(
    data: dict[str, Any],
    snowflake_tables: dict[str, list[dict[str, Any]]],
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
    query_rows = _derive_query_rows(snowflake_tables)
    primaries = [row["oppty_id"] for row in query_rows]
    if len(set(primaries)) != len(primaries):
        raise RuntimeError(
            f"recipe {RECIPE_ID} qualifying Opp IDs must be unique (duplicates would chain "
            "insert->update inside one run)"
        )
    seeded_by_primary = {row[PRIMARY_COLUMN]: row for row in dt_rows}
    expected_upserts = {
        row["oppty_id"]: {uuid: row[alias] for uuid, alias in PARAM_TO_ALIAS.items()}
        for row in query_rows
    }
    expected_created = {primary: primary not in seeded_by_primary for primary in expected_upserts}
    if expect.get("upsert_records") != expected_upserts:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.upsert_records must map each Opp ID to the TYPED "
            f"10-key record (None for LEFT-JOIN NULLs): {expected_upserts}"
        )
    if expect.get("created_by_primary") != expected_created:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.created_by_primary incoherent with the seeded table: "
            f"{expected_created}"
        )
    if expect.get("sql_row_count") != len(query_rows):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.sql_row_count must be {len(query_rows)}")
    opps = snowflake_tables[OPPORTUNITY_TABLE]
    accounts = {row["id"] for row in snowflake_tables[ACCOUNT_TABLE]}
    if branch == "churn_rows_insert":
        if dt_rows or len(query_rows) < 2 or any(
            value is None for record in expected_upserts.values() for value in record.values()
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} churn_rows_insert requires an EMPTY table {TABLE_ID}, >=2 "
                "fully-joined result rows and no NULL cells (all inserts)"
            )
    elif branch == "update_existing_opp":
        if (
            not any(not created for created in expected_created.values())
            or not any(created for created in expected_created.values())
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} update_existing_opp must exercise BOTH arms (>=1 primary "
                "match and >=1 miss)"
            )
    elif branch == "left_join_null_emails":
        if not any(
            record[
                "7886e8f6_1cb4_408a_9f96_933976459847"
            ] is None and record["fc98a645_e702_48a3_9d7c_8a15be5b5b61"] is None
            for record in expected_upserts.values()
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} left_join_null_emails must derive at least one row whose "
                "owner AND CSM emails are NULL (LEFT-JOIN misses -> _clean drops the params)"
            )
    elif branch == "where_arms_zero":
        if query_rows or not dt_rows:
            raise RuntimeError(
                f"recipe {RECIPE_ID} where_arms_zero requires ZERO qualifying rows and a "
                "non-empty db table (proving it stays untouched)"
            )
        has_type_arm = any(opp.get("type") != "Churn" for opp in opps)
        has_churn_arm = any(
            opp.get("type") == "Churn" and opp.get("churn_type__c") != "Non Payment" for opp in opps
        )
        has_join_arm = any(
            opp.get("type") == "Churn"
            and opp.get("churn_type__c") == "Non Payment"
            and opp.get("accountid") not in accounts
            for opp in opps
        )
        if not (has_type_arm and has_churn_arm and has_join_arm):
            raise RuntimeError(
                f"recipe {RECIPE_ID} where_arms_zero must seed all three exclusion arms "
                "(TYPE mismatch, CHURN_TYPE mismatch, INNER-JOIN account miss)"
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
            f"multiset (stringified overlays in place, None params dropped, inserts "
            f"_created_by 'agent', _row_id excluded): {expected_final}"
        )
    expected_tools = ["snowflake.search_rows_sql"] + ["workato_db_table.upsert_record"] * len(query_rows)
    if expect.get("tools") != expected_tools or expect.get("executed_action_count") != len(expected_tools):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools/executed_action_count incoherent; expected {expected_tools}"
        )
    # tool_expectations carries ONLY the search pin (same reasoning as sibling
    # 86990074: the index-aligned db-write check cannot express the update-arm
    # None-drop semantics; the fragment pins upserts order-insensitively).
    items = expect.get("tool_expectations")
    if (
        not isinstance(items, list)
        or len(items) != 1
        or not isinstance(items[0], dict)
        or items[0].get("tool") != "snowflake.search_rows_sql"
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin exactly the snowflake search"
        )


def _collect_keyword(node: dict[str, Any], keyword: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == keyword and not child.get("skip"):
            found.append(child)
        found.extend(_collect_keyword(child, keyword))
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
