from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_129988557


RECIPE_ID = "129988557"
SEED_TYPE = "webhook_agentic_not_interested_variant"
TRACK = "live_snowflake_slack_lookup_sheets_agentic_not_interested"
TRIGGER_PROVIDER = "workato_webhooks"
TRIGGER_NAME = "new_event"
TRIGGER_AS = "97425b71"
WEBHOOK_SUFFIX = "Not Interested in Agentic"
SQL_STEP_AS = "2d42fc76"
SLACK_STEP_AS = "d10ecead"
SHEETS_STEP_AS = "9666ca53"
DEAD_STEP_AS = ("6db82a50", "38168b5e", "b4374a34", "00c04c9d")
RAW_SPREADSHEET_ID = "1zB6BMnNrUJng_Xrlh73W4IUbXZOOP1LirxyWGGUdH1E"
RAW_SHEET_NAME = "Not Interested"
SHEET_HEADERS = ("USER_NAME", "WORKSPACE_ID", "WORKSPACE_EMAIL", "ACCOUNT_OWNER_EMAIL", "TIMESTAMP")
LIVE_LOOKUP_EMAIL = "jamie.lee@corp.example"
WORKSPACE_DIM_TABLE = "product.workato_usage.workspace_dim"
ACCOUNT_TABLE = "product.salesforce.account"
USER_TABLE = "product.salesforce.user"
SNOWFLAKE_TABLES = (WORKSPACE_DIM_TABLE, ACCOUNT_TABLE, USER_TABLE)
RESOLVED_SQL_TEMPLATE = (
    "select u.* from product.workato_usage.workspace_dim wd\n"
    "join product.salesforce.account a\n"
    "on wd.sales_account_id = a.id\n"
    "join product.salesforce.user u\n"
    "on a.owner_id = u.id\n"
    "where workspace_id = ifnull('{current_team}','{user_id}')"
)


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "workato_webhooks", "name": "new_event", "as": "97425b71", "skip": false, "input": {"request": {"headers_schema": "[{\"control_type\":\"text\",\"label\":\"Accept\",\"type\":\"string\",\"name\":\"accept\"},{\"control_type\":\"text\",\"label\":\"Accept encoding\",\"type\":\"string\",\"name\":\"accept_encoding\"},{\"control_type\":\"text\",\"label\":\"Accept language\",\"type\":\"string\",\"name\":\"accept_language\"},{\"control_type\":\"text\",\"label\":\"Cache control\",\"type\":\"string\",\"name\":\"cache_control\"},{\"control_type\":\"text\",\"label\":\"Upgrade insecure requests\",\"type\":\"string\",\"name\":\"upgrade_insecure_requests\"},{\"control_type\":\"text\",\"label\":\"User agent\",\"type\":\"string\",\"name\":\"user_agent\"},{\"control_type\":\"text\",\"label\":\"X amzn trace ID\",\"type\":\"string\",\"name\":\"x_amzn_trace_id\"},{\"control_type\":\"text\",\"label\":\"X correlation ID\",\"type\":\"string\",\"name\":\"x_correlation_id\"},{\"control_type\":\"text\",\"label\":\"X forwarded for\",\"type\":\"string\",\"name\":\"x_forwarded_for\"},{\"control_type\":\"text\",\"label\":\"X forwarded port\",\"type\":\"string\",\"name\":\"x_forwarded_port\"},{\"control_type\":\"text\",\"label\":\"X forwarded proto\",\"type\":\"string\",\"name\":\"x_forwarded_proto\"},{\"control_type\":\"text\",\"label\":\"X request ID\",\"type\":\"string\",\"name\":\"x_request_id\"}]", "payload_schema": "[{\"control_type\":\"text\",\"label\":\"Name\",\"type\":\"string\",\"name\":\"name\"},{\"control_type\":\"text\",\"label\":\"Account\",\"type\":\"string\",\"name\":\"account\"},{\"control_type\":\"text\",\"label\":\"User ID\",\"type\":\"string\",\"name\":\"user_id\"},{\"control_type\":\"number\",\"label\":\"Current team\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"current_team\"},{\"control_type\":\"text\",\"label\":\"Email\",\"type\":\"string\",\"name\":\"email\"},{\"control_type\":\"text\",\"label\":\"Server\",\"type\":\"string\",\"name\":\"server\"},{\"control_type\":\"number\",\"label\":\"Timestamp\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"timestamp\"}]", "query_params": "[]", "webhook_type": "json"}, "webhook_suffix": "Not Interested in Agentic"}, "block": [{"number": 2, "keyword": "action", "provider": "snowflake", "name": "search_rows_sql", "as": "2d42fc76", "skip": false, "input": {"parameters": {"schema": "[]"}, "sql": "select u.* from product.workato_usage.workspace_dim wd\njoin product.salesforce.account a\non wd.sales_account_id = a.id\njoin product.salesforce.user u\non a.owner_id = u.id\nwhere workspace_id = ifnull('#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"97425b71\",\"path\":[\"payload\", \"current_team\"]}')}','#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"97425b71\",\"path\":[\"payload\", \"user_id\"]}')}')"}, "block": []}, {"number": 3, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"2d42fc76\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"email\"]}')}", "operand": "present", "rhs": ""}], "operand": "and", "type": "compound"}, "block": [{"number": 4, "keyword": "action", "provider": "slack", "name": "get_user_by_email", "as": "d10ecead", "skip": false, "input": {"email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"2d42fc76\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"email\"]}')}"}, "block": []}]}, {"number": 5, "keyword": "action", "provider": "slack_bot", "name": "post_bot_message", "as": "6db82a50", "skip": true, "block": []}, {"number": 6, "keyword": "action", "provider": "google_sheets", "name": "add_spreadsheet_row_v4", "as": "9666ca53", "skip": false, "input": {"data": {"col_1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"97425b71\",\"path\":[\"payload\", \"name\"]}')}", "col_2": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"97425b71\",\"path\":[\"payload\", \"account\"]}')}", "col_3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"97425b71\",\"path\":[\"payload\", \"user_id\"]}')}", "col_4": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"97425b71\",\"path\":[\"payload\", \"current_team\"]}')}", "col_5": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"97425b71\",\"path\":[\"payload\", \"email\"]}')}"}, "is_top_left": "false", "sheet": "Not Interested", "spreadsheet": "1zB6BMnNrUJng_Xrlh73W4IUbXZOOP1LirxyWGGUdH1E", "team_drives": "my_drive"}, "block": []}, {"number": 7, "keyword": "action", "provider": "slack_bot", "name": "post_bot_message", "as": "38168b5e", "skip": true, "block": []}, {"number": 8, "keyword": "action", "provider": "gmail", "name": "send_mail", "as": "b4374a34", "skip": true, "block": []}, {"number": 9, "keyword": "action", "provider": "gmail", "name": "send_mail", "as": "00c04c9d", "skip": true, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[int, str, str, str]] = [
    (2, SQL_STEP_AS, "snowflake", "search_rows_sql"),
    (4, SLACK_STEP_AS, "slack", "get_user_by_email"),
    (6, SHEETS_STEP_AS, "google_sheets", "add_spreadsheet_row_v4"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "slack_bot.get_user_by_email",
    "google_sheets.add_spreadsheet_row_v4",
]
ALLOWED_TOOLS: list[str] = list(EXPECTED_RAW_TOOLS)
REQUIRED_EXPECT_KEYS = (
    "branch",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "resolved_sql",
    "matched_email",
    "slack_lookup_expected",
    "sheet_row",
    "sql_result_rows",
)
BRANCHES = (
    "owner_found_lookup_and_row",
    "no_workspace_match_row_only",
    "owner_without_email_row_only",
)
SQL_RESULT_WITNESS_FIELDS = (
    "ID",
    "EMAIL",
    "NAME",
    "ACTIVE",
    "DEPARTMENT",
    "DIVISION",
    "SALES_TEAM__C",
    "SUB_TEAM__C",
    "SYSTEM_ACCOUNT",
)
SQL_ARGUMENT_EQUIVALENCE = {
    "sql": "result_semantics",
    "evidence_pointer": "expect.sql_result_rows",
}
_EXPECT_ITEM_KEYS = {
    "tool", "table_id", "lookup_table_id", "match_fields", "channel",
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
    "argument_equivalence",
}
_EXPECT_VALUE_KEYS = {
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
    "argument_equivalence",
}
PAYLOAD_KEYS = ("name", "account", "user_id", "current_team", "email", "server", "timestamp")
_SQL_SAFE_RE = re.compile(r"^[A-Za-z0-9 ._@\-]+$")
_ASCII_RE = re.compile(r"^[\x20-\x7e]*$")
REQUIRED_COLUMNS = {
    WORKSPACE_DIM_TABLE: ("WORKSPACE_ID", "SALES_ACCOUNT_ID"),
    ACCOUNT_TABLE: ("ID", "OWNER_ID"),
    USER_TABLE: ("ID", "EMAIL"),
}


def validate_129988557(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    if str((raw.get("input") or {}).get("webhook_suffix") or "") != WEBHOOK_SUFFIX:
        raise RuntimeError(f"recipe {RECIPE_ID} webhook suffix changed")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    # Semantic pins over the drift-prone bits (the tree pin holds the bytes;
    # these name the trap when one changes).
    sql_node = next(node for node in _walk_nodes(raw) if str(node.get("as") or "") == SQL_STEP_AS)
    sql = str((sql_node.get("input") or {}).get("sql") or "")
    if "ifnull('#{" not in sql or '"current_team"' not in sql.replace("\\", "") or '"user_id"' not in sql.replace("\\", ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} step-2 SQL no longer quotes both payload pills inside "
            f"ifnull(...) -- the dead-fallback-arm analysis no longer holds: {sql!r}"
        )
    if re.search(r"\bORDER\s+BY\b", sql, flags=re.I) or (sql_node.get("input") or {}).get("orderby"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} step-2 SQL grew an ORDER BY -- the <=1-row seed "
            "determinism rule must be revisited"
        )
    for table in SNOWFLAKE_TABLES:
        if table not in sql:
            raise RuntimeError(f"recipe {RECIPE_ID} step-2 SQL no longer reads {table}")
    if re.search(r"\bcurrent_(?:date|timestamp)\b|\bsysdate\b", sql, flags=re.I):
        raise RuntimeError(
            f"recipe {RECIPE_ID} step-2 SQL grew a time function -- seeds must now pin "
            "current_time (they intentionally do not)"
        )
    sheets_node = next(node for node in _walk_nodes(raw) if str(node.get("as") or "") == SHEETS_STEP_AS)
    labels = _sheet_labels(sheets_node)
    if labels != list(SHEET_HEADERS):
        raise RuntimeError(f"recipe {RECIPE_ID} sheet column labels changed: {labels}")
    dead = [str(node.get("as") or "") for node in _walk_nodes(raw) if node.get("skip")]
    if dead != list(DEAD_STEP_AS):
        raise RuntimeError(f"recipe {RECIPE_ID} dead-step set changed: {dead}")
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
        "webhook_suffix": WEBHOOK_SUFFIX,
        "raw_spreadsheet_id": RAW_SPREADSHEET_ID,
        "raw_sheet_name": RAW_SHEET_NAME,
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


def seed_129988557(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_129988557(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    payload = _require_trigger_shape(trigger)
    expect = data.get("expect")
    _require_expect_common(expect)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["google_sheets", "snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must carry exactly google_sheets + snowflake_live "
            f"sections; got {sorted(seed_in.keys()) if isinstance(seed_in, dict) else seed_in!r}"
        )
    _require_sheets_section(seed_in["google_sheets"])
    matched_rows = _require_snowflake_section(seed_in["snowflake_live"], payload)
    _require_expect_groundtruth(expect, payload, matched_rows)
    # All validation passed -- only now touch live state.
    sheets_seed = ctx.tools.call("harness.google_sheets.seed_rows", {"sheets": deepcopy(seed_in["google_sheets"])})
    if not sheets_seed.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Sheets seed failed: {sheets_seed}")
    provision = ctx.tools.call("harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": deepcopy(expect),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "google_sheets_seed_response": deepcopy(sheets_seed),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_129988557(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_129988557(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed carries no snowflake_live state")
    raw_execution: dict[str, Any] | None = None
    initial_snapshot: dict[str, Any] = {}
    final_snapshot: dict[str, Any] = {}
    cleanup: dict[str, Any] | None = None
    try:
        initial_snapshot = _snapshot(ctx)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx)
    finally:
        # The 3 product.* tables are benchmark-owned create-or-replace live
        # state: drop them even when execution fails (cleanup principle). The
        # benchmark sheet tab needs no post-run cleanup -- every seed fully
        # overwrites it (replace_rows) and the appended row is the observable.
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
    result["verifier"] = verify_129988557(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> dict[str, Any]:
    if sorted(trigger.keys()) != ["payload"] or not isinstance(trigger.get("payload"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'payload': {{...}}}}; "
            f"got {sorted(trigger.keys())}"
        )
    payload = trigger["payload"]
    if sorted(payload.keys()) != sorted(PAYLOAD_KEYS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} payload must carry exactly {sorted(PAYLOAD_KEYS)}; "
            f"got {sorted(payload.keys())}"
        )
    for key in ("name", "account", "user_id", "email", "server"):
        value = payload.get(key)
        if not isinstance(value, str) or not value or not _ASCII_RE.fullmatch(value):
            raise RuntimeError(
                f"recipe {RECIPE_ID} payload.{key} must be a non-empty printable-ASCII "
                f"string; got {value!r}"
            )
    current_team = payload.get("current_team")
    if (
        not isinstance(current_team, int)
        or isinstance(current_team, bool)
        or current_team < 0
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} payload.current_team must be a non-negative integer "
            f"consistent with the published numeric webhook field; got {current_team!r}"
        )
    if not _SQL_SAFE_RE.fullmatch(payload["user_id"]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} payload.user_id lands in the quoted ifnull fallback arm: "
            f"no quotes/backslashes; got {payload['user_id']!r}"
        )
    if not isinstance(payload.get("timestamp"), (int, float)) or isinstance(payload.get("timestamp"), bool):
        raise RuntimeError(
            f"recipe {RECIPE_ID} payload.timestamp must be a number (schema "
            f"float_conversion; it is never dereferenced by live steps); "
            f"got {payload.get('timestamp')!r}"
        )
    return payload


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


def _require_sheets_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["headers", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.google_sheets must be exactly "
            f"{{'headers': [...], 'rows': []}}"
        )
    if section["headers"] != list(SHEET_HEADERS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.google_sheets.headers must be {list(SHEET_HEADERS)} "
            f"(the recipe's column labels); got {section['headers']!r}"
        )
    if section["rows"] != []:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.google_sheets.rows must be [] -- the appended row "
            f"must land at row_number 2 deterministically; got {section['rows']!r}"
        )


def _require_snowflake_section(section: Any, payload: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the SQL uses no time functions -> current_time must NOT be declared)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted(SNOWFLAKE_TABLES):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{sorted(SNOWFLAKE_TABLES)}; got "
            f"{sorted(tables.keys()) if isinstance(tables, dict) else tables!r}"
        )
    specs: dict[str, dict[str, Any]] = {}
    for table in SNOWFLAKE_TABLES:
        spec = tables[table]
        if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {table} spec must be exactly {{'columns': ..., 'rows': ...}}"
            )
        columns = spec["columns"]
        rows = spec["rows"]
        if not isinstance(columns, dict) or not isinstance(rows, list):
            raise RuntimeError(f"recipe {RECIPE_ID} {table} columns/rows malformed")
        for required in REQUIRED_COLUMNS[table]:
            if required not in columns:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {table} must declare column {required} "
                    f"(join/deref column); got {sorted(columns)}"
                )
        for row in rows:
            if not isinstance(row, dict) or set(row) - set(columns):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {table} row carries undeclared columns: {row!r}"
                )
            for key, value in row.items():
                if value is None or isinstance(value, bool):
                    continue
                if not isinstance(value, str) or not _ASCII_RE.fullmatch(value):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} {table} values must be printable-ASCII "
                        f"strings, booleans or null (deterministic renders): {row!r}"
                    )
        specs[table] = spec
    # Offline groundtruth of the live 3-table join (u.* projection): the seeds
    # must resolve to AT MOST one user row -- the SELECT has no ORDER BY, so a
    # 2+-row match would make `rows current_item` (= rows[0]) nondeterministic
    # live. Never author that.
    current_team = str(payload["current_team"])
    matched: list[dict[str, Any]] = []
    for wd_row in specs[WORKSPACE_DIM_TABLE]["rows"]:
        if str(wd_row.get("WORKSPACE_ID") or "") != current_team:
            continue
        for account_row in specs[ACCOUNT_TABLE]["rows"]:
            if account_row.get("ID") != wd_row.get("SALES_ACCOUNT_ID"):
                continue
            for user_row in specs[USER_TABLE]["rows"]:
                if user_row.get("ID") == account_row.get("OWNER_ID"):
                    matched.append(dict(user_row))
    if len(matched) > 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seeds derive {len(matched)} joined user rows for "
            f"workspace {current_team!r}; the un-ordered SELECT admits at most 1"
        )
    return matched


def _require_expect_groundtruth(
    expect: dict[str, Any],
    payload: dict[str, Any],
    matched_rows: list[dict[str, Any]],
) -> None:
    branch = expect["branch"]
    matched_email = matched_rows[0].get("EMAIL") if matched_rows else None
    if branch == "owner_found_lookup_and_row":
        if len(matched_rows) != 1 or matched_email != LIVE_LOOKUP_EMAIL:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {branch} must derive exactly 1 user row whose EMAIL "
                f"is the pinned live workspace member {LIVE_LOOKUP_EMAIL!r} (a non-member "
                f"email is a graceful not_found that feeds only dead steps -- never "
                f"author it); derived {matched_rows!r}"
            )
        lookup = True
    elif branch == "no_workspace_match_row_only":
        if matched_rows:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {branch} must derive zero joined rows; "
                f"derived {matched_rows!r}"
            )
        lookup = False
    elif branch == "owner_without_email_row_only":
        if len(matched_rows) != 1 or matched_email not in (None, ""):
            raise RuntimeError(
                f"recipe {RECIPE_ID} {branch} must derive exactly 1 user row with a "
                f"NULL/'' EMAIL (proves the IF guards the field, not the row); "
                f"derived {matched_rows!r}"
            )
        lookup = False
    else:
        raise RuntimeError(f"recipe {RECIPE_ID} unknown branch {branch!r}")
    resolved_sql = RESOLVED_SQL_TEMPLATE.format(
        current_team=payload["current_team"], user_id=payload["user_id"]
    )
    sheet_row = {
        "USER_NAME": payload["name"],
        "WORKSPACE_ID": payload["account"],
        "WORKSPACE_EMAIL": payload["user_id"],
        "ACCOUNT_OWNER_EMAIL": payload["current_team"],
        "TIMESTAMP": payload["email"],
    }
    expected_tools = ["snowflake.search_rows_sql"]
    if lookup:
        expected_tools.append("slack_bot.get_user_by_email")
    expected_tools.append("google_sheets.add_spreadsheet_row_v4")
    sql_result_rows = [
        {
            field.lower(): row.get(field)
            for field in SQL_RESULT_WITNESS_FIELDS
        }
        for row in matched_rows
    ]
    checks = (
        expect.get("executed_action_count") == len(expected_tools),
        expect.get("tools") == expected_tools,
        expect.get("resolved_sql") == resolved_sql,
        expect.get("matched_email") == matched_email,
        expect.get("slack_lookup_expected") is lookup,
        expect.get("sheet_row") == sheet_row,
        expect.get("sql_result_rows") == sql_result_rows,
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} {branch} expect block contradicts the derived "
            f"groundtruth (resolved_sql {resolved_sql!r}, matched_email "
            f"{matched_email!r}, sheet_row {sheet_row!r}): {expect!r}"
        )
    expected_items: list[dict[str, Any]] = [
        {
            "tool": "snowflake.search_rows_sql",
            "argument_equivalence": SQL_ARGUMENT_EQUIVALENCE,
            "args_contains": {"sql": resolved_sql},
            "result_count": len(matched_rows),
        },
    ]
    if lookup:
        expected_items.append(
            {
                "tool": "slack_bot.get_user_by_email",
                "args_contains": {"email": LIVE_LOOKUP_EMAIL},
            }
        )
    expected_items.append(
        {
            "tool": "google_sheets.add_spreadsheet_row_v4",
            "args_contains": {
                "spreadsheet": RAW_SPREADSHEET_ID,
                "sheet": RAW_SHEET_NAME,
                "data": sheet_row,
            },
            "result_count": 1,
        }
    )
    if expect.get("tool_expectations") != expected_items:
        raise RuntimeError(
            f"recipe {RECIPE_ID} {branch} tool_expectations must pin exactly the derived "
            f"sql/lookup/sheet items; expected {expected_items!r}, got "
            f"{expect.get('tool_expectations')!r}"
        )


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    out: dict[str, Any] = {}
    out.update(ctx.tools.call("harness.snowflake.snapshot", {}))
    out["google_sheets"] = ctx.tools.call("harness.google_sheets.snapshot", {})
    return out


def _sheet_labels(node: dict[str, Any]) -> list[str]:
    for entry in node.get("extended_input_schema") or []:
        if isinstance(entry, dict) and entry.get("name") == "data":
            return [
                str(prop.get("label") or "")
                for prop in entry.get("properties") or []
                if isinstance(prop, dict)
            ]
    return []


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
