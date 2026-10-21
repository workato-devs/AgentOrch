from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_88451624


RECIPE_ID = "88451624"
SEED_TYPE = "salesforce_skilljar_student_platform_event_link_variant"
TRACK = "live_salesforce_skilljar_student_link"
TRIGGER_PROVIDER = "salesforce"
TRIGGER_NAME = "new_platform_event"
# Salesforce platform event New_Updated_Skilljar_Student__e (as dd6906dc;
# dereferences Student_Id__c only) -> TRY:
#   #3 search_sobjects skilljar__Student__c by Id (as dc656cf3, limit 150,
#      field_list Email/First/Last/Domain/Id)
#   #4 workato_service.call_service flow 45071427 'Check Record In Salesforce
#      v2.5' (as e5696ea1) with {company: Domain__c, email, first_name,
#      last_name, create_section {create_record 'Lead', lead_source
#      'Automation Institute'}} — the sub-recipe is NOT executed; its reply is
#      deterministic Workato-internal seed state (seed.workato_service_replies
#      keyed by 'e5696ea1').
#   IF#5 reply.salesforce_id present:
#     IF#6 reply.object == 'Lead' -> #7 update skilljar__Student__c set
#       skilljar__Lead__c = reply.salesforce_id
#     ELSE#8 ('Contact') -> #9 update set skilljar__Contact__c = reply id
# CATCH#10 (as 12cae2c6, max_retry 0) > IF#11 catch message not_contains '404'
#   -> STOP#12 (as 51c78897, stop_with_error=true, reason = catch message);
#   a message containing '404' falls through silently (catch completes clean).
#
# Backend: Salesforce LIVE. skilljar__Student__c is a managed-package object
# routed to the benchmark-owned Student__c stand-in (mdapi deployed 2026-07-07,
# commit 948d5ede) via SALESFORCE_SOBJECT_MAP; the skilljar__ field names map
# via SALESFORCE_FIELD_MAP (Email__c/First_Name__c/Last_Name__c/Lead__c/
# Contact__c; Domain__c is physical on both sides). skilljar__Lead__c /
# skilljar__Contact__c are Lookup(Lead)/Lookup(Contact) reference fields, so
# the seeded call_service reply threads the LIVE id of a seeded companion
# Lead/Contact record ($LEAD_ID / $CONTACT_ID); the trigger Student_Id__c
# carries the seeded Student record's live id ($STUDENT_ID).
# Cleanup: every seeded record is benchmark-owned and deleted after the final
# snapshot (fail-fast on leftovers).
STUDENT_SOBJECT = "skilljar__Student__c"
FLOW_ID = "45071427"
CATCH_AS = "12cae2c6"
STOP_AS = "51c78897"
SEARCH_AS = "dc656cf3"
CALL_AS = "e5696ea1"
STUDENT_TOKEN = "$STUDENT_ID"
LEAD_TOKEN = "$LEAD_ID"
CONTACT_TOKEN = "$CONTACT_ID"
_REF_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*_ID")

FIELD_LIST = "skilljar__Email__c\nskilljar__First_Name__c\nskilljar__Last_Name__c\nDomain__c\nId"

# --- verbatim datapill templates (spacing/quoting exactly as in the raw JSON) ---

TRIGGER_ID_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\","
    "\"line\":\"dd6906dc\",\"path\":[\"Student_Id__c\"]}')}"
)


def _student_ci_pill(field: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"dc656cf3\","
        "\"path\":[\"skilljar__Student__c\", {\"path_element_type\": \"current_item\"}, \"%s\"]}')}"
        % field
    )


def _reply_pill(field: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"e5696ea1\","
        "\"path\":[\"reply\", \"%s\"]}')}" % field
    )


CATCH_MESSAGE_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"12cae2c6\","
    "\"path\":[\"message\"]}')}"
)


def _compound(conditions: list[dict[str, str]]) -> dict[str, Any]:
    return {"conditions": conditions, "operand": "and", "type": "compound"}


def _cond(lhs: str, operand: str, rhs: str = "") -> dict[str, str]:
    return {"lhs": lhs, "operand": operand, "rhs": rhs}


TRIGGER_INPUT_EXPECTED: dict[str, Any] = {"event_name": "New_Updated_Skilljar_Student__e"}
SEARCH_INPUT_EXPECTED: dict[str, Any] = {
    "Id": TRIGGER_ID_PILL,
    "field_list": FIELD_LIST,
    "limit": "150",
    "sobject_name": STUDENT_SOBJECT,
}
CALL_INPUT_EXPECTED: dict[str, Any] = {
    "flow_id": FLOW_ID,
    "request": {
        "company": _student_ci_pill("Domain__c"),
        "create_section": {
            "create_record": "Lead",
            "lead_source": "Automation Institute",
        },
        "email": _student_ci_pill("skilljar__Email__c"),
        "first_name": _student_ci_pill("skilljar__First_Name__c"),
        "last_name": _student_ci_pill("skilljar__Last_Name__c"),
    },
}
UPDATE_LEAD_INPUT_EXPECTED: dict[str, Any] = {
    "id": _student_ci_pill("Id"),
    "skilljar__Lead__c": _reply_pill("salesforce_id"),
    "sobject_name": STUDENT_SOBJECT,
}
UPDATE_CONTACT_INPUT_EXPECTED: dict[str, Any] = {
    "id": _student_ci_pill("Id"),
    "skilljar__Contact__c": _reply_pill("salesforce_id"),
    "sobject_name": STUDENT_SOBJECT,
}


def _node(depth: int, number: int, keyword: str, provider: str, name: str, as_: str,
          node_input: dict[str, Any]) -> dict[str, Any]:
    return {
        "depth": depth, "number": number, "keyword": keyword, "provider": provider,
        "name": name, "as": as_, "input": node_input,
    }


EXPECTED_NODES: list[dict[str, Any]] = [
    _node(1, 2, "try", "", "", "", {}),
    _node(2, 3, "action", "salesforce", "search_sobjects", SEARCH_AS, SEARCH_INPUT_EXPECTED),
    _node(2, 4, "action", "workato_service", "call_service", CALL_AS, CALL_INPUT_EXPECTED),
    _node(2, 5, "if", "", "", "",
          _compound([_cond(_reply_pill("salesforce_id"), "present")])),
    _node(3, 6, "if", "", "", "",
          _compound([_cond(_reply_pill("object"), "equals_to", "Lead")])),
    _node(4, 7, "action", "salesforce", "update_sobject", "1b810879", UPDATE_LEAD_INPUT_EXPECTED),
    _node(4, 8, "else", "", "", "", {}),
    _node(5, 9, "action", "salesforce", "update_sobject", "4caab51c", UPDATE_CONTACT_INPUT_EXPECTED),
    _node(2, 10, "catch", "", "", CATCH_AS, {"max_retry_count": "0", "retry_interval": "2"}),
    _node(3, 11, "if", "", "", "",
          _compound([_cond(CATCH_MESSAGE_PILL, "not_contains", "404")])),
    _node(4, 12, "stop", "", "", STOP_AS,
          {"stop_reason": CATCH_MESSAGE_PILL, "stop_with_error": "true"}),
]

# Every custom field the recipe (or its seeds) touches on the Student stand-in.
# ensure_custom_field grants FLS on the already-deployed physical fields
# (field names are PHYSICAL; the skilljar__Student__c sobject name maps via
# SALESFORCE_SOBJECT_MAP). Schema is a constant so a variant cannot silently
# drop a grant.
REQUIRED_SCHEMA: list[dict[str, str]] = [
    {"sobject": STUDENT_SOBJECT, "field": "Email__c", "sf_type": "Text"},
    {"sobject": STUDENT_SOBJECT, "field": "First_Name__c", "sf_type": "Text"},
    {"sobject": STUDENT_SOBJECT, "field": "Last_Name__c", "sf_type": "Text"},
    {"sobject": STUDENT_SOBJECT, "field": "Domain__c", "sf_type": "Text"},
    {"sobject": STUDENT_SOBJECT, "field": "Lead__c", "sf_type": "Lookup"},
    {"sobject": STUDENT_SOBJECT, "field": "Contact__c", "sf_type": "Lookup"},
]
STUDENT_SEED_FIELDS = (
    "Name",
    "skilljar__Email__c",
    "skilljar__First_Name__c",
    "skilljar__Last_Name__c",
    "Domain__c",
)
EXPECT_REQUIRED_KEYS = (
    "tools", "tool_expectations", "trace_tools", "executed_action_count",
    "stopped", "sf_update_fields_exact", "final_student", "final_student_id",
)
EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_service.call_service",
    "salesforce.update_record",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_service.call_service",
    "salesforce.update_record",
]


def _walk_nodes(node: dict[str, Any], depth: int = 0) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if depth > 0:
        out.append({
            "depth": depth,
            "number": node.get("number"),
            "keyword": str(node.get("keyword") or ""),
            "provider": str(node.get("provider") or ""),
            "name": str(node.get("name") or ""),
            "as": str(node.get("as") or ""),
            "input": node.get("input") if isinstance(node.get("input"), dict) else {},
        })
        if node.get("skip"):
            raise RuntimeError(f"recipe {RECIPE_ID} step {node.get('number')} is now skipped")
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} raw block contains a non-object node")
        out.extend(_walk_nodes(child, depth + 1))
    return out


def validate_88451624(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != "dd6906dc":
        raise RuntimeError(f"recipe {RECIPE_ID} trigger line id changed: {raw.get('as')}")
    if raw.get("input") != TRIGGER_INPUT_EXPECTED:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input changed: {raw.get('input')}")
    if raw.get("filter") is not None:
        raise RuntimeError(f"recipe {RECIPE_ID} grew a trigger filter: {raw.get('filter')}")
    actual = _walk_nodes(raw)
    if len(actual) != len(EXPECTED_NODES):
        raise RuntimeError(
            f"recipe {RECIPE_ID} node count changed: {len(actual)} != {len(EXPECTED_NODES)}"
        )
    for actual_node, expected_node in zip(actual, EXPECTED_NODES):
        for key in ("depth", "number", "keyword", "provider", "name", "as"):
            if actual_node[key] != expected_node[key]:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} step {actual_node['number']} {key} changed: "
                    f"{actual_node[key]!r} != {expected_node[key]!r}"
                )
        if actual_node["input"] != expected_node["input"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} step {actual_node['number']} input changed:\n"
                f"actual:   {actual_node['input']!r}\n"
                f"expected: {expected_node['input']!r}"
            )
    actions = [node for node in actual if node["keyword"] == "action"]
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": [
            {"number": node["number"], "provider": node["provider"], "name": node["name"], "as": node["as"]}
            for node in actions
        ],
    }


def _require_expect(expect: Any) -> dict[str, Any]:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in EXPECT_REQUIRED_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    if not isinstance(expect.get("stopped"), bool):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.stopped must be an explicit boolean")
    if expect["stopped"] and "stop_step_number" not in expect:
        raise RuntimeError(f"recipe {RECIPE_ID} stopped variants must pin expect.stop_step_number")
    if not isinstance(expect.get("sf_update_fields_exact"), list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.sf_update_fields_exact must be a list")
    if not isinstance(expect.get("final_student"), dict) or not expect["final_student"]:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.final_student must be a non-empty object")
    return expect


def _validate_salesforce_seed(section: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if section.get("schema") != REQUIRED_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare the canonical "
            "REQUIRED_SCHEMA verbatim (FLS grants on every touched Student stand-in field)"
        )
    records = section.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records must be a non-empty list")
    by_ref: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("fields"), dict):
            raise RuntimeError(f"recipe {RECIPE_ID} salesforce seed records must carry fields objects")
        sobject = str(record.get("sobject") or "")
        ref = str(record.get("ref") or "")
        fields = record["fields"]
        if sobject == STUDENT_SOBJECT:
            if ref != "student":
                raise RuntimeError(f"recipe {RECIPE_ID} the Student seed record must use ref 'student'")
            if sorted(fields.keys()) != sorted(STUDENT_SEED_FIELDS):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} Student seed must set exactly {sorted(STUDENT_SEED_FIELDS)}; "
                    f"got {sorted(fields.keys())}"
                )
            blank = [key for key in STUDENT_SEED_FIELDS if not str(fields.get(key) or "").strip()]
            if blank:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} Student seed fields must be non-empty (the recipe reads "
                    f"them into the call_service request): blank {blank}"
                )
        elif sobject == "Lead":
            if ref != "lead":
                raise RuntimeError(f"recipe {RECIPE_ID} the Lead seed record must use ref 'lead'")
            for key in ("LastName", "Company"):
                if not str(fields.get(key) or "").strip():
                    raise RuntimeError(f"recipe {RECIPE_ID} Lead seed requires non-empty {key}")
        elif sobject == "Contact":
            if ref != "contact":
                raise RuntimeError(f"recipe {RECIPE_ID} the Contact seed record must use ref 'contact'")
            if not str(fields.get("LastName") or "").strip():
                raise RuntimeError(f"recipe {RECIPE_ID} Contact seed requires non-empty LastName")
        else:
            raise RuntimeError(f"recipe {RECIPE_ID} unexpected seed sobject {sobject!r}")
        if ref in by_ref:
            raise RuntimeError(f"recipe {RECIPE_ID} duplicate seed ref {ref!r}")
        by_ref[ref] = record
    if "student" not in by_ref:
        raise RuntimeError(f"recipe {RECIPE_ID} seed must create exactly one Student record (ref 'student')")
    return by_ref


def _validate_reply_branch(
    data: dict[str, Any],
    by_ref: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    """Cross-check the seeded call_service reply against the seeded companion
    records so a reference-field update can only ever carry a benchmark-owned
    live id. Returns the reply template (with $REF tokens) or None when the
    forced-error variant never reaches the call_service step."""
    force = data.get("force_action_error")
    replies = (data.get("seed") or {}).get("workato_service_replies")
    if isinstance(force, dict):
        if str(force.get("step_as") or "") != SEARCH_AS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} force_action_error must target the search step "
                f"{SEARCH_AS!r}; got {force.get('step_as')!r}"
            )
        if not str(force.get("error") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} force_action_error requires an explicit error string")
        if replies is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} forced-error variants never reach call_service — "
                "remove seed.workato_service_replies (no dead seed state)"
            )
        if "lead" in by_ref or "contact" in by_ref:
            raise RuntimeError(
                f"recipe {RECIPE_ID} forced-error variants never link a record — "
                "remove the companion Lead/Contact seed (no dead seed state)"
            )
        return None
    if not isinstance(replies, dict) or sorted(replies.keys()) != [CALL_AS]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires seed.workato_service_replies keyed exactly "
            f"by the call_service step id {CALL_AS!r}"
        )
    reply = replies[CALL_AS]
    if not isinstance(reply, dict) or "salesforce_id" not in reply or "object" not in reply:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the seeded reply must declare explicit "
            f"'salesforce_id' and 'object' (IF#5/IF#6 read them): {reply!r}"
        )
    salesforce_id = str(reply.get("salesforce_id") or "")
    reply_object = str(reply.get("object") or "")
    if salesforce_id == "":
        if "lead" in by_ref or "contact" in by_ref:
            raise RuntimeError(
                f"recipe {RECIPE_ID} blank-reply variants never link a record — "
                "remove the companion Lead/Contact seed (no dead seed state)"
            )
    elif reply_object == "Lead":
        if salesforce_id != LEAD_TOKEN or "lead" not in by_ref or "contact" in by_ref:
            raise RuntimeError(
                f"recipe {RECIPE_ID} a 'Lead' reply must thread {LEAD_TOKEN} from a seeded "
                f"companion Lead record (and no Contact): salesforce_id={salesforce_id!r}"
            )
    else:
        if salesforce_id != CONTACT_TOKEN or "contact" not in by_ref or "lead" in by_ref:
            raise RuntimeError(
                f"recipe {RECIPE_ID} a non-'Lead' reply must thread {CONTACT_TOKEN} from a "
                f"seeded companion Contact record (and no Lead): salesforce_id={salesforce_id!r}"
            )
    return deepcopy(replies)


def _ref_ids(section: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    seeded = [record for record in section.get("records") or []]
    snapshot_records = (((provision.get("snapshot") or {}).get("salesforce") or {}).get("records") or [])
    if len(snapshot_records) != len(seeded):
        raise RuntimeError(
            f"recipe {RECIPE_ID} provision snapshot count mismatch: "
            f"{len(snapshot_records)} != {len(seeded)}"
        )
    refs: dict[str, str] = {}
    for record, snap in zip(seeded, snapshot_records):
        if str(snap.get("sobject") or "") != str(record.get("sobject") or ""):
            raise RuntimeError(
                f"recipe {RECIPE_ID} provision snapshot order mismatch: "
                f"{snap.get('sobject')} != {record.get('sobject')}"
            )
        record_id = str(snap.get("id") or "")
        if not record_id:
            raise RuntimeError(f"recipe {RECIPE_ID} provision snapshot record missing id: {snap}")
        refs["$%s_ID" % str(record.get("ref")).upper()] = record_id
    return refs


def _replace_tokens(value: Any, refs: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_tokens(item, refs) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_tokens(item, refs) for item in value]
    if isinstance(value, str):
        out = value
        for token, replacement in refs.items():
            out = out.replace(token, replacement)
        return out
    return value


def _require_no_tokens(value: Any, where: str) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            _require_no_tokens(item, f"{where}.{key}")
    elif isinstance(value, list):
        for idx, item in enumerate(value):
            _require_no_tokens(item, f"{where}[{idx}]")
    elif isinstance(value, str) and _REF_TOKEN_RE.search(value):
        raise RuntimeError(f"recipe {RECIPE_ID} unresolved seed ref token in {where}: {value!r}")


def seed_88451624(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88451624(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if sorted(trigger.keys()) != ["Student_Id__c"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the dereferenced "
            f"Student_Id__c field; got {sorted(trigger.keys())}"
        )
    if trigger.get("Student_Id__c") != STUDENT_TOKEN:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.Student_Id__c must be the {STUDENT_TOKEN} seed "
            "token (the live Student id is only known after provisioning)"
        )
    expect = _require_expect(data.get("expect"))
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or not isinstance(seed_in.get("salesforce"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce")
    by_ref = _validate_salesforce_seed(seed_in["salesforce"])
    replies_template = _validate_reply_branch(data, by_ref)
    provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": seed_in["salesforce"]})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    refs = _ref_ids(seed_in["salesforce"], provision)
    resolved_trigger = _replace_tokens(trigger, refs)
    _require_no_tokens(resolved_trigger, "trigger")
    resolved_expect = _replace_tokens(deepcopy(expect), refs)
    _require_no_tokens(resolved_expect, "expect")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": resolved_trigger,
        "track": data.get("track"),
        "expect": resolved_expect,
        "raw_validation": validation,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": refs,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if replies_template is not None:
        resolved_replies = _replace_tokens(replies_template, refs)
        _require_no_tokens(resolved_replies, "workato_service_replies")
        out["workato_service_replies"] = resolved_replies
    return attach_variant(out, ctx)


def run_88451624(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88451624(raw)
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    if "workato_service_replies" not in seed and not isinstance(seed.get("force_action_error"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed file missing workato_service_replies "
            "(only forced-error variants may omit the seeded reply)"
        )
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    try:
        details["initial_snapshot"] = _snapshot(ctx)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx)
    finally:
        # Snapshot-then-cleanup: verification reads final_snapshot; the owned
        # Salesforce records (Student + companion Lead/Contact) are deleted
        # here and the verifier fails closed on leftovers.
        details["salesforce_cleanup"] = ctx.tools.call("harness.salesforce.cleanup", {})
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_88451624(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


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
