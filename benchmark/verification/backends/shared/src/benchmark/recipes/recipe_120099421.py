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
from ..verifier import verify_120099421


RECIPE_ID = "120099421"
SEED_TYPE = "snowflake_app_tier_lookup_sync_variant"
TRACK = "live_snowflake_lookup_table_sync"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "f42a94d0"
SQL_STEP_AS = "39b44e18"
BASELINE_SEARCH_AS = "9f4b85c7"
FOREACH_AS = "e111e4a7"
INNER_SEARCH_AS = "3d6a002e"
ADD_STEP_AS = "78b012f3"
STOP_STEP_AS = "aa772329"
LOOKUP_TABLE_ID = "3300543"
# The literal 3-part names the SQL references; they MUST be the registered
# snowflake_live table keys so _rewrite_sql maps them onto the benchmark
# database (<SNOWFLAKE_DATABASE>.WORKATO_USAGE.APPLICATIONS_SNAPSHOT /
# <SNOWFLAKE_DATABASE>.PLG.RECIPE_SOPHISTICATION_APP_TIER).
SNAPSHOT_TABLE = "product.workato_usage.applications_snapshot"
TIER_TABLE = "product.plg.recipe_sophistication_app_tier"
SNAPSHOT_COLUMNS = {"TITLE": "string", "CATEGORY": "string", "ENTRY_DATE": "date"}
TIER_COLUMNS = {"TITLE": "string", "APP_TIER": "string"}
RAW_SQL = (
    "select final_table.title, final_table.category, app_tier\n"
    "from product.workato_usage.applications_snapshot final_table\n"
    "left join product.plg.recipe_sophistication_app_tier\n"
    "on final_table.title = recipe_sophistication_app_tier.title   \n"
    "and final_table.entry_date = (current_date - 1)\n"
    "where \n"
    "    final_table.category = 'app'\n"
    "    and app_tier in ('1','2','3','4')\n"
    "    and final_table.title not ilike '%secondary%'\n"
    "group by all"
)

# clock.scheduled_event (as f42a94d0, every 7 days at 00:00) — payload-less;
# NOTHING is dereferenced from the trigger output (trigger_input must be {}).
#   2  snowflake.run_custom_sql 39b44e18 (LIVE): RAW_SQL. The LEFT JOIN's
#      second ON predicate (entry_date = current_date - 1) gates the TIER
#      side, so a snapshot row with the wrong entry_date joins to NULL and
#      the `app_tier in ('1','2','3','4')` WHERE predicate drops it; category
#      and `not ilike '%secondary%'` prune the snapshot side; `group by all`
#      dedupes identical (title, category, app_tier) triples. current_date is
#      pinned via seed.snowflake_live.current_time (_rewrite_time fail-fast).
#   3  lookup_table.search_entries 9f4b85c7 table 3300543 (mock) col2='app'
#   IF 4: step-2 rows SIZE not_equals_to step-3 entries SIZE — a size-only
#      comparison (faithful author blind spot: equal counts with DIFFERENT
#      titles do nothing — pinned by a dedicated variant):
#     FOREACH 5 (as e111e4a7) over step-2 rows, repeat_mode simple:
#       6  lookup_table.search_entries 3d6a002e col1 = foreach title
#       IF 7 (3d6a002e entries size equals_to '0'):
#         8  lookup_table.add_entry 78b012f3 col1/col2/col3 =
#            foreach title/category/app_tier
#   9  STOP aa772329 (stop_with_error false) — top level, ALWAYS executes:
#      every trace ends in the stop marker.
#
# DETERMINISM RULE: the SQL has NO ORDER BY, so a multi-row result feeds the
# foreach in nondeterministic live order and per-iteration trace pins become
# flaky groundtruth. The seeder therefore requires expect.sql_rows to hold AT
# MOST ONE row; size mismatches are driven from the lookup side (0 or 2+
# seeded entries) and SQL-filter coverage comes from decoy rows the WHERE
# clause excludes. Every branch stays reachable: IF-4 true/false, inner IF-7
# true/false, foreach 1-iteration and 0-iteration paths.
#
# Backends: Snowflake runs LIVE (create-or-replace seed; BOTH tables dropped
# in the runner's finally). The recipe only READS Snowflake — live snapshot
# equality is verifier-pinned. lookup_table 3300543 is the Workato-internal
# mock, per-variant isolated; add_entry writes are the terminal observables
# (pinned via expect.final_lookup_rows). No try/catch exists, so
# force_action_error is forbidden (it would fail the whole run).

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "clock", "name": "scheduled_event", "as": "f42a94d0", "skip": false, "input": {"time_unit": "days", "trigger_at": "00:00:00", "trigger_every": "7"}, "block": [{"number": 2, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql", "as": "39b44e18", "skip": false, "input": {"output_schema": "[{\"name\":\"title\",\"type\":\"string\",\"optional\":false,\"label\":\"TITLE\",\"control_type\":\"text\"},{\"name\":\"category\",\"type\":\"string\",\"optional\":false,\"label\":\"CATEGORY\",\"control_type\":\"text\"},{\"name\":\"app_tier\",\"type\":\"string\",\"optional\":false,\"label\":\"APP_TIER\",\"control_type\":\"text\"}]", "parameters": {"schema": "[]"}, "sql": "select final_table.title, final_table.category, app_tier\nfrom product.workato_usage.applications_snapshot final_table\nleft join product.plg.recipe_sophistication_app_tier\non final_table.title = recipe_sophistication_app_tier.title   \nand final_table.entry_date = (current_date - 1)\nwhere \n    final_table.category = 'app'\n    and app_tier in ('1','2','3','4')\n    and final_table.title not ilike '%secondary%'\ngroup by all", "update_only": "false"}, "block": []}, {"number": 3, "keyword": "action", "provider": "lookup_table", "name": "search_entries", "as": "9f4b85c7", "skip": false, "input": {"lookup_table_id": "3300543", "parameters": {"col2": "app"}}, "block": []}, {"number": 4, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"39b44e18\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}", "operand": "not_equals_to", "rhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"9f4b85c7\",\"path\":[\"entries\", {\"path_element_type\": \"size\"}]}')}"}], "operand": "and", "type": "compound"}, "block": [{"number": 5, "keyword": "foreach", "provider": "", "name": "", "as": "e111e4a7", "skip": false, "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"39b44e18\",\"path\":[\"rows\"]}')}"}, "repeat_mode": "simple", "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"39b44e18\",\"path\":[\"rows\"]}')}", "block": [{"number": 6, "keyword": "action", "provider": "lookup_table", "name": "search_entries", "as": "3d6a002e", "skip": false, "input": {"lookup_table_id": "3300543", "parameters": {"col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"e111e4a7\",\"path\":[\"title\"]}')}"}}, "block": []}, {"number": 7, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"3d6a002e\",\"path\":[\"entries\", {\"path_element_type\": \"size\"}]}')}", "operand": "equals_to", "rhs": "0"}], "operand": "and", "type": "compound"}, "block": [{"number": 8, "keyword": "action", "provider": "lookup_table", "name": "add_entry", "as": "78b012f3", "skip": false, "input": {"lookup_table_id": "3300543", "parameters": {"col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"e111e4a7\",\"path\":[\"title\"]}')}", "col2": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"e111e4a7\",\"path\":[\"category\"]}')}", "col3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"e111e4a7\",\"path\":[\"app_tier\"]}')}"}}, "block": []}]}]}]}, {"number": 9, "keyword": "stop", "provider": "", "name": "", "as": "aa772329", "skip": false, "input": {"stop_with_error": "false"}, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (SQL_STEP_AS, "snowflake", "run_custom_sql"),
    (BASELINE_SEARCH_AS, "lookup_table", "search_entries"),
    (INNER_SEARCH_AS, "lookup_table", "search_entries"),
    (ADD_STEP_AS, "lookup_table", "add_entry"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "lookup_table.search_entries",
    "lookup_table.add_entry",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "lookup_table.search_entries",
    "lookup_table.add_entry",
]
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "sql_rows",
    "baseline_entry_count",
    "added_entries",
    "final_lookup_rows",
    "stopped",
)
SQL_ROW_KEYS = ("title", "category", "app_tier")
MAX_EXPECTED_SQL_ROWS = 1
LOOKUP_ROW_KEYS = ("col1", "col2", "col3")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIER_VALUES = ("1", "2", "3", "4")


def validate_120099421(raw: dict[str, Any]) -> dict[str, Any]:
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
    # Semantic pins on the drift-prone bits (the tree pin holds the exact
    # bytes; these name the trap when one changes).
    sql_node = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == SQL_STEP_AS), None
    )
    if not isinstance(sql_node, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} snowflake step {SQL_STEP_AS} missing")
    if str((sql_node.get("input") or {}).get("sql") or "") != RAW_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} custom SQL changed")
    for token in ("current_date - 1", "group by all", "not ilike '%secondary%'"):
        if token not in RAW_SQL:
            raise RuntimeError(f"recipe {RECIPE_ID} SQL lost load-bearing clause {token!r}")
    for node in _walk_nodes(raw):
        if node.get("provider") == "lookup_table":
            table = str((node.get("input") or {}).get("lookup_table_id") or "")
            if table != LOOKUP_TABLE_ID:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} lookup step {node.get('as')!r} targets table "
                    f"{table!r}, expected {LOOKUP_TABLE_ID!r}"
                )
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "lookup_table_id": LOOKUP_TABLE_ID,
        "snowflake_tables": [SNAPSHOT_TABLE, TIER_TABLE],
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


def seed_120099421(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_120099421(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (the scheduler tick "
            f"is payload-less and never dereferenced): {trigger!r}"
        )
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no try/catch: forced action errors would fail the "
            "whole run instead of exercising a recipe branch"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["lookup_table", "snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the lookup_table and "
            f"snowflake_live sections; got {sorted(seed_in.keys())}"
        )
    _require_snowflake_section(seed_in["snowflake_live"])
    lookup_rows = _require_lookup_section(seed_in["lookup_table"])
    expect = data.get("expect")
    _require_expect_shape(expect, lookup_rows)
    provision = ctx.tools.call(
        "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "lookup_table": deepcopy(seed_in["lookup_table"]),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_120099421(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_120099421(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
    raw_execution: dict[str, Any] | None = None
    initial_snapshot: dict[str, Any] = {}
    final_snapshot: dict[str, Any] = {}
    cleanup: dict[str, Any] | None = None
    try:
        initial_snapshot = _snapshot(ctx)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx)
    finally:
        # Required cleanup: the seeder create-or-replaced BOTH registered live
        # tables; drop them whether or not the run completed. The lookup table
        # is the per-variant Workato-internal mock (no cleanup required).
        cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    if not (cleanup or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake cleanup failed: {cleanup}")
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
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
            "cleanup_response": {"snowflake_live": cleanup},
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_120099421(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_snowflake_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["current_time", "tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly "
            "{'tables': ..., 'current_time': ...} (the SQL pins current_date)"
        )
    current_time = str(section.get("current_time") or "")
    try:
        datetime.datetime.fromisoformat(current_time.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.current_time must be an ISO "
            f"datetime: {current_time!r}"
        ) from exc
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted([SNAPSHOT_TABLE, TIER_TABLE]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{SNAPSHOT_TABLE!r} and {TIER_TABLE!r} (the literal 3-part SQL names)"
        )
    for table, expected_columns in ((SNAPSHOT_TABLE, SNAPSHOT_COLUMNS), (TIER_TABLE, TIER_COLUMNS)):
        spec = tables[table]
        if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {table} spec must be exactly "
                "{'columns': ..., 'rows': ...}"
            )
        if spec["columns"] != expected_columns:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {table} must declare exactly the columns "
                f"{expected_columns}"
            )
        rows = spec["rows"]
        if not isinstance(rows, list):
            raise RuntimeError(f"recipe {RECIPE_ID} table {table} rows must be a list")
        for idx, row in enumerate(rows):
            if not isinstance(row, dict) or sorted(row.keys()) != sorted(expected_columns.keys()):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table} row {idx} must fill exactly "
                    f"{sorted(expected_columns.keys())}; got {row!r}"
                )
            for column in expected_columns:
                value = row[column]
                if column == "ENTRY_DATE":
                    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
                        raise RuntimeError(
                            f"recipe {RECIPE_ID} table {table} row {idx} ENTRY_DATE must be "
                            f"YYYY-MM-DD; got {value!r}"
                        )
                elif not isinstance(value, str) or not value.strip():
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} table {table} row {idx} {column} must be a "
                        f"non-empty string; got {value!r}"
                    )


def _require_lookup_section(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table must be exactly {{'tables': ...}}"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [LOOKUP_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must declare exactly table "
            f"{LOOKUP_TABLE_ID!r} (rows may be an explicit empty list)"
        )
    rows = tables[LOOKUP_TABLE_ID]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} lookup table rows must be a list")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(LOOKUP_ROW_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} lookup row {idx} must fill exactly "
                f"{sorted(LOOKUP_ROW_KEYS)}; got {row!r}"
            )
        for key in LOOKUP_ROW_KEYS:
            if not isinstance(row[key], str) or not row[key].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} lookup row {idx}.{key} must be a non-empty string"
                )
    return rows


def _require_expect_shape(expect: Any, lookup_rows: list[dict[str, Any]]) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if expect.get("stopped") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the top-level STOP always executes: expect.stopped must "
            "be true in every variant"
        )
    sql_rows = expect.get("sql_rows")
    if (
        not isinstance(sql_rows, list)
        or len(sql_rows) > MAX_EXPECTED_SQL_ROWS
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.sql_rows must be a list of AT MOST ONE row: the "
            "SQL has no ORDER BY, so multi-row foreach trace order is not deterministic "
            "groundtruth (drive size mismatches from the lookup side instead)"
        )
    for row in sql_rows:
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(SQL_ROW_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.sql_rows rows must carry exactly "
                f"{sorted(SQL_ROW_KEYS)}; got {row!r}"
            )
        if row["app_tier"] not in _TIER_VALUES:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.sql_rows app_tier must survive the IN "
                f"filter {_TIER_VALUES}; got {row['app_tier']!r}"
            )
    baseline = expect.get("baseline_entry_count")
    seeded_app_entries = [row for row in lookup_rows if row["col2"] == "app"]
    if baseline != len(seeded_app_entries):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.baseline_entry_count must equal the number of "
            f"seeded col2='app' lookup rows ({len(seeded_app_entries)}); got {baseline!r}"
        )
    added = expect.get("added_entries")
    if not isinstance(added, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.added_entries must be a list")
    seeded_titles = {row["col1"] for row in lookup_rows}
    sizes_differ = len(sql_rows) != baseline
    expected_tools = ["snowflake.run_custom_sql", "lookup_table.search_entries"]
    expected_added: list[dict[str, Any]] = []
    if sizes_differ:
        for row in sql_rows:
            expected_tools.append("lookup_table.search_entries")
            if row["title"] not in seeded_titles:
                expected_tools.append("lookup_table.add_entry")
                expected_added.append(
                    {"col1": row["title"], "col2": row["category"], "col3": row["app_tier"]}
                )
    if added != expected_added:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.added_entries is inconsistent with the seeded "
            f"branch: expected {expected_added}, got {added!r}"
        )
    if expect.get("tools") != expected_tools:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools is inconsistent with the seeded branch: "
            f"expected {expected_tools}, got {expect.get('tools')!r}"
        )
    if expect.get("executed_action_count") != len(expected_tools):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.executed_action_count must be "
            f"{len(expected_tools)}; got {expect.get('executed_action_count')!r}"
        )
    expected_final = [dict(row) for row in lookup_rows] + expected_added
    if expect.get("final_lookup_rows") != expected_final:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_lookup_rows must be the seeded rows plus "
            f"the added entries in order: expected {expected_final}, got "
            f"{expect.get('final_lookup_rows')!r}"
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
