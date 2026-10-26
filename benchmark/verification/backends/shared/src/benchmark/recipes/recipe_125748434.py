from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_125748434


RECIPE_ID = "125748434"
SEED_TYPE = "agentic_error_slack_notification_variant"
TRACK = "live_slack_agentic_error_notification"
TRIGGER_PROVIDER = "workato_pub_sub"
TRIGGER_NAME = "subscribe_to_topic"
TRIGGER_AS = "dc957003"
ACCOUNT_PROPERTY = "Agentic.error.channel"
MESSAGE_FIELDS = (
    "job_id", "job_url", "conversation_id", "skill_name", "error",
    "genie", "tags", "recipe_name", "error_channel",
)
REQUIRED_NON_EMPTY = ("error", "recipe_name")
EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("f9b72e2e", "workato_variable", "declare_list"),
    ("ecc2e786", "workato_variable", "insert_to_list"),
    ("37102d1a", "workato_variable", "insert_to_list"),
    ("b61832fa", "workato_variable", "insert_to_list"),
    ("c47fbcde", "workato_variable", "insert_to_list"),
    ("edf02c48", "slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_list",
    "workato_runtime.insert_to_list",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "slack.post_message",
]
_EXPECT_ITEM_KEYS = {
    "tool", "table_id", "lookup_table_id", "match_fields", "channel",
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
}

_RAW_PIN_JSON = r"""{"as": "dc957003", "block": [{"as": "f9b72e2e", "block": [], "input": {"list_item_schema_json": "[{\"name\":\"name\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Name\"},{\"name\":\"value\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Value\"}]", "name": "Fields"}, "keyword": "action", "name": "declare_list", "number": 2, "provider": "workato_variable", "skip": false}, {"as": "", "block": [{"as": "ecc2e786", "block": [], "input": {"list_item": {"name": "Conversation ID", "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"conversation_id\"]}')}"}, "location": "end", "name": "29b6fc31-61a0-4704-be59-89988e5a4f90:f9b72e2e"}, "keyword": "action", "name": "insert_to_list", "number": 4, "provider": "workato_variable", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"conversation_id\"]}')}", "operand": "present", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 3, "provider": "", "skip": false}, {"as": "", "block": [{"as": "37102d1a", "block": [], "input": {"list_item": {"name": "Skill", "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"skill_name\"]}')}"}, "location": "end", "name": "29b6fc31-61a0-4704-be59-89988e5a4f90:f9b72e2e"}, "keyword": "action", "name": "insert_to_list", "number": 6, "provider": "workato_variable", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"skill_name\"]}')}", "operand": "present", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 5, "provider": "", "skip": false}, {"as": "", "block": [{"as": "b61832fa", "block": [], "input": {"list_item": {"name": "Tags", "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"tags\"]}')}"}, "location": "end", "name": "29b6fc31-61a0-4704-be59-89988e5a4f90:f9b72e2e"}, "keyword": "action", "name": "insert_to_list", "number": 8, "provider": "workato_variable", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"tags\"]}')}", "operand": "present", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 7, "provider": "", "skip": false}, {"as": "", "block": [{"as": "c47fbcde", "block": [], "input": {"list_item": {"name": "Job", "value": "<#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"job_url\"]}')}|#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"job_id\"]}')}>"}, "location": "end", "name": "29b6fc31-61a0-4704-be59-89988e5a4f90:f9b72e2e"}, "keyword": "action", "name": "insert_to_list", "number": 10, "provider": "workato_variable", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"job_id\"]}')}", "operand": "present", "rhs": ""}, {"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"job_url\"]}')}", "operand": "present", "rhs": ""}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 9, "provider": "", "skip": false}, {"as": "edf02c48", "block": [], "input": {"attachment_fields": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"f9b72e2e\",\"path\":[\"list_items\"]}')}", "title": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"f9b72e2e\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"name\"]}')}", "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"f9b72e2e\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"value\"]}')}"}, "channel": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\",\"error_channel\"]}').presence || _dp('{\"pill_type\":\"account_property\",\"property_name\":\"Agentic.error.channel\"}')", "message": {"attachment_text": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"error\"]}')}\n***************************", "color": "danger", "pretext": "*Error in Recipe `#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"dc957003\",\"path\":[\"message\", \"recipe_name\"]}')}`*", "title": "::  Error Details  ::"}}, "keyword": "action", "name": "post_bot_message", "number": 11, "provider": "slack_bot", "skip": false}], "input": {"since_offset": "-3600", "topic_id": "51011"}, "keyword": "trigger", "name": "subscribe_to_topic", "number": 1, "provider": "workato_pub_sub", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)


def validate_125748434(raw: dict[str, Any]) -> dict[str, Any]:
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
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "account_property": ACCOUNT_PROPERTY,
        "actions": [
            {"number": a.get("number"), "provider": a.get("provider"),
             "name": a.get("name"), "as": a.get("as")}
            for a in actions
        ],
    }


def seed_125748434(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_125748434(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    if data.get("seed"):
        # Explicit-empty seed ("seed": {}) is the corpus-wide convention for
        # stateless variants; non-empty seeds are still rejected because
        # pub_sub trigger + variable list are in-run state and
        # account_properties is a top-level variant key.
        raise RuntimeError(
            f"recipe {RECIPE_ID} takes no seed state (pub_sub trigger + variable list are "
            "in-run state; account_properties is a top-level variant key)"
        )
    properties = data.get("account_properties")
    if (
        not isinstance(properties, dict)
        or sorted(properties.keys()) != [ACCOUNT_PROPERTY]
        or not isinstance(properties.get(ACCOUNT_PROPERTY), str)
        or not properties[ACCOUNT_PROPERTY].strip()
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must seed account_properties with exactly the "
            f"non-empty {ACCOUNT_PROPERTY!r} property (the channel ||-fallback pill is "
            f"fail-fast); got {properties}"
        )
    expect = data.get("expect")
    _require_expect_shape(expect)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "expect": deepcopy(expect),
        "raw_validation": validation,
        "account_properties": deepcopy(properties),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_125748434(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_125748434(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("account_properties"), dict) or not str(
        seed["account_properties"].get(ACCOUNT_PROPERTY) or ""
    ).strip():
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing account_properties fallback channel")
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    cleanup_response = _cleanup_slack_posts(raw_execution, ctx)
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
            "cleanup_response": cleanup_response,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_125748434(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != ["message"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the pub_sub message object; "
            f"got {sorted(trigger.keys())}"
        )
    message = trigger.get("message")
    if not isinstance(message, dict) or sorted(message.keys()) != sorted(MESSAGE_FIELDS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger message must declare exactly the topic schema fields "
            f"{sorted(MESSAGE_FIELDS)} (blank optionals as explicit ''); got "
            f"{sorted(message.keys()) if isinstance(message, dict) else message}"
        )
    for key, value in message.items():
        if not isinstance(value, str):
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger message.{key} must be an explicit string "
                f"(use '' for blank optionals); got {value!r}"
            )
    for key in REQUIRED_NON_EMPTY:
        if not message[key].strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger message.{key} must be non-empty "
                "(it renders in the post body on every path)"
            )


def _require_expect_shape(expect: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    count = expect.get("executed_action_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.executed_action_count must be an int >= 2 "
            "(declare_list + post always run)"
        )
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or len(items) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin exactly the single live "
            "Slack post"
        )
    item = items[0]
    if not isinstance(item, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[0] must be an object")
    unknown = sorted(set(item.keys()) - _EXPECT_ITEM_KEYS)
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[0] has unrecognized keys: {unknown}")
    if item.get("tool") != "slack.post_message":
        raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[0].tool must be slack.post_message")
    if item.get("channel") != "override":
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0] must assert channel 'override' "
            "(the resolved C-channel is routed to SLACK_CHANNEL_OVERRIDE)"
        )
    args_contains = item.get("args_contains")
    if (
        not isinstance(args_contains, dict)
        or not isinstance(args_contains.get("text"), str)
        or not args_contains["text"].strip()
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0].args_contains.text must pin the FULL "
            "rendered post text (deterministic from the trigger message)"
        )
    fragments = item.get("text_fragments")
    if not isinstance(fragments, list) or not fragments or not all(
        isinstance(fragment, str) and fragment for fragment in fragments
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0].text_fragments must list non-empty "
            "fragments (the slack.post_message strict check requires them)"
        )
    if any(fragment not in args_contains["text"] for fragment in fragments):
        raise RuntimeError(
            f"recipe {RECIPE_ID} every text_fragment must appear in the pinned full text"
        )


def _cleanup_slack_posts(raw_execution: dict[str, Any], ctx: RecipeContext) -> list[dict[str, Any]]:
    cleanup: list[dict[str, Any]] = []
    for row in raw_execution.get("trace") or []:
        if not isinstance(row, dict) or row.get("tool") != "slack.post_message":
            continue
        result = row.get("result") if isinstance(row.get("result"), dict) else {}
        channel = str(result.get("channel") or "")
        ts = str(result.get("ts") or "")
        if channel and ts:
            cleanup.append(ctx.tools.call("slack.delete_message", {"channel": channel, "ts": ts}))
    return cleanup


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
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
