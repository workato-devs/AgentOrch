from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_85944692


RECIPE_ID = "85944692"
SEED_TYPE = "slack_block_confirm_completion_variant"
TRACK = "live_slack_block_update_confirm"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"
TRIGGER_AS = "2849d972"
UPDATE_AS = "74ec3e0a"
CATCH_AS = "8471803f"
LOGGER_AS = "70301f6f"
REPLACEMENT_SECTION_TEXT = ":white_check_mark: Marked as completed"
REPLACEMENT_INPUT_BLOCK = {
    "block_type": "section_with_text",
    "button_type": "continue_flow",
    "section_text": REPLACEMENT_SECTION_TEXT,
}


_STRUCTURE_PINS_JSON = r'''
[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "2849d972",
  "provider": "slack_bot",
  "name": "bot_command_v2",
  "skip": false,
  "input": {
   "allow_dialog": "false",
   "domain": "certinia",
   "name": "confirm",
   "parameters": "[\n  {\n    \"name\": \"blockId\",\n    \"type\": \"string\",\n    \"optional\": true,\n    \"control_type\": \"text\",\n    \"label\": \"Block Id - Slack Bot\"\n  }\n]",
   "scope": "reminder"
  }
 },
 {
  "keyword": "try",
  "number": 2,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {}
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "74ec3e0a",
  "provider": "slack_bot",
  "name": "update_blocks_by_block_id",
  "skip": false,
  "input": {
   "blocks_to_update": [
    {
     "block_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"2849d972\",\"path\":[\"parameters\", \"blockid\"]}')}",
     "blocks": [
      {
       "block_type": "section_with_text",
       "button_type": "continue_flow",
       "section_text": ":white_check_mark: Marked as completed"
      }
     ],
     "remove_block": "false"
    }
   ],
   "message_json": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"2849d972\",\"path\":[\"context\", \"original_message_json\"]}')}",
   "surface": "message"
  }
 },
 {
  "keyword": "catch",
  "number": 4,
  "as": "8471803f",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "max_retry_count": "0",
   "retry_interval": "2"
  }
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "70301f6f",
  "provider": "logger",
  "name": "log_message",
  "skip": false,
  "input": {
   "message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"8471803f\",\"path\":[\"type\"]}')} : #{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"8471803f\",\"path\":[\"message\"]}')}",
   "user_logs_enabled": "false"
  }
 }
]
'''

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "slack.update_blocks_by_block_id",
    "workato_runtime.log_message",
]
ALLOWED_TOOLS: list[str] = [
    "slack.update_blocks_by_block_id",
]
UPDATE_BRANCHES = ("confirm_replaces_block", "target_mid_message_multi_block")
CATCH_BRANCH = "catch_logs_type_and_message"
BRANCHES = UPDATE_BRANCHES + (CATCH_BRANCH,)
COMMON_EXPECT_KEYS = ("branch", "executed_action_count", "tools", "tool_expectations")
UPDATE_EXPECT_KEYS = COMMON_EXPECT_KEYS + ("target_block_id", "final_blocks")
CATCH_EXPECT_KEYS = COMMON_EXPECT_KEYS + ("catch_error", "log_message")
_EXPECT_ITEM_KEYS = {
    "tool", "table_id", "lookup_table_id", "match_fields", "channel",
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
}
_EXPECT_VALUE_KEYS = {
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
}


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


def validate_85944692(raw: dict[str, Any]) -> dict[str, Any]:
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


def replacement_block(target_id: str) -> dict[str, Any]:
    # Exactly what slack_live._modal_block renders for the raw
    # section_with_text replacement input (probe-verified): the replacement
    # inherits the TARGET block_id; button_type 'continue_flow' with no
    # button_title adds no accessory.
    return {
        "type": "section",
        "block_id": target_id,
        "text": {"type": "mrkdwn", "text": REPLACEMENT_SECTION_TEXT},
    }


def derive_final_blocks(seed_blocks: list[dict[str, Any]], target_id: str) -> list[dict[str, Any]]:
    return [
        replacement_block(target_id) if str(block.get("block_id") or "") == target_id else deepcopy(block)
        for block in seed_blocks
    ]


def seed_85944692(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_85944692(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    trigger = trigger_input(ctx)
    blockid = _require_trigger_shape(trigger)
    seed_message = data.get("slack_seed_message")
    text, blocks = _require_seed_message(seed_message, blockid)
    expect = data.get("expect")
    branch = _require_expect_shape(expect, blockid=blockid, blocks=blocks)
    force = data.get("force_action_error")
    if branch == CATCH_BRANCH:
        _require_force_shape(force, expect)
    elif force is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error is only sanctioned for the "
            f"{CATCH_BRANCH!r} branch; got branch {branch!r}"
        )

    # LIVE seed: post the bot-owned message the trigger context points at.
    # The injected original_message_json MUST be the real posted message
    # (channel+ts) — the engine fail-fasts on a JSON without them.
    posted = ctx.tools.call(
        "harness.slack.seed_message",
        {"channel": ctx.env.slack_channel_override, "text": text, "blocks": blocks},
    )
    channel = str(posted.get("channel") or ctx.env.slack_channel_override)
    ts = str(posted.get("ts") or "")
    if not ts:
        raise RuntimeError(f"recipe {RECIPE_ID} Slack seed message returned no ts: {posted}")
    context = trigger.setdefault("context", {})
    context["original_message_json"] = json.dumps(
        {"channel": channel, "ts": ts, "text": text, "blocks": blocks},
        sort_keys=True,
    )

    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": deepcopy(expect),
        "seed_slack_message": {"channel": channel, "ts": ts, "text": text, "blocks": deepcopy(blocks)},
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if branch == CATCH_BRANCH:
        out["force_action_error"] = deepcopy(force)
    return attach_variant(out, ctx)


def run_85944692(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_85944692(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    message = seed.get("seed_slack_message") if isinstance(seed.get("seed_slack_message"), dict) else {}
    if not (message.get("channel") and message.get("ts")):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing the live seed_slack_message ts")
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    if expect.get("branch") == CATCH_BRANCH and not isinstance(seed.get("force_action_error"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} catch-branch seed lost its force_action_error")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_slack_message": deepcopy(message),
        "expected_channel": ctx.env.slack_channel_override,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    cleanup_response: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
    finally:
        # Required cleanup (rerun determinism): the run chat.updates the
        # bot-owned seeded message in place — delete it so reruns never see
        # (or re-update) a stale message. Fail-fast on a failed delete.
        cleanup_response = ctx.tools.call(
            "slack.delete_message",
            {"channel": message["channel"], "ts": message["ts"]},
        )
        details["cleanup_response"] = cleanup_response
    if not cleanup_response.get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Slack cleanup failed: {cleanup_response}")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_85944692(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> str:
    if sorted(trigger.keys()) != ["parameters"] or not isinstance(trigger.get("parameters"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'parameters': ...}} "
            "(the seeder injects context.original_message_json from the live post)"
        )
    parameters = trigger["parameters"]
    if sorted(parameters.keys()) != ["blockid"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must carry exactly the LOWERCASE "
            f"'blockid' key (the pill path; a camelCase 'blockId' silently misses it "
            f"and routes to the catch); got {sorted(parameters.keys())}"
        )
    blockid = parameters["blockid"]
    if not isinstance(blockid, str) or not blockid.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} parameters.blockid must be a non-empty string")
    return blockid


def _require_seed_message(seed_message: Any, blockid: str) -> tuple[str, list[dict[str, Any]]]:
    if not isinstance(seed_message, dict) or sorted(seed_message.keys()) != ["blocks", "text"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} every variant must declare slack_seed_message "
            "{'text': ..., 'blocks': ...} (the message the confirm button lives on)"
        )
    text = seed_message["text"]
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} slack_seed_message.text must be a non-empty string")
    blocks = seed_message["blocks"]
    if not isinstance(blocks, list) or len(blocks) < 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} slack_seed_message.blocks must carry at least 2 raw "
            "Block Kit blocks (an in-place replacement among untouched neighbours is "
            "the observable)"
        )
    ids: list[str] = []
    for idx, block in enumerate(blocks):
        if not isinstance(block, dict) or not str(block.get("type") or ""):
            raise RuntimeError(f"recipe {RECIPE_ID} seed block {idx} must be a raw Block Kit object")
        block_id = block.get("block_id")
        if not isinstance(block_id, str) or not block_id.strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed block {idx} must pin an explicit block_id "
                "(the recipe addresses blocks by id)"
            )
        ids.append(block_id)
    if len(set(ids)) != len(ids):
        raise RuntimeError(f"recipe {RECIPE_ID} seed block_ids must be unique: {ids}")
    if ids.count(blockid) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger blockid {blockid!r} must match exactly ONE "
            f"seeded block (an unmatched id APPENDS the replacement — a data hazard, "
            f"not a sanctioned variant); seeded ids {ids}"
        )
    return text, blocks


def _require_force_shape(force: Any, expect: dict[str, Any]) -> None:
    if not isinstance(force, dict) or sorted(force.keys()) != ["error", "step_as"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the catch branch requires force_action_error "
            "{'step_as': '74ec3e0a', 'error': ...}"
        )
    if force.get("step_as") != UPDATE_AS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error.step_as must be {UPDATE_AS!r} "
            f"(the only try-body step); got {force.get('step_as')!r}"
        )
    error = force.get("error")
    if not isinstance(error, str) or not error.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error.error must be a non-empty string")
    if expect.get("catch_error") != error:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.catch_error must equal the forced error text "
            f"{error!r}; got {expect.get('catch_error')!r}"
        )
    expected_log = f"RawRecipeExecutionError : {error}"
    if expect.get("log_message") != expected_log:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.log_message must be {expected_log!r} "
            "(catch.type renders the exception class name); got "
            f"{expect.get('log_message')!r}"
        )


def _require_expect_shape(expect: Any, *, blockid: str, blocks: list[dict[str, Any]]) -> str:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    branch = expect.get("branch")
    if branch not in BRANCHES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch must be one of {BRANCHES}; got {branch!r}")
    required = CATCH_EXPECT_KEYS if branch == CATCH_BRANCH else UPDATE_EXPECT_KEYS
    missing = [key for key in required if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(set(expect) - set(required))
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has unexpected keys: {unknown}")
    if expect["executed_action_count"] != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.executed_action_count must be 1 on every branch "
            "(one chat.update OR one catch-logger step)"
        )
    items = expect.get("tool_expectations")
    if not isinstance(items, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must be a list")
    for idx, item in enumerate(items):
        if not isinstance(item, dict) or not item.get("tool"):
            raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[{idx}] must be an object with a tool")
        unknown_keys = sorted(set(item.keys()) - _EXPECT_ITEM_KEYS)
        if unknown_keys:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] has unsupported keys: {unknown_keys}"
            )
        if not (set(item.keys()) & _EXPECT_VALUE_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] must pin at least one VALUE key "
                f"({sorted(_EXPECT_VALUE_KEYS)})"
            )
    if branch == CATCH_BRANCH:
        if expect["tools"] != [] or items != []:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch branch: expect.tools and tool_expectations must "
                "be [] (the forced error fires before chat.update; the logger is an "
                "internal runtime marker outside tool_calls) — the fragment pins the "
                "logged catch text instead"
            )
        return branch
    if expect["tools"] != ALLOWED_TOOLS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} update branches: expect.tools must be {ALLOWED_TOOLS}"
        )
    if expect.get("target_block_id") != blockid:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.target_block_id must equal trigger blockid "
            f"{blockid!r}; got {expect.get('target_block_id')!r}"
        )
    expected_final = derive_final_blocks(blocks, blockid)
    if expect.get("final_blocks") != expected_final:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_blocks must pin the in-place replacement "
            f"result exactly: {json.dumps(expected_final, ensure_ascii=False)}"
        )
    if len(items) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} update branches: tool_expectations must pin exactly the "
            "one slack.update_blocks_by_block_id call"
        )
    expected_args = {
        "message_json": "__ANY__",
        "blocks_to_update": [
            {
                "block_id": blockid,
                "blocks": [dict(REPLACEMENT_INPUT_BLOCK)],
                "remove_block": "false",
            }
        ],
    }
    item = items[0]
    if item.get("tool") != "slack.update_blocks_by_block_id" or item.get("args_contains") != expected_args:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0] must pin the verbatim "
            f"blocks_to_update (message_json is seed-dependent -> '__ANY__'): "
            f"{json.dumps(expected_args, ensure_ascii=False)}"
        )
    return branch


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
