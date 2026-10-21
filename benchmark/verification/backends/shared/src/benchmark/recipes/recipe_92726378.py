from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_92726378


RECIPE_ID = "92726378"
SEED_TYPE = "slack_app_home_cs_copilot_publish_variant"
TRACK = "live_slack_app_home_publish"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "new_event"
TRIGGER_AS = "14600d8d"
DECLARE_AS = "01313dbb"
PUBLISH_AS = "055b99cf"
USER_PLACEHOLDER = "__TRIGGER_USER__"
# declare_variable stores the five date-typed anon literals VERBATIM — no
# date parsing is applied to the '<anon>MM/DD/YYYY</anon>' strings (dry-replay
# probed 2026-07-09; the declare trace result is exactly this mapping).
DECLARED_DATES = {
    "date1": "<anon>01/01/2024</anon>",
    "date2": "<anon>02/01/2024</anon>",
    "date3": "<anon>03/01/2024</anon>",
    "date4": "<anon>04/01/2024</anon>",
    "date5": "<anon>05/01/2024</anon>",
}

# slack_bot.new_event app_home_opened (as 14600d8d). Linear body, no
# branches; the ONLY trigger field any pill dereferences is
# app_home_opened.user (the '<@user>' mention in block 1 and the publish
# user_id). Steps:
#   2  workato_variable.declare_variable 01313dbb (MOCK Workato-internal):
#      date1..date5 = the anon literals above, stored verbatim.
#   3  slack_bot.open_bot_app_home 055b99cf (LIVE views.publish): the
#      adapter resolves the 9 raw blocks + user_id and calls
#      slack.publish_home; args.view carries the RAW Workato block shape
#      (block_type/...) — the Block Kit translation happens inside the live
#      client (_home_view; registered 109445492/86565478 precedent).
#      Conversion re-probed OFFLINE 2026-07-09 (no publish): 9 Block Kit
#      blocks ['image','section','divider','section','actions','divider',
#      'actions','divider','section']; the REAL unsplash image URL passes
#      through VERBATIM (only <anon> URLs get the Slack placeholder) and the
#      image branch ignores its vestigial section_text 'Hello'; the two
#      actions blocks carry 4 buttons total (incl bot_command '46745005' as
#      action_id/value on two of them, styles primary/danger; 'Lookup
#      Account' style 'default' is NOT a Block Kit style and is dropped by
#      the converter); the section_with_fields renders all 9
#      attachment_fields as '*title*\nvalue' mrkdwn with anon company names
#      + backticked date pill values verbatim.
#
# View-content semantics the variants pin byte-exactly via HOME_BLOCKS
# (whole-list equality, _contains_args exact-length list compare):
# - fields 6/7 REUSE date2/date1 (pill-fed), field 9 is the HARDCODED
#   literal '`<anon>06/01/2024</anon>`' (not variable-fed);
# - all view content except the mention is trigger-independent literals, so
#   across variants only the '<@user>' line and user_id may differ.
#
# Branch mapping: single reachable linear path. Variants swap the trigger
# user across the TWO real benchmark workspace users (U0B973TLN7N /
# U0B91BSRGF8 — the registered app-home family 48616658/86565478/83147854/
# 120700492/125342694 uses exactly these; live views.publish rejects unknown
# users, so a third-user variant is not provisionable — the triage
# 'user_c' pins are folded into every variant's byte-exact view pin).
#
# Backends: slack LIVE (views.publish App Home to the seeded trigger user).
# No cleanup: an App Home publish is never re-read by the benchmark and
# republishing is idempotent for reruns (86565478 precedent). The declare
# step is the sanctioned Workato-internal variable mock; no other state
# anywhere -> seed sections must be empty.
_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "14600d8d",
  "provider": "slack_bot",
  "name": "new_event",
  "skip": false,
  "input": {
   "event_name": "app_home_opened"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "01313dbb",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "date1": "<anon>01/01/2024</anon>",
     "date2": "<anon>02/01/2024</anon>",
     "date3": "<anon>03/01/2024</anon>",
     "date4": "<anon>04/01/2024</anon>",
     "date5": "<anon>05/01/2024</anon>"
    },
    "schema": "[{\"name\":\"date1\",\"type\":\"date\",\"optional\":true,\"label\":\"date1\",\"details\":{\"real_name\":\"date1\"},\"control_type\":\"date\"},{\"name\":\"date2\",\"type\":\"date\",\"optional\":true,\"label\":\"date2\",\"details\":{\"real_name\":\"date2\"},\"control_type\":\"date\"},{\"name\":\"date3\",\"type\":\"date\",\"optional\":true,\"label\":\"date3\",\"details\":{\"real_name\":\"date3\"},\"control_type\":\"date\"},{\"name\":\"date4\",\"type\":\"date\",\"optional\":true,\"label\":\"date4\",\"details\":{\"real_name\":\"date4\"},\"control_type\":\"date\"},{\"name\":\"date5\",\"type\":\"date\",\"optional\":true,\"label\":\"date5\",\"details\":{\"real_name\":\"date5\"},\"control_type\":\"date\"}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "055b99cf",
  "provider": "slack_bot",
  "name": "open_bot_app_home",
  "skip": false,
  "input": {
   "blocks": [
    {
     "alt_text": "Image of CSM",
     "block_type": "image",
     "image_url": "https://images.unsplash.com/photo-1694734260233-d5dc5ae02593?q=80&w=2874&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
     "section_text": "Hello"
    },
    {
     "block_type": "section_with_text",
     "section_text": "Hi <@#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"14600d8d\",\"path\":[\"app_home_opened\", \"user\"]}')}>  Welcome to CS Copilot, your digital CS Assistant"
    },
    {
     "block_type": "divider"
    },
    {
     "block_type": "section_with_text",
     "section_text": ":fire: CONTRACT RENEWALS :fire:"
    },
    {
     "actions": [
      {
       "bot_command": "search renewal account",
       "button_title": "Search for Renewals",
       "style": "primary",
       "type": "button"
      }
     ],
     "block_type": "actions"
    },
    {
     "block_type": "divider"
    },
    {
     "actions": [
      {
       "bot_command": "lookup account sheet",
       "button_title": "Lookup Account",
       "style": "default",
       "type": "button"
      },
      {
       "bot_command": "46745005",
       "button_title": "Update Account Health",
       "style": "primary",
       "type": "button"
      },
      {
       "bot_command": "46745005",
       "button_title": "Create At Risk task",
       "style": "danger",
       "type": "button"
      }
     ],
     "block_type": "actions"
    },
    {
     "block_type": "divider"
    },
    {
     "attachment_fields": [
      {
       "title": "• Balendly",
       "value": "`#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"01313dbb\",\"path\":[\"date1\"]}')}`"
      },
      {
       "title": "• Sunburst",
       "value": "`#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"01313dbb\",\"path\":[\"date2\"]}')}`"
      },
      {
       "title": "• <anon>Acme Corporation</anon>",
       "value": "`#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"01313dbb\",\"path\":[\"date3\"]}')}`"
      },
      {
       "title": "• <anon>John Smith</anon>",
       "value": "`#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"01313dbb\",\"path\":[\"date4\"]}')}`"
      },
      {
       "title": "• Zlearcollar",
       "value": "`#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"01313dbb\",\"path\":[\"date5\"]}')}`"
      },
      {
       "title": "• <anon>Beta Solutions LLC</anon>",
       "value": "`#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"01313dbb\",\"path\":[\"date2\"]}')}`"
      },
      {
       "title": "• <anon>Jane Doe</anon>",
       "value": "`#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"01313dbb\",\"path\":[\"date1\"]}')}`"
      },
      {
       "title": "• <anon>Gamma Partners</anon>",
       "value": "`#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"01313dbb\",\"path\":[\"date5\"]}')}`"
      },
      {
       "title": "• <anon>Delta Enterprises, Inc.</anon>",
       "value": "`<anon>06/01/2024</anon>`"
      }
     ],
     "block_type": "section_with_fields",
     "section_text": ":alarm_clock: Upcoming Renewals"
    }
   ],
   "user_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"14600d8d\",\"path\":[\"app_home_opened\", \"user\"]}')}"
  }
 }
]"""
STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

# The publish args' RAW blocks with every pill resolved (dry-replay probed
# byte-exact 2026-07-09); the trigger user is the only variable site.
_HOME_BLOCKS_TEMPLATE_JSON = r"""[
 {
  "alt_text": "Image of CSM",
  "block_type": "image",
  "image_url": "https://images.unsplash.com/photo-1694734260233-d5dc5ae02593?q=80&w=2874&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
  "section_text": "Hello"
 },
 {
  "block_type": "section_with_text",
  "section_text": "Hi <@__TRIGGER_USER__>  Welcome to CS Copilot, your digital CS Assistant"
 },
 {
  "block_type": "divider"
 },
 {
  "block_type": "section_with_text",
  "section_text": ":fire: CONTRACT RENEWALS :fire:"
 },
 {
  "actions": [
   {
    "bot_command": "search renewal account",
    "button_title": "Search for Renewals",
    "style": "primary",
    "type": "button"
   }
  ],
  "block_type": "actions"
 },
 {
  "block_type": "divider"
 },
 {
  "actions": [
   {
    "bot_command": "lookup account sheet",
    "button_title": "Lookup Account",
    "style": "default",
    "type": "button"
   },
   {
    "bot_command": "46745005",
    "button_title": "Update Account Health",
    "style": "primary",
    "type": "button"
   },
   {
    "bot_command": "46745005",
    "button_title": "Create At Risk task",
    "style": "danger",
    "type": "button"
   }
  ],
  "block_type": "actions"
 },
 {
  "block_type": "divider"
 },
 {
  "attachment_fields": [
   {
    "title": "• Balendly",
    "value": "`<anon>01/01/2024</anon>`"
   },
   {
    "title": "• Sunburst",
    "value": "`<anon>02/01/2024</anon>`"
   },
   {
    "title": "• <anon>Acme Corporation</anon>",
    "value": "`<anon>03/01/2024</anon>`"
   },
   {
    "title": "• <anon>John Smith</anon>",
    "value": "`<anon>04/01/2024</anon>`"
   },
   {
    "title": "• Zlearcollar",
    "value": "`<anon>05/01/2024</anon>`"
   },
   {
    "title": "• <anon>Beta Solutions LLC</anon>",
    "value": "`<anon>02/01/2024</anon>`"
   },
   {
    "title": "• <anon>Jane Doe</anon>",
    "value": "`<anon>01/01/2024</anon>`"
   },
   {
    "title": "• <anon>Gamma Partners</anon>",
    "value": "`<anon>05/01/2024</anon>`"
   },
   {
    "title": "• <anon>Delta Enterprises, Inc.</anon>",
    "value": "`<anon>06/01/2024</anon>`"
   }
  ],
  "block_type": "section_with_fields",
  "section_text": ":alarm_clock: Upcoming Renewals"
 }
]"""
HOME_BLOCKS_TEMPLATE: list[dict[str, Any]] = json.loads(_HOME_BLOCKS_TEMPLATE_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "slack_bot.open_bot_app_home",
]
ALLOWED_TOOLS: list[str] = ["slack_bot.open_bot_app_home"]
TRIGGER_EVENT_KEYS = ("channel", "tab", "type", "user")
_SLACK_USER_RE = re.compile(r"U[A-Z0-9]{6,}")
EXPECT_KEYS = (
    "case",
    "user_id",
    "executed_action_count",
    "raw_executed_action_count",
    "tools",
    "trace_tools",
    "tool_expectations",
    "declared_dates",
    "view_blocks",
)


def resolved_home_blocks(user: str) -> list[dict[str, Any]]:
    blocks = deepcopy(HOME_BLOCKS_TEMPLATE)
    blocks[1]["section_text"] = blocks[1]["section_text"].replace(USER_PLACEHOLDER, user)
    return blocks


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


def validate_92726378(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
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


def _require_trigger_shape(trigger: dict[str, Any]) -> str:
    if sorted(trigger.keys()) != ["app_home_opened"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the "
            f"app_home_opened event; got {sorted(trigger.keys())}"
        )
    event = trigger["app_home_opened"]
    if not isinstance(event, dict) or tuple(sorted(event.keys())) != TRIGGER_EVENT_KEYS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} app_home_opened must carry exactly "
            f"{list(TRIGGER_EVENT_KEYS)} (the recipe dereferences only .user; "
            "type/channel/tab are the minimal faithful event envelope)"
        )
    if event["type"] != "app_home_opened" or event["tab"] != "home":
        raise RuntimeError(
            f"recipe {RECIPE_ID} event must be type 'app_home_opened' on the 'home' tab"
        )
    user = event["user"]
    if not isinstance(user, str) or not _SLACK_USER_RE.fullmatch(user):
        raise RuntimeError(
            f"recipe {RECIPE_ID} event.user must be a REAL workspace user id "
            f"(live views.publish rejects unknown users); got {user!r}"
        )
    if not isinstance(event["channel"], str) or not event["channel"].strip():
        raise RuntimeError(f"recipe {RECIPE_ID} event.channel must be a non-empty string")
    return user


def _require_expect(expect: Any, user: str) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    blocks = resolved_home_blocks(user)
    checks = (
        bool(str(expect.get("case") or "").strip()),
        expect.get("user_id") == user,
        expect.get("executed_action_count") == len(ALLOWED_TOOLS),
        expect.get("raw_executed_action_count") == 2,
        expect.get("trace_tools") == EXPECTED_RAW_TOOLS,
        expect.get("tools") == ALLOWED_TOOLS,
        expect.get("declared_dates") == DECLARED_DATES,
        expect.get("view_blocks") == blocks,
        expect.get("tool_expectations")
        == [
            {
                "tool": "slack_bot.open_bot_app_home",
                "args_contains": {"user_id": user, "view": {"blocks": blocks}},
            }
        ],
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect must pin the single publish byte-exactly "
            f"(user_id {user!r} — the only variable site is the '<@user>' mention "
            f"in block 1 — plus the verbatim anon declares, the 9 resolved raw "
            f"blocks incl. the hardcoded 9th field '`<anon>06/01/2024</anon>`' and "
            f"the date2/date1 reuse in fields 6-7, 2 actions): {expect!r}"
        )


def seed_92726378(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_92726378(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    user = _require_trigger_shape(trigger)
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: a forced action error would fail the "
            "whole run instead of exercising a recipe branch"
        )
    if data.get("job_context") is not None:
        raise RuntimeError(f"recipe {RECIPE_ID} never reads job_context (dead seed state)")
    seed_in = data.get("seed")
    if seed_in not in (None, {}):
        raise RuntimeError(
            f"recipe {RECIPE_ID} takes no seed sections (live App Home publish only — "
            f"any seeded backend state would be dead); got {seed_in!r}"
        )
    _require_expect(data.get("expect"), user)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(data["expect"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_92726378(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_92726378(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    # No cleanup: the App Home publish is never re-read by the benchmark and
    # republishing is idempotent for reruns (cleanup principle; 86565478
    # precedent). The declare step is the Workato-internal variable mock.
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
            "ground_truth": _ground_truth(raw_execution),
            "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_92726378(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
