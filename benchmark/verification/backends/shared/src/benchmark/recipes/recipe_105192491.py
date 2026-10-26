from __future__ import annotations

import datetime
import json
import re
import zoneinfo
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_105192491


RECIPE_ID = "105192491"
SEED_TYPE = "snowflake_lut_stats_db_table_snapshot_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "e495d305"
SQL_STEP_AS = "b9f9415a"
FOREACH_STEP_AS = "1b368bb3"
ADD_STEP_AS = "1f3cbcf0"
DB_TABLE_ID = "13575"
LUT_ID_COL = "4a457f1d_c2cf_46a8_95b5_caf1f3a9a5fd"
TOTAL_ROWS_COL = "7807484b_2fef_41c1_9503_35b19e83ad63"
DATE_COL = "832eca21_0db3_43c7_a29a_2089c6f0e52c"
LUT_NAME_COL = "f02aaacd_f104_4a8c_9d7e_836e981e3a2d"
RECORD_ID_COL = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
SNAPSHOT_TZ = "Asia/Singapore"
ENTRIES_TABLE = "workato_usage.lookup_table_entries"
LUTS_TABLE = "workato_usage.lookup_tables"
WORKSPACE_TABLE = "workato_usage.workspace_dim"
ACCOUNTS_TABLE = "workato_usage.accounts_dim"
LINE_STATS_TABLE = "workato_usage.line_stats"
RECIPE_DIM_TABLE = "workato_usage.recipe_dim"
SEED_TABLES = (
    ENTRIES_TABLE,
    LUTS_TABLE,
    WORKSPACE_TABLE,
    ACCOUNTS_TABLE,
    LINE_STATS_TABLE,
    RECIPE_DIM_TABLE,
)
TABLE_COLUMNS: dict[str, dict[str, str]] = {
    ENTRIES_TABLE: {
        "lookup_table_id": "string",
        "data_center": "string",
        "data_size_bytes": "integer",
    },
    LUTS_TABLE: {
        "id": "string",
        "name": "string",
        "data_center": "string",
        "user_id": "string",
    },
    WORKSPACE_TABLE: {
        "workspace_id": "string",
        "data_center": "string",
        "workspace_name": "string",
        "environment": "string",
        "is_latest": "boolean",
        "sales_account_id": "string",
    },
    ACCOUNTS_TABLE: {
        "account_id": "string",
        "account_name": "string",
        "owner": "string",
        "success_owner": "string",
        "is_latest": "boolean",
    },
    LINE_STATS_TABLE: {
        "object_name": "string",
        "data_center": "string",
        "flow_id": "string",
    },
    RECIPE_DIM_TABLE: {
        "flow_id": "string",
        "data_center": "string",
        "is_latest": "boolean",
    },
}


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "clock", "name": "scheduled_event", "as": "e495d305", "skip": false, "input": {"days_of_month": "3", "time_unit": "months", "timezone": "Asia/Singapore", "trigger_at": "10:00:00", "trigger_every": "1"}, "block": [{"number": 2, "keyword": "action", "provider": "snowflake", "name": "search_rows_sql", "as": "b9f9415a", "skip": false, "input": {"limit": "100", "offset": "0", "sql": "WITH distinct_lookup_table_entries AS (SELECT distinct *\nFROM\n    workato_usage.lookup_table_entries),\nlut_stats AS (SELECT distinct\n    wd.data_center,\n    wd.workspace_id,\n    wd.workspace_name,\n    wd.environment,\n    ad.account_name,\n    ad.owner,\n    ad.success_owner,\n    lt.id,\n    lt.name as lut_name,\n    COUNT(lte.*) AS total_rows,\n    SUM(lte.data_size_bytes) AS total_rows_size,\n    MIN(lte.data_size_bytes) AS min_row_size,\n    MAX(lte.data_size_bytes) AS max_row_size,\n    AVG(lte.data_size_bytes) AS avg_row_size,\n    approx_percentile(lte.data_size_bytes,0.90) AS p90_row_size,\n    approx_percentile(lte.data_size_bytes,0.95) AS p95_row_size,\n    approx_percentile(lte.data_size_bytes,0.99) AS p99_row_size,\n    approx_percentile(lte.data_size_bytes,0.999) AS p999_row_size\nFROM\n    distinct_lookup_table_entries lte\nJOIN\n    workato_usage.lookup_tables lt ON lte.lookup_table_id = lt.id AND lte.data_center = lt.data_center\nJOIN\n    workato_usage.workspace_dim wd ON lt.user_id = wd.workspace_id AND lt.data_center = wd.data_center AND wd.is_latest = true\nJOIN\n    workato_usage.accounts_dim ad ON wd.sales_account_id = ad.account_id AND wd.is_latest = true AND ad.is_latest = true\nGROUP BY\n    1,2,3,4,5,6,7,8,9),\nlut_analysis AS (SELECT distinct\n    lt.data_center,\n    lt.workspace_id,\n    lt.workspace_name,\n    lt.environment,\n    lt.account_name,\n    lt.owner,\n    lt.success_owner,\n    -- rd.flow_id,\n    -- rd.name,\n    -- ls.operation,\n    lt.id as lut_id,\n    lt.lut_name,\n    lt.total_rows,\n    lt.total_rows_size,\n    lt.min_row_size,\n    lt.max_row_size,\n    lt.avg_row_size,\n    lt.p90_row_size,\n    lt.p95_row_size,\n    lt.p99_row_size,\n    lt.p999_row_size\nFROM lut_stats lt\nJOIN workato_usage.line_stats ls ON lt.id = ls.object_name AND lt.data_center = ls.data_center\nJOIN workato_usage.recipe_dim rd ON ls.flow_id = rd.flow_id AND ls.data_center = rd.data_center AND rd.is_latest = true\n-- AND rd.running = true\nWHERE lt.total_rows_size IS NOT null\n-- AND lt.total_rows >= 100000\nORDER BY lt.total_rows_size DESC)\n\nSELECT distinct lut_id, lut_name, total_rows FROM lut_analysis WHERE data_center = 'US' AND lut_id IN ('3663505','3188000','114607','278133','239210','3187998','312866','2363713','3627461','19437','3298516','2542966','3563156','3563155','3563154','3563157','2911972','146681','99451','3181579','3208018','330929','289929','139303','3169955','330930','233339','3187428','1474637','95384','2908554','34113','3245680','3240614','3522947','332453','3444464','3444798','223431','91784','47351','3641584','56357','3302666','2577817','246128','3451094','3421744','278869','43559','2901015','1974840','3040242','3199278','3669276','3168773','116792','75203','149942','40533','231376','221329','153997','3187999','218573','275102','110122','278870','106237','71865','3586444','3589197','3697949','3593992','2447996','3021377','111215','37163','218057','3430717','98311','3642343','3609641','3257930','363977','3556330','61486','2295552','330986','3667035','106269','3253274','3464519','105579','3250368','2016515','3250436','2311958','278157','3301087')"}, "block": []}, {"number": 3, "keyword": "foreach", "provider": "", "name": "", "as": "1b368bb3", "skip": false, "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"b9f9415a\",\"path\":[\"rows\"]}')}"}, "repeat_mode": "simple", "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"b9f9415a\",\"path\":[\"rows\"]}')}", "block": [{"number": 4, "keyword": "action", "provider": "workato_db_table", "name": "add_record", "as": "1f3cbcf0", "skip": false, "input": {"parameters": {"4a457f1d_c2cf_46a8_95b5_caf1f3a9a5fd": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"1b368bb3\",\"path\":[\"lut_id\"]}')}", "7807484b_2fef_41c1_9503_35b19e83ad63": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"1b368bb3\",\"path\":[\"total_rows\"]}')}", "832eca21_0db3_43c7_a29a_2089c6f0e52c": "=_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_created_at\"]}').in_time_zone(\"Asia/Singapore\").to_date", "f02aaacd_f104_4a8c_9d7e_836e981e3a2d": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"1b368bb3\",\"path\":[\"lut_name\"]}')}"}, "table_id": "13575"}, "block": []}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

RAW_SQL = str(
    ((_EXPECTED_TREE.get("block") or [{}])[0].get("input") or {}).get("sql") or ""
)
_IN_LIST_MATCH = re.search(r"lut_id IN \(([^)]*)\)", RAW_SQL)
IN_LIST_IDS = frozenset(re.findall(r"'([^']+)'", _IN_LIST_MATCH.group(1) if _IN_LIST_MATCH else ""))

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (SQL_STEP_AS, "snowflake", "search_rows_sql"),
    (ADD_STEP_AS, "workato_db_table", "add_record"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_db_table.add_record",
]
ALLOWED_TOOLS: list[str] = list(EXPECTED_RAW_TOOLS)
BRANCHES = ("no_rows", "rows")
REQUIRED_EXPECT_KEYS = (
    "branch",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "snapshot_date",
    "sql_row_count",
    "sql_rows",
    "added_records",
    "final_row_count",
    "final_table_rows",
)
_EXPECTATION_TARGET_KEYS = {"tool", "table_id", "lookup_table_id", "match_fields", "channel"}
_EXPECTATION_VALUE_KEYS = {
    "args_contains",
    "result_count",
    "response_contains",
    "result_contains",
    "created",
    "http_status_code",
    "text_fragments",
    "options_contains",
}


def validate_105192491(raw: dict[str, Any]) -> dict[str, Any]:
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
    # Semantic pins on the drift-prone pieces (the tree pin holds the bytes).
    if len(IN_LIST_IDS) != 100:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expected the 100-id lut_id IN list; parsed "
            f"{len(IN_LIST_IDS)} ids"
        )
    for table in SEED_TABLES:
        if table not in RAW_SQL:
            raise RuntimeError(f"recipe {RECIPE_ID} SQL no longer references {table}")
    if re.search(r"\blimit\b", RAW_SQL, flags=re.I):
        raise RuntimeError(
            f"recipe {RECIPE_ID} SQL grew a 'limit' token -- the connector limit-append "
            "analysis no longer holds"
        )
    if re.search(r"\bcurrent_(?:date|timestamp)\b|\bsysdate\b", RAW_SQL, flags=re.I):
        raise RuntimeError(
            f"recipe {RECIPE_ID} SQL grew a CURRENT_* reference -- current_time seeding "
            "analysis no longer holds"
        )
    nodes = {str(node.get("as") or ""): node for node in _walk_nodes(raw)}
    foreach_node = nodes.get(FOREACH_STEP_AS) or {}
    if foreach_node.get("keyword") != "foreach" or foreach_node.get("repeat_mode") != "simple":
        raise RuntimeError(f"recipe {RECIPE_ID} foreach step changed")
    if SQL_STEP_AS not in str(foreach_node.get("source") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} foreach no longer iterates the SQL rows")
    add_node = nodes.get(ADD_STEP_AS) or {}
    add_input = add_node.get("input") or {}
    if str(add_input.get("table_id") or "") != DB_TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} add_record table changed")
    parameters = add_input.get("parameters") or {}
    if sorted(parameters.keys()) != sorted([LUT_ID_COL, TOTAL_ROWS_COL, DATE_COL, LUT_NAME_COL]):
        raise RuntimeError(f"recipe {RECIPE_ID} add_record uuid parameter keys changed")
    for column, fragment in (
        (LUT_ID_COL, '"lut_id"'),
        (TOTAL_ROWS_COL, '"total_rows"'),
        (LUT_NAME_COL, '"lut_name"'),
    ):
        pill = str(parameters.get(column) or "")
        if fragment not in pill or FOREACH_STEP_AS not in pill:
            raise RuntimeError(
                f"recipe {RECIPE_ID} add_record {column} no longer maps the foreach "
                f"{fragment} pill: {pill!r}"
            )
    date_formula = str(parameters.get(DATE_COL) or "")
    if (
        not date_formula.startswith("=")
        or "job_created_at" not in date_formula
        or f'in_time_zone("{SNAPSHOT_TZ}")' not in date_formula
        or not date_formula.endswith(".to_date")
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} snapshot-date formula changed: {date_formula!r}"
        )
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "db_table_id": DB_TABLE_ID,
        "seed_tables": list(SEED_TABLES),
        "in_list_size": len(IN_LIST_IDS),
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


def seed_105192491(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_105192491(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (payload-less scheduler "
            f"tick; no trigger field is ever dereferenced): {trigger!r}"
        )
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: a forced action error would fail the whole "
            "run instead of exercising a recipe branch"
        )
    job_context = data.get("job_context")
    if not isinstance(job_context, dict) or sorted(job_context.keys()) != ["job_created_at"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} every variant must pin job_context with exactly "
            f"job_created_at (the add_record date formula reads it): {job_context!r}"
        )
    snapshot_date = _snapshot_date(str(job_context["job_created_at"]))
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["snowflake_live", "workato_db_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the snowflake_live and "
            f"workato_db_table sections; got {sorted(seed_in.keys())}"
        )
    preseeded_db_rows = _require_db_table_section(seed_in["workato_db_table"])
    tables = _require_snowflake_section(seed_in["snowflake_live"])
    qualifying = _qualifying_rows(tables)
    _require_expect_shape(data.get("expect"), qualifying, preseeded_db_rows, snapshot_date)
    provision = ctx.tools.call(
        "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    fixture_rows = deepcopy(data["expect"]["sql_rows"])
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "job_context": deepcopy(job_context),
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "expect": deepcopy(data["expect"]),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        # Exact hidden fixture for the imported multi-CTE query.  The local
        # simulator still exposes and verifies every seeded source table, but
        # does not claim to be a general Snowflake CTE engine.
        "_simulated_read_fixtures": [
            {
                "tool": "snowflake.search_rows_sql",
                "args": {
                    "sql": RAW_SQL,
                    "parameters": {},
                    "limit": "100",
                    "offset": "0",
                },
                "result": {
                    "ok": True,
                    "sql": RAW_SQL,
                    "parameters": {},
                    "rows": fixture_rows,
                    "records": deepcopy(fixture_rows),
                    "count": len(fixture_rows),
                    "rows_affected": len(fixture_rows),
                },
            }
        ],
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_105192491(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_105192491(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    if not isinstance(seed.get("job_context"), dict) or not seed["job_context"].get("job_created_at"):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing pinned job_context.job_created_at")
    if seed.get("trigger") != {}:
        raise RuntimeError(f"recipe {RECIPE_ID} seed trigger must be the explicit payload-less {{}}")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect"),
        "job_context": seed.get("job_context"),
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
        # The six seeded workato_usage tables are benchmark-owned live state:
        # drop them even when execution fails. Table 13575 is a per-variant
        # isolated mock -- no live cleanup exists for it.
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
    result["verifier"] = verify_105192491(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _snapshot_date(job_created_at: str) -> str:
    """The pinned groundtruth date: job_created_at converted to
    Asia/Singapore, date part (Workato in_time_zone(...).to_date parity,
    probed on HEAD)."""
    text = job_created_at.replace("Z", "+00:00")
    parsed = datetime.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} job_created_at must carry timezone information: "
            f"{job_created_at!r}"
        )
    return parsed.astimezone(zoneinfo.ZoneInfo(SNAPSHOT_TZ)).date().isoformat()


def _require_db_table_section(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table must be exactly {{'tables': ...}}"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [DB_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table.tables must declare exactly table "
            f"{DB_TABLE_ID!r} (rows may be an explicit empty list)"
        )
    rows = tables[DB_TABLE_ID]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {DB_TABLE_ID} rows must be a list")
    allowed = {RECORD_ID_COL, LUT_ID_COL, TOTAL_ROWS_COL, DATE_COL, LUT_NAME_COL}
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or not row:
            raise RuntimeError(
                f"recipe {RECIPE_ID} pre-seeded db row {idx} must be a non-empty object"
            )
        for key, value in row.items():
            if str(key) not in allowed:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} pre-seeded db row {idx} has a non-schema key {key!r}"
                )
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} pre-seeded db row {idx}.{key} must be a non-empty "
                    f"string (add_record stores strings); got {value!r}"
                )
    return [dict(row) for row in rows]


def _require_snowflake_section(section: Any) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the SQL has no CURRENT_* -> current_time must NOT be declared)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted(SEED_TABLES):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{sorted(SEED_TABLES)} (the LITERAL 2-part names the SQL uses)"
        )
    out: dict[str, list[dict[str, Any]]] = {}
    for table in SEED_TABLES:
        spec = tables[table]
        columns = TABLE_COLUMNS[table]
        if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {table} spec must be exactly {{'columns': ..., 'rows': ...}}"
            )
        if spec["columns"] != columns:
            raise RuntimeError(f"recipe {RECIPE_ID} {table} columns must be exactly {columns}")
        rows = spec["rows"]
        if not isinstance(rows, list):
            raise RuntimeError(f"recipe {RECIPE_ID} {table} rows must be a list")
        for idx, row in enumerate(rows):
            if not isinstance(row, dict) or sorted(row.keys()) != sorted(columns.keys()):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {table} row {idx} must fill exactly the declared "
                    f"columns (COUNT(lte.*) skips null-carrying rows -- keep every column "
                    f"non-null): {row!r}"
                )
            for column, kind in columns.items():
                value = row[column]
                if kind == "boolean":
                    if not isinstance(value, bool):
                        raise RuntimeError(
                            f"recipe {RECIPE_ID} {table} row {idx}.{column} must be a "
                            f"boolean; got {value!r}"
                        )
                elif kind == "integer":
                    if not isinstance(value, int) or isinstance(value, bool):
                        raise RuntimeError(
                            f"recipe {RECIPE_ID} {table} row {idx}.{column} must be an "
                            f"int; got {value!r}"
                        )
                else:
                    if not isinstance(value, str) or not value.strip():
                        raise RuntimeError(
                            f"recipe {RECIPE_ID} {table} row {idx}.{column} must be a "
                            f"non-empty string; got {value!r}"
                        )
        out[table] = [dict(row) for row in rows]
    return out


def _qualifying_rows(tables: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Re-derive the final SELECT from the seeded tables (faithful CTE walk):
    distinct entries -> inner joins lut/workspace(is_latest)/account(is_latest)
    grouped per (dc, workspace fields, account fields, lut id, lut name) with
    COUNT -> inner joins line_stats/recipe_dim(is_latest) -> final DISTINCT
    (lut_id, lut_name, total_rows) WHERE data_center='US' AND lut_id IN
    (the 100-id list). Order-insensitive (no top-level ORDER BY)."""
    entries = [
        json.loads(text)
        for text in sorted(
            {
                json.dumps(
                    {
                        "lookup_table_id": str(row["lookup_table_id"]),
                        "data_center": str(row["data_center"]),
                        "data_size_bytes": int(row["data_size_bytes"]),
                    },
                    sort_keys=True,
                )
                for row in tables[ENTRIES_TABLE]
            }
        )
    ]
    stats: dict[tuple[str, ...], dict[str, Any]] = {}
    for lut in tables[LUTS_TABLE]:
        matching_entries = [
            entry
            for entry in entries
            if entry["lookup_table_id"] == str(lut["id"])
            and entry["data_center"] == str(lut["data_center"])
        ]
        workspaces = [
            wd
            for wd in tables[WORKSPACE_TABLE]
            if str(wd["workspace_id"]) == str(lut["user_id"])
            and str(wd["data_center"]) == str(lut["data_center"])
            and wd["is_latest"] is True
        ]
        for entry in matching_entries:
            for wd in workspaces:
                accounts = [
                    ad
                    for ad in tables[ACCOUNTS_TABLE]
                    if str(ad["account_id"]) == str(wd["sales_account_id"])
                    and ad["is_latest"] is True
                ]
                for ad in accounts:
                    key = (
                        str(wd["data_center"]),
                        str(wd["workspace_id"]),
                        str(wd["workspace_name"]),
                        str(wd["environment"]),
                        str(ad["account_name"]),
                        str(ad["owner"]),
                        str(ad["success_owner"]),
                        str(lut["id"]),
                        str(lut["name"]),
                    )
                    group = stats.setdefault(
                        key, {"total_rows": 0, "total_rows_size": 0}
                    )
                    group["total_rows"] += 1
                    group["total_rows_size"] += int(entry["data_size_bytes"])
    final: set[tuple[str, str, int]] = set()
    for key, group in stats.items():
        data_center, lut_id, lut_name = key[0], key[7], key[8]
        # WHERE lt.total_rows_size IS NOT null: SUM over >=1 non-null values is
        # never null, and a lut with zero entries has no group at all.
        has_line_stats_partner = any(
            str(ls["object_name"]) == lut_id
            and str(ls["data_center"]) == data_center
            and any(
                str(rd["flow_id"]) == str(ls["flow_id"])
                and str(rd["data_center"]) == data_center
                and rd["is_latest"] is True
                for rd in tables[RECIPE_DIM_TABLE]
            )
            for ls in tables[LINE_STATS_TABLE]
        )
        if not has_line_stats_partner:
            continue
        if data_center != "US" or lut_id not in IN_LIST_IDS:
            continue
        final.add((lut_id, lut_name, int(group["total_rows"])))
    return [
        {"lut_id": lut_id, "lut_name": lut_name, "total_rows": total_rows}
        for lut_id, lut_name, total_rows in sorted(final)
    ]


def _added_record_for(row: dict[str, Any], snapshot_date: str) -> dict[str, Any]:
    """The add_record args for one qualifying SELECT row: uuid keys, native
    types (total_rows stays the live COUNT integer in the trace args; the
    mock str()-ifies it in the stored row)."""
    return {
        LUT_ID_COL: str(row["lut_id"]),
        TOTAL_ROWS_COL: int(row["total_rows"]),
        DATE_COL: snapshot_date,
        LUT_NAME_COL: str(row["lut_name"]),
    }


def _stored_record_for(row: dict[str, Any], snapshot_date: str) -> dict[str, str]:
    return {key: str(value) for key, value in _added_record_for(row, snapshot_date).items()}


def _same_multiset(actual: Any, expected: list[dict[str, Any]]) -> bool:
    if not isinstance(actual, list) or len(actual) != len(expected):
        return False
    key = lambda entry: json.dumps(entry, sort_keys=True, default=str)
    actual_sorted = sorted((entry for entry in actual if isinstance(entry, dict)), key=key)
    expected_sorted = sorted(expected, key=key)
    return actual_sorted == expected_sorted


def _require_expect_shape(
    expect: Any,
    qualifying: list[dict[str, Any]],
    preseeded_db_rows: list[dict[str, Any]],
    snapshot_date: str,
) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    branch = expect.get("branch")
    if branch not in BRANCHES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch must be one of {BRANCHES}")
    derived_branch = "no_rows" if not qualifying else "rows"
    if branch != derived_branch:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.branch {branch!r} contradicts the seeded tables "
            f"(derived {derived_branch!r}: {len(qualifying)} qualifying rows)"
        )
    lut_ids = [row["lut_id"] for row in qualifying]
    if len(set(lut_ids)) != len(lut_ids):
        raise RuntimeError(
            f"recipe {RECIPE_ID} QUALIFYING rows must carry distinct lut_id values "
            "(SELECT order is not guaranteed without ORDER BY; groundtruth matching "
            "is keyed on lut_id)"
        )
    expected_adds = [_added_record_for(row, snapshot_date) for row in qualifying]
    expected_final = [
        {key: str(value) for key, value in row.items()} for row in preseeded_db_rows
    ] + [_stored_record_for(row, snapshot_date) for row in qualifying]
    checks = (
        expect.get("executed_action_count") == 1 + len(qualifying),
        expect.get("tools")
        == ["snowflake.search_rows_sql"] + ["workato_db_table.add_record"] * len(qualifying),
        expect.get("snapshot_date") == snapshot_date,
        expect.get("sql_row_count") == len(qualifying),
        _same_multiset(expect.get("sql_rows"), qualifying),
        _same_multiset(expect.get("added_records"), expected_adds),
        expect.get("final_row_count") == len(expected_final),
        _same_multiset(expect.get("final_table_rows"), expected_final),
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with the seeded ground truth "
            f"(branch {branch!r}, {len(qualifying)} qualifying rows, snapshot_date "
            f"{snapshot_date!r}): {expect!r}"
        )
    _require_tool_expectations(expect, len(qualifying))


def _require_tool_expectations(expect: dict[str, Any], row_count: int) -> None:
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or len(items) != 1 + row_count:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin the SQL call plus "
            f"every add_record call ({1 + row_count} items)"
        )
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[{idx}] must be an object")
        unknown = sorted(set(item) - _EXPECTATION_TARGET_KEYS - _EXPECTATION_VALUE_KEYS)
        if unknown:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] has non-corpus keys: {unknown}"
            )
        if not any(key in item for key in _EXPECTATION_VALUE_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] pins no ground-truth value"
            )
    sql_item = items[0]
    if sql_item.get("tool") != "snowflake.search_rows_sql":
        raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[0] must pin the SQL step")
    if sql_item.get("args_contains") != {
        "sql": RAW_SQL,
        "parameters": {},
        "limit": "100",
        "offset": "0",
    } or sql_item.get("result_count") != row_count:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0] must pin the verbatim SQL args and "
            f"the derived row count {row_count}"
        )
    for idx, item in enumerate(items[1:], start=1):
        # add_record CALL ORDER is live SELECT order (not guaranteed): the
        # per-call items pin only the target table (match_fields stays the
        # default full-record match -- distinct lut_ids keep it unambiguous);
        # the exact record multiset is pinned via expect.added_records in the
        # verifier fragment.
        if (
            item.get("tool") != "workato_db_table.add_record"
            or item.get("table_id") != DB_TABLE_ID
            or item.get("args_contains") != {"table_id": DB_TABLE_ID}
            or "match_fields" in item
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] must pin the add_record "
                f"target table {DB_TABLE_ID!r} (and no custom match_fields)"
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
    out: dict[str, Any] = {}
    out.update(ctx.tools.call("harness.workato_db_table.snapshot", {}))
    out.update(ctx.tools.call("harness.snowflake.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
