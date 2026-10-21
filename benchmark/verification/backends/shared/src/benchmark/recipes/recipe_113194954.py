from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_113194954


RECIPE_ID = "113194954"
SEED_TYPE = "kt_roster_slack_mention_variant"
TRACK = "live_slack_kt_roster_mention"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "cfd6d1af"
GET_ENTRIES_AS = "24654513"
GET_ENTRY_AS = "ec6ffecf"
DECLARE_START_POS_AS = "3cbb97c3"
DECLARE_SLACK_LIST_AS = "132cb750"
SEARCH_ROSTER_AS = "469f790b"
SEARCH_GITHUB_AS = "843b95da"
POST_AS = "6f60f454"
ROSTER_TABLE = "3684742"
CLOSURES_TABLE = "3571620"
GITHUB_TABLE = "3571621"

# clock.scheduled_event (as cfd6d1af, biweekly Wed 09:00 Asia/Kolkata) —
# payload-less trigger, seed.trigger is the explicit {}:
#   2  lookup_table.get_entries 24654513 table 3684742 'knowledge sharing
#      session Roaster' (col1 Username / col2 slackname / col3 index).
#   3  lookup_table.get_entry ec6ffecf table 3571620 'KT CLOSURES'
#      parameters {col1: 'start_pos'} -> entry.col2 = the roster index.
#   4  workato_variable.declare_variable 3cbb97c3 start_pos =
#      #{ec6ffecf.entry.col2} (full-match pill, raw string).
#   5  workato_variable.declare_variable 132cb750 slack_list =
#      =entries.pluck("col1")[start_pos.to_i] — the POSITIONAL pluck works
#      because the mock flattens entry fields to the top level of each
#      get_entries item (lookup_table.py); the variable is DECLARED BUT DEAD
#      downstream (nothing reads it), pinned only via the declare trace.
#   6  lookup_table.search_entries 469f790b table 3684742 parameters
#      {col3: #{start_pos}} — a STRING VALUE match on the index column, NOT
#      positional (probe-verified with a shuffled roster).
#   7  lookup_table.search_entries 843b95da table 3571621 'Github Users'
#      parameters {col1: #{469f790b.entries[current_item].entry.col1}} —
#      current_item OUTSIDE any foreach = FIRST match.
#   8  slack.post_message_to_channel 6f60f454 channel
#      'knowledge-sharing-session' (non-'U' literal -> routed to
#      SLACK_CHANNEL_OVERRIDE), parse true; text renders the literal header
#      line + '<@#{843b95da…entry.col2}>' mention. The `buttons` input
#      (button_actions / flow_id 51780405) is DROPPED METADATA — the engine
#      renders text only and never waits; expects must not pin it as
#      rendered (the fragment asserts the args carry NO buttons key).
#
# Strictly linear, no ifs/foreach. Backends: lookup_table x3 +
# workato_variable are Workato-internal (mock / in-process per backend
# policy); slack runs LIVE. The run is read-only on the lookup tables and
# the post is a terminal observable that is never re-read -> no cleanup.
# Variants differ by the seeded start_pos ('0'/'1'/'2') to prove the
# col3-value match against three different roster/github pairs; seeds keep
# the pluck index in range (out-of-range would only nil the DEAD slack_list
# variable — probed, not a variant).

_RAW_PIN_JSON = r"""{"as": "cfd6d1af", "block": [{"as": "24654513", "block": [], "input": {"lookup_table_id": "3684742"}, "keyword": "action", "name": "get_entries", "number": 2, "provider": "lookup_table", "skip": false}, {"as": "ec6ffecf", "block": [], "input": {"lookup_table_id": "3571620", "parameters": {"col1": "start_pos"}}, "keyword": "action", "name": "get_entry", "number": 3, "provider": "lookup_table", "skip": false}, {"as": "3cbb97c3", "block": [], "input": {"variables": {"data": {"start_pos": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"ec6ffecf\",\"path\":[\"entry\", \"col2\"]}')}"}, "schema": "[{\"name\":\"start_pos\",\"type\":\"string\",\"optional\":true,\"label\":\"start_pos\",\"details\":{\"real_name\":\"start_pos\"},\"control_type\":\"text\"}]"}}, "keyword": "action", "name": "declare_variable", "number": 4, "provider": "workato_variable", "skip": false}, {"as": "132cb750", "block": [], "input": {"variables": {"data": {"slack_list": "=_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"24654513\",\"path\":[\"entries\"]}').pluck(\"col1\")[_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"3cbb97c3\",\"path\":[\"start_pos\"]}').to_i]"}, "schema": "[{\"name\":\"slack_list\",\"type\":\"string\",\"optional\":true,\"label\":\"slack_list\",\"details\":{\"real_name\":\"slack_list\"},\"control_type\":\"text\"}]"}}, "keyword": "action", "name": "declare_variable", "number": 5, "provider": "workato_variable", "skip": false}, {"as": "469f790b", "block": [], "input": {"lookup_table_id": "3684742", "parameters": {"col3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"3cbb97c3\",\"path\":[\"start_pos\"]}')}"}}, "keyword": "action", "name": "search_entries", "number": 6, "provider": "lookup_table", "skip": false}, {"as": "843b95da", "block": [], "input": {"lookup_table_id": "3571621", "parameters": {"col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"469f790b\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col1\"]}')}"}}, "keyword": "action", "name": "search_entries", "number": 7, "provider": "lookup_table", "skip": false}, {"as": "6f60f454", "block": [], "input": {"buttons": {"button_actions": "Take this session, bd, , , , ,\nSkip the session, sales, danger, Confirm, Are you sure you want to skip to next week?, Yes, Cancel", "flow_id": "51780405"}, "channel": "knowledge-sharing-session", "parse": "true", "text": "Hi, We have a KT session scheduled today\n<@#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"843b95da\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"entry\", \"col2\"]}')}> , could you please respond if you're ready today?"}, "keyword": "action", "name": "post_message_to_channel", "number": 8, "provider": "slack", "skip": false}], "input": {"days_of_week": "3", "time_unit": "weeks", "timezone": "Asia/Kolkata", "trigger_at": "09:00:00", "trigger_every": "2"}, "keyword": "trigger", "name": "scheduled_event", "number": 1, "provider": "clock", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (GET_ENTRIES_AS, "lookup_table", "get_entries"),
    (GET_ENTRY_AS, "lookup_table", "get_entry"),
    (DECLARE_START_POS_AS, "workato_variable", "declare_variable"),
    (DECLARE_SLACK_LIST_AS, "workato_variable", "declare_variable"),
    (SEARCH_ROSTER_AS, "lookup_table", "search_entries"),
    (SEARCH_GITHUB_AS, "lookup_table", "search_entries"),
    (POST_AS, "slack", "post_message_to_channel"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.get_entries",
    "lookup_table.get_entry",
    "workato_runtime.declare_variable",
    "lookup_table.search_entries",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.get_entries",
    "lookup_table.get_entry",
    "lookup_table.search_entries",
    "slack.post_message",
]
EXPECTED_TOOL_SEQUENCE = [
    "lookup_table.get_entries",
    "lookup_table.get_entry",
    "lookup_table.search_entries",
    "lookup_table.search_entries",
    "slack.post_message",
]
BRANCHES = ("index_0_first_member", "index_1_second_member", "index_2_third_member")
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "branch",
    "declared",
    "mention_user_id",
    "slack_text",
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


def validate_113194954(raw: dict[str, Any]) -> dict[str, Any]:
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
    for node in _walk_nodes(raw):
        as_id = str(node.get("as") or "")
        table = str((node.get("input") or {}).get("lookup_table_id") or "")
        if as_id in (GET_ENTRIES_AS, SEARCH_ROSTER_AS) and table != ROSTER_TABLE:
            raise RuntimeError(f"recipe {RECIPE_ID} step {as_id} targets table {table!r}")
        if as_id == GET_ENTRY_AS and table != CLOSURES_TABLE:
            raise RuntimeError(f"recipe {RECIPE_ID} step {as_id} targets table {table!r}")
        if as_id == SEARCH_GITHUB_AS and table != GITHUB_TABLE:
            raise RuntimeError(f"recipe {RECIPE_ID} step {as_id} targets table {table!r}")
        if as_id == GET_ENTRY_AS and (node.get("input") or {}).get("parameters") != {"col1": "start_pos"}:
            raise RuntimeError(f"recipe {RECIPE_ID} KT CLOSURES lookup key changed")
        if as_id == POST_AS:
            post_input = node.get("input") or {}
            if post_input.get("channel") != "knowledge-sharing-session":
                raise RuntimeError(f"recipe {RECIPE_ID} post channel literal changed")
            if "buttons" not in post_input:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} post no longer carries the (dropped) buttons metadata"
                )
            if not str(post_input.get("text") or "").startswith(
                "Hi, We have a KT session scheduled today\n<@"
            ):
                raise RuntimeError(f"recipe {RECIPE_ID} post text template changed")
    slack_list_node = next(
        node for node in _walk_nodes(raw) if str(node.get("as") or "") == DECLARE_SLACK_LIST_AS
    )
    formula = str(
        (((slack_list_node.get("input") or {}).get("variables") or {}).get("data") or {}).get("slack_list") or ""
    )
    if ".pluck(\"col1\")[" not in formula or ".to_i]" not in formula:
        raise RuntimeError(f"recipe {RECIPE_ID} slack_list pluck formula changed: {formula!r}")
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
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


def seed_113194954(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_113194954(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} — the scheduler tick is "
            f"payload-less and the recipe dereferences nothing from it; got {trigger}"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["lookup_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the lookup_table section"
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
    if expect.get("executed_action_count") != 7 or expect.get("tools") != EXPECTED_TOOL_SEQUENCE:
        raise RuntimeError(
            f"recipe {RECIPE_ID} is strictly linear: executed_action_count must be 7 and "
            f"expect.tools must be {EXPECTED_TOOL_SEQUENCE}"
        )
    _require_chain_coherence(expect, tables, branch)
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


def run_113194954(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_113194954(raw)
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    initial_snapshot = ctx.tools.call("harness.lookup_table.snapshot", {})
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = ctx.tools.call("harness.lookup_table.snapshot", {})
    # No cleanup: the run is read-only on the lookup tables and the Slack
    # post is a terminal observable that is never re-read.
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "expect": expect,
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "expected_channel": ctx.env.slack_channel_override,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_113194954(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_lookup_section(section: Any) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.lookup_table must be exactly {{'tables': ...}}")
    tables = section["tables"]
    expected_ids = sorted([ROSTER_TABLE, CLOSURES_TABLE, GITHUB_TABLE])
    if not isinstance(tables, dict) or sorted(tables.keys()) != expected_ids:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly lookup tables {expected_ids}"
        )
    _require_entry_rows(tables[ROSTER_TABLE], ROSTER_TABLE, ("col1", "col2", "col3"))
    _require_entry_rows(tables[CLOSURES_TABLE], CLOSURES_TABLE, ("col1", "col2"))
    _require_entry_rows(tables[GITHUB_TABLE], GITHUB_TABLE, ("col1", "col2"))
    if not tables[ROSTER_TABLE]:
        raise RuntimeError(f"recipe {RECIPE_ID} roster table must not be empty")
    for table_id, column in ((ROSTER_TABLE, "col3"), (ROSTER_TABLE, "col1"), (GITHUB_TABLE, "col1")):
        values = [row[column] for row in tables[table_id]]
        if len(values) != len(set(values)):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {table_id} column {column} values must be unique "
                "(first-match determinism)"
            )
    start_rows = [row for row in tables[CLOSURES_TABLE] if row["col1"] == "start_pos"]
    if len(start_rows) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} KT CLOSURES must carry exactly ONE col1='start_pos' row; "
            f"got {len(start_rows)}"
        )
    return tables


def _require_entry_rows(rows: Any, table_id: str, columns: tuple[str, ...]) -> None:
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} lookup table {table_id} rows must be a list")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(columns):
            raise RuntimeError(
                f"recipe {RECIPE_ID} lookup table {table_id} row {idx} must carry exactly "
                f"columns {sorted(columns)}; got {sorted(row.keys()) if isinstance(row, dict) else row!r}"
            )
        for column, value in row.items():
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} lookup table {table_id} row {idx}.{column} must be "
                    "a non-empty string"
                )


def _require_chain_coherence(
    expect: dict[str, Any],
    tables: dict[str, list[dict[str, Any]]],
    branch: str,
) -> None:
    start_pos = next(row for row in tables[CLOSURES_TABLE] if row["col1"] == "start_pos")["col2"]
    if not start_pos.isdigit() or not 0 <= int(start_pos) < len(tables[ROSTER_TABLE]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} start_pos {start_pos!r} must be an in-range roster index "
            "(out-of-range only nils the DEAD slack_list variable — probed, not a variant)"
        )
    if branch != f"index_{start_pos}_" + ("first", "second", "third")[int(start_pos)] + "_member":
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.branch {branch!r} does not match seeded start_pos {start_pos!r}"
        )
    roster_matches = [row for row in tables[ROSTER_TABLE] if row["col3"] == start_pos]
    if len(roster_matches) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} exactly one roster row must carry col3 == {start_pos!r}; "
            f"got {len(roster_matches)}"
        )
    username = roster_matches[0]["col1"]
    github_matches = [row for row in tables[GITHUB_TABLE] if row["col1"] == username]
    if len(github_matches) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} exactly one Github Users row must carry col1 == {username!r}; "
            f"got {len(github_matches)}"
        )
    mention = github_matches[0]["col2"]
    if expect.get("mention_user_id") != mention:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.mention_user_id {expect.get('mention_user_id')!r} does "
            f"not match the seeded chain ({mention!r})"
        )
    # The pluck is POSITIONAL over the get_entries order while the search is
    # a col3 VALUE match — both derive from the seed here.
    pluck_value = tables[ROSTER_TABLE][int(start_pos)]["col1"]
    declared = expect.get("declared")
    if declared != {"start_pos": start_pos, "slack_list": pluck_value}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.declared must pin "
            f"{{'start_pos': {start_pos!r}, 'slack_list': {pluck_value!r}}} (positional pluck "
            f"over the seeded roster order); got {declared}"
        )
    expected_text = (
        "Hi, We have a KT session scheduled today\n"
        f"<@{mention}> , could you please respond if you're ready today?"
    )
    if expect.get("slack_text") != expected_text:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.slack_text does not match the rendered template for "
            f"the seeded chain: {expect.get('slack_text')!r} != {expected_text!r}"
        )


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
        if item.get("tool") == "slack.post_message":
            if item.get("channel") != "override" or not item.get("text_fragments"):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} tool_expectations[{idx}] slack posts must pin "
                    "channel 'override' and non-empty text_fragments"
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
