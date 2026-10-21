from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_88783356


RECIPE_ID = "88783356"
SEED_TYPE = "workato_service_campaign_member_create_variant"
TRACK = "live_salesforce_campaign_member_service_create"
TRIGGER_PROVIDER = "workato_service"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "d422758b"
SERVICE_NAME = "Add person to Salesforce campaign"
CREATE_STEP_AS = "25a6445f"
SUCCESS_REPLY_AS = "eae47ad6"
CATCH_AS = "b3123d81"
ERROR_REPLY_AS = "c764d8ca"
SOBJECT = "CampaignMember"
NOTES_FIELD = "Campaign_Member_Notes__c"

# workato_service.receive_request 'Add person to Salesforce campaign'
# (as d422758b): request {lead_or_contact_id req, campaign_id req, notes opt,
# status req}. Body = one TRY:
#   3 salesforce.create_custom_object 25a6445f (LIVE create_record)
#     CampaignMember: CampaignId <- request.campaign_id,
#     Campaign_Member_Notes__c <- request.notes (a MISSING pill drops the
#     column entirely; re-probed), Status <- request.status, and the
#     SKIP-TERNARY PAIR over ONE request field:
#       ContactId = starts_with?("003") ? id : skip
#       LeadId    = starts_with?("00Q") ? id : skip
#     A 003-id keeps ContactId and DROPS LeadId; a 00Q-id the reverse; any
#     other prefix drops BOTH (the id then never reaches Salesforce at all)
#     and the live org rejects a CampaignMember without Lead/Contact ->
#     catch. The SKIP sentinel never reaches tool args (raw_executor
#     salesforce_create; re-probed).
#   4 workato_service.send_reply eae47ad6 success,
#     reply.campaign_member_id <- salesforce.25a6445f.id: the LIVE created
#     id, threaded from the create result - never a pinnable literal. NOT
#     terminal (send_reply does not stop a service recipe).
#   CATCH 5 (as b3123d81, max_retry_count 0):
#     6 workato_service.send_reply c764d8ca reply_type 'error', message
#       <- catch.b3123d81.message. The node's 'code' 500 and
#       'custom_error_response' true are NOT forwarded by the send_reply
#       adapter (only reply_type/reply/message; re-probed) - NEVER pin them.
#       The failed create never traces, so the catch branch executes exactly
#       ONE action.
#
# Live backend: Salesforce. Campaign + Contact/Lead are seeded live
# (harness.salesforce.seed_records); Campaign_Member_Notes__c provisions via
# ensure_custom_field schema-in-seed (idempotent Tooling-API create + FLS).
# CampaignMember is a standard sobject - no stand-in. The RECIPE-CREATED
# member is registered as owned by the run harness; cleanup deletes ALL owned
# records (member first - reverse creation order) in the runner's finally.
# Workato-internal mock: service trigger + send_reply.
#
# Branch mapping (offline dry-replay re-probed on this tree, 2026-07-08):
# - contact_member_created (2 actions): id $CONTACT_ID (003...) -> fields
#   {CampaignId, ContactId, Status, notes?}; LeadId ABSENT from args.
# - lead_member_created (2 actions): id $LEAD_ID (00Q...) -> fields
#   {CampaignId, LeadId, Status}; ContactId ABSENT; this variant also omits
#   notes to prove the MISSING-pill column drop.
# - bad_id_error_reply (1 action): a well-formed 005... id -> both ternaries
#   SKIP -> live create rejected (no Lead/Contact) -> catch -> error reply
#   {reply_type error, reply {}, message = live SF error text}. The message
#   is LIVE text: pinned as __ANY__; the verifier checks catch->reply
#   consistency, that the seeded Campaign is untouched, and that no
#   CampaignMember exists.
# Status stays within {'Sent','Responded'} (default CampaignMemberStatus
# values in the benchmark org; triage-verified live).
# Blank-string notes are rejected by the seeder: the executor would pass
# Campaign_Member_Notes__c '' but the live harness drops blank strings before
# the POST, so '' is not authorable groundtruth (absence is).
# Service->SF precedent: recipe_88708198 (committed this batch).

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "workato_service", "name": "receive_request", "as": "d422758b", "skip": false, "input": {"reply_schema_json": "[{\"name\":\"campaign_member_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"}]", "request_schema_json": "[{\"name\":\"lead_or_contact_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"campaign_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"notes\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"},{\"name\":\"status\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"}]", "service_name": "Add person to Salesforce campaign"}, "block": [{"number": 2, "keyword": "try", "provider": "", "name": "", "as": "", "skip": false, "input": {}, "block": [{"number": 3, "keyword": "action", "provider": "salesforce", "name": "create_custom_object", "as": "25a6445f", "skip": false, "input": {"CampaignId": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"d422758b\",\"path\":[\"request\", \"campaign_id\"]}')}", "Campaign_Member_Notes__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"d422758b\",\"path\":[\"request\", \"notes\"]}')}", "ContactId": "=_('data.workato_service.d422758b.request.lead_or_contact_id').starts_with?(\"003\") ? _('data.workato_service.d422758b.request.lead_or_contact_id') : skip", "LeadId": "=_('data.workato_service.d422758b.request.lead_or_contact_id').starts_with?(\"00Q\") ? _('data.workato_service.d422758b.request.lead_or_contact_id') : skip", "Status": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"d422758b\",\"path\":[\"request\", \"status\"]}')}", "sobject_name": "CampaignMember"}, "block": []}, {"number": 4, "keyword": "action", "provider": "workato_service", "name": "send_reply", "as": "eae47ad6", "skip": false, "input": {"reply": {"campaign_member_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"25a6445f\",\"path\":[\"id\"]}')}"}, "reply_type": "success"}, "block": []}, {"number": 5, "keyword": "catch", "provider": "", "name": "", "as": "b3123d81", "skip": false, "input": {"max_retry_count": "0", "retry_interval": "2"}, "block": [{"number": 6, "keyword": "action", "provider": "workato_service", "name": "send_reply", "as": "c764d8ca", "skip": false, "input": {"code": "500", "custom_error_response": "true", "message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"b3123d81\",\"path\":[\"message\"]}')}", "reply_type": "error"}, "block": []}]}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[int, str, str, str]] = [
    (3, CREATE_STEP_AS, "salesforce", "create_custom_object"),
    (4, SUCCESS_REPLY_AS, "workato_service", "send_reply"),
    (6, ERROR_REPLY_AS, "workato_service", "send_reply"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.create_record",
    "workato_service.send_reply",
]
ALLOWED_TOOLS: list[str] = list(EXPECTED_RAW_TOOLS)
REQUIRED_EXPECT_KEYS = (
    "branch",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "created_fields",
    "reply",
    "member_created",
)
BRANCHES = ("contact_member_created", "lead_member_created", "bad_id_error_reply")
REQUEST_KEYS = ("lead_or_contact_id", "campaign_id", "notes", "status")
ALLOWED_STATUSES = ("Sent", "Responded")
# Pinned schema-in-seed: re-ensure the notes custom field (+FLS) on every run
# (ensure_custom_field is idempotent). control_type text-area -> TextArea.
SF_SCHEMA: list[dict[str, str]] = [
    {"sobject": SOBJECT, "field": NOTES_FIELD, "sf_type": "TextArea"},
]
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_SF_ID_RE = re.compile(r"[a-zA-Z0-9]{15,18}")
# The deliberate neither-prefix id the catch variant sends: well-formed
# 18-char id shape (realistic caller mistake - a 005 User id), but it never
# reaches Salesforce because BOTH skip-ternaries drop it.
_BAD_ID_RE = re.compile(r"^005[a-zA-Z0-9]{12}(?:[a-zA-Z0-9]{3})?$")


def validate_88783356(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    if str((raw.get("input") or {}).get("service_name") or "") != SERVICE_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} service name changed")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    # Semantic pins over the drift-prone bits (the tree pin holds the bytes;
    # these name the trap when one changes).
    create = next(node for node in _walk_nodes(raw) if str(node.get("as") or "") == CREATE_STEP_AS)
    create_input = create.get("input") or {}
    if create_input.get("sobject_name") != SOBJECT:
        raise RuntimeError(f"recipe {RECIPE_ID} create sobject changed")
    path = f"data.workato_service.{TRIGGER_AS}.request.lead_or_contact_id"
    for field, prefix in (("ContactId", "003"), ("LeadId", "00Q")):
        expected = f"=_('{path}').starts_with?(\"{prefix}\") ? _('{path}') : skip"
        if str(create_input.get(field) or "") != expected:
            raise RuntimeError(
                f"recipe {RECIPE_ID} skip-ternary for {field} changed: "
                f"{create_input.get(field)!r}"
            )
    if set(create_input) - {"sobject_name"} != {
        "CampaignId", NOTES_FIELD, "ContactId", "LeadId", "Status",
    }:
        raise RuntimeError(f"recipe {RECIPE_ID} create field set changed: {sorted(create_input)}")
    success = next(node for node in _walk_nodes(raw) if str(node.get("as") or "") == SUCCESS_REPLY_AS)
    success_reply = ((success.get("input") or {}).get("reply") or {})
    if CREATE_STEP_AS not in str(success_reply.get("campaign_member_id") or ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} success reply no longer threads the created id: "
            f"{success_reply!r}"
        )
    error_reply = next(node for node in _walk_nodes(raw) if str(node.get("as") or "") == ERROR_REPLY_AS)
    error_input = error_reply.get("input") or {}
    if error_input.get("reply_type") != "error" or CATCH_AS not in str(error_input.get("message") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} error reply changed: {error_input!r}")
    control = {
        (str(node.get("keyword") or ""), int(node.get("number") or 0)): node
        for node in _walk_nodes(raw)
        if node.get("keyword") in {"try", "catch", "if", "foreach", "stop", "else"}
    }
    if sorted(control) != [("catch", 5), ("try", 2)]:
        raise RuntimeError(f"recipe {RECIPE_ID} control nodes changed: {sorted(control)}")
    catch_node = control[("catch", 5)]
    if str(catch_node.get("as") or "") != CATCH_AS or catch_node.get("input") != {
        "max_retry_count": "0",
        "retry_interval": "2",
    }:
        raise RuntimeError(f"recipe {RECIPE_ID} catch node changed")
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
        "service_name": SERVICE_NAME,
        "sobject": SOBJECT,
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


def seed_88783356(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88783356(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    request = _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    expect = data.get("expect")
    _require_expect_common(expect)
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} never forces action errors: the catch branch runs on "
            "the live rejection of a CampaignMember without Lead/Contact instead"
        )
    branch = expect["branch"]
    _require_branch(branch, request, seed_in, expect)
    provision = ctx.tools.call(
        "harness.salesforce.seed_records", {"salesforce": deepcopy(seed_in["salesforce"])}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    refs = _salesforce_ref_tokens(seed_in["salesforce"], provision)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": dict(refs),
        "trigger": _replace_value(trigger, refs),
        "expect": _replace_value(deepcopy(expect), refs),
    }
    _require_resolved(out["trigger"], "trigger")
    _require_resolved(out["expect"], "expect")
    resolved_id = str(((out["trigger"].get("request") or {}).get("lead_or_contact_id")) or "")
    if branch == "contact_member_created" and not resolved_id.startswith("003"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the provisioned Contact id does not carry the 003 "
            f"prefix the ternary keys on: {resolved_id!r}"
        )
    if branch == "lead_member_created" and not resolved_id.startswith("00Q"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the provisioned Lead id does not carry the 00Q "
            f"prefix the ternary keys on: {resolved_id!r}"
        )
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_88783356(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88783356(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} every variant seeds live Salesforce records (the catch "
            "variant proves its Campaign untouched); missing salesforce_live state"
        )
    raw_execution: dict[str, Any] | None = None
    initial_snapshot: dict[str, Any] = {}
    final_snapshot: dict[str, Any] = {}
    cleanup: dict[str, Any] | None = None
    try:
        initial_snapshot = dict(ctx.tools.call("harness.salesforce.snapshot", {}))
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = dict(ctx.tools.call("harness.salesforce.snapshot", {}))
    finally:
        # Required cleanup: the run owns the seeded Campaign/Contact/Lead AND
        # the CampaignMember the recipe itself created (create_record registers
        # it); delete ALL owned records whether or not the run completed.
        cleanup = ctx.tools.call("harness.salesforce.cleanup", {})
    if not (cleanup or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce cleanup failed: {cleanup}")
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
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
            "cleanup_response": {"salesforce": cleanup},
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_88783356(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> dict[str, Any]:
    if sorted(trigger.keys()) != ["request"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the request object; "
            f"got {sorted(trigger.keys())}"
        )
    request = trigger.get("request")
    if not isinstance(request, dict) or not request:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input.request must be a non-empty object")
    unknown = sorted(set(request) - set(REQUEST_KEYS))
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} request carries undeclared fields: {unknown}")
    for key in ("lead_or_contact_id", "campaign_id", "status"):
        value = request.get(key)
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} request.{key} is required (schema optional: false); "
                f"got {value!r}"
            )
    if request.get("status") not in ALLOWED_STATUSES:
        raise RuntimeError(
            f"recipe {RECIPE_ID} request.status must stay within {ALLOWED_STATUSES} "
            f"(default CampaignMemberStatus values in the benchmark org); got "
            f"{request.get('status')!r}"
        )
    if "notes" in request:
        notes = request.get("notes")
        if not isinstance(notes, str) or not notes.strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} request.notes must be a non-empty string when "
                f"present: the live harness drops blank strings before the POST, so "
                f"'' is not authorable groundtruth (omit the key instead); got {notes!r}"
            )
    if request.get("campaign_id") != "$CAMPAIGN_ID":
        raise RuntimeError(
            f"recipe {RECIPE_ID} request.campaign_id must be the $CAMPAIGN_ID token "
            f"(the live create needs a real Campaign id); got {request.get('campaign_id')!r}"
        )
    return request


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
    if not isinstance(expect.get("reply"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.reply must pin the final send_reply args")


def _expected_created_fields(branch: str, request: dict[str, Any]) -> dict[str, Any]:
    """Groundtruth of the create args: the skip-ternary pair keeps at most one
    of ContactId/LeadId, and a MISSING notes pill drops the column. At
    validation time the id is still the $CONTACT_ID/$LEAD_ID seed token, so
    the kept arm follows the BRANCH; the seeder re-checks the live 003/00Q
    prefix on the provisioned id after token replacement."""
    record_id = str(request.get("lead_or_contact_id") or "")
    fields: dict[str, Any] = {"CampaignId": request.get("campaign_id")}
    if "notes" in request:
        fields[NOTES_FIELD] = request.get("notes")
    if branch == "contact_member_created":
        fields["ContactId"] = record_id
    if branch == "lead_member_created":
        fields["LeadId"] = record_id
    fields["Status"] = request.get("status")
    return fields


def _require_branch(
    branch: str,
    request: dict[str, Any],
    seed_in: dict[str, Any],
    expect: dict[str, Any],
) -> None:
    if sorted(seed_in.keys()) != ["salesforce"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} every variant seeds exactly the salesforce section; "
            f"got {sorted(seed_in.keys())}"
        )
    record_id = str(request.get("lead_or_contact_id") or "")
    if branch == "contact_member_created":
        if record_id != "$CONTACT_ID":
            raise RuntimeError(
                f"recipe {RECIPE_ID} contact_member_created must send lead_or_contact_id "
                f"as the $CONTACT_ID token (live Contact ids carry the 003 prefix the "
                f"ternary keys on); got {record_id!r}"
            )
        _require_salesforce_section(seed_in["salesforce"], "Contact")
    elif branch == "lead_member_created":
        if record_id != "$LEAD_ID":
            raise RuntimeError(
                f"recipe {RECIPE_ID} lead_member_created must send lead_or_contact_id "
                f"as the $LEAD_ID token (live Lead ids carry the 00Q prefix); got {record_id!r}"
            )
        if "notes" in request:
            raise RuntimeError(
                f"recipe {RECIPE_ID} lead_member_created must OMIT notes (this variant "
                f"pins the MISSING-pill column drop)"
            )
        _require_salesforce_section(seed_in["salesforce"], "Lead")
    else:  # bad_id_error_reply
        if not _BAD_ID_RE.fullmatch(record_id):
            raise RuntimeError(
                f"recipe {RECIPE_ID} bad_id_error_reply must send a LITERAL well-formed "
                f"005-prefixed id (neither 003 nor 00Q -> both ternaries skip); got "
                f"{record_id!r}"
            )
        _require_salesforce_section(seed_in["salesforce"], None)
    expected_fields = _expected_created_fields(branch, request)
    if branch == "bad_id_error_reply":
        if "ContactId" in expected_fields or "LeadId" in expected_fields:
            raise RuntimeError(
                f"recipe {RECIPE_ID} bad_id_error_reply derived an id arm -- the "
                f"neither-prefix invariant broke: {expected_fields!r}"
            )
        checks = (
            expect.get("executed_action_count") == 1,
            expect.get("tools") == ["workato_service.send_reply"],
            expect.get("created_fields") is None,
            expect.get("member_created") is False,
            expect.get("reply")
            == {"reply_type": "error", "reply": {}, "message": "__ANY__"},
        )
        if not all(checks):
            raise RuntimeError(
                f"recipe {RECIPE_ID} bad_id_error_reply expect block is inconsistent "
                f"(1 action, error reply with __ANY__ live message, null created_fields): "
                f"{expect!r}"
            )
        expected_items = [
            {
                "tool": "workato_service.send_reply",
                "args_contains": {
                    "reply_type": "error",
                    "reply": {},
                    "message": "__ANY__",
                },
            },
        ]
    else:
        arm = "ContactId" if branch == "contact_member_created" else "LeadId"
        dropped = "LeadId" if arm == "ContactId" else "ContactId"
        if arm not in expected_fields or dropped in expected_fields:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {branch} derived fields lost the {arm}/{dropped} "
                f"split: {expected_fields!r}"
            )
        checks = (
            expect.get("executed_action_count") == 2,
            expect.get("tools")
            == ["salesforce.create_record", "workato_service.send_reply"],
            expect.get("created_fields") == expected_fields,
            expect.get("member_created") is True,
            expect.get("reply")
            == {"reply_type": "success", "reply": {"campaign_member_id": "__ANY__"}},
        )
        if not all(checks):
            raise RuntimeError(
                f"recipe {RECIPE_ID} {branch} expect block contradicts the derived "
                f"create fields {expected_fields!r} / the __ANY__ live-id reply: {expect!r}"
            )
        expected_items = [
            {
                "tool": "salesforce.create_record",
                "args_contains": {"sobject": SOBJECT, "fields": deepcopy(expected_fields)},
            },
            {
                "tool": "workato_service.send_reply",
                "args_contains": {
                    "reply_type": "success",
                    "reply": {"campaign_member_id": "__ANY__"},
                },
            },
        ]
    if expect.get("tool_expectations") != expected_items:
        raise RuntimeError(
            f"recipe {RECIPE_ID} {branch} tool_expectations must pin exactly the derived "
            f"items; expected {expected_items!r}, got {expect.get('tool_expectations')!r}"
        )


def _require_salesforce_section(section: Any, member_sobject: str | None) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["records", "schema"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce must be exactly {{'schema': ..., "
            f"'records': ...}}; got {sorted(section) if isinstance(section, dict) else section!r}"
        )
    if section.get("schema") != SF_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must be the pinned "
            f"{NOTES_FIELD} schema-in-seed entry (re-ensures the field + FLS)"
        )
    records = section.get("records")
    expected_shapes = [("Campaign", "campaign")]
    if member_sobject == "Contact":
        expected_shapes.append(("Contact", "contact"))
    elif member_sobject == "Lead":
        expected_shapes.append(("Lead", "lead"))
    if not isinstance(records, list) or len(records) != len(expected_shapes):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.records must contain exactly "
            f"{[shape[0] for shape in expected_shapes]}; got {records!r}"
        )
    for record, (sobject, ref) in zip(records, expected_shapes):
        if (
            not isinstance(record, dict)
            or record.get("sobject") != sobject
            or str(record.get("ref") or "") != ref
            or not isinstance(record.get("fields"), dict)
            or set(record) != {"sobject", "ref", "fields"}
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed record must be {{sobject: {sobject}, ref: "
                f"{ref!r}, fields: ...}}; got {record!r}"
            )
        fields = record["fields"]
        required = {
            "Campaign": ["Name"],
            "Contact": ["LastName"],
            "Lead": ["LastName", "Company"],
        }[sobject]
        for key in required:
            if not isinstance(fields.get(key), str) or not str(fields.get(key)).strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} seed {sobject} needs a non-empty {key}: {fields!r}"
                )
        for key, value in fields.items():
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} seed {sobject} field {key} must be a non-empty "
                    f"string: {value!r}"
                )


def _salesforce_ref_tokens(seed_section: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    records = [record for record in salesforce_snapshot.get("records") or [] if isinstance(record, dict)]
    owned = [record for record in records if not record.get("read_only")]
    seed_records = [record for record in seed_section.get("records") or [] if isinstance(record, dict)]
    if len(owned) != len(seed_records):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed/snapshot record count mismatch: "
            f"{len(seed_records)} seeded vs {len(owned)} provisioned"
        )
    refs: dict[str, str] = {}
    for idx, record in enumerate(seed_records):
        ref = str(record.get("ref") or "").strip()
        live_id = str(owned[idx].get("id") or "")
        if not _SF_ID_RE.fullmatch(live_id):
            raise RuntimeError(f"recipe {RECIPE_ID} provisioned record id looks invalid: {live_id!r}")
        refs[f"${ref.upper()}_ID"] = live_id
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


def _require_resolved(value: dict[str, Any], label: str) -> None:
    leftover = _TOKEN_RE.findall(json.dumps(value))
    if leftover:
        raise RuntimeError(f"recipe {RECIPE_ID} {label} has unresolved seed tokens: {leftover}")


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
