from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_113804593


RECIPE_ID = "113804593"
SEED_TYPE = "snowflake_old_pricing_customers_lookup_export_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "3be5e081"
LOOKUP_TABLE_ID = "3900147"
SNAPSHOT_TABLE = "edw_db.workato_usage_intermediate.accounts_snapshot"
INTERNAL_TABLE = "product.plg.salesforce_internal_accounts_jiawei"
DELETED_TABLE = "product.plg.sfdc_hard_deleted_accounts"
SNOWFLAKE_TABLES = (SNAPSHOT_TABLE, INTERNAL_TABLE, DELETED_TABLE)
TRUNCATE_STEP_AS = "c508a22e"
SQL_STEP_AS = "64fd1130"
BATCH_STEP_AS = "a909681c"
DEAD_STOP_AS = "fd3c9883"
DEAD_ELSE_BATCH_AS = "fadff562"
RAW_SQL = (
    "select \n"
    "    entry_date\n"
    "    , account_name as customer\n"
    "    , owner_id\n"
    "    , owner\n"
    "    , active_subscription\n"
    "    , subscription_start_date\n"
    "    , current_arr_usd as current_arr\n"
    "    , cat_company_size\n"
    "    , account_id as account_id\n"
    "    , pricing_model\n"
    "from edw_db.workato_usage_intermediate.accounts_snapshot\n"
    "where 1=1\n"
    "    and entry_date = (select max(entry_date) from edw_db.workato_usage_intermediate.accounts_snapshot)\n"
    "    and account_id not in (select id from product.plg.salesforce_internal_accounts_jiawei)\n"
    "    and account_id not in (select account_id from product.plg.sfdc_hard_deleted_accounts)\n"
    "    and is_direct\n"
    "    and is_paying\n"
    "    ;"
)


_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "3be5e081",
  "provider": "clock",
  "name": "scheduled_event",
  "skip": false,
  "input": {
   "time_unit": "days",
   "trigger_at": "17:00:00",
   "trigger_every": "1"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "c508a22e",
  "provider": "lookup_table",
  "name": "truncate",
  "skip": false,
  "input": {
   "lookup_table_id": "3900147"
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "64fd1130",
  "provider": "snowflake",
  "name": "run_custom_sql",
  "skip": false,
  "input": {
   "output_schema": "[{\"control_type\":\"text\",\"label\":\"entry_date\",\"name\":\"entry_date\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"customer\",\"name\":\"customer\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"owner_id\",\"name\":\"owner_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"owner\",\"name\":\"owner\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"active_subscription\",\"name\":\"active_subscription\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"subscription_start_date\",\"name\":\"subscription_start_date\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"current_plan\",\"name\":\"current_plan\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"current_arr\",\"name\":\"current_arr\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"cat_company_size\",\"name\":\"cat_company_size\",\"type\":\"string\",\"optional\":true},{\"name\":\"account_id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"},{\"name\":\"pricing_model\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Pricing model\"}]",
   "sql": "select \n    entry_date\n    , account_name as customer\n    , owner_id\n    , owner\n    , active_subscription\n    , subscription_start_date\n    , current_arr_usd as current_arr\n    , cat_company_size\n    , account_id as account_id\n    , pricing_model\nfrom edw_db.workato_usage_intermediate.accounts_snapshot\nwhere 1=1\n    and entry_date = (select max(entry_date) from edw_db.workato_usage_intermediate.accounts_snapshot)\n    and account_id not in (select id from product.plg.salesforce_internal_accounts_jiawei)\n    and account_id not in (select account_id from product.plg.sfdc_hard_deleted_accounts)\n    and is_direct\n    and is_paying\n    ;",
   "update_only": "false"
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "a909681c",
  "provider": "lookup_table",
  "name": "add_batch_of_entries",
  "skip": false,
  "input": {
   "entries": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\"]}')}",
    "parameters": {
     "col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"entry_date\"]}')}",
     "col10": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"pricing_model\"]}')}",
     "col2": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"customer\"]}')}",
     "col3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"owner_id\"]}')}",
     "col4": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"owner\"]}')}",
     "col5": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"active_subscription\"]}')}",
     "col6": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"subscription_start_date\"]}')}",
     "col7": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"current_arr\"]}')}",
     "col8": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"cat_company_size\"]}')}",
     "col9": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"account_id\"]}')}"
    }
   },
   "lookup_table_id": "3900147"
  }
 },
 {
  "keyword": "if",
  "number": 5,
  "as": null,
  "provider": null,
  "name": null,
  "skip": true,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows_affected\"]}')}",
     "operand": "equals_to",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "stop",
  "number": 6,
  "as": "fd3c9883",
  "provider": null,
  "name": null,
  "skip": true,
  "input": {
   "stop_with_error": "false"
  }
 },
 {
  "keyword": "else",
  "number": 7,
  "as": null,
  "provider": null,
  "name": null,
  "skip": true,
  "input": {}
 },
 {
  "keyword": "action",
  "number": 8,
  "as": "fadff562",
  "provider": "lookup_table",
  "name": "add_batch_of_entries",
  "skip": true,
  "input": {
   "entries": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\"]}')}",
    "parameters": {
     "col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"entry_date\"]}')}",
     "col10": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"pricing_model\"]}')}",
     "col2": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"customer\"]}')}",
     "col3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"owner_id\"]}')}",
     "col4": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"owner\"]}')}",
     "col5": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"active_subscription\"]}')}",
     "col6": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"subscription_start_date\"]}')}",
     "col7": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"current_arr\"]}')}",
     "col8": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"cat_company_size\"]}')}",
     "col9": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"64fd1130\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"account_id\"]}')}"
    }
   },
   "lookup_table_id": "3900147"
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.truncate",
    "snowflake.run_custom_sql",
    "lookup_table.add_batch_of_entries",
]
ALLOWED_TOOLS: list[str] = list(EXPECTED_RAW_TOOLS)
DEAD_STEP_IDS = (DEAD_STOP_AS, DEAD_ELSE_BATCH_AS)
SQL_ALIAS_TO_COL = {
    "entry_date": "col1",
    "customer": "col2",
    "owner_id": "col3",
    "owner": "col4",
    "active_subscription": "col5",
    "subscription_start_date": "col6",
    "current_arr": "col7",
    "cat_company_size": "col8",
    "account_id": "col9",
    "pricing_model": "col10",
}
SNAPSHOT_COLUMNS = {
    "entry_date": "date",
    "account_name": "string",
    "owner_id": "string",
    "owner": "string",
    "active_subscription": "string",
    "subscription_start_date": "string",
    "current_arr_usd": "string",
    "cat_company_size": "string",
    "account_id": "string",
    "pricing_model": "string",
    "is_direct": "boolean",
    "is_paying": "boolean",
}
INTERNAL_COLUMNS = {"id": "string"}
DELETED_COLUMNS = {"account_id": "string"}
SEED_COLUMN_TO_ALIAS = {
    "entry_date": "entry_date",
    "account_name": "customer",
    "owner_id": "owner_id",
    "owner": "owner",
    "active_subscription": "active_subscription",
    "subscription_start_date": "subscription_start_date",
    "current_arr_usd": "current_arr",
    "cat_company_size": "cat_company_size",
    "account_id": "account_id",
    "pricing_model": "pricing_model",
}
CASES = ("rows_exported", "zero_rows_empty_export", "max_entry_date_boundary")
REQUIRED_EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "truncate_deleted_rows",
    "sql_row_count",
    "batch_entries",
    "final_row_count",
    "final_lookup_rows",
    "dead_if_traced_skipped",
    "steps_absent_from_trace",
)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LOOKUP_COL_RE = re.compile(r"^col(?:[1-9]|10)$")


def _structure(node: dict[str, Any]) -> list[dict[str, Any]]:
    pin: dict[str, Any] = {
        "keyword": node.get("keyword"),
        "number": node.get("number"),
        "as": node.get("as"),
        "provider": node.get("provider"),
        "name": node.get("name"),
        "skip": bool(node.get("skip")),
        "input": node.get("input") or {},
    }
    if node.get("keyword") == "foreach":
        pin["repeat_mode"] = node.get("repeat_mode")
        pin["batch_size"] = node.get("batch_size")
        pin["source"] = node.get("source")
    if isinstance(node.get("filter"), dict):
        pin["filter"] = node["filter"]
    out = [pin]
    for child in node.get("block") or []:
        if isinstance(child, dict):
            out.extend(_structure(child))
    return out


def validate_113804593(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    actual = _structure(raw)
    if len(actual) != len(STRUCTURE_PINS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} node count changed: {len(actual)} != {len(STRUCTURE_PINS)}"
        )
    for idx, (got, expected) in enumerate(zip(actual, STRUCTURE_PINS)):
        if got != expected:
            raise RuntimeError(
                f"recipe {RECIPE_ID} node {idx} (step {expected.get('number')}) changed:\n"
                f"expected: {json.dumps(expected, sort_keys=True)}\n"
                f"actual:   {json.dumps(got, sort_keys=True)}"
            )
    # Semantic pins on the drift-prone pieces (the tree pin holds the bytes;
    # these name the trap when one changes).
    sql_pin = next(pin for pin in actual if pin["as"] == SQL_STEP_AS)
    if sql_pin["input"].get("sql") != RAW_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} custom SQL changed")
    if RAW_SQL.count(SNAPSHOT_TABLE) != 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expects the snapshot 3-part name in BOTH the FROM and "
            "the max() subselect"
        )
    if RAW_SQL.count(INTERNAL_TABLE) != 1 or RAW_SQL.count(DELETED_TABLE) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expects exactly one NOT IN subquery per exclusion table"
        )
    dead_pins = [pin for pin in actual if pin["number"] in (5, 6, 7, 8)]
    if not dead_pins or any(pin["skip"] is not True for pin in dead_pins):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the rows_affected IF subtree is no longer fully "
            "skip:true -- the dead-branch proof does not hold; re-triage before building"
        )
    for pin in actual:
        if pin["provider"] == "lookup_table":
            table = str((pin["input"] or {}).get("lookup_table_id") or "")
            if table != LOOKUP_TABLE_ID:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} lookup step {pin['as']!r} targets table "
                    f"{table!r}, expected {LOOKUP_TABLE_ID!r}"
                )
    batch_pin = next(pin for pin in actual if pin["as"] == BATCH_STEP_AS)
    dead_batch_pin = next(pin for pin in actual if pin["as"] == DEAD_ELSE_BATCH_AS)
    if batch_pin["input"].get("entries") != dead_batch_pin["input"].get("entries"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the live and dead add_batch mappings diverged -- the "
            "dead subtree is no longer a frozen copy of the live export"
        )
    actions = [pin for pin in actual if pin["keyword"] == "action" and not pin["skip"]]
    expected_actions = [
        (TRUNCATE_STEP_AS, "lookup_table", "truncate"),
        (SQL_STEP_AS, "snowflake", "run_custom_sql"),
        (BATCH_STEP_AS, "lookup_table", "add_batch_of_entries"),
    ]
    if [(pin["as"], pin["provider"], pin["name"]) for pin in actions] != expected_actions:
        raise RuntimeError(f"recipe {RECIPE_ID} live action sequence changed")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "lookup_table_id": LOOKUP_TABLE_ID,
        "snowflake_tables": list(SNOWFLAKE_TABLES),
        "actions": [
            {
                "number": pin["number"],
                "provider": pin["provider"],
                "name": pin["name"],
                "as": pin["as"],
            }
            for pin in actions
        ],
    }


def seed_113804593(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_113804593(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (payload-less "
            f"scheduler tick; no trigger field is ever dereferenced): {trigger!r}"
        )
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: a forced action error would fail the "
            "whole run instead of exercising a recipe branch"
        )
    if data.get("job_context") is not None:
        raise RuntimeError(f"recipe {RECIPE_ID} never reads job_context (dead seed state)")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["lookup_table", "snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the lookup_table and "
            f"snowflake_live sections; got {sorted(seed_in.keys())}"
        )
    preseeded = _require_lookup_section(seed_in["lookup_table"])
    snapshot_rows, internal_ids, deleted_ids = _require_snowflake_section(seed_in["snowflake_live"])
    qualifying = _qualifying_rows(snapshot_rows, internal_ids, deleted_ids)
    _require_expect_shape(
        data.get("expect"), snapshot_rows, internal_ids, deleted_ids, qualifying, preseeded
    )
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


def run_113804593(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_113804593(raw)
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
        # The three seeded Snowflake tables are benchmark-owned live state:
        # drop them even when execution fails. The lookup table is a
        # per-variant isolated mock -- no live cleanup exists for it.
        snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    details["cleanup_response"] = {"snowflake_live": snowflake_cleanup}
    if not (snowflake_cleanup or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake cleanup failed: {snowflake_cleanup}")
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
    result["verifier"] = verify_113804593(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_lookup_section(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table must be exactly {{'tables': ...}}"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [LOOKUP_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must declare exactly table "
            f"{LOOKUP_TABLE_ID!r}"
        )
    rows = tables[LOOKUP_TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} pre-seed at least one stale lookup row -- truncate is "
            "proven by its deleted_rows count"
        )
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


def _require_snowflake_section(
    section: Any,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the SQL has no CURRENT_* -> current_time must NOT be declared)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted(SNOWFLAKE_TABLES):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly the 3 "
            f"literal 3-part names {sorted(SNOWFLAKE_TABLES)} (all referenced by the SQL)"
        )
    snapshot_rows = _require_snapshot_table(tables[SNAPSHOT_TABLE])
    internal_ids = _require_single_column_table(tables[INTERNAL_TABLE], INTERNAL_TABLE, "id")
    deleted_ids = _require_single_column_table(tables[DELETED_TABLE], DELETED_TABLE, "account_id")
    return snapshot_rows, internal_ids, deleted_ids


def _require_snapshot_table(spec: Any) -> list[dict[str, Any]]:
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} snapshot table spec must be exactly "
            "{'columns': ..., 'rows': ...}"
        )
    if spec["columns"] != SNAPSHOT_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} accounts_snapshot columns must be exactly {SNAPSHOT_COLUMNS}"
        )
    rows = spec["rows"]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} accounts_snapshot rows must be non-empty -- the "
            "zero-export case proves the WHERE arms via non-qualifying rows, not an "
            "empty table"
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
                        f"recipe {RECIPE_ID} accounts_snapshot row {idx}.{column} must "
                        f"be a boolean; got {value!r}"
                    )
            elif kind == "date":
                if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} accounts_snapshot row {idx}.{column} must "
                        f"be YYYY-MM-DD (stable live DATE read-back); got {value!r}"
                    )
            else:
                if not isinstance(value, str) or not value.strip():
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} accounts_snapshot row {idx}.{column} must "
                        f"be a non-empty string (lookup mock stringifies -- seed "
                        f"numerics as strings); got {value!r}"
                    )
    return [dict(row) for row in rows]


def _require_single_column_table(spec: Any, table: str, column: str) -> list[str]:
    expected_columns = {column: "string"}
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {table} spec must be exactly "
            "{'columns': ..., 'rows': ...}"
        )
    if spec["columns"] != expected_columns:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {table} columns must be exactly {expected_columns}"
        )
    rows = spec["rows"]
    if not isinstance(rows, list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {table} rows must be a list (empty list = the "
            "NOT IN subquery excludes nothing)"
        )
    values: list[str] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != [column]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {table} row {idx} must be exactly "
                f"{{{column!r}: <account id>}}; got {row!r}"
            )
        value = row[column]
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {table} row {idx}.{column} must be a "
                f"non-empty string; got {value!r}"
            )
        values.append(value)
    return values


def _qualifying_rows(
    snapshot_rows: list[dict[str, Any]],
    internal_ids: list[str],
    deleted_ids: list[str],
) -> list[dict[str, Any]]:
    """The rows the live SELECT must return (as lookup colN dicts):
    entry_date == GLOBAL max(entry_date) over ALL rows AND account_id NOT IN
    the internal list AND NOT IN the hard-deleted list AND is_direct AND
    is_paying. Order-insensitive (no ORDER BY)."""
    max_entry_date = max(str(row["entry_date"]) for row in snapshot_rows)
    excluded = set(internal_ids) | set(deleted_ids)
    out: list[dict[str, Any]] = []
    for row in snapshot_rows:
        if (
            str(row["entry_date"]) == max_entry_date
            and str(row["account_id"]) not in excluded
            and row["is_direct"] is True
            and row["is_paying"] is True
        ):
            out.append(
                {
                    SQL_ALIAS_TO_COL[alias]: str(row[column])
                    for column, alias in SEED_COLUMN_TO_ALIAS.items()
                }
            )
    return out


def _require_expect_shape(
    expect: Any,
    snapshot_rows: list[dict[str, Any]],
    internal_ids: list[str],
    deleted_ids: list[str],
    qualifying: list[dict[str, Any]],
    preseeded: list[dict[str, Any]],
) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    case = expect.get("case")
    if case not in CASES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.case must be one of {CASES}")
    account_ids = [entry["col9"] for entry in qualifying]
    if len(set(account_ids)) != len(account_ids):
        raise RuntimeError(
            f"recipe {RECIPE_ID} QUALIFYING rows must carry distinct account_id values "
            "(SELECT order is not guaranteed without ORDER BY; groundtruth matching is "
            "keyed on col9). Non-qualifying rows may reuse an account_id -- that is the "
            "max-entry-date twin-row case."
        )
    _require_case(case, snapshot_rows, internal_ids, deleted_ids, qualifying)
    checks = (
        expect.get("executed_action_count") == 3,
        expect.get("tools") == EXPECTED_RAW_TOOLS,
        expect.get("truncate_deleted_rows") == len(preseeded),
        expect.get("sql_row_count") == len(qualifying),
        _same_multiset(expect.get("batch_entries"), qualifying),
        expect.get("final_row_count") == len(qualifying),
        _same_multiset(expect.get("final_lookup_rows"), qualifying),
        expect.get("dead_if_traced_skipped") is True,
        expect.get("steps_absent_from_trace") == list(DEAD_STEP_IDS),
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with the seeded ground "
            f"truth ({len(qualifying)} qualifying rows): {expect!r}"
        )
    _require_tool_expectations(expect, qualifying)


def _require_case(
    case: str,
    snapshot_rows: list[dict[str, Any]],
    internal_ids: list[str],
    deleted_ids: list[str],
    qualifying: list[dict[str, Any]],
) -> None:
    max_date = max(str(row["entry_date"]) for row in snapshot_rows)
    flags_pass = lambda row: row["is_direct"] is True and row["is_paying"] is True
    max_date_flag_rows = [
        row for row in snapshot_rows if str(row["entry_date"]) == max_date and flags_pass(row)
    ]
    internal_excluded = [
        row for row in max_date_flag_rows if str(row["account_id"]) in set(internal_ids)
    ]
    deleted_excluded = [
        row for row in max_date_flag_rows if str(row["account_id"]) in set(deleted_ids)
    ]
    flag_excluded = [
        row
        for row in snapshot_rows
        if str(row["entry_date"]) == max_date and not flags_pass(row)
    ]
    stale_excluded = [
        row
        for row in snapshot_rows
        if str(row["entry_date"]) != max_date
        and flags_pass(row)
        and str(row["account_id"]) not in set(internal_ids) | set(deleted_ids)
    ]
    if case == "rows_exported":
        checks = (
            len(qualifying) >= 2,
            len(internal_excluded) >= 1,
            len(deleted_excluded) >= 1,
            len(flag_excluded) >= 1,
            len(stale_excluded) >= 1,
        )
        reason = (
            "rows_exported must prove EVERY WHERE arm live: >=2 qualifying rows plus "
            ">=1 row excluded by each of (internal NOT IN, hard-deleted NOT IN, a "
            "false boolean flag on the max date, an older entry_date)"
        )
    elif case == "zero_rows_empty_export":
        checks = (
            len(qualifying) == 0,
            len(snapshot_rows) >= 3,
            len(internal_excluded) >= 1 or len(deleted_excluded) >= 1,
        )
        reason = (
            "zero_rows_empty_export seeds ONLY non-qualifying rows (>=3, at least one "
            "killed by a NOT IN list) so the empty export comes from the WHERE, not "
            "an empty table"
        )
    else:  # max_entry_date_boundary
        by_account: dict[str, set[str]] = {}
        for row in snapshot_rows:
            if flags_pass(row) and str(row["account_id"]) not in set(internal_ids) | set(deleted_ids):
                by_account.setdefault(str(row["account_id"]), set()).add(str(row["entry_date"]))
        twin_accounts = [acc for acc, dates in by_account.items() if len(dates) >= 2 and max_date in dates]
        old_only_accounts = [acc for acc, dates in by_account.items() if max_date not in dates]
        checks = (
            len(qualifying) >= 1,
            len(twin_accounts) >= 1,
            len(old_only_accounts) >= 1,
            not internal_ids and not deleted_ids,
        )
        reason = (
            "max_entry_date_boundary isolates the scalar subquery: one otherwise-"
            "qualifying account on BOTH the max and an older date (older row dropped) "
            "plus one account ONLY on the older date (fully absent -- proves the max "
            "is per-SNAPSHOT, not per-account); both exclusion tables must be EMPTY"
        )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} case {case!r} seed requirements not met ({reason})"
        )


def _same_multiset(actual: Any, expected: list[dict[str, Any]]) -> bool:
    if not isinstance(actual, list) or len(actual) != len(expected):
        return False
    key = lambda entry: (
        str(entry.get("col9") or ""),
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
    if (
        not isinstance(items, list)
        or len(items) != 3
        or not all(isinstance(item, dict) for item in items)
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin all 3 executed calls"
        )
    truncate_item, sql_item, batch_item = items
    checks = (
        truncate_item.get("tool") == EXPECTED_RAW_TOOLS[0],
        truncate_item.get("lookup_table_id") == LOOKUP_TABLE_ID,
        truncate_item.get("args_contains") == {"lookup_table_id": LOOKUP_TABLE_ID},
        sql_item.get("tool") == EXPECTED_RAW_TOOLS[1],
        sql_item.get("args_contains") == {"sql": RAW_SQL, "parameters": {}},
        sql_item.get("result_count") == len(qualifying),
        batch_item.get("tool") == EXPECTED_RAW_TOOLS[2],
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
