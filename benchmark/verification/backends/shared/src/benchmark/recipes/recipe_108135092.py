from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_108135092


RECIPE_ID = "108135092"
SEED_TYPE = "webhook_dbt_run_status_variant"
TRACK = "workato_dbtable_slack_dbt_run_status"
TRIGGER_PROVIDER = "workato_webhooks"
TRIGGER_NAME = "new_event"
TRIGGER_AS = "67ba14e5"
TABLE_ID = "16426"
RECORD_ID_COL = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
JOB_NAME_COL = "4f52113b_bdce_443c_8250_78b2dbf454ba"
JOB_ID_COL = "63c5b60c_d705_4718_a112_397c3f9e06af"
LATEST_RUN_COL = "07b98935_4bd6_4f0f_9cef_2d28cfefd9a0"
IS_RUNNING_COL = "423a965d_64e6_4051_a154_1b85f175c5d9"
RUN_START_COL = "a65d24c5_de74_4bc1_ac15_5a46bcfee8e3"
RUN_END_COL = "463920c8_fdf9_40c3_9cea_381a70213960"
GET_STEP_AS = "546ada32"
START_UPDATE_AS = "39d55120"
START_POST_AS = "e15639c0"
COMPLETED_UPDATE_AS = "3349789a"
CATCH_AS = "970ae84f"
CATCH_POST_AS = "994cd4cf"
CATCH_DM_CHANNEL = "U07GCQL582H"
SEED_SECTIONS = {"workato_db_table", "slack_channel_map"}

# dbt Cloud job.run webhook -> 'Jobs List' status tracker (trigger as
# 67ba14e5, webhook_type rawdatatxt, suffix 'RT Update'; the trigger exposes
# the raw JSON STRING under trigger['payload'] - the only pill the body reads):
#   2  json_parser.parse_json ff725bd6 over the payload string (in-executor,
#      fail-fast on empty/invalid JSON; never appears in tool_calls)
#   TRY 3:
#     4  workato_db_table.get_records 546ada32 (table 16426 'Jobs List',
#        filter Job ID 63c5b60c op_integer eq document.data.jobId, limit 1 +
#        'Created at' asc ordering are UI-only inputs the executor does not
#        forward - the seeded filter must therefore match exactly one row)
#     IF 5 (document.eventType contains 'start'):
#       6  workato_db_table.update_record 39d55120: record_id =
#          546ada32.records.current_item.<record id> (current_item OUTSIDE any
#          foreach = FIRST record); sets Latest Run ID = data.runId,
#          is running = 'true', last run start time = data.runStartedAt
#       7  slack_bot.post_bot_message e15639c0 -> channel '#dbt-notifications'
#          (non-'U' literal -> auto-redirected to SLACK_CHANNEL_OVERRIDE).
#          Rendered text = section 'Job: #{jobName} started' + top-level text
#          '#{jobName} started'. The actions/url_button block ('Go to Run
#          #{runId}' -> cloud.getdbt.com deep link) is metadata: slack_text
#          NEVER renders button titles/urls (engine-canonical block rendering;
#          the block structure itself is pinned verbatim in STRUCTURE_PINS).
#     ELSIF 8 (document.eventType contains 'completed'):
#       9  workato_db_table.update_record 3349789a: same current_item record;
#          sets is running = 'false', last success run end time =
#          data.runFinishedAt. NO Slack post on this arm.
#     (no else: any other eventType -> get_records only)
#   CATCH 10 (as 970ae84f, max_retry_count 0):
#     11 slack_bot.post_bot_message 994cd4cf -> literal DM channel
#        'U07GCQL582H' (must be routed via seed.slack_channel_map
#        {'U07GCQL582H': '__override__'}; the live workspace has no such
#        user). Text = section ':almighty_loaf: #{job_context.recipe_name}
#        broken, please fix! :almighty_loaf:' - catch variants must pin
#        seed job_context.recipe_name.
#
# Branch mapping (per benmark_rules):
# - variant_00 start    : eventType 'job.run.started' contains 'start' ->
#   update (Latest Run ID / is running true / runStartedAt) + live Slack post.
# - variant_01 completed: eventType 'job.run.completed' -> IF 5 false ('completed'
#   does not contain 'start'), ELSIF 8 true -> update (is running false /
#   runFinishedAt); no post.
# - variant_02 other    : eventType 'job.run.errored' contains neither ->
#   get_records only (the seeded row proves the no-op is the branch, not a
#   missing row).
# - variant_03 catch    : force_action_error on 546ada32 (the catch is NOT
#   naturally reachable: an empty get_records yields update ok:false, not an
#   exception; sanctioned fault injection per 100191291/106478365 precedent)
#   -> catch DM post; the db table stays untouched.
#
# Backends: workato_db_table 16426 is a Workato-internal per-variant mock
# (the seed fully overwrites it every run -> deterministic reruns; the
# variant pins the exact final table). Slack runs LIVE; posts are ordinary
# observable messages never re-read/deleted -> no Slack cleanup obligation
# (cleanup principle). json_parser is in-executor.

_STRUCTURE_PINS_JSON = r'''[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "67ba14e5",
  "provider": "workato_webhooks",
  "name": "new_event",
  "skip": false,
  "input": {
   "request": {
    "headers_schema": "[{\"control_type\":\"text\",\"label\":\"Accept encoding\",\"type\":\"string\",\"name\":\"accept_encoding\"},{\"control_type\":\"text\",\"label\":\"Authorization\",\"type\":\"string\",\"name\":\"authorization\"},{\"control_type\":\"text\",\"label\":\"Content length\",\"type\":\"string\",\"name\":\"content_length\"},{\"control_type\":\"text\",\"label\":\"Content type\",\"type\":\"string\",\"name\":\"content_type\"},{\"control_type\":\"text\",\"label\":\"User agent\",\"type\":\"string\",\"name\":\"user_agent\"},{\"control_type\":\"text\",\"label\":\"X amzn trace ID\",\"type\":\"string\",\"name\":\"x_amzn_trace_id\"},{\"control_type\":\"text\",\"label\":\"X correlation ID\",\"type\":\"string\",\"name\":\"x_correlation_id\"},{\"control_type\":\"text\",\"label\":\"X forwarded for\",\"type\":\"string\",\"name\":\"x_forwarded_for\"},{\"control_type\":\"text\",\"label\":\"X forwarded port\",\"type\":\"string\",\"name\":\"x_forwarded_port\"},{\"control_type\":\"text\",\"label\":\"X forwarded proto\",\"type\":\"string\",\"name\":\"x_forwarded_proto\"},{\"control_type\":\"text\",\"label\":\"X request ID\",\"type\":\"string\",\"name\":\"x_request_id\"}]",
    "query_params": "[]",
    "webhook_type": "rawdatatxt"
   },
   "webhook_suffix": "RT Update"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "ff725bd6",
  "provider": "json_parser",
  "name": "parse_json",
  "skip": false,
  "input": {
   "document": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"67ba14e5\",\"path\":[\"payload\"]}')}",
   "sample_document": "{\"accountId\":0,\"eventId\":\"wev_2KkC78P4Qux7RSn8XeZ2o2pdvcU\",\"timestamp\":\"<anon>2024-01-01T00:00:00.000000000Z</anon>\",\"eventType\":\"job.run.completed\",\"webhookId\":\"wsu_2OOKhFqtZGSLkMezu3SUujcF0Zj\",\"webhookName\":\"sample-completed-webhook\",\"data\":{\"jobId\":\"0\",\"jobName\":\"Sample Webhook Job\",\"runId\":\"1\",\"environmentId\":\"1\",\"environmentName\":\"Sample Webhook Environment\",\"dbtVersion\":\"1.0.0\",\"projectName\":\"Sample Webhook Project\",\"projectId\":\"\",\"runStatus\":\"Success\",\"runStatusCode\":0,\"runStatusMessage\":\"\",\"runReason\":\"Sample Webhook: Example RunCompleted\",\"runStartedAt\":\"<anon>2024-01-01T01:00:00.000000000Z</anon>\",\"runFinishedAt\":\"<anon>2024-01-01T02:00:00.000000000Z</anon>\"}}"
  }
 },
 {
  "keyword": "try",
  "number": 3,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {}
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "546ada32",
  "provider": "workato_db_table",
  "name": "get_records",
  "skip": false,
  "input": {
   "07b98935-4bd6-4f0f-9cef-2d28cfefd9a0": "integer",
   "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id",
   "423a965d-64e6-4051-a154-1b85f175c5d9": "boolean",
   "463920c8-fdf9-40c3-9cea-381a70213960": "string",
   "4f52113b-bdce-443c-8250-78b2dbf454ba": "string",
   "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time",
   "63c5b60c-d705-4718-a112-397c3f9e06af": "integer",
   "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time",
   "a65d24c5-de74-4bc1-ac15-5a46bcfee8e3": "date_time",
   "filters": [
    {
     "field_id": "63c5b60c-d705-4718-a112-397c3f9e06af",
     "op_integer": "eq",
     "value_integer": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"json_parser\",\"line\":\"ff725bd6\",\"path\":[\"document\", \"data\", \"jobId\"]}')}"
    }
   ],
   "limit": "1",
   "order_direction": "asc",
   "table_id": "16426"
  }
 },
 {
  "keyword": "if",
  "number": 5,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"json_parser\",\"line\":\"ff725bd6\",\"path\":[\"document\", \"eventType\"]}')}",
     "operand": "contains",
     "rhs": "start"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 6,
  "as": "39d55120",
  "provider": "workato_db_table",
  "name": "update_record",
  "skip": false,
  "input": {
   "parameters": {
    "07b98935_4bd6_4f0f_9cef_2d28cfefd9a0": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"json_parser\",\"line\":\"ff725bd6\",\"path\":[\"document\", \"data\", \"runId\"]}')}",
    "423a965d_64e6_4051_a154_1b85f175c5d9": "true",
    "a65d24c5_de74_4bc1_ac15_5a46bcfee8e3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"json_parser\",\"line\":\"ff725bd6\",\"path\":[\"document\", \"data\", \"runStartedAt\"]}')}"
   },
   "record_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"546ada32\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\"]}')}",
   "table_id": "16426"
  }
 },
 {
  "keyword": "action",
  "number": 7,
  "as": "e15639c0",
  "provider": "slack_bot",
  "name": "post_bot_message",
  "skip": false,
  "input": {
   "blocks": [
    {
     "block_type": "section_with_text",
     "button_type": "continue_flow",
     "section_text": "Job: #{_dp('{\"pill_type\":\"output\",\"provider\":\"json_parser\",\"line\":\"ff725bd6\",\"path\":[\"document\", \"data\", \"jobName\"]}')} started"
    },
    {
     "actions": [
      {
       "button_title": "Go to Run #{_dp('{\"pill_type\":\"output\",\"provider\":\"json_parser\",\"line\":\"ff725bd6\",\"path\":[\"document\", \"data\", \"runId\"]}')}",
       "button_type": "url_button",
       "type": "button_with_long_action",
       "url": "https://cloud.getdbt.com/deploy/139136/projects/266836/runs/#{_dp('{\"pill_type\":\"output\",\"provider\":\"json_parser\",\"line\":\"ff725bd6\",\"path\":[\"document\", \"data\", \"runId\"]}')}"
      }
     ],
     "block_type": "actions",
     "button_type": "continue_flow"
    }
   ],
   "channel": "#dbt-notifications",
   "text": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"json_parser\",\"line\":\"ff725bd6\",\"path\":[\"document\", \"data\", \"jobName\"]}')} started"
  }
 },
 {
  "keyword": "elsif",
  "number": 8,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"json_parser\",\"line\":\"ff725bd6\",\"path\":[\"document\", \"eventType\"]}')}",
     "operand": "contains",
     "rhs": "completed"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 9,
  "as": "3349789a",
  "provider": "workato_db_table",
  "name": "update_record",
  "skip": false,
  "input": {
   "parameters": {
    "423a965d_64e6_4051_a154_1b85f175c5d9": "false",
    "463920c8_fdf9_40c3_9cea_381a70213960": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"json_parser\",\"line\":\"ff725bd6\",\"path\":[\"document\", \"data\", \"runFinishedAt\"]}')}"
   },
   "record_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"546ada32\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\"]}')}",
   "table_id": "16426"
  }
 },
 {
  "keyword": "catch",
  "number": 10,
  "as": "970ae84f",
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
  "number": 11,
  "as": "994cd4cf",
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
 }
]'''

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.parse_json",
    "workato_db_table.get_records",
    "workato_db_table.update_record",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.update_record",
    "slack.post_message",
]
EXPECT_KEYS = (
    "branch",
    "catch",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "final_table_16426",
)
OPTIONAL_EXPECT_KEYS = {"slack_text", "catch_message", "case"}
BRANCHES = {"start", "completed", "other", "catch"}


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


def validate_108135092(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger 'as' changed: {raw.get('as')!r}")
    trigger_cfg = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    request = trigger_cfg.get("request") if isinstance(trigger_cfg.get("request"), dict) else {}
    if str(request.get("webhook_type") or "") != "rawdatatxt":
        raise RuntimeError(f"recipe {RECIPE_ID} webhook_type changed (payload must stay a raw string)")
    if str(trigger_cfg.get("webhook_suffix") or "") != "RT Update":
        raise RuntimeError(f"recipe {RECIPE_ID} webhook suffix changed")
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


def seed_108135092(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_108135092(raw)
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
    expect = _require_expect_shape(data.get("expect"))
    branch = str(expect["branch"])
    _require_branch_consistency(branch, document, expect, data, seed_in)
    _require_db_table_section(seed_in.get("workato_db_table"), document, branch)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": deepcopy(trigger),
        "trigger_document": document,
        "expect": deepcopy(expect),
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
    }
    if isinstance(seed_in.get("slack_channel_map"), dict):
        out["slack_channel_map"] = deepcopy(seed_in["slack_channel_map"])
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_108135092(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_108135092(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
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
    # Cleanup per the cleanup principle: the db table is a per-variant mock
    # whose state the seed fully overwrites on every run, and the live Slack
    # posts are ordinary observable messages that are never re-read, deleted
    # or verified live afterwards - no cleanup step is required.
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_108135092(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_payload(trigger: dict[str, Any]) -> dict[str, Any]:
    if sorted(trigger.keys()) != ["payload"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the raw webhook 'payload' "
            f"string (the only trigger pill the recipe reads); got {sorted(trigger.keys())}"
        )
    payload = trigger.get("payload")
    if not isinstance(payload, str) or not payload.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input.payload must be a non-empty JSON string")
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input.payload is not valid JSON: {exc}") from exc
    if not isinstance(document, dict) or not str(document.get("eventType") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} payload.eventType must be explicit (IF 5/ELSIF 8 read it)")
    data = document.get("data")
    if not isinstance(data, dict) or not str(data.get("jobId") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} payload.data.jobId must be explicit (the get_records filter "
            "dereferences it)"
        )
    return document


def _require_expect_shape(expect: Any) -> dict[str, Any]:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(set(expect) - set(EXPECT_KEYS) - OPTIONAL_EXPECT_KEYS)
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has unexpected keys: {unknown}")
    if expect.get("branch") not in BRANCHES:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.branch must be start|completed|other|catch: "
            f"{expect.get('branch')!r}"
        )
    if not isinstance(expect.get("catch"), bool):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.catch must be an explicit boolean")
    tools = expect.get("tools")
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tools, list) or not isinstance(tool_expectations, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools/tool_expectations must be lists")
    if len(tools) != len(tool_expectations):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry")
    unknown_tools = sorted(set(tools) - set(ALLOWED_TOOLS))
    if unknown_tools:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools has unknown tools: {unknown_tools}")
    if not isinstance(expect.get("final_table_16426"), list) or not expect["final_table_16426"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_table_16426 must pin the exact final Jobs List rows"
        )
    if ("slack.post_message" in tools) != ("slack_text" in expect):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.slack_text must be pinned exactly when a slack post "
            "is expected"
        )
    return expect


def _require_branch_consistency(
    branch: str,
    document: dict[str, Any],
    expect: dict[str, Any],
    data: dict[str, Any],
    seed_in: dict[str, Any],
) -> None:
    event_type = str(document.get("eventType") or "")
    payload_data = document.get("data") or {}
    expected_tools = {
        "start": [
            "workato_db_table.get_records",
            "workato_db_table.update_record",
            "slack.post_message",
        ],
        "completed": ["workato_db_table.get_records", "workato_db_table.update_record"],
        "other": ["workato_db_table.get_records"],
        "catch": ["slack.post_message"],
    }[branch]
    if expect.get("tools") != expected_tools:
        raise RuntimeError(
            f"recipe {RECIPE_ID} branch {branch!r} must expect exactly {expected_tools}"
        )
    if (branch == "catch") != bool(expect.get("catch")):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.catch must be true exactly for the catch branch")
    if branch != "catch":
        if data.get("force_action_error") is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} force_action_error requires branch 'catch' (a forced "
                "failure must be verified as the catch branch)"
            )
        starts = "start" in event_type
        completes = "completed" in event_type
        if branch == "start" and not starts:
            raise RuntimeError(f"recipe {RECIPE_ID} start branch needs eventType containing 'start'")
        if branch == "completed" and (starts or not completes):
            raise RuntimeError(
                f"recipe {RECIPE_ID} completed branch needs eventType containing 'completed' "
                "but not 'start'"
            )
        if branch == "other" and (starts or completes):
            raise RuntimeError(
                f"recipe {RECIPE_ID} other branch needs eventType containing neither 'start' "
                "nor 'completed'"
            )
        if branch == "start" and not str(payload_data.get("runStartedAt") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} start branch payload needs data.runStartedAt")
        if branch == "start" and not str(payload_data.get("runId") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} start branch payload needs data.runId")
        if branch == "completed" and not str(payload_data.get("runFinishedAt") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} completed branch payload needs data.runFinishedAt")
        if branch == "start" and not str(payload_data.get("jobName") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} start branch payload needs data.jobName (post text)")
        if "slack_channel_map" in seed_in:
            raise RuntimeError(
                f"recipe {RECIPE_ID} only the catch branch posts to the literal DM channel; "
                "non-catch variants must not seed slack_channel_map"
            )
    else:
        force = data.get("force_action_error")
        if not isinstance(force, dict) or str(force.get("step_as") or "") != GET_STEP_AS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} the catch is not naturally reachable: catch variants must "
                f"declare force_action_error.step_as == {GET_STEP_AS!r} (inside the try body)"
            )
        job_context = data.get("job_context")
        if not isinstance(job_context, dict) or not str(job_context.get("recipe_name") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must pin job_context.recipe_name "
                "(the catch message renders the job_context recipe_name pill)"
            )
        channel_map = seed_in.get("slack_channel_map")
        if not isinstance(channel_map, dict) or channel_map.get(CATCH_DM_CHANNEL) != "__override__":
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must map the literal DM channel "
                f"{CATCH_DM_CHANNEL!r} to '__override__' via seed.slack_channel_map "
                "(the live workspace has no such user)"
            )
        if not str(expect.get("catch_message") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must pin expect.catch_message "
                "(the forced error recorded in the 970ae84f catch payload)"
            )


def _require_db_table_section(section: Any, document: dict[str, Any], branch: str) -> None:
    if not isinstance(section, dict) or not isinstance(section.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.workato_db_table.tables")
    if sorted(section["tables"]) != [TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table.tables must declare exactly table {TABLE_ID}"
        )
    rows = section["tables"][TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"recipe {RECIPE_ID} table {TABLE_ID} must be a non-empty explicit list")
    job_id = str((document.get("data") or {}).get("jobId") or "")
    matches = 0
    decoys = 0
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table {TABLE_ID} rows must be objects")
        if not str(row.get(RECORD_ID_COL) or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} every Jobs List row needs an explicit record id "
                f"({RECORD_ID_COL}) - the update steps key off it"
            )
        if not isinstance(row.get(JOB_ID_COL), int):
            raise RuntimeError(
                f"recipe {RECIPE_ID} every Jobs List row must set the integer Job ID column "
                f"({JOB_ID_COL}): {row!r}"
            )
        if str(row.get(JOB_ID_COL)) == job_id:
            matches += 1
        else:
            decoys += 1
    if matches != 1 or decoys < 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} exactly ONE row must match payload jobId {job_id!r} (the "
            f"'limit 1' get_records is not forwarded, so a unique match is the faithful state) "
            f"plus >=1 non-matching decoy; got {matches} matches / {decoys} decoys"
        )


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    snap = ctx.tools.call("harness.workato_db_table.snapshot", {})
    return {"workato_db_table": snap.get("workato_db_table")}


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
