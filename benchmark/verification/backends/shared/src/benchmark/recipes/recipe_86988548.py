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
from ..verifier import verify_86988548


RECIPE_ID = "86988548"
SEED_TYPE = "employee_app_access_deprovision_sync_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "43e3382a"
SEARCH_STEP_AS = "064546a3"
FOREACH_AS = "4e6f4cf6"
DECLARE_STEP_AS = "596027f1"
UPDATE_STEP_AS = "44918af6"
LIST_STEP_AS = "34ff45c2"
CATCH_STEP_AS = "02087b2a"
STOP_STEP_AS = "17a5ef93"
LIST_NAME = "Troubleshooting"
MAX_ELIGIBLE_ROWS = 1
# Seed key discipline (LIVE-verified end-to-end by triage and re-probed on
# HEAD 80d400ce): the update action's literal table string is
# 'PUBLIC.EMPLOYEE_APP_ACCESS_LEVEL' — register EXACTLY that key so the
# search rewrite's bare-name fallback (FROM EMPLOYEE_APP_ACCESS_LEVEL) and
# the update resolve the SAME physical table; the other three tables are
# referenced bare in JOIN position and registered under bare keys.
EAAL_TABLE = "PUBLIC.EMPLOYEE_APP_ACCESS_LEVEL"
AAL_TABLE = "APP_ACCESS_LEVEL"
APP_TABLE = "APP"
EA_TABLE = "EMPLOYEE_APP"
TABLE_COLUMNS: dict[str, dict[str, str]] = {
    EAAL_TABLE: {
        "APP_ACCESS_LEVEL_ID": "string",
        "APP_USER_ID": "string",
        "CREATED_AT": "timestamp_ntz",
        "DEPROVISION_DATE": "timestamp_ntz",
        "EMPLOYEE_ID": "integer",
        "MODIFIED_AT": "timestamp_ntz",
        "PROVISION_DATE": "timestamp_ntz",
        "STATUS": "string",
        "USERNAME": "string",
    },
    AAL_TABLE: {"ID": "string", "NAME": "string", "APP_ID": "string"},
    APP_TABLE: {"ID": "string", "NAME": "string"},
    EA_TABLE: {
        "EMPLOYEE_ID": "integer",
        "APP_USER_ID": "string",
        "USERNAME": "string",
        "STATUS": "string",
        "DEPROVISION_DATE": "timestamp_ntz",
        "APP_ID": "string",
    },
}

# clock.scheduled_event (as 43e3382a, daily 10:00) — payload-less trigger;
# the ONLY time source is the pinned seed 'now' (modified_at formula):
#   TRY 2:
#     3  snowflake.search_rows_sql 064546a3 (LIVE, limit 50000): SELECT
#        DISTINCT EAAL.* aliases + EA.DEPROVISION_DATE::DATE AS
#        EA_DEPROVISION_DATE + CASE(EA inactive AND EAAL not-inactive) AS
#        UPDATE_RECORD FROM EMPLOYEE_APP_ACCESS_LEVEL EAAL JOIN
#        APP_ACCESS_LEVEL AAL JOIN APP A JOIN EMPLOYEE_APP EA ON a
#        CASE-in-JOIN match ladder (employee_id -> app_user_id -> username)
#        WHERE UPDATE_RECORD = TRUE (alias-in-WHERE, Snowflake lateral
#        alias semantics — triage LIVE-verified the verbatim SQL).
#     FOREACH 4 (as 4e6f4cf6, repeat_mode simple) over the rows:
#       5  workato_variable.declare_variable 596027f1 where_clause =
#          3-arm if/elsif/else (probed on HEAD): employee_id.present? ->
#          "...EMPLOYEE_ID = '<id>'..."; elsif app_user_id.present? ->
#          "...APP_USER_ID = '<id>'..."; else "...USERNAME = '<name>'..."
#          — each arm prefixed APP_ACCESS_LEVEL_ID = '<id>' AND … AND
#          STATUS NOT IN ('Inactive').
#       6  snowflake.update_rows 44918af6 (LIVE): table
#          PUBLIC.EMPLOYEE_APP_ACCESS_LEVEL, where = #{where_clause},
#          columns {deprovision_date = foreach.ea_deprovision_date,
#          modified_at = =now.in_time_zone("Etc/UTC"), status 'Inactive'}.
#       7  workato_list.accumulate_list_items 34ff45c2 'Troubleshooting'
#          (mock): where_clause + 8 foreach fields (employee_id stays a
#          live INT, app_user_id/username may be null — pinned verbatim).
#   CATCH 8 (as 02087b2a, max_retry_count 0):
#     9  STOP 17a5ef93 (stop_with_error 'true', reason = catch.message) —
#        the engine traces {stopped: true} WITHOUT rendering stop_reason
#        (probed on HEAD); the catch payload is pinned via step_outputs.
#
# Determinism rule: SELECT DISTINCT has no ORDER BY, so every variant seeds
# AT MOST ONE eligible row (the seeder enforces it via expect.eligible_rows)
# — multi-row foreach order would be live-nondeterministic.
# Cleanup: create-or-replace seed + registered drop of all four tables in
# the runner's finally (updates land in benchmark-owned tables). Catch
# variants never reach Snowflake and must not seed live state.

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "clock", "name": "scheduled_event", "as": "43e3382a", "skip": false, "input": {"time_unit": "days", "timezone": "<anon>Europe/London</anon>", "trigger_at": "10:00:00", "trigger_every": "1"}, "block": [{"number": 2, "keyword": "try", "provider": "", "name": "", "as": "", "skip": false, "input": {}, "block": [{"number": 3, "keyword": "action", "provider": "snowflake", "name": "search_rows_sql", "as": "064546a3", "skip": false, "input": {"limit": "50000", "output_schema": "[{\"control_type\":\"text\",\"label\":\"APP ACCESS LEVEL ID\",\"name\":\"APP_ACCESS_LEVEL_ID\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"APP ACCESS LEVEL NAME\",\"name\":\"APP_ACCESS_LEVEL_NAME\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"integer\",\"label\":\"EMPLOYEE ID\",\"parse_output\":\"integer_conversion\",\"name\":\"EMPLOYEE_ID\",\"type\":\"integer\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"APP USER ID\",\"name\":\"APP_USER_ID\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"USERNAME\",\"name\":\"USERNAME\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"EAAL STATUS\",\"name\":\"EAAL_STATUS\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"EA STATUS\",\"name\":\"EA_STATUS\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"date\",\"label\":\"EA DEPROVISION DATE\",\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\",\"name\":\"EA_DEPROVISION_DATE\",\"type\":\"date\",\"optional\":false},{\"name\":\"UPDATE_RECORD\",\"type\":\"boolean\",\"optional\":false,\"control_type\":\"checkbox\",\"label\":\"UPDATE RECORD\",\"render_input\":{},\"parse_output\":{},\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"UPDATE RECORD\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"UPDATE_RECORD\",\"type\":\"boolean\",\"optional\":false}}]", "sql": "SELECT DISTINCT\nEAAL.APP_ACCESS_LEVEL_ID,\nAAL.NAME AS APP_ACCESS_LEVEL_NAME,\nEAAL.EMPLOYEE_ID,\nEAAL.APP_USER_ID,\nEAAL.USERNAME,\nEAAL.STATUS AS EAAL_STATUS,\nEA.STATUS AS EA_STATUS,\nEA.DEPROVISION_DATE::DATE AS EA_DEPROVISION_DATE,\nCASE\nWHEN EA.STATUS = 'Inactive' AND EAAL.STATUS NOT IN ('Inactive')\nTHEN TRUE\nELSE FALSE\nEND AS UPDATE_RECORD\n\nFROM EMPLOYEE_APP_ACCESS_LEVEL EAAL\nJOIN APP_ACCESS_LEVEL AAL\nON EAAL.APP_ACCESS_LEVEL_ID = AAL.ID\n\nJOIN APP A\nON AAL.APP_ID = A.ID\n\nJOIN EMPLOYEE_APP EA\nON AAL.APP_ID = A.ID\nAND\nCASE\nWHEN EAAL.EMPLOYEE_ID IS NOT NULL\nTHEN EAAL.EMPLOYEE_ID = EA.EMPLOYEE_ID\nELSE \n  CASE\n  WHEN EAAL.APP_USER_ID IS NOT NULL\n  THEN EAAL.APP_USER_ID = EA.APP_USER_ID\n  ELSE EAAL.USERNAME = EA.USERNAME\n  END\nEND\nAND A.ID = EA.APP_ID\n\nWHERE UPDATE_RECORD = TRUE"}, "block": []}, {"number": 4, "keyword": "foreach", "provider": "", "name": "", "as": "4e6f4cf6", "skip": false, "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"064546a3\",\"path\":[\"rows\"]}')}"}, "repeat_mode": "simple", "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"064546a3\",\"path\":[\"rows\"]}')}", "block": [{"number": 5, "keyword": "action", "provider": "workato_variable", "name": "declare_variable", "as": "596027f1", "skip": false, "input": {"variables": {"data": {"where_clause": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"4e6f4cf6\",\"path\":[\"employee_id\"]}').present?\n  \"APP_ACCESS_LEVEL_ID = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"4e6f4cf6\",\"path\":[\"app_access_level_id\"]}')}' AND EMPLOYEE_ID = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"4e6f4cf6\",\"path\":[\"employee_id\"]}')}' AND STATUS NOT IN ('Inactive')\"\nelsif _dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"4e6f4cf6\",\"path\":[\"app_user_id\"]}').present?\n  \"APP_ACCESS_LEVEL_ID = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"4e6f4cf6\",\"path\":[\"app_access_level_id\"]}')}' AND APP_USER_ID = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"4e6f4cf6\",\"path\":[\"app_user_id\"]}')}' AND STATUS NOT IN ('Inactive')\"\nelse\n  \"APP_ACCESS_LEVEL_ID = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"4e6f4cf6\",\"path\":[\"app_access_level_id\"]}')}' AND USERNAME = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"4e6f4cf6\",\"path\":[\"username\"]}')}' AND STATUS NOT IN ('Inactive')\"\nend"}, "schema": "[{\"name\":\"where_clause\",\"type\":\"string\",\"optional\":true,\"label\":\"WHERE Clause\",\"details\":{\"real_name\":\"WHERE Clause\"},\"control_type\":\"text\"}]"}}, "block": []}, {"number": 6, "keyword": "action", "provider": "snowflake", "name": "update_rows", "as": "44918af6", "skip": false, "input": {"columns": {"deprovision_date": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"4e6f4cf6\",\"path\":[\"ea_deprovision_date\"]}')}", "modified_at": "=now.in_time_zone(\"Etc/UTC\")", "status": "Inactive"}, "table": "PUBLIC.EMPLOYEE_APP_ACCESS_LEVEL", "where": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"596027f1\",\"path\":[\"where_clause\"]}')}"}, "block": []}, {"number": 7, "keyword": "action", "provider": "workato_list", "name": "accumulate_list_items", "as": "34ff45c2", "skip": false, "input": {"list_item": {"data": {"Username": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"4e6f4cf6\",\"path\":[\"username\"]}')}", "app_access_level_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"4e6f4cf6\",\"path\":[\"app_access_level_id\"]}')}", "app_access_level_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"4e6f4cf6\",\"path\":[\"app_access_level_name\"]}')}", "app_user_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"4e6f4cf6\",\"path\":[\"app_user_id\"]}')}", "deprovision_date": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"4e6f4cf6\",\"path\":[\"ea_deprovision_date\"]}')}", "ea_status": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"4e6f4cf6\",\"path\":[\"ea_status\"]}')}", "eaal_status": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"4e6f4cf6\",\"path\":[\"eaal_status\"]}')}", "employee_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"4e6f4cf6\",\"path\":[\"employee_id\"]}')}", "where_clause": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"596027f1\",\"path\":[\"where_clause\"]}')}"}, "schema": "[{\"control_type\":\"text\",\"label\":\"WHERE Clause\",\"name\":\"where_clause\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"WHERE Clause\"}},{\"control_type\":\"text\",\"label\":\"App Access Level ID\",\"name\":\"app_access_level_id\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"App Access Level ID\"}},{\"name\":\"app_access_level_name\",\"type\":\"string\",\"optional\":true,\"label\":\"App Access Level Name\",\"details\":{\"real_name\":\"App Access Level Name\"},\"control_type\":\"text\"},{\"name\":\"employee_id\",\"type\":\"string\",\"optional\":true,\"label\":\"Employee ID\",\"details\":{\"real_name\":\"Employee ID\"},\"control_type\":\"text\"},{\"name\":\"app_user_id\",\"type\":\"string\",\"optional\":true,\"label\":\"App User ID\",\"details\":{\"real_name\":\"App User ID\"},\"control_type\":\"text\"},{\"name\":\"Username\",\"type\":\"string\",\"optional\":true,\"label\":\"Username\",\"details\":{\"real_name\":\"Username\"},\"control_type\":\"text\"},{\"name\":\"eaal_status\",\"type\":\"string\",\"optional\":true,\"label\":\"EAAL Status\",\"details\":{\"real_name\":\"EAAL Status\"},\"control_type\":\"text\"},{\"name\":\"ea_status\",\"type\":\"string\",\"optional\":true,\"label\":\"EA Status\",\"details\":{\"real_name\":\"EA Status\"},\"control_type\":\"text\"},{\"name\":\"deprovision_date\",\"type\":\"string\",\"optional\":true,\"label\":\"Deprovision Date\",\"details\":{\"real_name\":\"Deprovision Date\"},\"control_type\":\"text\"}]"}, "name": "Troubleshooting"}, "block": []}]}, {"number": 8, "keyword": "catch", "provider": "", "name": "", "as": "02087b2a", "skip": false, "input": {"max_retry_count": "0", "retry_interval": "2"}, "block": [{"number": 9, "keyword": "stop", "provider": "", "name": "", "as": "17a5ef93", "skip": false, "input": {"stop_reason": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"02087b2a\",\"path\":[\"message\"]}')}", "stop_with_error": "true"}, "block": []}]}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (SEARCH_STEP_AS, "snowflake", "search_rows_sql"),
    (DECLARE_STEP_AS, "workato_variable", "declare_variable"),
    (UPDATE_STEP_AS, "snowflake", "update_rows"),
    (LIST_STEP_AS, "workato_list", "accumulate_list_items"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_runtime.declare_variable",
    "snowflake.update_rows",
    "workato_runtime.accumulate_list_items",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "snowflake.update_rows",
]
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "eligible_rows",
    "where_clause",
    "update_args",
    "update_rows_updated",
    "troubleshooting_items",
    "final_eaal_rows",
    "stopped",
)
_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2})?$")
# Values that interpolate into the single-quoted where_clause SQL literal.
_SQL_LITERAL_RE = re.compile(r"^[A-Za-z0-9@._ \-]+$")


def validate_86988548(raw: dict[str, Any]) -> dict[str, Any]:
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
    search = _node_by_as(raw, SEARCH_STEP_AS)
    sql = str((search.get("input") or {}).get("sql") or "")
    for fragment in (
        "SELECT DISTINCT",
        "EA.DEPROVISION_DATE::DATE AS EA_DEPROVISION_DATE",
        "END AS UPDATE_RECORD",
        "FROM EMPLOYEE_APP_ACCESS_LEVEL EAAL",
        "WHERE UPDATE_RECORD = TRUE",
    ):
        if fragment not in sql:
            raise RuntimeError(f"recipe {RECIPE_ID} search SQL lost {fragment!r}: {sql!r}")
    if str((search.get("input") or {}).get("limit") or "") != "50000":
        raise RuntimeError(f"recipe {RECIPE_ID} search limit changed")
    declare = _node_by_as(raw, DECLARE_STEP_AS)
    formula = str(
        (((declare.get("input") or {}).get("variables") or {}).get("data") or {}).get(
            "where_clause"
        )
        or ""
    )
    if (
        not formula.startswith("=if ")
        or "elsif " not in formula
        or "else" not in formula
        or formula.count("STATUS NOT IN ('Inactive')") != 3
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} 3-arm where_clause formula changed: {formula!r}"
        )
    update = _node_by_as(raw, UPDATE_STEP_AS)
    update_input = update.get("input") or {}
    if str(update_input.get("table") or "") != EAAL_TABLE:
        raise RuntimeError(
            f"recipe {RECIPE_ID} update table changed: {update_input.get('table')!r} "
            f"(the registered seed key must equal it exactly)"
        )
    columns = update_input.get("columns") or {}
    if sorted(columns.keys()) != ["deprovision_date", "modified_at", "status"]:
        raise RuntimeError(f"recipe {RECIPE_ID} update column set changed: {columns!r}")
    if columns.get("status") != "Inactive" or columns.get("modified_at") != '=now.in_time_zone("Etc/UTC")':
        raise RuntimeError(f"recipe {RECIPE_ID} update column formulas changed: {columns!r}")
    stop = _node_by_as(raw, STOP_STEP_AS)
    if stop.get("keyword") != "stop" or str((stop.get("input") or {}).get("stop_with_error")) != "true":
        raise RuntimeError(f"recipe {RECIPE_ID} catch stop step changed")
    list_node = _node_by_as(raw, LIST_STEP_AS)
    if str((list_node.get("input") or {}).get("name") or "") != LIST_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} accumulate list name changed")
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "snowflake_tables": sorted(TABLE_COLUMNS.keys()),
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


def seed_86988548(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_86988548(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be an explicitly-empty object "
            f"(payload-less scheduler tick); got {trigger!r}"
        )
    now = data.get("now")
    if not isinstance(now, str) or not now.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must pin now "
            "('=now.in_time_zone(\"Etc/UTC\")' fails fast without it)"
        )
    parsed_now = datetime.datetime.fromisoformat(now.replace("Z", "+00:00"))
    if parsed_now.tzinfo is None:
        raise RuntimeError(f"recipe {RECIPE_ID} now must carry an explicit UTC offset: {now!r}")
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    force = data.get("force_action_error")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "now": now,
        "expect": deepcopy(expect),
    }
    if force is not None:
        # CATCH branch: the forced error fires BEFORE the live search runs,
        # so the variant owns no live resources and must not seed any.
        if not isinstance(force, dict) or str(force.get("step_as") or "") != SEARCH_STEP_AS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} force_action_error must target the snowflake "
                f"search step {SEARCH_STEP_AS!r}; got {force!r}"
            )
        if sorted(seed_in.keys()) != []:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must not seed live sections; "
                f"got {sorted(seed_in.keys())}"
            )
        if expect.get("stopped") is not True or expect.get("executed_action_count") != 0:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants stop before any action executes "
                "(expect.stopped true, executed_action_count 0)"
            )
        for key in (
            "eligible_rows",
            "where_clause",
            "update_args",
            "update_rows_updated",
            "troubleshooting_items",
            "final_eaal_rows",
        ):
            if expect.get(key) is not None:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} catch variants must pin expect.{key} as null; "
                    f"got {expect.get(key)!r}"
                )
    else:
        if sorted(seed_in.keys()) != ["snowflake_live"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} TRY variants must seed exactly the snowflake_live "
                f"section; got {sorted(seed_in.keys())}"
            )
        _require_snowflake_section(seed_in["snowflake_live"])
        _require_try_expect_coherence(expect, parsed_now)
        provision = ctx.tools.call(
            "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
        )
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
        out["snowflake_live"] = deepcopy(provision["state"])
        out["snowflake_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_86988548(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_86988548(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not str(seed.get("now") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing pinned now")
    live = isinstance(seed.get("snowflake_live"), dict)
    if not live and not isinstance(seed.get("force_action_error"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed carries neither snowflake_live state nor a "
            "forced catch error — nothing to run"
        )
    raw_execution: dict[str, Any] | None = None
    initial_snapshot: dict[str, Any] = {}
    final_snapshot: dict[str, Any] = {}
    cleanup: dict[str, Any] | None = None
    try:
        initial_snapshot = _snapshot(ctx, live)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, live)
    finally:
        if live:
            # Required cleanup: the seeder create-or-replaced the four
            # registered tables; drop them whether or not the run completed.
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
    result["verifier"] = verify_86988548(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_snowflake_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the SQL uses no CURRENT_DATE/TIMESTAMP, so current_time is not allowed)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted(TABLE_COLUMNS.keys()):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{sorted(TABLE_COLUMNS.keys())} (EAAL under the 2-part update key, the "
            f"other three under the bare names the JOINs reference)"
        )
    for table, expected_columns in TABLE_COLUMNS.items():
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
            _require_row(table, idx, row, expected_columns)
    for idx, row in enumerate(tables[EA_TABLE]["rows"]):
        # Any Inactive EMPLOYEE_APP row can become the eligible side of the
        # join; its DEPROVISION_DATE feeds a live TIMESTAMP_NTZ write and an
        # empty value would fail the update — require it up front.
        if row.get("STATUS") == "Inactive" and not row.get("DEPROVISION_DATE"):
            raise RuntimeError(
                f"recipe {RECIPE_ID} EMPLOYEE_APP row {idx} is Inactive but has no "
                "DEPROVISION_DATE (the update writes it into a timestamp column)"
            )


def _require_row(table: str, idx: int, row: Any, columns: dict[str, str]) -> None:
    if not isinstance(row, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} table {table} row {idx} must be an object")
    extra = sorted(set(row.keys()) - set(columns.keys()))
    if extra:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {table} row {idx} uses undeclared columns: {extra}"
        )
    for column, value in row.items():
        kind = columns[column]
        if value is None:
            continue
        if kind == "integer":
            if not isinstance(value, int) or isinstance(value, bool):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table} row {idx}.{column} must be an "
                    f"int or null; got {value!r}"
                )
            continue
        if kind == "timestamp_ntz":
            if not isinstance(value, str) or not _DATETIME_RE.fullmatch(value):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table} row {idx}.{column} must be "
                    f"YYYY-MM-DD[THH:MM:SS] or null; got {value!r}"
                )
            continue
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {table} row {idx}.{column} must be a "
                f"non-empty string or null; got {value!r}"
            )
        # Identity columns interpolate into the single-quoted where_clause SQL
        # literal — reject quote/backslash/wildcard charsets up front.
        if column in {"APP_ACCESS_LEVEL_ID", "APP_USER_ID", "USERNAME"} and not _SQL_LITERAL_RE.fullmatch(value):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {table} row {idx}.{column} interpolates into "
                f"a quoted SQL literal; got unsafe value {value!r}"
            )


def _require_try_expect_coherence(expect: dict[str, Any], parsed_now: datetime.datetime) -> None:
    eligible = expect.get("eligible_rows")
    if not isinstance(eligible, list) or len(eligible) > MAX_ELIGIBLE_ROWS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.eligible_rows must be a list of AT MOST ONE row "
            "(SELECT DISTINCT has no ORDER BY — multi-row foreach order is live-"
            f"nondeterministic); got {eligible!r}"
        )
    count = len(eligible)
    if expect.get("executed_action_count") != 1 + 3 * count:
        raise RuntimeError(
            f"recipe {RECIPE_ID} executed_action_count must be 1 + 3*eligible "
            f"({1 + 3 * count}); got {expect.get('executed_action_count')!r}"
        )
    if expect.get("stopped") is not False:
        raise RuntimeError(f"recipe {RECIPE_ID} TRY variants must pin expect.stopped false")
    if count == 0:
        for key in ("where_clause", "update_args", "update_rows_updated", "troubleshooting_items"):
            if expect.get(key) is not None:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} zero-eligible variants must pin expect.{key} "
                    f"as null; got {expect.get(key)!r}"
                )
        return
    update_args = expect.get("update_args")
    if not isinstance(update_args, dict) or sorted(update_args.keys()) != [
        "columns",
        "table",
        "where",
    ]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.update_args must be {{table, where, columns}}; "
            f"got {update_args!r}"
        )
    if update_args.get("table") != EAAL_TABLE:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.update_args.table must be {EAAL_TABLE!r}")
    if update_args.get("where") != expect.get("where_clause"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.update_args.where must equal expect.where_clause "
            "(the update interpolates the declared variable verbatim)"
        )
    modified_at = parsed_now.astimezone(datetime.timezone.utc).isoformat()
    columns = update_args.get("columns")
    if (
        not isinstance(columns, dict)
        or columns.get("status") != "Inactive"
        or columns.get("modified_at") != modified_at
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.update_args.columns must carry status 'Inactive' "
            f"and modified_at {modified_at!r} (the =now.in_time_zone render of the pinned "
            f"now); got {columns!r}"
        )
    if not isinstance(expect.get("troubleshooting_items"), list) or len(
        expect["troubleshooting_items"]
    ) != count:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.troubleshooting_items must list exactly one "
            "accumulated item per eligible row"
        )
    if not isinstance(expect.get("final_eaal_rows"), list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} TRY variants must pin expect.final_eaal_rows (the live "
            "EAAL read-back after the update)"
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


def _node_by_as(raw: dict[str, Any], step_as: str) -> dict[str, Any]:
    node = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == step_as),
        None,
    )
    if not isinstance(node, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} step {step_as} missing")
    return node


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


def _snapshot(ctx: RecipeContext, live: bool) -> dict[str, Any]:
    if not live:
        return {}
    return ctx.tools.call("harness.snowflake.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
