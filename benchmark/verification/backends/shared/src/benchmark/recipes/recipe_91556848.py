from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_91556848


RECIPE_ID = "91556848"
SEED_TYPE = "slack_dynamic_menu_sfbot_record_list_variant"
TRACK = "live_snowflake_slack_dynamic_menu_sfbot_record_list"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "dynamic_menu"
TRIGGER_AS = "6f2a4ce9"
DYNAMIC_MENU_NAME = "List of Records"
LOOKUP_STEP_AS = "7345c7be"
SQL_STEP_AS = "41c16eb0"
CATCH_AS = "9e7ca880"
MENU_STEP_AS = "a20f9927"
LOOKUP_TABLE_ID = "355280"
# The SQL text the trace must carry after pill interpolation: the lookup
# entry's col2 (display field) lands in the SELECT alias position, the trigger
# `type` lands in the FROM clause, and the connector's SEPARATE Order-by input
# ('display_name') is APPENDED by the engine (raw_executor
# snowflake_search_rows_sql; re-probed on this tree). :search_term stays a
# bind. The connector limit '10000' rides along and the live client appends
# it AFTER the appended ORDER BY (LIMIT-last, valid Snowflake).
RESOLVED_SQL_TEMPLATE = (
    "select\n  {col2} display_name,\n  id\nfrom salesforce.{type}\n"
    "where lower(display_name) like lower(:search_term) ORDER BY display_name"
)

# slack_bot.dynamic_menu 'List of Records' (as 6f2a4ce9): parameters {type
# required} + typeahead.value. Body:
#   TRY (2):
#     3 lookup_table.get_entry 7345c7be (mock table 355280 '[SFBOT] Objects',
#       cols col1=Object..col6=Object Detail SQL) parameters
#       {col1: #{parameters.type}} -> entry.col2 = the object's display field.
#     4 snowflake.search_rows_sql 41c16eb0 (LIVE): DYNAMICALLY COMPOSED SQL
#       'select #{entry.col2} display_name, id from salesforce.#{type} where
#       lower(display_name) like lower(:search_term)' + connector orderby
#       'display_name' (appended) + limit '10000'; bind search_term =
#       '%#{typeahead.value}%' (case preserved - lower() runs in Snowflake).
#       display_name in the WHERE is a Snowflake LATERAL column alias
#       (triage-verified live).
#   CATCH 5 (as 9e7ca880, max_retry_count 3):
#     6 stop (stop_with_error true, stop_reason #{catch.9e7ca880.message}).
#       The engine records only the bare stop marker {number 6, stopped true}
#       (stop_reason is never evaluated; re-probed) and `stopped` prevents
#       step 7.
#   7 slack_bot.generate_menu_options a20f9927 (AFTER the try): options
#     ____source over rows; label <- rows[current_item].display_name_431ff3ca,
#     value <- rows[current_item].id_b497e547 - HASH-SUFFIXED pill names that
#     resolve over the live row keys only via the `_<8-hex>` strip +
#     case-insensitive retry (raw_executor; re-probed).
#
# Branch mapping (offline dry-replay re-probed on this tree, 2026-07-08):
# - happy (3 actions): get_entry -> live SELECT -> menu; the appended ORDER BY
#   display_name pins EXACT option order (seed display values must be distinct
#   ASCII so Python sort == Snowflake binary collation); zero matches -> [].
# - catch_stop (1 action): seed.force_action_error on 41c16eb0 raises BEFORE
#   the live adapter -> catch payload {type RawRecipeExecutionError, message}
#   -> stop; generate_menu_options NEVER executes; the variant owns NO live
#   state (no snowflake seed, no snapshots, no cleanup call).
#
# Backends: Snowflake runs LIVE (create-or-replace seed of the single
# 2-part-named table salesforce.<type> -> <DB>.SALESFORCE.<TYPE>, dropped in
# the runner's finally; READ-ONLY - no writes). lookup_table 355280 is
# Workato-internal (mock). The SQL uses no time functions, so current_time
# must NOT be declared. Same hash-suffix + orderby-append class as the
# registered precedent recipe_122406899.

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "slack_bot", "name": "dynamic_menu", "as": "6f2a4ce9", "skip": false, "input": {"dynamic_menu_name": "List of Records", "parameters": "[\n  {\n    \"name\": \"type\",\n    \"type\": \"string\",\n    \"optional\": false,\n    \"control_type\": \"text\",\n    \"label\": \"Type\"\n  }\n]"}, "block": [{"number": 2, "keyword": "try", "provider": "", "name": "", "as": "", "skip": false, "input": {}, "block": [{"number": 3, "keyword": "action", "provider": "lookup_table", "name": "get_entry", "as": "7345c7be", "skip": false, "input": {"lookup_table_id": "355280", "parameters": {"col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"6f2a4ce9\",\"path\":[\"parameters\", \"type\"]}')}"}}, "block": []}, {"number": 4, "keyword": "action", "provider": "snowflake", "name": "search_rows_sql", "as": "41c16eb0", "skip": false, "input": {"limit": "10000", "orderby": "display_name", "output_schema": "[{\"name\":\"display_name\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Display name\"},{\"name\":\"id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"ID\"}]", "parameters": {"data": {"search_term": "%#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"6f2a4ce9\",\"path\":[\"typeahead\", \"value\"]}')}%"}, "schema": "[{\"name\":\"search_term\",\"type\":\"string\",\"optional\":true,\"label\":\"search_term\",\"control_type\":\"text\"}]"}, "sql": "select\n  #{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"7345c7be\",\"path\":[\"entry\", \"col2\"]}')} display_name,\n  id\nfrom salesforce.#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"6f2a4ce9\",\"path\":[\"parameters\", \"type\"]}')}\nwhere lower(display_name) like lower(:search_term)"}, "block": []}, {"number": 5, "keyword": "catch", "provider": "", "name": "", "as": "9e7ca880", "skip": false, "input": {"max_retry_count": "3", "retry_interval": "1"}, "block": [{"number": 6, "keyword": "stop", "provider": "", "name": "", "as": "", "skip": false, "input": {"stop_reason": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"9e7ca880\",\"path\":[\"message\"]}')}", "stop_with_error": "true"}, "block": []}]}]}, {"number": 7, "keyword": "action", "provider": "slack_bot", "name": "generate_menu_options", "as": "a20f9927", "skip": false, "input": {"options": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"41c16eb0\",\"path\":[\"rows\"]}')}", "label": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"41c16eb0\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"display_name_431ff3ca\"]}')}", "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"41c16eb0\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"id_b497e547\"]}')}"}, "use_option_groups": "false"}, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[int, str, str, str]] = [
    (3, LOOKUP_STEP_AS, "lookup_table", "get_entry"),
    (4, SQL_STEP_AS, "snowflake", "search_rows_sql"),
    (7, MENU_STEP_AS, "slack_bot", "generate_menu_options"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.get_entry",
    "snowflake.search_rows_sql",
    "slack_bot.generate_menu_options",
]
ALLOWED_TOOLS: list[str] = list(EXPECTED_RAW_TOOLS)
REQUIRED_EXPECT_KEYS = (
    "branch",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "resolved_sql",
    "search_term",
    "menu_options",
    "stopped",
    "catch_message",
)
BRANCHES = ("typeahead_match", "multi_match_ordering", "zero_match_empty_menu", "catch_stop")
_EXPECT_ITEM_KEYS = {
    "tool", "table_id", "lookup_table_id", "match_fields", "channel",
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
}
_EXPECT_VALUE_KEYS = {
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
}
# `type` interpolates into the FROM clause and must equal the seeded 2-part
# table's second component; keep it a plain lowercase identifier.
_TYPE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
# typeahead.value feeds the LIKE bind as '%<value>%': quotes, backslashes and
# LIKE wildcards (%/_) are rejected so groundtruth stays a plain substring
# match; ASCII-only so Python ordering == Snowflake binary collation.
_TYPEAHEAD_RE = re.compile(r"^[A-Za-z0-9 .@\-]+$")
_ASCII_VALUE_RE = re.compile(r"^[\x20-\x7e]+$")
LOOKUP_COLUMNS = ("col1", "col2", "col3", "col4", "col5", "col6")


def validate_91556848(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    if str((raw.get("input") or {}).get("dynamic_menu_name") or "") != DYNAMIC_MENU_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} dynamic menu name changed")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    # Semantic pins over the drift-prone bits (the tree pin holds the bytes;
    # these name the trap when one changes).
    lookup = next(node for node in _walk_nodes(raw) if str(node.get("as") or "") == LOOKUP_STEP_AS)
    lookup_input = lookup.get("input") or {}
    if str(lookup_input.get("lookup_table_id") or "") != LOOKUP_TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} lookup table id changed")
    col1 = str((lookup_input.get("parameters") or {}).get("col1") or "")
    if '"path\":[\"parameters\", \"type\"]' not in col1.replace("\\", ""):
        raise RuntimeError(f"recipe {RECIPE_ID} lookup col1 no longer binds parameters.type: {col1!r}")
    sql_node = next(node for node in _walk_nodes(raw) if str(node.get("as") or "") == SQL_STEP_AS)
    sql_input = sql_node.get("input") or {}
    sql = str(sql_input.get("sql") or "")
    if "salesforce.#{" not in sql or '["entry", "col2"]' not in sql:
        raise RuntimeError(
            f"recipe {RECIPE_ID} dynamic SQL composition changed (FROM-clause type pill / "
            f"lookup col2 alias pill): {sql!r}"
        )
    if re.search(r"\bORDER\s+BY\b", sql, flags=re.I):
        raise RuntimeError(
            f"recipe {RECIPE_ID} raw SQL grew an ORDER BY -- the connector orderby-append "
            "analysis no longer holds"
        )
    if str(sql_input.get("orderby") or "") != "display_name":
        raise RuntimeError(f"recipe {RECIPE_ID} connector orderby changed: {sql_input.get('orderby')!r}")
    if str(sql_input.get("limit") or "") != "10000":
        raise RuntimeError(f"recipe {RECIPE_ID} connector limit changed")
    term = str(((sql_input.get("parameters") or {}).get("data") or {}).get("search_term") or "")
    if not (term.startswith("%") and term.endswith("%") and "typeahead" in term):
        raise RuntimeError(f"recipe {RECIPE_ID} search_term bind changed: {term!r}")
    menu = next(node for node in _walk_nodes(raw) if str(node.get("as") or "") == MENU_STEP_AS)
    options = (menu.get("input") or {}).get("options") or {}
    if "display_name_431ff3ca" not in str(options.get("label")) or "id_b497e547" not in str(options.get("value")):
        raise RuntimeError(
            f"recipe {RECIPE_ID} hash-suffixed pill names changed -- the `_<8-hex>` "
            f"strip-fallback analysis no longer holds: {options!r}"
        )
    control = {
        (str(node.get("keyword") or ""), int(node.get("number") or 0)): node
        for node in _walk_nodes(raw)
        if node.get("keyword") in {"try", "catch", "if", "foreach", "stop", "else"}
    }
    if sorted(control) != [("catch", 5), ("stop", 6), ("try", 2)]:
        raise RuntimeError(f"recipe {RECIPE_ID} control nodes changed: {sorted(control)}")
    if str(control[("catch", 5)].get("as") or "") != CATCH_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} catch step id changed")
    stop_input = control[("stop", 6)].get("input") or {}
    if str(stop_input.get("stop_with_error")) != "true" or CATCH_AS not in str(stop_input.get("stop_reason")):
        raise RuntimeError(f"recipe {RECIPE_ID} stop step changed: {stop_input!r}")
    actions = _collect_actions(raw)
    actual = [
        (a.get("number"), str(a.get("as")), str(a.get("provider")), str(a.get("name")))
        for a in actions
    ]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "dynamic_menu_name": DYNAMIC_MENU_NAME,
        "lookup_table_id": LOOKUP_TABLE_ID,
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


def seed_91556848(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_91556848(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    object_type, typeahead = _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    expect = data.get("expect")
    _require_expect_common(expect)
    force = data.get("force_action_error")
    _require_force_shape(force, expect)
    lookup_section = seed_in.get("lookup_table")
    col2 = _require_lookup_section(lookup_section, object_type)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": deepcopy(expect),
        "lookup_table": deepcopy(lookup_section),
    }
    if force is not None:
        # CATCH branch: the forced error fires BEFORE the snowflake adapter
        # runs, so this variant owns no live resources and must not seed any.
        if sorted(seed_in.keys()) != ["lookup_table"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants seed exactly the lookup_table "
                f"section (nothing runs against Snowflake); got {sorted(seed_in.keys())}"
            )
        _require_catch_expect(expect, force, object_type)
    else:
        if sorted(seed_in.keys()) != ["lookup_table", "snowflake_live"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} non-catch variants seed exactly lookup_table + "
                f"snowflake_live; got {sorted(seed_in.keys())}"
            )
        rows = _require_snowflake_section(seed_in["snowflake_live"], object_type, col2)
        _require_happy_expect(expect, object_type, col2, typeahead, rows)
        provision = ctx.tools.call(
            "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
        )
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
        out["snowflake_live"] = deepcopy(provision["state"])
        out["snowflake_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_91556848(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_91556848(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed carries no lookup_table state")
    live = isinstance(seed.get("snowflake_live"), dict)
    raw_execution: dict[str, Any] | None = None
    initial_snapshot: dict[str, Any] = {}
    final_snapshot: dict[str, Any] = {}
    cleanup: dict[str, Any] | None = None
    try:
        if live:
            initial_snapshot = dict(ctx.tools.call("harness.snowflake.snapshot", {}))
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        if live:
            final_snapshot = dict(ctx.tools.call("harness.snowflake.snapshot", {}))
    finally:
        if live:
            # The salesforce.<type> table is benchmark-owned create-or-replace
            # live state: drop it even when execution fails (cleanup
            # principle). Catch variants own no live state.
            cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    if live and not (cleanup or {}).get("ok", False):
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
    result["verifier"] = verify_91556848(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> tuple[str, str]:
    if sorted(trigger.keys()) != ["parameters", "typeahead"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly parameters + typeahead; "
            f"got {sorted(trigger.keys())}"
        )
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict) or sorted(parameters.keys()) != ["type"]:
        raise RuntimeError(f"recipe {RECIPE_ID} parameters must carry exactly 'type'")
    object_type = parameters.get("type")
    if not isinstance(object_type, str) or not _TYPE_RE.fullmatch(object_type):
        raise RuntimeError(
            f"recipe {RECIPE_ID} parameters.type interpolates into the FROM clause "
            f"(salesforce.<type>): only a plain lowercase identifier is accepted; "
            f"got {object_type!r}"
        )
    typeahead = trigger.get("typeahead")
    if (
        not isinstance(typeahead, dict)
        or sorted(typeahead.keys()) != ["value"]
        or not isinstance(typeahead.get("value"), str)
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} typeahead must be {{'value': <str>}}")
    value = typeahead["value"]
    if not _TYPEAHEAD_RE.fullmatch(value):
        raise RuntimeError(
            f"recipe {RECIPE_ID} typeahead.value feeds the LIKE bind as '%<value>%': "
            f"it must be non-empty without quotes/backslashes/LIKE wildcards; got {value!r}"
        )
    return object_type, value


def _require_expect_common(expect: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if expect.get("branch") not in BRANCHES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch must be one of {BRANCHES}")
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or not items:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must be a non-empty list")
    for item in items:
        if not isinstance(item, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} tool expectation must be an object: {item!r}")
        unknown = sorted(set(item) - _EXPECT_ITEM_KEYS)
        if unknown:
            raise RuntimeError(f"recipe {RECIPE_ID} tool expectation has undeclared keys: {unknown}")
        if not (set(item) & _EXPECT_VALUE_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} every tool expectation must carry at least one "
                f"value-asserting key ({sorted(_EXPECT_VALUE_KEYS)}): {item!r}"
            )


def _require_force_shape(force: Any, expect: dict[str, Any]) -> None:
    catch = expect.get("branch") == "catch_stop"
    if force is None:
        if catch:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch_stop requires force_action_error on the "
                f"snowflake step (the only deterministic failure inside the TRY)"
            )
        return
    if not catch:
        raise RuntimeError(f"recipe {RECIPE_ID} only catch_stop variants may force an error")
    if not isinstance(force, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error must be an object")
    if str(force.get("step_as") or "") != SQL_STEP_AS or not str(force.get("error") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error must target step_as {SQL_STEP_AS!r} "
            "with an explicit error message"
        )


def _require_lookup_section(section: Any, object_type: str) -> str:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table must be exactly {{'tables': ...}}"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [LOOKUP_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must declare exactly "
            f"table {LOOKUP_TABLE_ID!r} ('[SFBOT] Objects')"
        )
    rows = tables[LOOKUP_TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"recipe {RECIPE_ID} lookup table {LOOKUP_TABLE_ID} must carry rows")
    col1_values: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != set(LOOKUP_COLUMNS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} every lookup row must fill exactly col1..col6 "
                f"(the '[SFBOT] Objects' schema): {row!r}"
            )
        for key in ("col1", "col2"):
            if not isinstance(row[key], str) or not row[key].strip():
                raise RuntimeError(f"recipe {RECIPE_ID} lookup row {key} must be non-empty: {row!r}")
        for key in ("col3", "col4", "col5", "col6"):
            if not isinstance(row[key], str):
                raise RuntimeError(f"recipe {RECIPE_ID} lookup row {key} must be a string: {row!r}")
        col1_values.append(row["col1"])
    if len(set(col1_values)) != len(col1_values):
        raise RuntimeError(f"recipe {RECIPE_ID} lookup col1 values must be distinct (get_entry match key)")
    matches = [row for row in rows if row["col1"] == object_type]
    if len(matches) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} parameters.type {object_type!r} must match exactly one "
            f"lookup row's col1 (a miss renders entry.col2 as '' and composes invalid "
            f"live SQL -- never author that); got {len(matches)}"
        )
    col2 = str(matches[0]["col2"])
    if not _TYPE_RE.fullmatch(col2):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the matched row's col2 lands in the SELECT alias "
            f"position: only a plain lowercase identifier is accepted; got {col2!r}"
        )
    return col2


def _require_snowflake_section(section: Any, object_type: str, col2: str) -> list[dict[str, Any]]:
    table_key = f"salesforce.{object_type}"
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the SQL uses no time functions -> current_time must NOT be declared)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [table_key]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{table_key!r} (the 2-part name the composed SQL references)"
        )
    spec = tables[table_key]
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table spec must be exactly {{'columns': ..., 'rows': ...}}"
        )
    expected_columns = {col2.upper(): "string", "ID": "string"}
    if spec["columns"] != expected_columns:
        raise RuntimeError(
            f"recipe {RECIPE_ID} {table_key} columns must be exactly {expected_columns} "
            f"(col2 drives the SELECT alias; got {spec['columns']!r})"
        )
    rows = spec["rows"]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} {table_key} rows must be a list")
    displays: list[str] = []
    ids: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != set(expected_columns):
            raise RuntimeError(
                f"recipe {RECIPE_ID} every row must fill exactly the declared columns: {row!r}"
            )
        display = row[col2.upper()]
        record_id = row["ID"]
        for value in (display, record_id):
            if not isinstance(value, str) or not _ASCII_VALUE_RE.fullmatch(value):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} row values must be non-empty printable-ASCII "
                    f"strings (Python sort must equal Snowflake binary collation): {row!r}"
                )
        displays.append(display)
        ids.append(record_id)
    if len(set(displays)) != len(displays):
        raise RuntimeError(
            f"recipe {RECIPE_ID} display values must be distinct (the appended ORDER BY "
            "display_name pins exact option order; ties would be nondeterministic)"
        )
    if len(set(ids)) != len(ids):
        raise RuntimeError(f"recipe {RECIPE_ID} ids must be distinct")
    return [dict(row) for row in rows]


def _derive_menu_options(rows: list[dict[str, Any]], col2: str, typeahead: str) -> list[dict[str, Any]]:
    """Groundtruth of the live SELECT + menu render: rows whose display value
    contains the typeahead case-insensitively (lower() on both LIKE arms),
    ordered by display value (Snowflake binary collation == Python codepoint
    sort for the enforced ASCII values)."""
    needle = typeahead.lower()
    matches = [row for row in rows if needle in str(row[col2.upper()]).lower()]
    ordered = sorted(matches, key=lambda row: str(row[col2.upper()]))
    return [{"label": str(row[col2.upper()]), "value": str(row["ID"])} for row in ordered]


def _require_happy_expect(
    expect: dict[str, Any],
    object_type: str,
    col2: str,
    typeahead: str,
    rows: list[dict[str, Any]],
) -> None:
    branch = expect["branch"]
    derived_options = _derive_menu_options(rows, col2, typeahead)
    if branch == "zero_match_empty_menu":
        if derived_options:
            raise RuntimeError(
                f"recipe {RECIPE_ID} zero_match_empty_menu must seed rows that do NOT "
                f"match the typeahead; derived {derived_options!r}"
            )
    elif branch == "multi_match_ordering":
        if len(derived_options) < 2:
            raise RuntimeError(
                f"recipe {RECIPE_ID} multi_match_ordering needs at least 2 matching rows "
                f"(the appended ORDER BY is the observable); derived {derived_options!r}"
            )
    elif branch == "typeahead_match":
        if len(derived_options) != 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} typeahead_match must derive exactly 1 option; "
                f"got {derived_options!r}"
            )
    else:
        raise RuntimeError(f"recipe {RECIPE_ID} {branch} is not a happy branch")
    resolved_sql = RESOLVED_SQL_TEMPLATE.format(col2=col2, type=object_type)
    search_term = f"%{typeahead}%"
    checks = (
        expect.get("executed_action_count") == 3,
        expect.get("tools") == EXPECTED_RAW_TOOLS,
        expect.get("resolved_sql") == resolved_sql,
        expect.get("search_term") == search_term,
        expect.get("menu_options") == derived_options,
        expect.get("stopped") is False,
        expect.get("catch_message") is None,
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} {branch} expect block contradicts the derived "
            f"groundtruth (resolved_sql {resolved_sql!r}, search_term {search_term!r}, "
            f"menu_options {derived_options!r}): {expect!r}"
        )
    expected_items = [
        {
            "tool": "lookup_table.get_entry",
            "lookup_table_id": LOOKUP_TABLE_ID,
            "args_contains": {
                "lookup_table_id": LOOKUP_TABLE_ID,
                "parameters": {"col1": object_type},
            },
        },
        {
            "tool": "snowflake.search_rows_sql",
            "args_contains": {
                "sql": resolved_sql,
                "limit": "10000",
                "parameters": {"search_term": search_term},
            },
            "result_count": len(derived_options),
        },
        {
            "tool": "slack_bot.generate_menu_options",
            "options_contains": deepcopy(derived_options),
            "result_count": len(derived_options),
        },
    ]
    if expect.get("tool_expectations") != expected_items:
        raise RuntimeError(
            f"recipe {RECIPE_ID} {branch} tool_expectations must pin exactly the derived "
            f"lookup/sql/menu triple; expected {expected_items!r}, got "
            f"{expect.get('tool_expectations')!r}"
        )


def _require_catch_expect(expect: dict[str, Any], force: dict[str, Any], object_type: str) -> None:
    checks = (
        expect.get("executed_action_count") == 1,
        expect.get("tools") == ["lookup_table.get_entry"],
        expect.get("resolved_sql") is None,
        expect.get("search_term") is None,
        expect.get("menu_options") is None,
        expect.get("stopped") is True,
        expect.get("catch_message") == force.get("error"),
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch_stop expect block is inconsistent (1 action = "
            f"the lookup only, stopped true, catch_message == the forced error, null "
            f"sql/menu pins): {expect!r}"
        )
    expected_items = [
        {
            "tool": "lookup_table.get_entry",
            "lookup_table_id": LOOKUP_TABLE_ID,
            "args_contains": {
                "lookup_table_id": LOOKUP_TABLE_ID,
                "parameters": {"col1": object_type},
            },
        },
    ]
    if expect.get("tool_expectations") != expected_items:
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch_stop tool_expectations must pin exactly the "
            f"lookup call; expected {expected_items!r}, got {expect.get('tool_expectations')!r}"
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
