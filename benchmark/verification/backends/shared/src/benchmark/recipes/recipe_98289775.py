from __future__ import annotations

import datetime
import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_98289775


RECIPE_ID = "98289775"
SEED_TYPE = "clock_marketo_export_activity_window_publish_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "2c9e2a88"
DECLARE_AS = "4d7f476d"
DECLARE_NUMBER = 2
PUBLISH_AS = "4c4f4c33"
PUBLISH_NUMBER = 3
TOPIC_ID = "29180"
ACTIVITY_TYPE_IDS = 46
_WINDOW_RENDER = "%Y-%m-%dT%H:%M:%S+00:00"


_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "2c9e2a88",
  "provider": "clock",
  "name": "scheduled_event",
  "skip": false,
  "input": {
   "cron_expression": "0 10 * * *",
   "time_unit": "custom_schedule",
   "timezone": "Etc/UTC"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "4d7f476d",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "activityTypeIds": "=46",
     "endAt": "=(_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_created_at\"]}').in_time_zone(\"UTC\"))",
     "startAt": "=(_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_created_at\"]}').in_time_zone(\"UTC\") - 2.days)"
    },
    "schema": "[{\"name\":\"startAt\",\"type\":\"string\",\"optional\":true,\"label\":\"startAt\",\"control_type\":\"text\"},{\"name\":\"endAt\",\"type\":\"string\",\"optional\":true,\"label\":\"endAt\",\"control_type\":\"text\"},{\"name\":\"activityTypeIds\",\"type\":\"string\",\"optional\":true,\"label\":\"activityTypeIds\",\"control_type\":\"text\"}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "4c4f4c33",
  "provider": "workato_pub_sub",
  "name": "publish_to_topic",
  "skip": false,
  "input": {
   "message": {
    "activityTypeIds": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"4d7f476d\",\"path\":[\"activityTypeIds\"]}')",
    "endAt": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"4d7f476d\",\"path\":[\"endAt\"]}')}",
    "startAt": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"4d7f476d\",\"path\":[\"startAt\"]}')}"
   },
   "topic_id": "29180"
  }
 }
]"""
STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "workato_pub_sub.publish_to_topic",
]
ALLOWED_TOOLS: list[str] = ["workato_pub_sub.publish_to_topic"]
REQUIRED_EXPECT_KEYS = (
    "branch",
    "executed_action_count",
    "raw_executed_action_count",
    "trace_tools",
    "tools",
    "tool_expectations",
    "declared",
    "published_message",
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


def validate_98289775(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
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
    # Semantic pins on the drift-prone load-bearing pieces.
    declare = next(pin for pin in actual if pin["as"] == DECLARE_AS)
    data = ((declare["input"] or {}).get("variables") or {}).get("data") or {}
    if data.get("activityTypeIds") != "=46":
        raise RuntimeError(f"recipe {RECIPE_ID} activityTypeIds literal changed: {data!r}")
    for key, needle in (("startAt", "- 2.days"), ("endAt", '.in_time_zone("UTC")')):
        if needle not in str(data.get(key) or "") or '"job_created_at"' not in str(
            data.get(key) or ""
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} {key} formula lost its job_created_at "
                f".in_time_zone(\"UTC\") window arithmetic: {data.get(key)!r}"
            )
    publish = next(pin for pin in actual if pin["as"] == PUBLISH_AS)
    if str((publish["input"] or {}).get("topic_id")) != TOPIC_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} publish topic changed")
    actions = [pin for pin in actual if pin["keyword"] == "action" and not pin["skip"]]
    if [(pin["provider"], pin["name"]) for pin in actions] != [
        ("workato_variable", "declare_variable"),
        ("workato_pub_sub", "publish_to_topic"),
    ]:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "topic_id": TOPIC_ID,
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


def _require_job_context(data: dict[str, Any]) -> str:
    job_context = data.get("job_context")
    if (
        not isinstance(job_context, dict)
        or sorted(job_context.keys()) != ["job_created_at"]
        or not isinstance(job_context.get("job_created_at"), str)
        or not job_context["job_created_at"].strip()
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must declare job_context "
            "{{'job_created_at': <ISO datetime>}} — both window formulas read it and "
            "the plain .in_time_zone chain raises on nil (that raise is NOT a recipe "
            "branch)"
        )
    value = job_context["job_created_at"]
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(
            f"recipe {RECIPE_ID} job_created_at must be an ISO datetime: {value!r}"
        ) from exc
    if parsed.tzinfo is None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} job_created_at must carry an explicit offset (the "
            f"in_time_zone('UTC') normalization is the recipe's observable): {value!r}"
        )
    if parsed.microsecond:
        raise RuntimeError(
            f"recipe {RECIPE_ID} job_created_at must be whole-second (fractional "
            f"seconds would make the pinned render ambiguous): {value!r}"
        )
    return value


def _derive_window(job_created_at: str) -> dict[str, Any]:
    """Mirror the declare formulas exactly (re-probed 2026-07-09 via
    resolve_value on the verbatim raw strings): UTC normalization renders
    'YYYY-MM-DDTHH:MM:SS+00:00', startAt is the same instant minus 2 days,
    activityTypeIds is the native int 46."""
    parsed = datetime.datetime.fromisoformat(job_created_at.replace("Z", "+00:00"))
    end = parsed.astimezone(datetime.timezone.utc)
    start = end - datetime.timedelta(days=2)
    return {
        "activityTypeIds": ACTIVITY_TYPE_IDS,
        "endAt": end.strftime(_WINDOW_RENDER),
        "startAt": start.strftime(_WINDOW_RENDER),
    }


def _require_expect_shape(expect: Any, derived: dict[str, Any]) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    checks = (
        expect.get("executed_action_count") == len(ALLOWED_TOOLS),
        expect.get("raw_executed_action_count") == 2,
        expect.get("trace_tools") == EXPECTED_RAW_TOOLS,
        expect.get("tools") == ALLOWED_TOOLS,
        expect.get("declared") == derived,
        expect.get("published_message") == derived,
        expect.get("tool_expectations")
        == [
            {
                "tool": "workato_pub_sub.publish_to_topic",
                "args_contains": {"topic_id": TOPIC_ID, "message": derived},
            }
        ],
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with the derived ground "
            f"truth {json.dumps(derived, sort_keys=True)} (the publish message equals "
            f"the declared window verbatim, activityTypeIds stays the INT 46): {expect!r}"
        )


def seed_98289775(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_98289775(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} — the clock "
            f"trigger is payload-less and no trigger pill is ever dereferenced: "
            f"{trigger!r}"
        )
    job_created_at = _require_job_context(data)
    if data.get("seed") not in (None, {}):
        raise RuntimeError(
            f"recipe {RECIPE_ID} owns no backend state (clock -> declare -> publish, "
            f"all Workato-internal): the variant input must not declare seed sections; "
            f"got {data.get('seed')}"
        )
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: a forced action error would fail the "
            "whole run instead of exercising a recipe branch"
        )
    _require_expect_shape(data.get("expect"), _derive_window(job_created_at))
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "job_context": deepcopy(data["job_context"]),
        "expect": deepcopy(data["expect"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_98289775(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_98289775(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("job_context"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing job_context")
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
            "job_context": seed.get("job_context"),
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_98289775(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
