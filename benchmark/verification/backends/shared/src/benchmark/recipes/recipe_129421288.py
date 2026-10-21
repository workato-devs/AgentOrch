from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_129421288


RECIPE_ID = "129421288"
SEED_TYPE = "scheduled_snowflake_gong_activity_slack_dm_variant"
TRACK = "live_snowflake_slack_gong_activity_dm"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "e8e4e424"
CONVERSATION_TABLE = "edw_db.salesforce.conversation"
ACCOUNT_TABLE = "workato_business_systems.salesforce.account"
USER_TABLE = "workato_business_systems.salesforce.user"
USER_ROLE_TABLE = "workato_business_systems.salesforce.user_role"
SEED_TABLES = [CONVERSATION_TABLE, ACCOUNT_TABLE, USER_TABLE, USER_ROLE_TABLE]
# Weekly (Friday 00:29 America/New_York) scheduled recipe; the trigger is
# payload-less and no time pills are read (the WHERE date is the recipe's own
# hardcoded -- and <anon>-anonymized -- constant, kept verbatim).
#   2  snowflake.search_rows_sql 58f6839f (LIVE): 4-table JOIN
#      (CONVERSATION x ACCOUNT x USER x USER_ROLE) selecting the DISTINCT
#      (GROUP BY 1) emails of CS-CSM-% expansion CSMs with federation ids who
#      participated in Gong calls since the anonymized cutoff that still
#      require Success Activities. orderby input 'success_owner_email' is
#      appended as ORDER BY by the executor (engine fix 4d133d1e -- the
#      multi-row GROUP BY output order is deterministic); limit 50000.
#   3  FOREACH 87a3b671 over rows (repeat_mode simple):
#      4  TRY>
#      5    slack_bot.get_user_by_email b1f3e255 (LIVE users.lookupByEmail;
#           unknown emails return ok+not_found -- never an exception)
#      6    IF b1f3e255.id present ->
#      7      slack_bot.post_bot_message cf34a028: DM to the resolved user id
#             (block section_with_button_with_long_action; the live text is
#             the rendered section_text -- button metadata is Workbot-only).
#             The resolved LIVE user id MUST be redirected through
#             seed.slack_channel_map {'<uid>': '__override__'} so the post
#             lands in the benchmark override channel, never a real DM.
#      8    CATCH b2ccc6d0 (max_retry_count 3, retry_interval 10) ->
#      9      STOP stop_with_error=true, reason '#{catch.type} : #{catch.message}'
# CATCH/STOP is proven live-unreachable deterministically: users_not_found
# returns ok+not_found (IF-false is the reachable negative branch) and posts
# to the mapped override channel succeed; only a real Slack/API infra failure
# (with 3 retries) could fire it, which cannot be seeded deterministically.
# Documented here instead of forcing a fake variant.
# The anon-wrapped createddate literal '<anon>2024-01-01</anon>' is executed
# verbatim against live Snowflake; createddate is seeded as a STRING column
# whose values keep the same '<anon>YYYY-MM-DD</anon>' wrapper, so the >=
# comparison behaves exactly like the underlying date window (identical
# prefix, lexicographic tail).
SQL = (
    "SELECT u.email AS success_owner_email\n"
    "  FROM EDW_DB.SALESFORCE.CONVERSATION c\n"
    " INNER JOIN WORKATO_BUSINESS_SYSTEMS.SALESFORCE.ACCOUNT a\n"
    "    ON c.gong__primary_account = a.id\n"
    " INNER JOIN WORKATO_BUSINESS_SYSTEMS.SALESFORCE.USER u\n"
    "    ON a.expansion_csm__c = u.id\n"
    "   AND u.federationidentifier IS NOT NULL\n"
    "   AND c.gong__participants_emails__c ILIKE '%' || u.email || '%'\n"
    " INNER JOIN WORKATO_BUSINESS_SYSTEMS.SALESFORCE.USER_ROLE ur\n"
    "    ON u.userroleid = ur.id\n"
    "   AND ur.name LIKE 'CS-CSM-%'\n"
    " WHERE c.createddate >= '<anon>2024-01-01</anon>'\n"
    "   AND c.activity_tracking_action__c = 'Activity Required'\n"
    " GROUP BY 1"
)
ORDERBY = "success_owner_email"
SECTION_TEXT = (
    ":todo_done: You have Gong calls that require Success Activities.  "
    "Please log the details of the customer interactions."
)
LOOKUP_EMAIL_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"87a3b671\","
    "\"path\":[\"success_owner_email\"]}')}"
)
IF_LHS = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"b1f3e255\","
    "\"path\":[\"id\"]}')}"
)
CHANNEL_PILL = IF_LHS
FOREACH_SOURCE = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"58f6839f\","
    "\"path\":[\"rows\"]}')}"
)
STOP_REASON = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"b2ccc6d0\","
    "\"path\":[\"type\"]}')} : "
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"b2ccc6d0\","
    "\"path\":[\"message\"]}')}"
)
EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("snowflake", "search_rows_sql", "58f6839f"),
    ("slack_bot", "get_user_by_email", "b1f3e255"),
    ("slack_bot", "post_bot_message", "cf34a028"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "slack_bot.get_user_by_email",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "slack_bot.get_user_by_email",
    "slack.post_message",
]


def validate_129421288(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed")
    trigger_config = raw.get("input") or {}
    if (
        str(trigger_config.get("days_of_week") or "") != "5"
        or str(trigger_config.get("time_unit") or "") != "weeks"
        or str(trigger_config.get("trigger_at") or "") != "00:29:00"
        or str(trigger_config.get("trigger_every") or "") != "1"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} schedule config changed: {trigger_config}")
    actions = _collect_keyword(raw, "action")
    actual = [(a.get("provider"), a.get("name"), a.get("as")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    search_input = _input(actions[0])
    if search_input.get("sql") != SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} SQL changed: {search_input.get('sql')!r}")
    if str(search_input.get("orderby") or "") != ORDERBY:
        raise RuntimeError(f"recipe {RECIPE_ID} orderby changed")
    if str(search_input.get("limit") or "") != "50000":
        raise RuntimeError(f"recipe {RECIPE_ID} limit changed")
    lookup_input = _input(actions[1])
    if lookup_input.get("email") != LOOKUP_EMAIL_PILL:
        raise RuntimeError(f"recipe {RECIPE_ID} lookup email pill changed: {lookup_input}")
    post_input = _input(actions[2])
    if post_input.get("channel") != CHANNEL_PILL:
        raise RuntimeError(f"recipe {RECIPE_ID} post channel pill changed: {post_input}")
    blocks = post_input.get("blocks")
    if (
        not isinstance(blocks, list)
        or len(blocks) != 1
        or blocks[0].get("block_type") != "section_with_button_with_long_action"
        or blocks[0].get("section_text") != SECTION_TEXT
        or blocks[0].get("button_title") != "Log Success Activity"
        or blocks[0].get("button_type") != "bot_command"
        or str(blocks[0].get("bot_command") or "") != "47040865"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} post blocks changed: {blocks}")
    foreachs = _collect_keyword(raw, "foreach")
    if (
        len(foreachs) != 1
        or foreachs[0].get("as") != "87a3b671"
        or foreachs[0].get("repeat_mode") != "simple"
        or _input(foreachs[0]).get("source") != FOREACH_SOURCE
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} foreach changed")
    ifs = _collect_keyword(raw, "if")
    if len(ifs) != 1 or _single_condition(ifs[0]) != (IF_LHS, "present", ""):
        raise RuntimeError(f"recipe {RECIPE_ID} IF step 6 changed")
    catches = _collect_keyword(raw, "catch")
    if (
        len(catches) != 1
        or catches[0].get("as") != "b2ccc6d0"
        or str(_input(catches[0]).get("max_retry_count") or "") != "3"
        or str(_input(catches[0]).get("retry_interval") or "") != "10"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} catch block changed")
    stops = _collect_keyword(raw, "stop")
    if len(stops) != 1 or stops[0].get("number") != 9:
        raise RuntimeError(f"recipe {RECIPE_ID} stop step changed")
    stop_input = _input(stops[0])
    if str(stop_input.get("stop_with_error") or "") != "true" or stop_input.get("stop_reason") != STOP_REASON:
        raise RuntimeError(f"recipe {RECIPE_ID} stop input changed: {stop_input}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": [
            {
                "number": action.get("number"),
                "provider": action.get("provider"),
                "name": action.get("name"),
                "as": action.get("as"),
            }
            for action in actions
        ],
    }


def seed_129421288(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_129421288(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    snowflake_seed = seed_in.get("snowflake_live")
    _require_snowflake_tables(RECIPE_ID, snowflake_seed, SEED_TABLES)
    channel_map = seed_in.get("slack_channel_map")
    if not isinstance(channel_map, dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must declare seed.slack_channel_map explicitly "
            "(may be empty only when no Slack post is reachable)"
        )
    for uid, target in channel_map.items():
        if not str(uid).startswith("U"):
            raise RuntimeError(f"recipe {RECIPE_ID} slack_channel_map key must be a user id: {uid!r}")
        if target != "__override__":
            raise RuntimeError(
                f"recipe {RECIPE_ID} slack_channel_map[{uid!r}] must be '__override__' -- "
                "benchmark posts never go to a real DM or explicit foreign channel"
            )
    expect = data.get("expect")
    if not isinstance(expect, dict) or not isinstance(expect.get("posted_texts"), list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must declare expect.posted_texts "
            "(exact list of rendered Slack texts; may be empty)"
        )
    if expect["posted_texts"] and not channel_map:
        raise RuntimeError(
            f"recipe {RECIPE_ID} variants expecting Slack posts must map every resolved "
            "user id in seed.slack_channel_map"
        )
    provision = ctx.tools.call("harness.snowflake_live.seed_tables", {"snowflake": snowflake_seed})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "slack_channel_map": deepcopy(channel_map),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    for key, value in seed_in.items():
        if key in {"snowflake_live", "slack_channel_map"}:
            continue
        if isinstance(value, dict):
            out[str(key)] = deepcopy(value)
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    return attach_variant(out, ctx)


def run_129421288(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_129421288(raw)
    trigger = seed.get("trigger")
    if not isinstance(trigger, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing trigger object")
    if not isinstance(seed.get("slack_channel_map"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing slack_channel_map")
    expect = seed.get("expect") if isinstance(seed.get("expect"), dict) else {}
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    snowflake_cleanup: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        if isinstance(seed.get("snowflake_live"), dict):
            snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": trigger,
            "track": seed.get("track"),
            "expect": expect,
            "slack_channel_map": deepcopy(seed.get("slack_channel_map")),
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "cleanup_response": {"snowflake_live": snowflake_cleanup},
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_129421288(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_snowflake_tables(recipe_id: str, snowflake_seed: Any, tables: list[str]) -> None:
    if not isinstance(snowflake_seed, dict) or not isinstance(snowflake_seed.get("tables"), dict):
        raise RuntimeError(f"recipe {recipe_id} requires seed.snowflake_live.tables")
    extra_tables = set(snowflake_seed["tables"]) - set(tables)
    if extra_tables:
        raise RuntimeError(
            f"recipe {recipe_id} seed declares unexpected Snowflake tables: {sorted(extra_tables)}"
        )
    for table in tables:
        spec = snowflake_seed["tables"].get(table)
        if not isinstance(spec, dict):
            raise RuntimeError(
                f"recipe {recipe_id} seed must define snowflake_live.tables[{table!r}] explicitly"
            )
        columns = spec.get("columns")
        if not isinstance(columns, dict) or not columns or not all(
            isinstance(kind, str) and kind.strip() for kind in columns.values()
        ):
            raise RuntimeError(
                f"recipe {recipe_id} snowflake_live table {table} must declare explicit column types"
            )
        rows = spec.get("rows")
        if not isinstance(rows, list):
            raise RuntimeError(
                f"recipe {recipe_id} snowflake_live table {table} must declare rows (may be empty)"
            )
        lower_columns = {str(name).strip().lower() for name in columns}
        for row in rows:
            if not isinstance(row, dict):
                raise RuntimeError(f"recipe {recipe_id} snowflake_live table {table} rows must be objects")
            extra = {str(key).strip().lower() for key in row} - lower_columns
            if extra:
                raise RuntimeError(
                    f"recipe {recipe_id} snowflake_live table {table} row uses undeclared columns: {sorted(extra)}"
                )


def _collect_keyword(node: dict[str, Any], keyword: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == keyword and not child.get("skip"):
            found.append(child)
        found.extend(_collect_keyword(child, keyword))
    return found


def _input(node: dict[str, Any]) -> dict[str, Any]:
    value = node.get("input")
    return value if isinstance(value, dict) else {}


def _single_condition(node: dict[str, Any]) -> tuple[str, str, str]:
    conditions = _input(node).get("conditions")
    if not isinstance(conditions, list) or len(conditions) != 1 or not isinstance(conditions[0], dict):
        raise RuntimeError(f"recipe {RECIPE_ID} IF step {node.get('number')} is not a single condition")
    condition = conditions[0]
    return (
        str(condition.get("lhs") or ""),
        str(condition.get("operand") or ""),
        str(condition.get("rhs") or ""),
    )


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("snowflake_live"), dict):
        out.update(ctx.tools.call("harness.snowflake.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
