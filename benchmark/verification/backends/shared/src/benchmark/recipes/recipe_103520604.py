from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_103520604


RECIPE_ID = "103520604"
SEED_TYPE = "snowflake_accounts_snapshot_xray_customers_lookup_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "3be5e081"
SNAPSHOT_TABLE = "edw_db.workato_usage_intermediate.accounts_snapshot"
LOOKUP_TABLE_ID = "3290579"
TRUNCATE_STEP_AS = "c508a22e"
SQL_STEP_AS = "64fd1130"
IF_BATCH_STEP_AS = "66dcea69"
ELSE_BATCH_STEP_AS = "fadff562"
DEAD_DECLARE_AS = "8038a067"
DEAD_SQL_LATEST_AS = "d5877211"
DEAD_SQL_SNAPSHOT_AS = "74bc10f8"
RAW_SQL = (
    "select \n"
    "    entry_date\n"
    "    , account_name as customer\n"
    "    , owner_id\n"
    "    , owner\n"
    "    , active_subscription\n"
    "    , subscription_start_date\n"
    "    , current_plan\n"
    "    , current_arr_usd as current_arr\n"
    "    , cat_company_size\n"
    "    , account_id as account_id\n"
    "from edw_db.workato_usage_intermediate.accounts_snapshot\n"
    "where 1=1\n"
    "    and entry_date = (select max(entry_date) from edw_db.workato_usage_intermediate.accounts_snapshot)\n"
    "    and is_direct\n"
    "    and is_paying\n"
    "    ;"
)


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "clock", "name": "scheduled_event", "as": "3be5e081", "skip": false, "input": {"time_unit": "days", "trigger_at": "<anon>12:00:00</anon>", "trigger_every": "1"}, "block": [{"number": 2, "keyword": "action", "provider": "lookup_table", "name": "truncate", "as": "c508a22e", "skip": false, "input": {"lookup_table_id": "3290579"}, "block": []}, {"number": 3, "keyword": "action", "provider": "workato_variable", "name": "declare_variable", "as": "8038a067", "skip": true, "block": []}, {"number": 4, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql", "as": "64fd1130", "skip": false, "input": {"output_schema": "[{\"control_type\":\"text\",\"label\":\"entry_date\",\"name\":\"entry_date\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"customer\",\"name\":\"customer\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"owner_id\",\"name\":\"owner_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"owner\",\"name\":\"owner\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"active_subscription\",\"name\":\"active_subscription\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"subscription_start_date\",\"name\":\"subscription_start_date\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"current_plan\",\"name\":\"current_plan\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"current_arr\",\"name\":\"current_arr\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"cat_company_size\",\"name\":\"cat_company_size\",\"type\":\"string\",\"optional\":true},{\"name\":\"account_id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"}]", "sql": "select \n    entry_date\n    , account_name as customer\n    , owner_id\n    , owner\n    , active_subscription\n    , subscription_start_date\n    , current_plan\n    , current_arr_usd as current_arr\n    , cat_company_size\n    , account_id as account_id\nfrom edw_db.workato_usage_intermediate.accounts_snapshot\nwhere 1=1\n    and entry_date = (select max(entry_date) from edw_db.workato_usage_intermediate.accounts_snapshot)\n    and is_direct\n    and is_paying\n    ;", "update_only": "false"}, "block": []}, {"number": 5, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows_affected\"]}')}", "operand": "equals_to", "rhs": "0"}], "operand": "and", "type": "compound"}, "block": [{"number": 6, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql", "as": "d5877211", "skip": true, "block": []}, {"number": 7, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql", "as": "74bc10f8", "skip": true, "block": []}, {"number": 8, "keyword": "action", "provider": "lookup_table", "name": "add_batch_of_entries", "as": "66dcea69", "skip": false, "input": {"entries": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\"]}')}", "parameters": {"col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"entry_date\"]}')}", "col10": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"account_id\"]}')}", "col2": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"customer\"]}')}", "col3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"owner_id\"]}')}", "col4": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"owner\"]}')}", "col5": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"active_subscription\"]}')}", "col6": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"subscription_start_date\"]}')}", "col7": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"current_plan\"]}')}", "col8": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"current_arr\"]}')}", "col9": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"cat_company_size\"]}')}"}}, "lookup_table_id": "3290579"}, "block": []}, {"number": 9, "keyword": "else", "provider": "", "name": "", "as": "", "skip": false, "input": {}, "block": [{"number": 10, "keyword": "action", "provider": "lookup_table", "name": "add_batch_of_entries", "as": "fadff562", "skip": false, "input": {"entries": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\"]}')}", "parameters": {"col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"entry_date\"]}')}", "col10": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"account_id\"]}')}", "col2": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"customer\"]}')}", "col3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"owner_id\"]}')}", "col4": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"owner\"]}')}", "col5": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"active_subscription\"]}')}", "col6": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"subscription_start_date\"]}')}", "col7": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"current_plan\"]}')}", "col8": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"current_arr\"]}')}", "col9": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"cat_company_size\"]}')}"}}, "lookup_table_id": "3290579"}, "block": []}]}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (TRUNCATE_STEP_AS, "lookup_table", "truncate"),
    (SQL_STEP_AS, "snowflake", "run_custom_sql"),
    (IF_BATCH_STEP_AS, "lookup_table", "add_batch_of_entries"),
    (ELSE_BATCH_STEP_AS, "lookup_table", "add_batch_of_entries"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.truncate",
    "snowflake.run_custom_sql",
    "lookup_table.add_batch_of_entries",
]
ALLOWED_TOOLS: list[str] = list(EXPECTED_RAW_TOOLS)
DEAD_STEP_IDS = (DEAD_DECLARE_AS, DEAD_SQL_LATEST_AS, DEAD_SQL_SNAPSHOT_AS)
SQL_ALIAS_TO_COL = {
    "entry_date": "col1",
    "customer": "col2",
    "owner_id": "col3",
    "owner": "col4",
    "active_subscription": "col5",
    "subscription_start_date": "col6",
    "current_plan": "col7",
    "current_arr": "col8",
    "cat_company_size": "col9",
    "account_id": "col10",
}
SNAPSHOT_COLUMNS = {
    "entry_date": "date",
    "account_name": "string",
    "owner_id": "string",
    "owner": "string",
    "active_subscription": "string",
    "subscription_start_date": "string",
    "current_plan": "string",
    "current_arr_usd": "string",
    "cat_company_size": "string",
    "account_id": "string",
    "is_direct": "boolean",
    "is_paying": "boolean",
}
SEED_COLUMN_TO_ALIAS = {
    "entry_date": "entry_date",
    "account_name": "customer",
    "owner_id": "owner_id",
    "owner": "owner",
    "active_subscription": "active_subscription",
    "subscription_start_date": "subscription_start_date",
    "current_plan": "current_plan",
    "current_arr_usd": "current_arr",
    "cat_company_size": "cat_company_size",
    "account_id": "account_id",
}
BRANCHES = ("if_empty", "else_rows")
REQUIRED_EXPECT_KEYS = (
    "case",
    "branch",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "truncate_deleted_rows",
    "sql_row_count",
    "batch_step_as",
    "batch_entries",
    "final_row_count",
    "final_lookup_rows",
    "dead_steps_traced_skipped",
    "steps_absent_from_trace",
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
_LOOKUP_COL_RE = re.compile(r"^col(?:[1-9]|10)$")


def validate_103520604(raw: dict[str, Any]) -> dict[str, Any]:
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
    # Semantic pins on the drift-prone pieces (the tree pin holds the exact
    # bytes; these name the trap when one changes).
    nodes = {str(node.get("as") or ""): node for node in _walk_nodes(raw)}
    sql_node = nodes.get(SQL_STEP_AS) or {}
    if str((sql_node.get("input") or {}).get("sql") or "") != RAW_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} custom SQL changed")
    if RAW_SQL.count(SNAPSHOT_TABLE) != 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expects the 3-part table name in BOTH the FROM and the "
            "max() subselect"
        )
    for step_as in DEAD_STEP_IDS:
        node = nodes.get(step_as)
        if not isinstance(node, dict) or node.get("skip") is not True:
            raise RuntimeError(
                f"recipe {RECIPE_ID} step {step_as} is no longer skip:true -- the dead-branch "
                "proof does not hold; re-triage before building"
            )
    for node in _walk_nodes(raw):
        if node.get("provider") == "lookup_table":
            table = str((node.get("input") or {}).get("lookup_table_id") or "")
            if table != LOOKUP_TABLE_ID:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} lookup step {node.get('as')!r} targets table "
                    f"{table!r}, expected {LOOKUP_TABLE_ID!r}"
                )
    if_node = next(
        (
            node
            for node in _walk_nodes(raw)
            if node.get("keyword") == "if" and not node.get("skip")
        ),
        None,
    )
    conditions = ((if_node or {}).get("input") or {}).get("conditions") or []
    if (
        len(conditions) != 1
        or "rows_affected" not in str(conditions[0].get("lhs") or "")
        or str(conditions[0].get("operand") or "") != "equals_to"
        or str(conditions[0].get("rhs") or "") != "0"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} IF-5 empty-result condition changed")
    if_batch = nodes.get(IF_BATCH_STEP_AS) or {}
    else_batch = nodes.get(ELSE_BATCH_STEP_AS) or {}
    if (if_batch.get("input") or {}).get("entries") != (else_batch.get("input") or {}).get("entries"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the two add_batch_of_entries mappings diverged -- the "
            "branch discriminator analysis (identical bodies, as-id pins) no longer holds"
        )
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "lookup_table_id": LOOKUP_TABLE_ID,
        "snapshot_table": SNAPSHOT_TABLE,
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


def seed_103520604(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_103520604(raw)
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
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["lookup_table", "snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the lookup_table and "
            f"snowflake_live sections; got {sorted(seed_in.keys())}"
        )
    preseeded_lookup_rows = _require_lookup_section(seed_in["lookup_table"])
    snapshot_rows = _require_snowflake_section(seed_in["snowflake_live"])
    qualifying = _qualifying_rows(snapshot_rows)
    _require_expect_shape(data.get("expect"), snapshot_rows, qualifying, preseeded_lookup_rows)
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
        "lookup_table": deepcopy(seed_in["lookup_table"]),
        "expect": deepcopy(data["expect"]),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_103520604(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_103520604(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    if seed.get("trigger") != {}:
        raise RuntimeError(f"recipe {RECIPE_ID} seed trigger must be the explicit payload-less {{}}")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect"),
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
        # The seeded accounts_snapshot table is benchmark-owned live state:
        # drop it even when execution fails. The lookup table is a per-variant
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
    result["verifier"] = verify_103520604(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_lookup_section(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table must be exactly {{'tables': ...}} "
            "(no formula-level lookup() exists, so no names map)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [LOOKUP_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must declare exactly table "
            f"{LOOKUP_TABLE_ID!r} (rows may be an explicit empty list)"
        )
    rows = tables[LOOKUP_TABLE_ID]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {LOOKUP_TABLE_ID} rows must be a list")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or not row:
            raise RuntimeError(
                f"recipe {RECIPE_ID} pre-seeded lookup row {idx} must be a non-empty object"
            )
        for key, value in row.items():
            if not _LOOKUP_COL_RE.fullmatch(str(key)):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} pre-seeded lookup row {idx} has non-colN key {key!r}"
                )
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} pre-seeded lookup row {idx}.{key} must be a "
                    f"non-empty string; got {value!r}"
                )
    return [dict(row) for row in rows]


def _require_snowflake_section(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the SQL has no CURRENT_* -> current_time must NOT be declared)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [SNAPSHOT_TABLE]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{SNAPSHOT_TABLE!r} (the LITERAL 3-part name both SQL occurrences use)"
        )
    spec = tables[SNAPSHOT_TABLE]
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} snowflake table spec must be exactly {{'columns': ..., 'rows': ...}}"
        )
    if spec["columns"] != SNAPSHOT_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} accounts_snapshot columns must be exactly {SNAPSHOT_COLUMNS}"
        )
    rows = spec["rows"]
    if not isinstance(rows, list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} accounts_snapshot rows must be a list (empty ONLY for an "
            "empty-table if-branch variant)"
        )
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(SNAPSHOT_COLUMNS.keys()):
            raise RuntimeError(
                f"recipe {RECIPE_ID} accounts_snapshot row {idx} must fill exactly the "
                f"declared columns: {row!r}"
            )
        for column, kind in SNAPSHOT_COLUMNS.items():
            value = row[column]
            if kind == "boolean":
                if not isinstance(value, bool):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} accounts_snapshot row {idx}.{column} must be a "
                        f"boolean; got {value!r}"
                    )
            elif kind == "date":
                if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} accounts_snapshot row {idx}.{column} must be "
                        f"YYYY-MM-DD (stable live DATE read-back); got {value!r}"
                    )
            else:
                if not isinstance(value, str) or not value.strip():
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} accounts_snapshot row {idx}.{column} must be a "
                        f"non-empty string; got {value!r}"
                    )
    return [dict(row) for row in rows]


def _qualifying_rows(snapshot_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The rows the live SELECT must return (as lookup colN dicts):
    entry_date == GLOBAL max(entry_date) over ALL rows AND is_direct AND
    is_paying. Order-insensitive (Snowflake has no ORDER BY here)."""
    if not snapshot_rows:
        return []
    max_entry_date = max(str(row["entry_date"]) for row in snapshot_rows)
    out: list[dict[str, Any]] = []
    for row in snapshot_rows:
        if row["is_direct"] is True and row["is_paying"] is True and str(row["entry_date"]) == max_entry_date:
            mapped = {
                SQL_ALIAS_TO_COL[alias]: str(row[column])
                for column, alias in SEED_COLUMN_TO_ALIAS.items()
            }
            out.append(mapped)
    return out


def _require_expect_shape(
    expect: Any,
    snapshot_rows: list[dict[str, Any]],
    qualifying: list[dict[str, Any]],
    preseeded_lookup_rows: list[dict[str, Any]],
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
    derived_branch = "if_empty" if not qualifying else "else_rows"
    if branch != derived_branch:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.branch {branch!r} contradicts the seeded rows "
            f"(derived {derived_branch!r}: {len(qualifying)} qualifying rows)"
        )
    if branch == "else_rows" and len(qualifying) == len(snapshot_rows):
        raise RuntimeError(
            f"recipe {RECIPE_ID} else_rows variants must seed at least one NON-qualifying "
            "row (a failed flag or an older entry_date) to prove the WHERE filters live"
        )
    account_ids = [entry["col10"] for entry in qualifying]
    if len(set(account_ids)) != len(account_ids):
        raise RuntimeError(
            f"recipe {RECIPE_ID} QUALIFYING rows must carry distinct account_id values "
            "(SELECT order is not guaranteed without ORDER BY; groundtruth matching is "
            "keyed on col10). Non-qualifying rows may reuse an account_id -- that is "
            "the max-entry-date twin-row case."
        )
    batch_step_as = IF_BATCH_STEP_AS if branch == "if_empty" else ELSE_BATCH_STEP_AS
    expected_dead = [DEAD_DECLARE_AS] + (
        [DEAD_SQL_LATEST_AS, DEAD_SQL_SNAPSHOT_AS] if branch == "if_empty" else []
    )
    expected_absent = (
        [ELSE_BATCH_STEP_AS]
        if branch == "if_empty"
        else [IF_BATCH_STEP_AS, DEAD_SQL_LATEST_AS, DEAD_SQL_SNAPSHOT_AS]
    )
    checks = (
        expect.get("executed_action_count") == 3,
        expect.get("tools") == EXPECTED_RAW_TOOLS,
        expect.get("truncate_deleted_rows") == len(preseeded_lookup_rows),
        expect.get("sql_row_count") == len(qualifying),
        expect.get("batch_step_as") == batch_step_as,
        _same_multiset(expect.get("batch_entries"), qualifying),
        expect.get("final_row_count") == len(qualifying),
        _same_multiset(expect.get("final_lookup_rows"), qualifying),
        expect.get("dead_steps_traced_skipped") == expected_dead,
        expect.get("steps_absent_from_trace") == expected_absent,
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with the seeded ground truth "
            f"(branch {branch!r}, {len(qualifying)} qualifying rows): {expect!r}"
        )
    _require_tool_expectations(expect, qualifying)


def _same_multiset(actual: Any, expected: list[dict[str, Any]]) -> bool:
    if not isinstance(actual, list) or len(actual) != len(expected):
        return False
    key = lambda entry: (
        str(entry.get("col10") or ""),
        str(entry.get("col2") or ""),
        json.dumps(entry, sort_keys=True, default=str),
    )
    actual_sorted = sorted((entry for entry in actual if isinstance(entry, dict)), key=key)
    expected_sorted = sorted(expected, key=key)
    return actual_sorted == expected_sorted


def _require_tool_expectations(
    expect: dict[str, Any],
    qualifying: list[dict[str, Any]],
) -> None:
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or len(items) != 3:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin all 3 executed calls"
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
        if item.get("tool") != EXPECTED_RAW_TOOLS[idx]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}].tool must be "
                f"{EXPECTED_RAW_TOOLS[idx]!r}; got {item.get('tool')!r}"
            )
    truncate_item, sql_item, batch_item = items
    checks = (
        truncate_item.get("lookup_table_id") == LOOKUP_TABLE_ID,
        truncate_item.get("args_contains") == {"lookup_table_id": LOOKUP_TABLE_ID},
        sql_item.get("args_contains") == {"sql": RAW_SQL, "parameters": {}},
        sql_item.get("result_count") == len(qualifying),
        batch_item.get("lookup_table_id") == LOOKUP_TABLE_ID,
        batch_item.get("args_contains") == {"lookup_table_id": LOOKUP_TABLE_ID},
        # entries order is live SELECT order (unpinned here); the verifier
        # fragment pins the exact multiset via expect.batch_entries.
        batch_item.get("result_count") == len(qualifying),
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
    out: dict[str, Any] = {}
    out.update(ctx.tools.call("harness.lookup_table.snapshot", {}))
    out.update(ctx.tools.call("harness.snowflake.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
