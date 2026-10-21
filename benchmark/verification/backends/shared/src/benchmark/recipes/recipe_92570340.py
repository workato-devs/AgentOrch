from __future__ import annotations

import datetime
import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_92570340


RECIPE_ID = "92570340"
SEED_TYPE = "lookup_table_gtm_chatter_log_retention_variant"
TRACK = "workato_lookup_table_gtm_chatter_log_retention"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "73e5c27a"
GET_ENTRIES_AS = "a39f8379"
FOREACH_AS = "e89b1cf4"
DELETE_AS = "c66fb912"
LOOKUP_TABLE_ID = "3417234"
DATE_COL = "col5"
CUTOFF_DAYS = 180
ROW_COLS = ("col1", "col2", "col3", "col4", "col5")

# clock.scheduled_event 73e5c27a (weekly Mon-Fri 06:00 America/Los_Angeles,
# payload-less) ->
#   2 lookup_table.get_entries a39f8379 (mock table 3417234 '[GTM] Chatter -
#     Log'; entries expose id + nested entry.col1..col5 + flat colN copies)
#   3 FOREACH e89b1cf4 over a39f8379.entries (simple; zero entries -> zero
#     iterations)
#     4 IF =_('data.foreach.e89b1cf4.entry.col5').to_date less_than
#         =180.days.ago
#       5 lookup_table.delete_entry c66fb912 (id = foreach.id pill,
#         ignore_not_found 'true', table 3417234)
#
# FULL MOCK (Workato-internal only): the lookup table is per-variant seeded
# mock state; the clock trigger is payload-less and determinism comes from the
# REQUIRED seed['now'] (=180.days.ago fail-fasts without it). No live lane,
# no cleanup (the mock table is rebuilt from the variant seed on every run —
# rerun-identical, probe-verified).
#
# Probe findings pinned by seeder/variants (current tree, 2026-07-08):
# - delete ids are the integer _row_ids the mock assigns in seed order
#   (0-based); the variants pin them per run via expect.deleted_ids.
# - BOUNDARY IS CLOCK-COUPLED: the IF compares '.to_date' (renders
#   'YYYY-MM-DD') against the ago cutoff rendered as a UTC ISO datetime
#   string; a row dated exactly the cutoff DATE compares less_than (deleted,
#   probe-verified 2025-09-11 vs cutoff 2025-09-11T06:00). The seeder
#   therefore requires every date to sit >= 2 days clear of the cutoff date.
# - BLANK col5 would silently DELETE (''.to_date -> '' -> '' less_than
#   '<cutoff>' is a string compare -> true) where real Workato errors the job
#   on ''.to_date — the seeder forbids blank col5 (probe-verified).
# - non-ISO col5 raises ValueError fail-fast (probe-verified) — the seeder
#   requires strict YYYY-MM-DD.
# - a missing seed['now'] fail-fasts inside =180.days.ago (probe-verified).

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "clock", "name": "scheduled_event", "as": "73e5c27a", "skip": false, "input": {"days_of_week": "1,2,3,4,5", "time_unit": "weeks", "timezone": "America/Los_Angeles", "trigger_at": "06:00:00", "trigger_every": "1"}, "block": [{"number": 2, "keyword": "action", "provider": "lookup_table", "name": "get_entries", "as": "a39f8379", "skip": false, "input": {"lookup_table_id": "3417234"}, "block": []}, {"number": 3, "keyword": "foreach", "provider": "", "name": "", "as": "e89b1cf4", "skip": false, "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"a39f8379\",\"path\":[\"entries\"]}')}"}, "repeat_mode": "simple", "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"a39f8379\",\"path\":[\"entries\"]}')}", "block": [{"number": 4, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "=_('data.foreach.e89b1cf4.entry.col5').to_date", "operand": "less_than", "rhs": "=180.days.ago"}], "operand": "and", "type": "compound"}, "block": [{"number": 5, "keyword": "action", "provider": "lookup_table", "name": "delete_entry", "as": "c66fb912", "skip": false, "input": {"id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"e89b1cf4\",\"path\":[\"id\"]}')}", "ignore_not_found": "true", "lookup_table_id": "3417234"}, "block": []}]}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[int, str, str, str]] = [
    (2, GET_ENTRIES_AS, "lookup_table", "get_entries"),
    (5, DELETE_AS, "lookup_table", "delete_entry"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.get_entries",
    "lookup_table.delete_entry",
]
ALLOWED_TOOLS: list[str] = list(EXPECTED_RAW_TOOLS)
REQUIRED_EXPECT_KEYS = (
    "branch",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "initial_row_count",
    "deleted_ids",
    "final_table_rows",
)
BRANCHES = (
    "mixed_old_and_recent",
    "all_recent_no_deletes",
    "all_old_all_deleted",
    "empty_table",
)
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_92570340(raw: dict[str, Any]) -> dict[str, Any]:
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
        "lookup_table_id": LOOKUP_TABLE_ID,
        "date_column": DATE_COL,
        "cutoff_days": CUTOFF_DAYS,
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


def seed_92570340(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_92570340(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger is a payload-less scheduler tick: trigger_input "
            f"must be exactly {{}} (nothing in the recipe dereferences it); got {trigger!r}"
        )
    cutoff_date = _require_now(data)
    rows = _require_table_rows(data)
    expect = data.get("expect")
    _require_expect(expect, rows, cutoff_date)
    seed_in = data["seed"]
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "now": data["now"],
        "lookup_table": deepcopy(seed_in["lookup_table"]),
    }
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no reachable catch: force_action_error would "
            "only produce an unverifiable crash, never a branch"
        )
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_92570340(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_92570340(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    initial_snapshot = ctx.tools.call("harness.lookup_table.snapshot", {})
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = ctx.tools.call("harness.lookup_table.snapshot", {})
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
            # Full mock (Workato-internal only): the per-variant mock table is
            # rebuilt from the seed on every run, so no cleanup is needed.
            "cleanup_response": None,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_92570340(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_now(data: dict[str, Any]) -> datetime.date:
    now_raw = data.get("now")
    if not isinstance(now_raw, str) or not now_raw.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires an explicit ISO seed 'now' with timezone "
            "(the =180.days.ago cutoff is derived from it)"
        )
    now_dt = datetime.datetime.fromisoformat(now_raw.replace("Z", "+00:00"))
    if now_dt.tzinfo is None:
        raise RuntimeError(f"recipe {RECIPE_ID} seed 'now' must carry timezone information")
    # Mirror the engine: N.days.ago = (now - N days) rendered in UTC.
    cutoff_dt = (now_dt - datetime.timedelta(days=CUTOFF_DAYS)).astimezone(
        datetime.timezone.utc
    )
    return cutoff_dt.date()


def _require_table_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["lookup_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant seed must carry exactly seed.lookup_table; "
            f"got {sorted(seed_in.keys()) if isinstance(seed_in, dict) else seed_in!r}"
        )
    section = seed_in["lookup_table"]
    tables = section.get("tables") if isinstance(section, dict) else None
    if (
        not isinstance(section, dict)
        or sorted(section.keys()) != ["tables"]
        or not isinstance(tables, dict)
        or sorted(tables.keys()) != [LOOKUP_TABLE_ID]
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table must seed exactly table "
            f"{LOOKUP_TABLE_ID} (tables key only); got {section!r}"
        )
    rows = tables[LOOKUP_TABLE_ID]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {LOOKUP_TABLE_ID} rows must be a list")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(ROW_COLS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} row {idx} must carry exactly columns "
                f"{sorted(ROW_COLS)} (no _row_id overrides — delete ids are the "
                f"0-based seed order); got {sorted(row.keys()) if isinstance(row, dict) else row!r}"
            )
        for col in ROW_COLS:
            value = row[col]
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} row {idx} column {col} must be a non-empty "
                    f"string (a blank {DATE_COL} would silently DELETE under the "
                    "engine where real Workato errors the job); got "
                    f"{value!r}"
                )
        if not _DATE_RE.fullmatch(row[DATE_COL]):
            raise RuntimeError(
                f"recipe {RECIPE_ID} row {idx} {DATE_COL} must be strict ISO "
                f"YYYY-MM-DD (non-ISO dates raise ValueError mid-run); got "
                f"{row[DATE_COL]!r}"
            )
    return rows


def _row_dates_clear_of_boundary(
    rows: list[dict[str, Any]], cutoff_date: datetime.date
) -> list[int]:
    deleted: list[int] = []
    for idx, row in enumerate(rows):
        row_date = datetime.date.fromisoformat(row[DATE_COL])
        margin = abs((row_date - cutoff_date).days)
        if margin < 2:
            raise RuntimeError(
                f"recipe {RECIPE_ID} row {idx} {DATE_COL} {row[DATE_COL]!r} sits "
                f"within 2 days of the {CUTOFF_DAYS}-day cutoff date {cutoff_date} — "
                "boundary rows are clock/timezone-coupled (a row dated exactly the "
                "cutoff date deletes via string compare, probe-verified); seed clear "
                "of the boundary"
            )
        if row_date < cutoff_date:
            deleted.append(idx)
    return deleted


def _require_expect(
    expect: Any, rows: list[dict[str, Any]], cutoff_date: datetime.date
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
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch must be one of {BRANCHES}")
    deleted = _row_dates_clear_of_boundary(rows, cutoff_date)
    kept_rows = [
        {"id": idx, **{col: row[col] for col in ROW_COLS}}
        for idx, row in enumerate(rows)
        if idx not in deleted
    ]
    branch_shape_ok = {
        "mixed_old_and_recent": bool(deleted) and bool(kept_rows),
        "all_recent_no_deletes": bool(rows) and not deleted,
        "all_old_all_deleted": bool(rows) and len(deleted) == len(rows),
        "empty_table": not rows,
    }[branch]
    if not branch_shape_ok:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seeded rows do not produce branch {branch!r}: "
            f"{len(rows)} rows, computed deletions {deleted}"
        )
    expected_tools = ["lookup_table.get_entries"] + ["lookup_table.delete_entry"] * len(deleted)
    expected_items = [
        {
            "tool": "lookup_table.get_entries",
            "lookup_table_id": LOOKUP_TABLE_ID,
            "args_contains": {"lookup_table_id": LOOKUP_TABLE_ID},
            "result_count": len(rows),
        }
    ] + [
        {
            "tool": "lookup_table.delete_entry",
            "lookup_table_id": LOOKUP_TABLE_ID,
            "args_contains": {
                "lookup_table_id": LOOKUP_TABLE_ID,
                "id": row_id,
                "ignore_not_found": "true",
            },
        }
        for row_id in deleted
    ]
    checks = (
        expect.get("executed_action_count") == 1 + len(deleted),
        expect.get("initial_row_count") == len(rows),
        expect.get("deleted_ids") == deleted,
        expect.get("final_table_rows") == kept_rows,
        expect.get("tools") == expected_tools,
        expect.get("tool_expectations") == expected_items,
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block does not match the seeded ground truth "
            f"(computed: deleted {deleted}, kept {kept_rows}, tools {expected_tools}, "
            f"items {expected_items}); got {expect!r}"
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
