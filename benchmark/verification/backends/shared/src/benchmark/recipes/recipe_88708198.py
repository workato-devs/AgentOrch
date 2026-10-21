from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_88708198


RECIPE_ID = "88708198"
SEED_TYPE = "workato_service_campaign_activity_update_variant"
TRACK = "live_salesforce_campaign_activity_service_update"
TRIGGER_PROVIDER = "workato_service"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "d42d4f2a"
SERVICE_NAME = "Update Campaign Activity"
UPDATE_STEP_AS = "8753d35d"
SUCCESS_REPLY_AS = "18f926a3"
CATCH_AS = "2d7b3539"
ERROR_REPLY_AS = "06138c68"
SOBJECT = "Campaign_Activity__c"
# The deliberate non-owned Campaign_Activity__c id the catch variant sends:
# OwnedSalesforce refuses it DETERMINISTICALLY (before any live write), which
# is the faithful "live update failed" catch path for this service recipe.
NON_OWNED_ID = "a0X000000000000AAA"

# workato_service.receive_request 'Update Campaign Activity' (as d42d4f2a):
# request carries sfdc_campaign_activity_id (required) + 27 optional fields.
#   TRY (2):
#     3 salesforce.update_sobject 8753d35d (LIVE) Campaign_Activity__c,
#       id = request.sfdc_campaign_activity_id; every one of the 27 field
#       writes sits behind a per-field formula guard - 21 x
#       `present?? _(...) : skip` + 6 x `.presence or skip` (SDR_Notes__c and
#       the five UTM_*__c). A guard that evaluates SKIP drops the column from
#       the live update entirely (fields never carry the sentinel).
#     4 workato_service.send_reply 18f926a3 reply_type 'success',
#       reply.sfdc_campaign_activity_id echoes the REQUEST id. NOT terminal.
#   CATCH 5 (as 2d7b3539, max_retry_count 0):
#     6 workato_service.send_reply 06138c68 reply_type 'error',
#       message = catch.2d7b3539.message. The failed update never traces, so
#       the catch branch executes exactly ONE action (probe-verified; the
#       triage note claiming 2 was wrong).
#
# Live backend: Campaign_Activity__c custom object ALREADY EXISTS in the org
# with all 27 recipe fields updateable (2026-07-08 tooling+describe probe).
# The seed schema section re-ensures FLS per field on every run
# (ensure_custom_field is idempotent) - it never redeploys the object.
# Workato-internal mock: service trigger + send_reply.
#
# Semantics pinned by variants (all probe-verified on the current tree):
# - present??:skip and `.presence or skip` both SKIP on ''/absent -> the
#   column is dropped before the tool call (blank-vs-missing equivalence).
# - admin_load=true passes through the ternary as a real boolean and writes
#   a boolean to the Admin_Load__c checkbox field.
# - ENGINE/RUBY DIVERGENCE (probe finding): admin_load=false would WRITE
#   False (Ruby `false.present?` is false -> skip). The seeder REJECTS
#   admin_load=false so no variant pins the divergent path.
# - OwnerId is a real reference field: only a live Salesforce id passes
#   _physical_update_fields; variants seed current_user and send
#   $CURRENT_USER_ID. A non-id value diverts into the catch (not exercised;
#   the ownership refusal is the pinned catch path instead).
# - catch message is the deterministic OwnedSalesforce refusal text
#   "refusing to update non-owned Salesforce record <id> for
#   Campaign_Activity__c"; the catch variant still seeds one owned record
#   and proves it survives untouched.

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "workato_service", "name": "receive_request", "as": "d42d4f2a", "skip": false, "input": {"reply_schema_json": "[{\"name\":\"sfdc_campaign_activity_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"}]", "request_schema_json": "[{\"control_type\":\"text\",\"label\":\"Sfdc campaign activity ID\",\"name\":\"sfdc_campaign_activity_id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Sfdc owner ID\",\"name\":\"sfdc_owner_id\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Region\",\"name\":\"region\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Category\",\"name\":\"category\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Fit\",\"name\":\"fit\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Unqualified reasons\",\"name\":\"unqualified_reasons\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Stage\",\"name\":\"stage\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Previous campaign activity\",\"name\":\"previous_campaign_activity\",\"type\":\"string\",\"optional\":true},{\"name\":\"admin_load\",\"type\":\"boolean\",\"optional\":true},{\"name\":\"browser_timezone\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"},{\"name\":\"notes\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"},{\"name\":\"utm_source\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"},{\"name\":\"utm_campaign\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"},{\"name\":\"utm_content\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"},{\"name\":\"utm_medium\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"},{\"name\":\"utm_term\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"},{\"name\":\"outreach_sequence_state_id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"},{\"name\":\"person_country\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"},{\"name\":\"hq_company_country\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"},{\"name\":\"person_sub_region\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"},{\"name\":\"hq_company_sub_region\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"},{\"name\":\"bizible_touchpoint_id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"},{\"name\":\"sdr_notes\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"},{\"name\":\"outreach_sequence_id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"},{\"name\":\"creative_id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"},{\"name\":\"lead_gen_form_id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"},{\"name\":\"campaign_id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"},{\"name\":\"form_type\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Form type\"}]", "service_name": "Update Campaign Activity"}, "block": [{"number": 2, "keyword": "try", "provider": "", "name": "", "as": "", "skip": false, "input": {}, "block": [{"number": 3, "keyword": "action", "provider": "salesforce", "name": "update_sobject", "as": "8753d35d", "skip": false, "input": {"Admin_Load__c": "=_('data.workato_service.d42d4f2a.request.admin_load').present?? _('data.workato_service.d42d4f2a.request.admin_load') : skip", "Bizible_Touchpoint__c": "=_('data.workato_service.d42d4f2a.request.bizible_touchpoint_id').present?? _('data.workato_service.d42d4f2a.request.bizible_touchpoint_id') : skip", "Browser_Timezone__c": "=_('data.workato_service.d42d4f2a.request.browser_timezone').present?? _('data.workato_service.d42d4f2a.request.browser_timezone') : skip", "Campaign_Id__c": "=_('data.workato_service.d42d4f2a.request.campaign_id').present?? _('data.workato_service.d42d4f2a.request.campaign_id') : skip", "Category__c": "=_('data.workato_service.d42d4f2a.request.category').present?? _('data.workato_service.d42d4f2a.request.category') : skip", "Creative_ID__c": "=_('data.workato_service.d42d4f2a.request.creative_id').present?? _('data.workato_service.d42d4f2a.request.creative_id') : skip", "Fit__c": "=_('data.workato_service.d42d4f2a.request.fit').present?? _('data.workato_service.d42d4f2a.request.fit') : skip", "Form_Type__c": "=_('data.workato_service.d42d4f2a.request.form_type').present?? _('data.workato_service.d42d4f2a.request.form_type') : skip", "HQ_Company_Country__c": "=_('data.workato_service.d42d4f2a.request.hq_company_country').present?? _('data.workato_service.d42d4f2a.request.hq_company_country') : skip", "HQ_Company_Sub_Region__c": "=_('data.workato_service.d42d4f2a.request.hq_company_sub_region').present?? _('data.workato_service.d42d4f2a.request.hq_company_sub_region') : skip", "Lead_Gen_Form_ID__c": "=_('data.workato_service.d42d4f2a.request.lead_gen_form_id').present?? _('data.workato_service.d42d4f2a.request.lead_gen_form_id') : skip", "Notes__c": "=_('data.workato_service.d42d4f2a.request.notes').present?? _('data.workato_service.d42d4f2a.request.notes') : skip", "Outreach_Sequence_State_ID__c": "=_('data.workato_service.d42d4f2a.request.outreach_sequence_state_id').present?? _('data.workato_service.d42d4f2a.request.outreach_sequence_state_id') : skip", "OwnerId": "=_('data.workato_service.d42d4f2a.request.sfdc_owner_id').present?? _('data.workato_service.d42d4f2a.request.sfdc_owner_id') : skip", "Person_Country__c": "=_('data.workato_service.d42d4f2a.request.person_country').present?? _('data.workato_service.d42d4f2a.request.person_country') : skip", "Person_Sub_Region__c": "=_('data.workato_service.d42d4f2a.request.person_sub_region').present?? _('data.workato_service.d42d4f2a.request.person_sub_region') : skip", "Previous_Campaign_Activity__c": "=_('data.workato_service.d42d4f2a.request.previous_campaign_activity').present?? _('data.workato_service.d42d4f2a.request.previous_campaign_activity') : skip", "Region__c": "=_('data.workato_service.d42d4f2a.request.region').present?? _('data.workato_service.d42d4f2a.request.region') : skip", "SDR_Notes__c": "=_('data.workato_service.d42d4f2a.request.sdr_notes').presence or skip", "Sequence_ID__c": "=_('data.workato_service.d42d4f2a.request.outreach_sequence_id').present?? _('data.workato_service.d42d4f2a.request.outreach_sequence_id') : skip", "Stage__c": "=_('data.workato_service.d42d4f2a.request.stage').present?? _('data.workato_service.d42d4f2a.request.stage') : skip", "UTM_Campaign__c": "=_('data.workato_service.d42d4f2a.request.utm_campaign').presence or skip", "UTM_Content__c": "=_('data.workato_service.d42d4f2a.request.utm_content').presence or skip", "UTM_Medium__c": "=_('data.workato_service.d42d4f2a.request.utm_medium').presence or skip", "UTM_Source__c": "=_('data.workato_service.d42d4f2a.request.utm_source').presence or skip", "UTM_Term__c": "=_('data.workato_service.d42d4f2a.request.utm_term').presence or skip", "Unqualified_Reason__c": "=_('data.workato_service.d42d4f2a.request.unqualified_reasons').present?? _('data.workato_service.d42d4f2a.request.unqualified_reasons') : skip", "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"d42d4f2a\",\"path\":[\"request\", \"sfdc_campaign_activity_id\"]}')}", "sobject_name": "Campaign_Activity__c"}, "block": []}, {"number": 4, "keyword": "action", "provider": "workato_service", "name": "send_reply", "as": "18f926a3", "skip": false, "input": {"reply": {"sfdc_campaign_activity_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"d42d4f2a\",\"path\":[\"request\", \"sfdc_campaign_activity_id\"]}')}"}, "reply_type": "success"}, "block": []}, {"number": 5, "keyword": "catch", "provider": "", "name": "", "as": "2d7b3539", "skip": false, "input": {"max_retry_count": "0", "retry_interval": "2"}, "block": [{"number": 6, "keyword": "action", "provider": "workato_service", "name": "send_reply", "as": "06138c68", "skip": false, "input": {"message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"2d7b3539\",\"path\":[\"message\"]}')}", "reply_type": "error"}, "block": []}]}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

# request key -> (salesforce field, guard kind)
GUARDED_FIELDS: dict[str, tuple[str, str]] = {
    "admin_load": ("Admin_Load__c", "present"),
    "bizible_touchpoint_id": ("Bizible_Touchpoint__c", "present"),
    "browser_timezone": ("Browser_Timezone__c", "present"),
    "campaign_id": ("Campaign_Id__c", "present"),
    "category": ("Category__c", "present"),
    "creative_id": ("Creative_ID__c", "present"),
    "fit": ("Fit__c", "present"),
    "form_type": ("Form_Type__c", "present"),
    "hq_company_country": ("HQ_Company_Country__c", "present"),
    "hq_company_sub_region": ("HQ_Company_Sub_Region__c", "present"),
    "lead_gen_form_id": ("Lead_Gen_Form_ID__c", "present"),
    "notes": ("Notes__c", "present"),
    "outreach_sequence_state_id": ("Outreach_Sequence_State_ID__c", "present"),
    "sfdc_owner_id": ("OwnerId", "present"),
    "person_country": ("Person_Country__c", "present"),
    "person_sub_region": ("Person_Sub_Region__c", "present"),
    "previous_campaign_activity": ("Previous_Campaign_Activity__c", "present"),
    "region": ("Region__c", "present"),
    "sdr_notes": ("SDR_Notes__c", "presence"),
    "outreach_sequence_id": ("Sequence_ID__c", "present"),
    "stage": ("Stage__c", "present"),
    "utm_campaign": ("UTM_Campaign__c", "presence"),
    "utm_content": ("UTM_Content__c", "presence"),
    "utm_medium": ("UTM_Medium__c", "presence"),
    "utm_source": ("UTM_Source__c", "presence"),
    "utm_term": ("UTM_Term__c", "presence"),
    "unqualified_reasons": ("Unqualified_Reason__c", "present"),
}
REQUEST_KEYS = ("sfdc_campaign_activity_id", *GUARDED_FIELDS)
CUSTOM_FIELDS = sorted(
    field for field, _kind in GUARDED_FIELDS.values() if field.endswith("__c")
)
# Pinned schema-in-seed: re-ensure FLS on the 26 custom fields every run
# (OwnerId is standard and never provisioned). sf_types mirror the live org
# probe: Admin_Load__c checkbox, Notes__c textarea, the rest plain text.
SF_SCHEMA: list[dict[str, str]] = [
    {
        "sobject": SOBJECT,
        "field": field,
        "sf_type": (
            "Checkbox" if field == "Admin_Load__c"
            else "TextArea" if field == "Notes__c"
            else "Text"
        ),
    }
    for field in CUSTOM_FIELDS
]

EXPECTED_ACTIONS: list[tuple[int, str, str, str]] = [
    (3, UPDATE_STEP_AS, "salesforce", "update_sobject"),
    (4, SUCCESS_REPLY_AS, "workato_service", "send_reply"),
    (6, ERROR_REPLY_AS, "workato_service", "send_reply"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.update_record",
    "workato_service.send_reply",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.update_record",
    "workato_service.send_reply",
]
REQUIRED_EXPECT_KEYS = (
    "branch",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "updated_fields",
    "absent_fields",
    "reply",
    "untouched_fields",
    "catch_message",
)
BRANCHES = (
    "full_update",
    "sparse_skip",
    "blank_string_skips",
    "admin_load_boolean",
    "catch_error_reply",
)
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_SF_ID_RE = re.compile(r"[a-zA-Z0-9]{15,18}")


def validate_88708198(raw: dict[str, Any]) -> dict[str, Any]:
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
    update = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == UPDATE_STEP_AS), None
    )
    if not isinstance(update, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} update step {UPDATE_STEP_AS} missing")
    update_input = update.get("input") or {}
    if update_input.get("sobject_name") != SOBJECT:
        raise RuntimeError(f"recipe {RECIPE_ID} update sobject changed")
    for request_key, (field, kind) in GUARDED_FIELDS.items():
        formula = str(update_input.get(field) or "")
        path = f"data.workato_service.{TRIGGER_AS}.request.{request_key}"
        if kind == "present":
            expected = f"=_('{path}').present?? _('{path}') : skip"
        else:
            expected = f"=_('{path}').presence or skip"
        if formula != expected:
            raise RuntimeError(
                f"recipe {RECIPE_ID} guard for {field} changed: {formula!r}"
            )
    guarded = set(update_input) - {"id", "sobject_name"}
    if guarded != {field for field, _kind in GUARDED_FIELDS.values()}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} guarded field set changed: {sorted(guarded)}"
        )
    actions = _collect_actions(raw)
    actual = [
        (a.get("number"), str(a.get("as")), str(a.get("provider")), str(a.get("name")))
        for a in actions
    ]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
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


def seed_88708198(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88708198(raw)
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
    branch = expect["branch"]
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} never forces action errors: the catch branch runs on "
            "the deterministic non-owned-record refusal instead"
        )
    _require_branch(branch, request, seed_in, expect)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
    }
    sf_section = seed_in.get("salesforce")
    refs: dict[str, str] = {}
    if sf_section is not None:
        provision = ctx.tools.call(
            "harness.salesforce.seed_records", {"salesforce": deepcopy(sf_section)}
        )
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
        out["salesforce_live"] = deepcopy(provision["state"])
        out["salesforce_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
        refs = _salesforce_ref_tokens(sf_section, provision)
        out["salesforce_ref_tokens"] = dict(refs)
    out["trigger"] = _replace_value(trigger, refs)
    _require_resolved(out["trigger"], "trigger")
    out["expect"] = _replace_value(deepcopy(expect), refs)
    _require_resolved(out["expect"], "expect")
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_88708198(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88708198(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    live = isinstance(seed.get("salesforce_live"), dict)
    if not live:
        raise RuntimeError(
            f"recipe {RECIPE_ID} every variant seeds a live Campaign_Activity__c record "
            "(the catch variant proves it untouched); missing salesforce_live state"
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
        # Required cleanup: the run owns the seeded Campaign_Activity__c
        # record; delete it whether or not the run completed.
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
    result["verifier"] = verify_88708198(result)
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
        raise RuntimeError(
            f"recipe {RECIPE_ID} request carries undeclared fields: {unknown}"
        )
    record_id = request.get("sfdc_campaign_activity_id")
    if not isinstance(record_id, str) or not record_id.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} request.sfdc_campaign_activity_id is required (the update "
            f"target id and the success-reply echo)"
        )
    for key, value in request.items():
        if key == "admin_load":
            if value is not True:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} request.admin_load may only be true: the engine "
                    "passes false through `.present??` (Ruby would skip it), so "
                    f"admin_load=false would pin divergent groundtruth; got {value!r}"
                )
        elif not isinstance(value, str):
            raise RuntimeError(
                f"recipe {RECIPE_ID} request.{key} must be a string "
                f"(explicit '' exercises the blank-skip guards); got {value!r}"
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
    if not isinstance(expect.get("absent_fields"), list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.absent_fields must be a list")
    if not isinstance(expect.get("reply"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.reply must pin the final send_reply args")


def _expected_update_fields(request: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for key, (field, _kind) in GUARDED_FIELDS.items():
        if key not in request:
            continue
        value = request[key]
        if isinstance(value, str) and not value.strip():
            continue  # both guard kinds SKIP blanks (probe-verified)
        fields[field] = value
    return fields


def _require_branch(
    branch: str,
    request: dict[str, Any],
    seed_in: dict[str, Any],
    expect: dict[str, Any],
) -> None:
    if sorted(seed_in.keys()) != ["salesforce"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} every variant seeds exactly the salesforce section "
            f"(the catch variant proves its record untouched); got {sorted(seed_in.keys())}"
        )
    _require_salesforce_section(seed_in["salesforce"], request)
    record_id = str(request.get("sfdc_campaign_activity_id") or "")
    expected_fields = _expected_update_fields(request)
    if branch == "catch_error_reply":
        if record_id != NON_OWNED_ID:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must target the pinned non-owned id "
                f"{NON_OWNED_ID!r} (deterministic refusal message); got {record_id!r}"
            )
        expected_message = (
            f"refusing to update non-owned Salesforce record {NON_OWNED_ID} for {SOBJECT}"
        )
        checks = (
            expect.get("executed_action_count") == 1,
            expect.get("tools") == ["workato_service.send_reply"],
            expect.get("updated_fields") is None,
            expect.get("catch_message") == expected_message,
            expect.get("reply")
            == {"reply_type": "error", "reply": {}, "message": expected_message},
            isinstance(expect.get("untouched_fields"), dict) and expect["untouched_fields"],
        )
        if not all(checks):
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch expect block is inconsistent (1 action, error "
                f"reply carrying the exact refusal text, null updated_fields, seeded "
                f"record pinned untouched): {expect!r}"
            )
        return
    if record_id != "$CA_ID":
        raise RuntimeError(
            f"recipe {RECIPE_ID} {branch} variants must target the seeded record via the "
            f"$CA_ID token; got {record_id!r}"
        )
    if not expected_fields:
        raise RuntimeError(
            f"recipe {RECIPE_ID} {branch} would issue an empty live update; give the "
            "request at least one non-blank guarded field"
        )
    checks = (
        expect.get("executed_action_count") == 2,
        expect.get("tools") == ["salesforce.update_record", "workato_service.send_reply"],
        expect.get("updated_fields") == expected_fields,
        expect.get("catch_message") is None,
        expect.get("reply")
        == {"reply_type": "success", "reply": {"sfdc_campaign_activity_id": "$CA_ID"}},
        isinstance(expect.get("untouched_fields"), dict),
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} {branch} expect block is inconsistent with the request "
            f"guards (expected update fields {expected_fields}): {expect!r}"
        )
    expected_absent = sorted(
        {field for field, _kind in GUARDED_FIELDS.values()} - set(expected_fields)
    )
    if sorted(expect.get("absent_fields") or []) != expected_absent:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.absent_fields must pin exactly the skipped "
            f"columns {expected_absent}; got {sorted(expect.get('absent_fields') or [])}"
        )
    if branch == "full_update":
        missing = sorted(set(REQUEST_KEYS) - set(request))
        blanks = [key for key in GUARDED_FIELDS if str(request.get(key) or "") == ""]
        if missing or blanks:
            raise RuntimeError(
                f"recipe {RECIPE_ID} full_update needs every request field non-blank; "
                f"missing {missing}, blank {blanks}"
            )
        if request.get("sfdc_owner_id") != "$CURRENT_USER_ID":
            raise RuntimeError(
                f"recipe {RECIPE_ID} full_update must send sfdc_owner_id as "
                "$CURRENT_USER_ID (OwnerId is a real reference field)"
            )
    elif branch == "sparse_skip":
        if sorted(request) != ["region", "sfdc_campaign_activity_id"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} sparse_skip request must carry exactly the id + "
                f"region (26 guards SKIP); got {sorted(request)}"
            )
    elif branch == "blank_string_skips":
        for key in ("utm_source", "sdr_notes"):
            if request.get(key) != "":
                raise RuntimeError(
                    f"recipe {RECIPE_ID} blank_string_skips must send {key} as the "
                    f"explicit blank string (present-but-blank proves the guard)"
                )
    elif branch == "admin_load_boolean":
        if request.get("admin_load") is not True:
            raise RuntimeError(
                f"recipe {RECIPE_ID} admin_load_boolean requires admin_load: true"
            )
        if expect["updated_fields"].get("Admin_Load__c") is not True:
            raise RuntimeError(
                f"recipe {RECIPE_ID} admin_load_boolean must pin the boolean write"
            )


def _require_salesforce_section(section: Any, request: dict[str, Any]) -> None:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce must be an object")
    allowed = {"schema", "records", "current_user"}
    unknown = sorted(set(section) - allowed)
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce has undeclared keys: {unknown}")
    if section.get("schema") != SF_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must be the pinned 26-field "
            "Campaign_Activity__c schema (re-ensures FLS; never redeploys the object)"
        )
    records = section.get("records")
    if not isinstance(records, list) or len(records) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.records must contain exactly the one "
            "benchmark-owned Campaign_Activity__c record"
        )
    record = records[0]
    if (
        not isinstance(record, dict)
        or record.get("sobject") != SOBJECT
        or str(record.get("ref") or "") != "ca"
        or not isinstance(record.get("fields"), dict)
        or not record["fields"]
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed record must be {{sobject: {SOBJECT}, ref: 'ca', "
            f"fields: <non-empty>}}; got {record!r}"
        )
    unknown_fields = sorted(set(record["fields"]) - set(CUSTOM_FIELDS))
    if unknown_fields:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed record fields must stay on the recipe's custom "
            f"columns; got {unknown_fields}"
        )
    for field, value in record["fields"].items():
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed record field {field} must be a non-empty "
                f"string; got {value!r}"
            )
    current_user = section.get("current_user")
    needs_user = request.get("sfdc_owner_id") == "$CURRENT_USER_ID"
    if needs_user and current_user != {"sobject": "User"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} variants sending sfdc_owner_id need "
            "seed.salesforce.current_user == {'sobject': 'User'}"
        )
    if not needs_user and current_user is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} current_user is only seeded when the request sends "
            "sfdc_owner_id"
        )


def _salesforce_ref_tokens(seed_section: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    records = [record for record in salesforce_snapshot.get("records") or [] if isinstance(record, dict)]
    owned = [record for record in records if not record.get("read_only")]
    read_only_users = [
        record for record in records
        if record.get("read_only") and str(record.get("sobject") or "").lower() == "user"
    ]
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
    if isinstance(seed_section.get("current_user"), dict):
        if len(read_only_users) != 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expected exactly one read-only current-user row; "
                f"got {len(read_only_users)}"
            )
        user_id = str(read_only_users[0].get("id") or "")
        if not _SF_ID_RE.fullmatch(user_id):
            raise RuntimeError(f"recipe {RECIPE_ID} current-user id looks invalid: {user_id!r}")
        refs["$CURRENT_USER_ID"] = user_id
    elif read_only_users:
        raise RuntimeError(f"recipe {RECIPE_ID} unexpected read-only user rows: {read_only_users}")
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
