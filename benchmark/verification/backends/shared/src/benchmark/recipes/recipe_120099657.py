from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import date
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_120099657


RECIPE_ID = "120099657"
SEED_TYPE = "newhire_startdate_change_review_variant"
TRACK = "live_slack_newhire_startdate_change"
TRIGGER_AS = "be5b34bf"
DECLARE_AS = "17e411b2"
REPLY_AS = "bd3a37a3"
LOOKUP_AS = "be887438"
POST_AS = "44ad1551"
ANON_EMAIL = "<anon>sarah.miller@company.com</anon>"
PARAM_KEYS = (
    "personal_email",
    "adjusted_start_date",
    "new_hire_name",
    "entity_id",
    "requester_email",
    "date_of_original_agreement",
)
MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)

# slack_bot.bot_command_v2 'newhire change startdate' (as be5b34bf; six
# required parameters + context.user/user_email pills). Linear body:
#   2  workato_variable.declare_variable 17e411b2 (MOCK Workato-internal):
#      job_created_at_formatted = parameters.adjusted_start_date
#      .strftime("%d %B %Y") — the ONLY uses of this variable downstream
#      (block attachment_fields + button params) are DROPPED from rendered
#      text by design, so variants pin it via the declare step's traced
#      result (triage note, re-probed 2026-07-08).
#   3  slack_bot.post_bot_reply_v2 bd3a37a3 (LIVE -> env override channel):
#      rendered text = the section_text ONLY ('Your request for adjusting
#      start date for `<new_hire_name>` is being reviewed by <anon>Sarah
#      Miller</anon>.') — block-level attachment_fields are dropped by
#      slack_text (registered 87484821 groundtruth pins the same drop) and
#      the <anon> tag stays verbatim in the live text.
#   4  slack.get_user_by_email be887438 (LIVE users.lookupByEmail): the email
#      is the HARDCODED fictional literal '<anon>sarah.miller@company.com
#      </anon>' -> deterministic users_not_found in EVERY variant (triage
#      probed live: {ok:true, not_found:true, id:null}, no raise).
#   5  slack_bot.post_bot_message 44ad1551 (LIVE): channel = be887438.id pill
#      -> null -> '' -> env override reroute (non-'U' channel routing,
#      re-probed); text = the section_text ('<@user> has requested for an
#      adjusted start date for `<new_hire_name>`.'); the actions block
#      (Approve/Reject buttons) is not rendered into text — same established
#      drop.
#
# Branch mapping: linear, no branches; the only data-dependent behavior is
# the deterministic not_found lookup. Variants pin pill resolution:
# - v0 request_a: offset date_time adjusted_start_date -> '20 July 2026'
# - v1 request_b_diff_date: different month/day + different new_hire_name
# - v2 request_c_date_only_param: date-only '2026-11-03' -> '03 November 2026'
#   (strftime %d zero-pads) + distinct entity_id/requester_email
#
# Backends: slack LIVE only (users.lookupByEmail + chat.postMessage x2, both
# posts to the env override channel). Ordinary posts that nothing later
# reads/updates/deletes -> no cleanup (cleanup principle). To keep the
# strftime derivation unambiguous, seeds must not sit on a UTC date
# boundary (offset instants whose UTC date differs from the written date
# are rejected fail-fast).
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "slack.post_reply",
    "slack_bot.get_user_by_email",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "slack.post_reply",
    "slack_bot.get_user_by_email",
    "slack.post_message",
]
EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "trace_tools",
    "job_created_at_formatted",
    "post_texts",
    "lookup_not_found",
)
_DATE_ONLY_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_DATE_TIME_RE = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|[+-]\d{2}:?\d{2})"
)

_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "be5b34bf",
  "provider": "slack_bot",
  "name": "bot_command_v2",
  "skip": false,
  "input": {
   "allow_dialog": "true",
   "domain": "newhire",
   "name": "change",
   "parameters": "[\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Personal Email\",\n    \"name\": \"personal_email\",\n    \"type\": \"string\",\n    \"optional\": false\n  },\n  {\n    \"control_type\": \"date_time\",\n    \"label\": \"Adjusted Start date\",\n    \"render_input\": \"date_time_conversion\",\n    \"parse_output\": \"date_time_conversion\",\n    \"name\": \"adjusted_start_date\",\n    \"type\": \"date_time\",\n    \"optional\": false\n  },\n  {\n    \"control_type\": \"text\",\n    \"label\": \"New Hire Name\",\n    \"name\": \"new_hire_name\",\n    \"type\": \"string\",\n    \"optional\": false\n  },\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Entity ID\",\n    \"name\": \"entity_id\",\n    \"type\": \"string\",\n    \"optional\": false\n  },\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Requester Email\",\n    \"name\": \"requester_email\",\n    \"type\": \"string\",\n    \"optional\": false\n  },\n  {\n    \"name\": \"date_of_original_agreement\",\n    \"type\": \"date_time\",\n    \"optional\": false,\n    \"control_type\": \"date\"\n  }\n]",
   "scope": "startdate"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "17e411b2",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "job_created_at_formatted": "=_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"be5b34bf\",\"path\":[\"parameters\",\"adjusted_start_date\"]}').strftime(\"%d %B %Y\")"
    },
    "schema": "[{\"name\":\"job_created_at_formatted\",\"type\":\"string\",\"optional\":true,\"label\":\"Job Created At (Formatted)\",\"control_type\":\"text\"}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "bd3a37a3",
  "provider": "slack_bot",
  "name": "post_bot_reply_v2",
  "skip": false,
  "input": {
   "blocks": [
    {
     "attachment_fields": [
      {
       "title": "Adjusted Start Date",
       "value": "`#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"17e411b2\",\"path\":[\"job_created_at_formatted\"]}')}`"
      }
     ],
     "block_type": "section_with_fields",
     "button_type": "continue_flow",
     "section_text": "Your request for adjusting start date for `#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"be5b34bf\",\"path\":[\"parameters\", \"new_hire_name\"]}')}` is being reviewed by <anon>Sarah Miller</anon>."
    }
   ]
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "be887438",
  "provider": "slack",
  "name": "get_user_by_email",
  "skip": false,
  "input": {
   "email": "<anon>sarah.miller@company.com</anon>"
  }
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "44ad1551",
  "provider": "slack_bot",
  "name": "post_bot_message",
  "skip": false,
  "input": {
   "blocks": [
    {
     "attachment_fields": [
      {
       "title": "Adjusted Start Date",
       "value": "`#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"17e411b2\",\"path\":[\"job_created_at_formatted\"]}')}`"
      }
     ],
     "block_type": "section_with_fields",
     "button_type": "continue_flow",
     "section_text": "<@#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"be5b34bf\",\"path\":[\"context\", \"user\"]}')}> has requested for an adjusted start date for `#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"be5b34bf\",\"path\":[\"parameters\", \"new_hire_name\"]}')}`."
    },
    {
     "actions": [
      {
       "bot_command": "18452764",
       "button_title": "Approve",
       "button_type": "continue_flow",
       "params": "personal_email: #{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"be5b34bf\",\"path\":[\"parameters\", \"personal_email\"]}')} name: #{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"be5b34bf\",\"path\":[\"parameters\", \"new_hire_name\"]}')}  adjusted_start_date:#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"17e411b2\",\"path\":[\"job_created_at_formatted\"]}')} type: approve entity_id: #{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"be5b34bf\",\"path\":[\"parameters\", \"entity_id\"]}')} requester_email: #{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"be5b34bf\",\"path\":[\"context\", \"user_email\"]}')} date_of_original_agreement: #{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"be5b34bf\",\"path\":[\"parameters\", \"date_of_original_agreement\"]}')}",
       "style": "primary",
       "type": "button"
      },
      {
       "bot_command": "18452764",
       "button_title": "Reject",
       "button_type": "continue_flow",
       "params": "personal_email: #{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"be5b34bf\",\"path\":[\"parameters\", \"personal_email\"]}')} name: #{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"be5b34bf\",\"path\":[\"parameters\", \"new_hire_name\"]}')}  adjusted_start_date:#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"17e411b2\",\"path\":[\"job_created_at_formatted\"]}')} type: reject entity_id: #{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"be5b34bf\",\"path\":[\"parameters\", \"entity_id\"]}')} requester_email: #{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"be5b34bf\",\"path\":[\"context\", \"user_email\"]}')}",
       "style": "danger",
       "type": "button"
      }
     ],
     "block_type": "actions",
     "button_type": "continue_flow"
    }
   ],
   "channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack\",\"line\":\"be887438\",\"path\":[\"id\"]}')}"
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)


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


def validate_120099657(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
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
        "trigger_provider": "slack_bot",
        "trigger_name": "bot_command_v2",
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


def _formatted_start_date(raw_value: str) -> str:
    """Mirror the recipe's .strftime('%d %B %Y') on the WRITTEN date
    components (re-probed: the engine formats the instant as written for
    date-only, micro-second and colon-less-offset forms alike). Seeds must
    keep the written date stable under UTC conversion so the derivation can
    never be timezone-ambiguous."""
    match = _DATE_TIME_RE.fullmatch(raw_value)
    if match:
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        hour = int(match.group(4))
        offset_text = match.group(7)
        if offset_text != "Z":
            sign = 1 if offset_text.startswith("+") else -1
            digits = offset_text[1:].replace(":", "")
            offset_minutes = sign * (int(digits[:2]) * 60 + int(digits[2:] or "0"))
            utc_minutes = hour * 60 + int(match.group(5)) - offset_minutes
            if not 0 <= utc_minutes < 24 * 60:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} adjusted_start_date {raw_value!r} crosses the "
                    "UTC date boundary — pick an instant whose UTC date equals the "
                    "written date so the strftime pin is unambiguous"
                )
    else:
        match = _DATE_ONLY_RE.fullmatch(raw_value)
        if not match:
            raise RuntimeError(
                f"recipe {RECIPE_ID} adjusted_start_date must be a date or ISO "
                f"date-time string: {raw_value!r}"
            )
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
    date(year, month, day)  # validates the calendar date
    return f"{day:02d} {MONTHS[month - 1]} {year}"


def _require_trigger(trigger: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input requires a parameters object")
    params: dict[str, str] = {}
    for key in PARAM_KEYS:
        value = parameters.get(key)
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger parameters.{key} must be a non-empty string "
                "(all six command parameters are required)"
            )
        params[key] = value
    context = trigger.get("context")
    if not isinstance(context, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input requires a context object")
    ctx_out: dict[str, str] = {}
    for key in ("user", "user_email"):
        value = context.get(key)
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger context.{key} must be a non-empty string"
            )
        ctx_out[key] = value
    if not ctx_out["user"].startswith("U"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} context.user must be a Slack user id (U...) — the "
            f"step-5 mention renders '<@{{user}}>': {ctx_out['user']!r}"
        )
    return params, ctx_out


def _derived_texts(params: dict[str, str], context: dict[str, str]) -> list[str]:
    return [
        f"Your request for adjusting start date for `{params['new_hire_name']}` "
        "is being reviewed by <anon>Sarah Miller</anon>.",
        f"<@{context['user']}> has requested for an adjusted start date for "
        f"`{params['new_hire_name']}`.",
    ]


def _require_expect(expect: Any, formatted: str, texts: list[str]) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    checks = (
        expect.get("executed_action_count") == 4,
        expect.get("trace_tools") == EXPECTED_RAW_TOOLS,
        expect.get("tools") == ALLOWED_TOOLS,
        expect.get("job_created_at_formatted") == formatted,
        expect.get("post_texts") == texts,
        expect.get("lookup_not_found") is True,
        expect.get("tool_expectations")
        == [
            {
                "tool": "slack.post_reply",
                "channel": "override",
                "text_fragments": [texts[0]],
            },
            {
                "tool": "slack_bot.get_user_by_email",
                "args_contains": {"email": ANON_EMAIL},
            },
            {
                "tool": "slack.post_message",
                "channel": "override",
                "text_fragments": [texts[1]],
            },
        ],
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with the derived ground "
            f"truth (formatted {formatted!r}, texts {texts!r}, lookup always "
            f"users_not_found): {expect!r}"
        )


def seed_120099657(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_120099657(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    params, context = _require_trigger(trigger)
    seed_in = data.get("seed")
    if seed_in not in (None, {}):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seeds NO backend state (live Slack posts only; the "
            f"lookup email is a hardcoded fictional literal): {seed_in!r}"
        )
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    formatted = _formatted_start_date(params["adjusted_start_date"])
    _require_expect(data.get("expect"), formatted, _derived_texts(params, context))
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": deepcopy(data["expect"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_120099657(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_120099657(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "raw_execution": raw_execution,
        "ground_truth": _ground_truth(raw_execution),
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_120099657(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
