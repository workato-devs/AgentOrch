from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_94001408


RECIPE_ID = "94001408"
SEED_TYPE = "salesforce_pub_sub_gears_survey_response_logger_variant"
TRACK = "live_salesforce_pub_sub_gears_survey_response_logger"
TRIGGER_PROVIDER = "workato_pub_sub"
TRIGGER_NAME = "subscribe_to_topic"
TRIGGER_AS = "e3dee984"
CREATE_AS = "1e300d60"
CATCH_AS = "0dd86881"
SLACK_AS = "d9474a4f"
SOBJECT = "Survey_Response__c"
SLACK_PROPERTY = "GEARS_V2_SLACK_ERROR"
SLACK_TITLE = "Salesforce Logger Error"


SF_SCHEMA: list[dict[str, str]] = [
    {"sobject": SOBJECT, "field": "Account__c", "sf_type": "Text"},
    {"sobject": SOBJECT, "field": "Contact__c", "sf_type": "Text"},
    {"sobject": SOBJECT, "field": "Comments__c", "sf_type": "Text"},
    {"sobject": SOBJECT, "field": "Score__c", "sf_type": "Text"},
    {"sobject": SOBJECT, "field": "Source_ID__c", "sf_type": "Text"},
    {"sobject": SOBJECT, "field": "Survey_Response_Date__c", "sf_type": "Date"},
    {"sobject": SOBJECT, "field": "Type__c", "sf_type": "Text"},
]
MESSAGE_KEYS = (
    "account_id",
    "assessment_id",
    "assessment_date",
    "responder_email",
    "score",
    "type",
    "contact_id",
)
_TYPE_RE = re.compile(r"[a-z0-9]+(?:[ _][a-z0-9]+)*")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.create_record",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = list(EXPECTED_RAW_TOOLS)
CASES = (
    "create_spaced_titleize",
    "create_underscored_titleize",
    "catch_slack_error",
)
REQUIRED_EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "created_fields",
    "created_record_fields",
    "slack",
    "steps_absent_from_trace",
)

_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "e3dee984",
  "provider": "workato_pub_sub",
  "name": "subscribe_to_topic",
  "skip": false,
  "input": {
   "since_offset": "-3600",
   "topic_id": "34038"
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
  "as": "1e300d60",
  "provider": "salesforce",
  "name": "create_custom_object",
  "skip": false,
  "input": {
   "Account__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"e3dee984\",\"path\":[\"message\", \"account_id\"]}')}",
   "Comments__c": "Responder: #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"e3dee984\",\"path\":[\"message\", \"responder_email\"]}')}",
   "Contact__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"e3dee984\",\"path\":[\"message\", \"contact_id\"]}')}",
   "Name": "=\"GEARS:\" + _dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"e3dee984\",\"path\":[\"message\",\"type\"]}').titleize",
   "Score__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"e3dee984\",\"path\":[\"message\", \"score\"]}')}",
   "Source_ID__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"e3dee984\",\"path\":[\"message\", \"assessment_id\"]}')}",
   "Survey_Response_Date__c": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_pub_sub\",\"line\":\"e3dee984\",\"path\":[\"message\",\"assessment_date\"]}')",
   "Type__c": "GEARS Assessment",
   "sobject_name": "Survey_Response__c"
  }
 },
 {
  "keyword": "catch",
  "number": 4,
  "as": "0dd86881",
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
  "as": "d9474a4f",
  "provider": "slack_bot",
  "name": "post_bot_message",
  "skip": false,
  "input": {
   "channel": "#{_dp('{\"pill_type\":\"account_property\",\"property_name\":\"GEARS_V2_SLACK_ERROR\"}')}",
   "message": {
    "attachment_text": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"0dd86881\",\"path\":[\"message\"]}')}",
    "color": "danger",
    "title": "Salesforce Logger Error",
    "title_link": "#{_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_url\"]}')}"
   }
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)


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


def validate_94001408(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
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
    # Semantic pins on the drift-prone pieces of the analysis above.
    create_pin = next(pin for pin in actual if pin["as"] == CREATE_AS)
    create_input = create_pin["input"]
    if str(create_input.get("sobject_name") or "") != SOBJECT:
        raise RuntimeError(f"recipe {RECIPE_ID} create sobject changed: {create_input!r}")
    if create_input.get("Type__c") != "GEARS Assessment":
        raise RuntimeError(f"recipe {RECIPE_ID} Type__c literal changed: {create_input!r}")
    if ".titleize" not in str(create_input.get("Name") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} Name titleize formula changed: {create_input!r}")
    if not str(create_input.get("Comments__c") or "").startswith("Responder: "):
        raise RuntimeError(f"recipe {RECIPE_ID} Comments__c template changed: {create_input!r}")
    catch_pin = next(pin for pin in actual if pin["keyword"] == "catch")
    if str(catch_pin["input"].get("max_retry_count") or "") != "0":
        raise RuntimeError(f"recipe {RECIPE_ID} catch retry contract changed: {catch_pin!r}")
    slack_pin = next(pin for pin in actual if pin["as"] == SLACK_AS)
    slack_input = slack_pin["input"]
    if SLACK_PROPERTY not in str(slack_input.get("channel") or ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} slack channel no longer reads the {SLACK_PROPERTY} "
            f"account property: {slack_input!r}"
        )
    message = slack_input.get("message") if isinstance(slack_input.get("message"), dict) else {}
    if str(message.get("title") or "") != SLACK_TITLE or "catch" not in str(
        message.get("attachment_text") or ""
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} slack attachment shape changed: {message!r}")
    actions = [pin for pin in actual if pin["keyword"] == "action"]
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "sobject": SOBJECT,
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


def _titleize(text: str) -> str:
    # Byte-for-byte mirror of the engine's .titleize (raw_executor):
    # underscores -> spaces, then every [A-Za-z0-9]+ run capitalized.
    return re.sub(r"[A-Za-z0-9]+", lambda match: match.group(0).capitalize(), text.replace("_", " "))


def _derive_created_fields(message: dict[str, Any]) -> dict[str, Any]:
    return {
        "Account__c": message["account_id"],
        "Comments__c": f"Responder: {message['responder_email']}",
        "Contact__c": message["contact_id"],
        "Name": "GEARS:" + _titleize(str(message["type"])),
        "Score__c": message["score"],
        "Source_ID__c": message["assessment_id"],
        "Survey_Response_Date__c": message["assessment_date"],
        "Type__c": "GEARS Assessment",
    }


def seed_94001408(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_94001408(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    message = _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    expect = data.get("expect")
    _require_expect_common(expect)
    case = expect["case"]
    force = data.get("force_action_error")
    if case == "catch_slack_error":
        _require_catch_seed(seed_in, force, message, expect)
    else:
        _require_create_seed(case, seed_in, force, data, message, expect)
    provision = ctx.tools.call(
        "harness.salesforce.seed_records", {"salesforce": deepcopy(seed_in["salesforce"])}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    owned = [
        record
        for record in ((provision.get("snapshot") or {}).get("salesforce") or {}).get("records") or []
        if isinstance(record, dict) and not record.get("read_only")
    ]
    if owned:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seeds no records (the RECIPE creates the live row); "
            f"got {len(owned)} provisioned records"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "trigger": deepcopy(trigger),
        "expect": deepcopy(expect),
    }
    if case == "catch_slack_error":
        # Both are read by the executor from the top-level seed (the account
        # property pill and the job_context pill).
        out["account_properties"] = deepcopy(seed_in["account_properties"])
        out["job_context"] = deepcopy(seed_in["job_context"])
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_94001408(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_94001408(raw)
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if expect.get("case") == "catch_slack_error" and not ctx.env.slack_channel_override:
        raise RuntimeError(
            f"recipe {RECIPE_ID} missing SLACK_CHANNEL_OVERRIDE; refusing to post to a "
            "guessed live Slack channel"
        )
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
        "force_action_error": deepcopy(seed.get("force_action_error"))
        if isinstance(seed.get("force_action_error"), dict)
        else None,
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    raw_execution: dict[str, Any] | None = None
    cleanup: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = dict(ctx.tools.call("harness.salesforce.snapshot", {}))
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["final_snapshot"] = dict(ctx.tools.call("harness.salesforce.snapshot", {}))
    finally:
        # Required cleanup: the recipe-created Survey_Response__c row is
        # benchmark-owned and must not leak into later runs (catch variants
        # own nothing; cleanup is then a no-op that must still report ok).
        cleanup = ctx.tools.call("harness.salesforce.cleanup", {})
    details["cleanup_response"] = {"salesforce": cleanup}
    if not (cleanup or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce cleanup failed: {cleanup}")
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_94001408(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> dict[str, Any]:
    if set(trigger.keys()) != {"message"} or not isinstance(trigger.get("message"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'message': {{...}}}}"
        )
    message = trigger["message"]
    if sorted(message.keys()) != sorted(MESSAGE_KEYS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger message must carry exactly the topic schema "
            f"fields {sorted(MESSAGE_KEYS)}; got {sorted(message.keys())}"
        )
    for key in MESSAGE_KEYS:
        value = message.get(key)
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger message.{key} must be a non-empty string "
                f"(the topic schema is all-string; score stays a STRING and Score__c "
                f"is a Text column live); got {value!r}"
            )
    if not _TYPE_RE.fullmatch(str(message["type"])):
        raise RuntimeError(
            f"recipe {RECIPE_ID} message.type must be lowercase word runs separated "
            f"by single spaces/underscores (deterministic titleize); got "
            f"{message['type']!r}"
        )
    if not _DATE_RE.fullmatch(str(message["assessment_date"])):
        raise RuntimeError(
            f"recipe {RECIPE_ID} message.assessment_date must be YYYY-MM-DD (the live "
            f"Survey_Response_Date__c column is a Date); got {message['assessment_date']!r}"
        )
    return message


def _require_expect_common(expect: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if expect.get("case") not in CASES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.case must be one of {CASES}")
    if expect.get("executed_action_count") != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} exactly one action executes on either branch "
            "(create OR the catch slack post)"
        )


def _require_create_seed(
    case: str,
    seed_in: dict[str, Any],
    force: Any,
    data: dict[str, Any],
    message: dict[str, Any],
    expect: dict[str, Any],
) -> None:
    if force is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} create variants must not force an action error"
        )
    if data.get("job_context") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} job_context is only read on the catch branch "
            "(dead seed state on create variants)"
        )
    if sorted(seed_in.keys()) != ["salesforce"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} create variants seed exactly the salesforce section "
            f"(no dead account_properties); got {sorted(seed_in.keys())}"
        )
    _require_salesforce_section(seed_in["salesforce"], schema_required=True)
    derived = _derive_created_fields(message)
    separator = " " if case == "create_spaced_titleize" else "_"
    if separator not in str(message["type"]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} case {case!r} must exercise the "
            f"{separator!r}-separated titleize arm; message.type {message['type']!r}"
        )
    checks = (
        expect.get("created_fields") == derived,
        expect.get("created_record_fields") == derived,
        expect.get("slack") is None,
        expect.get("tools") == ["salesforce.create_record"],
        expect.get("steps_absent_from_trace") == [SLACK_AS],
        expect.get("tool_expectations")
        == [
            {
                "tool": "salesforce.create_record",
                "args_contains": {"sobject": SOBJECT, "fields": derived},
            }
        ],
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} create expect block contradicts the message-derived "
            f"ground truth:\nderived fields: {json.dumps(derived, sort_keys=True)}\n"
            f"expect: {json.dumps(expect, sort_keys=True)}"
        )


def _require_catch_seed(
    seed_in: dict[str, Any],
    force: Any,
    message: dict[str, Any],
    expect: dict[str, Any],
) -> None:
    if (
        not isinstance(force, dict)
        or str(force.get("step_as") or "") != CREATE_AS
        or not str(force.get("error") or "").strip()
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch_slack_error requires force_action_error "
            f"{{step_as: {CREATE_AS!r}, error: <non-empty>}} (sanctioned fault "
            f"injection -- the catch is not naturally reachable from seedable state); "
            f"got {force!r}"
        )
    if sorted(seed_in.keys()) != ["account_properties", "job_context", "salesforce"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch variant must seed exactly account_properties + "
            f"job_context + salesforce; got {sorted(seed_in.keys())}"
        )
    properties = seed_in["account_properties"]
    if (
        not isinstance(properties, dict)
        or sorted(properties.keys()) != [SLACK_PROPERTY]
        or not str(properties.get(SLACK_PROPERTY) or "").strip()
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch variant must seed exactly account_properties."
            f"{SLACK_PROPERTY} (property name lacks 'channel' so the unseeded-property "
            f"override affordance does not apply -- probed fail-fast); got {properties!r}"
        )
    if str(properties[SLACK_PROPERTY]).startswith("U"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the seeded {SLACK_PROPERTY} value must stay a non-'U' "
            "channel text so the executor routes the post to the benchmark override "
            "channel (live isolation)"
        )
    job_context = seed_in["job_context"]
    if (
        not isinstance(job_context, dict)
        or sorted(job_context.keys()) != ["job_url"]
        or not str(job_context.get("job_url") or "").strip()
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch variant must seed job_context.job_url (the "
            f"title_link pill; flattening drops it but the pill must resolve); got "
            f"{job_context!r}"
        )
    _require_salesforce_section(seed_in["salesforce"], schema_required=False)
    expected_text = f"{SLACK_TITLE}\n{force['error']}"
    checks = (
        expect.get("created_fields") is None,
        expect.get("created_record_fields") is None,
        expect.get("slack") == {"channel": "override", "text": expected_text},
        expect.get("tools") == ["slack.post_message"],
        expect.get("steps_absent_from_trace") == [CREATE_AS],
        expect.get("tool_expectations")
        == [
            {
                "tool": "slack.post_message",
                "channel": "override",
                "args_contains": {"text": expected_text},
                "text_fragments": [SLACK_TITLE, str(force["error"])],
            }
        ],
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch expect block contradicts the derived ground "
            f"truth (text {expected_text!r}): {json.dumps(expect, sort_keys=True)}"
        )


def _require_salesforce_section(section: Any, *, schema_required: bool) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["records", "schema"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce must be exactly {{'schema': ..., "
            f"'records': ...}}; got "
            f"{sorted(section.keys()) if isinstance(section, dict) else section!r}"
        )
    if section.get("records") != []:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seeds NO Salesforce records (the recipe creates the "
            f"row; catch variants create nothing); got {section.get('records')!r}"
        )
    expected_schema = SF_SCHEMA if schema_required else []
    if section.get("schema") != expected_schema:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must be "
            f"{'the pinned 7-field Survey_Response__c set (6 mdapi FLS re-ensures + the missing Type__c Tooling-create)' if schema_required else '[] (the catch variant never reaches the create)'}"
        )
