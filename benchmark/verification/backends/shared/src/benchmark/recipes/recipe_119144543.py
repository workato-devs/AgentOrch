from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_119144543


RECIPE_ID = "119144543"
SEED_TYPE = "snowflake_adapters_join_lookup_refresh_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "e809962b"
SQL_STEP_AS = "ec7952c8"
TRUNCATE_STEP_AS = "0e4cf73e"
BATCH_STEP_AS = "4bfb1cef"
MAPPING_TABLE = "EDW_DB.WORKATO_USAGE.ADAPTERS_MAPPING"
ADAPTERS_TABLE = "EDW_DB.WORKATO_USAGE.ADAPTERS"
LOOKUP_TABLE_ID = "2257706"
RAW_SQL = (
    "SELECT\n"
    "AM.DATA_CENTER AS DATA_CENTER_ALPHA2CODE,\n"
    "AM.ADAPTER_ID,\n"
    "AM.DISPLAY_NAME,\n"
    "AM.CATEGORY,\n"
    "A.NAME AS KEY\n"
    "\n"
    "FROM EDW_DB.WORKATO_USAGE.ADAPTERS_MAPPING AM\n"
    "JOIN EDW_DB.WORKATO_USAGE.ADAPTERS A\n"
    "ON AM.ADAPTER_ID = A.ID\n"
    "AND AM.DATA_CENTER = A.DATA_CENTER"
)
MAPPING_COLUMNS = {
    "data_center": "string",
    "adapter_id": "string",
    "display_name": "string",
    "category": "string",
}
ADAPTERS_COLUMNS = {
    "id": "string",
    "data_center": "string",
    "name": "string",
}
COL_TO_ALIAS = {
    "col1": "data_center_alpha2code",
    "col2": "adapter_id",
    "col3": "display_name",
    "col4": "category",
    "col5": "key",
}


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "clock", "name": "scheduled_event", "as": "e809962b", "skip": false, "input": {"time_unit": "days", "timezone": "<anon>Asia/Tokyo</anon>", "trigger_at": "<anon>12:00:00</anon>", "trigger_every": "1"}, "block": [{"number": 2, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql", "as": "ec7952c8", "skip": false, "input": {"output_schema": "[{\"name\":\"data_center_alpha2code\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"adapter_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"display_name\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"category\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"key\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"}]", "sql": "SELECT\nAM.DATA_CENTER AS DATA_CENTER_ALPHA2CODE,\nAM.ADAPTER_ID,\nAM.DISPLAY_NAME,\nAM.CATEGORY,\nA.NAME AS KEY\n\nFROM EDW_DB.WORKATO_USAGE.ADAPTERS_MAPPING AM\nJOIN EDW_DB.WORKATO_USAGE.ADAPTERS A\nON AM.ADAPTER_ID = A.ID\nAND AM.DATA_CENTER = A.DATA_CENTER", "update_only": "false"}, "block": []}, {"number": 3, "keyword": "action", "provider": "lookup_table", "name": "truncate", "as": "0e4cf73e", "skip": false, "input": {"lookup_table_id": "2257706"}, "block": []}, {"number": 4, "keyword": "action", "provider": "lookup_table", "name": "add_batch_of_entries", "as": "4bfb1cef", "skip": false, "input": {"entries": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"ec7952c8\",\"path\":[\"rows\"]}')}", "parameters": {"col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"ec7952c8\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"data_center_alpha2code\"]}')}", "col2": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"ec7952c8\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"adapter_id\"]}')}", "col3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"ec7952c8\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"display_name\"]}')}", "col4": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"ec7952c8\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"category\"]}')}", "col5": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"ec7952c8\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"key\"]}')}"}}, "lookup_table_id": "2257706"}, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (SQL_STEP_AS, "snowflake", "run_custom_sql"),
    (TRUNCATE_STEP_AS, "lookup_table", "truncate"),
    (BATCH_STEP_AS, "lookup_table", "add_batch_of_entries"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "lookup_table.truncate",
    "lookup_table.add_batch_of_entries",
]
ALLOWED_TOOLS: list[str] = list(EXPECTED_RAW_TOOLS)
BRANCHES = ("zero_rows", "joined_rows")
REQUIRED_EXPECT_KEYS = (
    "branch",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "sql_row_count",
    "sql_rows",
    "batch_entries",
    "truncate_deleted_rows",
    "final_row_count",
    "final_lookup_rows",
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
_LOOKUP_COL_RE = re.compile(r"^col[1-5]$")


def validate_119144543(raw: dict[str, Any]) -> dict[str, Any]:
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
    sql_node = nodes.get(SQL_STEP_AS) or {}
    if str((sql_node.get("input") or {}).get("sql") or "") != RAW_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} custom SQL changed")
    if RAW_SQL.count(MAPPING_TABLE) != 1 or RAW_SQL.count(ADAPTERS_TABLE) != 2:
        # ADAPTERS appears once standalone and once as the ADAPTERS_MAPPING prefix.
        raise RuntimeError(
            f"recipe {RECIPE_ID} expected the two 3-part table names exactly once each "
            "in FROM/JOIN position"
        )
    for step_as in (TRUNCATE_STEP_AS, BATCH_STEP_AS):
        table = str(((nodes.get(step_as) or {}).get("input") or {}).get("lookup_table_id") or "")
        if table != LOOKUP_TABLE_ID:
            raise RuntimeError(
                f"recipe {RECIPE_ID} lookup step {step_as} targets table {table!r}, "
                f"expected {LOOKUP_TABLE_ID!r}"
            )
    batch_input = (nodes.get(BATCH_STEP_AS) or {}).get("input") or {}
    parameters = ((batch_input.get("entries") or {}).get("parameters")) or {}
    for col, alias in COL_TO_ALIAS.items():
        pill = str(parameters.get(col) or "")
        if f'"{alias}"' not in pill or SQL_STEP_AS not in pill:
            raise RuntimeError(
                f"recipe {RECIPE_ID} add_batch {col} no longer maps current_item "
                f"{alias!r}: {pill!r}"
            )
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "mapping_table": MAPPING_TABLE,
        "adapters_table": ADAPTERS_TABLE,
        "lookup_table_id": LOOKUP_TABLE_ID,
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


def seed_119144543(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_119144543(raw)
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
    mapping_rows, adapter_rows = _require_snowflake_section(seed_in["snowflake_live"])
    joined = _joined_rows(mapping_rows, adapter_rows)
    _require_expect_shape(data.get("expect"), joined, preseeded_lookup_rows)
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


def run_119144543(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_119144543(raw)
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
        # The two seeded 3-part tables are benchmark-owned live state: drop
        # them even when execution fails. The lookup table is a per-variant
        # isolated mock -- no live cleanup exists for it.
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
    result["verifier"] = verify_119144543(result)
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
                    f"recipe {RECIPE_ID} pre-seeded lookup row {idx} has non-col1..col5 key {key!r}"
                )
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} pre-seeded lookup row {idx}.{key} must be a "
                    f"non-empty string; got {value!r}"
                )
    return [dict(row) for row in rows]


def _require_snowflake_section(section: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the SQL has no CURRENT_* -> current_time must NOT be declared)"
        )
    tables = section["tables"]
    expected = sorted([MAPPING_TABLE, ADAPTERS_TABLE])
    if not isinstance(tables, dict) or sorted(tables.keys()) != expected:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{expected} (the LITERAL 3-part names both SQL refs use)"
        )
    mapping_rows = _require_table_rows(tables[MAPPING_TABLE], MAPPING_COLUMNS, MAPPING_TABLE)
    adapter_rows = _require_table_rows(tables[ADAPTERS_TABLE], ADAPTERS_COLUMNS, ADAPTERS_TABLE)
    seen = set()
    for idx, row in enumerate(adapter_rows):
        key = (row["id"], row["data_center"])
        if key in seen:
            raise RuntimeError(
                f"recipe {RECIPE_ID} adapters row {idx} duplicates the composite join key "
                f"{key!r} -- the join would fan out non-deterministically"
            )
        seen.add(key)
    return mapping_rows, adapter_rows


def _require_table_rows(
    spec: Any, columns: dict[str, str], table: str
) -> list[dict[str, Any]]:
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} {table} spec must be exactly {{'columns': ..., 'rows': ...}}"
        )
    if spec["columns"] != columns:
        raise RuntimeError(f"recipe {RECIPE_ID} {table} columns must be exactly {columns}")
    rows = spec["rows"]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} {table} rows must be a list")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(columns.keys()):
            raise RuntimeError(
                f"recipe {RECIPE_ID} {table} row {idx} must fill exactly the declared "
                f"columns: {row!r}"
            )
        for column in columns:
            value = row[column]
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {table} row {idx}.{column} must be a non-empty "
                    f"string; got {value!r}"
                )
    return [dict(row) for row in rows]


def _joined_rows(
    mapping_rows: list[dict[str, Any]], adapter_rows: list[dict[str, Any]]
) -> list[dict[str, str]]:
    """The rows the live JOIN must return, as lowercase-alias dicts. Composite
    ON clause: AM.ADAPTER_ID = A.ID AND AM.DATA_CENTER = A.DATA_CENTER.
    Order-insensitive (no ORDER BY)."""
    out: list[dict[str, str]] = []
    for mapping in mapping_rows:
        for adapter in adapter_rows:
            if (
                str(mapping["adapter_id"]) == str(adapter["id"])
                and str(mapping["data_center"]) == str(adapter["data_center"])
            ):
                out.append(
                    {
                        "data_center_alpha2code": str(mapping["data_center"]),
                        "adapter_id": str(mapping["adapter_id"]),
                        "display_name": str(mapping["display_name"]),
                        "category": str(mapping["category"]),
                        "key": str(adapter["name"]),
                    }
                )
    return out


def _entry_for(joined_row: dict[str, str]) -> dict[str, str]:
    return {col: joined_row[alias] for col, alias in COL_TO_ALIAS.items()}


def _same_multiset(actual: Any, expected: list[dict[str, Any]]) -> bool:
    if not isinstance(actual, list) or len(actual) != len(expected):
        return False
    key = lambda entry: json.dumps(entry, sort_keys=True, default=str)
    actual_sorted = sorted((entry for entry in actual if isinstance(entry, dict)), key=key)
    expected_sorted = sorted(expected, key=key)
    return actual_sorted == expected_sorted


def _require_expect_shape(
    expect: Any,
    joined: list[dict[str, str]],
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
    derived_branch = "zero_rows" if not joined else "joined_rows"
    if branch != derived_branch:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.branch {branch!r} contradicts the seeded tables "
            f"(derived {derived_branch!r}: {len(joined)} joined rows)"
        )
    if branch == "zero_rows" and not preseeded_lookup_rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the zero_rows variant must pre-seed at least one stale "
            "lookup row -- otherwise truncate is unobservable"
        )
    projected = [json.dumps(row, sort_keys=True) for row in joined]
    if len(set(projected)) != len(projected):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the joined 5-column projections must be pairwise "
            "distinct (multiset groundtruth matching would be ambiguous)"
        )
    expected_entries = [_entry_for(row) for row in joined]
    checks = (
        expect.get("executed_action_count") == 3,
        expect.get("tools") == EXPECTED_RAW_TOOLS,
        expect.get("sql_row_count") == len(joined),
        _same_multiset(expect.get("sql_rows"), joined),
        _same_multiset(expect.get("batch_entries"), expected_entries),
        expect.get("truncate_deleted_rows") == len(preseeded_lookup_rows),
        expect.get("final_row_count") == len(joined),
        _same_multiset(expect.get("final_lookup_rows"), expected_entries),
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with the seeded ground truth "
            f"(branch {branch!r}, {len(joined)} joined rows): {expect!r}"
        )
    _require_tool_expectations(expect, len(joined))


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
    sql_item, truncate_item, batch_item = items
    checks = (
        sql_item.get("args_contains") == {"sql": RAW_SQL, "parameters": {}},
        sql_item.get("result_count") == row_count,
        truncate_item.get("lookup_table_id") == LOOKUP_TABLE_ID,
        truncate_item.get("args_contains") == {"lookup_table_id": LOOKUP_TABLE_ID},
        batch_item.get("lookup_table_id") == LOOKUP_TABLE_ID,
        batch_item.get("args_contains") == {"lookup_table_id": LOOKUP_TABLE_ID},
        # entries order is live JOIN order (unpinned here); the verifier
        # fragment pins the exact multiset via expect.batch_entries.
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
