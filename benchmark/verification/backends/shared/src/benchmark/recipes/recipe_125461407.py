from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_125461407


RECIPE_ID = "125461407"
SEED_TYPE = "pub_sub_agentic_error_slack_alert_variant"
TRACK = "workato_pub_sub_agentic_error_slack_alert"
TRIGGER_PROVIDER = "workato_pub_sub"
TRIGGER_NAME = "subscribe_to_topic"
TRIGGER_AS = "dc957003"
TOPIC_ID = "49960"
ACCOUNT_PROPERTY = "Agentic.error.channel"
POST_STEP_AS = "edf02c48"
MESSAGE_FIELDS = (
    "job_id",
    "job_url",
    "conversation_id",
    "skill_name",
    "error",
    "genie",
    "tags",
    "recipe_name",
    "error_channel",
)
REQUIRED_NON_BLANK = ("error", "recipe_name")

# workato_pub_sub.subscribe_to_topic (as dc957003, topic 49960 'Agentic |
# Errors', since_offset -3600). Body:
#   2  declare_list f9b72e2e 'Fields' (item schema name/value)
#   3  IF message.conversation_id present -> 4 insert_to_list ecc2e786
#      {name 'Conversation ID', value message.conversation_id}
#   5  IF message.skill_name present -> 6 insert_to_list 37102d1a
#      {name 'Skill', value message.skill_name}
#   7  IF message.tags present -> 8 insert_to_list b61832fa
#      {name 'Tags', value message.tags}
#   9  IF message.job_id present AND message.job_url present (compound AND)
#      -> 10 insert_to_list c47fbcde {name 'Job', value '<job_url|job_id>'}
#   11 slack_bot.post_bot_message edf02c48 (LIVE slack):
#      channel = message.error_channel.presence ||
#                account_property 'Agentic.error.channel'
#      message pretext '*Error in Recipe `recipe_name`*',
#      title '::  Error Details  ::',
#      attachment_text 'error\n***************************', color danger;
#      attachment_fields ____source = f9b72e2e.list_items
#      (title = item.name / value = item.value).
#
# Branch mapping (per benmark_rules):
# - variant_00 full_payload_explicit_channel: all four IFs true; error_channel
#   non-blank -> the .presence arm wins. The account property is deliberately
#   NOT seeded: the engine's `a.presence || b` is lazy (probed), so an eager
#   property read would fail loudly here. 6 actions; 4 field lines.
# - variant_01 minimal_property_fallback: conversation_id/skill_name/tags
#   blank -> IFs 3/5/7 false; job pair present -> IF 9 true; error_channel ''
#   -> account_property fallback (seeded). 3 actions; only the Job field line.
# - variant_02 job_pair_incomplete: job_id present but job_url blank -> the
#   compound AND of IF 9 is false; skill_name present -> IF 5 true. Explicit
#   channel again (property unseeded). 3 actions; only the Skill field line.
# - variant_03 tags_and_conversation_only: conversation_id + tags present,
#   skill_name blank, job_url present but job_id blank (IF 9 false via its
#   FIRST condition). Property fallback channel. 4 actions; Conversation ID +
#   Tags field lines.
#
# Live isolation: the resolved channel never starts with 'U', so the executor
# routes the post to SLACK_CHANNEL_OVERRIDE regardless of which formula arm
# won (raw_executor.slack_post_message); the variant's channel_source is
# asserted structurally (error_channel blank vs non-blank + property seeding).
# slack_text render order is pinned verbatim in expect.slack_text: pretext,
# title, attachment_text, then one 'Name: value' line per inserted field.
# No cleanup: an ordinary Slack post that is never re-read, and the Fields
# list / pub-sub trigger are per-run Workato-internal state (cleanup
# principle: no persistent state affects reruns).

_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "dc957003",
  "provider": "workato_pub_sub",
  "name": "subscribe_to_topic",
  "skip": false,
  "input": {
   "since_offset": "-3600",
   "topic_id": "49960"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "f9b72e2e",
  "provider": "workato_variable",
  "name": "declare_list",
  "skip": false,
  "input": {
   "list_item_schema_json": "[{\"name\":\"name\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Name\"},{\"name\":\"value\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Value\"}]",
   "name": "Fields"
  }
 },
 {
  "keyword": "if",
  "number": 3,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"conversation_id\"]}')}",
     "operand": "present",
     "rhs": ""
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "ecc2e786",
  "provider": "workato_variable",
  "name": "insert_to_list",
  "skip": false,
  "input": {
   "list_item": {
    "name": "Conversation ID",
    "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"conversation_id\"]}')}"
   },
   "location": "end",
   "name": "29b6fc31-61a0-4704-be59-89988e5a4f90:f9b72e2e"
  }
 },
 {
  "keyword": "if",
  "number": 5,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"skill_name\"]}')}",
     "operand": "present",
     "rhs": ""
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 6,
  "as": "37102d1a",
  "provider": "workato_variable",
  "name": "insert_to_list",
  "skip": false,
  "input": {
   "list_item": {
    "name": "Skill",
    "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"skill_name\"]}')}"
   },
   "location": "end",
   "name": "29b6fc31-61a0-4704-be59-89988e5a4f90:f9b72e2e"
  }
 },
 {
  "keyword": "if",
  "number": 7,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"tags\"]}')}",
     "operand": "present",
     "rhs": ""
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 8,
  "as": "b61832fa",
  "provider": "workato_variable",
  "name": "insert_to_list",
  "skip": false,
  "input": {
   "list_item": {
    "name": "Tags",
    "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"tags\"]}')}"
   },
   "location": "end",
   "name": "29b6fc31-61a0-4704-be59-89988e5a4f90:f9b72e2e"
  }
 },
 {
  "keyword": "if",
  "number": 9,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"job_id\"]}')}",
     "operand": "present",
     "rhs": ""
    },
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"job_url\"]}')}",
     "operand": "present",
     "rhs": ""
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 10,
  "as": "c47fbcde",
  "provider": "workato_variable",
  "name": "insert_to_list",
  "skip": false,
  "input": {
   "list_item": {
    "name": "Job",
    "value": "<#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"job_url\"]}')}|#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"job_id\"]}')}>"
   },
   "location": "end",
   "name": "29b6fc31-61a0-4704-be59-89988e5a4f90:f9b72e2e"
  }
 },
 {
  "keyword": "action",
  "number": 11,
  "as": "edf02c48",
  "provider": "slack_bot",
  "name": "post_bot_message",
  "skip": false,
  "input": {
   "attachment_fields": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"f9b72e2e\",\"path\":[\"list_items\"]}')}",
    "title": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"f9b72e2e\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"name\"]}')}",
    "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"f9b72e2e\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"value\"]}')}"
   },
   "channel": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\",\"error_channel\"]}').presence || _dp('{\"pill_type\":\"account_property\",\"property_name\":\"Agentic.error.channel\"}')",
   "message": {
    "attachment_text": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"error\"]}')}\n***************************",
    "color": "danger",
    "pretext": "*Error in Recipe `#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"recipe_name\"]}')}`*",
    "title": "::  Error Details  ::"
   }
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_list",
    "workato_runtime.insert_to_list",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "slack.post_message",
]
EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "trace_tools",
    "slack_text",
    "channel_source",
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


def validate_125461407(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger 'as' changed: {raw.get('as')!r}")
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


def seed_125461407(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_125461407(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"account_properties"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    expect = data.get("expect")
    _require_expect_shape(expect)
    _require_channel_consistency(trigger, seed_in, expect)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": deepcopy(expect),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if "account_properties" in seed_in:
        out["account_properties"] = deepcopy(seed_in["account_properties"])
    return attach_variant(out, ctx)


def run_125461407(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_125461407(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    details["raw_execution"] = raw_execution
    details["ground_truth"] = _ground_truth(raw_execution)
    # Cleanup per the cleanup principle: the Slack post is an ordinary message
    # that is never re-read, deleted, updated, or verified live afterwards,
    # and the Fields list / pub-sub payload are per-run Workato-internal
    # state -- no persistent state can affect a rerun, so no cleanup step.
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_125461407(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {"message"} or not isinstance(trigger.get("message"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input must be exactly {{'message': {{...}}}}")
    message = trigger["message"]
    if set(message) != set(MESSAGE_FIELDS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger message must declare exactly the topic schema fields "
            f"{sorted(MESSAGE_FIELDS)} (blank '' = absent semantics); got {sorted(message)}"
        )
    for key, value in message.items():
        if not isinstance(value, str):
            raise RuntimeError(f"recipe {RECIPE_ID} trigger message field {key!r} must be a string")
    for key in REQUIRED_NON_BLANK:
        if not message[key].strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger message field {key!r} must be non-blank "
                "(the alert text interpolates it unconditionally)"
            )


def _require_expect_shape(expect: Any) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if expect.get("channel_source") not in ("message", "account_property"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.channel_source must be 'message' or 'account_property'"
        )


def _require_channel_consistency(
    trigger: dict[str, Any], seed_in: dict[str, Any], expect: dict[str, Any]
) -> None:
    error_channel = str(trigger["message"].get("error_channel") or "")
    source = expect.get("channel_source")
    if source == "message":
        if not error_channel.strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} channel_source 'message' requires a non-blank "
                "message.error_channel"
            )
        if "account_properties" in seed_in:
            raise RuntimeError(
                f"recipe {RECIPE_ID} channel_source 'message' variants must NOT seed "
                "account_properties: the || fallback is lazy and the unused property "
                "would be dead seed state"
            )
        return
    if error_channel.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} channel_source 'account_property' requires a blank "
            "message.error_channel"
        )
    properties = seed_in.get("account_properties")
    if not isinstance(properties, dict) or not str(properties.get(ACCOUNT_PROPERTY) or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} channel_source 'account_property' requires "
            f"seed.account_properties[{ACCOUNT_PROPERTY!r}] (the pill is fail-fast when unseeded)"
        )


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
