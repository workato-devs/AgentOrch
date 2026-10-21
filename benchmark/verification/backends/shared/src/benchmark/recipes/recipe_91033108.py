from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_91033108


RECIPE_ID = "91033108"
SEED_TYPE = "slack_member_left_standup_schedule_cleanup_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "new_event"
TRIGGER_AS = "eb16353c"
CONFIG_SEARCH_AS = "f9501965"
SCHED_SEARCH_AS = "902801c9"
DELETE_AS = "c0945c6f"
CONFIG_TABLE = "3357221"
SCHED_TABLE = "3357223"

# slack_bot.new_event member_left_channel (as eb16353c, toggleCfg event_name
# custom value; seeded trigger event, no live Slack call — the recipe
# dereferences ONLY member_left_channel.channel + .user):
#   2  lookup_table.search_entries f9501965 table 3357221 '[NEW] Standup Bot
#      Config Table', parameters exactly {col2: #{member_left_channel.channel}}.
#   IF 3: f9501965 entries size equals_to '0' ->
#     STOP 4 (stop_with_error 'false', NO as-id). ENGINE SEMANTICS
#     (probe-verified 2026-07-08): the stop traces as the bare marker
#     {number: 4, keyword: 'stop', stopped: true} and is the LAST trace row.
#   5  lookup_table.search_entries 902801c9 table 3357223 '[Standup Bot]
#      Message Scheduling Table', parameters {col2: .user, col3: .channel} —
#      AND match over both columns.
#   6  lookup_table.delete_entry c0945c6f table 3357223, id =
#      #{902801c9.entries[current_item].id} — current_item OUTSIDE any foreach
#      = FIRST matching schedule row ONLY (probe-verified: with 2 matching
#      rows only the first is deleted, the second survives);
#      ignore_not_found stays the literal STRING 'false' (toggleCfg custom).
#
# UNGUARDED ERROR EDGE (probe-verified, do NOT build a variant for it):
# config row present but NO schedule row matching user+channel -> the id pill
# resolves empty -> raw_executor raises NonRecipeError
# "lookup_table.delete_entry requires a resolved entry id". In real Workato
# this branch is a catchless JOB ERROR (blank required id,
# ignore_not_found=false); the engine classifies it NonRecipeError
# (harness-attributed), which would mis-bucket the failure — the seeder
# refuses such seeds instead.
#
# Family: shares tables 3357221/3357223 with registered 91033107 (schedule
# sync, update_entry x2) and 91033101 (workato_service + bot posts) — a
# DIFFERENT program, built fresh. Mock tables are per-run isolated; variant
# values are kept disjoint from the siblings' (U08MLC*/C08STDP* ids) for
# clarity. Both backends are Workato-internal (lookup tables + seeded
# trigger): full mock per backend policy, per-variant isolated state files,
# no cleanup (every seed fully overwrites both tables).

_RAW_PIN_JSON = r"""{"as": "eb16353c", "block": [{"as": "f9501965", "block": [], "input": {"lookup_table_id": "3357221", "parameters": {"col2": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"eb16353c\",\"path\":[\"member_left_channel\", \"channel\"]}')}"}}, "keyword": "action", "name": "search_entries", "number": 2, "provider": "lookup_table", "skip": false}, {"as": "", "block": [{"as": "", "block": [], "input": {"stop_with_error": "false"}, "keyword": "stop", "name": "", "number": 4, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"f9501965\",\"path\":[\"entries\", {\"path_element_type\": \"size\"}]}')}", "operand": "equals_to", "rhs": "0"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 3, "provider": "", "skip": false}, {"as": "902801c9", "block": [], "input": {"lookup_table_id": "3357223", "parameters": {"col2": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"eb16353c\",\"path\":[\"member_left_channel\", \"user\"]}')}", "col3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"eb16353c\",\"path\":[\"member_left_channel\", \"channel\"]}')}"}}, "keyword": "action", "name": "search_entries", "number": 5, "provider": "lookup_table", "skip": false}, {"as": "c0945c6f", "block": [], "input": {"id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"902801c9\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}", "ignore_not_found": "false", "lookup_table_id": "3357223"}, "keyword": "action", "name": "delete_entry", "number": 6, "provider": "lookup_table", "skip": false}], "input": {"event_name": "member_left_channel"}, "keyword": "trigger", "name": "new_event", "number": 1, "provider": "slack_bot", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

CONFIG_COLUMNS = ("id", "col1", "col2", "col3", "col4", "col5", "col6")
SCHED_COLUMNS = ("id", "col1", "col2", "col3", "col4", "col5")

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (CONFIG_SEARCH_AS, "lookup_table", "search_entries"),
    (SCHED_SEARCH_AS, "lookup_table", "search_entries"),
    (DELETE_AS, "lookup_table", "delete_entry"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "lookup_table.delete_entry",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "lookup_table.delete_entry",
]
BRANCHES = ("config_missing_stop", "schedule_delete_first")
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "branch",
    "stopped",
    "deleted_entry_id",
    "initial_table_rows",
    "final_table_rows",
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

_CHANNEL_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\""
    + TRIGGER_AS + "\",\"path\":[\"member_left_channel\", \"channel\"]}')}"
)
_USER_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\""
    + TRIGGER_AS + "\",\"path\":[\"member_left_channel\", \"user\"]}')}"
)
_DELETE_ID_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\""
    + SCHED_SEARCH_AS
    + "\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}"
)


def validate_91033108(raw: dict[str, Any]) -> dict[str, Any]:
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
    # Semantic pins on the drift-prone load-bearing bits (the tree pin holds
    # the bytes; these name the trap when one changes).
    if (raw.get("input") or {}).get("event_name") != "member_left_channel":
        raise RuntimeError(f"recipe {RECIPE_ID} trigger event_name changed")
    config_search = next(node for node in _walk_nodes(raw) if str(node.get("as") or "") == CONFIG_SEARCH_AS)
    if (config_search.get("input") or {}).get("parameters") != {"col2": _CHANNEL_PILL}:
        raise RuntimeError(f"recipe {RECIPE_ID} config search parameters changed")
    if str((config_search.get("input") or {}).get("lookup_table_id")) != CONFIG_TABLE:
        raise RuntimeError(f"recipe {RECIPE_ID} config search table changed")
    sched_search = next(node for node in _walk_nodes(raw) if str(node.get("as") or "") == SCHED_SEARCH_AS)
    if (sched_search.get("input") or {}).get("parameters") != {"col2": _USER_PILL, "col3": _CHANNEL_PILL}:
        raise RuntimeError(f"recipe {RECIPE_ID} schedule search parameters changed (col2 user AND col3 channel)")
    if str((sched_search.get("input") or {}).get("lookup_table_id")) != SCHED_TABLE:
        raise RuntimeError(f"recipe {RECIPE_ID} schedule search table changed")
    delete = next(node for node in _walk_nodes(raw) if str(node.get("as") or "") == DELETE_AS)
    delete_input = delete.get("input") or {}
    if delete_input.get("id") != _DELETE_ID_PILL:
        raise RuntimeError(f"recipe {RECIPE_ID} delete id pill changed (first-match current_item expected)")
    if delete_input.get("ignore_not_found") != "false":
        raise RuntimeError(f"recipe {RECIPE_ID} delete ignore_not_found changed (literal string 'false' expected)")
    if str(delete_input.get("lookup_table_id")) != SCHED_TABLE:
        raise RuntimeError(f"recipe {RECIPE_ID} delete table changed")
    stop = next((node for node in _walk_nodes(raw) if node.get("keyword") == "stop"), None)
    if not isinstance(stop, dict) or (stop.get("input") or {}).get("stop_with_error") != "false":
        raise RuntimeError(f"recipe {RECIPE_ID} stop step changed (non-error stop expected)")
    if_node = next((node for node in _walk_nodes(raw) if node.get("keyword") == "if"), None)
    conditions = ((if_node or {}).get("input") or {}).get("conditions") or []
    if (
        len(conditions) != 1
        or conditions[0].get("operand") != "equals_to"
        or conditions[0].get("rhs") != "0"
        or CONFIG_SEARCH_AS not in str(conditions[0].get("lhs"))
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} IF-3 condition changed: {conditions}")
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "config_table": CONFIG_TABLE,
        "sched_table": SCHED_TABLE,
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


def seed_91033108(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_91033108(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    user, channel = _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["lookup_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the lookup_table section; "
            f"got {sorted(seed_in.keys())}"
        )
    tables = _require_lookup_section(seed_in["lookup_table"])
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    _require_expect_items(expect)
    branch = expect.get("branch")
    if branch not in BRANCHES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch must be one of {BRANCHES}; got {branch!r}")
    if bool(expect.get("stopped")) != (branch == "config_missing_stop"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.stopped must be true exactly on the config_missing_stop branch"
        )
    # Branch/seed coherence: IF-3 is decided by the seeded config rows; the
    # delete target by the FIRST user+channel schedule match.
    matching_config = [row for row in tables[CONFIG_TABLE] if str(row.get("col2")) == channel]
    matching_sched = [
        row for row in tables[SCHED_TABLE]
        if str(row.get("col2")) == user and str(row.get("col3")) == channel
    ]
    if branch == "config_missing_stop":
        if matching_config:
            raise RuntimeError(
                f"recipe {RECIPE_ID} config_missing_stop variant seeds a config row for "
                f"channel {channel!r}"
            )
        if expect.get("deleted_entry_id") is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} config_missing_stop variant must pin deleted_entry_id null"
            )
    else:
        if not matching_config:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {branch} variant seeds no config row for channel {channel!r}"
            )
        if not matching_sched:
            # SEEDER GUARD for the recipe's unguarded error edge: config
            # present + schedule empty is REACHABLE in production but is a
            # catchless job error (blank required delete id,
            # ignore_not_found='false'); the engine raises NonRecipeError
            # 'lookup_table.delete_entry requires a resolved entry id', which
            # would mis-bucket the failure as harness-attributed. Refuse the
            # seed instead of building a variant for it.
            raise RuntimeError(
                f"recipe {RECIPE_ID} refuses config-present/schedule-empty seeds: the "
                "delete id pill would resolve empty and the run dies as a catchless "
                "job error (engine NonRecipeError) — seed at least one schedule row "
                f"matching user {user!r} + channel {channel!r}"
            )
        if expect.get("deleted_entry_id") != matching_sched[0].get("id"):
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.deleted_entry_id must pin the FIRST matching "
                f"schedule row id {matching_sched[0].get('id')!r}; got "
                f"{expect.get('deleted_entry_id')!r}"
            )
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole run"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "lookup_table": deepcopy(seed_in["lookup_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_91033108(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_91033108(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
    initial_snapshot = ctx.tools.call("harness.lookup_table.snapshot", {})
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = ctx.tools.call("harness.lookup_table.snapshot", {})
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
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_91033108(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> tuple[str, str]:
    if sorted(trigger.keys()) != ["member_left_channel"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'member_left_channel': ...}}; "
            f"got {sorted(trigger.keys())}"
        )
    event = trigger["member_left_channel"]
    allowed = {"type", "user", "channel", "channel_type", "team", "event_ts"}
    if not isinstance(event, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} member_left_channel must be an object")
    unknown = sorted(set(event.keys()) - allowed)
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} member_left_channel has unknown keys: {unknown}")
    for key, value in event.items():
        if not isinstance(value, str):
            raise RuntimeError(f"recipe {RECIPE_ID} member_left_channel.{key} must be a string")
    user = str(event.get("user") or "")
    channel = str(event.get("channel") or "")
    if not user.strip() or not channel.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} member_left_channel requires non-empty user + channel "
            "(both feed lookup search parameters)"
        )
    return user, channel


def _require_lookup_section(section: Any) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.lookup_table must be exactly {{'tables': ...}}")
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted([CONFIG_TABLE, SCHED_TABLE]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly tables {CONFIG_TABLE!r} and "
            f"{SCHED_TABLE!r} (rows may be explicit empty lists)"
        )
    for table_id, columns, required in (
        (CONFIG_TABLE, CONFIG_COLUMNS, ("col2",)),
        (SCHED_TABLE, SCHED_COLUMNS, ("col2", "col3")),
    ):
        rows = tables[table_id]
        if not isinstance(rows, list):
            raise RuntimeError(f"recipe {RECIPE_ID} table {table_id} rows must be a list")
        ids: set[str] = set()
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                raise RuntimeError(f"recipe {RECIPE_ID} table {table_id} row {idx} must be an object")
            unknown = sorted(set(row.keys()) - set(columns))
            if unknown:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table_id} row {idx} has unknown columns: {unknown}"
                )
            if not isinstance(row.get("id"), int) or isinstance(row.get("id"), bool):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table_id} row {idx} requires an explicit "
                    "integer 'id' (the delete pill reads entries[].id)"
                )
            ids.add(str(row["id"]))
            for column, value in row.items():
                if column == "id":
                    continue
                if not isinstance(value, str):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} table {table_id} row {idx}.{column} must be a string "
                        "(the mock matches on exact string equality)"
                    )
            for column in required:
                if not str(row.get(column) or "").strip():
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} table {table_id} row {idx} requires non-empty {column}"
                    )
        if len(ids) != len(rows):
            raise RuntimeError(f"recipe {RECIPE_ID} table {table_id} ids must be unique")
    return tables


def _require_expect_items(expect: dict[str, Any]) -> None:
    items = expect.get("tool_expectations")
    if not isinstance(items, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must be a list")
    for idx, item in enumerate(items):
        if not isinstance(item, dict) or not item.get("tool"):
            raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[{idx}] must be an object with a tool")
        unknown = sorted(set(item.keys()) - _EXPECT_ITEM_KEYS)
        if unknown:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] has unsupported keys: {unknown}"
            )
        if not (set(item.keys()) & _EXPECT_VALUE_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] must pin at least one VALUE key "
                f"({sorted(_EXPECT_VALUE_KEYS)})"
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
