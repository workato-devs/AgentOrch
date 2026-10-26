from __future__ import annotations

import datetime
import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_92330852


RECIPE_ID = "92330852"
SEED_TYPE = "flexi_idler_dp_variant"
TRACK = "workato_service_flexi_idler"
TRIGGER_PROVIDER = "workato_service"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "c5e63d24"
SERVICE_NAME = "Flexi Idler"
BASE_TIMER_FLOW_ID = "46919727"
LOG_STEP_AS = "f33691f6"
LIST_STEP_AS = "84057fa4"
FOREACH_AS = "95c0de6f"
CHUNK_CALL_AS = "664a521c"
REMAINDER_CALL_AS = "5ed86f4a"
REPLY_STEP_AS = "3a2a1647"


_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "c5e63d24",
  "provider": "workato_service",
  "name": "receive_request",
  "skip": false,
  "input": {
   "reply_schema_json": "[{\"name\":\"secs_waited\",\"type\":\"number\",\"optional\":false,\"control_type\":\"number\"}]",
   "request_schema_json": "[{\"name\":\"Secs\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\"}]",
   "service_name": "Flexi Idler"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "f33691f6",
  "provider": "logger",
  "name": "log_message",
  "skip": false,
  "input": {
   "message": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"c5e63d24\",\"path\":[\"request\",\"Secs\"]}')%10"
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "84057fa4",
  "provider": "workato_list",
  "name": "create_list",
  "skip": false,
  "input": {
   "size": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"c5e63d24\",\"path\":[\"request\",\"Secs\"]}')/10).to_i"
  }
 },
 {
  "keyword": "foreach",
  "number": 4,
  "as": "95c0de6f",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"84057fa4\",\"path\":[\"list\"]}')}"
  },
  "repeat_mode": null,
  "batch_size": null,
  "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"84057fa4\",\"path\":[\"list\"]}')}"
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "664a521c",
  "provider": "workato_service",
  "name": "call_service",
  "skip": false,
  "input": {
   "flow_id": "46919727",
   "request": {
    "secs": "=10-(((now-_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_created_at\"]}')).to_i+10)-(_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"95c0de6f\",\"path\":[\"seq_no\"]}')*10))"
   }
  }
 },
 {
  "keyword": "if",
  "number": 6,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"f33691f6\",\"path\":[\"message\"]}')}",
     "operand": "greater_than",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 7,
  "as": "5ed86f4a",
  "provider": "workato_service",
  "name": "call_service",
  "skip": false,
  "input": {
   "flow_id": "46919727",
   "request": {
    "secs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"f33691f6\",\"path\":[\"message\"]}').to_i-((now-_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_created_at\"]}')).to_i-_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"84057fa4\",\"path\":[\"list\",{\"path_element_type\":\"size\"}]}')*10)"
   }
  }
 },
 {
  "keyword": "action",
  "number": 8,
  "as": "3a2a1647",
  "provider": "workato_service",
  "name": "send_reply",
  "skip": false,
  "input": {
   "reply": {
    "secs_waited": "=(now-_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_created_at\"]}'))"
   },
   "reply_type": "success"
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

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
EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "log_message",
    "list_size",
    "chunk_call_secs",
    "remainder_call_secs",
    "reply",
)
SEED_SECTIONS = {"job_context", "workato_service_replies"}


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
    if node.get("keyword") == "foreach":
        pin["repeat_mode"] = node.get("repeat_mode")
        pin["batch_size"] = node.get("batch_size")
        pin["source"] = node.get("source")
    if isinstance(node.get("filter"), dict):
        pin["filter"] = node["filter"]
    out = [pin]
    for child in node.get("block") or []:
        if isinstance(child, dict):
            out.extend(_structure(child))
    return out


def validate_92330852(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if (raw.get("input") or {}).get("service_name") != SERVICE_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} service_name changed")
    actual = _structure(raw)
    if len(actual) != len(STRUCTURE_PINS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} node count changed: {len(actual)} != {len(STRUCTURE_PINS)}"
        )
    for idx, (got, expected) in enumerate(zip(actual, STRUCTURE_PINS)):
        if got != expected:
            raise RuntimeError(
                f"recipe {RECIPE_ID} node {idx} (step {expected.get('number')}) changed:\n"
                f"expected: {json.dumps(expected, sort_keys=True)}\n"
                f"actual:   {json.dumps(got, sort_keys=True)}"
            )
    actions = [pin for pin in actual if pin["keyword"] == "action"]
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "service_name": SERVICE_NAME,
        "base_timer_flow_id": BASE_TIMER_FLOW_ID,
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


def _pinned_epoch(label: str, value: Any) -> int:
    if value in (None, ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires a pinned {label} (the recipe reads now "
            "and job_context.job_created_at)"
        )
    parsed = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise RuntimeError(f"recipe {RECIPE_ID} {label} must carry timezone information")
    return int(parsed.timestamp())


def _require_secs(trigger: dict[str, Any]) -> int:
    if set(trigger) != {"request"} or not isinstance(trigger.get("request"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'request': {{...}}}}"
        )
    request = trigger["request"]
    if set(request) != {"Secs"}:
        raise RuntimeError(f"recipe {RECIPE_ID} request must declare exactly Secs")
    secs = request["Secs"]
    if isinstance(secs, bool) or not (
        isinstance(secs, int) or (isinstance(secs, str) and secs.isdigit())
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} request.Secs must be a non-negative integer or digit "
            f"string: {secs!r}"
        )
    return int(secs)


def _require_expect(expect: Any, secs: int, delta: int) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    list_size = expect.get("list_size")
    chunk_secs = expect.get("chunk_call_secs")
    remainder = expect.get("remainder_call_secs")
    if list_size != secs // 10:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.list_size must equal Secs//10 "
            f"({expect.get('list_size')!r} != {secs // 10})"
        )
    if not isinstance(chunk_secs, list) or len(chunk_secs) != list_size:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.chunk_call_secs must list one rendered secs "
            f"string per chunk call ({list_size} expected): {chunk_secs!r}"
        )
    if (remainder is not None) != (secs % 10 > 0):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.remainder_call_secs must be non-null exactly "
            f"when Secs%10 > 0 (Secs {secs}): {remainder!r}"
        )
    calls = list_size + (1 if remainder is not None else 0)
    if expect.get("executed_action_count") != 3 + calls:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.executed_action_count must be 3 + calls "
            f"(log, create_list, {calls} call_service, send_reply)"
        )
    reply = expect.get("reply")
    if not isinstance(reply, dict) or reply.get("reply") != {"secs_waited": delta}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.reply.reply.secs_waited must equal the pinned "
            f"now - job_created_at delta ({delta}): {reply!r}"
        )


def seed_92330852(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_92330852(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    secs = _require_secs(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - SEED_SECTIONS)
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    job_context = seed_in.get("job_context")
    if not isinstance(job_context, dict) or set(job_context) != {"job_created_at"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.job_context must be exactly {{'job_created_at': ...}}"
        )
    now_epoch = _pinned_epoch("now", data.get("now"))
    created_epoch = _pinned_epoch("job_context.job_created_at", job_context.get("job_created_at"))
    delta = now_epoch - created_epoch
    if delta < 0:
        raise RuntimeError(f"recipe {RECIPE_ID} pinned now must not precede job_created_at")
    replies = seed_in.get("workato_service_replies")
    if not isinstance(replies, dict) or set(replies) != {CHUNK_CALL_AS, REMAINDER_CALL_AS}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_service_replies must key exactly "
            f"{sorted((CHUNK_CALL_AS, REMAINDER_CALL_AS))} (fail-fast call_service replies)"
        )
    for step_as, reply in replies.items():
        if not isinstance(reply, dict):
            raise RuntimeError(
                f"recipe {RECIPE_ID} workato_service_replies[{step_as!r}] must be an object"
            )
    _require_expect(data.get("expect"), secs, delta)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "now": data["now"],
        "job_context": deepcopy(job_context),
        "workato_service_replies": deepcopy(replies),
        "expect": deepcopy(data["expect"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_92330852(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_92330852(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
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
            "now": seed.get("now"),
            "job_context": seed.get("job_context"),
            "expect": expect,
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_92330852(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
