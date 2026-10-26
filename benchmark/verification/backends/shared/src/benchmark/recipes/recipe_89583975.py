from __future__ import annotations

import datetime
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_89583975


RECIPE_ID = "89583975"
SEED_TYPE = "cached_person_data_sweep_variant"
TRACK = "lookup_table_cache_sweep_service"
TRIGGER_PROVIDER = "workato_service"
TRIGGER_NAME = "receive_request"
SERVICE_NAME = "Clear Cached Person Data that are created more than 5 mins ago v2"
LOOKUP_TABLE_ID = "3298516"
LOG1_FORMULA = "=(now-1.hours).to_i"
SQL_CREATE = "CREATE TABLE Temp (\n    ID int\n);"
SQL_INSERT = "INSERT INTO Temp VALUES (1),(1),(1),(1),(1),(1),(1),(1),(1),(1)"
SQL_SELECT = "SELECT rowid FROM Temp"
COL5_FORMULA = (
    "=(\"1970-01-01T00:00:00Z\".to_time + "
    "(_('data.logger.log_message__1.message').to_i"
    "+_('data.foreach.foreach.index', 'foreach_meta')))"
    ".in_time_zone(\"America/Los_Angeles\").strftime(\"%Y-%m-%dT%H:%M:%S%z\")"
)
LOG2_FORMULA = "=_('data.workato_list.accumulate_list_items.list_items')"
IF14_LHS = "=_('data.foreach.foreach__2.created_date')<(now-5.minutes)"
IF16_LHS = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\","
    "\"line\":\"delete_entry\",\"path\":[\"id\"]}')}"
)
FOREACH3_SOURCE = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\","
    "\"line\":\"create_list\",\"path\":[\"list\"]}')}"
)
FOREACH_SOURCE = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\","
    "\"line\":\"query_list__2\",\"path\":[\"rows\"]}')}"
)
FOREACH1_SOURCE = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\","
    "\"line\":\"search_entries\",\"path\":[\"entries\"]}')}"
)
FOREACH2_SOURCE = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\","
    "\"line\":\"accumulate_list_items\",\"path\":[\"list_items\"]}')}"
)
ACC_CREATED_DATE_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\","
    "\"line\":\"foreach__1\",\"path\":[\"entry\", \"col5\"]}')}"
)
ACC_ENTRY_ID_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\","
    "\"line\":\"foreach__1\",\"path\":[\"id\"]}')}"
)
DELETE_ID_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\","
    "\"line\":\"foreach__2\",\"path\":[\"entry_id\"]}')}"
)
SCAN_SECONDS = 3600
INSERT_STEPS = 360
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("logger", "log_message"),
    ("workato_smart_list", "query_list"),
    ("workato_list", "create_list"),
    ("workato_smart_list", "query_list"),
    ("workato_smart_list", "query_list"),
    ("lookup_table", "search_entries"),
    ("workato_list", "accumulate_list_items"),
    ("logger", "log_message"),
    ("lookup_table", "delete_entry"),
    ("workato_service", "send_reply"),
    ("workato_service", "send_reply"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.log_message",
    "workato_smart_list.query_list",
    "workato_runtime.create_list",
    "lookup_table.search_entries",
    "workato_runtime.accumulate_list_items",
    "lookup_table.delete_entry",
    "workato_service.send_reply",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "lookup_table.delete_entry",
    "workato_service.send_reply",
]

REQUIRED_EXPECT_KEYS = (
    "tools",
    "tool_expectations",
    "executed_action_count",
    "window_start_epoch",
    "scan_seconds",
    "insert_count",
    "initial_lookup_entries",
    "final_lookup_entries",
    "accumulated_items",
    "log2_message",
    "deleted_entry_ids",
    "reply",
    "stop_step_number",
    "trace_tool_counts",
)


def _child(node: dict[str, Any], keyword: str, number: int) -> dict[str, Any]:
    for item in node.get("block") or []:
        if isinstance(item, dict) and item.get("keyword") == keyword and item.get("number") == number:
            return item
        if isinstance(item, dict):
            found = _find_nested(item, keyword, number)
            if found is not None:
                return found
    raise RuntimeError(f"recipe {RECIPE_ID} missing {keyword} node number {number}")


def _find_nested(node: dict[str, Any], keyword: str, number: int) -> dict[str, Any] | None:
    if node.get("keyword") == keyword and node.get("number") == number:
        return node
    for item in node.get("block") or []:
        if isinstance(item, dict):
            found = _find_nested(item, keyword, number)
            if found is not None:
                return found
    return None


def _pin(name: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise RuntimeError(f"recipe {RECIPE_ID} raw drift at {name}: {actual!r} != {expected!r}")


def validate_89583975(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    trig_in = raw.get("input") or {}
    _pin("trigger.service_name", trig_in.get("service_name"), SERVICE_NAME)
    _pin("trigger.rest_enabled", trig_in.get("rest_enabled"), "false")
    _pin(
        "trigger.request_schema_json",
        trig_in.get("request_schema_json"),
        '[{"name":"start","type":"boolean","optional":true}]',
    )
    _pin(
        "trigger.reply_schema_json",
        trig_in.get("reply_schema_json"),
        '[{"name":"any_person_cleared","type":"boolean","optional":false}]',
    )
    actions = _collect_actions(raw)
    actual = [(a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    by_as = {str(a.get("as")): a for a in actions}
    _pin("log_message__1.message", (by_as["log_message__1"].get("input") or {}).get("message"), LOG1_FORMULA)
    _pin("query_list.sql", (by_as["query_list"].get("input") or {}).get("sql"), SQL_CREATE)
    _pin("create_list.size", (by_as["create_list"].get("input") or {}).get("size"), "360")
    _pin("query_list__1.sql", (by_as["query_list__1"].get("input") or {}).get("sql"), SQL_INSERT)
    _pin("query_list__2.sql", (by_as["query_list__2"].get("input") or {}).get("sql"), SQL_SELECT)
    search_in = by_as["search_entries"].get("input") or {}
    _pin("search_entries.lookup_table_id", search_in.get("lookup_table_id"), LOOKUP_TABLE_ID)
    _pin("search_entries.parameters.col5", (search_in.get("parameters") or {}).get("col5"), COL5_FORMULA)
    acc_in = by_as["accumulate_list_items"].get("input") or {}
    _pin("accumulate.name", acc_in.get("name"), "Lookup value")
    acc_data = ((acc_in.get("list_item") or {}).get("data")) or {}
    _pin("accumulate.data.created_date", acc_data.get("created_date"), ACC_CREATED_DATE_PILL)
    _pin("accumulate.data.entry_id", acc_data.get("entry_id"), ACC_ENTRY_ID_PILL)
    _pin("log_message__2.message", (by_as["log_message__2"].get("input") or {}).get("message"), LOG2_FORMULA)
    del_in = by_as["delete_entry"].get("input") or {}
    _pin("delete_entry.lookup_table_id", del_in.get("lookup_table_id"), LOOKUP_TABLE_ID)
    _pin("delete_entry.id", del_in.get("id"), DELETE_ID_PILL)
    _pin("delete_entry.ignore_not_found", del_in.get("ignore_not_found"), "true")
    reply_in = by_as["send_reply"].get("input") or {}
    _pin("send_reply.reply_type", reply_in.get("reply_type"), "success")
    _pin("send_reply.reply", reply_in.get("reply"), {"any_person_cleared": "true"})
    reply1_in = by_as["send_reply__1"].get("input") or {}
    _pin("send_reply__1.reply_type", reply1_in.get("reply_type"), "success")
    _pin("send_reply__1.reply", reply1_in.get("reply"), {"any_person_cleared": "false"})
    foreach3 = _child(raw, "foreach", 5)
    _pin("foreach__3.source", foreach3.get("source"), FOREACH3_SOURCE)
    foreach = _child(raw, "foreach", 8)
    _pin("foreach.source", foreach.get("source"), FOREACH_SOURCE)
    foreach1 = _child(raw, "foreach", 10)
    _pin("foreach__1.source", foreach1.get("source"), FOREACH1_SOURCE)
    foreach2 = _child(raw, "foreach", 13)
    _pin("foreach__2.source", foreach2.get("source"), FOREACH2_SOURCE)
    if14 = _child(raw, "if", 14)
    if14_conditions = (if14.get("input") or {}).get("conditions") or []
    _pin("if14.conditions", if14_conditions, [{"lhs": IF14_LHS, "operand": "is_true"}])
    if16 = _child(raw, "if", 16)
    if16_conditions = (if16.get("input") or {}).get("conditions") or []
    _pin("if16.conditions", if16_conditions, [{"lhs": IF16_LHS, "operand": "present"}])
    stop18 = _child(raw, "stop", 18)
    _pin("stop18.stop_with_error", (stop18.get("input") or {}).get("stop_with_error"), "false")
    stop20 = _child(raw, "stop", 20)
    _pin("stop20.stop_with_error", (stop20.get("input") or {}).get("stop_with_error"), "false")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "service_name": SERVICE_NAME,
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


def _pinned_now_epoch(value: Any) -> int:
    if value in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} requires a fixed variant 'now' (recipe reads now)")
    parsed = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise RuntimeError(f"recipe {RECIPE_ID} variant 'now' must carry timezone information")
    return int(parsed.timestamp())


def seed_89583975(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_89583975(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    request = trigger.get("request")
    if not isinstance(request, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input must carry the request object")
    if "start" in request and not isinstance(request.get("start"), bool):
        raise RuntimeError(f"recipe {RECIPE_ID} request.start must be a boolean when present")
    now_epoch = _pinned_now_epoch(data.get("now"))
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    lookup = seed_in.get("lookup_table")
    if not isinstance(lookup, dict) or not isinstance((lookup.get("tables") or {}).get(LOOKUP_TABLE_ID), list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must provide lookup_table.tables['{LOOKUP_TABLE_ID}'] rows"
        )
    for row in lookup["tables"][LOOKUP_TABLE_ID]:
        if not isinstance(row, dict) or not isinstance(row.get("_row_id"), int):
            raise RuntimeError(f"recipe {RECIPE_ID} lookup rows must be objects with integer _row_id")
        for col in ("col1", "col2", "col3", "col4", "col5"):
            if not isinstance(row.get(col), str) or not row[col]:
                raise RuntimeError(f"recipe {RECIPE_ID} lookup row {row.get('_row_id')} missing {col}")
    expect = data.get("expect")
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    for key in REQUIRED_EXPECT_KEYS:
        if key not in expect:
            raise RuntimeError(f"recipe {RECIPE_ID} expect block missing required key: {key}")
    if expect.get("window_start_epoch") != now_epoch - 3600:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.window_start_epoch must equal pinned now epoch - 3600 "
            f"({expect.get('window_start_epoch')!r} != {now_epoch - 3600})"
        )
    if expect.get("scan_seconds") != SCAN_SECONDS or expect.get("insert_count") != INSERT_STEPS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} runs the faithful full-scale loop: expect.scan_seconds must be "
            f"{SCAN_SECONDS} and expect.insert_count must be {INSERT_STEPS}"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "now": data["now"],
        "lookup_table": deepcopy(lookup),
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_89583975(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_89583975(raw)
    initial_snapshot = _snapshot(ctx)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = _snapshot(ctx)
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "now": seed.get("now"),
            "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_89583975(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


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
    return ctx.tools.call("harness.lookup_table.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    # Compact summary (the full trace already lives in details.raw_execution;
    # this recipe's ~4000-step trace makes a per-tool trace copy prohibitive).
    deletes: list[Any] = []
    accumulated: list[Any] = []
    reply: Any = None
    for row in raw_execution.get("trace") or []:
        if not isinstance(row, dict):
            continue
        tool = row.get("tool")
        if tool == "lookup_table.delete_entry":
            deletes.append((row.get("args") or {}).get("id"))
        elif tool == "workato_runtime.accumulate_list_items":
            accumulated.append((row.get("args") or {}).get("list_item"))
        elif tool == "workato_service.send_reply":
            reply = row.get("args")
    return {
        "deleted_entry_ids": deletes,
        "accumulated_items": accumulated,
        "send_reply": reply,
        "return_value": raw_execution.get("return_value"),
    }
