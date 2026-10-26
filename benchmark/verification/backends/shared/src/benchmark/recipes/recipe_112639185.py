from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_112639185


RECIPE_ID = "112639185"
SEED_TYPE = "recipe_function_heatmap_city_lookup_sheets_bulk_variant"
TRACK = "live_google_sheets_recipe_function_heatmap_contacts_bulk"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
LOOKUP_TABLES: list[tuple[str, str]] = [
    ("3667208", "Chicago Heatmap Invite List (Q3)"),
    ("3667207", "Austin Heatmap Invite List (Q3)"),
    ("3667140", "Boston Heatmap Invite List (Q3)"),
    ("3667146", "New York Heatmap Invite List (Q3)"),
    ("3667213", "Denver Heatmap Invite List (Q3)"),
    ("3667209", "Los Angeles Heatmap Invite List (Q3)"),
]
OWNER_NAME_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\","
    "\"line\":\"46f1feda\",\"path\":[\"parameters\", \"Owner_Name\"]}')}"
)
CITY_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\","
    "\"line\":\"46f1feda\",\"path\":[\"parameters\", \"City\"]}')}"
)
CITY_VARIABLE_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\","
    "\"line\":\"58abf69a\",\"path\":[\"City\"]}')}"
)
EXPECTED_IF_RHS: list[str] = [
    "<anon>City_1</anon>",
    "IT",
    "<anon>City_2</anon>",
    "IT",
    "<anon>City_3</anon>",
    "<anon>City_4</anon>",
    "<anon>City_5</anon>",
    "GTM",
    "<anon>City_6</anon>",
    "IT",
]
CREATE_LIST_NAME_TEMPLATE = OWNER_NAME_PILL + " - Heatmap Contacts"
CREATE_LIST_SOURCE_FORMULA = (
    "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\","
    "\"line\":\"b2992d26\",\"path\":[\"list_items\"]}')"
)
QUERY_SQL_TEMPLATE = (
    "SELECT * FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\","
    "\"line\":\"3f26a6d5\",\"path\":[\"list_name\"]}')} ORDER BY "
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\","
    "\"line\":\"3f26a6d5\",\"path\":[\"columns\", \"Company\"]}')} ASC"
)
QUERY_RESULT_SCHEMA_JSON = (
    '[{"name":"Account_Owner","type":"string","optional":false,"control_type":"text","label":"Owner"},'
    '{"name":"Company","type":"string","optional":false,"control_type":"text","label":"Company"},'
    '{"name":"First_Name","type":"string","optional":false,"control_type":"text","label":"First name"},'
    '{"name":"Last_Name","type":"string","optional":false,"control_type":"text","label":"Last name"},'
    '{"name":"Email","type":"string","optional":false,"control_type":"text","label":"Email"},'
    '{"name":"Title","type":"string","optional":false,"control_type":"text","label":"Title"},'
    '{"name":"City","type":"string","optional":false,"control_type":"text","label":"Status"},'
    '{"name":"Persona","type":"string","optional":false,"control_type":"text","label":"Persona"},'
    '{"name":"Exec_Connect","type":"string","optional":false,"control_type":"text","label":"Exec connect"},'
    '{"name":"Num_Invites","type":"string","optional":false,"control_type":"text","label":"Num invites"}]'
)
SHEET_HEADER_TRAILING_TABS = "Who will own invite? " + "\t" * 16
SHEET_HEADERS: list[str] = [
    "Owner",
    "Account Name",
    "First Name",
    "Last Name",
    "Email",
    "Title",
    "City",
    "Executive Connection?",
    "Number of Previous Invites",
    SHEET_HEADER_TRAILING_TABS,
]
BULK_COLUMN_HEADERS = "\n".join(SHEET_HEADERS)
BULK_SPREADSHEET_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\","
    "\"line\":\"46f1feda\",\"path\":[\"parameters\", \"Sheet_id\"]}')}"
)
BULK_SHEET_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\","
    "\"line\":\"46f1feda\",\"path\":[\"parameters\", \"Region\"]}')}"
)
BULK_SOURCE_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\","
    "\"line\":\"967cf3aa\",\"path\":[\"rows\"]}')}"
)
CATCH_ERROR_TEMPLATE = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"58b0935d\",\"path\":[\"type\"]}')}"
    " - "
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"58b0935d\",\"path\":[\"message\"]}')}"
)
TRIGGER_PARAMETERS_SCHEMA_JSON = (
    '[{"name":"Owner_Name","type":"string","optional":false,"control_type":"text","label":"Owner name"},'
    '{"name":"Sheet_id","type":"string","optional":false,"control_type":"text","label":"Sheet ID"},'
    '{"name":"City","type":"string","optional":true,"control_type":"text","label":"City"},'
    '{"name":"Region","type":"string","optional":false,"control_type":"text","label":"Region"}]'
)
PARAMETER_KEYS = ["Owner_Name", "Sheet_id", "City", "Region"]
INSERT_TARGET_NAME = "9be1d405-9900-45d2-948c-894f96b89dd1:b2992d26"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_variable", "declare_variable"),  # 58abf69a step 2
    ("workato_variable", "declare_list"),  # b2992d26 step 3
    ("lookup_table", "search_entries"),  # 88e78e30 step 5 (Chicago)
    ("workato_variable", "insert_to_list"),  # d5adef10 step 8
    ("lookup_table", "search_entries"),  # 5c63a2da step 10 (Austin)
    ("workato_variable", "insert_to_list"),  # f9150381 step 13
    ("lookup_table", "search_entries"),  # bd240acc step 15 (Boston)
    ("workato_variable", "insert_to_list"),  # 4f5c1d09 step 17
    ("lookup_table", "search_entries"),  # 5d36b8c9 step 19 (New York)
    ("workato_variable", "insert_to_list"),  # 1101ebc5 step 21
    ("lookup_table", "search_entries"),  # 3300892f step 23 (Denver)
    ("workato_variable", "insert_to_list"),  # 6891a080 step 26
    ("lookup_table", "search_entries"),  # c0c4c82e step 28 (Los Angeles)
    ("workato_variable", "insert_to_list"),  # 648c1009 step 31
    ("workato_smart_list", "create_list"),  # 3f26a6d5 step 32
    ("workato_smart_list", "query_list"),  # 967cf3aa step 33
    ("google_sheets", "add_row_v4_bulk"),  # 1c727c37 step 35 (inside TRY)
    ("workato_recipe_function", "return_result"),  # 18006b7b step 37 (CATCH)
    ("workato_recipe_function", "return_result"),  # 2c3c9900 step 38
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "workato_runtime.declare_list",
    "lookup_table.search_entries",
    "workato_runtime.insert_to_list",
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
    "google_sheets.add_spreadsheet_row_v4",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "google_sheets.add_spreadsheet_row_v4",
    "workato_recipe_function.return_result",
]


def validate_112639185(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    trigger_in = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    if str(trigger_in.get("parameters_schema_json") or "") != TRIGGER_PARAMETERS_SCHEMA_JSON:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters schema changed")
    actions = _collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    if_rhs = _collect_if_rhs(raw)
    if if_rhs != EXPECTED_IF_RHS:
        raise RuntimeError(f"recipe {RECIPE_ID} IF conditions changed: {if_rhs}")
    searches = [action for action in actions if action.get("provider") == "lookup_table"]
    for search, (table_id, display_name) in zip(searches, LOOKUP_TABLES):
        search_in = search.get("input") if isinstance(search.get("input"), dict) else {}
        picked = search.get("dynamicPickListSelection") if isinstance(search.get("dynamicPickListSelection"), dict) else {}
        if str(search_in.get("lookup_table_id") or "") != table_id:
            raise RuntimeError(f"recipe {RECIPE_ID} lookup table id changed: {search_in}")
        if str(picked.get("lookup_table_id") or "") != display_name:
            raise RuntimeError(f"recipe {RECIPE_ID} lookup table display name changed: {picked}")
        parameters = search_in.get("parameters") if isinstance(search_in.get("parameters"), dict) else {}
        if parameters != {"col1": OWNER_NAME_PILL}:
            raise RuntimeError(f"recipe {RECIPE_ID} lookup search filter changed: {parameters}")
    declare_in = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    declared = declare_in.get("variables") if isinstance(declare_in.get("variables"), dict) else {}
    declared_data = declared.get("data") if isinstance(declared.get("data"), dict) else {}
    if declared_data != {"City": CITY_PILL}:
        raise RuntimeError(f"recipe {RECIPE_ID} City variable declaration changed: {declared_data}")
    inserts = [action for action in actions if action.get("name") == "insert_to_list"]
    for insert in inserts:
        insert_in = insert.get("input") if isinstance(insert.get("input"), dict) else {}
        if str(insert_in.get("name") or "") != INSERT_TARGET_NAME:
            raise RuntimeError(f"recipe {RECIPE_ID} insert_to_list target changed: {insert_in}")
        item = insert_in.get("list_item") if isinstance(insert_in.get("list_item"), dict) else {}
        if str(item.get("City") or "") != CITY_VARIABLE_PILL:
            raise RuntimeError(f"recipe {RECIPE_ID} insert_to_list City pill changed: {item}")
    create_in = actions[14].get("input") if isinstance(actions[14].get("input"), dict) else {}
    if str(create_in.get("list_name") or "") != CREATE_LIST_NAME_TEMPLATE:
        raise RuntimeError(f"recipe {RECIPE_ID} smart list name template changed: {create_in}")
    if str(create_in.get("list_source") or "") != CREATE_LIST_SOURCE_FORMULA:
        raise RuntimeError(f"recipe {RECIPE_ID} smart list source formula changed: {create_in}")
    query_in = actions[15].get("input") if isinstance(actions[15].get("input"), dict) else {}
    if str(query_in.get("sql") or "") != QUERY_SQL_TEMPLATE:
        raise RuntimeError(f"recipe {RECIPE_ID} smart list query SQL changed: {query_in.get('sql')}")
    if str(query_in.get("result_schema_json") or "") != QUERY_RESULT_SCHEMA_JSON:
        raise RuntimeError(f"recipe {RECIPE_ID} smart list result schema changed")
    if str(query_in.get("output_schema_by") or "") != "index" or str(query_in.get("headers") or "") != "true":
        raise RuntimeError(f"recipe {RECIPE_ID} smart list query options changed: {query_in}")
    bulk_in = actions[16].get("input") if isinstance(actions[16].get("input"), dict) else {}
    if str(bulk_in.get("column_headers") or "") != BULK_COLUMN_HEADERS:
        raise RuntimeError(f"recipe {RECIPE_ID} sheet column headers changed")
    if str(bulk_in.get("spreadsheet_id") or "") != BULK_SPREADSHEET_PILL:
        raise RuntimeError(f"recipe {RECIPE_ID} bulk spreadsheet pill changed")
    if str(bulk_in.get("sheet_name") or "") != BULK_SHEET_PILL:
        raise RuntimeError(f"recipe {RECIPE_ID} bulk sheet name pill changed")
    bulk_rows = bulk_in.get("rows") if isinstance(bulk_in.get("rows"), dict) else {}
    if str(bulk_rows.get("____source") or "") != BULK_SOURCE_PILL:
        raise RuntimeError(f"recipe {RECIPE_ID} bulk rows source pill changed")
    if str(bulk_rows.get("col_City") or "") != CITY_VARIABLE_PILL:
        raise RuntimeError(f"recipe {RECIPE_ID} bulk col_City pill changed")
    if "col_" + SHEET_HEADER_TRAILING_TABS in bulk_rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} bulk rows now map the 'Who will own invite?' column "
            "(it must stay unmapped/blank)"
        )
    catch_in = actions[17].get("input") if isinstance(actions[17].get("input"), dict) else {}
    catch_result = catch_in.get("result") if isinstance(catch_in.get("result"), dict) else {}
    if catch_result != {"Error": CATCH_ERROR_TEMPLATE, "Success": "false"}:
        raise RuntimeError(f"recipe {RECIPE_ID} catch return_result changed: {catch_result}")
    final_in = actions[18].get("input") if isinstance(actions[18].get("input"), dict) else {}
    if final_in.get("result") != {"Success": "true"}:
        raise RuntimeError(f"recipe {RECIPE_ID} final return_result changed: {final_in}")
    catch_node = _find_catch(raw)
    if catch_node is None or str((catch_node.get("input") or {}).get("max_retry_count")) != "0":
        raise RuntimeError(f"recipe {RECIPE_ID} try/catch structure changed")
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


def seed_112639185(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_112639185(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict) or sorted(parameters.keys()) != sorted(PARAMETER_KEYS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must carry exactly "
            f"{PARAMETER_KEYS}; got {sorted(parameters.keys()) if isinstance(parameters, dict) else parameters}"
        )
    for key in PARAMETER_KEYS:
        if not str(parameters.get(key) or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter {key!r} must be a non-empty string")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    lookup_seed = seed_in.get("lookup_table")
    tables = lookup_seed.get("tables") if isinstance(lookup_seed, dict) else None
    if not isinstance(tables, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed must define lookup_table.tables explicitly")
    expected_ids = [table_id for table_id, _ in LOOKUP_TABLES]
    if sorted(tables.keys()) != sorted(expected_ids):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare ALL six heatmap lookup tables "
            f"{expected_ids} (empty tables still declare an explicit empty list); got {sorted(tables.keys())}"
        )
    for table_id, rows in tables.items():
        if not isinstance(rows, list):
            raise RuntimeError(f"recipe {RECIPE_ID} lookup table {table_id} rows must be a list")
    names = lookup_seed.get("names")
    if names != {display_name: table_id for table_id, display_name in LOOKUP_TABLES}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed lookup_table.names must map the six Q3 heatmap "
            f"display names to their table ids; got {names}"
        )
    sheets_seed = seed_in.get("sheets")
    if not isinstance(sheets_seed, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.sheets")
    if sheets_seed.get("headers") != SHEET_HEADERS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets.headers must pin the ten raw sheet headers "
            "verbatim (including the trailing-tabs 'Who will own invite?' column)"
        )
    if sheets_seed.get("rows") != []:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets.rows must be an explicit empty list "
            "(the recipe only appends; expects are derived from an empty tab)"
        )
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    sheets_seed_response = ctx.tools.call("harness.google_sheets.seed_rows", {"sheets": sheets_seed})
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(expect),
        "raw_validation": validation,
        "lookup_table": deepcopy(lookup_seed),
        "sheets": deepcopy(sheets_seed),
        "sheets_seed_response": sheets_seed_response,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if isinstance(data.get("force_action_error"), dict):
        out["force_action_error"] = deepcopy(data["force_action_error"])
    return attach_variant(out, ctx)


def run_112639185(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_112639185(raw)
    if not ctx.env.sheets_spreadsheet_id or not ctx.env.sheets_tab:
        raise RuntimeError("missing SHEETS_SPREADSHEET_ID or SHEETS_TAB for live Google Sheets append")
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    try:
        details["initial_snapshot"] = _snapshot(ctx)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
    finally:
        # The tab was fully overwritten by this run's seed and the recipe only
        # appends, so the final snapshot IS the cleanup evidence: rerunning any
        # variant starts from a freshly re-seeded (headers-only) tab. No live
        # objects other than benchmark-sheet rows are created.
        details["final_snapshot"] = _snapshot(ctx)
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_112639185(result)
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


def _collect_if_rhs(node: dict[str, Any]) -> list[str]:
    found: list[str] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "if":
            for condition in ((child.get("input") or {}).get("conditions") or []):
                if isinstance(condition, dict):
                    found.append(str(condition.get("rhs") or ""))
        found.extend(_collect_if_rhs(child))
    return found


def _find_catch(node: dict[str, Any]) -> dict[str, Any] | None:
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "catch":
            return child
        nested = _find_catch(child)
        if nested is not None:
            return nested
    return None


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return {
        "google_sheets": ctx.tools.call("harness.google_sheets.snapshot", {}),
        "lookup_table": ctx.tools.call("harness.lookup_table.snapshot", {}),
    }


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
