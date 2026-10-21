from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_88676643


RECIPE_ID = "88676643"
SEED_TYPE = "slack_bot_fridaybot_do_command_logger_variant"
TRACK = "workato_logger_fridaybot_do_command_mock"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"
TRIGGER_AS = "0d147108"
TRY_LOG_AS = "8a8d5d15"
CATCH_AS = "cdf884c4"
CATCH_LOG_AS = "71f22ee0"
LOG_TOOL = "workato_runtime.log_message"

# slack_bot.bot_command_v2 0d147108 (domain 'fridaybot', name 'do', scope
# 'nothing', allow_dialog 'false', hide_from_help 'true' — "This command does
# nothing. Use this as a vase action."; parameters schema is an empty object)
#   TRY (2):
#     3 logger.log_message 8a8d5d15 (comment 'Who clicked this?'): message =
#       trigger context.user_email pill — the ONLY trigger deref in the recipe.
#   CATCH 4 (as cdf884c4, max_retry_count 0, retry_interval 2):
#     5 logger.log_message 71f22ee0: message = catch.cdf884c4.message pill.
#
# PURE MOCK (Workato-internal only): logger renders as the runtime tool
# workato_runtime.log_message directly in the raw trace — it never touches
# ctx.tools, so result.tool_calls is ALWAYS [] and expect.tools /
# expect.tool_expectations are empty lists on every variant; the verifier
# fragment pins the log message text and the executing step as-id from the
# trace instead. No live lane, no cleanup, no snapshots.
#
# BYTE-EXACT TWIN of 88674737: the two raw_recipe.md files differ ONLY in the
# title line and CSV metadata (flow_id 45178933 vs 44982407, created_at,
# version_no 1 vs 3); every recipe-body byte (as-ids, uuids, inputs, schema)
# is identical — probe-diffed on the current tree. verify_88674737 delegates
# to this recipe's fragment (batch-06 delegation precedent).
#
# Probe findings pinned by seeder/variants (current tree, 2026-07-08):
# - happy: 1 action — log 8a8d5d15 {message: <context.user_email>}; the catch
#   never records (no cdf884c4 step output).
# - catch: reachable ONLY via seed.force_action_error on 8a8d5d15 (the mock
#   logger cannot fail naturally; established batch-04/05 mechanism). The
#   failed try logger records NOTHING; the single traced action is 71f22ee0
#   logging the forced error text verbatim (catch payload {type, message}).
# - a MISSING context.user_email renders the pill as '' silently (probed);
#   the seeder requires a non-empty plausible email so the happy log is
#   always a non-trivial pinned value.

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "slack_bot", "name": "bot_command_v2", "as": "0d147108", "skip": false, "input": {"allow_dialog": "false", "description": "This command does nothing. Use this as a vase action.", "domain": "fridaybot", "hide_from_help": "true", "name": "do", "scope": "nothing"}, "block": [{"number": 2, "keyword": "try", "provider": "", "name": "", "as": "", "skip": false, "input": {}, "block": [{"number": 3, "keyword": "action", "provider": "logger", "name": "log_message", "as": "8a8d5d15", "skip": false, "input": {"message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"0d147108\",\"path\":[\"context\", \"user_email\"]}')}"}, "block": []}, {"number": 4, "keyword": "catch", "provider": "", "name": "", "as": "cdf884c4", "skip": false, "input": {"max_retry_count": "0", "retry_interval": "2"}, "block": [{"number": 5, "keyword": "action", "provider": "logger", "name": "log_message", "as": "71f22ee0", "skip": false, "input": {"message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"cdf884c4\",\"path\":[\"message\"]}')}"}, "block": []}]}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[int, str, str, str]] = [
    (3, TRY_LOG_AS, "logger", "log_message"),
    (5, CATCH_LOG_AS, "logger", "log_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [LOG_TOOL]
# logger is a runtime-internal tool: nothing is exposed through ctx.tools.
ALLOWED_TOOLS: list[str] = []
REQUIRED_EXPECT_KEYS = (
    "branch",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "log_step_as",
    "log_message",
    "catch_message",
)
BRANCHES = ("happy_log_email", "catch_log_error")


def validate_88676643(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    actions = _collect_actions(raw)
    actual = [
        (a.get("number"), str(a.get("as")), str(a.get("provider")), str(a.get("name")))
        for a in actions
    ]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "command_domain": "fridaybot",
        "command_name": "do",
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


def seed_88676643(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88676643(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    user_email = _require_trigger_shape(trigger)
    expect = data.get("expect")
    _require_expect_common(expect)
    force = data.get("force_action_error")
    if data.get("seed") not in (None, {}):
        raise RuntimeError(
            f"recipe {RECIPE_ID} is pure-mock with no backend state: seed section "
            f"must be absent/empty; got {data.get('seed')!r}"
        )
    if expect["branch"] == "happy_log_email":
        _require_happy_variant(expect, user_email, force)
    else:  # catch_log_error
        _require_catch_variant(expect, force)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
    }
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_88676643(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88676643(raw)
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
            "expect": seed.get("expect"),
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            # Pure mock (Workato-internal only): nothing to snapshot or clean.
            "initial_snapshot": {},
            "final_snapshot": {},
            "cleanup_response": None,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_88676643(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> str:
    if sorted(trigger.keys()) != ["context", "parameters"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly context + parameters "
            f"(the bot_command_v2 payload); got {sorted(trigger.keys())}"
        )
    if trigger.get("parameters") != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters schema is an empty object — seed "
            f"parameters as exactly {{}}; got {trigger.get('parameters')!r}"
        )
    context = trigger.get("context")
    if not isinstance(context, dict) or sorted(context.keys()) != ["user_email"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger context must carry exactly user_email (the "
            f"recipe's only trigger deref; extra keys would be dead data); got "
            f"{sorted(context.keys()) if isinstance(context, dict) else context!r}"
        )
    user_email = context["user_email"]
    if not isinstance(user_email, str) or "@" not in user_email or not user_email.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} context.user_email must be a non-empty plausible "
            f"email string (a missing/blank email renders the log message '' "
            f"SILENTLY — probe-verified); got {user_email!r}"
        )
    return user_email


def _require_expect_common(expect: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if expect.get("branch") not in BRANCHES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch must be one of {BRANCHES}")
    checks = (
        expect.get("executed_action_count") == 1,
        expect.get("tools") == [],
        expect.get("tool_expectations") == [],
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} every branch runs exactly ONE logger action and the "
            f"runtime logger never surfaces through ctx.tools (tools/tool_expectations "
            f"must be []); got {expect!r}"
        )


def _require_happy_variant(expect: dict[str, Any], user_email: str, force: Any) -> None:
    if force is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} happy_log_email must not force an action error"
        )
    checks = (
        expect.get("log_step_as") == TRY_LOG_AS,
        expect.get("log_message") == user_email,
        expect.get("catch_message") is None,
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} happy expect must pin log_step_as {TRY_LOG_AS!r}, "
            f"log_message == trigger context.user_email {user_email!r} and "
            f"catch_message null; got {expect!r}"
        )


def _require_catch_variant(expect: dict[str, Any], force: Any) -> None:
    if not isinstance(force, dict) or str(force.get("step_as") or "") != TRY_LOG_AS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch_log_error requires force_action_error."
            f"step_as == {TRY_LOG_AS!r} (the mock logger cannot fail naturally — "
            f"forcing is the only route into the catch); got {force!r}"
        )
    error = force.get("error")
    if not isinstance(error, str) or not error.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error.error must be explicit")
    checks = (
        expect.get("log_step_as") == CATCH_LOG_AS,
        expect.get("log_message") == error,
        expect.get("catch_message") == error,
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch expect must pin log_step_as {CATCH_LOG_AS!r} "
            f"and log_message == catch_message == the forced error {error!r}; got "
            f"{expect!r}"
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
