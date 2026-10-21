from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_121898837


RECIPE_ID = "121898837"
SEED_TYPE = "pub_sub_ticket_event_notified_user_cleanup_variant"
TRACK = "workato_pub_sub_db_delete"
TRIGGER_PROVIDER = "workato_pub_sub"
TRIGGER_NAME = "subscribe_to_topic"
TRIGGER_AS = "3cf14e01"
GET_AS = "3528cee8"
DELETE_AS = "2e33611c"
TABLE_ID = "26786"
TOPIC_ID = "47223"
FILTER_EVENT_VALUE = "End Date Changed"
FILTER_EVENT_RHS = "<anon>End Date Changed</anon>"
EVENT_LITERAL = "NEAR_EXPIRE_EVENT"
GET_LIMIT = 100

# workato_pub_sub.subscribe_to_topic (as 3cf14e01, topic 47223 'DIFA | CRT |
# Ticket Event', since_offset -3600) with a ROOT-LEVEL TRIGGER FILTER:
# message.event equals_to '<anon>End Date Changed</anon>'. The rhs is an
# anonymizer-TAGGED recipe literal compared against the CLEAN seeded
# message.event — the engine's mixed-anonymization condition rule (raw_executor
# condition(), :356-366) strips the wrapped side, so the de-tagged literal
# 'End Date Changed' matches a clean seeded event (re-probed verbatim on HEAD
# 07af31c2; seeds NEVER carry <anon> tags).
#   2  workato_db_table.get_records 3528cee8 table 26786 'DIFA | DT-002 |
#      Notified User': filters ticketkey eq #{trigger message.ticket.key} AND
#      event eq 'NEAR_EXPIRE_EVENT' (literal); limit 100, order_direction asc
#      WITHOUT order_by_field_id. Every seed sets
#      workato_db_table.honor_order_and_limit so the node's order/limit args
#      flow like live Workato: order_direction alone triggers NO re-sort
#      (live_tools.py:413-425 sorts only on order_by_field_id) and the limit
#      applies — seeded (Workato-created) order is the contract, re-probed on
#      HEAD. Seeds stay under 100 rows so the limit never truncates the
#      derived match set.
#   IF 3: 3528cee8 records size greater_than 0 ->
#     4  workato_db_table.delete_record 2e33611c record_id = records
#        [current_item].11fbe9a6_… — current_item OUTSIDE any foreach is the
#        FIRST matching record (Workato first-item semantics, re-probed): with
#        N>=2 matches only the first seeded match is deleted.
# Branches: trigger filter false -> 0 actions; filter true + 0 matches ->
# get_records only (IF false); filter true + >=1 match -> get + delete-first.
# All backends are Workato-internal (pub_sub trigger payload seeded, db table
# mock): full mock replay per backend policy, per-variant isolated table
# state, no cleanup (each seed fully overwrites table 26786).

_RAW_PIN_JSON = r"""{"as": "3cf14e01", "block": [{"as": "3528cee8", "block": [], "input": {"11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "142d75a2-5bba-4aa6-a8ed-321003ffcd3b": "string", "394ffd38-e1e6-48ab-b4de-c4bcfe00ad1e": "relation", "499fd87d-e86e-46df-80a7-6b521e5ba052": "string", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "6ffaedd7-f150-4445-9cef-7b9ebe1cb8f2": "string", "9c8ca6d3-0142-4cb2-98dc-4386e62d7412": "string", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "c4a63369-4675-4b2a-808e-e0e0a334676a": "string", "fcc88f74-dd6f-4819-b868-1d36a3679a6a": "string", "filters": [{"field_id": "fcc88f74-dd6f-4819-b868-1d36a3679a6a", "op_default": "eq", "value_default": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"3cf14e01\",\"path\":[\"message\", \"ticket\", \"key\"]}')}"}, {"field_id": "9c8ca6d3-0142-4cb2-98dc-4386e62d7412", "op_default": "eq", "value_default": "NEAR_EXPIRE_EVENT"}], "limit": "100", "order_direction": "asc", "table_id": "26786"}, "keyword": "action", "name": "get_records", "number": 2, "provider": "workato_db_table", "skip": false}, {"as": "", "block": [{"as": "2e33611c", "block": [], "input": {"record_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"3528cee8\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\"]}')}", "table_id": "26786"}, "keyword": "action", "name": "delete_record", "number": 4, "provider": "workato_db_table", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"3528cee8\",\"path\":[\"records\", {\"path_element_type\": \"size\"}]}')}", "operand": "greater_than", "rhs": "0"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 3, "provider": "", "skip": false}], "filter": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"3cf14e01\",\"path\":[\"message\", \"event\"]}')}", "operand": "equals_to", "rhs": "<anon>End Date Changed</anon>"}], "operand": "and", "type": "compound"}, "input": {"since_offset": "-3600", "topic_id": "47223"}, "keyword": "trigger", "name": "subscribe_to_topic", "number": 1, "provider": "workato_pub_sub", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

# Table 26786 'DIFA | DT-002 | Notified User' columns (underscored output ids).
COL_RECORD_ID = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
COL_EVENT = "9c8ca6d3_0142_4cb2_98dc_4386e62d7412"
COL_USERNAME = "c4a63369_4675_4b2a_808e_e0e0a334676a"
COL_CHANNEL = "142d75a2_5bba_4aa6_a8ed_321003ffcd3b"
COL_MESSAGE_ID = "499fd87d_e86e_46df_80a7_6b521e5ba052"
COL_STATUS = "6ffaedd7_f150_4445_9cef_7b9ebe1cb8f2"
COL_TICKETKEY = "fcc88f74_dd6f_4819_b868_1d36a3679a6a"
COL_LINKED_INSTANCE = "394ffd38_e1e6_48ab_b4de_c4bcfe00ad1e"
COL_CREATED_AT = "a5612739_5401_4ae7_bd07_782c1a6fb2d1"
COL_UPDATED_AT = "61aae604_a95e_4519_9091_bb0bf754a67f"
TABLE_COLUMNS = (
    COL_RECORD_ID, COL_EVENT, COL_USERNAME, COL_CHANNEL, COL_MESSAGE_ID,
    COL_STATUS, COL_TICKETKEY, COL_LINKED_INSTANCE, COL_CREATED_AT,
    COL_UPDATED_AT,
)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (GET_AS, "workato_db_table", "get_records"),
    (DELETE_AS, "workato_db_table", "delete_record"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.delete_record",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.delete_record",
]
BRANCHES = (
    "match_deletes_first",
    "single_match_delete",
    "no_match_if_false",
    "trigger_filter_false",
)
REQUIRED_EXPECT_KEYS = (
    "branch",
    "trigger_filter_matched",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "matched_records",
    "deleted_record_id",
    "initial_table_rows",
    "final_table_rows",
)


def validate_121898837(raw: dict[str, Any]) -> dict[str, Any]:
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
    # Semantic pins on the load-bearing bits (redundant with the tree pin,
    # kept for sharp failure messages).
    trigger_filter = raw.get("filter") or {}
    conditions = trigger_filter.get("conditions") or []
    if (
        len(conditions) != 1
        or conditions[0].get("operand") != "equals_to"
        or conditions[0].get("rhs") != FILTER_EVENT_RHS
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger filter changed (anon-tagged rhs expected): {conditions}"
        )
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    get_input = actions[0].get("input") or {}
    if (
        str(get_input.get("table_id") or "") != TABLE_ID
        or str(get_input.get("limit") or "") != str(GET_LIMIT)
        or str(get_input.get("order_direction") or "") != "asc"
        or "order_by_field_id" in get_input
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} get_records config changed (limit 100 / order_direction "
            f"WITHOUT order_by_field_id expected): {get_input}"
        )
    filters = get_input.get("filters") or []
    if (
        len(filters) != 2
        or str(filters[0].get("field_id") or "") != COL_TICKETKEY.replace("_", "-")
        or str(filters[0].get("op_default") or "") != "eq"
        or "message\", \"ticket\", \"key" not in str(filters[0].get("value_default") or "")
        or str(filters[1].get("field_id") or "") != COL_EVENT.replace("_", "-")
        or str(filters[1].get("op_default") or "") != "eq"
        or filters[1].get("value_default") != EVENT_LITERAL
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} get_records filters changed: {filters}")
    delete_input = actions[1].get("input") or {}
    if str(delete_input.get("table_id") or "") != TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} delete_record table changed: {delete_input}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "topic_id": TOPIC_ID,
        "table_id": TABLE_ID,
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


def seed_121898837(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_121898837(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    event, ticket_key = _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["workato_db_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the workato_db_table section; "
            f"got {sorted(seed_in.keys()) if isinstance(seed_in, dict) else seed_in!r}"
        )
    rows = _require_db_table_section(seed_in["workato_db_table"])
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    branch = expect.get("branch")
    if branch not in BRANCHES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch must be one of {BRANCHES}; got {branch!r}")

    # Branch/seed coherence, derived exactly like the engine (re-probed on
    # HEAD 07af31c2): mixed-anon filter equality, ticketkey+event match in
    # seeded order, first-item delete.
    filter_matched = event == FILTER_EVENT_VALUE
    normalized_rows = [
        {"_row_id": idx, "_created_by": "seed", **row} for idx, row in enumerate(rows)
    ]
    matched = [
        row for row in normalized_rows
        if str(row.get(COL_TICKETKEY)) == ticket_key and str(row.get(COL_EVENT)) == EVENT_LITERAL
    ]
    derived_branch = (
        "trigger_filter_false" if not filter_matched
        else "no_match_if_false" if not matched
        else "single_match_delete" if len(matched) == 1
        else "match_deletes_first"
    )
    if branch != derived_branch:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.branch {branch!r} does not match the seeded state "
            f"(derived {derived_branch!r}: filter_matched={filter_matched}, matches={len(matched)})"
        )
    if bool(expect.get("trigger_filter_matched")) != filter_matched:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.trigger_filter_matched must be {filter_matched}")
    expected_deleted = matched[0][COL_RECORD_ID] if filter_matched and matched else None
    if expect.get("deleted_record_id") != expected_deleted:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.deleted_record_id must pin the FIRST matching record's "
            f"Record ID ({expected_deleted!r}); got {expect.get('deleted_record_id')!r}"
        )
    expected_matched = matched if filter_matched else []
    if expect.get("matched_records") != expected_matched:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.matched_records must be the ticketkey+NEAR_EXPIRE_EVENT "
            f"matches in seeded order (with _row_id/_created_by bookkeeping): {expected_matched}"
        )
    if expect.get("initial_table_rows") != normalized_rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.initial_table_rows must be the seeded rows with "
            f"bookkeeping, byte-exact: {normalized_rows}"
        )
    expected_final = [
        row for row in normalized_rows
        if expected_deleted is None or row[COL_RECORD_ID] != expected_deleted
    ]
    if expect.get("final_table_rows") != expected_final:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_table_rows must be the seeded rows minus the "
            f"deleted first match, byte-exact: {expected_final}"
        )
    expected_tools = (
        [] if not filter_matched
        else ["workato_db_table.get_records"] + (["workato_db_table.delete_record"] if matched else [])
    )
    if expect.get("tools") != expected_tools or expect.get("executed_action_count") != len(expected_tools):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools/executed_action_count incoherent with the branch; "
            f"expected {expected_tools}"
        )
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or [item.get("tool") for item in items] != expected_tools:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must align 1:1 with expect.tools"
        )
    if data.get("force_action_error") is not None:
        raise RuntimeError(f"recipe {RECIPE_ID} has no catch: forced action errors would fail the run")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_121898837(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_121898837(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    dt_section = seed.get("workato_db_table")
    if not isinstance(dt_section, dict) or dt_section.get("honor_order_and_limit") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must set workato_db_table.honor_order_and_limit "
            "(the get_records order/limit args are load-bearing on this recipe)"
        )
    initial_snapshot = ctx.tools.call("harness.workato_db_table.snapshot", {})
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = ctx.tools.call("harness.workato_db_table.snapshot", {})
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
    result["verifier"] = verify_121898837(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> tuple[str, str]:
    if sorted(trigger.keys()) != ["message"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'message': ...}}; "
            f"got {sorted(trigger.keys())}"
        )
    message = trigger["message"]
    if not isinstance(message, dict) or sorted(message.keys()) != ["event", "ticket"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger message must carry exactly event + ticket "
            "(the recipe dereferences message.event and message.ticket.key)"
        )
    event = message["event"]
    if not isinstance(event, str) or not event.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} message.event must be a non-empty string")
    if "<anon>" in event:
        raise RuntimeError(
            f"recipe {RECIPE_ID} message.event must be a CLEAN value — anonymizer tags never "
            "leak into seeds (the engine de-tags the recipe-literal rhs, not the seed)"
        )
    ticket = message["ticket"]
    if not isinstance(ticket, dict) or sorted(ticket.keys()) != ["key"]:
        raise RuntimeError(f"recipe {RECIPE_ID} message.ticket must be exactly {{'key': ...}}")
    key = ticket["key"]
    if not isinstance(key, str) or not key.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} message.ticket.key must be a non-empty string")
    return event, key


def _require_db_table_section(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["honor_order_and_limit", "tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table must be exactly "
            "{'honor_order_and_limit': true, 'tables': ...}"
        )
    if section["honor_order_and_limit"] is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must opt into honor_order_and_limit (this recipe's "
            "get_records carries live order/limit args — batch-06 opt-in covers it)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [TABLE_ID]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed must declare exactly table {TABLE_ID}")
    rows = tables[TABLE_ID]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {TABLE_ID} rows must be a list")
    if len(rows) > GET_LIMIT:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seeds must stay under the get_records limit ({GET_LIMIT}) so "
            "the derived match set is exact"
        )
    record_ids: set[str] = set()
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table {TABLE_ID} row {idx} must be an object")
        unknown = sorted(set(row.keys()) - set(TABLE_COLUMNS))
        if unknown:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {TABLE_ID} row {idx} has unknown columns: {unknown}"
            )
        for column, value in row.items():
            if not isinstance(value, str):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {TABLE_ID} row {idx}.{column} must be a string "
                    "(the mock compares filter values on canonical strings)"
                )
        if not str(row.get(COL_RECORD_ID) or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {TABLE_ID} row {idx} requires a non-empty Record ID "
                "(the delete pill reads it)"
            )
        record_ids.add(str(row[COL_RECORD_ID]))
    if len(record_ids) != len(rows):
        raise RuntimeError(f"recipe {RECIPE_ID} table {TABLE_ID} Record IDs must be unique")
    return rows


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


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
