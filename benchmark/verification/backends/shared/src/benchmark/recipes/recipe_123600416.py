from __future__ import annotations

import datetime
import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_123600416


RECIPE_ID = "123600416"
SEED_TYPE = "clock_month_global_allocations_slack_variant"
TRACK = "live_slack_clock_month_post"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "e733a3e8"
DECLARE_AS = "41b89356"
POST_AS = "05bb94d6"
RAW_CHANNEL = "finance-close"
BUTTON_TITLE = "Proceed"
TEXT_TEMPLATE = "Run Global Allocations for {month}"
# Relative seed token resolved against the variant's PINNED time anchor
# (fixed-timestamp rule, benmark_rules 'Simulated input variant rule': a
# recipe that uses scheduled-event/job_context time must get a fixed
# timestamp from the variant input — never wall-clock). Each variant input
# pins a top-level "now" (ISO-8601 with explicit UTC offset, the 104508126
# anchor precedent); $SCHEDULED_TICK_MINUS_<N>M = the recipe's own
# configured monthly fire instant (days_of_month '3', 08:00:00
# Asia/Singapore, both pinned trigger config) N whole months before the
# ANCHOR's month in the trigger's own zone. For a clock recipe the job is
# created at the fire instant, so the token seeds
# job_context.job_created_at. Resolution happens IN THE SEEDER from the
# anchor ONLY (fail-fast when the anchor is missing — no datetime.now
# fallback), so the resolved tick and the concrete month pins in expect are
# stable forever. Same token grammar as the in-batch twin 97126841.
TICK_TOKEN_RE = re.compile(r"^\$SCHEDULED_TICK_MINUS_(\d+)M$")
TICK_MAX_MONTHS_BACK = 24
TICK_DAY = 3
TICK_TIME = "08:00:00"
TICK_OFFSET = "+08:00"  # Asia/Singapore, fixed offset (no DST)
MONTHS_FULL = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)

# clock.scheduled_event (as e733a3e8; monthly, days_of_month '3', trigger_at
# 08:00:00 Asia/Singapore, comment 'Day 3 of month end closing' — ALL node
# metadata, inert). The trigger is PAYLOAD-LESS: no body pill reads any
# trigger field, so trigger_input must be exactly {} (108028920 precedent)
# and the seeded job_context supplies the only variable input
# (raw_executor exposes seed.job_context to the _dp job_context pill).
# Linear body, no branches:
#   2  workato_variable.declare_variable 41b89356 (MOCK Workato-internal):
#      Month = job_context.job_created_at.strftime("%B %Y") — literal
#      timestamp strftime, NO timezone conversion (dry-replayed 2026-07-09:
#      '2026-07-03T08:00:00+08:00' -> 'July 2026', November -> 'November
#      2026', '2027-01-03T08:00:00+08:00' -> 'January 2027'; registered
#      120099657 strftime-declare precedent). An UNSEEDED job_context raises
#      inside the engine (probed: ValueError on the MISSING sentinel) — the
#      seeder therefore fail-fasts on absent job_created_at.
#   3  slack_bot.post_bot_message 05bb94d6 (LIVE): single
#      section_with_button_with_long_action block. Rendered text =
#      section_text ONLY 'Run Global Allocations for #{Month pill}' — the
#      interactive Proceed button (bot_command 63660740, style primary) is
#      DROPPED by slack_text (registered 87484821/120099657 drop precedent,
#      re-probed via dry replay). Channel 'finance-close' does not start
#      with 'U' -> auto-reroute to env.slack_channel_override.
#
# IN-BATCH TWIN of 97126841 (same clock -> declare-strftime ->
# post_bot_message '#finance-close' skeleton; delta = formula
# (job_created_at '%B %Y' here vs (scheduled_time - 1.months) '%b %Y'),
# bot_command 63660740 vs 47097324, button/section wording, channel without
# the leading '#'). Closest registered shapes: 108028920 (payload-less
# scheduler tick + override-channel reroute), 120099657 (declare-strftime
# pin + block-content drop).
#
# Branch mapping: linear, single path; the only variable input is the
# seeded job_created_at flowing through strftime into the posted text.
# Variants differ ONLY in the tick token offset (0/1/2 months back from the
# pinned anchor month -> three consecutive distinct '%B YYYY' renders,
# proving the text is formula-driven; full month names also pin %B vs the
# twin's %b). The December->'January <Y+1>' year rollover is the same
# literal-strftime path (probed offline, deterministic).
#
# Backends: slack LIVE (one chat.postMessage to the override channel — an
# ordinary terminal observable that nothing re-reads: no cleanup per the
# cleanup principle). The declare step is the sanctioned Workato-internal
# variable mock. No other state anywhere -> seed sections must be empty.
_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "e733a3e8",
  "provider": "clock",
  "name": "scheduled_event",
  "skip": false,
  "input": {
   "days_of_month": "3",
   "time_unit": "months",
   "timezone": "Asia/Singapore",
   "trigger_at": "08:00:00",
   "trigger_every": "1"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "41b89356",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "Month": "=_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_created_at\"]}').strftime(\"%B %Y\")"
    },
    "schema": "[{\"name\":\"Month\",\"type\":\"string\",\"optional\":true,\"label\":\"Month\",\"details\":{\"real_name\":\"Month\"},\"control_type\":\"text\",\"parent\":[\"variables\",\"data\"]}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "05bb94d6",
  "provider": "slack_bot",
  "name": "post_bot_message",
  "skip": false,
  "input": {
   "blocks": [
    {
     "block_type": "section_with_button_with_long_action",
     "bot_command": "63660740",
     "button_title": "Proceed",
     "button_type": "bot_command",
     "section_text": "Run Global Allocations for #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"41b89356\",\"path\":[\"Month\"]}')}",
     "style": "primary"
    }
   ],
   "channel": "finance-close"
  }
 }
]"""
STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = ["slack.post_message"]
EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "raw_executed_action_count",
    "tools",
    "trace_tools",
    "tool_expectations",
    "months_back",
    "month",
    "post_text",
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


def validate_123600416(raw: dict[str, Any]) -> dict[str, Any]:
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


def _months_back_from_token(data: dict[str, Any]) -> int:
    job_context = data.get("job_context")
    if not isinstance(job_context, dict) or sorted(job_context.keys()) != ["job_created_at"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must seed job_context with exactly "
            f"job_created_at (the only pill the recipe dereferences; an unseeded "
            f"job_context raises inside the engine); got {job_context!r}"
        )
    token = job_context.get("job_created_at")
    match = TICK_TOKEN_RE.fullmatch(token) if isinstance(token, str) else None
    if not match:
        raise RuntimeError(
            f"recipe {RECIPE_ID} job_created_at must be a $SCHEDULED_TICK_MINUS_<N>M "
            f"relative token (single time source per variant: the tick derives from "
            f"the pinned 'now' anchor, never a hand-typed instant); got {token!r}"
        )
    months_back = int(match.group(1))
    if months_back > TICK_MAX_MONTHS_BACK:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tick token offset must be <= {TICK_MAX_MONTHS_BACK} "
            f"months (plausible recent tick relative to the anchor): {months_back}"
        )
    return months_back


def _anchor_sgt(data: dict[str, Any]) -> datetime.datetime:
    """The variant's pinned time anchor, converted to the trigger's own fixed
    Asia/Singapore offset. Fixed-timestamp rule: scheduled-event/job_context
    time comes ONLY from the variant input's top-level 'now' — fail-fast when
    it is missing or ambiguous; there is deliberately no wall-clock fallback."""
    raw_value = data.get("now")
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must pin a top-level 'now' anchor "
            f"(ISO-8601 with explicit UTC offset) — job_context time never "
            f"resolves from wall-clock (fixed-timestamp rule); got {raw_value!r}"
        )
    try:
        anchor = datetime.datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(
            f"recipe {RECIPE_ID} unparseable 'now' anchor: {raw_value!r}"
        ) from exc
    if anchor.tzinfo is None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} 'now' anchor must carry an explicit UTC offset "
            f"(the tick math runs in the trigger's Asia/Singapore zone): {raw_value!r}"
        )
    return anchor.astimezone(datetime.timezone(datetime.timedelta(hours=8)))


def _shift_year_month(year: int, month: int, months_back: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) - months_back
    return index // 12, index % 12 + 1


def _resolve_tick(months_back: int, anchor_sgt: datetime.datetime) -> tuple[str, str]:
    """Resolve the token at seed time FROM THE PINNED ANCHOR: the trigger's
    configured monthly fire instant (day 3, 08:00:00 +08:00) months_back
    months before the anchor's month IN THE TRIGGER'S OWN ZONE, plus the
    '%B %Y' render of that instant (mirrors the probed engine semantics:
    literal-timestamp strftime, no timezone conversion). Never reads
    wall-clock."""
    tick_year, tick_month = _shift_year_month(anchor_sgt.year, anchor_sgt.month, months_back)
    job_created_at = f"{tick_year:04d}-{tick_month:02d}-{TICK_DAY:02d}T{TICK_TIME}{TICK_OFFSET}"
    return job_created_at, f"{MONTHS_FULL[tick_month - 1]} {tick_year}"


def _require_resolved(value: Any) -> None:
    leftover = re.findall(r"\$(?:MONTH|SCHEDULED_TICK)[A-Z0-9_]*", json.dumps(value))
    if leftover:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect must pin CONCRETE month renders (derived from "
            f"the pinned 'now' anchor), not tokens: {sorted(set(leftover))}"
        )


def _require_expect(expect: Any, months_back: int, render: str) -> dict[str, Any]:
    """Expect pins are CONCRETE values re-derived from the pinned anchor;
    the seeder cross-checks every month-bearing pin against the anchor-derived
    render and fails fast on any drift."""
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    resolved = deepcopy(expect)
    _require_resolved(resolved)
    post_text = TEXT_TEMPLATE.format(month=render)
    checks = (
        bool(str(resolved.get("case") or "").strip()),
        resolved.get("months_back") == months_back,
        resolved.get("executed_action_count") == len(ALLOWED_TOOLS),
        resolved.get("raw_executed_action_count") == 2,
        resolved.get("trace_tools") == EXPECTED_RAW_TOOLS,
        resolved.get("tools") == ALLOWED_TOOLS,
        resolved.get("month") == render,
        resolved.get("post_text") == post_text,
        resolved.get("tool_expectations")
        == [
            {
                "tool": "slack.post_message",
                "channel": "override",
                "args_contains": {"text": post_text},
                "text_fragments": [post_text],
            }
        ],
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with the derived ground "
            f"truth (months_back {months_back}, Month {render!r}, post text "
            f"{post_text!r}, 2 actions, declare+post trace): {resolved!r}"
        )
    return resolved


def seed_123600416(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_123600416(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (payload-less "
            f"monthly scheduler tick — no body pill reads a trigger field; the "
            f"job_context section carries the tick token): {trigger!r}"
        )
    months_back = _months_back_from_token(data)
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: a forced action error would fail the "
            "whole run instead of exercising a recipe branch"
        )
    seed_in = data.get("seed")
    if seed_in not in (None, {}):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seeds NO backend state (one live Slack post only); "
            f"got {seed_in!r}"
        )
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    anchor_sgt = _anchor_sgt(data)
    job_created_at, render = _resolve_tick(months_back, anchor_sgt)
    resolved_expect = _require_expect(data.get("expect"), months_back, render)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": {},
        "now": data["now"],
        # Token resolved at seed time from the variant's pinned anchor. Set
        # explicitly so the raw token in variant_input.job_context never
        # reaches the executor (attach_variant only copies job_context when
        # the seeder did not set it).
        "job_context": {"job_created_at": job_created_at},
        "seed_tokens": {f"$SCHEDULED_TICK_MINUS_{months_back}M": job_created_at},
        "expect": resolved_expect,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_123600416(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_123600416(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    job_context = seed.get("job_context")
    if not isinstance(job_context, dict) or not str(job_context.get("job_created_at") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed file missing resolved job_context.job_created_at "
            "(the declare formula raises on an unseeded job_context)"
        )
    if TICK_TOKEN_RE.fullmatch(str(job_context.get("job_created_at") or "")):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed carries an UNRESOLVED tick token — re-seed "
            f"(tokens resolve at seed time): {job_context!r}"
        )
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    # No cleanup: the single live post is an ordinary terminal observable
    # that nothing re-reads/updates/deletes (cleanup principle); the declare
    # step is the Workato-internal mock with no persistent state.
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
        "job_context": deepcopy(job_context),
        "seed_tokens": seed.get("seed_tokens"),
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
    result["verifier"] = verify_123600416(result)
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
