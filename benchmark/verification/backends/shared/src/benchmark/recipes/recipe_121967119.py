from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_121967119


RECIPE_ID = "121967119"
SEED_TYPE = "chi_entry_dates_loaded_sync_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "workato_webhooks"
TRIGGER_NAME = "new_event"
TRIGGER_AS = "7f0d10a3"
PARSE_AS = "9d3ba345"
GET_AS = "f32d35bd"
SQL_AS = "91e97e92"
FOREACH_AS = "3ebb9454"
UPSERT_AS = "fa765093"
STOP_AS = "282ae64d"
DB_TABLE_ID = "16848"
PRIMARY_FIELD_ID = "1bfbff0a-6438-4de9-86f1-e02ba0ead9e0"
FIELD_ENTRY_DATE = "1bfbff0a_6438_4de9_86f1_e02ba0ead9e0"
FIELD_LOADED = "dc03d5e3_96f1_4b45_8e35_e1f1c675abfc"
SNOW_TABLE = "edw_db.workato_usage.flows_snapshot"
SNOW_COLUMNS = {"ENTRY_DATE": "date"}


_RAW_PIN_JSON = r"""{"as": "7f0d10a3", "block": [{"as": "9d3ba345", "block": [], "input": {"document": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"7f0d10a3\",\"path\":[\"payload\"]}')}", "sample_document": "{\"accountId\":139136,\"eventId\":\"wev_2YBoHtS7KlvmYY04QGiqzFpocmg\",\"timestamp\":\"<anon>2024-01-01T10:00:00.000000000Z</anon>\",\"eventType\":\"job.run.started\",\"webhookId\":\"wsu_2YBnj2uT2XAvH7mwzNJWmQyVN6O\",\"webhookName\":\"EDW_staging_deployment\",\"data\":{\"jobId\":\"452823\",\"jobName\":\"Ad hoc deploy\",\"runId\":\"216792841\",\"environmentId\":\"228594\",\"environmentName\":\"EDW_STAGING Deployment\",\"dbtVersion\":\"1.6.0-latest\",\"projectName\":\"EDW - Enteprise Data Warehouse\",\"projectId\":\"266836\",\"runStatus\":\"Running\",\"runStatusCode\":3,\"runStatusMessage\":\"None\",\"runReason\":\"Kicked off from the UI by <anon>john.smith@company.com</anon>\",\"runStartedAt\":\"<anon>2024-01-01T10:00:00Z</anon>\"}}"}, "keyword": "action", "name": "parse_json", "number": 2, "provider": "json_parser", "skip": false}, {"as": "", "block": [{"as": "f32d35bd", "block": [], "input": {"11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "1bfbff0a-6438-4de9-86f1-e02ba0ead9e0": "date", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "dc03d5e3-96f1-4b45-8e35-e1f1c675abfc": "boolean", "filters": [{"field_id": "dc03d5e3-96f1-4b45-8e35-e1f1c675abfc", "op_boolean": "istrue"}], "limit": "1", "order_by_field_id": "1bfbff0a-6438-4de9-86f1-e02ba0ead9e0", "order_direction": "desc", "table_id": "16848"}, "keyword": "action", "name": "get_records", "number": 4, "provider": "workato_db_table", "skip": false}, {"as": "91e97e92", "block": [], "input": {"orderby": "entry_date ASC", "parameters": {"schema": "[{\"name\":\"entry_date\",\"type\":\"date\",\"optional\":true,\"label\":\"entry_date\",\"details\":{\"real_name\":\"entry_date\"},\"control_type\":\"date\"}]"}, "sql": "select entry_date \nfrom edw_db.workato_usage.flows_snapshot\nwhere entry_date > '#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"f32d35bd\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"1bfbff0a_6438_4de9_86f1_e02ba0ead9e0\"]}')}'\ngroup by all"}, "keyword": "action", "name": "search_rows_sql", "number": 5, "provider": "snowflake", "skip": false}, {"as": "3ebb9454", "block": [{"as": "fa765093", "block": [], "input": {"parameters": {"1bfbff0a_6438_4de9_86f1_e02ba0ead9e0": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"3ebb9454\",\"path\":[\"entry_date\"]}')}", "dc03d5e3_96f1_4b45_8e35_e1f1c675abfc": "true"}, "primary_field_id": "1bfbff0a-6438-4de9-86f1-e02ba0ead9e0", "table_id": "16848"}, "keyword": "action", "name": "upsert_record", "number": 7, "provider": "workato_db_table", "skip": false}], "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"91e97e92\",\"path\":[\"rows\"]}')}"}, "keyword": "foreach", "name": "", "number": 6, "provider": "", "repeat_mode": "simple", "skip": false, "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"91e97e92\",\"path\":[\"rows\"]}')}"}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"json_parser\",\"line\":\"9d3ba345\",\"path\":[\"document\", \"data\", \"runStatus\"]}')}", "operand": "equals_to", "rhs": "Success"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 3, "provider": "", "skip": false}, {"as": "282ae64d", "block": [], "input": {"stop_with_error": "false"}, "keyword": "stop", "name": "", "number": 8, "provider": "", "skip": false}], "input": {"request": {"headers_schema": "[{\"control_type\":\"text\",\"label\":\"Accept encoding\",\"type\":\"string\",\"name\":\"accept_encoding\"},{\"control_type\":\"text\",\"label\":\"Authorization\",\"type\":\"string\",\"name\":\"authorization\"},{\"control_type\":\"text\",\"label\":\"Content length\",\"type\":\"string\",\"name\":\"content_length\"},{\"control_type\":\"text\",\"label\":\"Content type\",\"type\":\"string\",\"name\":\"content_type\"},{\"control_type\":\"text\",\"label\":\"User agent\",\"type\":\"string\",\"name\":\"user_agent\"},{\"control_type\":\"text\",\"label\":\"X amzn trace ID\",\"type\":\"string\",\"name\":\"x_amzn_trace_id\"},{\"control_type\":\"text\",\"label\":\"X correlation ID\",\"type\":\"string\",\"name\":\"x_correlation_id\"},{\"control_type\":\"text\",\"label\":\"X forwarded for\",\"type\":\"string\",\"name\":\"x_forwarded_for\"},{\"control_type\":\"text\",\"label\":\"X forwarded port\",\"type\":\"string\",\"name\":\"x_forwarded_port\"},{\"control_type\":\"text\",\"label\":\"X forwarded proto\",\"type\":\"string\",\"name\":\"x_forwarded_proto\"},{\"control_type\":\"text\",\"label\":\"X request ID\",\"type\":\"string\",\"name\":\"x_request_id\"}]", "query_params": "[]", "webhook_type": "rawdatatxt"}, "webhook_suffix": "workato_usage and plg_data schema completed running"}, "keyword": "trigger", "name": "new_event", "number": 1, "provider": "workato_webhooks", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (PARSE_AS, "json_parser", "parse_json"),
    (GET_AS, "workato_db_table", "get_records"),
    (SQL_AS, "snowflake", "search_rows_sql"),
    (UPSERT_AS, "workato_db_table", "upsert_record"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.parse_json",
    "workato_db_table.get_records",
    "snowflake.search_rows_sql",
    "workato_db_table.upsert_record",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "snowflake.search_rows_sql",
    "workato_db_table.upsert_record",
]
REQUIRED_EXPECT_KEYS = (
    "case",
    "branch",
    "run_status",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "latest_loaded_entry_date",
    "sql_dates",
    "upsert_records",
    "upsert_created",
    "initial_table_rows",
    "final_table_rows",
)
OPTIONAL_EXPECT_KEYS = ("final_table",)
BRANCHES = ("success_upserts", "success_no_new_dates", "not_success")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_121967119(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    if str(((raw.get("input") or {}).get("request") or {}).get("webhook_type")) != "rawdatatxt":
        raise RuntimeError(f"recipe {RECIPE_ID} webhook_type changed (payload must stay a raw string)")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    nodes = {str(node.get("as") or ""): node for node in _walk_nodes(raw)}
    # Semantic pins (the tree pin holds the bytes; these name the traps):
    # 1. the get_records order/limit trio (the fixed engine gap) + the
    #    loaded-istrue filter,
    get_input = nodes[GET_AS].get("input") or {}
    if (
        str(get_input.get("table_id")) != DB_TABLE_ID
        or str(get_input.get("order_by_field_id")) != PRIMARY_FIELD_ID
        or str(get_input.get("order_direction")) != "desc"
        or str(get_input.get("limit")) != "1"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} get_records order/limit changed: {get_input!r}")
    filters = get_input.get("filters") or []
    if (
        len(filters) != 1
        or str(filters[0].get("field_id")).replace("-", "_") != FIELD_LOADED
        or str(filters[0].get("op_boolean")) != "istrue"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} get_records filter changed: {filters!r}")
    # 2. the snowflake SQL + the separate orderby input the executor appends,
    sql_input = nodes[SQL_AS].get("input") or {}
    sql_text = str(sql_input.get("sql") or "")
    if (
        "group by all" not in sql_text
        or "entry_date > '" not in sql_text
        or SNOW_TABLE not in sql_text
        or str(sql_input.get("orderby")) != "entry_date ASC"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} snowflake SQL changed: {sql_input!r}")
    # 3. the upsert target + the literal-string 'true' loaded value,
    upsert_input = nodes[UPSERT_AS].get("input") or {}
    if (
        str(upsert_input.get("table_id")) != DB_TABLE_ID
        or str(upsert_input.get("primary_field_id")) != PRIMARY_FIELD_ID
        or (upsert_input.get("parameters") or {}).get(FIELD_LOADED) != "true"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} upsert target changed: {upsert_input!r}")
    # 4. the IF keys on document.data.runStatus equals_to Success,
    if_nodes = [node for node in _walk_nodes(raw) if node.get("keyword") == "if"]
    conditions = (if_nodes[0].get("input") or {}).get("conditions") or [] if if_nodes else []
    if (
        len(if_nodes) != 1
        or len(conditions) != 1
        or str(conditions[0].get("operand")) != "equals_to"
        or str(conditions[0].get("rhs")) != "Success"
        or '"runStatus"' not in str(conditions[0].get("lhs"))
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} IF condition changed: {conditions!r}")
    # 5. the unconditional trailing non-error stop.
    stop = nodes[STOP_AS]
    if str((stop.get("input") or {}).get("stop_with_error")) != "false":
        raise RuntimeError(f"recipe {RECIPE_ID} stop node changed")
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
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


def seed_121967119(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_121967119(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    run_status = _require_trigger_shape(trigger)
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no try/catch: a forced action error would fail the "
            f"whole run instead of exercising a recipe branch"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["snowflake_live", "workato_db_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the snowflake_live + "
            f"workato_db_table sections: got "
            f"{sorted(seed_in.keys()) if isinstance(seed_in, dict) else seed_in!r}"
        )
    _require_db_section(seed_in["workato_db_table"])
    _require_snowflake_section(seed_in["snowflake_live"])
    _require_expect_shape(data.get("expect"), run_status, seed_in)
    provision = ctx.tools.call(
        "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": deepcopy(data["expect"]),
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_121967119(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_121967119(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live section")
    db_section = seed.get("workato_db_table")
    if not isinstance(db_section, dict) or db_section.get("honor_order_and_limit") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed file must carry workato_db_table."
            f"honor_order_and_limit: true (without it the engine drops the node's "
            f"order/limit and silently returns the WRONG record)"
        )
    _require_trigger_shape(seed.get("trigger") or {})
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    raw_execution: dict[str, Any] | None = None
    snowflake_cleanup: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = _snapshot(ctx)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx)
    finally:
        # The seeded flows_snapshot table is benchmark-owned create-or-replace
        # live state: drop it even when execution fails (cleanup principle).
        # The mock table is per-variant seeded state re-materialized from
        # seed.json on every run -- no cleanup needed.
        snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    details["cleanup_response"] = {"snowflake_live": snowflake_cleanup}
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_121967119(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> str:
    if sorted(trigger.keys()) != ["payload"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'payload': '<raw json "
            f"string>'}} (webhook_type rawdatatxt): got {sorted(trigger.keys())}"
        )
    payload = trigger["payload"]
    if not isinstance(payload, str) or not payload.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} payload must be a NON-EMPTY RAW JSON STRING -- a "
            f"schema-shaped object would be unfaithful to rawdatatxt: {type(payload)}"
        )
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"recipe {RECIPE_ID} payload must parse as JSON: {exc}") from exc
    if not isinstance(document, dict) or not isinstance(document.get("data"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} payload document must carry a data object")
    run_status = document["data"].get("runStatus")
    if not isinstance(run_status, str) or not run_status:
        raise RuntimeError(
            f"recipe {RECIPE_ID} payload data.runStatus must be a non-empty string (the "
            f"IF dereferences it): {run_status!r}"
        )
    return run_status


def _require_db_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["honor_order_and_limit", "tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table must be exactly "
            f"{{'honor_order_and_limit': true, 'tables': ...}} (the opt-in flag is the "
            f"whole point of this recipe's order/limit semantics)"
        )
    if section["honor_order_and_limit"] is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} honor_order_and_limit must be exactly true"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [DB_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table.tables must declare exactly table "
            f"{DB_TABLE_ID!r}"
        )
    rows = tables[DB_TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"recipe {RECIPE_ID} table {DB_TABLE_ID} rows must be non-empty")
    dates: list[str] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted([FIELD_ENTRY_DATE, FIELD_LOADED]):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} must carry exactly entry_date + "
                f"loaded: {row!r}"
            )
        if not isinstance(row[FIELD_ENTRY_DATE], str) or not _DATE_RE.match(row[FIELD_ENTRY_DATE]):
            raise RuntimeError(
                f"recipe {RECIPE_ID} entry_date must be yyyy-mm-dd (lexicographic order "
                f"== date order for the honored sort): {row!r}"
            )
        if not isinstance(row[FIELD_LOADED], bool):
            raise RuntimeError(
                f"recipe {RECIPE_ID} seeded loaded must be a JSON boolean (the recipe "
                f"WRITES the literal string 'true'; seeds pin the boolean form): {row!r}"
            )
        dates.append(row[FIELD_ENTRY_DATE])
    if len(set(dates)) != len(dates):
        raise RuntimeError(
            f"recipe {RECIPE_ID} entry_date values must be unique (upsert primary key)"
        )


def _require_snowflake_section(section: Any) -> None:
    if not isinstance(section, dict) or not isinstance(section.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.snowflake_live.tables")
    unexpected = sorted(set(section.keys()) - {"tables"})
    if unexpected:
        raise RuntimeError(
            f"recipe {RECIPE_ID} snowflake_live has unexpected keys: {unexpected} "
            f"(the SQL never uses current date/time, so current_time must not be seeded)"
        )
    if sorted(section["tables"]) != [SNOW_TABLE]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{SNOW_TABLE!r}"
        )
    spec = section["tables"][SNOW_TABLE]
    if not isinstance(spec, dict) or spec.get("columns") != SNOW_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} {SNOW_TABLE} columns must be exactly {SNOW_COLUMNS} "
            f"(DATE renders bare isoformat)"
        )
    rows = spec.get("rows")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"recipe {RECIPE_ID} {SNOW_TABLE} rows must be non-empty")
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"ENTRY_DATE"}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} every {SNOW_TABLE} row carries exactly ENTRY_DATE: {row!r}"
            )
        if not _DATE_RE.match(str(row["ENTRY_DATE"])):
            raise RuntimeError(
                f"recipe {RECIPE_ID} ENTRY_DATE must be yyyy-mm-dd: {row!r}"
            )


def _require_expect_shape(expect: Any, run_status: str, seed_in: dict[str, Any]) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS) - set(OPTIONAL_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    branch = expect.get("branch")
    if branch not in BRANCHES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch must be one of {BRANCHES}")
    if expect.get("run_status") != run_status:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.run_status must pin the payload's data.runStatus: "
            f"{expect.get('run_status')!r} != {run_status!r}"
        )
    if (branch == "not_success") != (run_status != "Success"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} branch {branch!r} contradicts runStatus {run_status!r}"
        )
    mock_rows = seed_in["workato_db_table"]["tables"][DB_TABLE_ID]
    seeded_table_rows = [
        {"_row_id": idx, "_created_by": "seed", **deepcopy(row)}
        for idx, row in enumerate(mock_rows)
    ]
    if branch == "not_success":
        checks = (
            expect.get("executed_action_count") == 1,
            expect.get("tools") == [],
            expect.get("tool_expectations") == [],
            expect.get("latest_loaded_entry_date") is None,
            expect.get("sql_dates") is None,
            expect.get("upsert_records") == [],
            expect.get("upsert_created") == [],
            expect.get("initial_table_rows") == seeded_table_rows,
            expect.get("final_table_rows") == seeded_table_rows,
        )
        if not all(checks):
            raise RuntimeError(f"recipe {RECIPE_ID} not_success expect block is incoherent: {expect!r}")
        _require_final_table_alias(expect, seeded_table_rows)
        return
    loaded_dates = sorted(
        row[FIELD_ENTRY_DATE] for row in mock_rows if row[FIELD_LOADED] is True
    )
    if len(loaded_dates) < 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} Success branches must seed AT LEAST TWO loaded rows -- a "
            f"single-loaded-row seed would mask the order/limit semantics this recipe "
            f"exists to pin"
        )
    latest = loaded_dates[-1]
    if not any(
        row[FIELD_LOADED] is False and row[FIELD_ENTRY_DATE] > latest for row in mock_rows
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} Success branches must seed an UNLOADED decoy row dated "
            f"AFTER the latest loaded row (a broken loaded-filter would surface it as "
            f"the 'latest' date)"
        )
    if expect.get("latest_loaded_entry_date") != latest:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.latest_loaded_entry_date must equal the seeded "
            f"latest loaded date ({latest!r}): {expect.get('latest_loaded_entry_date')!r}"
        )
    snow_dates = [
        str(row["ENTRY_DATE"])
        for row in seed_in["snowflake_live"]["tables"][SNOW_TABLE]["rows"]
    ]
    expected_sql_dates = sorted({date for date in snow_dates if date > latest})
    if expect.get("sql_dates") != expected_sql_dates:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.sql_dates must equal the deduped ASC-ordered "
            f"snowflake dates > latest loaded ({expected_sql_dates!r}): "
            f"{expect.get('sql_dates')!r}"
        )
    if (branch == "success_no_new_dates") != (len(expected_sql_dates) == 0):
        raise RuntimeError(
            f"recipe {RECIPE_ID} branch {branch!r} contradicts sql_dates "
            f"{expected_sql_dates!r}"
        )
    if branch == "success_upserts" and not any(date <= latest for date in snow_dates):
        raise RuntimeError(
            f"recipe {RECIPE_ID} success_upserts must seed at least one snowflake date "
            f"<= latest loaded (the > filter must be observable)"
        )
    records = expect.get("upsert_records")
    created = expect.get("upsert_created")
    if (
        not isinstance(records, list)
        or not isinstance(created, list)
        or len(records) != len(expected_sql_dates)
        or len(created) != len(expected_sql_dates)
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} one upsert per SQL date: {expected_sql_dates!r} vs "
            f"{len(records) if isinstance(records, list) else records!r}"
        )
    existing_dates = {row[FIELD_ENTRY_DATE] for row in mock_rows}
    for date, record, flag in zip(expected_sql_dates, records, created):
        if record != {FIELD_ENTRY_DATE: date, FIELD_LOADED: "true"}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} upsert record for {date!r} must be exactly "
                f"{{entry_date: date, loaded: 'true' (LITERAL STRING)}}: {record!r}"
            )
        if flag is not (date not in existing_dates):
            raise RuntimeError(
                f"recipe {RECIPE_ID} created flag for {date!r} contradicts the seeded "
                f"table (existing entry_date -> update created:false)"
            )
    expected_tools = (
        ["workato_db_table.get_records", "snowflake.search_rows_sql"]
        + ["workato_db_table.upsert_record"] * len(expected_sql_dates)
    )
    checks = (
        expect.get("executed_action_count") == 3 + len(expected_sql_dates),
        expect.get("tools") == expected_tools,
        isinstance(expect.get("tool_expectations"), list)
        and len(expect["tool_expectations"]) == len(expected_tools),
        isinstance(expect.get("initial_table_rows"), list),
        isinstance(expect.get("final_table_rows"), list),
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with branch {branch!r}: {expect!r}"
        )
    if "final_table" in expect:
        derived_final_rows = deepcopy(seeded_table_rows)
        row_by_date = {row[FIELD_ENTRY_DATE]: row for row in derived_final_rows}
        for date in expected_sql_dates:
            if date in row_by_date:
                row_by_date[date][FIELD_LOADED] = "true"
                row_by_date[date]["_modified_by"] = "agent"
            else:
                added = {
                    "_row_id": len(derived_final_rows),
                    "_created_by": "agent",
                    FIELD_ENTRY_DATE: date,
                    FIELD_LOADED: "true",
                }
                derived_final_rows.append(added)
                row_by_date[date] = added
        if expect.get("final_table_rows") != derived_final_rows:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.final_table_rows contradicts the derived "
                f"ground truth: {expect.get('final_table_rows')!r}"
            )
        _require_final_table_alias(expect, derived_final_rows)


def _require_final_table_alias(
    expect: dict[str, Any], derived_final_rows: list[dict[str, Any]]
) -> None:
    if "final_table" not in expect:
        return
    expected = {
        "backend": "workato_db_table",
        "table_id": DB_TABLE_ID,
        "row_count": len(derived_final_rows),
        "rows": derived_final_rows,
    }
    if expect.get("final_table") != expected:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_table must be the canonical exact alias "
            f"of the derived table state: {expected!r}"
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
    merged: dict[str, Any] = {}
    for key, value in ctx.tools.call("harness.workato_db_table.snapshot", {}).items():
        if key != "ok":
            merged[key] = value
    for key, value in ctx.tools.call("harness.snowflake.snapshot", {}).items():
        if key != "ok":
            merged[key] = value
    return merged


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
