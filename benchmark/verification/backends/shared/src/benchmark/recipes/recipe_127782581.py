from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_127782581


RECIPE_ID = "127782581"
SEED_TYPE = "webhook_crawl_log_level_router_variant"
TRACK = "workato_internal_webhook_crawl_log_router"
TRIGGER_PROVIDER = "workato_webhooks"
TRIGGER_NAME = "new_event"
TRIGGER_AS = "2866ff93"
WEBHOOK_SUFFIX = "Crawl-log"
INFO_LOG_AS = "b91c6491"
INFO_STOP_AS = "449a142b"
ERROR_LOG_AS = "e1dd5675"
ERROR_STOP_AS = "53bbd031"
WARN_LOG_AS = "9e7ca601"
WARN_STOP_AS = "7bbe0728"
FALLTHROUGH_LOG_AS = "8ea3ffbc"


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "workato_webhooks", "name": "new_event", "as": "2866ff93", "skip": false, "input": {"request": {"payload_schema": "[{\"name\":\"event_type\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Event type\"},{\"name\":\"org_id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Org ID\"},{\"name\":\"datasource_name\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Datasource name\"},{\"name\":\"level\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Level\"},{\"name\":\"message\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Message\"},{\"name\":\"timestamp\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Timestamp\"},{\"name\":\"logger_name\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Logger name\"},{\"name\":\"metadata\",\"type\":\"object\",\"optional\":true,\"properties\":[{\"control_type\":\"text\",\"label\":\"Additional options\",\"name\":\"additional_options\",\"type\":\"string\",\"optional\":true}],\"label\":\"Metadata\"}]", "webhook_type": "json"}, "webhook_suffix": "Crawl-log"}, "block": [{"number": 2, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"2866ff93\",\"path\":[\"payload\",\"level\"]}').downcase", "operand": "equals_to", "rhs": "info"}], "operand": "and", "type": "compound"}, "block": [{"number": 3, "keyword": "action", "provider": "logger", "name": "log_message", "as": "b91c6491", "skip": false, "input": {"log_level": "INFO", "message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"2866ff93\",\"path\":[\"payload\", \"message\"]}')}", "user_logs_enabled": true}, "block": []}, {"number": 4, "keyword": "stop", "provider": "", "name": "", "as": "449a142b", "skip": false, "input": {"stop_with_error": "false"}, "block": []}]}, {"number": 5, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"2866ff93\",\"path\":[\"payload\",\"level\"]}').downcase", "operand": "equals_to", "rhs": "error"}], "operand": "and", "type": "compound"}, "block": [{"number": 6, "keyword": "action", "provider": "logger", "name": "log_message", "as": "e1dd5675", "skip": false, "input": {"log_level": "ERROR", "message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"2866ff93\",\"path\":[\"payload\", \"message\"]}')}", "user_logs_enabled": true}, "block": []}, {"number": 7, "keyword": "stop", "provider": "", "name": "", "as": "53bbd031", "skip": false, "input": {"stop_with_error": "false"}, "block": []}]}, {"number": 8, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"2866ff93\",\"path\":[\"payload\",\"level\"]}').downcase", "operand": "equals_to", "rhs": "warn"}], "operand": "and", "type": "compound"}, "block": [{"number": 9, "keyword": "action", "provider": "logger", "name": "log_message", "as": "9e7ca601", "skip": false, "input": {"log_level": "WARN", "message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"2866ff93\",\"path\":[\"payload\", \"message\"]}')}", "user_logs_enabled": true}, "block": []}, {"number": 10, "keyword": "stop", "provider": "", "name": "", "as": "7bbe0728", "skip": false, "input": {"stop_with_error": "false"}, "block": []}]}, {"number": 11, "keyword": "action", "provider": "logger", "name": "log_message", "as": "8ea3ffbc", "skip": false, "input": {"message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"2866ff93\",\"path\":[\"payload\", \"message\"]}')}", "user_logs_enabled": "false"}, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (INFO_LOG_AS, "logger", "log_message"),
    (ERROR_LOG_AS, "logger", "log_message"),
    (WARN_LOG_AS, "logger", "log_message"),
    (FALLTHROUGH_LOG_AS, "logger", "log_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.log_message",
]
ALLOWED_TOOLS: list[str] = []
LEVEL_ROUTES = {
    "info": (INFO_LOG_AS, INFO_STOP_AS),
    "error": (ERROR_LOG_AS, ERROR_STOP_AS),
    "warn": (WARN_LOG_AS, WARN_STOP_AS),
}
PAYLOAD_KEYS = (
    "event_type",
    "org_id",
    "datasource_name",
    "level",
    "message",
    "timestamp",
    "logger_name",
    "metadata",
)
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "log_step_as",
    "log_message",
    "stop_step_as",
)


def validate_127782581(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    if str((raw.get("input") or {}).get("webhook_suffix") or "") != WEBHOOK_SUFFIX:
        raise RuntimeError(f"recipe {RECIPE_ID} webhook suffix changed")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    # Semantic pins (the tree pin holds the exact bytes; these name the trap):
    # the three IFs stay .downcase equality on info/error/warn IN THAT ORDER,
    # and each guarded block is log-then-stop.
    if_nodes = [node for node in _walk_nodes(raw) if node.get("keyword") == "if"]
    if len(if_nodes) != 3:
        raise RuntimeError(f"recipe {RECIPE_ID} no longer has exactly three IFs")
    expected_rhs = ["info", "error", "warn"]
    for idx, node in enumerate(if_nodes):
        condition = ((node.get("input") or {}).get("conditions") or [{}])[0]
        if (
            not str(condition.get("lhs") or "").endswith(".downcase")
            or str(condition.get("operand")) != "equals_to"
            or str(condition.get("rhs")) != expected_rhs[idx]
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} IF #{idx + 1} condition changed: {condition!r}"
            )
        children = [child for child in node.get("block") or [] if isinstance(child, dict)]
        if [child.get("keyword") for child in children] != ["action", "stop"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} IF #{idx + 1} block is no longer log-then-stop"
            )
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "webhook_suffix": WEBHOOK_SUFFIX,
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


def seed_127782581(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_127782581(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if seed_in != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must be an explicitly-empty object (pure-mock "
            f"webhooks + logger, no backend state); got {seed_in!r}"
        )
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole "
            "run instead of exercising a recipe branch"
        )
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    _require_expect_coherence(trigger, expect)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_127782581(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_127782581(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    raw_execution = execute_raw_recipe(raw, seed, ctx)
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
            "initial_snapshot": {},
            "final_snapshot": {},
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_127782581(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != ["payload"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the payload object; "
            f"got {sorted(trigger.keys())}"
        )
    payload = trigger.get("payload")
    if not isinstance(payload, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger payload must be an object")
    unknown = sorted(set(payload.keys()) - set(PAYLOAD_KEYS))
    if unknown:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger payload may only carry the declared webhook "
            f"schema fields {list(PAYLOAD_KEYS)}; got {unknown}"
        )
    for key in ("level", "message"):
        if not isinstance(payload.get(key), str) or not payload[key].strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger payload.{key} must be a non-empty string "
                "(level routes the IF ladder; message feeds every log step)"
            )
    for key, value in payload.items():
        if key == "metadata":
            if not isinstance(value, dict) or sorted(set(value.keys()) - {"additional_options"}):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} payload.metadata may only carry "
                    f"additional_options; got {value!r}"
                )
            continue
        if not isinstance(value, str):
            raise RuntimeError(f"recipe {RECIPE_ID} payload.{key} must be a string")


def _require_expect_coherence(trigger: dict[str, Any], expect: dict[str, Any]) -> None:
    # The routed branch is fully determined by level.downcase (probed on HEAD):
    # the authored expect may never contradict it.
    level = str(trigger["payload"]["level"]).lower()
    message = str(trigger["payload"]["message"])
    log_as, stop_as = LEVEL_ROUTES.get(level, (FALLTHROUGH_LOG_AS, None))
    if expect.get("log_step_as") != log_as or expect.get("stop_step_as") != stop_as:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect routes level {level!r} to "
            f"({expect.get('log_step_as')!r}, {expect.get('stop_step_as')!r}); the recipe "
            f"routes it to ({log_as!r}, {stop_as!r})"
        )
    if expect.get("log_message") != message:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.log_message must equal the trigger message "
            f"verbatim; got {expect.get('log_message')!r}"
        )
    if expect.get("executed_action_count") != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} every branch executes exactly ONE log action; got "
            f"{expect.get('executed_action_count')!r}"
        )
    if expect.get("tools") != [] or expect.get("tool_expectations") != []:
        raise RuntimeError(
            f"recipe {RECIPE_ID} runs zero registry tools on every branch: expect.tools "
            "and expect.tool_expectations must be explicitly-empty lists"
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


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
