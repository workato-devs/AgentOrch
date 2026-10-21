from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_102158721


RECIPE_ID = "102158721"
SEED_TYPE = "api_workspace_grant_gate_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "f7d177ec"
GET_STEP_AS = "98b231b1"
ADD_STEP_AS = "824eb544"
R401_STEP_AS = "792322e2"
R200_STEP_AS = "cd1d44cf"
TABLE_ID = "11026"
# 'OpenAI Proxy Workspaces' table 11026 field ids (underscore-normalized,
# as the mock rows and the engine's filters both key them).
RECORD_ID_COL = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
WORKSPACE_COL = "faf6d561_0a7e_42d1_8f8c_ec11f9f86c31"
CLIENT_COL = "50dd1528_57bf_4ed5_a678_03e9c709b140"
PROFILE_COL = "856d93af_9a6e_4091_af46_051211c25a75"
NAME_COL = "8016f9ed_ec17_40fd_a45b_4511efa3daf9"
ENABLED_COL = "c3f5a247_f6d7_498f_a5fa_6b469edb74d9"
CREATED_COL = "a5612739_5401_4ae7_bd07_782c1a6fb2d1"
UPDATED_COL = "61aae604_a95e_4519_9091_bb0bf754a67f"
ROW_COLUMNS = (
    RECORD_ID_COL,
    WORKSPACE_COL,
    CLIENT_COL,
    PROFILE_COL,
    NAME_COL,
    ENABLED_COL,
    CREATED_COL,
    UPDATED_COL,
)

# TWIN NOTE: 102158704 is a byte-twin of this recipe (diff verified
# against both raw_recipe.md files): only CSV metadata and the table_id
# (10529 there vs 11026 here, on BOTH get_records and add_record) differ.
# Each module pins ITS OWN table id and verbatim raw tree so twin drift
# between the deployed recipes is caught, never papered over.

# workato_api_platform.receive_request (as f7d177ec, JSON request schema
# {workspace_user_id: string, REQUIRED}; responses 200/401). Dereferenced:
# context.client.id, context.access_profile.{id,name}, request.workspace_user_id.
#   2  workato_db_table.get_records 98b231b1 (mock table 11026): filters
#      api_client_id eq context.client.id.to_i, access_profile_id eq
#      context.access_profile.id.to_i, workspace_id eq
#      request.workspace_user_id.to_i, enabled ISTRUE (engine converts
#      op_boolean istrue -> eq true; the editor's limit '100' / order 'asc'
#      are metadata the engine never forwards into args).
#   IF 3 (workspace_user_id present AND records size equals_to 0):
#     4  workato_db_table.add_record 824eb544 table 11026: the three ids
#        .to_i + name = context.access_profile.name + enabled = LITERAL string
#        'true' (recipe constant — the mock stores it verbatim, faithful).
#   ELSIF 5 (records[current_item].enabled is_not_true — current_item OUTSIDE
#        any foreach = FIRST record; MISSING when records is empty -> ''
#        -> is_not_true TRUE):
#     6  workato_api_platform.return_response 401 — ENGINE-TERMINAL: the
#        unconditional tail 200 (step 7) never runs after it.
#   7  workato_api_platform.return_response 200 (unconditional tail, terminal).
#
# Branch mapping (the get_records filter pins enabled istrue, so a NONEMPTY
# result ALWAYS has an enabled first record and the elsif can only fire when
# records is EMPTY and the IF was false, i.e. workspace_user_id is blank —
# '' is schema-present but fails `present`, and ''.to_i = 0 makes the
# workspace filter match nothing):
# - grant_new_workspace: workspace_user_id present, no matching enabled row
#   (decoys prove all four filters) -> get + add + 200. 3 actions.
# - already_enabled_noop: matching row seeded with enabled JSON true -> IF
#   false (size 1), elsif false (first record enabled) -> get + tail 200 only.
#   2 actions.
# - blank_user_401: workspace_user_id '' -> get (0 rows) + 401, tail 200
#   NEVER executed (terminality pinned via the absent cd1d44cf row). 2 actions.
#
# SEED-AUTHORING HAZARD (probe-pinned): row enabled MUST be JSON true/false.
# The engine converts istrue to eq True and live_tools compares str()-forms
# ('True'), so a STRING 'true' cell is INVISIBLE to the filter and silently
# flips the noop branch into a duplicate grant. The seeder rejects non-bool
# enabled cells.
#
# All backends are Workato-internal (api_platform trigger/response, db table):
# mock per backend policy, per-variant isolated, no cleanup.

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "workato_api_platform", "name": "receive_request", "as": "f7d177ec", "skip": false, "input": {"request": {"content_type": "json", "schema": "[{\"name\":\"workspace_user_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Workspace user ID\"}]"}, "response": {"content_type": "json", "responses": [{"http_status_code": "200"}, {"http_status_code": "401", "name": "Unauthorized"}]}}, "block": [{"number": 2, "keyword": "action", "provider": "workato_db_table", "name": "get_records", "as": "98b231b1", "skip": false, "input": {"11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "50dd1528-57bf-4ed5-a678-03e9c709b140": "integer", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "8016f9ed-ec17-40fd-a45b-4511efa3daf9": "string", "856d93af-9a6e-4091-af46-051211c25a75": "integer", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "c3f5a247-f6d7-498f-a5fa-6b469edb74d9": "boolean", "faf6d561-0a7e-42d1-8f8c-ec11f9f86c31": "integer", "filters": [{"field_id": "50dd1528-57bf-4ed5-a678-03e9c709b140", "op_integer": "eq", "value_integer": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"f7d177ec\",\"path\":[\"context\",\"client\",\"id\"]}').to_i"}, {"field_id": "856d93af-9a6e-4091-af46-051211c25a75", "op_integer": "eq", "value_integer": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"f7d177ec\",\"path\":[\"context\",\"access_profile\",\"id\"]}').to_i"}, {"field_id": "faf6d561-0a7e-42d1-8f8c-ec11f9f86c31", "op_integer": "eq", "value_integer": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"f7d177ec\",\"path\":[\"request\",\"workspace_user_id\"]}').to_i"}, {"field_id": "c3f5a247-f6d7-498f-a5fa-6b469edb74d9", "op_boolean": "istrue"}], "limit": "100", "order_direction": "asc", "table_id": "11026"}, "block": []}, {"number": 3, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"f7d177ec\",\"path\":[\"request\", \"workspace_user_id\"]}')}", "operand": "present", "rhs": ""}, {"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"98b231b1\",\"path\":[\"records\", {\"path_element_type\": \"size\"}]}')}", "operand": "equals_to", "rhs": "0"}], "operand": "and", "type": "compound"}, "block": [{"number": 4, "keyword": "action", "provider": "workato_db_table", "name": "add_record", "as": "824eb544", "skip": false, "input": {"parameters": {"50dd1528_57bf_4ed5_a678_03e9c709b140": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"f7d177ec\",\"path\":[\"context\",\"client\",\"id\"]}').to_i", "8016f9ed_ec17_40fd_a45b_4511efa3daf9": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"f7d177ec\",\"path\":[\"context\", \"access_profile\", \"name\"]}')}", "856d93af_9a6e_4091_af46_051211c25a75": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"f7d177ec\",\"path\":[\"context\",\"access_profile\",\"id\"]}').to_i", "c3f5a247_f6d7_498f_a5fa_6b469edb74d9": "true", "faf6d561_0a7e_42d1_8f8c_ec11f9f86c31": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"f7d177ec\",\"path\":[\"request\",\"workspace_user_id\"]}').to_i"}, "table_id": "11026"}, "block": []}, {"number": 5, "keyword": "elsif", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"98b231b1\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"c3f5a247_f6d7_498f_a5fa_6b469edb74d9\"]}')}", "operand": "is_not_true", "rhs": ""}], "operand": "and", "type": "compound"}, "block": [{"number": 6, "keyword": "action", "provider": "workato_api_platform", "name": "return_response", "as": "792322e2", "skip": false, "input": {"http_status_code": "401"}, "block": []}]}]}, {"number": 7, "keyword": "action", "provider": "workato_api_platform", "name": "return_response", "as": "cd1d44cf", "skip": false, "input": {"http_status_code": "200"}, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (GET_STEP_AS, "workato_db_table", "get_records"),
    (ADD_STEP_AS, "workato_db_table", "add_record"),
    (R401_STEP_AS, "workato_api_platform", "return_response"),
    (R200_STEP_AS, "workato_api_platform", "return_response"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.add_record",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.add_record",
    "workato_api_platform.return_response",
]
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "branch",
    "terminal_response_step",
    "http_status",
    "return_value",
    "initial_table_rows",
    "final_table_rows",
)
BRANCHES = ("grant_new_workspace", "already_enabled_noop", "blank_user_401")


def validate_102158721(raw: dict[str, Any]) -> dict[str, Any]:
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
    # Twin-drift guard: BOTH db-table steps must target THIS recipe's table id
    # (the twin differs only here).
    for node in _walk_nodes(raw):
        if node.get("provider") == "workato_db_table":
            table = str((node.get("input") or {}).get("table_id") or "")
            if table != TABLE_ID:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} db-table step {node.get('as')!r} targets table "
                    f"{table!r}, expected {TABLE_ID!r} (twin drift?)"
                )
    # Semantic pins on the drift-prone bits (the tree pin holds the exact
    # bytes; these guards name the trap when one changes).
    get_node = next((n for n in _walk_nodes(raw) if str(n.get("as") or "") == GET_STEP_AS), None)
    filters = ((get_node or {}).get("input") or {}).get("filters") or []
    if (
        len(filters) != 4
        or str(filters[3].get("op_boolean") or "") != "istrue"
        or str(filters[3].get("field_id") or "").replace("-", "_") != ENABLED_COL
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} enabled istrue filter changed: {filters!r}")
    add_node = next((n for n in _walk_nodes(raw) if str(n.get("as") or "") == ADD_STEP_AS), None)
    add_params = ((add_node or {}).get("input") or {}).get("parameters") or {}
    if add_params.get(ENABLED_COL) != "true":
        raise RuntimeError(f"recipe {RECIPE_ID} add_record no longer writes literal enabled 'true'")
    if_nodes = [n for n in _walk_nodes(raw) if n.get("keyword") == "if"]
    elsif_nodes = [n for n in _walk_nodes(raw) if n.get("keyword") == "elsif"]
    if len(if_nodes) != 1 or len(elsif_nodes) != 1:
        raise RuntimeError(f"recipe {RECIPE_ID} IF/ELSIF structure changed")
    elsif_lhs = str((((elsif_nodes[0].get("input") or {}).get("conditions") or [{}])[0]).get("lhs") or "")
    if "current_item" not in elsif_lhs or ENABLED_COL not in elsif_lhs:
        raise RuntimeError(f"recipe {RECIPE_ID} elsif no longer reads first-record enabled: {elsif_lhs!r}")
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
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


def seed_102158721(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_102158721(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    client_id, profile_id, profile_name, workspace_user_id = _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["workato_db_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the workato_db_table section; "
            f"got {sorted(seed_in.keys())}"
        )
    rows = _require_db_table_section(seed_in["workato_db_table"])
    matched = _count_filter_matches(rows, client_id, profile_id, workspace_user_id)
    expect = data.get("expect")
    _require_expect(expect, rows, matched, client_id, profile_id, profile_name, workspace_user_id)
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: force_action_error would only abort "
            "the run and is not a recipe branch"
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


def run_102158721(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_102158721(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
    initial_snapshot = _snapshot(ctx)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = _snapshot(ctx)
    # Cleanup per the cleanup principle: every backend is a per-variant mock
    # the seed fully overwrites before each run — nothing persistent to clean.
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
    result["verifier"] = verify_102158721(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> tuple[str, str, str, str]:
    if sorted(trigger.keys()) != ["context", "request"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly context + request; "
            f"got {sorted(trigger.keys())}"
        )
    context = trigger["context"]
    if not isinstance(context, dict) or sorted(context.keys()) != ["access_profile", "client"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger context must carry exactly access_profile + "
            f"client (the only context objects the recipe dereferences)"
        )
    client = context["client"]
    if not isinstance(client, dict) or sorted(client.keys()) != ["id"]:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger context.client must be exactly {{'id': ...}}")
    profile = context["access_profile"]
    if not isinstance(profile, dict) or sorted(profile.keys()) != ["id", "name"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger context.access_profile must be exactly "
            f"{{'id': ..., 'name': ...}}"
        )
    request = trigger["request"]
    if not isinstance(request, dict) or sorted(request.keys()) != ["workspace_user_id"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger request must be exactly {{'workspace_user_id': ...}} "
            f"(the endpoint's whole request schema)"
        )
    for label, value in (("context.client.id", client["id"]), ("context.access_profile.id", profile["id"])):
        if not isinstance(value, str) or not value.isdigit() or str(int(value)) != value:
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger {label} must be a canonical digit string "
                f"(.to_i feeds the filters verbatim); got {value!r}"
            )
    name = profile["name"]
    if not isinstance(name, str) or not name.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} trigger access_profile.name must be a non-empty string")
    workspace_user_id = request["workspace_user_id"]
    if not isinstance(workspace_user_id, str) or (
        workspace_user_id != "" and (not workspace_user_id.isdigit() or str(int(workspace_user_id)) != workspace_user_id)
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} request.workspace_user_id must be a canonical digit "
            f"string or '' (the schema-present-but-blank 401 trigger); got {workspace_user_id!r}"
        )
    return client["id"], profile["id"], name, workspace_user_id


def _require_db_table_section(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table must be exactly {{'tables': ...}}"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table.tables must declare exactly table "
            f"{TABLE_ID!r} (twin guard: the twin recipe seeds a different id)"
        )
    rows = tables[TABLE_ID]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {TABLE_ID} rows must be a list")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table row {idx} must be an object")
        unknown = sorted(set(row.keys()) - set(ROW_COLUMNS))
        if unknown:
            raise RuntimeError(f"recipe {RECIPE_ID} table row {idx} has unknown columns: {unknown}")
        if ENABLED_COL in row and not isinstance(row[ENABLED_COL], bool):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} enabled must be JSON true/false — "
                f"a STRING 'true' is INVISIBLE to the istrue filter "
                f"(str-compare 'True' != 'true', probe-pinned hazard); got "
                f"{row[ENABLED_COL]!r}"
            )
        for column in (WORKSPACE_COL, CLIENT_COL, PROFILE_COL):
            if column in row and not isinstance(row[column], int):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table row {idx}.{column} must be a JSON integer "
                    f"(the live column type is integer); got {row[column]!r}"
                )
    return rows


def _count_filter_matches(
    rows: list[dict[str, Any]],
    client_id: str,
    profile_id: str,
    workspace_user_id: str,
) -> int:
    workspace = str(int(workspace_user_id)) if workspace_user_id else "0"
    return sum(
        1
        for row in rows
        if str(row.get(CLIENT_COL)) == client_id
        and str(row.get(PROFILE_COL)) == profile_id
        and str(row.get(WORKSPACE_COL)) == workspace
        and row.get(ENABLED_COL) is True
    )


def _expected_added_row(
    bookkept_rows: list[dict[str, Any]],
    client_id: str,
    profile_id: str,
    profile_name: str,
    workspace_user_id: str,
) -> dict[str, Any]:
    # bookkept_rows carry the mock's _row_id assignment (seed order); the add
    # allocates max+1 exactly like WorkatoDbTableMock._next_row_id.
    next_row_id = max((int(row.get("_row_id", -1)) for row in bookkept_rows), default=-1) + 1
    # add_record stores via _clean: every non-string value is str()-ified.
    return {
        "_row_id": next_row_id,
        "_created_by": "agent",
        CLIENT_COL: client_id,
        NAME_COL: profile_name,
        PROFILE_COL: profile_id,
        ENABLED_COL: "true",
        WORKSPACE_COL: str(int(workspace_user_id)),
    }


def _require_expect(
    expect: Any,
    rows: list[dict[str, Any]],
    matched: int,
    client_id: str,
    profile_id: str,
    profile_name: str,
    workspace_user_id: str,
) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    branch = expect.get("branch")
    if branch not in BRANCHES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch must be one of {BRANCHES}; got {branch!r}")
    # Branch/seed coherence: the IF needs a present workspace_user_id and zero
    # filter matches; the elsif is reachable ONLY via a blank workspace_user_id
    # (the istrue filter guarantees a nonempty result has an enabled first
    # record). Guarding here keeps a variant from pinning a branch its own
    # trigger/seed cannot reach.
    if branch == "grant_new_workspace" and (not workspace_user_id or matched != 0):
        raise RuntimeError(
            f"recipe {RECIPE_ID} grant_new_workspace needs a present workspace_user_id "
            f"and ZERO filter-matching rows; got workspace_user_id={workspace_user_id!r}, "
            f"matched={matched}"
        )
    if branch == "already_enabled_noop" and (not workspace_user_id or matched < 1):
        raise RuntimeError(
            f"recipe {RECIPE_ID} already_enabled_noop needs a present workspace_user_id "
            f"and >=1 filter-matching enabled row; got workspace_user_id="
            f"{workspace_user_id!r}, matched={matched}"
        )
    if branch == "blank_user_401":
        if workspace_user_id != "":
            raise RuntimeError(
                f"recipe {RECIPE_ID} blank_user_401 needs workspace_user_id == '' "
                f"(the ONLY reachable 401 path); got {workspace_user_id!r}"
            )
        if matched != 0:
            raise RuntimeError(
                f"recipe {RECIPE_ID} blank_user_401 seed matches the blank-user filters "
                f"(a workspace_id 0 row?) — the elsif needs an EMPTY result"
            )
    expected_initial = []
    for idx, row in enumerate(rows):
        rec = dict(row)
        rec.setdefault("_row_id", idx)
        rec.setdefault("_created_by", "seed")
        expected_initial.append(rec)
    if expect.get("initial_table_rows") != expected_initial:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.initial_table_rows must equal the seeded rows "
            f"plus mock bookkeeping ({json.dumps(expected_initial, sort_keys=True)[:400]}...)"
        )
    if branch == "grant_new_workspace":
        expected_final = expected_initial + [
            _expected_added_row(expected_initial, client_id, profile_id, profile_name, workspace_user_id)
        ]
        shape = (
            expect.get("executed_action_count") == 3,
            expect.get("tools")
            == [
                "workato_db_table.get_records",
                "workato_db_table.add_record",
                "workato_api_platform.return_response",
            ],
            expect.get("terminal_response_step") == R200_STEP_AS,
            expect.get("http_status") == "200",
        )
    else:
        expected_final = expected_initial
        shape = (
            expect.get("executed_action_count") == 2,
            expect.get("tools")
            == ["workato_db_table.get_records", "workato_api_platform.return_response"],
            expect.get("terminal_response_step")
            == (R401_STEP_AS if branch == "blank_user_401" else R200_STEP_AS),
            expect.get("http_status") == ("401" if branch == "blank_user_401" else "200"),
        )
    if expect.get("final_table_rows") != expected_final:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_table_rows is not the deterministic "
            f"post-run table for branch {branch!r}"
        )
    if not all(shape) or expect.get("return_value") != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with branch {branch!r}: {expect!r}"
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


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return dict(ctx.tools.call("harness.workato_db_table.snapshot", {}))


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
