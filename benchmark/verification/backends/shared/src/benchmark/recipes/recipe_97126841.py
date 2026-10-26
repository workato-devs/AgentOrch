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
from ..verifier import verify_97126841


RECIPE_ID = "97126841"
SEED_TYPE = "clock_month_allocation_schedule_slack_variant"
TRACK = "live_slack_clock_month_post"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "272cbb15"
DECLARE_AS = "6658dcd5"
POST_AS = "cfdec45a"
RAW_CHANNEL = "#finance-close"
BUTTON_TITLE = "Select Subsidiaries"
TEXT_TEMPLATE = "*Run Allocation Schedule for {month}*"
TICK_TOKEN_RE = re.compile(r"^\$SCHEDULED_TICK_MINUS_(\d+)M$")
TICK_MAX_MONTHS_BACK = 24
TICK_DAY = 1
TICK_TIME = "10:00:00"
TICK_OFFSET = "+08:00"  # Asia/Singapore, fixed offset (no DST)
MONTHS_ABBREV = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)

_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "272cbb15",
  "provider": "clock",
  "name": "scheduled_event",
  "skip": false,
  "input": {
   "days_of_month": "1",
   "time_unit": "months",
   "timezone": "Asia/Singapore",
   "trigger_at": "10:00:00",
   "trigger_every": "1"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "6658dcd5",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "run_month_slack_formatted": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"clock\",\"line\":\"272cbb15\",\"path\":[\"scheduled_time\"]}') - 1.months).strftime(\"%b %Y\")"
    },
    "schema": "[{\"control_type\":\"text\",\"label\":\"Run Month (Slack formatted)\",\"name\":\"run_month_slack_formatted\",\"type\":\"string\",\"optional\":true}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "cfdec45a",
  "provider": "slack_bot",
  "name": "post_bot_message",
  "skip": false,
  "input": {
   "blocks": [
    {
     "block_type": "section_with_button_with_long_action",
     "bot_command": "47097324",
     "button_title": "Select Subsidiaries",
     "button_type": "bot_command",
     "section_text": "*Run Allocation Schedule for #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"6658dcd5\",\"path\":[\"run_month_slack_formatted\"]}')}*",
     "style": "primary"
    }
   ],
   "channel": "#finance-close"
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
    "run_month_slack_formatted",
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


def validate_97126841(raw: dict[str, Any]) -> dict[str, Any]:
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


def _months_back_from_token(trigger: dict[str, Any]) -> int:
    if sorted(trigger.keys()) != ["scheduled_time"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly scheduled_time (the "
            f"only trigger pill the recipe reads); got {sorted(trigger.keys())}"
        )
    token = trigger.get("scheduled_time")
    match = TICK_TOKEN_RE.fullmatch(token) if isinstance(token, str) else None
    if not match:
        raise RuntimeError(
            f"recipe {RECIPE_ID} scheduled_time must be a $SCHEDULED_TICK_MINUS_<N>M "
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
    Asia/Singapore offset. Fixed-timestamp rule: scheduled-event time comes
    ONLY from the variant input's top-level 'now' — fail-fast when it is
    missing or ambiguous; there is deliberately no wall-clock fallback."""
    raw_value = data.get("now")
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must pin a top-level 'now' anchor "
            f"(ISO-8601 with explicit UTC offset) — scheduled-event time never "
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
    configured monthly fire instant (day 1, 10:00:00 +08:00) months_back
    months before the anchor's month IN THE TRIGGER'S OWN ZONE, plus the
    '%b %Y' render of that instant minus 1.months (mirrors the probed engine
    semantics: literal-timestamp strftime, calendar month decrement, no
    timezone conversion). Never reads wall-clock."""
    tick_year, tick_month = _shift_year_month(anchor_sgt.year, anchor_sgt.month, months_back)
    scheduled_time = f"{tick_year:04d}-{tick_month:02d}-{TICK_DAY:02d}T{TICK_TIME}{TICK_OFFSET}"
    run_year, run_month = _shift_year_month(tick_year, tick_month, 1)
    return scheduled_time, f"{MONTHS_ABBREV[run_month - 1]} {run_year}"


def _require_resolved(value: Any) -> None:
    leftover = re.findall(r"\$(?:RUN_MONTH|SCHEDULED_TICK)[A-Z0-9_]*", json.dumps(value))
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
        resolved.get("run_month_slack_formatted") == render,
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
            f"truth (months_back {months_back}, run month {render!r}, post text "
            f"{post_text!r}, 2 actions, declare+post trace): {resolved!r}"
        )
    return resolved


def seed_97126841(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_97126841(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    months_back = _months_back_from_token(trigger_input(ctx))
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: a forced action error would fail the "
            "whole run instead of exercising a recipe branch"
        )
    if data.get("job_context") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} never reads job_context (the formula derefs the "
            "clock scheduled_time output pill, not job_created_at — that is the "
            "123600416 twin's shape)"
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
    scheduled_time, render = _resolve_tick(months_back, anchor_sgt)
    resolved_expect = _require_expect(data.get("expect"), months_back, render)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        # Token resolved at seed time from the variant's pinned anchor —
        # the stored trigger and expect are concrete and stable forever.
        "now": data["now"],
        "trigger": {"scheduled_time": scheduled_time},
        "seed_tokens": {f"$SCHEDULED_TICK_MINUS_{months_back}M": scheduled_time},
        "expect": resolved_expect,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_97126841(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_97126841(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    trigger = seed.get("trigger")
    if not isinstance(trigger, dict) or not str(trigger.get("scheduled_time") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing resolved trigger.scheduled_time")
    if TICK_TOKEN_RE.fullmatch(str(trigger.get("scheduled_time") or "")):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed carries an UNRESOLVED tick token — re-seed "
            f"(tokens resolve at seed time): {trigger!r}"
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
    result["verifier"] = verify_97126841(result)
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
