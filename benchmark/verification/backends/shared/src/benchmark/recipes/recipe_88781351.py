from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_88781351


RECIPE_ID = "88781351"
SEED_TYPE = "round_robin_linkedin_routing_variant"
TRACK = "workato_service_round_robin_linkedin"
TRIGGER_PROVIDER = "workato_service"
TRIGGER_NAME = "receive_request"
SERVICE_NAME = "Round Robin LinkedIn Routing"
LOOKUP_TABLE_ID = "3256282"
TRY_GET_ENTRY_AS = "84800fd6"
CATCH_AS = "90e02762"
CATCH_GET_ENTRY_AS = "478aa0df"
DEAD_STEP_NUMBERS = [3, 4]
REQUIRED_TRIGGER_REQUEST_FIELDS = ("persona", "category", "asset", "email", "ad_type")
EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("c4998cd3", "workato_variable", "declare_variable"),
    ("b82548af", "workato_variable", "update_variables"),
    ("80079618", "lookup_table", "search_entries"),
    ("84800fd6", "lookup_table", "get_entry"),
    ("478aa0df", "lookup_table", "get_entry"),
    ("e3546496", "workato_service", "send_reply"),
    ("5c5d2e94", "lookup_table", "update_entry"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "workato_runtime.update_variables",
    "lookup_table.search_entries",
    "lookup_table.get_entry",
    "workato_service.send_reply",
    "lookup_table.update_entry",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "lookup_table.get_entry",
    "workato_service.send_reply",
    "lookup_table.update_entry",
]

_RAW_PIN_JSON = r"""{"as": "7b372a5c", "block": [{"as": "c4998cd3", "block": [], "input": {"variables": {"data": {"category": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"7b372a5c\",\"path\":[\"request\", \"category\"]}')}"}, "schema": "[{\"control_type\":\"text\",\"label\":\"Category\",\"name\":\"category\",\"type\":\"string\",\"optional\":true}]"}}, "keyword": "action", "name": "declare_variable", "number": 2, "provider": "workato_variable", "skip": false}, {"as": "", "block": [{"as": "6297598e", "block": [], "keyword": "action", "name": "update_variables", "number": 4, "provider": "workato_variable", "skip": true}], "keyword": "if", "name": "", "number": 3, "provider": "", "skip": true}, {"as": "", "block": [{"as": "b82548af", "block": [], "input": {"category": "ALL", "name": "dcc0acfb-8105-4969-a6ae-de18f0339439:c4998cd3:category"}, "keyword": "action", "name": "update_variables", "number": 6, "provider": "workato_variable", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"7b372a5c\",\"path\":[\"request\", \"ad_type\"]}')}", "operand": "equals_to", "rhs": "Sponsored Message"}, {"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"7b372a5c\",\"path\":[\"request\", \"persona\"]}')}", "operand": "not_equals_to", "rhs": "OEM"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 5, "provider": "", "skip": false}, {"as": "80079618", "block": [], "input": {"lookup_table_id": "3256282", "parameters": {"col2": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c4998cd3\",\"path\":[\"category\"]}')}", "col4": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"7b372a5c\",\"path\":[\"request\", \"ad_type\"]}')}"}}, "keyword": "action", "name": "search_entries", "number": 7, "provider": "lookup_table", "skip": false}, {"as": "", "block": [{"as": "84800fd6", "block": [], "input": {"lookup_table_id": "3256282", "parameters": {"col2": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c4998cd3\",\"path\":[\"category\"]}')}", "col3": "=_('data.lookup_table.80079618.entries').pluck('entry').pluck('col3').min", "col4": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"7b372a5c\",\"path\":[\"request\", \"ad_type\"]}')}"}}, "keyword": "action", "name": "get_entry", "number": 9, "provider": "lookup_table", "skip": false}, {"as": "90e02762", "block": [{"as": "478aa0df", "block": [], "input": {"lookup_table_id": "3256282", "parameters": {"col2": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c4998cd3\",\"path\":[\"category\"]}')}", "col3": "=_('data.lookup_table.80079618.entries').pluck('entry').pluck('col3').last", "col4": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"7b372a5c\",\"path\":[\"request\", \"ad_type\"]}')}"}}, "keyword": "action", "name": "get_entry", "number": 11, "provider": "lookup_table", "skip": false}], "input": {"max_retry_count": "0", "retry_interval": "2"}, "keyword": "catch", "name": "", "number": 10, "provider": "", "skip": false}], "input": {}, "keyword": "try", "name": "", "number": 8, "provider": "", "skip": false}, {"as": "e3546496", "block": [], "input": {"reply": {"sdr_email": "=_('data.lookup_table.478aa0df.entry.col1').presence or _('data.lookup_table.84800fd6.entry.col1')", "success": "true"}, "reply_type": "success"}, "keyword": "action", "name": "send_reply", "number": 12, "provider": "workato_service", "skip": false}, {"as": "5c5d2e94", "block": [], "input": {"id": "=_('data.lookup_table.478aa0df.id').presence or _('data.lookup_table.84800fd6.id')", "ignore_not_found": "false", "lookup_table_id": "3256282", "parameters": {"col3": "=if _('data.lookup_table.478aa0df.entry.col3').present?\n_('data.lookup_table.478aa0df.entry.col3').to_i + 1\nelse \n_('data.lookup_table.84800fd6.entry.col3').to_i + 1\nend"}}, "keyword": "action", "name": "update_entry", "number": 13, "provider": "lookup_table", "skip": false}], "input": {"reply_schema_json": "[{\"name\":\"sdr_email\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"success\",\"type\":\"boolean\",\"optional\":false}]", "request_schema_json": "[{\"control_type\":\"text\",\"label\":\"Persona\",\"name\":\"persona\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Category\",\"name\":\"category\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Asset\",\"name\":\"asset\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Email\",\"name\":\"email\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Ad type\",\"name\":\"ad_type\",\"type\":\"string\",\"optional\":false}]", "service_name": "Round Robin LinkedIn Routing"}, "keyword": "trigger", "name": "receive_request", "number": 1, "provider": "workato_service", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)


def validate_88781351(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != "7b372a5c":
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    if str((raw.get("input") or {}).get("service_name") or "") != SERVICE_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger service name changed")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    # Dead-code proof: IF number 3 and its inner update_variables number 4 must
    # remain skip=true (the executor traces them as skipped, runs nothing).
    dead = {node["number"]: bool(node.get("skip")) for node in _walk_nodes(raw) if node.get("number") in DEAD_STEP_NUMBERS}
    if sorted(dead) != DEAD_STEP_NUMBERS or not all(dead.values()):
        raise RuntimeError(f"recipe {RECIPE_ID} dead steps 3-4 changed: {dead}")
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "service_name": SERVICE_NAME,
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


def seed_88781351(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88781351(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    request = trigger.get("request")
    if not isinstance(request, dict) or sorted(request.keys()) != sorted(REQUIRED_TRIGGER_REQUEST_FIELDS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger request must carry exactly "
            f"{sorted(REQUIRED_TRIGGER_REQUEST_FIELDS)}; got "
            f"{sorted(request.keys()) if isinstance(request, dict) else request}"
        )
    for field in ("persona", "asset", "email", "ad_type"):
        if not str(request.get(field) or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} trigger request field {field!r} must be a non-empty string")
    seed_in = data.get("seed")
    lookup_seed = seed_in.get("lookup_table") if isinstance(seed_in, dict) else None
    tables = lookup_seed.get("tables") if isinstance(lookup_seed, dict) else None
    if not isinstance(tables, dict) or sorted(tables.keys()) != [LOOKUP_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly lookup_table.tables[{LOOKUP_TABLE_ID!r}]"
        )
    rows = tables[LOOKUP_TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {LOOKUP_TABLE_ID} seed must be a non-empty row list "
            "(an empty round-robin table cannot exercise any reachable branch)"
        )
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table {LOOKUP_TABLE_ID} rows must be objects")
        col3 = str(row.get("col3") or "")
        if not (len(col3) == 1 and col3.isdigit()):
            raise RuntimeError(
                f"recipe {RECIPE_ID} seeded col3 counts must be single-digit strings so the "
                f"recipe's lexicographic string .min equals the numeric min; got {row.get('col3')!r}"
            )
    force = data.get("force_action_error")
    if force is not None:
        if not isinstance(force, dict) or str(force.get("step_as") or "") != TRY_GET_ENTRY_AS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} force_action_error is only meaningful on the TRY get_entry "
                f"step_as {TRY_GET_ENTRY_AS!r} (the mock never raises naturally); got {force}"
            )
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "lookup_table": deepcopy(lookup_seed),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_88781351(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88781351(raw)
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
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
            "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_88781351(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


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
