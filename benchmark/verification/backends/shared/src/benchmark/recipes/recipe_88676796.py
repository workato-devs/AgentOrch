from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_88676796


RECIPE_ID = "88676796"
SEED_TYPE = "slack_bot_button_view_design_ticket_variant"
TRACK = "workato_service_slack_button_design_ticket_mock"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "new_event"
TRIGGER_AS = "a18cc028"
EVENT_NAME = "block_actions:button"
FILTER_SUBSTRING = "check_design_tickets"
EMAIL_CALL_AS = "e288d19a"
MODAL_CALL_AS = "8a1debc1"
CATCH_AS = "039d01ad"
APJ_CALL_AS = "2b973332"
EMAIL_FLOW_ID = "45178535"
MODAL_FLOW_ID = "45178957"
APJ_FLOW_ID = "45178280"

# slack_bot.new_event block_actions:button (as a18cc028) with a TRIGGER FILTER:
# actions[current_item].value contains 'check_design_tickets' (substring;
# current_item on the actions array reads the FIRST element, so variants seed
# a single-element actions list to keep the semantics unambiguous).
#   TRY (2):
#     3 workato_service.call_service e288d19a flow 45178535 'Get Email by
#       Slack ID', request.user = button user.id -> seeded reply carries
#       reply.profile.email (fail-fast when the reply is not seeded).
#     4 workato_service.call_service 8a1debc1 flow 45178957 '[Firefighter x
#       Smartsheet] View Design Ticket', request {modal_type 'open',
#       trigger_id, user_email <- step-3 reply.profile.email, user_id,
#       user_name}.
#   CATCH 5 (as 039d01ad, max_retry_count 0):
#     6 workato_service.call_service 2b973332 flow 45178280 'APJ Recipe
#       Errors', request {error_message = catch.039d01ad.message, job_id/
#       job_url/recipe_id = job_context pills, stop_recipe 'false'}.
#     7 STOP stop_with_error true, stop_reason = catch message (the executor
#       records a stopped trace row; stop args are not traced).
#
# FULL MOCK (Workato-internal only): the slack_bot event trigger is seeded
# verbatim, call_service replies come from seed.workato_service_replies
# (fail-fast when a needed key is missing), job_context pills read
# seed.job_context. No live lane, no cleanup.
#
# Probe findings pinned by seeder/variants (current tree, 2026-07-08):
# - A missing reply for the IN-TRY call (8a1debc1) does NOT stop the run: the
#   recipe's own catch swallows it and the run diverts into the error branch.
#   The seeder therefore validates the reply keys per branch (exactly the
#   calls that branch executes) so a mis-seeded happy variant cannot silently
#   pin catch-branch groundtruth.
# - A missing seed.job_context renders the job_id/job_url/recipe_id pills as
#   null SILENTLY - every catch variant must seed job_context explicitly (the
#   seeder enforces it).
# - The trigger filter is a plain substring contains: 'check_design_tickets_
#   2024' matches, 'something_else' does not (both arms probe-verified).

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "slack_bot", "name": "new_event", "as": "a18cc028", "skip": false, "input": {"event_name": "block_actions:button"}, "filter": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"a18cc028\",\"path\":[\"block_actions:button\", \"actions\", {\"path_element_type\": \"current_item\"}, \"value\"]}')}", "operand": "contains", "rhs": "check_design_tickets"}], "operand": "and", "type": "compound"}, "block": [{"number": 2, "keyword": "try", "provider": "", "name": "", "as": "", "skip": false, "input": {}, "block": [{"number": 3, "keyword": "action", "provider": "workato_service", "name": "call_service", "as": "e288d19a", "skip": false, "input": {"flow_id": "45178535", "request": {"user": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"a18cc028\",\"path\":[\"block_actions:button\", \"user\", \"id\"]}')}"}}, "block": []}, {"number": 4, "keyword": "action", "provider": "workato_service", "name": "call_service", "as": "8a1debc1", "skip": false, "input": {"flow_id": "45178957", "request": {"modal_type": "open", "trigger_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"a18cc028\",\"path\":[\"block_actions:button\", \"trigger_id\"]}')}", "user_email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"e288d19a\",\"path\":[\"reply\", \"profile\", \"email\"]}')}", "user_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"a18cc028\",\"path\":[\"block_actions:button\", \"user\", \"id\"]}')}", "user_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"a18cc028\",\"path\":[\"block_actions:button\", \"user\", \"username\"]}')}"}}, "block": []}, {"number": 5, "keyword": "catch", "provider": "", "name": "", "as": "039d01ad", "skip": false, "input": {"max_retry_count": "0", "retry_interval": "2"}, "block": [{"number": 6, "keyword": "action", "provider": "workato_service", "name": "call_service", "as": "2b973332", "skip": false, "input": {"flow_id": "45178280", "request": {"error_message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"039d01ad\",\"path\":[\"message\"]}')}", "job_id": "#{_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_id\"]}')}", "job_url": "#{_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_url\"]}')}", "recipe_id": "#{_dp('{\"pill_type\":\"job_context\",\"path\":[\"recipe_id\"]}')}", "stop_recipe": "false"}}, "block": []}, {"number": 7, "keyword": "stop", "provider": "", "name": "", "as": "", "skip": false, "input": {"stop_reason": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"039d01ad\",\"path\":[\"message\"]}')}", "stop_with_error": "true"}, "block": []}]}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[int, str, str, str]] = [
    (3, EMAIL_CALL_AS, "workato_service", "call_service"),
    (4, MODAL_CALL_AS, "workato_service", "call_service"),
    (6, APJ_CALL_AS, "workato_service", "call_service"),
]
EXPECTED_RAW_TOOLS: list[str] = ["workato_service.call_service"]
ALLOWED_TOOLS: list[str] = ["workato_service.call_service"]
REQUIRED_EXPECT_KEYS = (
    "branch",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "trigger_filter_matched",
    "stopped",
    "catch_message",
)
BRANCHES = ("filter_false_no_run", "happy_path_two_calls", "catch_error_stop")
REPLY_KEYS_BY_BRANCH = {
    "happy_path_two_calls": [EMAIL_CALL_AS, MODAL_CALL_AS],
    "catch_error_stop": [APJ_CALL_AS, EMAIL_CALL_AS],
}


def validate_88676796(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    if str((raw.get("input") or {}).get("event_name") or "") != EVENT_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger event changed")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    trigger_filter = raw.get("filter")
    if not isinstance(trigger_filter, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger filter missing")
    conditions = trigger_filter.get("conditions") or [{}]
    condition = conditions[0] if isinstance(conditions[0], dict) else {}
    if (
        len(conditions) != 1
        or condition.get("operand") != "contains"
        or condition.get("rhs") != FILTER_SUBSTRING
        or "current_item" not in str(condition.get("lhs") or "")
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger filter changed: {trigger_filter!r}")
    actions = _collect_actions(raw)
    actual = [
        (a.get("number"), str(a.get("as")), str(a.get("provider")), str(a.get("name")))
        for a in actions
    ]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    flow_ids = {
        str(a.get("as")): str((a.get("input") or {}).get("flow_id") or "") for a in actions
    }
    if flow_ids != {
        EMAIL_CALL_AS: EMAIL_FLOW_ID,
        MODAL_CALL_AS: MODAL_FLOW_ID,
        APJ_CALL_AS: APJ_FLOW_ID,
    }:
        raise RuntimeError(f"recipe {RECIPE_ID} called flow ids changed: {flow_ids}")
    control = {
        (str(node.get("keyword") or ""), int(node.get("number") or 0)): node
        for node in _walk_nodes(raw)
        if node.get("keyword") in {"try", "catch", "if", "foreach", "stop", "else"}
    }
    if sorted(control) != [("catch", 5), ("stop", 7), ("try", 2)]:
        raise RuntimeError(f"recipe {RECIPE_ID} control nodes changed: {sorted(control)}")
    catch_node = control[("catch", 5)]
    if str(catch_node.get("as") or "") != CATCH_AS or catch_node.get("input") != {
        "max_retry_count": "0",
        "retry_interval": "2",
    }:
        raise RuntimeError(f"recipe {RECIPE_ID} catch node changed")
    stop_node = control[("stop", 7)]
    if str((stop_node.get("input") or {}).get("stop_with_error") or "") != "true":
        raise RuntimeError(f"recipe {RECIPE_ID} stop node lost stop_with_error")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "event_name": EVENT_NAME,
        "filter_substring": FILTER_SUBSTRING,
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


def seed_88676796(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88676796(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    button = _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    expect = data.get("expect")
    _require_expect_common(expect)
    branch = expect["branch"]
    action_value = str(button["actions"][0].get("value") or "")
    filter_hit = FILTER_SUBSTRING in action_value
    force = data.get("force_action_error")
    job_context = data.get("job_context")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
    }
    if branch == "filter_false_no_run":
        _require_filter_false_variant(seed_in, expect, filter_hit, force, job_context)
    elif branch == "happy_path_two_calls":
        _require_happy_variant(seed_in, expect, filter_hit, force, job_context)
        out["workato_service_replies"] = deepcopy(seed_in["workato_service_replies"])
    else:  # catch_error_stop
        _require_catch_variant(seed_in, expect, filter_hit, force, job_context)
        out["workato_service_replies"] = deepcopy(seed_in["workato_service_replies"])
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_88676796(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88676796(raw)
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
            # Full mock (Workato-internal only): nothing live to snapshot or
            # clean up.
            "initial_snapshot": {},
            "final_snapshot": {},
            "cleanup_response": None,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_88676796(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> dict[str, Any]:
    if sorted(trigger.keys()) != [EVENT_NAME]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the "
            f"{EVENT_NAME!r} payload; got {sorted(trigger.keys())}"
        )
    button = trigger.get(EVENT_NAME)
    if not isinstance(button, dict) or not button:
        raise RuntimeError(f"recipe {RECIPE_ID} {EVENT_NAME} payload must be a non-empty object")
    if not str(button.get("trigger_id") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} payload needs a non-empty trigger_id (modal pill)")
    user = button.get("user")
    if (
        not isinstance(user, dict)
        or not str(user.get("id") or "").strip()
        or not str(user.get("username") or "").strip()
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} payload.user needs non-empty id and username "
            f"(both are dereferenced); got {user!r}"
        )
    actions = button.get("actions")
    if not isinstance(actions, list) or len(actions) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} payload.actions must be a SINGLE-element list: the "
            "trigger filter reads actions[current_item].value which resolves to the "
            "first element only (probe-verified); a longer list would hide dead data"
        )
    if not isinstance(actions[0], dict) or not isinstance(actions[0].get("value"), str):
        raise RuntimeError(
            f"recipe {RECIPE_ID} payload.actions[0].value must be an explicit string"
        )
    return button


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


def _require_replies(seed_in: dict[str, Any], branch: str) -> dict[str, Any]:
    replies = seed_in.get("workato_service_replies")
    expected_keys = sorted(REPLY_KEYS_BY_BRANCH[branch])
    if not isinstance(replies, dict) or sorted(replies.keys()) != expected_keys:
        raise RuntimeError(
            f"recipe {RECIPE_ID} {branch} must seed workato_service_replies for "
            f"exactly {expected_keys} (a missing in-try reply key would silently "
            f"divert into the catch instead of failing fast); got "
            f"{sorted(replies.keys()) if isinstance(replies, dict) else replies!r}"
        )
    for key, reply in replies.items():
        if not isinstance(reply, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} reply for {key} must be an object")
    email_reply = replies.get(EMAIL_CALL_AS) or {}
    profile = email_reply.get("profile")
    if not isinstance(profile, dict) or not str(profile.get("email") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} the {EMAIL_CALL_AS} reply must carry a non-empty "
            "profile.email (step 4 dereferences reply.profile.email)"
        )
    return replies


def _require_filter_false_variant(
    seed_in: dict[str, Any],
    expect: dict[str, Any],
    filter_hit: bool,
    force: Any,
    job_context: Any,
) -> None:
    if filter_hit:
        raise RuntimeError(
            f"recipe {RECIPE_ID} filter_false_no_run needs actions[0].value WITHOUT "
            f"the {FILTER_SUBSTRING!r} substring"
        )
    if sorted(seed_in.keys()) != [] or force is not None or job_context is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} filter_false_no_run seeds nothing (no replies, no "
            f"force, no job_context); got seed keys {sorted(seed_in.keys())}"
        )
    checks = (
        expect.get("executed_action_count") == 0,
        expect.get("tools") == [],
        expect.get("tool_expectations") == [],
        expect.get("trigger_filter_matched") is False,
        expect.get("stopped") is False,
        expect.get("catch_message") is None,
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} filter_false expect block is inconsistent (0 actions, "
            f"filter unmatched, no stop): {expect!r}"
        )


def _require_happy_variant(
    seed_in: dict[str, Any],
    expect: dict[str, Any],
    filter_hit: bool,
    force: Any,
    job_context: Any,
) -> None:
    if not filter_hit:
        raise RuntimeError(
            f"recipe {RECIPE_ID} happy_path_two_calls needs actions[0].value carrying "
            f"the {FILTER_SUBSTRING!r} substring"
        )
    if force is not None:
        raise RuntimeError(f"recipe {RECIPE_ID} happy variants must not force an action error")
    if job_context is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} happy variants never read job_context; seeding it "
            "would hide dead data"
        )
    if sorted(seed_in.keys()) != ["workato_service_replies"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} happy variants seed exactly workato_service_replies; "
            f"got {sorted(seed_in.keys())}"
        )
    _require_replies(seed_in, "happy_path_two_calls")
    checks = (
        expect.get("executed_action_count") == 2,
        expect.get("tools") == ["workato_service.call_service"] * 2,
        expect.get("trigger_filter_matched") is True,
        expect.get("stopped") is False,
        expect.get("catch_message") is None,
        len(expect.get("tool_expectations") or []) == 2,
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} happy expect block is inconsistent (2 call_service, "
            f"no stop): {expect!r}"
        )


def _require_catch_variant(
    seed_in: dict[str, Any],
    expect: dict[str, Any],
    filter_hit: bool,
    force: Any,
    job_context: Any,
) -> None:
    if not filter_hit:
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch variants need the trigger filter to match "
            "(the try body must run to fail)"
        )
    if not isinstance(force, dict) or str(force.get("step_as") or "") != MODAL_CALL_AS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch variants must declare force_action_error."
            f"step_as == {MODAL_CALL_AS!r} (the modal call is the deliberate failure "
            "point after the email call succeeded)"
        )
    if not str(force.get("error") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error.error must be explicit")
    if not isinstance(job_context, dict) or sorted(job_context.keys()) != [
        "job_id",
        "job_url",
        "recipe_id",
    ] or not all(str(job_context[key]).strip() for key in job_context):
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch variants MUST seed job_context with non-empty "
            "job_id/job_url/recipe_id: missing job_context renders the pills null "
            f"SILENTLY (probe-verified caveat); got {job_context!r}"
        )
    if sorted(seed_in.keys()) != ["workato_service_replies"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch variants seed exactly workato_service_replies; "
            f"got {sorted(seed_in.keys())}"
        )
    _require_replies(seed_in, "catch_error_stop")
    checks = (
        expect.get("executed_action_count") == 2,
        expect.get("tools") == ["workato_service.call_service"] * 2,
        expect.get("trigger_filter_matched") is True,
        expect.get("stopped") is True,
        str(expect.get("catch_message") or "") == str(force.get("error") or ""),
        len(expect.get("tool_expectations") or []) == 2,
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch expect block is inconsistent (email call + APJ "
            f"call, stopped true, catch_message == forced error): {expect!r}"
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
