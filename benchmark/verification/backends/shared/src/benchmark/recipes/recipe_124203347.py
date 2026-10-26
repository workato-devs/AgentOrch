from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_124203347


RECIPE_ID = "124203347"
SEED_TYPE = "slack_bot_opportunity_team_member_add_variant"
TRACK = "live_salesforce_slack_opportunity_team_member_add"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"
TRIGGER_AS = "688055db"
OTM_SOBJECT = "OpportunityTeamMember"
OTM_SEARCH_AS = "3eb6ef17"
OPP_SEARCH_AS = "fbb7b395"
CREATE_AS = "3bdf6080"
ADD_POST_AS = "73e80daa"
PRESENT_POST_AS = "ed5b9843"
RAW_CHANNEL = "C06USNHSQ6M"  # non-U literal -> raw_executor routes to SLACK_CHANNEL_OVERRIDE
TEAM_ROLE = "RevOps BDE"
ADDED_PREFIX = "Added to "
PRESENT_PREFIX = "Current Opportunity Team Member on "
REQUIRED_SCHEMA = [
    {"sobject": "OpportunityTeamMember__c", "field": "OpportunityId__c", "sf_type": "Text"},
    {"sobject": "OpportunityTeamMember__c", "field": "UserId__c", "sf_type": "Text"},
    {"sobject": "OpportunityTeamMember__c", "field": "TeamMemberRole__c", "sf_type": "Text"},
]
TRIGGER_PARAM_KEYS = ("user_id", "message_id", "account_id", "opportunity_id")
OPP_FIELD_KEYS = {"Name", "StageName", "CloseDate"}
OTM_FIELD_KEYS = {"Name", "OpportunityId", "TeamMemberRole", "UserId"}
OPP_TOKEN = "$OPP_ID"
USER_TOKEN = "$CURRENT_USER_ID"
TS_TOKEN = "$SLACK_MESSAGE_TS"
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_SYNTHETIC_ACCOUNT_RE = re.compile(r"001[0-9A-Za-z]{12,15}")
_SYNTHETIC_USER_RE = re.compile(r"005[0-9A-Za-z]{12,15}")
_TS_RE = re.compile(r"\d{10}\.\d{6}")


_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "688055db",
  "provider": "slack_bot",
  "name": "bot_command_v2",
  "skip": false,
  "input": {
   "allow_dialog": "true",
   "domain": "salesforce",
   "name": "add",
   "parameters": "[\n  {\n    \"name\": \"user_id\",\n    \"type\": \"string\",\n    \"optional\": true,\n    \"label\": \"User ID\",\n    \"control_type\": \"text\"\n  },\n  {\n    \"name\": \"message_id\",\n    \"type\": \"string\",\n    \"optional\": true,\n    \"label\": \"Message ID\",\n    \"control_type\": \"text\"\n  },\n  {\n    \"name\": \"account_id\",\n    \"type\": \"string\",\n    \"optional\": true,\n    \"label\": \"Account ID\",\n    \"control_type\": \"text\"\n  },\n  {\n    \"name\": \"opportunity_id\",\n    \"type\": \"string\",\n    \"optional\": true,\n    \"label\": \"Opportunity ID\",\n    \"control_type\": \"text\"\n  }\n]",
   "scope": "opportunity"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "3eb6ef17",
  "provider": "salesforce",
  "name": "search_sobjects",
  "skip": false,
  "input": {
   "OpportunityId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"688055db\",\"path\":[\"parameters\", \"opportunity_id\"]}')}",
   "TeamMemberRole": "RevOps BDE",
   "UserId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"688055db\",\"path\":[\"parameters\", \"user_id\"]}')}",
   "field_list": "UserId",
   "limit": "150",
   "sobject_name": "OpportunityTeamMember"
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "fbb7b395",
  "provider": "salesforce",
  "name": "search_sobjects",
  "skip": false,
  "input": {
   "Id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"688055db\",\"path\":[\"parameters\", \"opportunity_id\"]}')}",
   "field_list": "Name",
   "limit": "150",
   "sobject_name": "Opportunity"
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
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"3eb6ef17\",\"path\":[\"list_size\"]}')}",
     "operand": "equals_to",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "3bdf6080",
  "provider": "salesforce",
  "name": "create_custom_object",
  "skip": false,
  "input": {
   "OpportunityId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"688055db\",\"path\":[\"parameters\", \"opportunity_id\"]}')}",
   "TeamMemberRole": "RevOps BDE",
   "UserId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"688055db\",\"path\":[\"parameters\", \"user_id\"]}')}",
   "sobject_name": "OpportunityTeamMember"
  }
 },
 {
  "keyword": "action",
  "number": 6,
  "as": "73e80daa",
  "provider": "slack_bot",
  "name": "post_bot_message",
  "skip": false,
  "input": {
   "advanced": {
    "ts": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"688055db\",\"path\":[\"parameters\", \"message_id\"]}')}"
   },
   "blocks": [
    {
     "block_type": "section_with_text",
     "button_type": "continue_flow",
     "section_text": "Added to #{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"fbb7b395\",\"path\":[\"Opportunity\", {\"path_element_type\": \"current_item\"}, \"Name\"]}')}"
    }
   ],
   "channel": "C06USNHSQ6M"
  }
 },
 {
  "keyword": "if",
  "number": 7,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"3eb6ef17\",\"path\":[\"list_size\"]}')}",
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
  "number": 8,
  "as": "ed5b9843",
  "provider": "slack_bot",
  "name": "post_bot_message",
  "skip": false,
  "input": {
   "advanced": {
    "ts": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"688055db\",\"path\":[\"parameters\", \"message_id\"]}')}"
   },
   "blocks": [
    {
     "block_type": "section_with_text",
     "button_type": "continue_flow",
     "section_text": "Current Opportunity Team Member on #{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"fbb7b395\",\"path\":[\"Opportunity\", {\"path_element_type\": \"current_item\"}, \"Name\"]}')}"
    }
   ],
   "channel": "C06USNHSQ6M"
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.search_records",
    "salesforce.create_record",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "salesforce.create_record",
    "slack.post_message",
]
EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "otm_precheck_count",
    "created",
    "slack_text",
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


def validate_124203347(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_124203347(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_124203347(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole "
            "run instead of exercising a recipe branch"
        )
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"salesforce"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    expect = data.get("expect")
    salesforce_section = seed_in.get("salesforce")
    _require_salesforce_section(salesforce_section, trigger)
    _require_expect_shape(expect, trigger, salesforce_section)
    slack_expected = "slack.post_message" in (expect.get("tools") or [])
    slack_seed = data.get("slack_seed_message")
    if slack_expected != isinstance(slack_seed, dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} slack_seed_message must be present exactly when the variant "
            f"expects a slack post (chat.update needs a live seeded ts); "
            f"slack_expected={slack_expected}"
        )
    if slack_expected and not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    provision = ctx.tools.call(
        "harness.salesforce.seed_records", {"salesforce": deepcopy(salesforce_section)}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    refs = _salesforce_ref_tokens(salesforce_section, provision)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
    }
    if slack_expected:
        text = str(slack_seed.get("text") or "")
        if not text.strip():
            raise RuntimeError(f"recipe {RECIPE_ID} slack_seed_message.text must be non-empty")
        posted = ctx.tools.call(
            "harness.slack.seed_message",
            {"channel": ctx.env.slack_channel_override, "text": text},
        )
        channel = str(posted.get("channel") or ctx.env.slack_channel_override)
        ts = str(posted.get("ts") or "")
        if not ts:
            raise RuntimeError(f"recipe {RECIPE_ID} Slack seed message returned no ts: {posted}")
        refs[TS_TOKEN] = ts
        refs["$SLACK_CHANNEL"] = channel
        out["seed_slack_message"] = {"channel": channel, "ts": ts, "text": text}
    trigger = _replace_value(trigger, refs)
    expect = _replace_value(deepcopy(expect), refs)
    _require_no_tokens(trigger, "trigger")
    _require_no_tokens(expect, "expect")
    out["trigger"] = trigger
    out["expect"] = expect
    out["salesforce_ref_tokens"] = refs
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_124203347(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_124203347(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    slack_expected = "slack.post_message" in (expect.get("tools") or [])
    message = seed.get("seed_slack_message") if isinstance(seed.get("seed_slack_message"), dict) else {}
    if slack_expected and not (message.get("channel") and message.get("ts")):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing the live seed_slack_message ts")
    if slack_expected and not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
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
        details["initial_snapshot"] = _snapshot(ctx)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx)
    finally:
        # Required cleanup: ALL owned Salesforce records (seeded Opportunity/
        # OTM rows AND the row the recipe itself created) must not leak. The
        # seeded slack message is updated in place and left in the override
        # channel per policy (it is the run's observable).
        cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
        details["cleanup_response"] = cleanup_response
    if not cleanup_response.get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce cleanup failed: {cleanup_response}")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_124203347(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {"parameters"} or not isinstance(trigger.get("parameters"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'parameters': {{...}}}}"
        )
    parameters = trigger["parameters"]
    if tuple(sorted(parameters)) != tuple(sorted(TRIGGER_PARAM_KEYS)):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must carry exactly "
            f"{sorted(TRIGGER_PARAM_KEYS)} (the declared bot_command_v2 schema); "
            f"got {sorted(parameters)}"
        )
    if parameters.get("opportunity_id") != OPP_TOKEN:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters.opportunity_id must be the {OPP_TOKEN!r} "
            "token (both searches and the create dereference the LIVE seeded Opportunity id)"
        )
    if parameters.get("user_id") != USER_TOKEN:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters.user_id must be the {USER_TOKEN!r} token "
            "(a REAL org user id, read-only-resolved at seed time; Users are never created)"
        )
    account_id = str(parameters.get("account_id") or "")
    if not _SYNTHETIC_ACCOUNT_RE.fullmatch(account_id):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters.account_id must be a well-formed synthetic "
            f"001 id (declared in the payload schema but never dereferenced): {account_id!r}"
        )
    message_id = str(parameters.get("message_id") or "")
    if message_id != TS_TOKEN and not _TS_RE.fullmatch(message_id):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters.message_id must be the {TS_TOKEN!r} token "
            f"(slack-post variants) or a ts-shaped literal (no-post variants): {message_id!r}"
        )


def _seeded_otm_records(section: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        record
        for record in section.get("records") or []
        if isinstance(record, dict) and str(record.get("sobject") or "") == OTM_SOBJECT
    ]


def _matching_otm_count(section: dict[str, Any], trigger: dict[str, Any]) -> int:
    parameters = trigger.get("parameters") or {}
    return sum(
        1
        for record in _seeded_otm_records(section)
        if str((record.get("fields") or {}).get("OpportunityId")) == str(parameters.get("opportunity_id"))
        and str((record.get("fields") or {}).get("TeamMemberRole")) == TEAM_ROLE
        and str((record.get("fields") or {}).get("UserId")) == str(parameters.get("user_id"))
    )


def _opportunity_record(section: dict[str, Any]) -> dict[str, Any]:
    opportunities = [
        record
        for record in section.get("records") or []
        if isinstance(record, dict) and str(record.get("sobject") or "") == "Opportunity"
    ]
    if len(opportunities) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.records must contain exactly ONE Opportunity "
            f"(the step-3 search pins result_count 1); got {len(opportunities)}"
        )
    return opportunities[0]


def _require_salesforce_section(section: Any, trigger: dict[str, Any]) -> None:
    if not isinstance(section, dict) or sorted(section) != [
        "current_user",
        "records",
        "schema",
        "strict_soql_conditions",
    ]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce must be exactly {{'strict_soql_conditions': "
            "true, 'current_user': ..., 'schema': ..., 'records': ...}}"
        )
    if section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true "
            "(benchmark policy; the searches use exact field filters)"
        )
    if section.get("current_user") != {"sobject": "User"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.current_user must be {{'sobject': 'User'}} "
            "(read-only live resolution of the running user id -- never creates a User)"
        )
    if section.get("schema") != REQUIRED_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare exactly "
            f"{json.dumps(REQUIRED_SCHEMA)} (the stand-in object pre-exists with NO fields)"
        )
    records = section.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records must be a non-empty list")
    opportunity = _opportunity_record(section)
    if str(opportunity.get("ref") or "").strip().lower() != "opp":
        raise RuntimeError(f"recipe {RECIPE_ID} the Opportunity seed must use ref 'opp'")
    opp_fields = opportunity.get("fields")
    if not isinstance(opp_fields, dict) or set(opp_fields) != OPP_FIELD_KEYS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} Opportunity fields must be exactly {sorted(OPP_FIELD_KEYS)} "
            "(org-required Name/StageName/CloseDate; nothing the recipe never reads)"
        )
    if not str(opp_fields.get("Name") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} Opportunity Name must be non-empty")
    for record in records:
        if not isinstance(record, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} seeded records must be objects: {record}")
        sobject = str(record.get("sobject") or "")
        if sobject == "Opportunity":
            continue
        if sobject != OTM_SOBJECT:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seeded records must be Opportunity or {OTM_SOBJECT}: {record}"
            )
        if not str(record.get("ref") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} every seeded record needs a 'ref': {record}")
        fields = record.get("fields")
        if not isinstance(fields, dict) or set(fields) != OTM_FIELD_KEYS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {OTM_SOBJECT} seeds must set exactly "
                f"{sorted(OTM_FIELD_KEYS)}; got {record}"
            )
        for key in OTM_FIELD_KEYS:
            if not isinstance(fields.get(key), str) or not fields[key].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {OTM_SOBJECT} seed {key} must be a non-empty string: {record}"
                )
        if fields["OpportunityId"] != OPP_TOKEN:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {OTM_SOBJECT} seeds must reference the seeded Opportunity "
                f"via {OPP_TOKEN!r}: {record}"
            )
        if fields["UserId"] != USER_TOKEN and not _SYNTHETIC_USER_RE.fullmatch(fields["UserId"]):
            raise RuntimeError(
                f"recipe {RECIPE_ID} {OTM_SOBJECT} seed UserId must be {USER_TOKEN!r} or a "
                f"well-formed 005 decoy id (Text column; no User is created): {record}"
            )


def _require_expect_shape(expect: Any, trigger: dict[str, Any], section: dict[str, Any]) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(set(expect) - set(EXPECT_KEYS))
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
    precheck = _matching_otm_count(section, trigger)
    if expect.get("otm_precheck_count") != precheck:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.otm_precheck_count must equal the number of seeded OTM "
            f"rows matching ALL THREE trigger filters ({precheck}); got "
            f"{expect.get('otm_precheck_count')!r}"
        )
    created = precheck == 0
    if expect.get("created") is not created:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.created must be {created} (IF4 fires exactly when the "
            "pre-create search returns 0 rows)"
        )
    opp_name = str((_opportunity_record(section).get("fields") or {}).get("Name") or "")
    if created:
        expected_text = ADDED_PREFIX + opp_name
        expected_tools = [
            "salesforce.search_records",
            "salesforce.search_records",
            "salesforce.create_record",
            "slack.post_message",
        ]
    elif precheck == 1:
        expected_text = PRESENT_PREFIX + opp_name
        expected_tools = [
            "salesforce.search_records",
            "salesforce.search_records",
            "slack.post_message",
        ]
    else:
        expected_text = None
        expected_tools = ["salesforce.search_records", "salesforce.search_records"]
    if tools != expected_tools:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools must be {expected_tools} for otm_precheck_count "
            f"{precheck}; got {tools}"
        )
    if expect.get("executed_action_count") != len(expected_tools):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.executed_action_count must be {len(expected_tools)}"
        )
    if expect.get("slack_text") != expected_text:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.slack_text must be {expected_text!r} (the rendered "
            f"section_text over the seeded Opportunity Name); got {expect.get('slack_text')!r}"
        )


def _salesforce_ref_tokens(section: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    rows = [row for row in salesforce_snapshot.get("records") or [] if isinstance(row, dict)]
    owned_ids = [str(row.get("id") or "") for row in rows if not row.get("read_only") and row.get("id")]
    user_ids = [
        str(row.get("id") or "")
        for row in rows
        if row.get("read_only") and str(row.get("sobject") or "") == "User" and row.get("id")
    ]
    if len(user_ids) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expected exactly one read-only current-user row in the seed "
            f"snapshot; got {len(user_ids)}"
        )
    seed_records = [record for record in section.get("records") or [] if isinstance(record, dict)]
    if len(owned_ids) != len(seed_records):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed/snapshot record count mismatch: "
            f"{len(seed_records)} seeded vs {len(owned_ids)} provisioned"
        )
    refs: dict[str, str] = {USER_TOKEN: user_ids[0]}
    for idx, record in enumerate(seed_records):
        ref = str(record.get("ref") or "").strip()
        if ref:
            refs[f"${ref.upper()}_ID"] = owned_ids[idx]
    return refs


def _replace_value(value: Any, refs: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_value(item, refs) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_value(item, refs) for item in value]
    if isinstance(value, str):
        out = value
        for token, replacement in refs.items():
            out = out.replace(token, replacement)
        return out
    return value


def _require_no_tokens(value: Any, label: str) -> None:
    leftover = sorted(set(_TOKEN_RE.findall(json.dumps(value))))
    if leftover:
        raise RuntimeError(f"recipe {RECIPE_ID} {label} has unresolved seed tokens: {leftover}")


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return ctx.tools.call("harness.salesforce.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
