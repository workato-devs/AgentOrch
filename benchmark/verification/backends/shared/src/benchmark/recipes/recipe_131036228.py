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
from ..verifier import verify_131036228


RECIPE_ID = "131036228"
SEED_TYPE = "gtm_drive_logs_retention_counter_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "25347c51"
LOOKUP_TABLE_ID = "4506281"
DECLARE_STEP_AS = "a57546c4"
GET_STEP_AS = "c03a70f4"
FOREACH_AS = "459ab803"
DELETE_STEP_AS = "708d7eed"
UPDATE_STEP_AS = "19f0eb6a"

# clock.scheduled_event (as 25347c51, daily 06:19 America/Los_Angeles) —
# payload-less; ALL time comes from the pinned seed 'now' (=6.months.ago
# fails fast without it):
#   2  workato_variable.declare_variable a57546c4 num_deleted = '0', schema
#      integer (parse_output integer_conversion) — the declare stores int 0
#      and registers num_deleted as an integer-typed variable field.
#   3  lookup_table.get_entries c03a70f4 table 4506281 '[GTM] Google Drive
#      Logs' (col1 Account Id, col2 Phase, col3 Date)
#   FOREACH 4 (as 459ab803, repeat_mode simple) over the entries:
#     IF 5: '=entry.col3.to_date' less_than '=6.months.ago':
#       6  lookup_table.delete_entry 708d7eed (id = foreach id,
#          ignore_not_found 'false')
#       7  workato_variable.update_variables 19f0eb6a num_deleted =
#          '=_dp(a57546c4.num_deleted) + 1' (input_mode raw) — the declared
#          integer schema coerces each write, so the counter accumulates
#          ARITHMETICALLY across iterations (1 -> 2 -> 3; engine fix
#          f9d83a51, re-probed on HEAD): trace args stay engine-canonical
#          STRINGS '1','2','3' while the stored variable is an int.
#
# Boundary semantics (probe-verified): '=6.months.ago' renders an ISO
# DATETIME (now minus 6 months, e.g. '2026-01-07T10:00:00+00:00') while
# '.to_date' renders a DATE ('2026-01-07'); the less_than compares the
# strings, so a col3 equal to the cutoff DATE is deleted whenever the run
# time-of-day is after midnight — exactly Workato's Rails semantics (Date
# coerces to midnight, midnight < run time). The seeder REQUIRES a
# non-midnight 'now' so the one edge where the engine's lexicographic
# compare would diverge from Ruby (exact midnight equality: engine deletes,
# Ruby's strict < keeps) can never be pinned as groundtruth.
#
# All backends are Workato-internal (lookup table + variable + scheduler):
# mock per backend policy, per-variant isolated, no cleanup.

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "clock", "name": "scheduled_event", "as": "25347c51", "skip": false, "input": {"time_unit": "days", "timezone": "America/Los_Angeles", "trigger_at": "06:19:00.000", "trigger_every": "1"}, "block": [{"number": 2, "keyword": "action", "provider": "workato_variable", "name": "declare_variable", "as": "a57546c4", "skip": false, "input": {"variables": {"data": {"num_deleted": "0"}, "schema": "[{\"name\":\"num_deleted\",\"type\":\"integer\",\"optional\":true,\"label\":\"num_deleted\",\"details\":{\"real_name\":\"num_deleted\"},\"control_type\":\"integer\",\"parent\":[\"variables\",\"data\"]}]"}}, "block": []}, {"number": 3, "keyword": "action", "provider": "lookup_table", "name": "get_entries", "as": "c03a70f4", "skip": false, "input": {"lookup_table_id": "4506281"}, "block": []}, {"number": 4, "keyword": "foreach", "provider": "", "name": "", "as": "459ab803", "skip": false, "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"c03a70f4\",\"path\":[\"entries\"]}')}"}, "repeat_mode": "simple", "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"c03a70f4\",\"path\":[\"entries\"]}')}", "block": [{"number": 5, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"459ab803\",\"path\":[\"entry\",\"col3\"]}').to_date", "operand": "less_than", "rhs": "=6.months.ago"}], "operand": "and", "type": "compound"}, "block": [{"number": 6, "keyword": "action", "provider": "lookup_table", "name": "delete_entry", "as": "708d7eed", "skip": false, "input": {"id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"459ab803\",\"path\":[\"id\"]}')}", "ignore_not_found": "false", "lookup_table_id": "4506281"}, "block": []}, {"number": 7, "keyword": "action", "provider": "workato_variable", "name": "update_variables", "as": "19f0eb6a", "skip": false, "input": {"input_mode": "raw", "name": "8c5a396a-44dc-440d-8723-6b88aa8870d7:a57546c4:num_deleted", "num_deleted": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"a57546c4\",\"path\":[\"num_deleted\"]}') + 1"}, "block": []}]}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (DECLARE_STEP_AS, "workato_variable", "declare_variable"),
    (GET_STEP_AS, "lookup_table", "get_entries"),
    (DELETE_STEP_AS, "lookup_table", "delete_entry"),
    (UPDATE_STEP_AS, "workato_variable", "update_variables"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "lookup_table.get_entries",
    "lookup_table.delete_entry",
    "workato_runtime.update_variables",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.get_entries",
    "lookup_table.delete_entry",
]
ROW_COLUMNS = ("col1", "col2", "col3")
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "num_deleted_final",
    "update_args_sequence",
    "deleted_entry_ids",
    "initial_row_count",
    "final_rows",
)
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def validate_131036228(raw: dict[str, Any]) -> dict[str, Any]:
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
    for node in _walk_nodes(raw):
        if node.get("provider") == "lookup_table":
            table = str((node.get("input") or {}).get("lookup_table_id") or "")
            if table != LOOKUP_TABLE_ID:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} lookup step {node.get('as')!r} targets table "
                    f"{table!r}, expected {LOOKUP_TABLE_ID!r}"
                )
    # Semantic pin on the retention window formula pair.
    if_nodes = [node for node in _walk_nodes(raw) if node.get("keyword") == "if"]
    if len(if_nodes) != 1:
        raise RuntimeError(f"recipe {RECIPE_ID} no longer has exactly one IF")
    condition = ((if_nodes[0].get("input") or {}).get("conditions") or [{}])[0]
    if (
        not str(condition.get("lhs") or "").endswith(".to_date")
        or str(condition.get("operand")) != "less_than"
        or str(condition.get("rhs")) != "=6.months.ago"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} retention condition changed: {condition!r}")
    # Semantic pin OUTSIDE the tree pin: the integer coercion that makes the
    # counter accumulate arithmetically hangs off the declare step's
    # extended_input_schema (parse_output integer_conversion), which the
    # normalized tree does NOT cover — guard it explicitly.
    declare = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == DECLARE_STEP_AS),
        None,
    )
    if not isinstance(declare, dict) or not _declares_integer_num_deleted(
        declare.get("extended_input_schema")
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} declare step no longer marks num_deleted as an "
            "integer_conversion field — the counter would string-join"
        )
    update = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == UPDATE_STEP_AS),
        None,
    )
    update_input = (update or {}).get("input") or {}
    formula = str(update_input.get("num_deleted") or "")
    if not formula.endswith(" + 1") or f'"line\\":\\"{DECLARE_STEP_AS}\\"' not in json.dumps(formula):
        raise RuntimeError(f"recipe {RECIPE_ID} counter increment formula changed: {formula!r}")
    if not str(update_input.get("name") or "").endswith(f":{DECLARE_STEP_AS}:num_deleted"):
        raise RuntimeError(f"recipe {RECIPE_ID} update_variables target changed")
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
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


def seed_131036228(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_131036228(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    now = data.get("now")
    if now in (None, ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input requires a fixed 'now' (=6.months.ago "
            "derives from it — fail-fast otherwise)"
        )
    _require_non_midnight_now(str(now))
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be an explicitly-empty object "
            f"(payload-less scheduler tick); got {trigger!r}"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["lookup_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the lookup_table section; "
            f"got {sorted(seed_in.keys())}"
        )
    _require_lookup_section(seed_in["lookup_table"])
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    # Counter-coherence guards: the three counter views of the same ground
    # truth may never drift apart in an authored expect.
    num_deleted = expect.get("num_deleted_final")
    if not isinstance(num_deleted, int) or isinstance(num_deleted, bool) or num_deleted < 0:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.num_deleted_final must be a non-negative INTEGER "
            "(the stored variable is int-typed)"
        )
    if expect.get("update_args_sequence") != [str(i + 1) for i in range(num_deleted)]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.update_args_sequence must be the engine-canonical "
            f"string ladder ['1'..'{num_deleted}']; got {expect.get('update_args_sequence')!r}"
        )
    if (
        not isinstance(expect.get("deleted_entry_ids"), list)
        or len(expect["deleted_entry_ids"]) != num_deleted
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.deleted_entry_ids must list exactly "
            f"{num_deleted} entry ids"
        )
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole "
            "run instead of exercising a recipe branch"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "now": data["now"],
        "expect": deepcopy(expect),
        "lookup_table": deepcopy(seed_in["lookup_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_131036228(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_131036228(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
    if seed.get("now") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing the fixed 'now'")
    initial_snapshot = _snapshot(ctx)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = _snapshot(ctx)
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
    result["verifier"] = verify_131036228(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_non_midnight_now(now: str) -> None:
    try:
        parsed = datetime.datetime.fromisoformat(now.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(f"recipe {RECIPE_ID} 'now' must be an ISO datetime: {now!r}") from exc
    if (parsed.hour, parsed.minute, parsed.second, parsed.microsecond) == (0, 0, 0, 0):
        raise RuntimeError(
            f"recipe {RECIPE_ID} 'now' must not be exactly midnight: a col3 equal to the "
            "cutoff date would then hit the one comparison edge where the engine "
            "(lexicographic: deletes) and Ruby (strict <: keeps) diverge — any other "
            "time of day is Workato-faithful"
        )


def _require_lookup_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.lookup_table must be exactly {{'tables': ...}}")
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
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(ROW_COLUMNS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} must carry exactly columns "
                f"{sorted(ROW_COLUMNS)}; got {sorted(row.keys()) if isinstance(row, dict) else row!r}"
            )
        for column, value in row.items():
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table row {idx}.{column} must be a non-empty string"
                )
        # col3 feeds '.to_date': Workato errors the job on an unparseable
        # date, so every seeded row must be parse-safe ISO — which rows get
        # deleted stays retention behavior, never seed luck.
        if not _DATE_RE.fullmatch(row["col3"]):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx}.col3 must be an ISO date "
                f"(YYYY-MM-DD); got {row['col3']!r}"
            )


def _declares_integer_num_deleted(entries: Any) -> bool:
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        if (
            str(entry.get("name") or "") == "num_deleted"
            and entry.get("parse_output") == "integer_conversion"
        ):
            return True
        if _declares_integer_num_deleted(entry.get("properties")):
            return True
    return False


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
    return ctx.tools.call("harness.lookup_table.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
