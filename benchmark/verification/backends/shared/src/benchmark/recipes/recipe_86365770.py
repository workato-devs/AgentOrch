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
from ..verifier import verify_86365770


RECIPE_ID = "86365770"
SEED_TYPE = "snowflake_membership_reversal_daily_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "20be9af8"
SELECT_STEP_AS = "5bdff6c3"
UPDATE_STEP_AS = "d0df7fcd"
FOREACH_AS = "e7ea675a"
CATCH_AS = "eb032286"
ADJ_TABLE = "PUBLIC.WORKSPACE_FEATURES_ADJ_LOG"
REQ_TABLE = "PUBLIC.WORKSPACE_REQ_LOG"
EMP_TABLE = "PUBLIC.EMPLOYEE"
RAW_SELECT_SQL = (
    "SELECT\nW.ID AS REQUEST_ID,\nF.KEY,\nF.TYPE,\nF.OLD_VALUE,\nF.NEW_VALUE\n\n"
    "FROM PUBLIC.WORKSPACE_FEATURES_ADJ_LOG F\nJOIN PUBLIC.WORKSPACE_REQ_LOG W\n"
    "ON W.ID = F.REQUEST_ID\n    \nJOIN PUBLIC.EMPLOYEE R\nON W.REQUESTER_ID = R.ID\n\n"
    "WHERE F.STATUS = 'Adjusted'\nAND W.STATUS = 'Pending Next Action'\n"
    "AND W.NEXT_ACTION = 'Features Adjustment'\nAND F.KEY = 'membership_id'\n"
    "AND F.OLD_VALUE = 'premium_yearly'\n\nORDER BY RIGHT(W.ID, LEN(W.ID)-1)::INT DESC"
)

# clock.scheduled_event (as 20be9af8, daily 22:00) — payload-less; the trigger
# output is never dereferenced (the recipe reads only `now`). Body = one TRY:
#   3  snowflake.search_rows_sql 5bdff6c3 (LIVE): 3-way join
#      WORKSPACE_FEATURES_ADJ_LOG F x WORKSPACE_REQ_LOG W x EMPLOYEE R —
#      Adjusted membership_id/premium_yearly rows whose request is
#      'Pending Next Action'/'Features Adjustment'; ORDER BY
#      RIGHT(W.ID, LEN(W.ID)-1)::INT DESC (W.ID must be letter+digits so the
#      cast succeeds), limit 50000
#   FOREACH 4 (e7ea675a over rows, repeat_mode simple):
#     5  snowflake.update_rows d0df7fcd (LIVE): SET modified_at =
#        =now.in_time_zone("Etc/UTC"), old_value = 'free' WHERE
#        REQUEST_ID = '#{foreach.request_id}' AND STATUS = 'Adjusted' AND
#        KEY = 'membership_id' AND OLD_VALUE = 'premium_yearly'
#     IF 6 (d0df7fcd rows_updated not_equals_to '1'):
#       7  STOP (stop_with_error true; reason interpolates the where clause —
#          the engine's stop node never evaluates/records stop_reason)
#   CATCH 8 (eb032286, max_retry_count 0):
#     9  STOP (stop_with_error true; reason = catch.message — same
#        unevaluated-stop semantics; the catch payload is pinned via
#        step_outputs instead)
#
# ENGINE NOTE (batch-05 fix, re-probed on HEAD): snowflake_live.update_rows
# now returns the connector field name `rows_updated` alongside the legacy
# `updated`, so the IF at step 6 compares the REAL row count ("1" != '1' →
# False on a clean single-row update; "2" → the duplicate-request stop path).
#
# Backends: Snowflake runs LIVE (create-or-replace seed of the three PUBLIC.*
# tables; registered drops in the runner's finally). MODIFIED_AT is seeded
# VARCHAR so the =now.in_time_zone("Etc/UTC") render ('...+00:00') is pinned
# byte-exactly. The update WHERE uses unquoted identifiers only, so the
# live client's double-quoted-identifier rewrite leaves it verbatim.
#
# VERIFIER NOTE: no tool_expectations item may target snowflake.update_rows —
# the generic strict verifier parses single-clause WHEREs only and this
# recipe's WHERE is a 4-way AND; the per-recipe verifier pins the update
# call (where/columns/rows_updated) and the final live table state instead.

_RAW_PIN_JSON = r"""{"as": "20be9af8", "block": [{"as": "", "block": [{"as": "5bdff6c3", "block": [], "input": {"limit": "50000", "output_schema": "[{\"name\":\"REQUEST_ID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"REQUEST ID\"},{\"name\":\"KEY\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"KEY\"},{\"name\":\"TYPE\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"TYPE\"},{\"name\":\"OLD_VALUE\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"OLD VALUE\"},{\"name\":\"NEW_VALUE\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"NEW VALUE\"}]", "sql": "SELECT\nW.ID AS REQUEST_ID,\nF.KEY,\nF.TYPE,\nF.OLD_VALUE,\nF.NEW_VALUE\n\nFROM PUBLIC.WORKSPACE_FEATURES_ADJ_LOG F\nJOIN PUBLIC.WORKSPACE_REQ_LOG W\nON W.ID = F.REQUEST_ID\n    \nJOIN PUBLIC.EMPLOYEE R\nON W.REQUESTER_ID = R.ID\n\nWHERE F.STATUS = 'Adjusted'\nAND W.STATUS = 'Pending Next Action'\nAND W.NEXT_ACTION = 'Features Adjustment'\nAND F.KEY = 'membership_id'\nAND F.OLD_VALUE = 'premium_yearly'\n\nORDER BY RIGHT(W.ID, LEN(W.ID)-1)::INT DESC"}, "keyword": "action", "name": "search_rows_sql", "number": 3, "provider": "snowflake", "skip": false}, {"as": "e7ea675a", "block": [{"as": "d0df7fcd", "block": [], "input": {"columns": {"modified_at": "=now.in_time_zone(\"Etc/UTC\")", "old_value": "free"}, "table": "PUBLIC.WORKSPACE_FEATURES_ADJ_LOG", "where": "REQUEST_ID = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"e7ea675a\",\"path\":[\"request_id\"]}')}' AND STATUS = 'Adjusted' AND KEY = 'membership_id' AND OLD_VALUE = 'premium_yearly'"}, "keyword": "action", "name": "update_rows", "number": 5, "provider": "snowflake", "skip": false}, {"as": "", "block": [{"as": "", "block": [], "input": {"stop_reason": "Rows update failed: \nWHERE REQUEST_ID = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"e7ea675a\",\"path\":[\"request_id\"]}')}' AND STATUS = 'Adjusted' AND KEY = 'membership_id' AND OLD_VALUE = 'premium_yearly'", "stop_with_error": "true"}, "keyword": "stop", "name": "", "number": 7, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"d0df7fcd\",\"path\":[\"rows_updated\"]}')}", "operand": "not_equals_to", "rhs": "1"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 6, "provider": "", "skip": false}], "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5bdff6c3\",\"path\":[\"rows\"]}')}"}, "keyword": "foreach", "name": "", "number": 4, "provider": "", "repeat_mode": "simple", "skip": false, "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5bdff6c3\",\"path\":[\"rows\"]}')}"}, {"as": "eb032286", "block": [{"as": "", "block": [], "input": {"stop_reason": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"eb032286\",\"path\":[\"message\"]}')}", "stop_with_error": "true"}, "keyword": "stop", "name": "", "number": 9, "provider": "", "skip": false}], "input": {"max_retry_count": "0", "retry_interval": "2"}, "keyword": "catch", "name": "", "number": 8, "provider": "", "skip": false}], "input": {}, "keyword": "try", "name": "", "number": 2, "provider": "", "skip": false}], "input": {"time_unit": "days", "trigger_at": "22:00:00", "trigger_every": "1"}, "keyword": "trigger", "name": "scheduled_event", "number": 1, "provider": "clock", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (SELECT_STEP_AS, "snowflake", "search_rows_sql"),
    (UPDATE_STEP_AS, "snowflake", "update_rows"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "snowflake.update_rows",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "snowflake.update_rows",
]
ADJ_COLUMNS = {
    "REQUEST_ID": "string",
    "KEY": "string",
    "TYPE": "string",
    "OLD_VALUE": "string",
    "NEW_VALUE": "string",
    "STATUS": "string",
    "MODIFIED_AT": "string",
}
REQ_COLUMNS = {
    "ID": "string",
    "STATUS": "string",
    "NEXT_ACTION": "string",
    "REQUESTER_ID": "string",
}
EMP_COLUMNS = {"ID": "string"}
OUTCOMES = ("updated", "stop_duplicate", "noop", "catch_stop")
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "outcome",
    "select_rows",
    "update_calls",
    "stop_step_number",
    "catch_message",
    "final_adj_rows",
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
_W_ID_RE = re.compile(r"^[A-Za-z]\d+$")
_WHERE_RE = re.compile(
    r"^REQUEST_ID = '([A-Za-z]\d+)' AND STATUS = 'Adjusted' "
    r"AND KEY = 'membership_id' AND OLD_VALUE = 'premium_yearly'$"
)


def validate_86365770(raw: dict[str, Any]) -> dict[str, Any]:
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
    # Semantic pins on the drift-prone inputs (the tree pin holds exact bytes).
    for node in _walk_nodes(raw):
        step = str(node.get("as") or "")
        node_input = node.get("input") or {}
        if step == SELECT_STEP_AS:
            if node_input.get("sql") != RAW_SELECT_SQL or str(node_input.get("limit")) != "50000":
                raise RuntimeError(f"recipe {RECIPE_ID} select SQL changed")
        if step == UPDATE_STEP_AS:
            columns = node_input.get("columns") or {}
            if (
                columns.get("old_value") != "free"
                or columns.get("modified_at") != '=now.in_time_zone("Etc/UTC")'
                or node_input.get("table") != ADJ_TABLE
            ):
                raise RuntimeError(f"recipe {RECIPE_ID} update columns changed: {node_input}")
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


def seed_86365770(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_86365770(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (payload-less daily "
            f"clock tick; only `now` is read): {trigger!r}"
        )
    now = data.get("now")
    if not isinstance(now, str) or not now.endswith("+00:00"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must pin now as an explicit '+00:00' ISO "
            f"string (=now.in_time_zone(\"Etc/UTC\") render is pinned byte-exactly): {now!r}"
        )
    datetime.datetime.fromisoformat(now)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["snowflake_live"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed must declare exactly the snowflake_live section")
    _require_snowflake_section(seed_in["snowflake_live"], now)
    force = data.get("force_action_error")
    _require_force_shape(force)
    _require_expect_shape(data.get("expect"), force, now)
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
        "now": now,
        "expect": deepcopy(data["expect"]),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_86365770(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_86365770(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    if not str(seed.get("now") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing pinned now")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect"),
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    cleanup_response: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = _snapshot(ctx)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx)
    finally:
        # Required cleanup: all three PUBLIC.* tables are benchmark-owned live
        # objects (create-or-replace seed + registered drop), on every path
        # including the stop-with-error and catch branches.
        cleanup_response = ctx.tools.call("harness.snowflake_live.cleanup", {})
        details["cleanup_response"] = {"snowflake_live": cleanup_response}
    if not (cleanup_response or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake cleanup failed: {cleanup_response}")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_86365770(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_snowflake_section(section: Any, now: str) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["current_time", "tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly "
            "{'current_time': ..., 'tables': ...}"
        )
    if str(section["current_time"] or "") != now:
        raise RuntimeError(
            f"recipe {RECIPE_ID} snowflake_live.current_time must equal the pinned now "
            f"(one clock per run): {section['current_time']!r} != {now!r}"
        )
    tables = section["tables"]
    expected_tables = {ADJ_TABLE: ADJ_COLUMNS, REQ_TABLE: REQ_COLUMNS, EMP_TABLE: EMP_COLUMNS}
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted(expected_tables):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the three joined tables "
            f"{sorted(expected_tables)}"
        )
    for table, expected_columns in expected_tables.items():
        spec = tables[table]
        if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
            raise RuntimeError(f"recipe {RECIPE_ID} table {table} spec must be {{'columns', 'rows'}}")
        if spec["columns"] != expected_columns:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {table} must declare exactly the columns "
                f"{expected_columns} (MODIFIED_AT stays VARCHAR so the update render is "
                f"pinned byte-exactly)"
            )
        if not isinstance(spec["rows"], list):
            raise RuntimeError(f"recipe {RECIPE_ID} table {table} rows must be a list (may be empty)")
        for idx, row in enumerate(spec["rows"]):
            if not isinstance(row, dict) or sorted(row.keys()) != sorted(expected_columns):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table} row {idx} must fill exactly "
                    f"{sorted(expected_columns)}"
                )
            for key, value in row.items():
                if not isinstance(value, str):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} table {table} row {idx}.{key} must be a string"
                    )
        if table == REQ_TABLE:
            for idx, row in enumerate(spec["rows"]):
                if not _W_ID_RE.fullmatch(str(row.get("ID") or "")):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} {REQ_TABLE} row {idx}.ID must be letter+digits "
                        f"(ORDER BY RIGHT(W.ID, LEN(W.ID)-1)::INT casts the tail): {row.get('ID')!r}"
                    )


def _require_force_shape(force: Any) -> None:
    if force is None:
        return
    if not isinstance(force, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error must be an object")
    if str(force.get("step_as") or "") != SELECT_STEP_AS or not str(force.get("error") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error must target step_as {SELECT_STEP_AS!r} "
            "with an explicit error message (the deterministic catch path)"
        )


def _require_expect_shape(expect: Any, force: Any, now: str) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    outcome = expect.get("outcome")
    if outcome not in OUTCOMES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.outcome must be one of {OUTCOMES}")
    if (outcome == "catch_stop") != (force is not None):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the catch outcome and force_action_error must be declared "
            "together (the static SQL has no trigger-controllable live failure)"
        )
    select_rows = expect.get("select_rows")
    if not isinstance(select_rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.select_rows must be a list")
    for idx, row in enumerate(select_rows):
        if not isinstance(row, dict) or sorted(row.keys()) != [
            "KEY", "NEW_VALUE", "OLD_VALUE", "REQUEST_ID", "TYPE",
        ]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.select_rows[{idx}] must carry exactly the five "
                "SELECT aliases"
            )
    update_calls = expect.get("update_calls")
    if not isinstance(update_calls, list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.update_calls must be a list (one entry per "
            "foreach iteration, in ORDER BY RIGHT(W.ID, ...)::INT DESC order)"
        )
    for idx, update_call in enumerate(update_calls):
        if not isinstance(update_call, dict) or sorted(update_call.keys()) != [
            "columns", "rows_updated", "where",
        ]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.update_calls[{idx}] must be "
                "{'where','columns','rows_updated'}"
            )
        if not _WHERE_RE.fullmatch(str(update_call["where"])):
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.update_calls[{idx}].where must be the "
                f"interpolated 4-way AND clause: {update_call['where']!r}"
            )
        if update_call["columns"] != {"modified_at": now, "old_value": "free"}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.update_calls[{idx}].columns must pin the "
                f"pinned-now render exactly: {update_call['columns']!r}"
            )
    checks = {
        "updated": (
            expect.get("tools")
            == ["snowflake.search_rows_sql"] + ["snowflake.update_rows"] * len(update_calls),
            expect.get("executed_action_count") == 1 + len(update_calls),
            len(update_calls) >= 1,
            len(select_rows) == len(update_calls),
            all(call.get("rows_updated") == 1 for call in update_calls),
            expect.get("stop_step_number") is None,
            expect.get("catch_message") is None,
        ),
        "stop_duplicate": (
            expect.get("tools") == EXPECTED_RAW_TOOLS,
            expect.get("executed_action_count") == 2,
            len(select_rows) >= 2,
            len(update_calls) == 1 and int(update_calls[0].get("rows_updated") or 0) >= 2,
            expect.get("stop_step_number") == 7,
            expect.get("catch_message") is None,
        ),
        "noop": (
            expect.get("tools") == ["snowflake.search_rows_sql"],
            expect.get("executed_action_count") == 1,
            select_rows == [],
            update_calls == [],
            expect.get("stop_step_number") is None,
            expect.get("catch_message") is None,
        ),
        "catch_stop": (
            expect.get("tools") == [],
            expect.get("executed_action_count") == 0,
            select_rows == [],
            update_calls == [],
            expect.get("stop_step_number") == 9,
            isinstance(force, dict) and expect.get("catch_message") == force.get("error"),
        ),
    }[outcome]
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with outcome {outcome!r}: {expect!r}"
        )
    final_adj = expect.get("final_adj_rows")
    if (
        not isinstance(final_adj, dict)
        or sorted(final_adj.keys()) != ["count", "match_fields", "rows"]
        or not isinstance(final_adj.get("rows"), list)
        or not isinstance(final_adj.get("match_fields"), list)
        or final_adj.get("count") != len(final_adj["rows"])
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_adj_rows must be "
            "{'count','match_fields','rows'} covering the WHOLE final table"
        )
    items = expect.get("tool_expectations")
    if not isinstance(items, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must be a list")
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[{idx}] must be an object")
        unknown = sorted(set(item.keys()) - _EXPECT_ITEM_KEYS)
        if unknown:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] has unrecognized keys: {unknown}"
            )
        if item.get("tool") == "snowflake.update_rows":
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] must not target "
                "snowflake.update_rows (compound WHERE breaks the generic single-clause "
                "matcher; the per-recipe verifier pins the update instead)"
            )
        if item.get("tool") not in ALLOWED_TOOLS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}].tool must be one of "
                f"{ALLOWED_TOOLS}; got {item.get('tool')!r}"
            )
        if not any(key in item for key in _EXPECT_VALUE_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] must carry at least one value "
                "key (corpus lint)"
            )
    if outcome != "catch_stop":
        if not items or item_sql(items[0]) != RAW_SELECT_SQL:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[0] must pin the verbatim select SQL"
            )


def item_sql(item: dict[str, Any]) -> str:
    args = item.get("args_contains")
    return str((args or {}).get("sql") or "") if isinstance(args, dict) else ""


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
