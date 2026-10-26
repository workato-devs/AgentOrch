from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_108625382


RECIPE_ID = "108625382"
SEED_TYPE = "slack_dynamic_menu_snowflake_employee_email_typeahead_variant"
TRACK = "live_snowflake_slack_dynamic_menu_employee_email"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "dynamic_menu"
TRIGGER_AS = "1f5130ea"
SEARCH_AS = "826258bc"
MENU_AS = "25629193"
SNOWFLAKE_TABLE = "PUBLIC.EMPLOYEE"
SEED_COLUMNS = {"email": "string", "first_name": "string", "last_name": "string"}
ROW_KEYS = {"EMAIL", "FIRST_NAME", "LAST_NAME"}
_TYPEAHEAD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 .@-]*")
_SEED_TEXT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 .@_-]*")


_STRUCTURE_PINS_JSON = r'''
[
 {
  "as": "1f5130ea",
  "input": {
   "dynamic_menu_name": "Employee Email",
   "parameters": "[\n\n]"
  },
  "keyword": "trigger",
  "name": "dynamic_menu",
  "number": 1,
  "provider": "slack_bot",
  "skip": false
 },
 {
  "as": "826258bc",
  "input": {
   "limit": "50000",
   "offset": "0",
   "table": "PUBLIC.EMPLOYEE",
   "where": "EMAIL LIKE LOWER(CONCAT('%#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"1f5130ea\",\"path\":[\"typeahead\", \"value\"]}')}%'))\nOR LOWER(CONCAT(FIRST_NAME, ' ', LAST_NAME)) LIKE LOWER(CONCAT('%#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"1f5130ea\",\"path\":[\"typeahead\", \"value\"]}')}%'))"
  },
  "keyword": "action",
  "name": "search_rows",
  "number": 2,
  "provider": "snowflake",
  "skip": false
 },
 {
  "as": "25629193",
  "input": {
   "options": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"826258bc\",\"path\":[\"rows\"]}')}",
    "label": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"826258bc\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"first_name\"]}')} #{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"826258bc\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"last_name\"]}')} (#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"826258bc\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"email\"]}')})",
    "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"826258bc\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"email\"]}')}"
   }
  },
  "keyword": "action",
  "name": "generate_menu_options",
  "number": 3,
  "provider": "slack_bot",
  "skip": false
 }
]
'''

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows",
    "slack_bot.generate_menu_options",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows",
    "slack_bot.generate_menu_options",
]
BRANCHES = (
    "email_arm_match",
    "name_arm_mixed_case",
    "email_case_quirk",
    "zero_match",
    "multi_match",
)


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
    out = [pin]
    for child in node.get("block") or []:
        if isinstance(child, dict):
            out.extend(_structure(child))
    return out


def validate_108625382(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger line id changed: {raw.get('as')!r}")
    actual = _structure(raw)
    if len(actual) != len(STRUCTURE_PINS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} node count changed: "
            f"{len(actual)} != {len(STRUCTURE_PINS)}"
        )
    for idx, (got, expected) in enumerate(zip(actual, STRUCTURE_PINS)):
        if got != expected:
            raise RuntimeError(
                f"recipe {RECIPE_ID} node {idx} "
                f"(step {expected.get('number')}) changed:\n"
                f"expected: {json.dumps(expected, sort_keys=True)}\n"
                f"actual:   {json.dumps(got, sort_keys=True)}"
            )
    actions = [pin for pin in actual if pin["keyword"] == "action"]
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
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


def seed_108625382(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_108625382(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    _require_expect_shape(data)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"snowflake_live"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    snowflake_seed = seed_in.get("snowflake_live")
    _require_snowflake_section(snowflake_seed)
    provision = ctx.tools.call("harness.snowflake_live.seed_tables", {"snowflake": snowflake_seed})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch block: a forced action error would "
            "fail the whole job, which is not a recipe branch"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(data.get("expect")),
        "raw_validation": validation,
        "snowflake_live": deepcopy(provision["state"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_108625382(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_108625382(raw)
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    cleanup: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
    if not (cleanup or {}).get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake cleanup failed: {cleanup}")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
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
    result["verifier"] = verify_108625382(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {"typeahead"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the typeahead "
            f"object (the menu declares parameters '[]' -- none); got {sorted(trigger)}"
        )
    typeahead = trigger.get("typeahead")
    if not isinstance(typeahead, dict) or set(typeahead) != {"value"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger typeahead must be exactly {{'value'}}; got {typeahead!r}"
        )
    value = typeahead.get("value")
    if not isinstance(value, str) or not _TYPEAHEAD_RE.fullmatch(value):
        raise RuntimeError(
            f"recipe {RECIPE_ID} typeahead.value is spliced raw into SQL twice: it "
            f"must match {_TYPEAHEAD_RE.pattern!r} (no quotes, no %/_ LIKE "
            f"wildcards); got {value!r}"
        )


def _require_expect_shape(data: dict[str, Any]) -> None:
    expect = data.get("expect")
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    if not isinstance(expect.get("tools"), list) or not isinstance(expect.get("tool_expectations"), list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect must pin tools and tool_expectations lists")
    if expect.get("branch") not in BRANCHES:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.branch must be one of {sorted(BRANCHES)}; "
            f"got {expect.get('branch')!r}"
        )
    if not isinstance(expect.get("menu_options"), list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.menu_options must pin the exact options list")
    if expect.get("executed_action_count") != 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} is branchless: both steps run on every variant "
            f"(executed_action_count must be 2); got {expect.get('executed_action_count')!r}"
        )


def _require_snowflake_section(section: Any) -> None:
    if not isinstance(section, dict) or set(section) != {"tables"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must carry exactly the tables "
            f"object; got {sorted(section) if isinstance(section, dict) else section!r}"
        )
    tables = section.get("tables")
    if not isinstance(tables, dict) or set(tables) != {SNOWFLAKE_TABLE}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} must seed exactly tables[{SNOWFLAKE_TABLE!r}]; "
            f"got {sorted(tables) if isinstance(tables, dict) else tables!r}"
        )
    spec = tables.get(SNOWFLAKE_TABLE)
    if not isinstance(spec, dict) or set(spec) != {"columns", "rows"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table spec must declare exactly columns + rows; "
            f"got {sorted(spec) if isinstance(spec, dict) else spec!r}"
        )
    if spec.get("columns") != SEED_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seeds exactly the three dereferenced columns "
            f"{SEED_COLUMNS!r} (the 28-column extended schema is read-shape "
            f"metadata only); got {spec.get('columns')!r}"
        )
    rows = spec.get("rows")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires a non-empty EMPLOYEE seed -- an empty "
            f"table cannot prove the where clause excluded anything"
        )
    for row in rows:
        if not isinstance(row, dict) or set(row) != ROW_KEYS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} each seed row must carry exactly "
                f"{sorted(ROW_KEYS)}; got {row!r}"
            )
        for key, value in row.items():
            if not isinstance(value, str) or not _SEED_TEXT_RE.fullmatch(value):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} seed row value {key}={value!r} must match "
                    f"{_SEED_TEXT_RE.pattern!r} (plain SQL-safe text)"
                )


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("snowflake_live"), dict):
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
