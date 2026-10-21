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
from ..verifier import verify_113487781


RECIPE_ID = "113487781"
SEED_TYPE = "snowflake_etl_monitor_slack_alert_variant"
TRACK = "live_snowflake_slack_alert"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "bd074867"
DECLARE_STEP_AS = "3b02e1c6"
SEARCH_STEP_AS = "4700b64e"
ALERT_POST_AS = "b2adabc3"
CATCH_AS = "8d0fff6e"
CATCH_POST_AS = "69fde971"
# The literal 3-part name the SQL references; MUST be the registered
# snowflake_live table key so _rewrite_sql maps it onto the benchmark
# database (<SNOWFLAKE_DATABASE>.ETL_METADATA.ELT_WORKFLOW_MONITORING).
MONITOR_TABLE = "workato_business_systems.etl_metadata.elt_workflow_monitoring"
# 'date' is seeded as a STRING column (the org's output schema types it
# string) so the `date = :date` bind equality is exact text comparison.
MONITOR_COLUMNS = {
    "ID": "number",
    "DATE": "string",
    "WORKFLOW": "string",
    "STATUS": "string",
    "CREATED_AT": "timestamp",
    "MODIFIED_AT": "timestamp",
}
RAW_SQL = (
    "select * from workato_business_systems.etl_metadata.elt_workflow_monitoring\n"
    "where status = 'In Progress' and workflow = 'Snowflake Data Load' and date = :date "
)
ALERT_TEXT = (
    "@here Daily Run has not started because Snowflake Data Load is still in "
    "progress, please check!"
)
CATCH_DM_CHANNEL = "U07GCQL582H"

# clock.scheduled_event (as bd074867, daily 23:58 Asia/Singapore) — the ONLY
# trigger pill dereferenced is scheduled_time (strftime'd into the variable).
# Body = one TRY (step 2):
#   3  workato_variable.declare_variable 3b02e1c6 (mock):
#      date = =_dp(scheduled_time).strftime("%Y-%m-%d") — formatted from the
#      literal seeded timestamp, NO timezone conversion (probe-verified:
#      '2026-07-07T23:58:00+08:00' -> '2026-07-07').
#   4  snowflake.search_rows_sql 4700b64e (LIVE): RAW_SQL with the :date bind
#      -> pyformat %(date)s, parameters {date: <declared date>}. select *
#      returns live cursor columns (original case + lowercase alias).
#   IF 5: rows current_item id_b497e547 present — current_item OUTSIDE a
#      loop = FIRST row; the hashed output-schema name resolves through
#      lookup_path's _<8hex> suffix-strip + case-insensitive retry against
#      the live 'id' column; empty rows -> MISSING -> present false:
#     6  slack_bot.post_bot_message b2adabc3 (LIVE): section_with_text
#        ALERT_TEXT to '#dbt-notifications' — not a 'U' literal, so the
#        adapter auto-routes it to SLACK_CHANNEL_OVERRIDE.
#   CATCH 7 (as 8d0fff6e, max_retry_count 0):
#     8  slack_bot.post_bot_message 69fde971 (LIVE): '#{job_context.
#        recipe_name} ded' to the literal org-foreign DM channel
#        'U07GCQL582H' — passes the U-check, so catch variants MUST route it
#        via seed.slack_channel_map {'U07GCQL582H': '__override__'}.
#
# Branch mapping:
# - alert: exactly ONE seeded row matches all three WHERE predicates
#   (status/workflow/date); decoys for each predicate prove the filter bites
#   live. 3 actions, post text pinned verbatim (including '@here ').
# - silent: only decoys -> 0 rows -> present false -> no post. 2 actions.
# - catch_dm: seed.force_action_error on 4700b64e fires BEFORE the adapter
#   (no live SQL, no snowflake seed, nothing to clean); the catch posts
#   '<job_context.recipe_name> ded'. 2 actions.
#
# Backends: Snowflake runs LIVE (create-or-replace seed + drop in the
# runner's finally; READ-ONLY — snapshot equality pinned). Slack posts are
# live terminal observables (never re-read; no cleanup). The declare step is
# the Workato-internal variable mock.

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "clock", "name": "scheduled_event", "as": "bd074867", "skip": false, "input": {"time_unit": "days", "timezone": "Asia/Singapore", "trigger_at": "23:58:00", "trigger_every": "1"}, "block": [{"number": 2, "keyword": "try", "provider": "", "name": "", "as": "", "skip": false, "input": {}, "block": [{"number": 3, "keyword": "action", "provider": "workato_variable", "name": "declare_variable", "as": "3b02e1c6", "skip": false, "input": {"variables": {"data": {"date": "=_dp('{\"pill_type\":\"output\",\"provider\":\"clock\",\"line\":\"bd074867\",\"path\":[\"scheduled_time\"]}').strftime(\"%Y-%m-%d\")"}, "schema": "[{\"name\":\"date\",\"type\":\"date\",\"optional\":true,\"label\":\"date\",\"details\":{\"real_name\":\"date\"},\"control_type\":\"date\",\"parent\":[\"variables\",\"data\"]}]"}}, "block": []}, {"number": 4, "keyword": "action", "provider": "snowflake", "name": "search_rows_sql", "as": "4700b64e", "skip": false, "input": {"output_schema": "[{\"control_type\":\"number\",\"label\":\"ID\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"id\"},{\"control_type\":\"text\",\"label\":\"Date\",\"type\":\"string\",\"name\":\"date\"},{\"control_type\":\"text\",\"label\":\"Workflow\",\"type\":\"string\",\"name\":\"workflow\"},{\"control_type\":\"text\",\"label\":\"Status\",\"type\":\"string\",\"name\":\"status\"},{\"control_type\":\"text\",\"label\":\"Created at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"type\":\"date_time\",\"name\":\"created_at\"},{\"control_type\":\"text\",\"label\":\"Modified at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"type\":\"date_time\",\"name\":\"modified_at\"}]", "parameters": {"data": {"date": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"3b02e1c6\",\"path\":[\"date\"]}')}"}, "schema": "[{\"name\":\"date\",\"type\":\"date\",\"optional\":true,\"label\":\"date\",\"details\":{\"real_name\":\"date\"},\"control_type\":\"date\"}]"}, "sql": "select * from workato_business_systems.etl_metadata.elt_workflow_monitoring\nwhere status = 'In Progress' and workflow = 'Snowflake Data Load' and date = :date "}, "block": []}, {"number": 5, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"4700b64e\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"id_b497e547\"]}')}", "operand": "present", "rhs": ""}], "operand": "and", "type": "compound"}, "block": [{"number": 6, "keyword": "action", "provider": "slack_bot", "name": "post_bot_message", "as": "b2adabc3", "skip": false, "input": {"blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": "@here Daily Run has not started because Snowflake Data Load is still in progress, please check!"}], "channel": "#dbt-notifications"}, "block": []}]}, {"number": 7, "keyword": "catch", "provider": "", "name": "", "as": "8d0fff6e", "skip": false, "input": {"max_retry_count": "0", "retry_interval": "2"}, "block": [{"number": 8, "keyword": "action", "provider": "slack_bot", "name": "post_bot_message", "as": "69fde971", "skip": false, "input": {"blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": "#{_dp('{\"pill_type\":\"job_context\",\"path\":[\"recipe_name\"]}')} ded"}], "channel": "U07GCQL582H"}, "block": []}]}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (DECLARE_STEP_AS, "workato_variable", "declare_variable"),
    (SEARCH_STEP_AS, "snowflake", "search_rows_sql"),
    (ALERT_POST_AS, "slack_bot", "post_bot_message"),
    (CATCH_POST_AS, "slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "snowflake.search_rows_sql",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "slack.post_message",
]
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "outcome",
    "declared_date",
    "sql_row_count",
    "post_text",
)
OPTIONAL_EXPECT_KEYS = {"catch_message"}
OUTCOMES = ("alert", "silent", "catch_dm")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def validate_113487781(raw: dict[str, Any]) -> dict[str, Any]:
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
    # Semantic pins on the drift-prone bits.
    search = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == SEARCH_STEP_AS), None
    )
    if not isinstance(search, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} search step {SEARCH_STEP_AS} missing")
    if str((search.get("input") or {}).get("sql") or "") != RAW_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} monitoring SQL changed")
    alert = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == ALERT_POST_AS), None
    )
    if not isinstance(alert, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} alert post step {ALERT_POST_AS} missing")
    blocks = (alert.get("input") or {}).get("blocks") or []
    if len(blocks) != 1 or blocks[0].get("section_text") != ALERT_TEXT:
        raise RuntimeError(f"recipe {RECIPE_ID} alert text changed: {blocks!r}")
    catch_post = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == CATCH_POST_AS), None
    )
    if not isinstance(catch_post, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} catch post step {CATCH_POST_AS} missing")
    if str((catch_post.get("input") or {}).get("channel") or "") != CATCH_DM_CHANNEL:
        raise RuntimeError(f"recipe {RECIPE_ID} catch DM channel changed")
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "snowflake_table": MONITOR_TABLE,
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


def seed_113487781(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_113487781(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    declared_date = _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    expect = data.get("expect")
    _require_expect_common(expect, declared_date)
    outcome = expect["outcome"]
    force = data.get("force_action_error")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
    }
    if outcome == "catch_dm":
        _require_catch_variant(seed_in, expect, force, data)
        out["slack_channel_map"] = deepcopy(seed_in["slack_channel_map"])
    else:
        _require_try_variant(seed_in, expect, force, declared_date)
        provision = ctx.tools.call(
            "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
        )
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
        out["snowflake_live"] = deepcopy(provision["state"])
        out["snowflake_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_113487781(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_113487781(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    live = isinstance(seed.get("snowflake_live"), dict)
    if not live and not isinstance(seed.get("force_action_error"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed carries neither snowflake_live state nor a forced "
            "catch error — nothing to run"
        )
    if "slack.post_message" in (expect.get("tools") or []) and not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
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
            # Required cleanup: drop the create-or-replace seeded monitoring
            # table whether or not the run completed. Slack posts are terminal
            # observables (never re-read; no cleanup).
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
    result["verifier"] = verify_113487781(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> str:
    if sorted(trigger.keys()) != ["scheduled_time"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly scheduled_time (the "
            f"only trigger pill the recipe reads); got {sorted(trigger.keys())}"
        )
    value = trigger.get("scheduled_time")
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} scheduled_time must be a non-empty ISO string")
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(
            f"recipe {RECIPE_ID} scheduled_time is not ISO datetime: {value!r}"
        ) from exc
    if parsed.tzinfo is None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} scheduled_time must carry an explicit UTC offset "
            f"(the trigger emits zoned timestamps): {value!r}"
        )
    # The engine strftime formats the literal timestamp with NO timezone
    # conversion — the declared date is the date component of the seeded value.
    return parsed.strftime("%Y-%m-%d")


def _require_expect_common(expect: Any, declared_date: str) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS) - OPTIONAL_EXPECT_KEYS)
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if expect.get("outcome") not in OUTCOMES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.outcome must be one of {OUTCOMES}")
    if expect.get("declared_date") != declared_date:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.declared_date must equal the strftime of the "
            f"seeded scheduled_time ({declared_date!r}); got {expect.get('declared_date')!r}"
        )


def _require_try_variant(
    seed_in: dict[str, Any],
    expect: dict[str, Any],
    force: Any,
    declared_date: str,
) -> None:
    if force is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} alert/silent variants must not force an action error"
        )
    if sorted(seed_in.keys()) != ["snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} alert/silent variants must seed exactly the "
            f"snowflake_live section; got {sorted(seed_in.keys())}"
        )
    match_count = _require_snowflake_section(seed_in["snowflake_live"], declared_date)
    outcome = expect["outcome"]
    if expect.get("sql_row_count") != match_count:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.sql_row_count must equal the number of seeded "
            f"rows matching all three WHERE predicates ({match_count}); got "
            f"{expect.get('sql_row_count')!r}"
        )
    if "catch_message" in expect:
        raise RuntimeError(f"recipe {RECIPE_ID} only catch variants pin catch_message")
    if outcome == "alert":
        checks = (
            match_count == 1,
            expect.get("post_text") == ALERT_TEXT,
            expect.get("executed_action_count") == 3,
            expect.get("tools") == ["snowflake.search_rows_sql", "slack.post_message"],
        )
        reason = (
            "alert variants seed EXACTLY ONE matching row (select * has no ORDER BY; "
            "one match keeps the first-row current_item deterministic), pin the "
            "verbatim @here text and run declare -> search -> post"
        )
    else:  # silent
        checks = (
            match_count == 0,
            expect.get("post_text") is None,
            expect.get("executed_action_count") == 2,
            expect.get("tools") == ["snowflake.search_rows_sql"],
        )
        reason = "silent variants seed only decoy rows: no post, post_text null"
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with outcome "
            f"{outcome!r} ({reason}): {expect!r}"
        )


def _require_catch_variant(
    seed_in: dict[str, Any],
    expect: dict[str, Any],
    force: Any,
    data: dict[str, Any],
) -> None:
    if not isinstance(force, dict) or str(force.get("step_as") or "") != SEARCH_STEP_AS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the catch is not naturally reachable: catch variants "
            f"must declare force_action_error.step_as == {SEARCH_STEP_AS!r}"
        )
    if not str(force.get("error") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error.error must be explicit")
    if sorted(seed_in.keys()) != ["slack_channel_map"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch variants must seed exactly slack_channel_map "
            "(the forced error fires BEFORE the snowflake adapter — no live table "
            f"may be provisioned); got {sorted(seed_in.keys())}"
        )
    if seed_in["slack_channel_map"] != {CATCH_DM_CHANNEL: "__override__"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch variants must map the literal DM channel "
            f"{CATCH_DM_CHANNEL!r} to '__override__' (the benchmark workspace has no "
            f"such user); got {seed_in['slack_channel_map']!r}"
        )
    job_context = data.get("job_context")
    if not isinstance(job_context, dict) or not str(job_context.get("recipe_name") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch variants must pin job_context.recipe_name "
            "(the catch post renders the job_context recipe_name pill)"
        )
    recipe_name = str(job_context["recipe_name"])
    checks = (
        expect.get("sql_row_count") is None,
        expect.get("post_text") == f"{recipe_name} ded",
        expect.get("catch_message") == force.get("error"),
        expect.get("executed_action_count") == 2,
        expect.get("tools") == ["slack.post_message"],
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch expect block is inconsistent: sql_row_count must "
            f"be null, post_text '{recipe_name} ded', catch_message the forced error, "
            f"2 actions, tools [slack.post_message]; got {expect!r}"
        )


def _require_snowflake_section(section: Any, declared_date: str) -> int:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the SQL uses no CURRENT_DATE/TIMESTAMP, so current_time is not allowed)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [MONITOR_TABLE]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{MONITOR_TABLE!r} (the literal 3-part SQL name)"
        )
    spec = tables[MONITOR_TABLE]
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table spec must be exactly {{'columns': ..., 'rows': ...}}"
        )
    if spec["columns"] != MONITOR_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table must declare exactly the columns {MONITOR_COLUMNS} "
            "(date STRING keeps the :date bind equality exact)"
        )
    rows = spec["rows"]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table rows must be a NON-EMPTY list — silent variants "
            "prove the WHERE clause bites via decoys, not via an empty table"
        )
    match_count = 0
    ids: set[Any] = set()
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(MONITOR_COLUMNS.keys()):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} must fill exactly "
                f"{sorted(MONITOR_COLUMNS.keys())}; got {row!r}"
            )
        if isinstance(row["ID"], bool) or not isinstance(row["ID"], int):
            raise RuntimeError(f"recipe {RECIPE_ID} row {idx} ID must be an integer")
        ids.add(row["ID"])
        if not isinstance(row["DATE"], str) or not _DATE_RE.fullmatch(row["DATE"]):
            raise RuntimeError(f"recipe {RECIPE_ID} row {idx} DATE must be YYYY-MM-DD")
        for key in ("WORKFLOW", "STATUS"):
            if not isinstance(row[key], str) or not row[key].strip():
                raise RuntimeError(f"recipe {RECIPE_ID} row {idx} {key} must be non-empty")
        for key in ("CREATED_AT", "MODIFIED_AT"):
            if not isinstance(row[key], str) or not _TS_RE.fullmatch(row[key]):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} row {idx} {key} must be 'YYYY-MM-DD HH:MM:SS' "
                    "(stable isoformat read-back)"
                )
        if (
            row["STATUS"] == "In Progress"
            and row["WORKFLOW"] == "Snowflake Data Load"
            and row["DATE"] == declared_date
        ):
            match_count += 1
    if len(ids) != len(rows):
        raise RuntimeError(f"recipe {RECIPE_ID} row IDs must be distinct")
    if match_count > 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} at most ONE row may match the WHERE clause (select * "
            "has no ORDER BY; the IF reads the FIRST row's id — multi-match order is "
            f"not deterministic groundtruth); got {match_count}"
        )
    return match_count


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


def _snapshot(ctx: RecipeContext, live: bool) -> dict[str, Any]:
    if not live:
        return {}
    return dict(ctx.tools.call("harness.snowflake.snapshot", {}))


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
