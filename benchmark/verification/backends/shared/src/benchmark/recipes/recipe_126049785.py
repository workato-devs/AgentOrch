from __future__ import annotations

import datetime
import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_126049785


RECIPE_ID = "126049785"
SEED_TYPE = "snowflake_chi_first_connections_ctas_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "2511c130"
DECLARE_STEP_AS = "a2d14c5e"
SQL_STEP_AS = "920ebe3a"
DEAD_ASYNC_STEP_AS = "495e1405"
RETURN_STEP_AS = "48439cd5"
WINDOW_START = "2024-02-01"
SNAP_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\","
    "\"line\":\"a2d14c5e\",\"path\":[\"snap_date\"]}')}"
)
ACCOUNTS_TABLE = "workato_usage.accounts_dim"
SHARED_TABLE = "workato_usage.shared_accounts_snapshot"
APPS_TABLE = "workato_usage.applications_snapshot"
CALENDAR_TABLE = "workato_usage.calendar_dim"
WORKSPACE_TABLE = "workato_usage.workspace_dim"
TIER_TABLE = "plg.recipe_sophistication_app_tier"
TARGET_TABLE = "plg.chi_2024_first_connections_operational"
SEED_TABLES = (
    ACCOUNTS_TABLE,
    SHARED_TABLE,
    APPS_TABLE,
    CALENDAR_TABLE,
    WORKSPACE_TABLE,
    TIER_TABLE,
    TARGET_TABLE,
)
TABLE_COLUMNS: dict[str, dict[str, str]] = {
    ACCOUNTS_TABLE: {
        "account_id": "string",
        "account_name": "string",
        "subscription_start_date": "date",
        "startdate": "date",
        "is_paying": "boolean",
        "is_direct": "boolean",
    },
    SHARED_TABLE: {
        "id": "string",
        "data_center": "string",
        "user_id": "string",
        "provider": "string",
        "authorized_at": "timestamp",
        "authorization_status": "string",
        "created_at": "timestamp",
    },
    APPS_TABLE: {
        "data_center": "string",
        "name": "string",
        "title": "string",
        "category": "string",
        "entry_date": "date",
    },
    CALENDAR_TABLE: {
        "date": "date",
        "year": "integer",
        "week": "integer",
        "dayname": "string",
    },
    WORKSPACE_TABLE: {
        "workspace_id": "string",
        "data_center": "string",
        "sales_account_id": "string",
        "is_latest": "boolean",
        "is_paid_workspace": "boolean",
    },
    TIER_TABLE: {
        "title": "string",
        "category": "string",
        "app_tier": "integer",
    },
}
NULLABLE_COLUMNS = {
    APPS_TABLE: {"category"},
    TIER_TABLE: {"category"},
}
CREATED_SCALAR_COLUMNS = (
    "account_id",
    "account_name",
    "subscription_start_date",
    "connected_after_subscription_start",
    "belonging_week_snapshot_first_connection",
    "n_tier_1_2_app_connected",
    "n_tier_3_4_app_connected",
    "n_tier_5_app_connected",
)
CREATED_LISTAGG_COLUMNS = (
    "tier_1_2_apps_connected",
    "tier_3_4_apps_connected",
    "tier_5_apps_connected",
)


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "workato_recipe_function", "name": "execute", "as": "2511c130", "skip": false, "input": {"result_schema_json": "[{\"name\":\"Result\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Result\"}]"}, "block": [{"number": 2, "keyword": "action", "provider": "workato_variable", "name": "declare_variable", "as": "a2d14c5e", "skip": false, "input": {"variables": {"data": {"days_threshold": "30", "snap_date": "=now.strftime(\"%Y-%m-%d\")"}, "schema": "[{\"name\":\"days_threshold\",\"type\":\"string\",\"optional\":true,\"label\":\"days_threshold\",\"details\":{\"real_name\":\"days_threshold\"},\"control_type\":\"text\"},{\"name\":\"snap_date\",\"type\":\"string\",\"optional\":true,\"label\":\"snap_date\",\"details\":{\"real_name\":\"snap_date\"},\"control_type\":\"text\"}]"}}, "block": []}, {"number": 3, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql", "as": "920ebe3a", "skip": false, "input": {"sql": "create or replace table plg.chi_2024_first_connections_operational as\n\nwith account_data as (\n    select a.*, max(startdate) latest_start_date, row_number() over (partition by account_id order by latest_start_date desc) rn \n    from workato_usage.accounts_dim a\n    where\n        a.startdate >= '<anon>2024-02-01</anon>'\n        and a.startdate <= '#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"a2d14c5e\",\"path\":[\"snap_date\"]}')}'\n        and is_paying = true\n    and is_direct /*we exclude embed because the thresholds are very different*/\n    group by all\n    qualify rn = 1\n)\n\n, first_sha_dates as ( \n/* there will be some situations where the provider for shared account changed. e.g 1092207, 917004, 921790, 976401, 977622, 986193 in US dc. Not sure why that happens \n    we are also only looking at situations where authorization status = success, i.e a successful connection is made. This will not include when a connection is ATTEMPTEd, but only when the connection is SUCCESSFUL.\n*/\nselect id sha_id, data_center, user_id, provider, min(authorized_at) sha_first_auth_at, authorization_status, min(created_at) conn_created_at\nfrom workato_usage.shared_accounts_snapshot\nwhere authorization_status = 'success'\ngroup by all\norder by sha_id\n)\n\n, mapped_first_sha_dates as (\nselect fsd.*, coalesce(app.title, fsd.provider) title, app.category\nfrom first_sha_dates fsd\nleft join workato_usage.applications_snapshot app\n    on fsd.data_center = app.data_center and fsd.provider = app.name\n    and app.entry_date = current_date -1\ngroup by all\n)  \n\n, app_first_events as (\nselect data_center, user_id, title, category, date(min(sha_first_auth_at)) app_first_connected_date, date(min(conn_created_at)) app_first_creation_date\nfrom mapped_first_sha_dates \ngroup by all\n)\n\n, app_interim as (\n    select \n          afe.data_center\n        , afe.user_id\n        , afe.title\n        , afe.category\n        , afe.app_first_connected_date\n        , c2.date belonging_week_snapshot_first_connection\n        , afe.app_first_creation_date\n        , c4.date belonging_week_snapshot_first_creation\n    from app_first_events afe\n    join workato_usage.calendar_dim c1\n        on afe.app_first_connected_date = c1.date\n    join workato_usage.calendar_dim c2\n        on c1.year = c2.year and c1.week = c2.week and c2.dayname = 'Mon'\n    join workato_usage.calendar_dim c3\n        on afe.app_first_creation_date = c3.date\n    join workato_usage.calendar_dim c4\n        on c3.year = c4.year and c3.week = c4.week and c4.dayname = 'Mon'\n    group by all\n)\n\n, app_interim2 as (\n    select w.sales_account_id account_id, ai.*\n    from app_interim ai\n    join workato_usage.workspace_dim w \n        on w.is_latest = true\n        and w.workspace_id = ai.user_id and w.data_center = ai.data_center\n        and w.is_paid_workspace = true\n    group by all\n)\n\n, app_interim3 as (\n    select ai2.account_id, ad.account_name, ad.subscription_start_date, min(belonging_week_snapshot_first_connection) belonging_week_snapshot_first_connection , ai2.title, ai2.category\n        , case when belonging_week_snapshot_first_connection < ad.subscription_start_date then 0 else 1 end connected_after_subscription_start /* connections may happen prior to subscription start as part of trial/poc/go-live */\n    -- , belonging_week_snapshot_first_creation /* we dont add in created connection, but when they successfully connect then its an indication that they're ready and able to do something. */\n        , case when at.category in ('workato', 'others') or at.category is null then 5\n            else coalesce(at.app_tier, 5) end as app_tier\n            \n    from app_interim2 ai2\n    join account_data ad \n        on ai2.account_id = ad.account_id\n    left join plg.recipe_sophistication_app_tier at\n        on ai2.title = at.title\n    where 1=1\n    group by all\n    order by belonging_week_snapshot_first_connection\n)\n, app_interim4 as (\n    select *\n        , rank() over (partition by ai3.account_id, ai3.title order by belonging_week_snapshot_first_connection asc) app_connection_rank\n    from app_interim3 ai3\n)\n\n, app_interim5 as (\n    select account_id, account_name, subscription_start_date, connected_after_subscription_start, belonging_week_snapshot_first_connection\n        , sum(case when ai4.category in ('app', 'custom') and app_tier in (1,2) and app_connection_rank = 1 then 1 else 0 end) n_tier_1_2_app_connected\n        , listagg(case when ai4.category in ('app', 'custom') and app_tier in (1,2) and app_connection_rank = 1 then ai4.title end, ';') tier_1_2_apps_connected\n        \n        , sum(case when ai4.category in ('app', 'custom') and app_tier in (3,4) and app_connection_rank = 1 then 1 else 0 end) n_tier_3_4_app_connected\n        , listagg(case when ai4.category in ('app', 'custom') and app_tier in (3,4) and app_connection_rank = 1 then ai4.title end, ';') tier_3_4_apps_connected\n        \n        , sum(case when app_tier in (5) and app_connection_rank = 1 then 1 else 0 end) n_tier_5_app_connected\n        , listagg(case when app_tier in (5) and app_connection_rank = 1 then ai4.title end, ';') tier_5_apps_connected\n        , \n    from app_interim4 ai4\n    group by all\n    order by belonging_week_snapshot_first_connection\n)\n\nselect * \nfrom app_interim5\n", "update_only": "false"}, "block": []}, {"number": 4, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql_async_v2", "as": "495e1405", "skip": true, "block": []}, {"number": 5, "keyword": "action", "provider": "workato_recipe_function", "name": "return_result", "as": "48439cd5", "skip": false, "input": {"result": {"Result": "success"}}, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

RAW_SQL = str(
    ((_EXPECTED_TREE.get("block") or [{}, {}])[1].get("input") or {}).get("sql") or ""
)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (DECLARE_STEP_AS, "workato_variable", "declare_variable"),
    (SQL_STEP_AS, "snowflake", "run_custom_sql"),
    (RETURN_STEP_AS, "workato_recipe_function", "return_result"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "snowflake.run_custom_sql",
    "workato_recipe_function.return_result",
]
EXPECTED_REGISTRY_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = list(EXPECTED_REGISTRY_TOOLS)
BRANCHES = ("zero_rows", "rows")
REQUIRED_EXPECT_KEYS = (
    "branch",
    "executed_action_count",
    "tools",
    "trace_tools",
    "tool_expectations",
    "snap_date",
    "resolved_sql",
    "declare_result",
    "dead_async_step_skipped",
    "return_value",
    "created_row_count",
    "created_rows",
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
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def validate_126049785(raw: dict[str, Any]) -> dict[str, Any]:
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
    nodes = {str(node.get("as") or ""): node for node in _walk_nodes(raw)}
    declare_data = (
        ((nodes.get(DECLARE_STEP_AS) or {}).get("input") or {}).get("variables") or {}
    ).get("data") or {}
    if declare_data.get("days_threshold") != "30" or declare_data.get("snap_date") != '=now.strftime("%Y-%m-%d")':
        raise RuntimeError(f"recipe {RECIPE_ID} declare_variable data changed: {declare_data!r}")
    if SNAP_PILL not in RAW_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} the snap_date pill vanished from the CTAS SQL")
    if f"'<anon>{WINDOW_START}</anon>'" not in RAW_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} the anonymized startdate window literal changed")
    if not RAW_SQL.startswith(f"create or replace table {TARGET_TABLE} as"):
        raise RuntimeError(f"recipe {RECIPE_ID} the CTAS target changed")
    for table in SEED_TABLES[:-1]:
        if table not in RAW_SQL:
            raise RuntimeError(f"recipe {RECIPE_ID} SQL no longer references {table}")
    if len(re.findall(r"\bcurrent_date\b", RAW_SQL)) != 1 or re.search(
        r"\bcurrent_timestamp\b|\bsysdate\b", RAW_SQL, flags=re.I
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} time-function usage changed (current_date -1 only)")
    dead = nodes.get(DEAD_ASYNC_STEP_AS)
    if not isinstance(dead, dict) or dead.get("skip") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} step {DEAD_ASYNC_STEP_AS} is no longer skip:true -- the "
            "dead-duplicate-CTAS proof does not hold; re-triage before building"
        )
    return_input = (nodes.get(RETURN_STEP_AS) or {}).get("input") or {}
    if return_input.get("result") != {"Result": "success"}:
        raise RuntimeError(f"recipe {RECIPE_ID} return_result literal changed")
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "target_table": TARGET_TABLE,
        "seed_tables": list(SEED_TABLES),
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


def seed_126049785(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_126049785(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (the recipe-function "
            f"trigger declares no parameters schema and no pill is dereferenced): {trigger!r}"
        )
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: a forced action error would fail the whole "
            "run instead of exercising a recipe branch"
        )
    now = data.get("now")
    if not isinstance(now, str) or not now.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} every variant must pin a top-level 'now' "
            "(=now.strftime fails fast without seed.now)"
        )
    snap_date, app_entry_date = _time_pins(now)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the snowflake_live section; "
            f"got {sorted(seed_in.keys())}"
        )
    tables = _require_snowflake_section(seed_in["snowflake_live"], now)
    derived = _derived_created_rows(tables, snap_date, app_entry_date)
    _require_expect_shape(data.get("expect"), derived, snap_date)
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
        "now": now,
        "expect": deepcopy(data["expect"]),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_126049785(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_126049785(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    if not str(seed.get("now") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing pinned now")
    if str((seed.get("snowflake_live") or {}).get("current_time") or "") != str(seed.get("now")):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.now and snowflake_live.current_time diverged -- "
            "snap_date and current_date would disagree"
        )
    if seed.get("trigger") != {}:
        raise RuntimeError(f"recipe {RECIPE_ID} seed trigger must be the explicit payload-less {{}}")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect"),
        "now": seed.get("now"),
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
        # All seven registered tables (five read-only sources, the tier table
        # and the CTAS-created target) are benchmark-owned live state: drop
        # them even when execution fails.
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
    result["verifier"] = verify_126049785(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _time_pins(now: str) -> tuple[str, str]:
    """snap_date = now.strftime('%Y-%m-%d') (Workato parity, probed) and the
    app-join entry date = pinned current_date - 1 day. Both read the SAME
    pinned instant, so `now` must be UTC (the engine pins current_date in
    UTC)."""
    text = now.replace("Z", "+00:00")
    parsed = datetime.datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() != datetime.timedelta(0):
        raise RuntimeError(
            f"recipe {RECIPE_ID} 'now' must be an explicit UTC instant "
            f"(snap_date and the current_date pin must agree): {now!r}"
        )
    snap_date = parsed.strftime("%Y-%m-%d")
    app_entry_date = (parsed.date() - datetime.timedelta(days=1)).isoformat()
    return snap_date, app_entry_date


def _require_snowflake_section(section: Any, now: str) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["current_time", "tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly "
            "{'current_time': ..., 'tables': ...} (current_date -1 needs the pin)"
        )
    if str(section["current_time"]) != now:
        raise RuntimeError(
            f"recipe {RECIPE_ID} snowflake_live.current_time must equal the top-level "
            f"'now' (one pinned instant): {section['current_time']!r} != {now!r}"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted(SEED_TABLES):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{sorted(SEED_TABLES)} (sources + tier + the CTAS target)"
        )
    target_spec = tables[TARGET_TABLE]
    if target_spec != {"columns": {}, "rows": []}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the CTAS target must be registered with empty columns "
            "and rows (the seeder drops any leftover; the recipe creates it): "
            f"{target_spec!r}"
        )
    out: dict[str, list[dict[str, Any]]] = {}
    for table in SEED_TABLES[:-1]:
        spec = tables[table]
        columns = TABLE_COLUMNS[table]
        nullable = NULLABLE_COLUMNS.get(table, set())
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
                    f"columns: {row!r}"
                )
            for column, kind in columns.items():
                value = row[column]
                if value is None:
                    if column in nullable:
                        continue
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} {table} row {idx}.{column} must not be null"
                    )
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
                elif kind == "date":
                    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
                        raise RuntimeError(
                            f"recipe {RECIPE_ID} {table} row {idx}.{column} must be "
                            f"YYYY-MM-DD; got {value!r}"
                        )
                elif kind == "timestamp":
                    if not isinstance(value, str) or not _TS_RE.fullmatch(value):
                        raise RuntimeError(
                            f"recipe {RECIPE_ID} {table} row {idx}.{column} must be "
                            f"'YYYY-MM-DD HH:MM:SS' (lexicographic == chronological for "
                            f"the min() pins); got {value!r}"
                        )
                else:
                    if not isinstance(value, str) or not value.strip():
                        raise RuntimeError(
                            f"recipe {RECIPE_ID} {table} row {idx}.{column} must be a "
                            f"non-empty string; got {value!r}"
                        )
        out[table] = [dict(row) for row in rows]
    for idx, row in enumerate(out[APPS_TABLE]):
        if ";" in str(row.get("title") or ""):
            raise RuntimeError(
                f"recipe {RECIPE_ID} app title {row.get('title')!r} must not contain ';' "
                "(the listagg delimiter; split-based pinning would be ambiguous)"
            )
    for idx, row in enumerate(out[SHARED_TABLE]):
        if ";" in str(row.get("provider") or ""):
            raise RuntimeError(
                f"recipe {RECIPE_ID} provider {row.get('provider')!r} must not contain ';'"
            )
    return out


def _derived_created_rows(
    tables: dict[str, list[dict[str, Any]]],
    snap_date: str,
    app_entry_date: str,
) -> list[dict[str, Any]]:
    """Faithful walk of the 9-CTE CTAS (semantics live-checked per triage;
    the fragment re-derives the same rows from the pre-run snapshot).
    Determinism rules are ENFORCED here (fail-fast) so live evaluation cannot
    silently disagree: <=1 qualifying accounts_dim row per account (rn tie),
    <=1 app-snapshot match per (dc, provider), unique calendar date rows +
    unique Monday per (year, week), <=1 latest+paid workspace per (user, dc),
    <=1 tier row per title, unique (account, title) pairs at the rank stage.
    listagg columns come back as SORTED title lists ('' -> [])."""
    # -- account_data: window + flags, one survivor per account (rn = 1) --
    qualifying_by_account: dict[str, list[dict[str, Any]]] = {}
    for row in tables[ACCOUNTS_TABLE]:
        if (
            str(row["startdate"]) >= WINDOW_START
            and str(row["startdate"]) <= snap_date
            and row["is_paying"] is True
            and row["is_direct"] is True
        ):
            qualifying_by_account.setdefault(str(row["account_id"]), []).append(row)
    account_data: dict[str, dict[str, Any]] = {}
    for account_id, rows in qualifying_by_account.items():
        if len(rows) != 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} account {account_id} has {len(rows)} qualifying "
                "accounts_dim rows -- the rn=1 pick would be a live tie; seed exactly one"
            )
        account_data[account_id] = rows[0]
    # -- first_sha_dates: success-only, min timestamps per shared account --
    sha_groups: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in tables[SHARED_TABLE]:
        if str(row["authorization_status"]) != "success":
            continue
        key = (
            str(row["id"]),
            str(row["data_center"]),
            str(row["user_id"]),
            str(row["provider"]),
        )
        group = sha_groups.setdefault(
            key, {"auth": str(row["authorized_at"]), "created": str(row["created_at"])}
        )
        group["auth"] = min(group["auth"], str(row["authorized_at"]))
        group["created"] = min(group["created"], str(row["created_at"]))
    # -- mapped_first_sha_dates: LEFT JOIN yesterday's application snapshot --
    mapped: list[dict[str, Any]] = []
    for (sha_id, data_center, user_id, provider), group in sha_groups.items():
        apps = [
            app
            for app in tables[APPS_TABLE]
            if str(app["data_center"]) == data_center
            and str(app["name"]) == provider
            and str(app["entry_date"]) == app_entry_date
        ]
        if len(apps) > 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} provider {provider!r} in {data_center} matches "
                f"{len(apps)} application rows at {app_entry_date} -- seed exactly one"
            )
        app = apps[0] if apps else None
        title = str(app["title"]) if app and app.get("title") else provider
        category = app.get("category") if app else None
        mapped.append(
            {
                "data_center": data_center,
                "user_id": user_id,
                "title": title,
                "category": category,
                "auth": group["auth"],
                "created": group["created"],
            }
        )
    # -- app_first_events: min per (dc, user, title, category) --
    events: dict[tuple[str, str, str, Any], dict[str, str]] = {}
    for row in mapped:
        key = (row["data_center"], row["user_id"], row["title"], row["category"])
        event = events.setdefault(key, {"auth": row["auth"], "created": row["created"]})
        event["auth"] = min(event["auth"], row["auth"])
        event["created"] = min(event["created"], row["created"])
    # -- app_interim: Monday-of-week via calendar_dim (INNER joins) --
    calendar = tables[CALENDAR_TABLE]

    def _belonging_monday(day: str, what: str) -> str:
        day_rows = [row for row in calendar if str(row["date"]) == day]
        if len(day_rows) != 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} calendar_dim must carry exactly one row for the "
                f"{what} date {day}; got {len(day_rows)} (an inner-join miss would "
                "silently drop the event live)"
            )
        year, week = day_rows[0]["year"], day_rows[0]["week"]
        mondays = [
            row
            for row in calendar
            if row["year"] == year and row["week"] == week and str(row["dayname"]) == "Mon"
        ]
        if len(mondays) != 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} calendar_dim must carry exactly one Mon row for "
                f"(year {year}, week {week}); got {len(mondays)}"
            )
        return str(mondays[0]["date"])

    interim: list[dict[str, Any]] = []
    for (data_center, user_id, title, category), event in events.items():
        connected_date = event["auth"][:10]
        creation_date = event["created"][:10]
        belonging_conn = _belonging_monday(connected_date, "first-connection")
        _belonging_monday(creation_date, "first-creation")  # inner join must hold
        interim.append(
            {
                "data_center": data_center,
                "user_id": user_id,
                "title": title,
                "category": category,
                "belonging_conn": belonging_conn,
            }
        )
    # -- app_interim2: latest paid workspace -> sales account --
    interim2: list[dict[str, Any]] = []
    for row in interim:
        workspaces = [
            wd
            for wd in tables[WORKSPACE_TABLE]
            if str(wd["workspace_id"]) == row["user_id"]
            and str(wd["data_center"]) == row["data_center"]
            and wd["is_latest"] is True
            and wd["is_paid_workspace"] is True
        ]
        if len(workspaces) > 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} user {row['user_id']!r} matches {len(workspaces)} "
                "latest paid workspaces -- seed exactly one"
            )
        if not workspaces:
            continue
        interim2.append(row | {"account_id": str(workspaces[0]["sales_account_id"])})
    # -- app_interim3: join account_data, tier CASE, connected flag --
    tier_by_title: dict[str, list[dict[str, Any]]] = {}
    for tier in tables[TIER_TABLE]:
        tier_by_title.setdefault(str(tier["title"]), []).append(tier)
    for title, rows in tier_by_title.items():
        if len(rows) > 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tier table carries {len(rows)} rows for title "
                f"{title!r} -- the left join would fan out; seed at most one"
            )
    groups: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in interim2:
        account = account_data.get(row["account_id"])
        if account is None:
            continue
        tier_rows = tier_by_title.get(row["title"]) or []
        tier = tier_rows[0] if tier_rows else None
        at_category = tier.get("category") if tier else None
        if at_category in ("workato", "others") or at_category is None:
            app_tier = 5
        else:
            app_tier = int(tier["app_tier"]) if tier.get("app_tier") is not None else 5
        connected_flag = (
            0 if str(row["belonging_conn"]) < str(account["subscription_start_date"]) else 1
        )
        key = (
            row["account_id"],
            str(account["account_name"]),
            str(account["subscription_start_date"]),
            row["title"],
            row["category"],
            connected_flag,
            app_tier,
        )
        group = groups.setdefault(key, {"belonging": row["belonging_conn"]})
        group["belonging"] = min(group["belonging"], row["belonging_conn"])
    # -- app_interim4: rank per (account, title) must be trivially 1 --
    pair_counts: dict[tuple[str, str], int] = {}
    for key in groups:
        pair = (key[0], key[3])
        pair_counts[pair] = pair_counts.get(pair, 0) + 1
    for pair, count in pair_counts.items():
        if count > 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} (account, title) {pair!r} appears in {count} "
                "app_interim3 groups -- rank>1 rows would make bucket membership "
                "depend on live tie-breaks; seed one group per pair"
            )
    # -- app_interim5: bucket sums + listaggs per output group --
    out_groups: dict[tuple[Any, ...], dict[str, Any]] = {}
    for key, group in groups.items():
        account_id, account_name, sub_date, title, category, connected_flag, app_tier = key
        out_key = (account_id, account_name, sub_date, connected_flag, group["belonging"])
        bucket = out_groups.setdefault(
            out_key,
            {"t12": [], "t34": [], "t5": []},
        )
        app_category = category
        if app_category in ("app", "custom") and app_tier in (1, 2):
            bucket["t12"].append(title)
        if app_category in ("app", "custom") and app_tier in (3, 4):
            bucket["t34"].append(title)
        if app_tier == 5:
            bucket["t5"].append(title)
    rows_out: list[dict[str, Any]] = []
    for (account_id, account_name, sub_date, connected_flag, belonging), bucket in out_groups.items():
        rows_out.append(
            {
                "account_id": account_id,
                "account_name": account_name,
                "subscription_start_date": sub_date,
                "connected_after_subscription_start": connected_flag,
                "belonging_week_snapshot_first_connection": belonging,
                "n_tier_1_2_app_connected": len(bucket["t12"]),
                "tier_1_2_apps_connected": sorted(bucket["t12"]),
                "n_tier_3_4_app_connected": len(bucket["t34"]),
                "tier_3_4_apps_connected": sorted(bucket["t34"]),
                "n_tier_5_app_connected": len(bucket["t5"]),
                "tier_5_apps_connected": sorted(bucket["t5"]),
            }
        )
    rows_out.sort(key=lambda row: json.dumps(row, sort_keys=True))
    return rows_out


def _same_multiset(actual: Any, expected: list[dict[str, Any]]) -> bool:
    if not isinstance(actual, list) or len(actual) != len(expected):
        return False
    key = lambda entry: json.dumps(entry, sort_keys=True, default=str)
    actual_sorted = sorted((entry for entry in actual if isinstance(entry, dict)), key=key)
    expected_sorted = sorted(expected, key=key)
    return actual_sorted == expected_sorted


def _resolved_sql(snap_date: str) -> str:
    return RAW_SQL.replace(SNAP_PILL, snap_date)


def _require_expect_shape(
    expect: Any,
    derived: list[dict[str, Any]],
    snap_date: str,
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
    derived_branch = "zero_rows" if not derived else "rows"
    if branch != derived_branch:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.branch {branch!r} contradicts the seeded tables "
            f"(derived {derived_branch!r}: {len(derived)} created rows)"
        )
    projected = [json.dumps(row, sort_keys=True) for row in derived]
    if len(set(projected)) != len(projected):
        raise RuntimeError(
            f"recipe {RECIPE_ID} derived created rows must be pairwise distinct "
            "(multiset groundtruth matching would be ambiguous)"
        )
    checks = (
        expect.get("executed_action_count") == 3,
        expect.get("tools") == EXPECTED_REGISTRY_TOOLS,
        expect.get("trace_tools") == EXPECTED_RAW_TOOLS,
        expect.get("snap_date") == snap_date,
        expect.get("resolved_sql") == _resolved_sql(snap_date),
        expect.get("declare_result") == {"days_threshold": "30", "snap_date": snap_date},
        expect.get("dead_async_step_skipped") is True,
        expect.get("return_value") == {"Result": "success"},
        expect.get("created_row_count") == len(derived),
        _same_multiset(expect.get("created_rows"), derived),
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with the seeded ground truth "
            f"(branch {branch!r}, {len(derived)} created rows, snap_date {snap_date!r}): "
            f"{expect!r}"
        )
    _require_tool_expectations(expect, snap_date)


def _require_tool_expectations(expect: dict[str, Any], snap_date: str) -> None:
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or len(items) != 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin both registry calls"
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
        if item.get("tool") != EXPECTED_REGISTRY_TOOLS[idx]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}].tool must be "
                f"{EXPECTED_REGISTRY_TOOLS[idx]!r}; got {item.get('tool')!r}"
            )
    sql_item, return_item = items
    checks = (
        sql_item.get("args_contains") == {"sql": _resolved_sql(snap_date), "parameters": {}},
        # A CTAS returns exactly one status row live regardless of contents.
        sql_item.get("result_count") == 1,
        return_item.get("args_contains") == {"result": {"Result": "success"}},
        return_item.get("result_contains") == {"Result": "success"},
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations do not pin the derived ground truth: {items!r}"
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
    return dict(ctx.tools.call("harness.snowflake.snapshot", {}))


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
