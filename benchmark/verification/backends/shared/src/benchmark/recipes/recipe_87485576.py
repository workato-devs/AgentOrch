from __future__ import annotations

import json
from typing import Any

from ..context import RecipeContext
from ..variant_input import trigger_input, variant_data
from ..verifier import verify_87485576
from .snowflake_live_recipe_utils import (
    run_live_snowflake_recipe,
    seed_live_snowflake,
    snowflake_seed_base,
)


RECIPE_ID = "87485576"
SEED_TYPE = "scheduled_snowflake_pending_staff_movement_publish_variant"
TRACK = "live_snowflake_pub_sub_publish"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "96cb2b85"
SEARCH_AS = "7e1c2e4f"
FOREACH_AS = "6693f032"
PUBLISH_AS = "3ff46377"
TOPIC_ID = "28798"
MOVEMENT_TABLE = "STAFF_MOVEMENT_LOG"
EMPLOYEE_TABLE = "EMPLOYEE"
SEED_TABLES = [MOVEMENT_TABLE, EMPLOYEE_TABLE]
PENDING_STATUSES = ("Pending Apps Exchange", "Pending Staff Movement", "Pending")

SQL = (
    "SELECT DISTINCT\nE.EMAIL\n\nFROM STAFF_MOVEMENT_LOG EML\nJOIN EMPLOYEE E\n"
    "ON EML.EMPLOYEE_ID = E.ID\n\n"
    "WHERE EML.STATUS IN ('Pending Apps Exchange', 'Pending Staff Movement', 'Pending')"
)

_RAW_PIN_JSON = r"""{"as": "96cb2b85", "block": [{"as": "7e1c2e4f", "block": [], "input": {"limit": "50000", "output_schema": "[{\"name\":\"EMAIL\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"EMAIL\"}]", "sql": "SELECT DISTINCT\nE.EMAIL\n\nFROM STAFF_MOVEMENT_LOG EML\nJOIN EMPLOYEE E\nON EML.EMPLOYEE_ID = E.ID\n\nWHERE EML.STATUS IN ('Pending Apps Exchange', 'Pending Staff Movement', 'Pending')"}, "keyword": "action", "name": "search_rows_sql", "number": 2, "provider": "snowflake", "skip": false}, {"as": "6693f032", "block": [{"as": "3ff46377", "block": [], "input": {"message": {"email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"6693f032\",\"path\":[\"email\"]}')}"}, "topic_id": "28798"}, "keyword": "action", "name": "publish_to_topic", "number": 4, "provider": "workato_pub_sub", "skip": false}], "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"7e1c2e4f\",\"path\":[\"rows\"]}')}"}, "keyword": "foreach", "name": "", "number": 3, "provider": "", "repeat_mode": "simple", "skip": false, "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"7e1c2e4f\",\"path\":[\"rows\"]}')}"}], "input": {"time_unit": "hours", "trigger_every": "1"}, "keyword": "trigger", "name": "scheduled_event", "number": 1, "provider": "clock", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

MOVEMENT_COLUMNS = {"employee_id": "string", "status": "string"}
EMPLOYEE_COLUMNS = {"id": "string", "email": "string"}

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (SEARCH_AS, "snowflake", "search_rows_sql"),
    (PUBLISH_AS, "workato_pub_sub", "publish_to_topic"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_pub_sub.publish_to_topic",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_pub_sub.publish_to_topic",
]
BRANCHES = (
    "three_pending_published",
    "distinct_dedupes_email",
    "zero_pending",
    "join_drops_orphan_movement",
)
REQUIRED_EXPECT_KEYS = (
    "branch",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "sql_row_count",
    "published_emails",
)


def validate_87485576(raw: dict[str, Any]) -> dict[str, Any]:
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
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    search_input = actions[0].get("input") or {}
    if search_input.get("sql") != SQL or str(search_input.get("limit") or "") != "50000":
        raise RuntimeError(f"recipe {RECIPE_ID} search SQL/limit changed: {search_input}")
    publish_input = actions[1].get("input") or {}
    if str(publish_input.get("topic_id") or "") != TOPIC_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} publish topic changed: {publish_input}")
    message = publish_input.get("message")
    if not isinstance(message, dict) or sorted(message.keys()) != ["email"]:
        raise RuntimeError(f"recipe {RECIPE_ID} publish message shape changed: {message}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "topic_id": TOPIC_ID,
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


def seed_87485576(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_87485576(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (payload-less scheduler tick)"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the snowflake_live section; "
            f"got {sorted(seed_in.keys()) if isinstance(seed_in, dict) else seed_in!r}"
        )
    movements, employees = _require_snowflake_section(seed_in["snowflake_live"])
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    branch = expect.get("branch")
    if branch not in BRANCHES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch must be one of {BRANCHES}; got {branch!r}")

    # Derive the query result exactly like live Snowflake: INNER JOIN on
    # employee id, IN-list status filter, DISTINCT emails.
    email_by_id = {row["id"]: row["email"] for row in employees}
    pending = [row for row in movements if row["status"] in PENDING_STATUSES]
    joined = [row for row in pending if row["employee_id"] in email_by_id]
    orphans = [row for row in pending if row["employee_id"] not in email_by_id]
    emails = sorted({email_by_id[row["employee_id"]] for row in joined})
    if expect.get("published_emails") != emails:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.published_emails must be the SORTED distinct pending "
            f"emails {emails}; got {expect.get('published_emails')!r}"
        )
    if expect.get("sql_row_count") != len(emails):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.sql_row_count must equal the DISTINCT email count "
            f"({len(emails)})"
        )
    if branch == "three_pending_published":
        statuses = {row["status"] for row in joined}
        if statuses != set(PENDING_STATUSES) or len(emails) != 3:
            raise RuntimeError(
                f"recipe {RECIPE_ID} three_pending_published must cover every IN-list arm with "
                f"3 distinct emails (statuses {sorted(statuses)}, emails {emails})"
            )
    elif branch == "distinct_dedupes_email":
        movement_counts: dict[str, int] = {}
        for row in joined:
            movement_counts[row["employee_id"]] = movement_counts.get(row["employee_id"], 0) + 1
        if not any(count >= 2 for count in movement_counts.values()) or len(joined) <= len(emails):
            raise RuntimeError(
                f"recipe {RECIPE_ID} distinct_dedupes_email must seed one employee with >=2 "
                f"pending movement rows so DISTINCT collapses them (rows {len(joined)}, "
                f"emails {len(emails)})"
            )
    elif branch == "zero_pending":
        if emails or not movements:
            raise RuntimeError(
                f"recipe {RECIPE_ID} zero_pending must seed only non-pending movement rows "
                f"(movements {len(movements)}, derived emails {emails})"
            )
    elif branch == "join_drops_orphan_movement":
        if not orphans or not emails:
            raise RuntimeError(
                f"recipe {RECIPE_ID} join_drops_orphan_movement must seed at least one pending "
                "movement without an EMPLOYEE match plus at least one joined pending row"
            )
    expected_tools = ["snowflake.search_rows_sql"] + ["workato_pub_sub.publish_to_topic"] * len(emails)
    if expect.get("tools") != expected_tools or expect.get("executed_action_count") != len(expected_tools):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools/executed_action_count incoherent with the derived "
            f"result; expected {expected_tools}"
        )
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or [item.get("tool") for item in items] != expected_tools:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must align 1:1 with expect.tools")
    if data.get("force_action_error") is not None:
        raise RuntimeError(f"recipe {RECIPE_ID} has no catch: forced action errors would fail the run")
    provision = seed_live_snowflake(RECIPE_ID, data, ctx)
    return snowflake_seed_base(
        recipe_id=RECIPE_ID,
        seed_type=SEED_TYPE,
        track=TRACK,
        validation=validation,
        ctx=ctx,
        snowflake_state=provision["state"],
        extra={"trigger": trigger},
    )


def run_87485576(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    return run_live_snowflake_recipe(
        recipe_id=RECIPE_ID,
        track=TRACK,
        raw=raw,
        seed=seed,
        ctx=ctx,
        validation=validate_87485576(raw),
        expected_raw_tools=EXPECTED_RAW_TOOLS,
        allowed_tools=ALLOWED_TOOLS,
        verifier=verify_87485576,
    )


def _require_snowflake_section(section: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}}")
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted(SEED_TABLES):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly Snowflake tables {sorted(SEED_TABLES)}"
        )
    out: dict[str, list[dict[str, Any]]] = {}
    for table, columns in ((MOVEMENT_TABLE, MOVEMENT_COLUMNS), (EMPLOYEE_TABLE, EMPLOYEE_COLUMNS)):
        spec = tables[table]
        if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} snowflake table {table} must declare exactly columns + rows"
            )
        if spec["columns"] != columns:
            raise RuntimeError(
                f"recipe {RECIPE_ID} snowflake table {table} columns must be exactly {columns}"
            )
        rows = spec["rows"]
        if not isinstance(rows, list):
            raise RuntimeError(f"recipe {RECIPE_ID} snowflake table {table} rows must be a list")
        for idx, row in enumerate(rows):
            if not isinstance(row, dict) or sorted(row.keys()) != sorted(columns):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} snowflake table {table} row {idx} must carry exactly "
                    f"columns {sorted(columns)}"
                )
            for column, value in row.items():
                if not isinstance(value, str) or not value.strip():
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} snowflake table {table} row {idx}.{column} must be "
                        "a non-empty string (published emails and join keys are load-bearing)"
                    )
        out[table] = rows
    employee_ids = [row["id"] for row in out[EMPLOYEE_TABLE]]
    if len(set(employee_ids)) != len(employee_ids):
        raise RuntimeError(f"recipe {RECIPE_ID} EMPLOYEE ids must be unique (join key)")
    return out[MOVEMENT_TABLE], out[EMPLOYEE_TABLE]


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


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found
