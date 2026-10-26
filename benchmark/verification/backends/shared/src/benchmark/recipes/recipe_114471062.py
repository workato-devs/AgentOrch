from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_114471062


RECIPE_ID = "114471062"
SEED_TYPE = "fy_quota_sheet_to_snowflake_reload_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "49b2799a"
DECLARE_AS = "fd2899ad"
SEARCH_AS = "0a1d8423"
CREATE_LIST_AS = "010b3708"
QUERY_LIST_AS = "1375c2b6"
TRUNCATE_AS = "f4a05902"
UPSERT_AS = "b3ea987f"
STOP_STEP_NUMBER = 5
SNOWFLAKE_TABLE = "SALESFORCE.FY_QUOTA"
SNOWFLAKE_COLUMNS = {
    "fiscal_period": "string",
    "fiscal_period_and_month": "string",
    "fiscal_year": "string",
    "fy_full_monthly_quota": "float",
    "month_of_quota_final": "number",
    "quota_amount": "float",
    "ramp_status": "string",
    "row_number": "number",
    "sales_sub_team": "string",
    "sfdc_sales_team": "string",
    "user": "string",
}
SHEET_HEADERS = [
    "col_user",
    "col_sfdc_sales_team",
    "col_sales_sub_team",
    "col_fy_full_monthly_quota",
    "col_fiscal_year",
    "col_month_of_quota_final",
    "col_fiscal_period",
    "col_fiscal_period_and_month",
    "col_quota_amount",
    "col_ramp_status",
]
HEADER_ECHO_ROW = {header: header[len("col_"):] for header in SHEET_HEADERS}


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "clock", "name": "scheduled_event", "as": "49b2799a", "skip": false, "input": {"time_unit": "days", "timezone": "Etc/UTC", "trigger_at": "14:00:00", "trigger_every": "1"}, "block": [{"number": 2, "keyword": "action", "provider": "workato_variable", "name": "declare_variable", "as": "fd2899ad", "skip": false, "input": {"variables": {"data": {"Table": "FY_QUOTA", "batch_size": "16000"}, "schema": "[{\"name\":\"batch_size\",\"type\":\"integer\",\"optional\":true,\"label\":\"batch size\",\"control_type\":\"integer\"},{\"name\":\"Table\",\"type\":\"string\",\"optional\":true,\"label\":\"Table\",\"details\":{\"real_name\":\"Table\"},\"control_type\":\"text\"}]"}}, "block": []}, {"number": 3, "keyword": "action", "provider": "google_sheets", "name": "search_spreadsheet_rows_v4_new", "as": "0a1d8423", "skip": false, "input": {"column_headers": "user\nsfdc_sales_team\nsales_sub_team\nfy_full_monthly_quota\nfiscal_year\nmonth_of_quota_final\nfiscal_period\nfiscal_period_and_month\nquota_amount\nramp_status", "count": "50000", "data": {"col_user": "="}, "sheet_name": "FY21 - FY26 Monthly Quotas - For Data Upload", "spreadsheet_id": "<anon>2AbC3DeF4GhI5JkL6MnO7PqR8StU9VwX0YzA1BcD2EfG</anon>", "team_drives": "0AAIkb6BAiONcUk9PVA/0AAIkb6BAiONcUk9PVA"}, "block": []}, {"number": 4, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"0a1d8423\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}", "operand": "equals_to", "rhs": "50000"}], "operand": "and", "type": "compound"}, "block": [{"number": 5, "keyword": "stop", "provider": "", "name": "", "as": "", "skip": false, "input": {"stop_reason": "Result size has been hit", "stop_with_error": "true"}, "block": []}]}, {"number": 6, "keyword": "action", "provider": "workato_smart_list", "name": "create_list", "as": "010b3708", "skip": false, "input": {"list_name": "fy_quota", "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"0a1d8423\",\"path\":[\"rows\"]}')[1..-1]", "primary_index": "row_number"}, "block": []}, {"number": 7, "keyword": "action", "provider": "workato_smart_list", "name": "query_list", "as": "1375c2b6", "skip": false, "input": {"col_sep": "comma", "csv": "false", "headers": "false", "output_schema_by": "index", "result_schema_json": "[{\"name\":\"row_number\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\"},{\"name\":\"user\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"sfdc_sales_team\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"sales_sub_team\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"fy_full_monthly_quota\",\"type\":\"number\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"fiscal_year\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"month_of_quota_final\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\"},{\"name\":\"fiscal_period\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"fiscal_period_and_month\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"quota_amount\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\"},{\"name\":\"ramp_status\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Ramp status\"}]", "sql": "select \n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"010b3708\",\"path\":[\"columns\", \"row_number\"]}')},\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"010b3708\",\"path\":[\"columns\", \"col_user\"]}')},\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"010b3708\",\"path\":[\"columns\", \"col_sfdc_sales_team\"]}')},\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"010b3708\",\"path\":[\"columns\", \"col_sales_sub_team\"]}')},\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"010b3708\",\"path\":[\"columns\", \"col_fy_full_monthly_quota\"]}')},\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"010b3708\",\"path\":[\"columns\", \"col_fiscal_year\"]}')},\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"010b3708\",\"path\":[\"columns\", \"col_month_of_quota_final\"]}')},\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"010b3708\",\"path\":[\"columns\", \"col_fiscal_period\"]}')},\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"010b3708\",\"path\":[\"columns\", \"col_fiscal_period_and_month\"]}')},\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"010b3708\",\"path\":[\"columns\", \"col_quota_amount\"]}')},\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"010b3708\",\"path\":[\"columns\", \"col_ramp_status\"]}')}\n\nfrom #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"010b3708\",\"path\":[\"list_name\"]}')}"}, "block": []}, {"number": 8, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql", "as": "f4a05902", "skip": false, "input": {"sql": "TRUNCATE TABLE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"fd2899ad\",\"path\":[\"Table\"]}')}", "update_only": "false"}, "block": []}, {"number": 9, "keyword": "action", "provider": "snowflake", "name": "upsert_rows_batch", "as": "b3ea987f", "skip": false, "input": {"key_columns": "ROW_NUMBER", "rows": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"1375c2b6\",\"path\":[\"rows\"]}')}", "fiscal_period": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"1375c2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"fiscal_period\"]}')}", "fiscal_period_and_month": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"1375c2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"fiscal_period_and_month\"]}')}", "fiscal_year": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"1375c2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"fiscal_year\"]}')}", "fy_full_monthly_quota": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"1375c2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"fy_full_monthly_quota\"]}')}", "month_of_quota_final": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"1375c2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"month_of_quota_final\"]}')}", "quota_amount": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"1375c2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"quota_amount\"]}')}", "ramp_status": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"1375c2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"ramp_status\"]}')}", "row_number": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"1375c2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"row_number\"]}')}", "sales_sub_team": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"1375c2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"sales_sub_team\"]}')}", "sfdc_sales_team": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"1375c2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"sfdc_sales_team\"]}')}", "user": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"1375c2b6\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"user\"]}')}"}, "table": "SALESFORCE.FY_QUOTA"}, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (DECLARE_AS, "workato_variable", "declare_variable"),
    (SEARCH_AS, "google_sheets", "search_spreadsheet_rows_v4_new"),
    (CREATE_LIST_AS, "workato_smart_list", "create_list"),
    (QUERY_LIST_AS, "workato_smart_list", "query_list"),
    (TRUNCATE_AS, "snowflake", "run_custom_sql"),
    (UPSERT_AS, "snowflake", "upsert_rows_batch"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "google_sheets.search_spreadsheet_rows_v4_new",
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
    "snowflake.run_custom_sql",
    "snowflake.upsert_rows_batch",
]
ALLOWED_TOOLS: list[str] = [
    "google_sheets.search_spreadsheet_rows_v4_new",
    "snowflake.run_custom_sql",
    "snowflake.upsert_rows_batch",
]
EXPECTED_TRIGGER_INPUT = {
    "time_unit": "days",
    "timezone": "Etc/UTC",
    "trigger_at": "14:00:00",
    "trigger_every": "1",
}
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "stopped",
    "search_row_count",
    "smart_list_rows",
    "query_sql",
    "query_rows",
    "upsert_created",
    "upsert_updated",
    "final_fy_quota_rows",
)
MAX_SEED_ROWS = 100


def validate_114471062(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    if raw.get("input") != EXPECTED_TRIGGER_INPUT:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger schedule changed: {raw.get('input')!r}")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    nodes = {str(node.get("as") or ""): node for node in _walk_nodes(raw)}
    # Semantic pins (the tree pin holds the bytes; these name the traps):
    # 1. the retrieve-all blank formula criterion,
    search_input = (nodes[SEARCH_AS].get("input") or {})
    if search_input.get("data") != {"col_user": "="} or str(search_input.get("count")) != "50000":
        raise RuntimeError(f"recipe {RECIPE_ID} search criterion changed: {search_input!r}")
    # 2. the load-bearing [1..-1] header-drop slice,
    list_source = str((nodes[CREATE_LIST_AS].get("input") or {}).get("list_source") or "")
    if "[1..-1]" not in list_source or SEARCH_AS not in list_source:
        raise RuntimeError(f"recipe {RECIPE_ID} create_list slice changed: {list_source!r}")
    # 3. the bare 1-part TRUNCATE pill,
    truncate_sql = str((nodes[TRUNCATE_AS].get("input") or {}).get("sql") or "")
    if not truncate_sql.startswith("TRUNCATE TABLE #{") or DECLARE_AS not in truncate_sql:
        raise RuntimeError(f"recipe {RECIPE_ID} TRUNCATE sql changed: {truncate_sql!r}")
    # 4. the upsert target + key.
    upsert_input = nodes[UPSERT_AS].get("input") or {}
    if (
        str(upsert_input.get("table")) != SNOWFLAKE_TABLE
        or str(upsert_input.get("key_columns")) != "ROW_NUMBER"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} upsert target changed: {upsert_input!r}")
    # 5. the dead stop branch stays exactly as documented.
    stop_nodes = [node for node in _walk_nodes(raw) if node.get("keyword") == "stop"]
    if len(stop_nodes) != 1 or stop_nodes[0].get("number") != STOP_STEP_NUMBER:
        raise RuntimeError(f"recipe {RECIPE_ID} stop layout changed: {stop_nodes!r}")
    stop_input = stop_nodes[0].get("input") or {}
    if (
        str(stop_input.get("stop_with_error")) != "true"
        or str(stop_input.get("stop_reason")) != "Result size has been hit"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} stop config changed: {stop_input!r}")
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
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


def seed_114471062(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_114471062(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (payload-less scheduler "
            f"tick; nothing dereferences the trigger): {trigger!r}"
        )
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no try/catch: a forced action error would fail the whole "
            "run instead of exercising a recipe branch"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["google_sheets", "snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the google_sheets and "
            f"snowflake_live sections; got "
            f"{sorted(seed_in.keys()) if isinstance(seed_in, dict) else seed_in!r}"
        )
    sheets_section = _require_sheets_section(seed_in["google_sheets"])
    _require_snowflake_section(seed_in["snowflake_live"])
    expect = data.get("expect")
    _require_expect_shape(expect)
    sheet_provision = ctx.tools.call("harness.google_sheets.seed_rows", {"sheets": sheets_section})
    if not sheet_provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Google Sheets seed failed: {sheet_provision}")
    provision = ctx.tools.call(
        "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "google_sheets": deepcopy(sheets_section),
        "sheets_seed_response": deepcopy(sheet_provision),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_114471062(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_114471062(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("google_sheets"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing google_sheets section")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect"),
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    raw_execution: dict[str, Any] | None = None
    snowflake_cleanup: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = _snapshot(ctx)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx)
    finally:
        # SALESFORCE.FY_QUOTA is a benchmark-owned live table: drop it even
        # when execution fails. The sheets tab is fully re-seeded per run
        # (cleanup principle), so it needs no teardown.
        snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    details["cleanup_response"] = {"snowflake_live": snowflake_cleanup}
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_114471062(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_sheets_section(section: Any) -> dict[str, Any]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["headers", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.google_sheets must be exactly {{'headers','rows'}}"
        )
    if section.get("headers") != SHEET_HEADERS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.google_sheets.headers must be exactly the 10 literal "
            "col_-prefixed quota headers in canonical order (the row pills, create_list "
            "source keys and query column pills all dereference these keys)"
        )
    rows = section.get("rows")
    if not isinstance(rows, list) or len(rows) < 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.google_sheets.rows needs the header-echo row plus at "
            "least one data row"
        )
    if len(rows) > MAX_SEED_ROWS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} refuses seeds over {MAX_SEED_ROWS} sheet rows (the IF-4 "
            "'50000 rows' stop branch is documented dead; a huge seed cannot flip it and "
            "only strains the live tab)"
        )
    if rows[0] != HEADER_ECHO_ROW:
        raise RuntimeError(
            f"recipe {RECIPE_ID} sheet data row 0 must be the header-echo row "
            f"{HEADER_ECHO_ROW} (production layout: the recipe declares its own "
            "column_headers, so the in-cell header line comes back as the first search row "
            "and the [1..-1] slice exists to drop it)"
        )
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(SHEET_HEADERS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} sheet row {idx} must carry exactly the 10 col_ headers; "
                f"got {sorted(row.keys()) if isinstance(row, dict) else row!r}"
            )
        for key, value in row.items():
            if not isinstance(value, str):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} sheet row {idx} {key!r} must be a string "
                    "(rendered-form pinning; USER_ENTERED re-renders what it parses)"
                )
    for idx, row in enumerate(rows[1:], start=1):
        # FLOAT columns: the upsert args carry the sheet STRING while the live
        # read-back is a float, and the strict snowflake args->final check
        # compares str() forms -- so every float cell must be the canonical
        # str(float) rendering (a mandatory exact-binary fraction like
        # .5/.25/.75; '35000' would read back as '35000.0' and mismatch).
        for key in ("col_fy_full_monthly_quota", "col_quota_amount"):
            cell = row[key]
            try:
                parsed = float(cell)
            except ValueError as exc:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} sheet row {idx} {key!r} must be a plain numeric "
                    f"string (it is upserted into a Snowflake FLOAT column): {cell!r}"
                ) from exc
            if str(parsed) != cell:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} sheet row {idx} {key!r} must be the canonical "
                    f"str(float) rendering incl. an exact-binary fraction (got {cell!r}, "
                    f"want {str(parsed)!r}); Snowflake FLOAT read-back would otherwise "
                    "diverge from the sheet string in the strict str() comparison"
                )
        # NUMBER(38,0) column: canonical int rendering.
        cell = row["col_month_of_quota_final"]
        if not cell.isdigit() or str(int(cell)) != cell:
            raise RuntimeError(
                f"recipe {RECIPE_ID} sheet row {idx} col_month_of_quota_final must be a "
                f"canonical non-negative int string (NUMBER(38,0) read-back): {cell!r}"
            )
    return {"headers": list(SHEET_HEADERS), "rows": deepcopy(rows)}


def _require_snowflake_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}}")
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [SNOWFLAKE_TABLE]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{SNOWFLAKE_TABLE!r} (2-part name; the bare TRUNCATE pill rewrites to it)"
        )
    spec = tables[SNOWFLAKE_TABLE]
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(f"recipe {RECIPE_ID} snowflake table spec must be {{'columns','rows'}}")
    if spec["columns"] != SNOWFLAKE_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} snowflake columns must be exactly {SNOWFLAKE_COLUMNS}"
        )
    rows = spec["rows"]
    if not isinstance(rows, list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} snowflake rows must be a list (stale rows prove the "
            "TRUNCATE; an empty list is a valid clean-table variant)"
        )
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(SNOWFLAKE_COLUMNS.keys()):
            raise RuntimeError(
                f"recipe {RECIPE_ID} snowflake stale row {idx} must fill every declared "
                f"column: {row!r}"
            )
        for column, kind in SNOWFLAKE_COLUMNS.items():
            value = row[column]
            if kind == "number" and (isinstance(value, bool) or not isinstance(value, int)):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} snowflake stale row {idx} {column} must be an int"
                )
            if kind == "float" and (isinstance(value, bool) or not isinstance(value, (int, float))):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} snowflake stale row {idx} {column} must be numeric"
                )
            if kind == "string" and not isinstance(value, str):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} snowflake stale row {idx} {column} must be a string"
                )


def _require_expect_shape(expect: Any) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if expect.get("executed_action_count") != 6:
        raise RuntimeError(
            f"recipe {RECIPE_ID} always executes exactly 6 actions (the only branch is the "
            f"documented-dead 50000-row stop): {expect.get('executed_action_count')!r}"
        )
    if expect.get("tools") != ALLOWED_TOOLS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools must be exactly {ALLOWED_TOOLS} (linear path): "
            f"{expect.get('tools')!r}"
        )
    if expect.get("stopped") is not False:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.stopped must be false (dead-branch proof): "
            f"{expect.get('stopped')!r}"
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
    merged: dict[str, Any] = {"google_sheets": ctx.tools.call("harness.google_sheets.snapshot", {})}
    for key, value in ctx.tools.call("harness.snowflake.snapshot", {}).items():
        if key != "ok":
            merged[key] = value
    return merged


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
