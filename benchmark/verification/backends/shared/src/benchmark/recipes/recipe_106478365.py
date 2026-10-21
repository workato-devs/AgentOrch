from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_106478365


RECIPE_ID = "106478365"
SEED_TYPE = "webhook_dbt_error_resolution_variant"
TRACK = "workato_dbtable_lookup_slack_error_resolution"
TRIGGER_PROVIDER = "workato_webhooks"
TRIGGER_NAME = "new_event"
TRIGGER_AS = "c40de19d"

# dbt-job "Error Resolution" webhook recipe (trigger as c40de19d, webhook_suffix
# 'Error Resolution'; only trigger['payload'] — a raw JSON string — is read):
#   2  json_parser.parse_json (08df4f91) over the payload (fail-fast on
#      empty/invalid JSON)
#   3  workato_db_table.get_records (474ba69f, table 14696 'Error History',
#      filters: jobId col 194f7b20 op_integer eq document.data.jobId AND
#      resolved col ff897762 op_boolean isfalse -> eq False; limit 10 desc)
#   4  IF records.current_item.<record id 11fbe9a6> present ->
#   5  TRY:
#      6  lookup_table.get_entries (0e4202e2, table 3820912 data-owner list)
#      7  FOREACH over entries:
#         8  slack_bot.post_bot_message (2a1f0dc1: channel = entry.col3,
#            section 'Bad Job #{document.data.jobName} fixed
#            :smiley::thumbsup::skin-tone-2:')
#         9  slack_bot.post_bot_message (909c0957) — "skip": true — DISABLED
#      10 slack_bot.post_bot_message (f92a551d) — "skip": true — DISABLED
#      11 slack_bot.post_bot_message (f6269629) — "skip": true — DISABLED
#      12 workato_db_table.update_record (be64d30f: record_id =
#         records.current_item id, set resolved-datetime col 18644aef = '=now'
#         and resolved col ff897762 = 'true') — ACTIVE: the recipe's real
#         persistent effect (variant MUST pin data.now)
#   13 CATCH (90ddfe8f, max_retry 0):
#      14 slack_bot.post_bot_message (e241bc28: channel literal 'U07GCQL582H',
#         ':almighty_loaf: #{job_context.recipe_name} broken, please fix!
#         :almighty_loaf:')
#   15 workato_recipe_function.return_result (c2b86df3, {} — terminal)
#
# IMPORTANT — TRIAGE CORRECTION (probe-verified against the current engine's
# execute_node skip handling, same semantics as real Workato
# disabled steps): steps 9, 10 and 11 carry "skip": true in the raw recipe.
# They are DISABLED — the executor records reached-but-skipped trace markers
# and never runs them. In particular the no-text post f92a551d (step 10) can
# NEVER raise 'Slack message rendered empty text', so the batch_C triage claim
# that "the catch post is the de-facto happy path" and that "steps 11-12 are
# dead code" is WRONG: the happy path posts one live Slack message per lookup
# entry and then step 12 marks the Error History row resolved. The catch
# branch is reachable only through a genuine action failure and is covered via
# variant force_action_error (variant_04, forced on be64d30f).
#
# Backends: workato_db_table + lookup_table are Workato-internal mocks (seeded
# per variant); Slack is LIVE — entry.col3 channels are non-'U' seeds that the
# executor auto-redirects to SLACK_CHANNEL_OVERRIDE, and the literal catch DM
# channel 'U07GCQL582H' requires seed.slack_channel_map
# {"U07GCQL582H": "__override__"} (only the catch variant reaches it).
# Ordinary posts are never read back/deleted -> no Slack cleanup obligation
# (cleanup principle). The db-table update is idempotent per variant because
# every variant fully re-seeds table 14696.

_STRUCTURE_PINS_JSON = r'''
[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "c40de19d",
  "provider": "workato_webhooks",
  "name": "new_event",
  "skip": false,
  "input": {
   "request": {
    "headers_schema": "[{\"control_type\":\"text\",\"label\":\"Accept encoding\",\"type\":\"string\",\"name\":\"accept_encoding\"},{\"control_type\":\"text\",\"label\":\"Authorization\",\"type\":\"string\",\"name\":\"authorization\"},{\"control_type\":\"text\",\"label\":\"Content length\",\"type\":\"string\",\"name\":\"content_length\"},{\"control_type\":\"text\",\"label\":\"Content type\",\"type\":\"string\",\"name\":\"content_type\"},{\"control_type\":\"text\",\"label\":\"User agent\",\"type\":\"string\",\"name\":\"user_agent\"},{\"control_type\":\"text\",\"label\":\"X amzn trace ID\",\"type\":\"string\",\"name\":\"x_amzn_trace_id\"},{\"control_type\":\"text\",\"label\":\"X correlation ID\",\"type\":\"string\",\"name\":\"x_correlation_id\"},{\"control_type\":\"text\",\"label\":\"X forwarded for\",\"type\":\"string\",\"name\":\"x_forwarded_for\"},{\"control_type\":\"text\",\"label\":\"X forwarded port\",\"type\":\"string\",\"name\":\"x_forwarded_port\"},{\"control_type\":\"text\",\"label\":\"X forwarded proto\",\"type\":\"string\",\"name\":\"x_forwarded_proto\"},{\"control_type\":\"text\",\"label\":\"X request ID\",\"type\":\"string\",\"name\":\"x_request_id\"}]",
    "query_params": "[]",
    "webhook_type": "rawdatatxt"
   },
   "webhook_suffix": "Error Resolution"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "08df4f91",
  "provider": "json_parser",
  "name": "parse_json",
  "skip": false,
  "input": {
   "document": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"c40de19d\",\"path\":[\"payload\"]}')}",
   "sample_document": "{\"accountId\":0,\"eventId\":\"wev_2KkC78P4Qux7RSn8XeZ2o2pdvcU\",\"timestamp\":\"<anon>2024-01-01T00:00:00.000000000Z</anon>\",\"eventType\":\"job.run.completed\",\"webhookId\":\"wsu_2OOKhFqtZGSLkMezu3SUujcF0Zj\",\"webhookName\":\"sample-completed-webhook\",\"data\":{\"jobId\":\"0\",\"jobName\":\"Sample Webhook Job\",\"runId\":\"1\",\"environmentId\":\"1\",\"environmentName\":\"Sample Webhook Environment\",\"dbtVersion\":\"1.0.0\",\"projectName\":\"Sample Webhook Project\",\"projectId\":\"\",\"runStatus\":\"Success\",\"runStatusCode\":0,\"runStatusMessage\":\"\",\"runReason\":\"Sample Webhook: Example RunCompleted\",\"runStartedAt\":\"<anon>2024-01-01T00:00:00.000000000Z</anon>\",\"runFinishedAt\":\"<anon>2024-01-01T00:00:00.000000000Z</anon>\"}}"
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "474ba69f",
  "provider": "workato_db_table",
  "name": "get_records",
  "skip": false,
  "input": {
   "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id",
   "18644aef-da36-4f25-a93e-c0a9ec45a348": "date_time",
   "194f7b20-293e-4d6b-8433-667a1ed4eb1c": "integer",
   "1e4fff4e-5edc-4c18-98dd-363101a1b918": "integer",
   "36fd8e48-f78f-4abb-baea-3cc7cc41b032": "string",
   "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time",
   "76a33a78-9f5f-441c-ad96-6db0847d4283": "date_time",
   "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time",
   "b33934da-f778-4dc0-bf08-8f8bff15f541": "string",
   "b8b6e4c3-3772-4ee3-9b6e-6200ee5e8f1d": "string",
   "cc1c1438-7aa4-4bf3-aeda-b5fd119be70a": "integer",
   "ff897762-fb6c-4eca-aee9-abcd3aeee3a3": "boolean",
   "filters": [
    {
     "field_id": "194f7b20-293e-4d6b-8433-667a1ed4eb1c",
     "op_integer": "eq",
     "value_integer": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"json_parser\",\"line\":\"08df4f91\",\"path\":[\"document\", \"data\", \"jobId\"]}')}"
    },
    {
     "field_id": "ff897762-fb6c-4eca-aee9-abcd3aeee3a3",
     "op_boolean": "isfalse"
    }
   ],
   "limit": "10",
   "order_direction": "desc",
   "table_id": "14696"
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
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"474ba69f\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\"]}')}",
     "operand": "present",
     "rhs": ""
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "try",
  "number": 5,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {}
 },
 {
  "keyword": "action",
  "number": 6,
  "as": "0e4202e2",
  "provider": "lookup_table",
  "name": "get_entries",
  "skip": false,
  "input": {
   "lookup_table_id": "3820912"
  }
 },
 {
  "keyword": "foreach",
  "number": 7,
  "as": "331e908d",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"0e4202e2\",\"path\":[\"entries\"]}')}"
  },
  "repeat_mode": "simple",
  "batch_size": null,
  "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"lookup_table\",\"line\":\"0e4202e2\",\"path\":[\"entries\"]}')}"
 },
 {
  "keyword": "action",
  "number": 8,
  "as": "2a1f0dc1",
  "provider": "slack_bot",
  "name": "post_bot_message",
  "skip": false,
  "input": {
   "blocks": [
    {
     "block_type": "section_with_text",
     "button_type": "continue_flow",
     "section_text": "Bad Job #{_dp('{\"pill_type\":\"output\",\"provider\":\"json_parser\",\"line\":\"08df4f91\",\"path\":[\"document\", \"data\", \"jobName\"]}')} fixed :smiley::thumbsup::skin-tone-2:"
    }
   ],
   "channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"331e908d\",\"path\":[\"entry\", \"col3\"]}')}"
  }
 },
 {
  "keyword": "action",
  "number": 9,
  "as": "909c0957",
  "provider": "slack_bot",
  "name": "post_bot_message",
  "skip": true,
  "input": {
   "blocks": [
    {
     "block_type": "section_with_text",
     "button_type": "continue_flow",
     "section_text": "Bad Job #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"3ad1fc89\",\"path\":[\"parameters\", \"Job_Name\"]}')} fixed :smiley::thumbsup::skin-tone-2:"
    }
   ],
   "channel": "U07GCQL582H"
  }
 },
 {
  "keyword": "action",
  "number": 10,
  "as": "f92a551d",
  "provider": "slack_bot",
  "name": "post_bot_message",
  "skip": true,
  "input": {
   "channel": "#ask-product-data"
  }
 },
 {
  "keyword": "action",
  "number": 11,
  "as": "f6269629",
  "provider": "slack_bot",
  "name": "post_bot_message",
  "skip": true,
  "input": {
   "blocks": [
    {
     "block_type": "section_with_text",
     "button_type": "continue_flow",
     "section_text": "Bad Job #{_dp('{\"pill_type\":\"output\",\"provider\":\"json_parser\",\"line\":\"08df4f91\",\"path\":[\"document\", \"data\", \"jobName\"]}')} fixed :smiley::thumbsup::skin-tone-2:"
    }
   ],
   "channel": "#dbt-notifications"
  }
 },
 {
  "keyword": "action",
  "number": 12,
  "as": "be64d30f",
  "provider": "workato_db_table",
  "name": "update_record",
  "skip": false,
  "input": {
   "parameters": {
    "18644aef_da36_4f25_a93e_c0a9ec45a348": "=now",
    "ff897762_fb6c_4eca_aee9_abcd3aeee3a3": "true"
   },
   "record_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"474ba69f\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\"]}')}",
   "table_id": "14696"
  }
 },
 {
  "keyword": "catch",
  "number": 13,
  "as": "90ddfe8f",
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
  "number": 14,
  "as": "e241bc28",
  "provider": "slack_bot",
  "name": "post_bot_message",
  "skip": false,
  "input": {
   "blocks": [
    {
     "block_type": "section_with_text",
     "button_type": "continue_flow",
     "section_text": ":almighty_loaf: #{_dp('{\"pill_type\":\"job_context\",\"path\":[\"recipe_name\"]}')} broken, please fix! :almighty_loaf:"
    }
   ],
   "channel": "U07GCQL582H"
  }
 },
 {
  "keyword": "action",
  "number": 15,
  "as": "c2b86df3",
  "provider": "workato_recipe_function",
  "name": "return_result",
  "skip": false,
  "input": {}
 }
]
'''

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

TABLE_ID = "14696"
LOOKUP_TABLE_ID = "3820912"
RECORD_ID_COL = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
JOB_ID_COL = "194f7b20_293e_4d6b_8433_667a1ed4eb1c"
RESOLVED_COL = "ff897762_fb6c_4eca_aee9_abcd3aeee3a3"
RESOLVED_AT_COL = "18644aef_da36_4f25_a93e_c0a9ec45a348"
CATCH_DM_CHANNEL = "U07GCQL582H"
UPDATE_STEP_AS = "be64d30f"

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.parse_json",
    "workato_db_table.get_records",
    "lookup_table.get_entries",
    "slack.post_message",
    "workato_db_table.update_record",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "lookup_table.get_entries",
    "slack.post_message",
    "workato_db_table.update_record",
    "workato_recipe_function.return_result",
]
SEED_SECTIONS = {"workato_db_table", "lookup_table", "slack_channel_map"}
EXPECT_KEYS = (
    "tools",
    "tool_expectations",
    "executed_action_count",
    "catch",
    "skipped_steps",
    "final_table_14696",
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


def validate_106478365(raw: dict[str, Any]) -> dict[str, Any]:
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
    # The disabled-step layout is load-bearing for this benchmark's semantics:
    # steps 9/10/11 MUST stay skipped and step 12 MUST stay active. A corpus
    # edit that re-enables the empty post (or disables the update) changes the
    # ground truth completely — fail here, not in a confusing replay diff.
    skip_map = {pin["number"]: pin["skip"] for pin in actual if pin["keyword"] == "action"}
    if not (skip_map.get(9) and skip_map.get(10) and skip_map.get(11)):
        raise RuntimeError(f"recipe {RECIPE_ID} steps 9/10/11 are no longer disabled: {skip_map}")
    if skip_map.get(12):
        raise RuntimeError(f"recipe {RECIPE_ID} step 12 (update_record) became disabled")
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
                "skip": pin["skip"],
            }
            for pin in actions
        ],
    }


def seed_106478365(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_106478365(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    document = _require_trigger_payload(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - SEED_SECTIONS)
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    expect = _require_expect(data)
    _require_db_table_section(seed_in.get("workato_db_table"))
    _require_lookup_section(seed_in.get("lookup_table"))
    reaches_update = "workato_db_table.update_record" in expect["tools"]
    if reaches_update and data.get("now") in (None, ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} variants that reach step 12 must pin data.now "
            "(the resolved-datetime column renders '=now')"
        )
    if expect["catch"] is True:
        if not isinstance(data.get("force_action_error"), dict):
            raise RuntimeError(
                f"recipe {RECIPE_ID} the catch branch is reachable only through a genuine "
                "action failure — catch variants must declare force_action_error"
            )
        job_context = data.get("job_context")
        if not isinstance(job_context, dict) or not str(job_context.get("recipe_name") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must pin job_context.recipe_name "
                "(the catch message renders the job_context recipe_name pill)"
            )
        channel_map = seed_in.get("slack_channel_map")
        if not isinstance(channel_map, dict) or CATCH_DM_CHANNEL not in channel_map:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must map the literal DM channel "
                f"{CATCH_DM_CHANNEL!r} via seed.slack_channel_map (live workspace has no such user)"
            )
    elif isinstance(data.get("force_action_error"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error requires expect.catch: true "
            "(a forced failure must be verified as the catch branch)"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": deepcopy(trigger),
        "trigger_document": document,
        "expect": deepcopy(expect),
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "lookup_table": deepcopy(seed_in["lookup_table"]),
    }
    if isinstance(seed_in.get("slack_channel_map"), dict):
        out["slack_channel_map"] = deepcopy(seed_in["slack_channel_map"])
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_106478365(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_106478365(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    for section in ("workato_db_table", "lookup_table"):
        if not isinstance(seed.get(section), dict):
            raise RuntimeError(f"recipe {RECIPE_ID} seed file missing {section} section")
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    initial_snapshot = _snapshot(ctx)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = _snapshot(ctx)
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
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_106478365(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_payload(trigger: dict[str, Any]) -> dict[str, Any]:
    if sorted(trigger.keys()) != ["payload"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the raw webhook "
            f"'payload' string (the only trigger pill the recipe reads); got {sorted(trigger.keys())}"
        )
    payload = trigger.get("payload")
    if not isinstance(payload, str) or not payload.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input.payload must be a non-empty JSON string")
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input.payload is not valid JSON: {exc}") from exc
    data = document.get("data") if isinstance(document, dict) else None
    if not isinstance(data, dict) or not str(data.get("jobId") or "").strip() or not str(data.get("jobName") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} payload.data.jobId and payload.data.jobName must be explicit "
            "(the get_records filter and the Slack section text dereference them)"
        )
    return document


def _require_expect(data: dict[str, Any]) -> dict[str, Any]:
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    tools = expect.get("tools")
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tools, list) or not isinstance(tool_expectations, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools/tool_expectations must be lists")
    if len(tools) != len(tool_expectations):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry")
    unknown_tools = sorted(set(tools) - set(ALLOWED_TOOLS))
    if unknown_tools:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools has unknown tools: {unknown_tools}")
    if not isinstance(expect.get("catch"), bool):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.catch must be an explicit boolean")
    skipped = expect.get("skipped_steps")
    if not isinstance(skipped, dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.skipped_steps must map disabled step numbers to their "
            "reached-but-skipped trace marker counts (steps 9/10/11 are disabled in the raw recipe)"
        )
    if not isinstance(expect.get("final_table_14696"), list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_table_14696 must pin the exact final Error History rows"
        )
    if tools and tools[-1] != "workato_recipe_function.return_result":
        raise RuntimeError(
            f"recipe {RECIPE_ID} step 15 return_result is terminal and unconditional — it must be "
            "the last expected tool"
        )
    if expect["catch"] is True and "workato_db_table.update_record" in tools:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the shipped catch variant forces the failure on step 12 itself — "
            "the update must not also be expected to run"
        )
    return expect


def _require_db_table_section(section: Any) -> None:
    if not isinstance(section, dict) or not isinstance(section.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.workato_db_table.tables")
    if sorted(section["tables"]) != [TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table.tables must declare exactly table {TABLE_ID}"
        )
    rows = section["tables"][TABLE_ID]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {TABLE_ID} rows must be a list")
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table {TABLE_ID} rows must be objects")
        if not str(row.get(RECORD_ID_COL) or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} every Error History row needs an explicit record id "
                f"({RECORD_ID_COL}) — IF4 and the step-12 update key off it"
            )
        if JOB_ID_COL not in row:
            raise RuntimeError(f"recipe {RECIPE_ID} every Error History row must set the jobId column")
        if not isinstance(row.get(RESOLVED_COL), bool):
            raise RuntimeError(
                f"recipe {RECIPE_ID} the resolved column must be an explicit JSON boolean — the "
                "isfalse filter compares eq False and a null/string value would silently not match"
            )


def _require_lookup_section(section: Any) -> None:
    if not isinstance(section, dict) or not isinstance(section.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.lookup_table.tables")
    if sorted(section["tables"]) != [LOOKUP_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must declare exactly table {LOOKUP_TABLE_ID}"
        )
    entries = section["tables"][LOOKUP_TABLE_ID]
    if not isinstance(entries, list):
        raise RuntimeError(f"recipe {RECIPE_ID} lookup table {LOOKUP_TABLE_ID} must be a list")
    for entry in entries:
        if not isinstance(entry, dict) or not str(entry.get("col3") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} every data-owner entry needs an explicit col3 notification "
                "channel (step 8 posts to entry.col3)"
            )
        if str(entry.get("col3") or "").startswith("U"):
            raise RuntimeError(
                f"recipe {RECIPE_ID} entry.col3 must not be a literal U-prefixed user id — the "
                "executor posts U-channels verbatim and the live workspace has no such user; seed "
                "a '#'-named channel (auto-redirected to SLACK_CHANNEL_OVERRIDE)"
            )


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    out: dict[str, Any] = {}
    out.update(ctx.tools.call("harness.workato_db_table.snapshot", {}))
    out.update(ctx.tools.call("harness.lookup_table.snapshot", {}))
    out.pop("ok", None)
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
