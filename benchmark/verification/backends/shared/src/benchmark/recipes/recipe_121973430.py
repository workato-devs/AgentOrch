from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_121973430


RECIPE_ID = "121973430"
SEED_TYPE = "api_resume_upsert_allowlist_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "98519657"
TABLE_ID = "29375"
UPSERT_STEP_AS = "9c05c139"
RESPONSE_STEP_AS = "return_response_5"
STOP_STEP_AS = "c5aec6a6"
CATCH_STEP_AS = "catch_6"
LOG_STEP_AS = "log_message_7"


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "workato_api_platform", "name": "receive_request", "as": "98519657", "skip": false, "input": {"request": {"content_type": "json", "schema": "[{\"control_type\":\"text\",\"label\":\"job_id\",\"name\":\"job_id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"application_id\",\"name\":\"application_id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Role\",\"name\":\"role\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Resume URL\",\"name\":\"resume_url\",\"type\":\"string\",\"optional\":true}]"}, "response": {"content_type": "json", "responses": [{"http_status_code": "200", "name": "success"}]}}, "block": [{"number": 2, "keyword": "try", "provider": "", "name": "", "as": "try_3", "skip": false, "input": {}, "block": [{"number": 3, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"98519657\",\"path\":[\"request\",\"job_id\"]}').to_s.match?(/7984378002|7983026002|7951510002|7953119002|7829658002|6171798002/)", "operand": "is_true"}], "operand": "and", "type": "compound"}, "block": [{"number": 4, "keyword": "action", "provider": "workato_db_table", "name": "upsert_record", "as": "9c05c139", "skip": false, "input": {"parameters": {"3ac3e90c_8e9b_4b58_b019_715ecd63b3d4": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"98519657\",\"path\":[\"request\", \"application_id\"]}')}", "7b20b969_f842_4eaa_8f35_753fe911fbee": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"98519657\",\"path\":[\"request\", \"resume_url\"]}')}", "a7ba4bb3_7e03_4298_8f2e_f302d17fff39": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"98519657\",\"path\":[\"request\", \"job_id\"]}')}", "c90c7596_43bf_466c_8a8f_b6d9819e2169": "New", "fe5cbb7e_f1ba_4cc2_8cd3_509e81f6b4d1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"98519657\",\"path\":[\"request\", \"role\"]}')}"}, "primary_field_id": "3ac3e90c-8e9b-4b58-b019-715ecd63b3d4", "table_id": "29375"}, "block": []}, {"number": 5, "keyword": "action", "provider": "workato_api_platform", "name": "return_response", "as": "return_response_5", "skip": false, "input": {"http_status_code": "200"}, "block": []}]}, {"number": 6, "keyword": "stop", "provider": "", "name": "", "as": "c5aec6a6", "skip": false, "input": {"stop_with_error": "false"}, "block": []}, {"number": 7, "keyword": "catch", "provider": "", "name": "", "as": "catch_6", "skip": false, "input": {"max_retry_count": "0", "retry_interval": "2"}, "block": [{"number": 8, "keyword": "action", "provider": "logger", "name": "log_message", "as": "log_message_7", "skip": false, "input": {"message": "Type: #{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"catch_6\",\"path\":[\"type\"]}')}\nMessage: #{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"catch_6\",\"path\":[\"message\"]}')}\nStep: #{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"catch_6\",\"path\":[\"line_number\"]}')}\nApp: #{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"catch_6\",\"path\":[\"adapter\"]}')}\nAction: #{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"catch_6\",\"path\":[\"action\"]}')}", "user_logs_enabled": "false"}, "block": []}]}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (UPSERT_STEP_AS, "workato_db_table", "upsert_record"),
    (RESPONSE_STEP_AS, "workato_api_platform", "return_response"),
    (LOG_STEP_AS, "logger", "log_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.upsert_record",
    "workato_api_platform.return_response",
    "workato_runtime.log_message",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.upsert_record",
    "workato_api_platform.return_response",
]
ALLOWLIST = (
    "7984378002",
    "7983026002",
    "7951510002",
    "7953119002",
    "7829658002",
    "6171798002",
)
APP_COL = "3ac3e90c_8e9b_4b58_b019_715ecd63b3d4"
JOB_COL = "a7ba4bb3_7e03_4298_8f2e_f302d17fff39"
ROLE_COL = "fe5cbb7e_f1ba_4cc2_8cd3_509e81f6b4d1"
URL_COL = "7b20b969_f842_4eaa_8f35_753fe911fbee"
STATUS_COL = "c90c7596_43bf_466c_8a8f_b6d9819e2169"
LOG_COL = "d32edade_33fa_4613_b8f7_976915faf727"
ROW_COLUMNS = (APP_COL, JOB_COL, ROLE_COL, URL_COL, STATUS_COL, LOG_COL)
TRIGGER_REQUEST_KEYS = ("job_id", "application_id", "role", "resume_url")
BRANCHES = ("upsert_create", "upsert_update", "stop_no_match", "catch_error")
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "branch",
    "stopped",
    "return_value",
    "catch_log_messages",
    "initial_table_rows",
    "final_table_rows",
)
_ALLOWLIST_RE = re.compile("|".join(ALLOWLIST))


def validate_121973430(raw: dict[str, Any]) -> dict[str, Any]:
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
    # Twin-drift guard: the upsert must target THIS recipe's table id (the
    # 122043574 twin differs only here).
    for node in _walk_nodes(raw):
        if node.get("provider") == "workato_db_table":
            table = str((node.get("input") or {}).get("table_id") or "")
            if table != TABLE_ID:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} db-table step {node.get('as')!r} targets table "
                    f"{table!r}, expected {TABLE_ID!r} (twin drift?)"
                )
    # Semantic pins on the drift-prone bits (the tree pin holds the exact
    # bytes; these guards name the trap when one changes).
    if_nodes = [node for node in _walk_nodes(raw) if node.get("keyword") == "if"]
    if len(if_nodes) != 1:
        raise RuntimeError(f"recipe {RECIPE_ID} no longer has exactly one IF")
    if_lhs = str(((if_nodes[0].get("input") or {}).get("conditions") or [{}])[0].get("lhs") or "")
    if f".to_s.match?(/{'|'.join(ALLOWLIST)}/)" not in if_lhs:
        raise RuntimeError(f"recipe {RECIPE_ID} allowlist regex changed: {if_lhs!r}")
    stop = next((node for node in _walk_nodes(raw) if node.get("keyword") == "stop"), None)
    if not isinstance(stop, dict) or str((stop.get("input") or {}).get("stop_with_error")) != "false":
        raise RuntimeError(f"recipe {RECIPE_ID} stop step changed")
    log = next((node for node in _walk_nodes(raw) if str(node.get("as") or "") == LOG_STEP_AS), None)
    message = str(((log or {}).get("input") or {}).get("message") or "")
    for path in ("type", "message", "line_number", "adapter", "action"):
        if f'\\"path\\":[\\"{path}\\"]' not in json.dumps(message):
            raise RuntimeError(f"recipe {RECIPE_ID} catch log no longer renders catch.{path}")
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "table_id": TABLE_ID,
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


def seed_121973430(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_121973430(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["workato_db_table"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the workato_db_table section; "
            f"got {sorted(seed_in.keys())}"
        )
    _require_db_table_section(seed_in["workato_db_table"])
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    branch = expect.get("branch")
    if branch not in BRANCHES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch must be one of {BRANCHES}; got {branch!r}")
    # Branch/seed coherence: the IF-3 outcome is decided by the trigger job_id
    # (Ruby match? is UNANCHORED: containment matches). Guarding here keeps a
    # variant from pinning a branch its own trigger cannot reach.
    matched = bool(_ALLOWLIST_RE.search(str(trigger["request"]["job_id"])))
    if branch == "stop_no_match" and matched:
        raise RuntimeError(
            f"recipe {RECIPE_ID} stop_no_match variant carries an allowlist-matching job_id"
        )
    if branch != "stop_no_match" and not matched:
        raise RuntimeError(
            f"recipe {RECIPE_ID} {branch} variant needs an allowlist-matching job_id "
            "(containment counts: match? is unanchored)"
        )
    force = data.get("force_action_error")
    if branch == "catch_error":
        if not isinstance(force, dict) or str(force.get("step_as") or "") != UPSERT_STEP_AS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch_error variants must force the error on the "
                f"upsert step {UPSERT_STEP_AS} (the mock upsert cannot fail organically)"
            )
    elif force is not None:
        raise RuntimeError(f"recipe {RECIPE_ID} only catch_error variants may force an action error")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_121973430(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_121973430(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
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
    result["verifier"] = verify_121973430(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != ["request"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'request': ...}} "
            f"(the receive_request payload); got {sorted(trigger.keys())}"
        )
    request = trigger["request"]
    if not isinstance(request, dict) or sorted(request.keys()) != sorted(TRIGGER_REQUEST_KEYS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger request must carry exactly "
            f"{sorted(TRIGGER_REQUEST_KEYS)}; got "
            f"{sorted(request.keys()) if isinstance(request, dict) else request!r}"
        )
    for key in TRIGGER_REQUEST_KEYS:
        if not isinstance(request.get(key), str) or not request[key].strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger request.{key} must be a non-empty string "
                "(every field feeds the upsert record verbatim)"
            )


def _require_db_table_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table must be exactly {{'tables': ...}}"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table.tables must declare exactly table "
            f"{TABLE_ID!r} (rows may be an explicit empty list)"
        )
    rows = tables[TABLE_ID]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {TABLE_ID} rows must be a list")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table row {idx} must be an object")
        unknown = sorted(set(row.keys()) - set(ROW_COLUMNS))
        if unknown:
            raise RuntimeError(f"recipe {RECIPE_ID} table row {idx} has unknown columns: {unknown}")
        for column, value in row.items():
            if not isinstance(value, str):
                raise RuntimeError(f"recipe {RECIPE_ID} table row {idx}.{column} must be a string")
        if not str(row.get(APP_COL) or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} requires a non-empty Application ID "
                f"({APP_COL}) — the upsert keys on it"
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
    return ctx.tools.call("harness.workato_db_table.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
