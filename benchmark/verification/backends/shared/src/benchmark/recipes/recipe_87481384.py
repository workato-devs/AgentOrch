from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_87481384


RECIPE_ID = "87481384"
SEED_TYPE = "slack_bot_lookup_table_product_update_variant"
TRACK = "workato_lookup_table_slack_bot_product_update"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"
TRIGGER_AS = "4a3ee5e6"
LOOKUP_TABLE_ID = "2257714"
SEARCH_STEP_AS = "06e12221"
UPDATE_STEP_AS = "ea1b2bce"
POST_STEP_AS = "88f90b2b"
CATCH_STEP_AS = "9e0d5d07"
NOT_FOUND_STOP_STEP = 5
DUPLICATED_STOP_STEP = 7
ERROR_STOP_STEP = 12
FORCEABLE_STEPS = {SEARCH_STEP_AS, UPDATE_STEP_AS}
REQUIRED_TRIGGER_PARAMS = ("product_id", "orig_conv_id", "orig_message_id")
OPTIONAL_TRIGGER_PARAMS = ("product_name", "category", "product_family", "true_quantity", "active")
SEED_MSG_CHANNEL_TOKEN = "$SEED_MSG_CHANNEL"
SEED_MSG_TS_TOKEN = "$SEED_MSG_TS"

# slack_bot.bot_command_v2 (as 4a3ee5e6, domain firefighter, command
# 'updated', scope lut_salesforce_products): parameters {product_id*,
# product_name, category, product_family, true_quantity(int), active,
# orig_conv_id*, orig_message_id*}. Body (one big TRY, catch 9e0d5d07):
#   3  lookup_table.search_entries 06e12221 table 2257714 col4 = product_id
#      (Workato-internal mock table '[WORK] Salesforce Products')
#   4  IF entries size < 1  -> 5 STOP stop_with_error=true 'Product not found?'
#   6  IF entries size > 1  -> 7 STOP stop_with_error=true 'Duplicated products found'
#   8  IF entries size == 1 -> 9 lookup_table.update_entry ea1b2bce
#      id = entries.current_item.id, ignore_not_found=false, col1/2/3/5/6 =
#      '<param>.presence or skip' (blank/absent params are OMITTED from the
#      update -- presence-or-skip probed green on the current engine)
#   10 slack_bot.post_bot_message 88f90b2b (LIVE slack): channel =
#      parameters.orig_conv_id, advanced.ts = parameters.orig_message_id ->
#      the executor maps this to slack.post_message with a non-empty ts,
#      i.e. a live chat.update EDIT of the seeded command message. Rendered
#      text = section block ('All good! ...Lookup Table>!') + context element
#      (multiline if category.present? 'New category: ...' else 'Have a great
#      day!' end) + 5 attachment fields (Name/Category/Family/True Quantity
#      backtick-wrapped from the ea1b2bce update output; Active is the
#      == "true" ternary rendering :firefighter_check:/:firefighter_cross:).
#      message.footer (Product2 lightning link) and attachment_buttons [{}]
#      are metadata: slack_text never renders them (footer pinned in the
#      structure pins only).
#   CATCH 11 (as 9e0d5d07, max_retry_count=0) -> 12 STOP stop_with_error=true
#      stop_reason = catch message pill (stop rows carry no reason in the
#      trace; the catch payload is asserted via raw_execution.data.catch).
#
# Branch mapping (per benmark_rules):
# - variant_00 single_match_full_update_active_true: 1 matching row, all
#   optional params present, active='true' -> update writes col1/2/3/5/6,
#   context 'New category: ...', Active ':firefighter_check: true'.
# - variant_01 single_match_partial_skip_inactive: 1 matching row,
#   product_name/category blank + product_family/true_quantity absent,
#   active='false' -> update carries ONLY col6 (presence-or-skip), context
#   'Have a great day!', Active ':firefighter_cross: false'.
# - variant_02 not_found_stop: no col4 match (decoy row seeded) -> STOP 5
#   after exactly one action.
# - variant_03 duplicated_stop: two col4 matches -> STOP 7 after one action.
# - variant_04 catch_error_stop: forced error on the 06e12221 search -> catch
#   -> STOP 12; zero actions traced (the forced error raises before the tool
#   call), catch payload message = forced error.
#
# Backends: lookup_table is a Workato-internal deterministic mock (per-variant
# state file; the seed fully overwrites the table every run -> deterministic
# reruns per the cleanup principle, no cleanup step). Slack runs LIVE: post
# variants seed a real command message (harness.slack.seed_message) and thread
# its channel/ts into the trigger parameters via $SEED_MSG_* tokens; the
# recipe's chat.update edit of that benchmark-owned message is the observable
# artifact and is never re-read afterwards (no cleanup required). Stop/catch
# variants never reach the post step and carry explicit placeholder
# channel/ts literals instead of a live seed.

_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "4a3ee5e6",
  "provider": "slack_bot",
  "name": "bot_command_v2",
  "skip": false,
  "input": {
   "allow_dialog": "false",
   "domain": "firefighter",
   "hide_from_help": "true",
   "name": "updated",
   "parameters": "[\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Product ID\",\n    \"name\": \"product_id\",\n    \"type\": \"string\",\n    \"optional\": false\n  },\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Product Name\",\n    \"name\": \"product_name\",\n    \"type\": \"string\",\n    \"optional\": true,\n    \"prompt\": false\n  },\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Category\",\n    \"name\": \"category\",\n    \"type\": \"string\",\n    \"optional\": true,\n    \"prompt\": false\n  },\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Product Family\",\n    \"name\": \"product_family\",\n    \"type\": \"string\",\n    \"optional\": true,\n    \"prompt\": false\n  },\n  {\n    \"control_type\": \"text\",\n    \"label\": \"True Quantity\",\n    \"parse_output\": \"integer_conversion\",\n    \"name\": \"true_quantity\",\n    \"type\": \"integer\",\n    \"optional\": true,\n    \"prompt\": false\n  },\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Active\",\n    \"name\": \"active\",\n    \"type\": \"string\",\n    \"optional\": true,\n    \"prompt\": false\n  },\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Original Conversation ID\",\n    \"name\": \"orig_conv_id\",\n    \"type\": \"string\",\n    \"optional\": false\n  },\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Original Message ID\",\n    \"name\": \"orig_message_id\",\n    \"type\": \"string\",\n    \"optional\": false\n  }\n]",
   "scope": "lut_salesforce_products"
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
  "as": "06e12221",
  "provider": "lookup_table",
  "name": "search_entries",
  "skip": false,
  "input": {
   "lookup_table_id": "2257714",
   "parameters": {
    "col4": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"4a3ee5e6\",\"path\":[\"parameters\", \"product_id\"]}')}"
   }
  }
 },
 {
  "keyword": "if",
  "number": 4,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"06e12221\",\"path\":[\"entries\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "less_than",
     "rhs": "1"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "stop",
  "number": 5,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "stop_reason": "Product not found?",
   "stop_with_error": "true"
  }
 },
 {
  "keyword": "if",
  "number": 6,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"06e12221\",\"path\":[\"entries\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "greater_than",
     "rhs": "1"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "stop",
  "number": 7,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "stop_reason": "Duplicated products found",
   "stop_with_error": "true"
  }
 },
 {
  "keyword": "if",
  "number": 8,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"06e12221\",\"path\":[\"entries\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "equals_to",
     "rhs": "1"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 9,
  "as": "ea1b2bce",
  "provider": "lookup_table",
  "name": "update_entry",
  "skip": false,
  "input": {
   "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"06e12221\",\"path\":[\"entries\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}",
   "ignore_not_found": "false",
   "lookup_table_id": "2257714",
   "parameters": {
    "col1": "=_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"4a3ee5e6\",\"path\":[\"parameters\",\"product_name\"]}').presence or skip",
    "col2": "=_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"4a3ee5e6\",\"path\":[\"parameters\",\"category\"]}').presence or skip",
    "col3": "=_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"4a3ee5e6\",\"path\":[\"parameters\",\"product_family\"]}').presence or skip",
    "col5": "=_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"4a3ee5e6\",\"path\":[\"parameters\",\"true_quantity\"]}').presence or skip",
    "col6": "=_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"4a3ee5e6\",\"path\":[\"parameters\",\"active\"]}').presence or skip"
   }
  }
 },
 {
  "keyword": "action",
  "number": 10,
  "as": "88f90b2b",
  "provider": "slack_bot",
  "name": "post_bot_message",
  "skip": false,
  "input": {
   "advanced": {
    "ts": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"4a3ee5e6\",\"path\":[\"parameters\", \"orig_message_id\"]}')}"
   },
   "attachment_buttons": [
    {}
   ],
   "attachment_fields": [
    {
     "title": "Name",
     "value": "`#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"ea1b2bce\",\"path\":[\"entry\", \"col1\"]}')}`"
    },
    {
     "title": "Category",
     "value": "`#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"ea1b2bce\",\"path\":[\"entry\", \"col2\"]}')}`"
    },
    {
     "title": "Family",
     "value": "`#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"ea1b2bce\",\"path\":[\"entry\", \"col3\"]}')}`"
    },
    {
     "title": "True Quantity",
     "value": "`#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"ea1b2bce\",\"path\":[\"entry\", \"col5\"]}')}`"
    },
    {
     "title": "Active",
     "value": "=_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"ea1b2bce\",\"path\":[\"entry\",\"col6\"]}') == \"true\" ? \":firefighter_check: #{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"ea1b2bce\",\"path\":[\"entry\",\"col6\"]}')}\" : \":firefighter_cross: #{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"ea1b2bce\",\"path\":[\"entry\",\"col6\"]}')}\""
    }
   ],
   "blocks": [
    {
     "block_type": "section_with_text",
     "button_type": "continue_flow",
     "section_text": "All good! :firefighter_5: \n\nI've completed the updates to our <https://app.workato.com/lookup_tables/2257714|Lookup Table>!"
    },
    {
     "block_type": "divider",
     "button_type": "continue_flow"
    },
    {
     "block_type": "context",
     "button_type": "continue_flow",
     "elements": [
      {
       "text": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"4a3ee5e6\",\"path\":[\"parameters\",\"category\"]}').present?\n  \"New category: #{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"4a3ee5e6\",\"path\":[\"parameters\",\"category\"]}')}. Might wna check if you need to update <https://app.workato.com/recipes/23099448|Salesforce Products Mapper>!\"\nelse\n  \"Have a great day!\"\nend",
       "type": "text"
      }
     ]
    }
   ],
   "channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"4a3ee5e6\",\"path\":[\"parameters\", \"orig_conv_id\"]}')}",
   "message": {
    "color": "good",
    "footer": "<https://workato.lightning.force.com/lightning/r/Product2/#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"4a3ee5e6\",\"path\":[\"parameters\", \"product_id\"]}')}/view|Product ID: #{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"4a3ee5e6\",\"path\":[\"parameters\", \"product_id\"]}')}>"
   }
  }
 },
 {
  "keyword": "catch",
  "number": 11,
  "as": "9e0d5d07",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "max_retry_count": "0",
   "retry_interval": "2"
  }
 },
 {
  "keyword": "stop",
  "number": 12,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "stop_reason": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"9e0d5d07\",\"path\":[\"message\"]}')}",
   "stop_with_error": "true"
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "lookup_table.update_entry",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "lookup_table.update_entry",
    "slack.post_message",
]
EXPECT_KEYS = ("executed_action_count", "tools", "tool_expectations", "stopped", "final_lookup_rows")
OPTIONAL_EXPECT_KEYS = {"case", "stop_step_number", "catch_message", "slack_text"}


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


def validate_87481384(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_87481384(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_87481384(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"lookup_table"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    expect = data.get("expect")
    force = data.get("force_action_error")
    _require_force_shape(force)
    _require_expect_shape(expect, force)
    _require_lookup_section(seed_in.get("lookup_table"), trigger, expect)
    expect = deepcopy(expect)
    parameters = trigger["parameters"]
    post_expected = "slack.post_message" in (expect.get("tools") or [])
    uses_tokens = SEED_MSG_CHANNEL_TOKEN in json.dumps(data)
    if post_expected != uses_tokens:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the $SEED_MSG_* tokens must be used exactly when the "
            f"variant expects the slack post (post_expected={post_expected})"
        )
    if post_expected:
        if (
            parameters.get("orig_conv_id") != SEED_MSG_CHANNEL_TOKEN
            or parameters.get("orig_message_id") != SEED_MSG_TS_TOKEN
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} post variants must thread orig_conv_id/orig_message_id "
                f"through {SEED_MSG_CHANNEL_TOKEN}/{SEED_MSG_TS_TOKEN} (live-seeded message)"
            )
        if not ctx.env.slack_channel_override:
            raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
        posted = ctx.tools.call("harness.slack.seed_message", {
            "channel": ctx.env.slack_channel_override,
            "text": (
                f"benchmark seed for recipe {RECIPE_ID} "
                f"variant {int(data.get('variant', 0) or 0):02d}: firefighter updated command"
            ),
        })
        seed_ts = str(posted.get("ts") or "")
        if not seed_ts:
            raise RuntimeError(f"recipe {RECIPE_ID} Slack seed message returned no ts: {posted}")
        seed_channel = str(posted.get("channel") or ctx.env.slack_channel_override)
        tokens = {SEED_MSG_CHANNEL_TOKEN: seed_channel, SEED_MSG_TS_TOKEN: seed_ts}
        trigger = _replace_tokens(trigger, tokens)
        expect = _replace_tokens(expect, tokens)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": expect,
        "lookup_table": deepcopy(seed_in["lookup_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_87481384(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_87481384(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
    if "slack.post_message" in (expect.get("tools") or []) and not ctx.env.slack_channel_override:
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
    details["initial_snapshot"] = _snapshot(ctx)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    details["raw_execution"] = raw_execution
    details["ground_truth"] = _ground_truth(raw_execution)
    details["final_snapshot"] = _snapshot(ctx)
    # Cleanup per the cleanup principle: the lookup table is a per-variant
    # mock whose state the seed fully overwrites on every run, and the live
    # Slack edit targets the message this run's own seed created (which is
    # never re-read afterwards) -- no cleanup step is required for
    # deterministic reruns.
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_87481384(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {"parameters"} or not isinstance(trigger.get("parameters"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input must be exactly {{'parameters': {{...}}}}")
    parameters = trigger["parameters"]
    extra = sorted(set(parameters) - set(REQUIRED_TRIGGER_PARAMS) - set(OPTIONAL_TRIGGER_PARAMS))
    if extra:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters has undeclared fields: {extra}")
    for key in REQUIRED_TRIGGER_PARAMS:
        if not isinstance(parameters.get(key), str) or not parameters[key].strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger parameter {key!r} must be a non-empty string "
                "(the command schema marks it required)"
            )
    if "true_quantity" in parameters and not isinstance(parameters["true_quantity"], (int, str)):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameter true_quantity must be an int or string "
            "(integer_conversion command parameter)"
        )


def _require_lookup_section(section: Any, trigger: dict[str, Any], expect: dict[str, Any]) -> None:
    if not isinstance(section, dict) or not isinstance(section.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.lookup_table.tables")
    if sorted(section["tables"]) != [LOOKUP_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must declare exactly table {LOOKUP_TABLE_ID}"
        )
    rows = section["tables"][LOOKUP_TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {LOOKUP_TABLE_ID} must be a non-empty explicit list "
            "(the not-found variant seeds a non-matching decoy row, never an empty table)"
        )
    product_id = str(trigger["parameters"].get("product_id"))
    matches = 0
    for row in rows:
        if not isinstance(row, dict) or not set(row) <= {"col1", "col2", "col3", "col4", "col5", "col6"}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} lookup rows must only use col1..col6: {row!r}"
            )
        if not str(row.get("col4") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded product row needs a non-empty col4 "
                "(the Salesforce-ID search key)"
            )
        if str(row.get("col4")) == product_id:
            matches += 1
    update_expected = "lookup_table.update_entry" in (expect.get("tools") or [])
    stop_step = str(expect.get("stop_step_number") or "")
    if update_expected and matches != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} update variants must seed exactly one col4={product_id!r} row "
            f"(got {matches})"
        )
    if stop_step == str(NOT_FOUND_STOP_STEP) and matches != 0:
        raise RuntimeError(f"recipe {RECIPE_ID} not-found variants must seed zero matching rows")
    if stop_step == str(DUPLICATED_STOP_STEP) and matches < 2:
        raise RuntimeError(f"recipe {RECIPE_ID} duplicated variants must seed >= 2 matching rows")


def _require_force_shape(force: Any) -> None:
    if force is None:
        return
    if not isinstance(force, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error must be an object")
    if str(force.get("step_as") or "") not in FORCEABLE_STEPS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error.step_as must be one of {sorted(FORCEABLE_STEPS)}"
        )
    if not str(force.get("error") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error.error must be a non-empty message")


def _require_expect_shape(expect: Any, force: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(set(expect) - set(EXPECT_KEYS) - OPTIONAL_EXPECT_KEYS)
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has unexpected keys: {unknown}")
    tools = expect.get("tools")
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tools, list) or not isinstance(tool_expectations, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools/tool_expectations must be lists")
    if len(tools) != len(tool_expectations):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry")
    unknown_tools = sorted(set(tools) - set(ALLOWED_TOOLS))
    if unknown_tools:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools has unknown tools: {unknown_tools}")
    if not isinstance(expect.get("stopped"), bool):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.stopped must be a bool")
    if not isinstance(expect.get("final_lookup_rows"), list) or not expect["final_lookup_rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} every variant must pin expect.final_lookup_rows "
            f"(the exact final state of mock table {LOOKUP_TABLE_ID})"
        )
    if force is not None:
        if tools:
            raise RuntimeError(
                f"recipe {RECIPE_ID} the forced search error raises before the tool call: "
                "expect.tools must be [] on the catch variant"
            )
        if not expect["stopped"] or str(expect.get("stop_step_number")) != str(ERROR_STOP_STEP):
            raise RuntimeError(
                f"recipe {RECIPE_ID} forced-error variants stop with error at step {ERROR_STOP_STEP}"
            )
        if str(expect.get("catch_message") or "") != str(force.get("error")):
            raise RuntimeError(f"recipe {RECIPE_ID} expect.catch_message must equal the forced error")
    else:
        if "catch_message" in expect:
            raise RuntimeError(f"recipe {RECIPE_ID} only forced-error variants pin catch_message")
        if not tools or tools[0] != "lookup_table.search_entries":
            raise RuntimeError(f"recipe {RECIPE_ID} every unforced path starts with the step-3 search")
    if expect["stopped"]:
        allowed_stops = {str(NOT_FOUND_STOP_STEP), str(DUPLICATED_STOP_STEP), str(ERROR_STOP_STEP)}
        if str(expect.get("stop_step_number")) not in allowed_stops:
            raise RuntimeError(
                f"recipe {RECIPE_ID} stopped variants must pin stop_step_number in {sorted(allowed_stops)}"
            )
    elif "stop_step_number" in expect:
        raise RuntimeError(f"recipe {RECIPE_ID} non-stopped variants must not pin stop_step_number")
    post_expected = "slack.post_message" in tools
    if post_expected != bool(str(expect.get("slack_text") or "")):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.slack_text must pin the exact rendered message "
            "exactly when the slack post executes"
        )
    if post_expected == expect["stopped"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the post step runs exactly on non-stopped paths"
        )


def _replace_tokens(value: Any, tokens: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_tokens(item, tokens) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_tokens(item, tokens) for item in value]
    if isinstance(value, str):
        out = value
        for token, replacement in tokens.items():
            out = out.replace(token, replacement)
        return out
    return value


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return {
        "lookup_table": (ctx.tools.call("harness.lookup_table.snapshot", {}) or {}).get("lookup_table"),
    }


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
