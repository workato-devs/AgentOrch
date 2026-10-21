from __future__ import annotations

import json
import re
import time
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_88704851


RECIPE_ID = "88704851"
SEED_TYPE = "workato_service_campaign_history_variant"
TRACK = "live_salesforce_campaign_history_service"
TRIGGER_PROVIDER = "workato_service"
TRIGGER_NAME = "receive_request"
SERVICE_NAME = "Get campaign history"
# Callable service "Get campaign history" (trigger as a3b34dfa; request
# {opportunity_id?, contact_id?, lead_id?} — all optional, all dereferenced):
#   IF (step 2) all three request ids blank -> send_reply error (step 3,
#     220127b3) + graceful STOP (step 4, stop_with_error=false).
#   TRY (step 5):
#     IF (step 6) opportunity_id present -> salesforce.search_sobjects
#       OpportunityContactRole (step 7, a7f4d089; IsPrimary='true',
#       OpportunityId=request pill, field_list ContactId).
#     salesforce.search_sobjects CampaignMember (step 8, eeeeef41;
#       LeadOrContactId = or-chain over OCR.first.ContactId /
#       request.contact_id / request.lead_id; field_list
#       'Campaign$Campaign ID.Name\nCreatedDate\nCampaignId'; table_list
#       Campaign -> each record carries nested Campaign.Name).
#     IF (step 9) CampaignMember size > 0:
#       workato_smart_list.query_list CREATE TABLE campaigns (step 10,
#         76a4de75); FOREACH CampaignMember (step 11, as 29ce44a1):
#         logger.log_message Campaign.Name with single quotes doubled for the
#         SQL literal (step 12, f72e383e), then query_list INSERT INTO campaigns
#         VALUES (CampaignId, logger message, CreatedDate), decoding doubled
#         apostrophes on storage (step 13, 57f474f6);
#       query_list SELECT name, joined FROM campaigns ORDER BY joined ASC
#         (step 14, 9f1ef503).
#     send_reply success (step 15, 09861141; num_campaigns = rows size pill,
#       campaign_history = multi-line if + pluck('name').smart_join(" > "),
#       campaigns = ____source mapping of the SELECT rows). This step runs on
#       the zero-campaign path too, dereferencing the never-executed 9f1ef503:
#       engine ground truth is num_campaigns null / campaign_history null /
#       campaigns [] (probed).
#   CATCH (step 16, cdf7ba50, max_retry_count=0) -> send_reply error with the
#     catch message pill (step 17, d33df715).
#
# Live backend: Salesforce (Campaign / CampaignMember / OpportunityContactRole
# / Contact / Lead / Opportunity seeds; benchmark-owned, deleted in cleanup).
# Workato-internal (deterministic mock): workato_service reply, workato_smart
# list ad-hoc SQL table, logger.
#
# Live-faithfulness notes:
# - CampaignMember.LeadOrContactId is a REAL Salesforce derived column
#   (describe: createable=false, present on every CampaignMember). The generic
#   owned-record read-back only fetches seeded field names + a small derived
#   whitelist, so the seeder pins LeadOrContactId into the owned CampaignMember
#   field_names explicitly — the value is still read back live, never
#   fabricated.
# - CampaignMember.CreatedDate is org-assigned (audit-field create is DISABLED
#   in the benchmark org: describe createable=false). The recipe ORDER BYs on
#   it, so variants needing TWO members with strictly increasing CreatedDate
#   seed the second member in a separate provisioning call after a real pause
#   (seed.salesforce_phase2). Expected `joined` values are therefore live
#   read-backs, asserted as "__ANY__" in expects and cross-checked against the
#   CampaignMember search trace by the verifier.
REQUEST_SCHEMA_JSON = (
    '[{"name":"opportunity_id","type":"string","optional":true,"control_type":"text"},'
    '{"name":"contact_id","type":"string","optional":true,"control_type":"text"},'
    '{"name":"lead_id","type":"string","optional":true,"control_type":"text"}]'
)
REPLY_SCHEMA_JSON = (
    '[{"control_type":"integer","label":"Number of campaigns","parse_output":"integer_conversion",'
    '"name":"num_campaigns","type":"integer","optional":false},'
    '{"control_type":"text","label":"Campaign history","name":"campaign_history","type":"string","optional":false},'
    '{"name":"campaigns","type":"array","of":"object","label":"Campaigns","optional":false,"properties":'
    '[{"control_type":"text","label":"Campaign name","name":"campaign_name","type":"string","optional":false},'
    '{"control_type":"date","label":"Joined","render_input":"date_conversion","parse_output":"date_conversion",'
    '"name":"joined","type":"date_time","optional":false}]}]'
)
REQUEST_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\","
    "\"line\":\"a3b34dfa\",\"path\":[\"request\", \"%s\"]}')}"
)
IF_ALL_BLANK_CONDITIONS: list[dict[str, Any]] = [
    {"lhs": REQUEST_PILL % "opportunity_id", "operand": "blank"},
    {"lhs": REQUEST_PILL % "contact_id", "operand": "blank"},
    {"lhs": REQUEST_PILL % "lead_id", "operand": "blank"},
]
NO_IDS_ERROR_INPUT: dict[str, Any] = {
    "message": "Please provide either an opportunity, contact or lead ID from Salesforce.",
    "reply_type": "error",
}
STOP_INPUT: dict[str, Any] = {"stop_with_error": "false"}
IF_OPP_PRESENT_CONDITIONS: list[dict[str, Any]] = [
    {"lhs": REQUEST_PILL % "opportunity_id", "operand": "present"},
]
OCR_SEARCH_INPUT: dict[str, Any] = {
    "IsPrimary": "true",
    "OpportunityId": REQUEST_PILL % "opportunity_id",
    "field_list": "ContactId",
    "sobject_name": "OpportunityContactRole",
}
CAMPAIGN_MEMBER_SEARCH_INPUT: dict[str, Any] = {
    "LeadOrContactId": (
        "=_('data.salesforce.a7f4d089.OpportunityContactRole.first.ContactId') "
        "or _('data.workato_service.a3b34dfa.request.contact_id') "
        "or _('data.workato_service.a3b34dfa.request.lead_id')"
    ),
    "field_list": "Campaign$Campaign ID.Name\nCreatedDate\nCampaignId",
    "sobject_name": "CampaignMember",
    "table_list": "Campaign",
}
CAMPAIGN_MEMBER_SIZE_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"eeeeef41\","
    "\"path\":[\"CampaignMember\", {\"path_element_type\": \"size\"}]}')}"
)
IF_MEMBERS_CONDITIONS: list[dict[str, Any]] = [
    {"lhs": CAMPAIGN_MEMBER_SIZE_PILL, "operand": "greater_than", "rhs": "0"},
]
FOREACH_SOURCE = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"eeeeef41\","
    "\"path\":[\"CampaignMember\"]}')}"
)
DDL_RESULT_SCHEMA_JSON = '[{"name":"a","type":"string","optional":false,"control_type":"text"}]'
CREATE_TABLE_SQL = (
    "CREATE TABLE campaigns\n(\n  id VARCHAR(18) PRIMARY KEY,\n  name VARCHAR(255),\n  joined DATETIME\n)"
)
LOGGER_QUOTE_ESCAPE_FORMULA = "=_('data.foreach.29ce44a1.Campaign.Name').gsub(/\\'/, \"''\")"
INSERT_SQL = (
    "INSERT INTO campaigns\nVALUES ("
    "'#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"29ce44a1\",\"path\":[\"CampaignId\"]}')}',"
    "'#{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"f72e383e\",\"path\":[\"message\"]}')}',"
    "'#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"29ce44a1\",\"path\":[\"CreatedDate\"]}')}')"
)
SELECT_SQL = "SELECT name, joined\nFROM campaigns\nORDER BY joined ASC"
SELECT_RESULT_SCHEMA_JSON = (
    '[{"name":"name","type":"string","optional":false,"control_type":"text"},'
    '{"name":"joined","type":"date_time","optional":false}]'
)
ROWS_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"9f1ef503\","
    "\"path\":[\"rows\"]}')}"
)
ROWS_ITEM_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"9f1ef503\","
    "\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"%s\"]}')}"
)
SUCCESS_REPLY_INPUT: dict[str, Any] = {
    "reply": {
        "campaign_history": (
            "=if _('data.workato_smart_list.9f1ef503.rows.first.____Size', 'list_meta', "
            "'____Size', 'data.workato_smart_list.9f1ef503.rows') > 0\n"
            "  _('data.workato_smart_list.9f1ef503.rows').pluck('name').smart_join(\" > \")\n"
            "else\n  nil\nend"
        ),
        "campaigns": {
            "____source": ROWS_PILL,
            "campaign_name": ROWS_ITEM_PILL % "name",
            "joined": ROWS_ITEM_PILL % "joined",
        },
        "num_campaigns": (
            "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"9f1ef503\","
            "\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}"
        ),
    },
    "reply_type": "success",
}
CATCH_ERROR_REPLY_INPUT: dict[str, Any] = {
    "message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"cdf7ba50\",\"path\":[\"message\"]}')}",
    "reply_type": "error",
}
CATCH_INPUT: dict[str, Any] = {"max_retry_count": "0", "retry_interval": "2"}
EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("220127b3", "workato_service", "send_reply"),
    ("a7f4d089", "salesforce", "search_sobjects"),
    ("eeeeef41", "salesforce", "search_sobjects"),
    ("76a4de75", "workato_smart_list", "query_list"),
    ("f72e383e", "logger", "log_message"),
    ("57f474f6", "workato_smart_list", "query_list"),
    ("9f1ef503", "workato_smart_list", "query_list"),
    ("09861141", "workato_service", "send_reply"),
    ("d33df715", "workato_service", "send_reply"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_service.send_reply",
    "salesforce.search_records",
    "workato_smart_list.query_list",
    "workato_runtime.log_message",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_service.send_reply",
    "workato_smart_list.query_list",
    "workato_runtime.log_message",
]
# CampaignMember.CreatedDate has whole-second precision; a >1s pause between
# the phase-1 and phase-2 member creates guarantees strictly increasing values.
CREATED_DATE_SPACING_SECONDS = 2.0
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")


def validate_88704851(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    trigger_cfg = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    if str(trigger_cfg.get("service_name") or "") != SERVICE_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger service name changed")
    if str(trigger_cfg.get("request_schema_json") or "") != REQUEST_SCHEMA_JSON:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger request schema changed")
    if str(trigger_cfg.get("reply_schema_json") or "") != REPLY_SCHEMA_JSON:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger reply schema changed")
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    by_as = {str(a.get("as")): a for a in actions}
    _require_input(by_as["220127b3"].get("input"), NO_IDS_ERROR_INPUT, "no-ids error reply")
    _require_input(by_as["a7f4d089"].get("input"), OCR_SEARCH_INPUT, "OCR search")
    _require_input(by_as["eeeeef41"].get("input"), CAMPAIGN_MEMBER_SEARCH_INPUT, "CampaignMember search")
    create_input = by_as["76a4de75"].get("input") if isinstance(by_as["76a4de75"].get("input"), dict) else {}
    if str(create_input.get("sql") or "") != CREATE_TABLE_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} CREATE TABLE sql changed")
    if str(create_input.get("result_schema_json") or "") != DDL_RESULT_SCHEMA_JSON:
        raise RuntimeError(f"recipe {RECIPE_ID} CREATE TABLE result schema changed")
    _require_input(by_as["f72e383e"].get("input"), {"message": LOGGER_QUOTE_ESCAPE_FORMULA}, "logger quote escape")
    insert_input = by_as["57f474f6"].get("input") if isinstance(by_as["57f474f6"].get("input"), dict) else {}
    if str(insert_input.get("sql") or "") != INSERT_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} INSERT sql changed")
    if str(insert_input.get("result_schema_json") or "") != DDL_RESULT_SCHEMA_JSON:
        raise RuntimeError(f"recipe {RECIPE_ID} INSERT result schema changed")
    select_input = by_as["9f1ef503"].get("input") if isinstance(by_as["9f1ef503"].get("input"), dict) else {}
    if str(select_input.get("sql") or "") != SELECT_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} final SELECT sql changed")
    if str(select_input.get("result_schema_json") or "") != SELECT_RESULT_SCHEMA_JSON:
        raise RuntimeError(f"recipe {RECIPE_ID} final SELECT result schema changed")
    _require_input(by_as["09861141"].get("input"), SUCCESS_REPLY_INPUT, "success reply")
    _require_input(by_as["d33df715"].get("input"), CATCH_ERROR_REPLY_INPUT, "catch error reply")
    control = _collect_control_nodes(raw)
    _require_conditions(control["if_2"], "and", IF_ALL_BLANK_CONDITIONS, "no-ids IF")
    _require_input(control["stop_4"].get("input"), STOP_INPUT, "graceful stop")
    _require_conditions(control["if_6"], "and", IF_OPP_PRESENT_CONDITIONS, "opportunity IF")
    _require_conditions(control["if_9"], "and", IF_MEMBERS_CONDITIONS, "members IF")
    foreach = control["foreach_11"]
    if str(foreach.get("as") or "") != "29ce44a1":
        raise RuntimeError(f"recipe {RECIPE_ID} foreach step id changed")
    foreach_input = foreach.get("input") if isinstance(foreach.get("input"), dict) else {}
    if str(foreach_input.get("source") or "") != FOREACH_SOURCE:
        raise RuntimeError(f"recipe {RECIPE_ID} foreach source changed")
    _require_input(control["catch_16"].get("input"), CATCH_INPUT, "catch configuration")
    if str(control["catch_16"].get("as") or "") != "cdf7ba50":
        raise RuntimeError(f"recipe {RECIPE_ID} catch step id changed")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "service_name": SERVICE_NAME,
        "actions": [
            {"number": a.get("number"), "provider": a.get("provider"), "name": a.get("name"), "as": a.get("as")}
            for a in actions
        ],
    }


def seed_88704851(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88704851(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if not isinstance(trigger.get("request"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger input must carry an explicit request object "
            "(empty object for the no-ids branch)"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if not isinstance(data.get("expect"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track"),
        "raw_validation": validation,
    }
    refs: dict[str, str] = {}
    if "salesforce" in seed_in or "salesforce_phase2" in seed_in:
        if not isinstance(seed_in.get("salesforce"), dict):
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed.salesforce_phase2 requires a seed.salesforce phase-1 section"
            )
        state, snapshot, refs = _provision_salesforce(
            ctx,
            seed_in,
            simulated_now=data.get("now"),
        )
        out["salesforce_live"] = state
        out["salesforce_seed_snapshot"] = snapshot
        out["salesforce_ref_tokens"] = dict(refs)
    out["trigger"] = _replace_value(trigger, refs)
    _require_resolved(out["trigger"], "trigger")
    out["expect"] = _replace_value(deepcopy(data["expect"]), refs)
    _require_resolved(out["expect"], "expect")
    for key, value in seed_in.items():
        if isinstance(value, dict):
            out[str(key)] = deepcopy(value)
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    for key in ("force_action_error", "job_context"):
        if isinstance(data.get(key), dict):
            out[key] = deepcopy(data[key])
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_88704851(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88704851(raw)
    initial_snapshot = _snapshot(ctx, seed)
    cleanup_response: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        if isinstance(seed.get("salesforce_live"), dict):
            cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "cleanup_response": cleanup_response,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_88704851(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _provision_salesforce(
    ctx: RecipeContext,
    seed_in: dict[str, Any],
    *,
    simulated_now: Any = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    section = deepcopy(seed_in["salesforce"])
    if simulated_now not in (None, ""):
        # Ignored by the live harness; consumed by the in-process simulator so
        # Salesforce-assigned audit fields are reproducible across gold and
        # later evaluator runs.
        section["_simulated_now"] = simulated_now
    provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": section})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    state = deepcopy(provision["state"])
    snapshot = deepcopy(provision.get("snapshot") or {})
    refs = _salesforce_ref_tokens(section, provision)
    phase2 = seed_in.get("salesforce_phase2")
    if isinstance(phase2, dict):
        # Org-assigned CreatedDate must strictly increase for the recipe's
        # ORDER BY joined ASC ground truth; audit-field create is disabled in
        # the benchmark org, so a real pause is the only faithful spacing.
        time.sleep(CREATED_DATE_SPACING_SECONDS)
        section2 = _replace_value(deepcopy(phase2), refs)
        if simulated_now not in (None, ""):
            section2["_simulated_now"] = simulated_now
        try:
            provision2 = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": section2})
            if not provision2.get("ok"):
                raise RuntimeError(f"recipe {RECIPE_ID} Salesforce phase-2 seed failed: {provision2}")
        except Exception:
            # Phase 2 failed after phase 1 committed live records: remove them
            # before failing so a rerun never sees stale benchmark state.
            from ..salesforce_live_harness import OwnedSalesforce

            OwnedSalesforce(state).delete_owned()
            raise
        state2 = deepcopy(provision2["state"])
        state["owned_records"] = list(state.get("owned_records") or []) + list(
            state2.get("owned_records") or []
        )
        state["read_only_records"] = list(state.get("read_only_records") or []) + list(
            state2.get("read_only_records") or []
        )
        state["expand_relationships"] = bool(
            state.get("expand_relationships") or state2.get("expand_relationships")
        )
        state["strict_soql_conditions"] = bool(
            state.get("strict_soql_conditions") or state2.get("strict_soql_conditions")
        )
        refs.update(_salesforce_ref_tokens(section2, provision2))
        merged_records = list((snapshot.get("salesforce") or {}).get("records") or []) + list(
            ((provision2.get("snapshot") or {}).get("salesforce") or {}).get("records") or []
        )
        snapshot = {"salesforce": {"records": merged_records}}
    # LeadOrContactId is a real derived CampaignMember column the recipe
    # filters on; the generic read-back field set skips it, so pin it into the
    # owned field_names explicitly (the value is read back live every time).
    for row in state.get("owned_records") or []:
        if isinstance(row, dict) and str(row.get("logical_sobject") or "") == "CampaignMember":
            field_names = list(row.get("field_names") or [])
            if "LeadOrContactId" not in field_names:
                field_names.append("LeadOrContactId")
            row["field_names"] = field_names
    return state, snapshot, refs


def _salesforce_ref_tokens(seed_section: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    live_ids = [
        str(record.get("id") or "")
        for record in salesforce_snapshot.get("records") or []
        if isinstance(record, dict) and record.get("id")
    ]
    seed_records = [record for record in seed_section.get("records") or [] if isinstance(record, dict)]
    if len(live_ids) != len(seed_records):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed/snapshot record count mismatch: "
            f"{len(seed_records)} seeded vs {len(live_ids)} provisioned"
        )
    refs: dict[str, str] = {}
    for idx, record in enumerate(seed_records):
        ref = str(record.get("ref") or "").strip()
        if ref:
            refs[f"${ref.upper()}_ID"] = live_ids[idx]
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


def _require_input(actual: Any, expected: dict[str, Any], label: str) -> None:
    if actual != expected:
        raise RuntimeError(f"recipe {RECIPE_ID} {label} input changed: {actual!r}")


def _require_conditions(
    node: dict[str, Any], operand: str, conditions: list[dict[str, Any]], label: str
) -> None:
    node_input = node.get("input") if isinstance(node.get("input"), dict) else {}
    expected = {"conditions": conditions, "operand": operand, "type": "compound"}
    if node_input != expected:
        raise RuntimeError(f"recipe {RECIPE_ID} {label} conditions changed: {node_input!r}")


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _collect_control_nodes(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    control: dict[str, dict[str, Any]] = {}

    def walk(node: dict[str, Any]) -> None:
        for child in node.get("block") or []:
            if not isinstance(child, dict):
                continue
            keyword = str(child.get("keyword") or "")
            if keyword in {"if", "stop", "foreach", "catch", "try"}:
                control[f"{keyword}_{child.get('number')}"] = child
            walk(child)

    walk(raw)
    for key in ("if_2", "stop_4", "try_5", "if_6", "if_9", "foreach_11", "catch_16"):
        if key not in control:
            raise RuntimeError(f"recipe {RECIPE_ID} control-flow node missing: {key}")
    return control


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("salesforce_live"), dict):
        out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
