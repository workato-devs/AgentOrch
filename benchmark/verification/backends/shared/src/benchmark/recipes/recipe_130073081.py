from __future__ import annotations

import datetime
import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_130073081


RECIPE_ID = "130073081"
SEED_TYPE = "chi_2024_recipe_hierarchy_ctas_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "d5a45675"
DECLARE_STEP_AS = "70d77402"
SQL_STEP_AS = "a0fed501"
ASYNC_STEP_AS = "171a0a26"
CATCH_RETURN_AS = "c4d311ab"
STOP_STEP_AS = "49c00a91"
SUCCESS_RETURN_AS = "fdf1f721"
TARGET_TABLE = "plg.chi_2024_recipe_hierarchy_operational"
SOURCE_TABLE = "plg.chi_2024_hierarchy_base_interim_operational"
SOURCE_COLUMNS = {
    "flow_id": "string",
    "parent_id": "string",
    "entry_date": "date",
    "data_center": "string",
    "is_valid_workflow": "boolean",
}


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "workato_recipe_function", "name": "execute", "as": "d5a45675", "skip": false, "input": {"result_schema_json": "[{\"name\":\"status\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Status\"}]"}, "block": [{"number": 2, "keyword": "action", "provider": "workato_variable", "name": "declare_variable", "as": "70d77402", "skip": false, "input": {"variables": {"data": {"snap_date": "=now.strftime(\"%Y-%m-%d\")"}, "schema": "[{\"name\":\"snap_date\",\"type\":\"string\",\"optional\":true,\"label\":\"snap_date\",\"details\":{\"real_name\":\"snap_date\"},\"control_type\":\"text\"}]"}}, "block": []}, {"number": 3, "keyword": "try", "provider": "", "name": "", "as": "", "skip": false, "input": {}, "block": [{"number": 4, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql", "as": "a0fed501", "skip": false, "input": {"sql": "create or replace table plg.chi_2024_recipe_hierarchy_operational as \nwith recursive recipe_hierarchy_interim as (\n    select t.flow_id\n        , t.entry_date\n        , t.data_center\n        , t.parent_id\n        , t.flow_id as root_flow\n        , 0 as level\n        , array_construct(t.flow_id) as hierarchy_path\n    from plg.chi_2024_hierarchy_base_interim_operational t\n    where is_valid_workflow = true\n\n    union all\n\n    select t.flow_id\n        , rhi.entry_date\n        , rhi.data_center\n        , t.parent_id\n        , rhi.root_flow\n        , rhi.level + 1 as level\n        , array_append(rhi.hierarchy_path, t.flow_id) hierarchy_path\n    from plg.chi_2024_hierarchy_base_interim_operational t\n    cross join recipe_hierarchy_interim rhi\n    where t.parent_id = rhi.flow_id and t.entry_date = rhi.entry_date and t.data_center = rhi.data_center\n    and array_contains(t.flow_id::variant, rhi.hierarchy_path) = false\n)\n\nselect entry_date calendar_date\n    , rh.flow_id, rh.data_center\n    , case when level = 0 and parent_id is not null then null else parent_id end parent_id\n    , case \n        when level = 0 and parent_id is not null then 'RF workflow'\n        when level = 0 and parent_id is null then 'Root workflow'\n        else 'Not workflow'\n    end as workflow_type\n    , root_flow\n    , level\n    , hierarchy_path\nfrom recipe_hierarchy_interim rh\ngroup by all\n\n;", "update_only": "false"}, "block": []}, {"number": 5, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql_async_v2", "as": "171a0a26", "skip": true, "block": []}, {"number": 6, "keyword": "catch", "provider": "", "name": "", "as": "461b1472", "skip": false, "input": {"max_retry_count": "0", "retry_interval": "2"}, "block": [{"number": 7, "keyword": "action", "provider": "workato_recipe_function", "name": "return_result", "as": "c4d311ab", "skip": false, "input": {"result": {"status": "failed"}}, "block": []}, {"number": 8, "keyword": "stop", "provider": "", "name": "", "as": "49c00a91", "skip": false, "input": {"stop_reason": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"461b1472\",\"path\":[\"type\"]}')}, #{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"461b1472\",\"path\":[\"message\"]}')}", "stop_with_error": "true"}, "block": []}]}]}, {"number": 9, "keyword": "action", "provider": "workato_recipe_function", "name": "return_result", "as": "fdf1f721", "skip": false, "input": {"result": {"status": "success"}}, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (DECLARE_STEP_AS, "workato_variable", "declare_variable"),
    (SQL_STEP_AS, "snowflake", "run_custom_sql"),
    (CATCH_RETURN_AS, "workato_recipe_function", "return_result"),
    (SUCCESS_RETURN_AS, "workato_recipe_function", "return_result"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "snowflake.run_custom_sql",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "workato_recipe_function.return_result",
]
EXPECTED_RESULT_SCHEMA_JSON = (
    '[{"name":"status","type":"string","optional":false,"control_type":"text","label":"Status"}]'
)
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "return_value",
    "async_step_skipped",
    "final_snowflake_tables",
    "cleanup_tables",
)


def validate_130073081(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    schema_json = str((raw.get("input") or {}).get("result_schema_json") or "")
    if schema_json != EXPECTED_RESULT_SCHEMA_JSON:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger result schema changed")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
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


def seed_130073081(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130073081(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (the recipe-function "
            f"trigger declares no parameters and the recipe reads none): {trigger!r}"
        )
    now = data.get("now")
    if not isinstance(now, str) or not now.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} variant input must pin now (snap_date strftime)")
    parsed_now = datetime.datetime.fromisoformat(now.replace("Z", "+00:00"))
    if parsed_now.tzinfo is None:
        raise RuntimeError(f"recipe {RECIPE_ID} now must carry an explicit UTC offset: {now!r}")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the snowflake_live section"
        )
    _require_snowflake_section(seed_in["snowflake_live"])
    force = data.get("force_action_error")
    _require_force_shape(force)
    expect = data.get("expect")
    _require_expect_shape(expect, force)
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
        "now": now,
        "expect": deepcopy(expect),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_130073081(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_130073081(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    if not str(seed.get("now") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing pinned now")
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
        # Both registered tables (source seed + CTAS target) are
        # benchmark-owned live objects: drop them even when execution fails.
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
    result["verifier"] = verify_130073081(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_snowflake_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the SQL uses no current_date/current_timestamp, so no current_time)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted([TARGET_TABLE, SOURCE_TABLE]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must register exactly {SOURCE_TABLE!r} and "
            f"{TARGET_TABLE!r} (2-part literal names so _rewrite_sql maps both)"
        )
    target = tables[TARGET_TABLE]
    if target != {"rows": []}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} CTAS target {TARGET_TABLE} must be exactly {{'rows': []}}: "
            "no columns means the seeder drops any stale copy and cleanup owns the created "
            f"table; got {target!r}"
        )
    source = tables[SOURCE_TABLE]
    if not isinstance(source, dict) or sorted(source.keys()) != ["columns", "rows"]:
        raise RuntimeError(f"recipe {RECIPE_ID} source table spec must be {{'columns','rows'}}")
    if source["columns"] != SOURCE_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} source columns must be exactly {SOURCE_COLUMNS}"
        )
    rows = source["rows"]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} source rows must be a list (may be empty)")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(SOURCE_COLUMNS.keys()):
            raise RuntimeError(
                f"recipe {RECIPE_ID} source row {idx} must fill every declared column "
                f"(parent_id may be null): {row!r}"
            )
        if not isinstance(row["flow_id"], str) or not row["flow_id"].strip():
            raise RuntimeError(f"recipe {RECIPE_ID} source row {idx} flow_id must be a non-empty string")
        if row["parent_id"] is not None and (
            not isinstance(row["parent_id"], str) or not row["parent_id"].strip()
        ):
            raise RuntimeError(f"recipe {RECIPE_ID} source row {idx} parent_id must be null or non-empty")
        if not isinstance(row["is_valid_workflow"], bool):
            raise RuntimeError(f"recipe {RECIPE_ID} source row {idx} is_valid_workflow must be boolean")
        entry = str(row["entry_date"] or "")
        try:
            datetime.date.fromisoformat(entry)
        except ValueError as exc:
            raise RuntimeError(
                f"recipe {RECIPE_ID} source row {idx} entry_date must be YYYY-MM-DD: {entry!r}"
            ) from exc


def _require_force_shape(force: Any) -> None:
    if force is None:
        return
    if not isinstance(force, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error must be an object")
    if str(force.get("step_as") or "") != SQL_STEP_AS or not str(force.get("error") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error must target step_as {SQL_STEP_AS!r} with an "
            "explicit error message (the CTAS is the only fallible step inside the TRY)"
        )


def _require_expect_shape(expect: Any, force: Any) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    is_catch = force is not None
    expected_return = {"status": "failed"} if is_catch else {"status": "success"}
    if expect.get("return_value") != expected_return:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.return_value must be {expected_return} "
            f"({'catch' if is_catch else 'success'} path): {expect.get('return_value')!r}"
        )
    if bool(expect.get("async_step_skipped")) == is_catch:
        raise RuntimeError(
            f"recipe {RECIPE_ID} async_step_skipped must be true exactly on success paths "
            "(the catch path never reaches the skipped async twin)"
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


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return dict(ctx.tools.call("harness.snowflake.snapshot", {}))


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
