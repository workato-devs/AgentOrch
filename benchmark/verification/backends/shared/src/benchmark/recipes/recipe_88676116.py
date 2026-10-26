from __future__ import annotations

import datetime
import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import _check, _verify_replay_recipe


RECIPE_ID = "88676116"
SEED_TYPE = "flexi_idler_variant"
TRACK = "workato_service_flexi_idler"
TRIGGER_PROVIDER = "workato_service"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "c5e63d24"
SERVICE_NAME = "Flexi Idler"
FLOW_ID = "45178306"
LOG_STEP_AS = "f33691f6"
CREATE_LIST_STEP_AS = "84057fa4"
FOREACH_AS = "95c0de6f"
CHUNK_CALL_AS = "664a521c"
REMAINDER_CALL_AS = "5ed86f4a"
REPLY_STEP_AS = "3a2a1647"


_RAW_PIN_JSON = r"""{"as": "c5e63d24", "block": [{"as": "f33691f6", "block": [], "input": {"message": "=_('data.workato_service.c5e63d24.request.Secs')%10"}, "keyword": "action", "name": "log_message", "number": 2, "provider": "logger", "skip": false}, {"as": "84057fa4", "block": [], "input": {"size": "=(_('data.workato_service.c5e63d24.request.Secs')/10).to_i"}, "keyword": "action", "name": "create_list", "number": 3, "provider": "workato_list", "skip": false}, {"as": "95c0de6f", "block": [{"as": "664a521c", "block": [], "input": {"flow_id": "45178306", "request": {"secs": "=10-(((now-_('data.workato.job_context.job_created_at')).to_i+10)-(_('data.foreach.95c0de6f.seq_no')*10))"}}, "keyword": "action", "name": "call_service", "number": 5, "provider": "workato_service", "skip": false}], "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"84057fa4\",\"path\":[\"list\"]}')}"}, "keyword": "foreach", "name": "", "number": 4, "provider": "", "repeat_mode": null, "skip": false, "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"84057fa4\",\"path\":[\"list\"]}')}"}, {"as": "", "block": [{"as": "5ed86f4a", "block": [], "input": {"flow_id": "45178306", "request": {"secs": "=_('data.logger.f33691f6.message').to_i-((now-_('data.workato.job_context.job_created_at')).to_i-_('data.workato_list.84057fa4.list.first.____Size', 'list_meta', '____Size', 'data.workato_list.84057fa4.list')*10)"}}, "keyword": "action", "name": "call_service", "number": 7, "provider": "workato_service", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"f33691f6\",\"path\":[\"message\"]}')}", "operand": "greater_than", "rhs": "0"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 6, "provider": "", "skip": false}, {"as": "3a2a1647", "block": [], "input": {"reply": {"secs_waited": "=(now-_('data.workato.job_context.job_created_at'))"}, "reply_type": "success"}, "keyword": "action", "name": "send_reply", "number": 8, "provider": "workato_service", "skip": false}], "input": {"reply_schema_json": "[{\"name\":\"secs_waited\",\"type\":\"number\",\"optional\":false,\"control_type\":\"number\"}]", "request_schema_json": "[{\"name\":\"Secs\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\"}]", "service_name": "Flexi Idler"}, "keyword": "trigger", "name": "receive_request", "number": 1, "provider": "workato_service", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (LOG_STEP_AS, "logger", "log_message"),
    (CREATE_LIST_STEP_AS, "workato_list", "create_list"),
    (CHUNK_CALL_AS, "workato_service", "call_service"),
    (REMAINDER_CALL_AS, "workato_service", "call_service"),
    (REPLY_STEP_AS, "workato_service", "send_reply"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.log_message",
    "workato_runtime.create_list",
    "workato_service.call_service",
    "workato_service.send_reply",
]
ALLOWED_TOOLS: list[str] = [
    "workato_service.call_service",
    "workato_service.send_reply",
]
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "call_service_step_as",
    "create_list_size",
    "reply",
)
_CHUNK_SECS_FORMULA = (
    "=10-(((now-_('data.workato.job_context.job_created_at')).to_i+10)"
    "-(_('data.foreach.95c0de6f.seq_no')*10))"
)
_REMAINDER_SECS_FORMULA = (
    "=_('data.logger.f33691f6.message').to_i-((now-_('data.workato.job_context"
    ".job_created_at')).to_i-_('data.workato_list.84057fa4.list.first.____Size',"
    " 'list_meta', '____Size', 'data.workato_list.84057fa4.list')*10)"
)
_SECS_WAITED_FORMULA = "=(now-_('data.workato.job_context.job_created_at'))"


def validate_88676116(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    if str((raw.get("input") or {}).get("service_name") or "") != SERVICE_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} service name changed")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    # Twin-drift guard: both call_service steps must target THIS recipe's
    # sub-flow (the 89454478 twin differs only here).
    calls = [
        node for node in _walk_nodes(raw)
        if node.get("provider") == "workato_service" and node.get("name") == "call_service"
    ]
    if len(calls) != 2:
        raise RuntimeError(f"recipe {RECIPE_ID} expected exactly 2 call_service steps")
    for node in calls:
        flow = str((node.get("input") or {}).get("flow_id") or "")
        if flow != FLOW_ID:
            raise RuntimeError(
                f"recipe {RECIPE_ID} call_service step {node.get('as')!r} targets flow "
                f"{flow!r}, expected {FLOW_ID!r} (twin drift?)"
            )
    # Semantic pins on the drift-prone formulas (the tree pin holds the exact
    # bytes; these guards name the trap when one changes).
    by_as = {str(node.get("as") or ""): node for node in _walk_nodes(raw)}
    chunk_secs = str(((by_as[CHUNK_CALL_AS].get("input") or {}).get("request") or {}).get("secs") or "")
    if chunk_secs != _CHUNK_SECS_FORMULA:
        raise RuntimeError(f"recipe {RECIPE_ID} chunk secs formula changed: {chunk_secs!r}")
    remainder_secs = str(((by_as[REMAINDER_CALL_AS].get("input") or {}).get("request") or {}).get("secs") or "")
    if remainder_secs != _REMAINDER_SECS_FORMULA:
        raise RuntimeError(f"recipe {RECIPE_ID} remainder secs formula changed: {remainder_secs!r}")
    reply_input = (by_as[REPLY_STEP_AS].get("input") or {}).get("reply") or {}
    if str(reply_input.get("secs_waited") or "") != _SECS_WAITED_FORMULA:
        raise RuntimeError(f"recipe {RECIPE_ID} secs_waited formula changed")
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "service_name": SERVICE_NAME,
        "flow_id": FLOW_ID,
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


def seed_88676116(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88676116(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    now, job_context = _require_pinned_clock(data)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["workato_service_replies"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the workato_service_replies "
            f"section; got {sorted(seed_in.keys())}"
        )
    _require_replies(seed_in["workato_service_replies"])
    expect = data.get("expect")
    _require_expect_shape(expect)
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
        "now": now,
        "job_context": deepcopy(job_context),
        "workato_service_replies": deepcopy(seed_in["workato_service_replies"]),
        "expect": deepcopy(expect),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_88676116(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88676116(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not str(seed.get("now") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing pinned now")
    if not isinstance(seed.get("job_context"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing job_context")
    if not isinstance(seed.get("workato_service_replies"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_service_replies")
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
            # No persistent backends (logger/list/service replies are all
            # in-run mock state): nothing to snapshot, nothing to clean up.
            "initial_snapshot": {},
            "final_snapshot": {},
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_88676116(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def verify_88676116(result: dict[str, Any]) -> dict[str, Any]:
    # Kept in lockstep with this recipe's registered shared verifier (the
    # batch-05 authoring fragment was merged there; edit both together).
    replay = _verify_replay_recipe(result)
    details = result.get("details") or {}
    expect = details.get("expect") if isinstance(details.get("expect"), dict) else {}
    raw_execution = details.get("raw_execution") if isinstance(details.get("raw_execution"), dict) else {}
    trace = raw_execution.get("trace") if isinstance(raw_execution.get("trace"), list) else []
    checks = list(replay.get("checks") or [])

    required_keys = (
        "executed_action_count",
        "tools",
        "tool_expectations",
        "call_service_step_as",
        "create_list_size",
        "reply",
    )
    missing = [key for key in required_keys if key not in expect]
    checks.append(_check(
        "expect_carries_all_88676116_ground_truth_keys",
        not missing,
        {"missing": missing, "expect_keys": sorted(expect.keys())},
    ))

    # The per-call step ids prove BOTH the foreach iteration count and the
    # IF-6 branch: a 0-remainder phantom call would ask for the same secs as
    # the last chunk call (size*10-delta), so args alone cannot distinguish
    # '664a521c' from '5ed86f4a'.
    expected_step_as = expect.get("call_service_step_as")
    actual_step_as = [
        str(row.get("as") or "")
        for row in trace
        if isinstance(row, dict) and row.get("tool") == "workato_service.call_service"
    ]
    checks.append(_check(
        "call_service_step_sequence_proves_foreach_and_if_branch",
        isinstance(expected_step_as, list) and actual_step_as == expected_step_as,
        {"expected": expected_step_as, "actual": actual_step_as},
    ))

    create_rows = [
        row for row in trace
        if isinstance(row, dict) and row.get("tool") == "workato_runtime.create_list"
    ]
    actual_size = (create_rows[0].get("args") or {}).get("size") if create_rows else None
    checks.append(_check(
        "create_list_size_matches_chunk_count",
        len(create_rows) == 1 and actual_size == expect.get("create_list_size"),
        {"expected": expect.get("create_list_size"), "actual": actual_size,
         "create_rows": len(create_rows)},
    ))

    # OPTIONAL pin: only variants whose logger rendering is Ruby-faithful
    # (remainder != 0) carry log_messages. Engine gap (batch-05, reported):
    # resolve_text str(resolved or "") renders integer 0 as '' where Ruby
    # renders '0' -- never pin the deviant '' rendering.
    if "log_messages" in expect:
        actual_logs = [
            (row.get("args") or {}).get("message")
            for row in trace
            if isinstance(row, dict) and row.get("tool") == "workato_runtime.log_message"
        ]
        checks.append(_check(
            "logger_messages_match_engine_canonical_rendering",
            actual_logs == expect.get("log_messages"),
            {"expected": expect.get("log_messages"), "actual": actual_logs},
        ))

    checks.append(_check(
        "service_reply_return_value_matches",
        raw_execution.get("return_value") == expect.get("reply"),
        {"expected": expect.get("reply"), "actual": raw_execution.get("return_value")},
    ))
    return {"ok": all(check["ok"] for check in checks), "checks": checks}


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != ["request"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the request object; "
            f"got {sorted(trigger.keys())}"
        )
    request = trigger.get("request")
    if not isinstance(request, dict) or sorted(request.keys()) != ["Secs"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.request must be exactly {{'Secs': <int>}}"
        )
    secs = request.get("Secs")
    if isinstance(secs, bool) or not isinstance(secs, int) or secs < 0:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger request.Secs must be a non-negative JSON integer "
            f"(the trigger schema declares integer_conversion); got {secs!r}"
        )


def _require_pinned_clock(data: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    now = data.get("now")
    job_context = data.get("job_context")
    if not isinstance(job_context, dict) or sorted(job_context.keys()) != ["job_created_at"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input requires job_context = "
            "{'job_created_at': <ISO datetime>} (three formulas read the now-delta)"
        )
    parsed: dict[str, datetime.datetime] = {}
    for label, value in (("now", now), ("job_context.job_created_at", job_context["job_created_at"])):
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"recipe {RECIPE_ID} {label} must be a non-empty ISO string")
        try:
            stamp = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise RuntimeError(f"recipe {RECIPE_ID} {label} is not ISO-8601: {value!r}") from exc
        if stamp.tzinfo is None:
            raise RuntimeError(f"recipe {RECIPE_ID} {label} must carry an explicit UTC offset")
        if stamp.microsecond:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {label} must be whole-second (the recipe arithmetic "
                f"pins integer second deltas); got {value!r}"
            )
        parsed[label] = stamp
    delta = (parsed["now"] - parsed["job_context.job_created_at"]).total_seconds()
    if delta < 0:
        raise RuntimeError(
            f"recipe {RECIPE_ID} now must not precede job_created_at (delta {delta}s)"
        )
    return str(now), job_context


def _require_replies(replies: Any) -> None:
    if not isinstance(replies, dict) or sorted(replies.keys()) != sorted([CHUNK_CALL_AS, REMAINDER_CALL_AS]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_service_replies must be keyed by exactly "
            f"the two call_service step ids {[CHUNK_CALL_AS, REMAINDER_CALL_AS]!r}"
        )
    for step_as, reply in replies.items():
        if (
            not isinstance(reply, dict)
            or sorted(reply.keys()) != ["success"]
            or not isinstance(reply.get("success"), bool)
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} reply for step {step_as!r} must be exactly "
                f"{{'success': <bool>}} (the sub-recipe reply schema); got {reply!r}"
            )


def _require_expect_shape(expect: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    tools = expect.get("tools")
    items = expect.get("tool_expectations")
    if not isinstance(tools, list) or not isinstance(items, list) or len(tools) != len(items):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools and expect.tool_expectations must be lists "
            "of equal length (strict scorability: one value-pinned item per call)"
        )
    for idx, item in enumerate(items):
        if not isinstance(item, dict) or item.get("tool") not in ALLOWED_TOOLS:
            raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[{idx}] has an invalid tool")
        if not isinstance(item.get("args_contains"), dict) or not item["args_contains"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] must pin values via "
                "args_contains (strict scorability policy)"
            )
    step_as = expect.get("call_service_step_as")
    if not isinstance(step_as, list) or any(
        value not in (CHUNK_CALL_AS, REMAINDER_CALL_AS) for value in step_as
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.call_service_step_as must list the call_service "
            f"step ids in call order (only {CHUNK_CALL_AS!r}/{REMAINDER_CALL_AS!r})"
        )
    if "log_messages" in expect and (
        not isinstance(expect["log_messages"], list)
        or not all(isinstance(msg, str) for msg in expect["log_messages"])
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.log_messages must be a list of strings")


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
