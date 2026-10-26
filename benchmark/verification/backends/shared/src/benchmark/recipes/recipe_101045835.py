from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_101045835


RECIPE_ID = "101045835"
SEED_TYPE = "api_mobile_events_delivery_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "793a69c9"
CLIENTS_TABLE = "11694"
EVENTS_TABLE = "11683"
GET_CLIENTS_AS = "258f8175"
GET_EVENTS_AS = "5e2e6f78"
FOREACH_AS = "3579e054"
UPDATE_AS = "ad92eb08"
RESPONSE_AS = "675b8b5e"
STOP_AS = "292f8511"


_RAW_PIN_JSON = r"""{"as": "793a69c9", "block": [{"as": "258f8175", "block": [], "input": {"11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "b0dbc8e8-039b-4f9f-99cd-c4a6e7c778f9": "integer", "e83cee8a-521e-4820-8bbe-9f5cb36b1b3c": "string", "eb41603c-14dd-4897-8f62-f96a2ceaae47": "integer", "filters": [{"field_id": "eb41603c-14dd-4897-8f62-f96a2ceaae47", "op_integer": "eq", "value_integer": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"793a69c9\",\"path\":[\"context\", \"access_profile\", \"id\"]}')}"}], "limit": "100", "order_direction": "asc", "table_id": "11694"}, "keyword": "action", "name": "get_records", "number": 2, "provider": "workato_db_table", "skip": false}, {"as": "", "block": [{"as": "292f8511", "block": [], "input": {"stop_reason": "Unauthorized", "stop_with_error": "true"}, "keyword": "stop", "name": "", "number": 4, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"258f8175\",\"path\":[\"records\", {\"path_element_type\": \"size\"}]}')}", "operand": "equals_to", "rhs": "0"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 3, "provider": "", "skip": false}, {"as": "5e2e6f78", "block": [], "input": {"027dbe96-f079-4fb4-816a-7b7ed0514436": "relation", "0b0389e6-152d-444a-aa99-2e6736f56a2c": "string", "0e6d8c4b-818c-4da2-9f1b-94d9b6f4b7e4": "string", "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "76b133de-c64a-4092-bbbe-680b253167af": "string", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "cc26c65b-3c30-44e6-b34b-03009a970b5c": "boolean", "fbbef48d-ac46-4429-9a9b-ba8977afdbb0": "string", "fc382250-48e5-49db-aac7-4a306ca88106": "string", "filters": [{"field_id": "027dbe96-f079-4fb4-816a-7b7ed0514436", "op_relation": "eq", "value_relation": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"258f8175\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\"]}')}"}, {"field_id": "cc26c65b-3c30-44e6-b34b-03009a970b5c", "op_boolean": "isfalse"}], "limit": "200", "order_direction": "asc", "table_id": "11683"}, "keyword": "action", "name": "get_records", "number": 5, "provider": "workato_db_table", "skip": false}, {"as": "3579e054", "block": [{"as": "ad92eb08", "block": [], "input": {"parameters": {"cc26c65b_3c30_44e6_b34b_03009a970b5c": "true"}, "record_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"3579e054\",\"path\":[\"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\"]}')}", "table_id": "11683"}, "keyword": "action", "name": "update_record", "number": 7, "provider": "workato_db_table", "skip": false}], "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"5e2e6f78\",\"path\":[\"records\"]}')}"}, "keyword": "foreach", "name": "", "number": 6, "provider": "", "repeat_mode": "simple", "skip": false, "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"5e2e6f78\",\"path\":[\"records\"]}')}"}, {"as": "675b8b5e", "block": [], "input": {"http_status_code": "200", "response": {"events": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"5e2e6f78\",\"path\":[\"records\"]}')}", "created": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"5e2e6f78\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"a5612739_5401_4ae7_bd07_782c1a6fb2d1\"]}')}", "message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"5e2e6f78\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"0b0389e6_152d_444a_aa99_2e6736f56a2c\"]}')}", "process_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"5e2e6f78\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"fc382250_48e5_49db_aac7_4a306ca88106\"]}')}", "retrieval": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"5e2e6f78\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"22f03614_5ce2_475a_a653_8d8804064580\"]}')}", "skill": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"5e2e6f78\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"fbbef48d_ac46_4429_9a9b_ba8977afdbb0\"]}')}", "status": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"5e2e6f78\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"e7efb7b7_5bef_4d4b_9b58_f4d3a05f9160\"]}')}", "step_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"5e2e6f78\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"0e6d8c4b_818c_4da2_9f1b_94d9b6f4b7e4\"]}')}", "type": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"5e2e6f78\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"76b133de_c64a_4092_bbbe_680b253167af\"]}')}"}}}, "keyword": "action", "name": "return_response", "number": 8, "provider": "workato_api_platform", "skip": false}], "input": {"request": {"content_type": "json"}, "response": {"content_type": "json", "responses": [{"body_schema": "[{\"name\":\"events\",\"type\":\"array\",\"optional\":true,\"properties\":[{\"name\":\"retrieval\",\"type\":\"boolean\",\"optional\":false,\"control_type\":\"checkbox\",\"label\":\"Retrieval\",\"render_input\":{},\"parse_output\":{},\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Retrieval\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"retrieval\",\"type\":\"boolean\",\"optional\":false}},{\"name\":\"status\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Status\"},{\"name\":\"created\",\"type\":\"date_time\",\"optional\":false,\"control_type\":\"date_time\",\"label\":\"Created\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\"},{\"name\":\"type\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Type\"},{\"name\":\"step_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Step ID\"},{\"name\":\"process_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Process ID\"},{\"name\":\"message\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Message\"},{\"name\":\"skill\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Skill\"}],\"of\":\"object\",\"label\":\"Events\"}]", "http_status_code": "200", "name": "OK"}]}}, "keyword": "trigger", "name": "receive_request", "number": 1, "provider": "workato_api_platform", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

CL_RECORD_ID = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
CL_ACCESS_PROFILE = "eb41603c_14dd_4897_8f62_f96a2ceaae47"
CL_USER_ID = "b0dbc8e8_039b_4f9f_99cd_c4a6e7c778f9"
CL_EMAIL = "e83cee8a_521e_4820_8bbe_9f5cb36b1b3c"
CL_CREATED_AT = "a5612739_5401_4ae7_bd07_782c1a6fb2d1"
CL_UPDATED_AT = "61aae604_a95e_4519_9091_bb0bf754a67f"
CLIENT_COLUMNS = (
    CL_RECORD_ID, CL_ACCESS_PROFILE, CL_USER_ID, CL_EMAIL, CL_CREATED_AT, CL_UPDATED_AT,
)

EV_RECORD_ID = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
EV_CLIENT = "027dbe96_f079_4fb4_816a_7b7ed0514436"
EV_PROCESS_ID = "fc382250_48e5_49db_aac7_4a306ca88106"
EV_TYPE = "76b133de_c64a_4092_bbbe_680b253167af"
EV_STEP_ID = "0e6d8c4b_818c_4da2_9f1b_94d9b6f4b7e4"
EV_DELIVERED = "cc26c65b_3c30_44e6_b34b_03009a970b5c"
EV_MESSAGE = "0b0389e6_152d_444a_aa99_2e6736f56a2c"
EV_SKILL = "fbbef48d_ac46_4429_9a9b_ba8977afdbb0"
EV_STATUS = "e7efb7b7_5bef_4d4b_9b58_f4d3a05f9160"
EV_RETRIEVAL = "22f03614_5ce2_475a_a653_8d8804064580"
EV_CREATED_AT = "a5612739_5401_4ae7_bd07_782c1a6fb2d1"
EV_UPDATED_AT = "61aae604_a95e_4519_9091_bb0bf754a67f"
EVENT_COLUMNS = (
    EV_RECORD_ID, EV_CLIENT, EV_PROCESS_ID, EV_TYPE, EV_STEP_ID, EV_DELIVERED,
    EV_MESSAGE, EV_SKILL, EV_STATUS, EV_RETRIEVAL, EV_CREATED_AT, EV_UPDATED_AT,
)
EVENT_BOOL_COLUMNS = (EV_DELIVERED, EV_RETRIEVAL)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (GET_CLIENTS_AS, "workato_db_table", "get_records"),
    (GET_EVENTS_AS, "workato_db_table", "get_records"),
    (UPDATE_AS, "workato_db_table", "update_record"),
    (RESPONSE_AS, "workato_api_platform", "return_response"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.update_record",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.update_record",
    "workato_api_platform.return_response",
]
BRANCHES = ("unauthorized_stop", "no_pending_events", "deliver_events")
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "branch",
    "stopped",
    "return_value",
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


def validate_101045835(raw: dict[str, Any]) -> dict[str, Any]:
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
    for node in _walk_nodes(raw):
        if node.get("provider") != "workato_db_table":
            continue
        table = str((node.get("input") or {}).get("table_id") or "")
        expected_table = CLIENTS_TABLE if str(node.get("as") or "") == GET_CLIENTS_AS else EVENTS_TABLE
        if table != expected_table:
            raise RuntimeError(
                f"recipe {RECIPE_ID} db step {node.get('as')!r} targets table {table!r}, "
                f"expected {expected_table!r}"
            )
    events_get = next(node for node in _walk_nodes(raw) if str(node.get("as") or "") == GET_EVENTS_AS)
    filters = (events_get.get("input") or {}).get("filters") or []
    if len(filters) != 2 or filters[0].get("op_relation") != "eq" or filters[1].get("op_boolean") != "isfalse":
        raise RuntimeError(f"recipe {RECIPE_ID} events filters changed: {filters}")
    stop = next((node for node in _walk_nodes(raw) if node.get("keyword") == "stop"), None)
    if not isinstance(stop, dict) or str((stop.get("input") or {}).get("stop_with_error")) != "true":
        raise RuntimeError(f"recipe {RECIPE_ID} stop step changed")
    if str((stop.get("input") or {}).get("stop_reason")) != "Unauthorized":
        raise RuntimeError(f"recipe {RECIPE_ID} stop reason changed")
    update = next(node for node in _walk_nodes(raw) if str(node.get("as") or "") == UPDATE_AS)
    if (update.get("input") or {}).get("parameters") != {EV_DELIVERED: "true"}:
        raise RuntimeError(f"recipe {RECIPE_ID} update parameters changed (literal string 'true' expected)")
    response = next(node for node in _walk_nodes(raw) if str(node.get("as") or "") == RESPONSE_AS)
    events_mapping = ((response.get("input") or {}).get("response") or {}).get("events") or {}
    mapped = sorted(key for key in events_mapping if key != "____source")
    if mapped != ["created", "message", "process_id", "retrieval", "skill", "status", "step_id", "type"]:
        raise RuntimeError(f"recipe {RECIPE_ID} response events mapping changed: {mapped}")
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "clients_table": CLIENTS_TABLE,
        "events_table": EVENTS_TABLE,
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


def seed_101045835(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_101045835(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    access_profile_id = _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["workato_db_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the workato_db_table section; "
            f"got {sorted(seed_in.keys())}"
        )
    tables = _require_db_table_section(seed_in["workato_db_table"])
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
    if bool(expect.get("stopped")) != (branch == "unauthorized_stop"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.stopped must be true exactly on the unauthorized_stop branch"
        )
    # Branch/seed coherence (the IF-3 outcome is decided by the seeded Clients
    # rows; the foreach count by the seeded undelivered events).
    matching_clients = [
        row for row in tables[CLIENTS_TABLE]
        if str(row.get(CL_ACCESS_PROFILE)) == access_profile_id
    ]
    if branch == "unauthorized_stop":
        if matching_clients:
            raise RuntimeError(
                f"recipe {RECIPE_ID} unauthorized_stop variant seeds a matching Clients row"
            )
    else:
        if len(matching_clients) != 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {branch} variants must seed exactly ONE matching Clients "
                f"row (the step-5 filter reads the FIRST match; got {len(matching_clients)})"
            )
        client_record_id = str(matching_clients[0].get(CL_RECORD_ID))
        pending = [
            row for row in tables[EVENTS_TABLE]
            if str((row.get(EV_CLIENT) or {}).get("record_id")) == client_record_id
            and row.get(EV_DELIVERED) is False
        ]
        if branch == "no_pending_events" and pending:
            raise RuntimeError(
                f"recipe {RECIPE_ID} no_pending_events variant seeds undelivered events "
                f"for the matching client: {[row.get(EV_RECORD_ID) for row in pending]}"
            )
        if branch == "deliver_events" and not pending:
            raise RuntimeError(
                f"recipe {RECIPE_ID} deliver_events variant seeds no undelivered event "
                "for the matching client"
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
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_101045835(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_101045835(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
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
    result["verifier"] = verify_101045835(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> str:
    if sorted(trigger.keys()) != ["context"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'context': ...}} — the "
            f"recipe dereferences only context.access_profile.id; got {sorted(trigger.keys())}"
        )
    context = trigger["context"]
    if not isinstance(context, dict) or sorted(context.keys()) != ["access_profile"]:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger context must be exactly {{'access_profile': ...}}")
    access_profile = context["access_profile"]
    if not isinstance(access_profile, dict) or sorted(access_profile.keys()) != ["id"]:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger access_profile must be exactly {{'id': ...}}")
    profile_id = access_profile["id"]
    if (
        not isinstance(profile_id, int)
        or isinstance(profile_id, bool)
        or profile_id < 0
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} access_profile.id must be a non-negative integer "
            "matching the public trigger schema"
        )
    # Seed-coherence checks compare against the table fixture's canonical text
    # storage. The raw execution still receives the public integer unchanged.
    return str(profile_id)


def _require_db_table_section(section: Any) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table must be exactly {{'tables': ...}}"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted([CLIENTS_TABLE, EVENTS_TABLE]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly tables {CLIENTS_TABLE!r} and "
            f"{EVENTS_TABLE!r} (rows may be explicit empty lists)"
        )
    client_record_ids: set[str] = set()
    for idx, row in enumerate(_require_rows(tables[CLIENTS_TABLE], CLIENTS_TABLE)):
        unknown = sorted(set(row.keys()) - set(CLIENT_COLUMNS))
        if unknown:
            raise RuntimeError(f"recipe {RECIPE_ID} Clients row {idx} has unknown columns: {unknown}")
        for column, value in row.items():
            if not isinstance(value, str):
                raise RuntimeError(f"recipe {RECIPE_ID} Clients row {idx}.{column} must be a string")
        for column in (CL_RECORD_ID, CL_ACCESS_PROFILE):
            if not str(row.get(column) or "").strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} Clients row {idx} requires non-empty {column} "
                    "(RecordID feeds the relation filter; access_profile_id feeds the eq filter)"
                )
        client_record_ids.add(str(row[CL_RECORD_ID]))
    if len(client_record_ids) != len(tables[CLIENTS_TABLE]):
        raise RuntimeError(f"recipe {RECIPE_ID} Clients RecordIDs must be unique")
    event_record_ids: set[str] = set()
    for idx, row in enumerate(_require_rows(tables[EVENTS_TABLE], EVENTS_TABLE)):
        unknown = sorted(set(row.keys()) - set(EVENT_COLUMNS))
        if unknown:
            raise RuntimeError(f"recipe {RECIPE_ID} Events row {idx} has unknown columns: {unknown}")
        if not str(row.get(EV_RECORD_ID) or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} Events row {idx} requires a non-empty RecordID")
        event_record_ids.add(str(row[EV_RECORD_ID]))
        client = row.get(EV_CLIENT)
        if (
            not isinstance(client, dict)
            or sorted(client.keys()) != ["display_name", "record_id"]
            or not isinstance(client.get("record_id"), str)
            or not client["record_id"].strip()
            or not isinstance(client.get("display_name"), str)
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} Events row {idx} client must be the relation OBJECT "
                "{'record_id': <non-empty str>, 'display_name': <str>} — the op_relation "
                "eq filter matches it via record_id"
            )
        for column in EVENT_BOOL_COLUMNS:
            if not isinstance(row.get(column), bool):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} Events row {idx}.{column} must be a JSON BOOLEAN "
                    "(string 'false' does NOT match op_boolean isfalse — probe-verified hazard)"
                )
        for column, value in row.items():
            if column in (EV_CLIENT,) + EVENT_BOOL_COLUMNS:
                continue
            if not isinstance(value, str):
                raise RuntimeError(f"recipe {RECIPE_ID} Events row {idx}.{column} must be a string")
        # Relation hazard guard: the eq filter ALSO matches via the
        # display_name arm; a display_name colliding with a client RecordID
        # would admit unintended rows (probe-verified).
        if str(client.get("display_name")) in client_record_ids:
            raise RuntimeError(
                f"recipe {RECIPE_ID} Events row {idx} client.display_name collides with a "
                "Clients RecordID — the relation filter matches EITHER arm"
            )
    if len(event_record_ids) != len(tables[EVENTS_TABLE]):
        raise RuntimeError(f"recipe {RECIPE_ID} Events RecordIDs must be unique (update targeting)")
    return tables


def _require_rows(rows: Any, table_id: str) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {table_id} rows must be a list")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table {table_id} row {idx} must be an object")
    return rows


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
