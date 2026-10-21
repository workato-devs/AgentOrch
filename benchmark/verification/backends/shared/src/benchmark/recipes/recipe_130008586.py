from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_130008586


RECIPE_ID = "130008586"
SEED_TYPE = "snowflake_hr_laptop_catalog_lookup_refresh_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "a2fa32db"
SEARCH_STEP_AS = "476a4fe9"
TRUNCATE_STEP_AS = "a6359a29"
BATCH_STEP_AS = "55db3318"
CATALOG_TABLE = "ITAM.HR_LAPTOP_CATALOG"
LOOKUP_TABLE_ID = "4473690"
# The connector's Order-by field carries a boolean EXPRESSION as its 4th term
# (batch-08 engine fix: snowflake_live._order_by passes parenthesized
# expression terms through verbatim; identifiers are still quoted). Live
# Snowflake orders false < true ASC, so 'All'-location rows sort BEFORE
# specific locations among numeric ties.
ORDERBY = "display_inch asc, ram_gb asc, storage_gb asc, (office_location_id != 'All') asc"
# Full live column set (verbatim from the node's extended_output_schema; the
# read is SELECT * so every column must exist).
CATALOG_COLUMNS = {
    "display_inch": "float",
    "id": "string",
    "keyboard_layout": "string",
    "manufacturer": "string",
    "name": "string",
    "object_key": "string",
    "office_location_id": "string",
    "office_location_name": "string",
    "ram_gb": "integer",
    "slack_emoji": "string",
    "storage_gb": "integer",
    "type": "string",
}
# add_batch entry mapping (verbatim ____source parameters, current_item):
COL_TO_SOURCE = {
    "col1": "id",
    "col2": "name",
    "col3": "office_location_id",
    "col4": "slack_emoji",
}

# clock.scheduled_event (as a2fa32db, daily 06:00) -- payload-less; NO trigger
# field is ever dereferenced (trigger_input must be exactly {}).
#   2  snowflake.search_rows 476a4fe9 (LIVE): table ITAM.HR_LAPTOP_CATALOG
#      (2-part -> BENCH_DB.ITAM.HR_LAPTOP_CATALOG), limit 100 offset 0 (offset
#      0 is dropped by the connector), orderby carries the boolean-expression
#      4th term -- the composed SQL is exactly
#      select * from "BENCH_DB"."ITAM"."HR_LAPTOP_CATALOG" order by
#      "DISPLAY_INCH" ASC, "RAM_GB" ASC, "STORAGE_GB" ASC,
#      (office_location_id != 'All') ASC limit 100   (re-probed on HEAD).
#      ORDER BY on the top-level query IS a live row-order guarantee, so this
#      recipe pins batch entries and the final lookup table as ORDERED lists
#      (unlike the no-ORDER-BY multiset siblings 119144543/105192491); the
#      seeder requires the 4-term sort key to be UNIQUE per row.
#   3  lookup_table.truncate a6359a29 table 4473690 (mock, Workato-internal):
#      always runs -- proven by pre-seeded stale rows (deleted_rows pin).
#   4  lookup_table.add_batch_of_entries 55db3318: ____source over
#      476a4fe9.rows -> col1=id, col2=name, col3=office_location_id,
#      col4=slack_emoji. Empty rows -> faithful no-op add (added_count 0).
# IN-BATCH sibling of 119144543 (same truncate+add_batch tail; delta is the
# read step: search_rows+orderby here vs run_custom_sql JOIN there).
# Snowflake is READ-ONLY here: live snapshot equality before/after; cleanup
# drops exactly the one seeded table. The lookup table is a per-variant mock.

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "clock", "name": "scheduled_event", "as": "a2fa32db", "skip": false, "input": {"time_unit": "days", "trigger_at": "06:00:00.000", "trigger_every": "1"}, "block": [{"number": 2, "keyword": "action", "provider": "snowflake", "name": "search_rows", "as": "476a4fe9", "skip": false, "input": {"limit": "100", "offset": "0", "orderby": "display_inch asc, ram_gb asc, storage_gb asc, (office_location_id != 'All') asc", "table": "ITAM.HR_LAPTOP_CATALOG"}, "block": []}, {"number": 3, "keyword": "action", "provider": "lookup_table", "name": "truncate", "as": "a6359a29", "skip": false, "input": {"lookup_table_id": "4473690"}, "block": []}, {"number": 4, "keyword": "action", "provider": "lookup_table", "name": "add_batch_of_entries", "as": "55db3318", "skip": false, "input": {"entries": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"476a4fe9\",\"path\":[\"rows\"]}')}", "parameters": {"col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"476a4fe9\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}", "col2": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"476a4fe9\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"name\"]}')}", "col3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"476a4fe9\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"office_location_id\"]}')}", "col4": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"476a4fe9\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"slack_emoji\"]}')}"}}, "lookup_table_id": "4473690"}, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (SEARCH_STEP_AS, "snowflake", "search_rows"),
    (TRUNCATE_STEP_AS, "lookup_table", "truncate"),
    (BATCH_STEP_AS, "lookup_table", "add_batch_of_entries"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows",
    "lookup_table.truncate",
    "lookup_table.add_batch_of_entries",
]
ALLOWED_TOOLS: list[str] = list(EXPECTED_RAW_TOOLS)
BRANCHES = ("zero_rows", "ordered_rows")
REQUIRED_EXPECT_KEYS = (
    "branch",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "sql_row_count",
    "ordered_sql_ids",
    "batch_entries_ordered",
    "truncate_deleted_rows",
    "final_row_count",
    "final_lookup_rows_ordered",
)
_EXPECTATION_TARGET_KEYS = {"tool", "table_id", "lookup_table_id", "match_fields", "channel"}
_EXPECTATION_VALUE_KEYS = {
    "args_contains",
    "result_count",
    "response_contains",
    "result_contains",
    "created",
    "http_status_code",
    "text_fragments",
    "options_contains",
}
_LOOKUP_COL_RE = re.compile(r"^col[1-4]$")


def validate_130008586(raw: dict[str, Any]) -> dict[str, Any]:
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
    nodes = {str(node.get("as") or ""): node for node in _walk_nodes(raw)}
    search_input = (nodes.get(SEARCH_STEP_AS) or {}).get("input") or {}
    if str(search_input.get("table") or "") != CATALOG_TABLE:
        raise RuntimeError(f"recipe {RECIPE_ID} search_rows table changed")
    if str(search_input.get("orderby") or "") != ORDERBY:
        raise RuntimeError(
            f"recipe {RECIPE_ID} orderby changed -- the expression-term ordering "
            f"analysis no longer holds: {search_input.get('orderby')!r}"
        )
    if str(search_input.get("limit") or "") != "100" or str(search_input.get("offset") or "") != "0":
        raise RuntimeError(f"recipe {RECIPE_ID} search_rows limit/offset changed")
    if "where" in search_input or "output_columns" in search_input:
        raise RuntimeError(f"recipe {RECIPE_ID} search_rows grew a where/output_columns input")
    for step_as in (TRUNCATE_STEP_AS, BATCH_STEP_AS):
        table = str(((nodes.get(step_as) or {}).get("input") or {}).get("lookup_table_id") or "")
        if table != LOOKUP_TABLE_ID:
            raise RuntimeError(
                f"recipe {RECIPE_ID} lookup step {step_as} targets table {table!r}, "
                f"expected {LOOKUP_TABLE_ID!r}"
            )
    batch_input = (nodes.get(BATCH_STEP_AS) or {}).get("input") or {}
    parameters = ((batch_input.get("entries") or {}).get("parameters")) or {}
    for col, source in COL_TO_SOURCE.items():
        pill = str(parameters.get(col) or "")
        if f'"{source}"' not in pill or SEARCH_STEP_AS not in pill:
            raise RuntimeError(
                f"recipe {RECIPE_ID} add_batch {col} no longer maps current_item "
                f"{source!r}: {pill!r}"
            )
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "catalog_table": CATALOG_TABLE,
        "lookup_table_id": LOOKUP_TABLE_ID,
        "orderby": ORDERBY,
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


def seed_130008586(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130008586(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (payload-less scheduler "
            f"tick; no trigger field is ever dereferenced): {trigger!r}"
        )
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: a forced action error would fail the whole "
            "run instead of exercising a recipe branch"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["lookup_table", "snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the lookup_table and "
            f"snowflake_live sections; got {sorted(seed_in.keys())}"
        )
    preseeded_lookup_rows = _require_lookup_section(seed_in["lookup_table"])
    catalog_rows = _require_snowflake_section(seed_in["snowflake_live"])
    ordered = _ordered_rows(catalog_rows)
    _require_expect_shape(data.get("expect"), ordered, preseeded_lookup_rows)
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
        "lookup_table": deepcopy(seed_in["lookup_table"]),
        "expect": deepcopy(data["expect"]),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_130008586(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130008586(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    if seed.get("trigger") != {}:
        raise RuntimeError(f"recipe {RECIPE_ID} seed trigger must be the explicit payload-less {{}}")
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
        # The seeded catalog table is benchmark-owned live state: drop it even
        # when execution fails. The lookup table is a per-variant isolated mock.
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
    result["verifier"] = verify_130008586(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_lookup_section(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table must be exactly {{'tables': ...}}"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [LOOKUP_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must declare exactly table "
            f"{LOOKUP_TABLE_ID!r} (rows may be an explicit empty list)"
        )
    rows = tables[LOOKUP_TABLE_ID]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {LOOKUP_TABLE_ID} rows must be a list")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or not row:
            raise RuntimeError(
                f"recipe {RECIPE_ID} pre-seeded lookup row {idx} must be a non-empty object"
            )
        for key, value in row.items():
            if not _LOOKUP_COL_RE.fullmatch(str(key)):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} pre-seeded lookup row {idx} has non-col1..col4 key {key!r}"
                )
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} pre-seeded lookup row {idx}.{key} must be a "
                    f"non-empty string; got {value!r}"
                )
    return [dict(row) for row in rows]


def _require_snowflake_section(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(no time functions anywhere -> current_time must NOT be declared)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [CATALOG_TABLE]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{CATALOG_TABLE!r} (the LITERAL 2-part name the node reads)"
        )
    spec = tables[CATALOG_TABLE]
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} snowflake table spec must be exactly {{'columns': ..., 'rows': ...}}"
        )
    if spec["columns"] != CATALOG_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} catalog columns must be exactly {CATALOG_COLUMNS}"
        )
    rows = spec["rows"]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} catalog rows must be a list")
    seen_keys: set[tuple[Any, ...]] = set()
    seen_ids: set[str] = set()
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(CATALOG_COLUMNS.keys()):
            raise RuntimeError(
                f"recipe {RECIPE_ID} catalog row {idx} must fill exactly the declared "
                f"columns: {row!r}"
            )
        for column, kind in CATALOG_COLUMNS.items():
            value = row[column]
            if kind == "float":
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} catalog row {idx}.{column} must be numeric; got {value!r}"
                    )
            elif kind == "integer":
                if not isinstance(value, int) or isinstance(value, bool):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} catalog row {idx}.{column} must be an int; got {value!r}"
                    )
            else:
                if not isinstance(value, str) or not value.strip():
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} catalog row {idx}.{column} must be a "
                        f"non-empty string; got {value!r}"
                    )
        key = _sort_key(row)
        if key in seen_keys:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catalog row {idx} duplicates the 4-term ORDER BY sort "
                f"key {key!r} -- live row order would be non-deterministic; make "
                "(display_inch, ram_gb, storage_gb, office_location_id!='All') unique per row"
            )
        seen_keys.add(key)
        if str(row["id"]) in seen_ids:
            raise RuntimeError(f"recipe {RECIPE_ID} catalog row {idx} duplicates id {row['id']!r}")
        seen_ids.add(str(row["id"]))
    return [dict(row) for row in rows]


def _sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
    """The live 4-term ORDER BY key: three ascending numerics plus the boolean
    expression (office_location_id != 'All') -- FALSE ('All') sorts first ASC,
    matching Snowflake boolean ordering."""
    return (
        float(row["display_inch"]),
        int(row["ram_gb"]),
        int(row["storage_gb"]),
        str(row["office_location_id"]) != "All",
    )


def _ordered_rows(catalog_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(catalog_rows, key=_sort_key)


def _entry_for(row: dict[str, Any]) -> dict[str, str]:
    return {col: str(row[source]) for col, source in COL_TO_SOURCE.items()}


def _require_expect_shape(
    expect: Any,
    ordered: list[dict[str, Any]],
    preseeded_lookup_rows: list[dict[str, Any]],
) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    branch = expect.get("branch")
    if branch not in BRANCHES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch must be one of {BRANCHES}")
    derived_branch = "zero_rows" if not ordered else "ordered_rows"
    if branch != derived_branch:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.branch {branch!r} contradicts the seeded catalog "
            f"(derived {derived_branch!r}: {len(ordered)} rows)"
        )
    if branch == "zero_rows" and not preseeded_lookup_rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the zero_rows variant must pre-seed at least one stale "
            "lookup row -- otherwise truncate is unobservable"
        )
    expected_entries = [_entry_for(row) for row in ordered]
    checks = (
        expect.get("executed_action_count") == 3,
        expect.get("tools") == EXPECTED_RAW_TOOLS,
        expect.get("sql_row_count") == len(ordered),
        expect.get("ordered_sql_ids") == [str(row["id"]) for row in ordered],
        expect.get("batch_entries_ordered") == expected_entries,
        expect.get("truncate_deleted_rows") == len(preseeded_lookup_rows),
        expect.get("final_row_count") == len(ordered),
        expect.get("final_lookup_rows_ordered") == expected_entries,
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with the seeded ground truth "
            f"(branch {branch!r}, {len(ordered)} ordered rows): {expect!r}"
        )
    _require_tool_expectations(expect, len(ordered))


def _require_tool_expectations(expect: dict[str, Any], row_count: int) -> None:
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or len(items) != 3:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin all 3 executed calls"
        )
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[{idx}] must be an object")
        unknown = sorted(set(item) - _EXPECTATION_TARGET_KEYS - _EXPECTATION_VALUE_KEYS)
        if unknown:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] has non-corpus keys: {unknown}"
            )
        if not any(key in item for key in _EXPECTATION_VALUE_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] pins no ground-truth value"
            )
        if item.get("tool") != EXPECTED_RAW_TOOLS[idx]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}].tool must be "
                f"{EXPECTED_RAW_TOOLS[idx]!r}; got {item.get('tool')!r}"
            )
    search_item, truncate_item, batch_item = items
    checks = (
        search_item.get("args_contains")
        == {
            "table": CATALOG_TABLE,
            "where": "",
            "parameters": {},
            "limit": "100",
            "offset": "0",
            "orderby": ORDERBY,
        },
        search_item.get("result_count") == row_count,
        truncate_item.get("lookup_table_id") == LOOKUP_TABLE_ID,
        truncate_item.get("args_contains") == {"lookup_table_id": LOOKUP_TABLE_ID},
        batch_item.get("lookup_table_id") == LOOKUP_TABLE_ID,
        batch_item.get("args_contains") == {"lookup_table_id": LOOKUP_TABLE_ID},
        batch_item.get("result_count") == row_count,
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations do not pin the derived ground truth: {items!r}"
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
    out: dict[str, Any] = {}
    out.update(ctx.tools.call("harness.lookup_table.snapshot", {}))
    out.update(ctx.tools.call("harness.snowflake.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
