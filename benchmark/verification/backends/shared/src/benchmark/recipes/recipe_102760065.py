from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_102760065


RECIPE_ID = "102760065"
SEED_TYPE = "slack_dynamic_menu_search_by_user_twin_variant"
TRACK = "live_snowflake_slack_dynamic_menu_user_search"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "dynamic_menu"
TRIGGER_AS = "28312336"
DYNAMIC_MENU_NAME = "[CB] Search by User"
DECLARE_STEP_AS = "97ffa775"
GET_RECORDS_STEP_AS = "3c62d745"
UPDATE_STEP_AS = "7f8ed08b"
SQL_STEP_AS = "18dd84d9"
MENU_STEP_AS = "9c70908d"
TABLE_ID = "13516"
PRIVATE_SUFFIX = "AND u.isprivate = FALSE"
F_RECID = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
F_EMAIL = "79c522be_02a9_4d35_b94b_8dfa4960a2c2"
F_TEAM = "15ca98b2_7c7b_4c04_b713_f5d783b6b318"
F_VIEW = "e0388988_bb54_4e13_942a_71a7a50db3b7"
F_CREATED = "a5612739_5401_4ae7_bd07_782c1a6fb2d1"
F_UPDATED = "61aae604_a95e_4519_9091_bb0bf754a67f"
EXCEPTION_ROW_KEYS = (F_RECID, F_EMAIL, F_TEAM, F_VIEW, F_CREATED, F_UPDATED)
# The exact SQL text the trace must carry after pill interpolation
# (workspace_ids inline + privatequery suffix); :parameter stays a bind.
SQL_TEMPLATE = (
    "SELECT distinct(r.relationid), u.username, a.name \n"
    "FROM DEMOINFRA_RELATION r \n"
    "INNER JOIN DEMOINFRA_USERS_WORKSPACES w ON w.relationid = r.relationid \n"
    "LEFT JOIN DEMOINFRA_USERS u ON u.id = r.userid \n"
    "LEFT JOIN DEMOINFRA_INSTANCES i ON r.instanceid = i.id \n"
    "LEFT JOIN DEMOINFRA_APPLICATIONS a ON i.applicationid = a.id\n"
    "WHERE (lower(u.username) like :parameter \n"
    "OR lower(a.name) like :parameter) \n"
    "AND w.workspaceid in ({ws})\n"
    "{suffix}"
)
# Bare 1-part names in the SQL (5 tables; the twin head also joins
# DEMOINFRA_WORKSPACES): snowflake_live maps each registered key onto
# <SNOWFLAKE_DATABASE>.BENCH.<NAME> (identifier redirect probe-verified).
TABLE_SPECS: dict[str, dict[str, str]] = {
    "DEMOINFRA_RELATION": {"RELATIONID": "integer", "USERID": "integer", "INSTANCEID": "integer"},
    "DEMOINFRA_USERS_WORKSPACES": {"RELATIONID": "integer", "WORKSPACEID": "integer"},
    "DEMOINFRA_USERS": {"ID": "integer", "USERNAME": "string", "ISPRIVATE": "boolean"},
    "DEMOINFRA_INSTANCES": {"ID": "integer", "APPLICATIONID": "integer"},
    "DEMOINFRA_APPLICATIONS": {"ID": "integer", "NAME": "string"},
}

# NEAR-TWIN of 103711977 (family head; built there, derived mechanically
# here, then independently probe-verified). Byte-diff deltas from the head,
# proven by normalized-tree diff on 2026-07-08:
# - workato_db_table table_id 12788 -> 13516 (same '[CB] | DT-001 | User
#   Exception' schema and hashed field ids);
# - the SQL drops 'w.name as workspace_name' and the INNER JOIN
#   DEMOINFRA_WORKSPACES, and aliases DEMOINFRA_USERS_WORKSPACES as w (the
#   head uses wu) - so 5 seeded tables instead of 6;
# - output_schema carries 'name' instead of application_name/workspace_name;
# - the menu label drops the third ' || workspace_name' segment (2-segment
#   'user || app');
# - the trigger parameters JSON is a whitespace-only reformat.
#
# Flow (identical shape to the head):
#   2 declare_variable 97ffa775 privatequery (schema-only -> nil)
#   3 workato_db_table.get_records 3c62d745 (mock table 13516) filter email
#     eq =parameters.uemail.downcase
#   IF 4 records[current_item].RecordID blank:
#     5 update_variables 7f8ed08b privatequery = 'AND u.isprivate = FALSE'
#   6 snowflake.run_custom_sql 18dd84d9 (LIVE, 5 bare DEMOINFRA_* tables,
#     :parameter bind, workspace_ids + privatequery pills inline)
#   7 generate_menu_options 9c70908d label = username.gsub(".onmicrosoft.com",
#     "") + ' || ' + name; value = int relationid pill
#
# Branch mapping and live semantics as on the head: suffix appended (5
# actions, private hidden) vs nil-pill '' (4 actions, private visible);
# multiset menu compare when multi-row (no ORDER BY); downcased uemail eq
# filter; boolean isprivate. The twin's v1 additionally seeds DUPLICATE
# users_workspaces memberships inside the IN filter so DISTINCT provably
# collapses the duplicate output row (the head cannot exercise this: its
# workspace join makes duplicates distinct rows).

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "slack_bot", "name": "dynamic_menu", "as": "28312336", "skip": false, "input": {"dynamic_menu_name": "[CB] Search by User", "parameters": "[\n  {\n    \"name\": \"uemail\",\n    \"type\": \"string\",\n    \"optional\": true,\n    \"control_type\": \"text\",\n    \"label\": \"Uemail\"\n  },\n  {\n    \"name\": \"workspace_ids\",\n    \"type\": \"string\",\n    \"optional\": false,\n    \"control_type\": \"text\",\n    \"label\": \"Workspace ids\"\n  }\n]"}, "block": [{"number": 2, "keyword": "action", "provider": "workato_variable", "name": "declare_variable", "as": "97ffa775", "skip": false, "input": {"variables": {"schema": "[{\"name\":\"privatequery\",\"type\":\"string\",\"optional\":true,\"label\":\"privatequery\",\"control_type\":\"text\"}]"}}, "block": []}, {"number": 3, "keyword": "action", "provider": "workato_db_table", "name": "get_records", "as": "3c62d745", "skip": false, "input": {"11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "15ca98b2-7c7b-4c04-b713-f5d783b6b318": "string", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "79c522be-02a9-4d35-b94b-8dfa4960a2c2": "string", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "e0388988-bb54-4e13-942a-71a7a50db3b7": "string", "filters": [{"field_id": "79c522be-02a9-4d35-b94b-8dfa4960a2c2", "op_default": "eq", "value_default": "=_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"28312336\",\"path\":[\"parameters\",\"uemail\"]}').downcase"}], "limit": "100", "order_direction": "asc", "table_id": "13516"}, "block": []}, {"number": 4, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"3c62d745\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\"]}')}", "operand": "blank", "rhs": ""}], "operand": "and", "type": "compound"}, "block": [{"number": 5, "keyword": "action", "provider": "workato_variable", "name": "update_variables", "as": "7f8ed08b", "skip": false, "input": {"name": "690f29ef-508d-4f97-854a-2cc692253a3c:97ffa775:privatequery", "privatequery": "AND u.isprivate = FALSE"}, "block": []}]}, {"number": 6, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql", "as": "18dd84d9", "skip": false, "input": {"output_schema": "[{\"control_type\":\"number\",\"label\":\"Relationid\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"relationid\"},{\"control_type\":\"text\",\"label\":\"Username\",\"type\":\"string\",\"name\":\"username\"},{\"control_type\":\"text\",\"label\":\"Name\",\"type\":\"string\",\"name\":\"name\"}]", "parameters": {"data": {"parameter": "='%' + _dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"28312336\",\"path\":[\"typeahead\",\"value\"]}').downcase + '%'"}, "schema": "[{\"name\":\"parameter\",\"type\":\"string\",\"optional\":true,\"label\":\"parameter\",\"details\":{\"real_name\":\"parameter\"},\"control_type\":\"text\"}]"}, "sql": "SELECT distinct(r.relationid), u.username, a.name \nFROM DEMOINFRA_RELATION r \nINNER JOIN DEMOINFRA_USERS_WORKSPACES w ON w.relationid = r.relationid \nLEFT JOIN DEMOINFRA_USERS u ON u.id = r.userid \nLEFT JOIN DEMOINFRA_INSTANCES i ON r.instanceid = i.id \nLEFT JOIN DEMOINFRA_APPLICATIONS a ON i.applicationid = a.id\nWHERE (lower(u.username) like :parameter \nOR lower(a.name) like :parameter) \nAND w.workspaceid in (#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"28312336\",\"path\":[\"parameters\", \"workspace_ids\"]}')})\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"97ffa775\",\"path\":[\"privatequery\"]}')}", "update_only": "false"}, "block": []}, {"number": 7, "keyword": "action", "provider": "slack_bot", "name": "generate_menu_options", "as": "9c70908d", "skip": false, "input": {"options": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"18dd84d9\",\"path\":[\"rows\"]}')}", "label": "=_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"18dd84d9\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"username\"]}').gsub(\".onmicrosoft.com\", \"\")+ ' || ' + _dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"18dd84d9\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"name\"]}')", "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"18dd84d9\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"relationid\"]}')}"}, "use_option_groups": "false"}, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[int, str, str, str]] = [
    (2, DECLARE_STEP_AS, "workato_variable", "declare_variable"),
    (3, GET_RECORDS_STEP_AS, "workato_db_table", "get_records"),
    (5, UPDATE_STEP_AS, "workato_variable", "update_variables"),
    (6, SQL_STEP_AS, "snowflake", "run_custom_sql"),
    (7, MENU_STEP_AS, "slack_bot", "generate_menu_options"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "workato_db_table.get_records",
    "workato_runtime.update_variables",
    "snowflake.run_custom_sql",
    "slack_bot.generate_menu_options",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "snowflake.run_custom_sql",
    "slack_bot.generate_menu_options",
]
REQUIRED_EXPECT_KEYS = (
    "branch",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "exception_matched",
    "resolved_sql",
    "menu_options",
    "menu_options_ordered",
)
BRANCHES = (
    "not_excepted_private_hidden",
    "excepted_private_visible",
    "zero_matches_menu_empty",
)
_TYPEAHEAD_RE = re.compile(r"^[A-Za-z0-9 .@\-]*$")
_WORKSPACE_IDS_RE = re.compile(r"^\d+(,\d+)*$")


def validate_102760065(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    if str((raw.get("input") or {}).get("dynamic_menu_name") or "") != DYNAMIC_MENU_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} dynamic menu name changed")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    # Semantic pins over the drift-prone bits.
    get_node = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == GET_RECORDS_STEP_AS),
        None,
    )
    if not isinstance(get_node, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} get_records step missing")
    get_input = get_node.get("input") or {}
    if str(get_input.get("table_id") or "") != TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} exception table id changed")
    filters = get_input.get("filters") or [{}]
    if (
        len(filters) != 1
        or filters[0].get("op_default") != "eq"
        or not str(filters[0].get("value_default") or "").endswith(".downcase")
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} exception filter changed: {filters!r}")
    if_nodes = [node for node in _walk_nodes(raw) if node.get("keyword") == "if"]
    if len(if_nodes) != 1:
        raise RuntimeError(f"recipe {RECIPE_ID} expected exactly one IF gate")
    condition = ((if_nodes[0].get("input") or {}).get("conditions") or [{}])[0]
    if condition.get("operand") != "blank" or F_RECID not in str(condition.get("lhs") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} IF blank condition changed: {condition!r}")
    update = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == UPDATE_STEP_AS), None
    )
    if not isinstance(update, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} update_variables step missing")
    update_input = update.get("input") or {}
    if update_input.get("privatequery") != PRIVATE_SUFFIX or str(
        update_input.get("name") or ""
    ).split(":")[1:] != [DECLARE_STEP_AS, "privatequery"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} privatequery update no longer targets the declared "
            f"step: {update_input!r}"
        )
    sql_node = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == SQL_STEP_AS), None
    )
    if not isinstance(sql_node, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} snowflake step missing")
    sql = str((sql_node.get("input") or {}).get("sql") or "")
    for table in TABLE_SPECS:
        if not re.search(r"(?<![A-Za-z0-9_$])" + table + r"(?![A-Za-z0-9_$])", sql):
            raise RuntimeError(f"recipe {RECIPE_ID} SQL lost table {table}")
    if ":parameter" not in sql or "privatequery" not in sql:
        raise RuntimeError(f"recipe {RECIPE_ID} SQL bind/suffix pills changed")
    menu = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == MENU_STEP_AS), None
    )
    if not isinstance(menu, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} menu step missing")
    menu_input = menu.get("input") or {}
    label = str((menu_input.get("options") or {}).get("label") or "")
    if '.gsub(".onmicrosoft.com", "")' not in label or label.count("' || '") != 1:
        raise RuntimeError(f"recipe {RECIPE_ID} menu label formula changed: {label!r}")
    if str(menu_input.get("use_option_groups") or "") != "false":
        raise RuntimeError(f"recipe {RECIPE_ID} menu grouping changed")
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
        "dynamic_menu_name": DYNAMIC_MENU_NAME,
        "table_id": TABLE_ID,
        "snowflake_tables": sorted(TABLE_SPECS),
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


def seed_102760065(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_102760065(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    uemail, workspace_ids, typeahead = _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["snowflake_live", "workato_db_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} every variant seeds exactly workato_db_table + "
            f"snowflake_live (all branches reach the live SQL); got {sorted(seed_in.keys())}"
        )
    expect = data.get("expect")
    _require_expect_common(expect)
    if data.get("force_action_error") is not None:
        raise RuntimeError(f"recipe {RECIPE_ID} has no catch: forcing an action error is invalid")
    exception_rows = _require_exception_table(seed_in["workato_db_table"])
    _require_snowflake_section(seed_in["snowflake_live"])
    matched = any(row[F_EMAIL] == uemail.lower() for row in exception_rows)
    _require_branch(expect, matched, workspace_ids, typeahead)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
    }
    provision = ctx.tools.call(
        "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    out["snowflake_live"] = deepcopy(provision["state"])
    out["snowflake_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_102760065(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_102760065(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed carries no snowflake_live state")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed carries no workato_db_table state")
    raw_execution: dict[str, Any] | None = None
    initial_snapshot: dict[str, Any] = {}
    final_snapshot: dict[str, Any] = {}
    cleanup: dict[str, Any] | None = None
    try:
        initial_snapshot = dict(ctx.tools.call("harness.snowflake.snapshot", {}))
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = dict(ctx.tools.call("harness.snowflake.snapshot", {}))
    finally:
        # Required cleanup: the seeder create-or-replaced the registered live
        # tables; drop them whether or not the run completed.
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
    result["verifier"] = verify_102760065(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> tuple[str, str, str]:
    if sorted(trigger.keys()) != ["parameters", "typeahead"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly parameters + "
            f"typeahead; got {sorted(trigger.keys())}"
        )
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict) or sorted(parameters.keys()) != [
        "uemail",
        "workspace_ids",
    ]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} parameters must carry exactly uemail + workspace_ids"
        )
    uemail = parameters.get("uemail")
    if not isinstance(uemail, str) or not uemail.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} parameters.uemail must be non-empty: the exception "
            "filter dereferences it (a missing pill fails the run, never a branch)"
        )
    workspace_ids = parameters.get("workspace_ids")
    if not isinstance(workspace_ids, str) or not _WORKSPACE_IDS_RE.fullmatch(workspace_ids):
        raise RuntimeError(
            f"recipe {RECIPE_ID} parameters.workspace_ids interpolates INLINE into "
            f"the SQL IN (...): only comma-separated integers are accepted; got "
            f"{workspace_ids!r}"
        )
    typeahead = trigger.get("typeahead")
    if (
        not isinstance(typeahead, dict)
        or sorted(typeahead.keys()) != ["value"]
        or not isinstance(typeahead.get("value"), str)
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} typeahead must be {{'value': <str>}}")
    value = typeahead["value"]
    if not _TYPEAHEAD_RE.fullmatch(value):
        raise RuntimeError(
            f"recipe {RECIPE_ID} typeahead.value feeds the LIKE bind as "
            f"'%'+value.downcase+'%': quotes, backslashes and LIKE wildcards (%/_) "
            f"are rejected so groundtruth stays a plain substring match; got {value!r}"
        )
    return uemail, workspace_ids, value


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
    if not isinstance(expect.get("menu_options"), list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.menu_options must be a list")


def _require_exception_table(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table must be exactly {{'tables': ...}}"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the exception table seed must declare exactly table "
            f"{TABLE_ID!r} (an empty list is a valid empty table)"
        )
    rows = tables[TABLE_ID]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {TABLE_ID} rows must be a list")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(EXCEPTION_ROW_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} exception row {idx} must carry exactly the 6 "
                f"hashed schema fields; got {sorted(row.keys()) if isinstance(row, dict) else row!r}"
            )
        for key, value in row.items():
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} exception row {idx} field {key} must be a "
                    f"non-empty string; got {value!r}"
                )
    return rows


def _require_snowflake_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the SQL uses no CURRENT_DATE/TIMESTAMP, so current_time is not allowed)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted(TABLE_SPECS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly the "
            f"{len(TABLE_SPECS)} bare-named tables {sorted(TABLE_SPECS)}"
        )
    for name, spec in tables.items():
        if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {name} spec must be exactly "
                f"{{'columns': ..., 'rows': ...}}"
            )
        if spec["columns"] != TABLE_SPECS[name]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {name} must declare exactly the columns "
                f"{TABLE_SPECS[name]}; got {spec['columns']!r}"
            )
        rows = spec["rows"]
        if not isinstance(rows, list):
            raise RuntimeError(f"recipe {RECIPE_ID} table {name} rows must be a list")
        for idx, row in enumerate(rows):
            if not isinstance(row, dict) or sorted(row.keys()) != sorted(TABLE_SPECS[name]):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {name} row {idx} must carry exactly "
                    f"{sorted(TABLE_SPECS[name])}; got {row!r}"
                )
            for column, value in row.items():
                kind = TABLE_SPECS[name][column]
                ok = (
                    isinstance(value, bool)
                    if kind == "boolean"
                    else isinstance(value, int) and not isinstance(value, bool)
                    if kind == "integer"
                    else isinstance(value, str) and bool(value.strip())
                )
                if not ok:
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} table {name} row {idx} column {column} "
                        f"must be {kind}; got {value!r}"
                    )


def _require_branch(
    expect: dict[str, Any],
    exception_matched: bool,
    workspace_ids: str,
    typeahead: str,
) -> None:
    branch = expect["branch"]
    if expect.get("exception_matched") is not exception_matched:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.exception_matched={expect.get('exception_matched')!r} "
            f"disagrees with the seeded exception table (computed {exception_matched})"
        )
    if (branch == "excepted_private_visible") is not exception_matched:
        raise RuntimeError(
            f"recipe {RECIPE_ID} branch {branch!r} disagrees with the seeded "
            f"exception table (uemail.downcase match computed {exception_matched})"
        )
    suffix = "" if exception_matched else PRIVATE_SUFFIX
    expected_sql = SQL_TEMPLATE.format(ws=workspace_ids, suffix=suffix)
    if expect.get("resolved_sql") != expected_sql:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.resolved_sql must be the pill-interpolated "
            f"SQL text (workspace_ids inline, suffix {suffix!r}); expected "
            f"{expected_sql!r}, got {expect.get('resolved_sql')!r}"
        )
    expected_count = 4 if exception_matched else 5
    checks = (
        expect.get("executed_action_count") == expected_count,
        expect.get("tools") == ALLOWED_TOOLS,
        len(expect.get("tool_expectations") or []) == 3,
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} {branch} expect block is inconsistent "
            f"({expected_count} actions, 3 registry tools): {expect!r}"
        )
    options = expect.get("menu_options") or []
    if branch == "zero_matches_menu_empty":
        if options != [] or expect.get("menu_options_ordered") is not True:
            raise RuntimeError(
                f"recipe {RECIPE_ID} zero_matches variants must pin an EMPTY ordered "
                f"menu; got {options!r}"
            )
    elif len(options) > 1 and expect.get("menu_options_ordered") is not False:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the SQL has no ORDER BY: multi-row menus must set "
            "menu_options_ordered false (multiset compare)"
        )
    for option in options:
        if (
            not isinstance(option, dict)
            or sorted(option.keys()) != ["label", "value"]
            or not isinstance(option.get("label"), str)
            or not isinstance(option.get("value"), int)
            or option["label"].count(" || ") != 1
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} menu options must be {{label: '<user> || <app>', "
                f"value: <int relationid>}}; got {option!r}"
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
