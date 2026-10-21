from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_108028920


RECIPE_ID = "108028920"
SEED_TYPE = "sfdc_hard_deleted_accounts_ctas_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "027722a7"
SQL_STEP_AS = "0be77de3"
CATCH_AS = "ddf5dd60"
POST_STEP_AS = "1ffedbe4"
RAW_CHANNEL = "C07594FG2ER"
# The recipe's 3-part production names; seeds register them verbatim so the
# snowflake_live boundary rewrites every reference (FROM + LEFT JOIN + the
# CTAS target itself) into the benchmark database. Registering the CTAS
# TARGET with exactly {'rows': []} is the ownership mechanism: the empty-rows
# spec PRE-DROPS the table at seed (deterministic rerun), participates in
# _rewrite_sql, and is cleanup-owned afterwards (130549575 precedent;
# LIVE-VERIFIED end-to-end by batch-07 triage).
TARGET_TABLE = "product.plg.sfdc_hard_deleted_accounts"
DIM_TABLE = "edw_db.workato_usage.accounts_dim"
SF_ACCOUNT_TABLE = "workato_business_systems.salesforce.account"
DIM_COLUMNS = {
    "account_id": "string",
    "account_name": "string",
    "is_latest": "boolean",
    "is_paying": "boolean",
}
SF_ACCOUNT_COLUMNS = {"id": "string"}

# clock.scheduled_event (as 027722a7, weekly Monday 12:00) -- payload-less:
# trigger_input is exactly {} and seed.trigger {} (declared payload-less
# scheduler tick). Body:
#   TRY (step 2):
#     3  snowflake.run_custom_sql 0be77de3 (LIVE): CREATE OR REPLACE TABLE
#        product.plg.sfdc_hard_deleted_accounts AS SELECT a.account_id,
#        a.account_name FROM edw_db.workato_usage.accounts_dim a LEFT JOIN
#        workato_business_systems.salesforce.account b ON a.account_id = b.id
#        WHERE 1=1 AND is_latest AND is_paying AND b.id IS NULL -- bare
#        boolean predicates + the LEFT-JOIN-NULL arm select exactly the
#        latest paying dim accounts that are hard-deleted from Salesforce.
#        The CTAS returns one status row ('Table SFDC_HARD_DELETED_ACCOUNTS
#        successfully created.') and rows_affected 1 even when the selected
#        set is empty.
#   CATCH (step 4, as ddf5dd60, max_retry_count 0):
#     5  slack_bot.post_bot_message 1ffedbe4 (LIVE slack): channel
#        C07594FG2ER routes to env.slack_channel_override (non-'U' literal);
#        one section_with_text block whose dataset-only anon wrapper renders as
#        '@john.smith something
#        wrong with product.plg.sfdc_hard_deleted_accounts recipe
#        \n\nlink:#{job_context.recipe_url}\nworkspace: plg dev env\n' (the
#        anonymization wrapper is not user-visible; the vestigial
#        second block {button_type: continue_flow} has no block_type and
#        renders nothing) -- catch variants must seed job_context.recipe_url.
#
# Branch mapping (probe-verified offline 2026-07-08 on the current tree; the
# verbatim CTAS + cleanup were LIVE-VERIFIED end-to-end by triage):
# - variant_00 ctas_one_hard_deleted: dim rows cover every exclusion arm
#   (in-SF / non-paying / non-latest) plus one hard-deleted include ->
#   target = exactly that one row.
# - variant_01 ctas_zero_rows: every dim account exists in sf.account ->
#   target created EMPTY (status row still returned) -- proves the
#   LEFT-JOIN-NULL arm is the only include path.
# - variant_02 ctas_multi_rows_null_boolean: sf.account seeded EMPTY (all
#   b.id NULL) -> two includes; a NULL is_latest row is excluded (SQL
#   three-valued logic on the bare boolean) beside a false is_paying row.
# - variant_03 catch_slack_alert: force_action_error on 0be77de3 (sanctioned
#   fault injection -- the CTAS is the only fallible step) -> CATCH -> live
#   Slack alert on the override channel with the seeded recipe_url; the
#   target table is pre-dropped at seed and never created.
#
# Backends: Snowflake LIVE (all 3 registered tables benchmark-owned;
# cleanup drops them in a finally block); Slack LIVE on the catch path only
# (ordinary post, never re-read -- no cleanup per the cleanup principle).
# No current_date/current_timestamp in the SQL -> no
# seed.snowflake_live.current_time. No time deref anywhere -> no seed.now.

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "clock", "name": "scheduled_event", "as": "027722a7", "skip": false, "input": {"days_of_week": "1", "time_unit": "weeks", "trigger_at": "12:00:00", "trigger_every": "1"}, "block": [{"number": 2, "keyword": "try", "provider": "", "name": "", "as": "", "skip": false, "input": {}, "block": [{"number": 3, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql", "as": "0be77de3", "skip": false, "input": {"sql": "create or replace table product.plg.sfdc_hard_deleted_accounts as \n\nselect a.account_id, a.account_name\nfrom edw_db.workato_usage.accounts_dim a\nleft join workato_business_systems.salesforce.account b\n    on a.account_id = b.id\nwhere 1=1\n    and is_latest\n    and is_paying\n    and b.id is null\n    ;", "update_only": "false"}, "block": []}, {"number": 4, "keyword": "catch", "provider": "", "name": "", "as": "ddf5dd60", "skip": false, "input": {"max_retry_count": "0", "retry_interval": "2"}, "block": [{"number": 5, "keyword": "action", "provider": "slack_bot", "name": "post_bot_message", "as": "1ffedbe4", "skip": false, "input": {"blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": "@<anon>john.smith</anon> something wrong with product.plg.sfdc_hard_deleted_accounts recipe \n\nlink:#{_dp('{\"pill_type\":\"job_context\",\"path\":[\"recipe_url\"]}')}\nworkspace: plg dev env\n"}, {"button_type": "continue_flow"}], "channel": "C07594FG2ER"}, "block": []}]}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (SQL_STEP_AS, "snowflake", "run_custom_sql"),
    (POST_STEP_AS, "slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "slack.post_message",
]
REQUIRED_EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "status_row",
    "final_snowflake_tables",
    "cleanup_tables",
    "catch",
    "slack_alert_text",
)


def validate_108028920(raw: dict[str, Any]) -> dict[str, Any]:
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
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "target_table": TARGET_TABLE,
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


def seed_108028920(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_108028920(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (payload-less weekly "
            f"scheduler tick): {trigger!r}"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the snowflake_live section"
        )
    _require_snowflake_section(seed_in["snowflake_live"])
    force = data.get("force_action_error")
    _require_force_shape(force)
    job_context = data.get("job_context")
    if force is not None:
        if not isinstance(job_context, dict) or not str(job_context.get("recipe_url") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must seed job_context.recipe_url "
                "(the alert text dereferences the job_context pill; the engine is "
                "fail-safe on absence which would silently blank the link)"
            )
    elif job_context is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} job_context is only dereferenced on the catch path; "
            "happy variants must omit it"
        )
    expect = data.get("expect")
    _require_expect_shape(expect, force)
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
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_108028920(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_108028920(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    if isinstance(seed.get("force_action_error"), dict) and not ctx.env.slack_channel_override:
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch variants post the live Slack alert to "
            "env.slack_channel_override -- it must be configured"
        )
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect"),
        "force_action_error": deepcopy(seed.get("force_action_error"))
        if isinstance(seed.get("force_action_error"), dict)
        else None,
        "job_context": deepcopy(seed.get("job_context"))
        if isinstance(seed.get("job_context"), dict)
        else None,
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
        # Required cleanup: all three registered tables (two seeded sources +
        # the CTAS-created target) are benchmark-owned live objects -- drop
        # them even on failure. The catch-path Slack post is an ordinary
        # observable (never re-read) -- no cleanup per the cleanup principle.
        snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    details["cleanup_response"] = {"snowflake_live": snowflake_cleanup}
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
    if not (snowflake_cleanup or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake cleanup failed: {snowflake_cleanup}")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_108028920(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_snowflake_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the CTAS uses no current date/time functions, so no current_time)"
        )
    tables = section["tables"]
    expected_keys = sorted([TARGET_TABLE, DIM_TABLE, SF_ACCOUNT_TABLE])
    if not isinstance(tables, dict) or sorted(tables.keys()) != expected_keys:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must register exactly {expected_keys} (all three "
            "3-part production names participate in rewrite + cleanup)"
        )
    if tables[TARGET_TABLE] != {"rows": []}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} CTAS target {TARGET_TABLE} must be exactly {{'rows': []}} "
            f"(pre-drop + rewrite + cleanup ownership); got {tables[TARGET_TABLE]!r}"
        )
    _require_typed_table(tables[DIM_TABLE], DIM_TABLE, DIM_COLUMNS)
    _require_typed_table(tables[SF_ACCOUNT_TABLE], SF_ACCOUNT_TABLE, SF_ACCOUNT_COLUMNS)
    for idx, row in enumerate(tables[DIM_TABLE]["rows"]):
        if not str(row.get("account_id") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} dim row {idx} needs a non-empty account_id "
                f"(the join key): {row!r}"
            )


def _require_typed_table(spec: Any, table: str, columns: dict[str, str]) -> None:
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(f"recipe {RECIPE_ID} table {table} spec must be {{'columns','rows'}}")
    if spec["columns"] != columns:
        raise RuntimeError(f"recipe {RECIPE_ID} table {table} columns must be exactly {columns}")
    rows = spec["rows"]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {table} rows must be a list (may be empty)")
    for idx, row in enumerate(rows):
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
                # Explicit null (e.g. is_latest: null) exercises SQL
                # three-valued logic on the bare boolean predicates.
                continue
            if kind == "boolean" and not isinstance(value, bool):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table} row {idx} {column} must be boolean/null"
                )
            if kind == "string" and not isinstance(value, str):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table} row {idx} {column} must be a string"
                )


def _require_force_shape(force: Any) -> None:
    if force is None:
        return
    if not isinstance(force, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error must be an object")
    if str(force.get("step_as") or "") != SQL_STEP_AS or not str(force.get("error") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error must target step_as {SQL_STEP_AS!r} with an "
            "explicit error message (the CTAS is the only step inside the TRY)"
        )


def _require_expect_shape(expect: Any, force: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if expect.get("executed_action_count") != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} exactly one action executes on either path (the failed "
            "try step never records): executed_action_count must be 1"
        )
    is_catch = force is not None
    if is_catch:
        if expect.get("tools") != ["slack.post_message"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants trace exactly the Slack alert post"
            )
        if expect.get("status_row") is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} the CTAS never runs on the catch path: status_row "
                "must be null"
            )
        catch = expect.get("catch")
        if not isinstance(catch, dict) or set(catch) != {
            "type", "message", "adapter", "action", "line_number"
        }:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must pin the full connector catch payload"
            )
        if not str(expect.get("slack_alert_text") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must pin the exact rendered alert text"
            )
    else:
        if expect.get("tools") != ["snowflake.run_custom_sql"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} happy variants trace exactly the CTAS"
            )
        if not str(expect.get("status_row") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} happy variants must pin the CTAS status row text"
            )
        if expect.get("catch") is not None or expect.get("slack_alert_text") is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} happy variants must pin expect.catch and "
                "expect.slack_alert_text as null"
            )
    tools = expect.get("tools")
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tools, list) or not isinstance(tool_expectations, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools/tool_expectations must be lists")
    if len(tools) != len(tool_expectations):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry"
        )
    final_tables = expect.get("final_snowflake_tables")
    expected_names = sorted([TARGET_TABLE, DIM_TABLE, SF_ACCOUNT_TABLE])
    if not isinstance(final_tables, dict) or sorted(final_tables.keys()) != expected_names:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_snowflake_tables must pin all three "
            f"registered tables {expected_names} (sources unchanged + target contents)"
        )
    if sorted(expect.get("cleanup_tables") or []) != expected_names:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.cleanup_tables must list all three registered tables"
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
        return (
            f"{path}: {json.dumps(actual, default=str)[:200]} != "
            f"{json.dumps(expected, default=str)[:200]}"
        )
    return ""


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
