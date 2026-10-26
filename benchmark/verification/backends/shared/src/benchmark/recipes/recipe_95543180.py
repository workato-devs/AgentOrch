from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_95543180


RECIPE_ID = "95543180"
SEED_TYPE = "clock_sheets_to_snowflake_ga_weekly_traffic_variant"
TRACK = "live_snowflake_upsert"
TRIGGER_AS = "bee88ce4"
DECLARE_AS = "e0f225fa"
SHEETS_AS = "99ff93ec"
INSERT_AS = "952fcb9a"
UPSERT_AS = "5d679a2e"
SNOWFLAKE_TABLE = "GOOGLE.GOOGLE_ANALYTICS_WEEKLY_USER_TRAFFIC"
KEY_COLUMN = "ROW_NUMBER"

SHEET_HEADERS = [
    "col_Date",
    "col_End Date",
    "col_Week Number",
    "col_NORAM Organic",
    "col_NORAM Direct",
    "col_NORAM Referral",
]
HEADER_TO_FIELD = {
    "col_Date": "date",
    "col_End Date": "end_date",
    "col_Week Number": "week_number",
    "col_NORAM Organic": "noram_organic",
    "col_NORAM Direct": "noram_direct",
    "col_NORAM Referral": "noram_referral",
}
TABLE_COLUMNS = {
    "date": "string",
    "end_date": "string",
    "week_number": "string",
    "noram_organic": "string",
    "noram_direct": "string",
    "noram_referral": "string",
    "row_number": "number",
}
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_list",
    "google_sheets.get_spreadsheet_rows_v4",
    "workato_runtime.insert_to_list_batch",
    "snowflake.upsert_rows_batch",
]
ALLOWED_TOOLS: list[str] = [
    "google_sheets.get_spreadsheet_rows_v4",
    "snowflake.upsert_rows_batch",
]
EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "trace_tools",
    "list_items",
    "final_row_count",
)
MAX_ROWS = 20
_BARE_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_BARE_TIME_RE = re.compile(r"\d{1,2}:\d{2}(:\d{2})?")

_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "bee88ce4",
  "provider": "clock",
  "name": "scheduled_event",
  "skip": false,
  "input": {
   "time_unit": "days",
   "timezone": "Etc/UTC",
   "trigger_at": "22:00:00",
   "trigger_every": "1"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "e0f225fa",
  "provider": "workato_variable",
  "name": "declare_list",
  "skip": false,
  "input": {
   "list_item_schema_json": "[{\"name\":\"row_number\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"Row number\",\"parse_output\":\"integer_conversion\"},{\"name\":\"date\",\"type\":\"date_time\",\"optional\":false,\"control_type\":\"date\",\"label\":\"Date\",\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\"},{\"name\":\"end_date\",\"type\":\"date_time\",\"optional\":false,\"control_type\":\"date\",\"label\":\"End date\",\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\"},{\"name\":\"week_number\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"Week number\",\"parse_output\":\"integer_conversion\"},{\"name\":\"noram_organic\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"Noram organic\",\"parse_output\":\"integer_conversion\"},{\"name\":\"noram_direct\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"Noram direct\",\"parse_output\":\"integer_conversion\"},{\"name\":\"noram_referral\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"Noram referral\",\"parse_output\":\"integer_conversion\"}]",
   "name": "Google Analytics Weekly Cost Metrics"
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "99ff93ec",
  "provider": "google_sheets",
  "name": "get_spreadsheet_rows_v4",
  "skip": false,
  "input": {
   "sheet": "Google Analytics Weekly Cost Metrics",
   "spreadsheet": "1wYWbTgevbFHZKgU4w-LT0D0rnXHe4zghtewQBYwlu5c",
   "team_drives": "0AFQ6xjaIkjNcUk9PVA/0AFQ6xjaIkjNcUk9PVA"
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "952fcb9a",
  "provider": "workato_variable",
  "name": "insert_to_list_batch",
  "skip": false,
  "input": {
   "list_items": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"99ff93ec\",\"path\":[\"rows\"]}')}",
    "date": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"99ff93ec\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_Date\"]}')}",
    "end_date": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"99ff93ec\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_End Date\"]}')}",
    "noram_direct": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"99ff93ec\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_NORAM Direct\"]}')}",
    "noram_organic": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"99ff93ec\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_NORAM Organic\"]}')}",
    "noram_referral": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"99ff93ec\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_NORAM Referral\"]}')}",
    "row_number": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"99ff93ec\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"row_number\"]}')}",
    "week_number": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"99ff93ec\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_Week Number\"]}')}"
   },
   "location": "end",
   "name": "45cfe61a-37d5-4526-8b3f-6c1c5c207f74:e0f225fa"
  }
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "5d679a2e",
  "provider": "snowflake",
  "name": "upsert_rows_batch",
  "skip": false,
  "input": {
   "key_columns": "ROW_NUMBER",
   "rows": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"99ff93ec\",\"path\":[\"rows\"]}')}",
    "date": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"99ff93ec\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_Date\"]}')}",
    "end_date": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"99ff93ec\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_End Date\"]}')}",
    "noram_direct": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"99ff93ec\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_NORAM Direct\"]}')}",
    "noram_organic": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"99ff93ec\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_NORAM Organic\"]}')}",
    "noram_referral": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"99ff93ec\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_NORAM Referral\"]}')}",
    "row_number": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"99ff93ec\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"row_number\"]}')}",
    "week_number": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"99ff93ec\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"col_Week Number\"]}')}"
   },
   "table": "GOOGLE.GOOGLE_ANALYTICS_WEEKLY_USER_TRAFFIC"
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)


def _structure(node: dict[str, Any]) -> list[dict[str, Any]]:
    pin: dict[str, Any] = {
        "keyword": node.get("keyword"),
        "number": node.get("number"),
        "as": node.get("as"),
        "provider": node.get("provider"),
        "name": node.get("name"),
        "skip": bool(node.get("skip")),
        "input": node.get("input") or {},
    }
    if node.get("keyword") == "foreach":
        pin["repeat_mode"] = node.get("repeat_mode")
        pin["batch_size"] = node.get("batch_size")
        pin["source"] = node.get("source")
    if isinstance(node.get("filter"), dict):
        pin["filter"] = node["filter"]
    out = [pin]
    for child in node.get("block") or []:
        if isinstance(child, dict):
            out.extend(_structure(child))
    return out


def validate_95543180(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger 'as' changed: {raw.get('as')!r}")
    actual = _structure(raw)
    if len(actual) != len(STRUCTURE_PINS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} node count changed: {len(actual)} != {len(STRUCTURE_PINS)}"
        )
    for idx, (got, expected) in enumerate(zip(actual, STRUCTURE_PINS)):
        if got != expected:
            raise RuntimeError(
                f"recipe {RECIPE_ID} node {idx} (step {expected.get('number')}) changed:\n"
                f"expected: {json.dumps(expected, sort_keys=True)}\n"
                f"actual:   {json.dumps(got, sort_keys=True)}"
            )
    actions = [pin for pin in actual if pin["keyword"] == "action"]
    return {
        "trigger_provider": "clock",
        "trigger_name": "scheduled_event",
        "snowflake_table": SNOWFLAKE_TABLE,
        "actions": [
            {
                "number": pin["number"],
                "provider": pin["provider"],
                "name": pin["name"],
                "as": pin["as"],
            }
            for pin in actions
        ],
    }


def _require_cell(row_idx: int, header: str, value: Any) -> str:
    if not isinstance(value, str):
        raise RuntimeError(
            f"recipe {RECIPE_ID} sheet row {row_idx} {header!r} must be a string "
            "(live cells round-trip as rendered strings)"
        )
    if _BARE_DATE_RE.fullmatch(value) or _BARE_TIME_RE.fullmatch(value):
        raise RuntimeError(
            f"recipe {RECIPE_ID} sheet row {row_idx} {header!r} is a bare date/time "
            f"({value!r}) — USER_ENTERED re-renders those; suffix the value like the "
            "91495261 precedent"
        )
    return value


def _require_sheets_seed(section: Any) -> list[dict[str, str]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["headers", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets must be exactly {{'headers': ..., 'rows': ...}}"
        )
    if section["headers"] != SHEET_HEADERS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} sheet headers must be the col_-LITERAL schema names "
            f"(spaces included) {SHEET_HEADERS!r}; get_spreadsheet_rows_v4 has no col_ "
            f"aliasing: {section['headers']!r}"
        )
    rows = section["rows"]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} seed.sheets.rows must be a list")
    if len(rows) > MAX_ROWS:
        raise RuntimeError(f"recipe {RECIPE_ID} at most {MAX_ROWS} sheet rows")
    out: list[dict[str, str]] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(SHEET_HEADERS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} sheet row {idx} must fill exactly the headers "
                f"{sorted(SHEET_HEADERS)}; got {sorted(row) if isinstance(row, dict) else row!r}"
            )
        out.append({header: _require_cell(idx, header, row[header]) for header in SHEET_HEADERS})
    return out


def _require_snowflake_seed(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}}"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [SNOWFLAKE_TABLE]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} snowflake_live.tables must declare exactly "
            f"{SNOWFLAKE_TABLE!r} (the recipe's literal 2-part name)"
        )
    spec = tables[SNOWFLAKE_TABLE]
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table spec must be exactly {{'columns': ..., 'rows': ...}}"
        )
    if spec["columns"] != TABLE_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table must declare exactly the columns {TABLE_COLUMNS!r} "
            "(string-typed per the 91495261 precedent; row_number number)"
        )
    pre_rows = spec["rows"]
    if not isinstance(pre_rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table rows must be a list")
    seen: set[int] = set()
    for idx, row in enumerate(pre_rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(TABLE_COLUMNS.keys()):
            raise RuntimeError(
                f"recipe {RECIPE_ID} pre-seeded table row {idx} must fill exactly "
                f"{sorted(TABLE_COLUMNS.keys())}"
            )
        if isinstance(row["row_number"], bool) or not isinstance(row["row_number"], int):
            raise RuntimeError(
                f"recipe {RECIPE_ID} pre-seeded row {idx} row_number must be an integer "
                "(the ROW_NUMBER upsert key; live sheet rows carry ints)"
            )
        if row["row_number"] in seen:
            raise RuntimeError(f"recipe {RECIPE_ID} pre-seeded ROW_NUMBER values must be distinct")
        seen.add(row["row_number"])
    return pre_rows


def _derived_list_items(sheet_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(sheet_rows):
        item: dict[str, Any] = {HEADER_TO_FIELD[h]: row[h] for h in SHEET_HEADERS}
        # Live snapshot numbering: header row is 1, first data row is 2.
        item["row_number"] = idx + 2
        out.append(item)
    return out


def _require_expect(
    expect: Any,
    list_items: list[dict[str, Any]],
    pre_rows: list[dict[str, Any]],
) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    upserted_numbers = {item["row_number"] for item in list_items}
    pre_numbers = {row["row_number"] for row in pre_rows}
    updated = len(upserted_numbers & pre_numbers)
    created = len(upserted_numbers - pre_numbers)
    final_row_count = len(pre_numbers | upserted_numbers)
    checks = (
        expect.get("executed_action_count") == 4,
        expect.get("trace_tools") == EXPECTED_RAW_TOOLS,
        expect.get("tools") == ALLOWED_TOOLS,
        expect.get("list_items") == list_items,
        expect.get("final_row_count") == final_row_count,
        expect.get("tool_expectations")
        == [
            {
                "tool": "google_sheets.get_spreadsheet_rows_v4",
                "result_count": len(list_items),
            },
            {
                "tool": "snowflake.upsert_rows_batch",
                "table": SNOWFLAKE_TABLE,
                "created_count": created,
                "updated_count": updated,
                "rows": list_items,
                "args_contains": {
                    "table": SNOWFLAKE_TABLE,
                    "key_columns": KEY_COLUMN,
                    "rows": list_items,
                },
            },
        ],
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with the derived ground "
            f"truth (list_items {list_items!r}, created {created}, updated {updated}, "
            f"final_row_count {final_row_count}): {expect!r}"
        )


def seed_95543180(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_95543180(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (payload-less "
            f"scheduled_event): {trigger!r}"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["sheets", "snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must carry exactly the sheets and snowflake_live "
            f"sections; got {sorted(seed_in.keys()) if isinstance(seed_in, dict) else seed_in!r}"
        )
    sheet_rows = _require_sheets_seed(seed_in["sheets"])
    pre_rows = _require_snowflake_seed(seed_in["snowflake_live"])
    _require_expect(data.get("expect"), _derived_list_items(sheet_rows), pre_rows)
    sheets_response = ctx.tools.call("harness.google_sheets.seed_rows", {"sheets": seed_in["sheets"]})
    if not sheets_response.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Google Sheets seed failed: {sheets_response}")
    provision = ctx.tools.call(
        "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": deepcopy(data["expect"]),
        "sheets": deepcopy(seed_in["sheets"]),
        "sheets_seed_response": sheets_response,
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_95543180(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_95543180(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not ctx.env.sheets_spreadsheet_id or not ctx.env.sheets_tab:
        raise RuntimeError("missing SHEETS_SPREADSHEET_ID or SHEETS_TAB for live Google Sheets read")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
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
        # Required cleanup: the GA weekly-traffic table is benchmark-owned
        # create-or-replace state — drop it whether or not the run completed.
        # The sheets tab needs no cleanup (every seed fully overwrites it).
        snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    details["cleanup_response"] = {"snowflake_live": snowflake_cleanup}
    if not (snowflake_cleanup or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake cleanup failed: {snowflake_cleanup}")
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
    result["verifier"] = verify_95543180(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    out: dict[str, Any] = {"google_sheets": ctx.tools.call("harness.google_sheets.snapshot", {})}
    out.update(ctx.tools.call("harness.snowflake.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
