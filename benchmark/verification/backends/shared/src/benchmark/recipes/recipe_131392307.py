from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_131392307


RECIPE_ID = "131392307"
SEED_TYPE = "webhook_event_registration_sheet_upsert_variant"
TRACK = "live_google_sheets_slack_webhook_event_registration"
TRIGGER_PROVIDER = "workato_webhooks"
TRIGGER_NAME = "new_event"
WEBHOOK_SUFFIX = "formfills-apj"
# APJ event-registration form-fill webhook (trigger as a933e72a; payload
# firstname/lastname/email/company/campaign_id/phone/comments/time_zone/
# leadid/sfdcid/joinURL) with a RUNTIME TRIGGER FILTER:
#   payload.campaign_id equals_to job_context.parameters.marketo_id
# (a non-matching campaign_id runs ZERO actions). -> TRY:
#   #3 google_sheets.search_spreadsheet_rows_v4_new (as 4cd73a31) sheet
#      '01 Registration List - Exec Program' by col_Email = payload.email,
#      count 200. The raw spreadsheet id comes from
#      job_context.parameters.event_kit_gsheet_id but the live adapter targets
#      the configured SHEETS_SPREADSHEET_ID/SHEETS_TAB (redirect-inert).
#   #4 workato_service.call_service flow 45178540 'Get Collaboration Tools &
#      Job Title' (as 33035003) request {lead_id: payload.leadid}; the reply
#      is deterministic Workato-internal seed state
#      (seed.workato_service_replies keyed '33035003').
#   IF#5 search rows size != '0' ->
#     #6 update_row_v4_new on the found row_number: 19 col_* values (webhook
#        names, service reply fields, col_Status PASSED THROUGH from the found
#        row's col_Status) — the adapter writes col_-stripped headers, so the
#        live sheet carries the seeded col_* search columns AND the stripped
#        write columns (86735472 precedent).
#   ELSE#7 -> #8 add_spreadsheet_row_v4: same values plus col_Status
#        'Waitlisted' and col_ID = payload.leadid.
#   #9 slack_bot.post_bot_message (as 35a6b894) channel C02FSQ910JH (live
#      override), 2 attachment_buttons (bot_command 66675913 Accept/Reject
#      with leadid+email params — buttons/title_link/color are not part of
#      rendered slack_text), title 'JPN-#{event_date}-Executive Program',
#      6 attachment_fields.
# CATCH#10 (as 36d3b7d0, max_retry_count=3; engine single-shot convention) ->
#   #11 workato_service.call_service flow 45178280 'APJ Recipe Errors' (as
#       50073cae) error_message '(first last - email)#{catch.message}' +
#       job_context job_id/job_url/recipe_id pills, stop_recipe 'false'
#   #12 stop (stop_with_error=true, trace-only stop marker).
#
# TWIN of 131392306 (byte-identical skeleton; diff = bot_command id 66675913
# vs 66973554, button command string literal, slack title suffix 'Executive
# Program' vs 'Women Leadership Luncheon').
#
# KNOWN ENGINE GAP (dry-replay confirmed, blocks the ELSE/add variants at
# output-write time): the add step's sheet_name pill reads search output
# ['sheet'], which the live sheets client does not expose ('tab' instead);
# google_sheets_add_row passes the raw resolve_value result into args, so the
# MISSING sentinel lands in args['sheet'] / the trace and run_recipe's
# json.dumps(result) raises TypeError. Needs the MISSING->None coercion in
# raw_executor.google_sheets_add_row before the add-branch variants can run.
# Expectations here deliberately omit args['sheet'] so they hold once fixed.
SEARCH_AS = "4cd73a31"
CALL_AS = "33035003"
UPDATE_AS = "fb8e9257"
ADD_AS = "98f30966"
SLACK_AS = "35a6b894"
ERROR_CALL_AS = "50073cae"
CATCH_AS = "36d3b7d0"
MAIN_FLOW_ID = "45178540"
ERROR_FLOW_ID = "45178280"
SHEET_NAME_LITERAL = "01 Registration List - Exec Program"
SLACK_CHANNEL_LITERAL = "C02FSQ910JH"
BOT_COMMAND_ID = "66675913"
SLACK_TITLE_SUFFIX = "Executive Program"
CATCH_MAX_RETRY = "3"

COLUMN_HEADERS = (
    "ID\nStatus\nGCal Invite\nFirst Name\nLast Name\nCompany\nEmail\nJob Title\nPhone\n"
    "Country\nCity\nCompany Size\nUTM Campaign\nUTM Source\nUTM Medium\nUTM Content\n"
    "UTM Term\nPartner Referral\nTech Stack\nCollaboration Tool used\nAttended?\nRegion\n"
    "Who should follow up?\nFollow-up actions"
)
REQUIRED_PAYLOAD_FIELDS = (
    "firstname",
    "lastname",
    "email",
    "company",
    "campaign_id",
    "phone",
    "comments",
    "time_zone",
    "leadid",
    "sfdcid",
)
REQUIRED_REPLY_SHAPE: dict[str, tuple[str, ...]] = {
    "Lead": ("job_title", "phone"),
    "Company": ("company", "tools", "tech_stack", "city", "country", "company_size", "region"),
    "MKTO": ("partner_referral", "utm_campaign", "utm_source", "utm_medium", "utm_content", "utm_term"),
}

EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("google_sheets", "search_spreadsheet_rows_v4_new"),
    ("workato_service", "call_service"),
    ("google_sheets", "update_row_v4_new"),
    ("google_sheets", "add_spreadsheet_row_v4"),
    ("slack_bot", "post_bot_message"),
    ("workato_service", "call_service"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "google_sheets.search_spreadsheet_rows_v4_new",
    "workato_service.call_service",
    "google_sheets.update_row_v4_new",
    "google_sheets.add_spreadsheet_row_v4",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "google_sheets.search_spreadsheet_rows_v4_new",
    "workato_service.call_service",
    "google_sheets.update_row_v4_new",
    "google_sheets.add_spreadsheet_row_v4",
    "slack.post_message",
]

# --- verbatim raw pill templates (drift -> RuntimeError) ---


def _payload_pill(field: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_webhooks\",\"line\":\"a933e72a\","
        "\"path\":[\"payload\", \"%s\"]}')}" % field
    )


def _reply_pill(section: str, field: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"33035003\","
        "\"path\":[\"reply\", \"%s\", \"%s\"]}')}" % (section, field)
    )


def _search_pill(path_json: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"4cd73a31\","
        "\"path\":[%s]}')}" % path_json
    )


EVENT_DATE_PILL = "#{_dp('{\"pill_type\":\"job_context\",\"path\":[\"parameters\", \"event_date\"]}')}"
GSHEET_ID_PILL = "#{_dp('{\"pill_type\":\"job_context\",\"path\":[\"parameters\", \"event_kit_gsheet_id\"]}')}"
MARKETO_ID_PILL = "#{_dp('{\"pill_type\":\"job_context\",\"path\":[\"parameters\", \"marketo_id\"]}')}"
CATCH_MESSAGE_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"36d3b7d0\",\"path\":[\"message\"]}')}"
)
ROW_NUMBER_PILL = _search_pill('"rows", {"path_element_type": "current_item"}, "row_number"')
FOUND_STATUS_PILL = _search_pill('"rows", {"path_element_type": "current_item"}, "col_Status"')
SHEET_PILL = _search_pill('"sheet"')
SPREADSHEET_ID_PILL = _search_pill('"spreadsheet_id"')
SLACK_TITLE = "JPN-" + EVENT_DATE_PILL + "-" + SLACK_TITLE_SUFFIX
SLACK_TITLE_LINK = "https://docs.google.com/spreadsheets/d/" + SPREADSHEET_ID_PILL + "/edit#gid=0"
BUTTON_PARAMS_ACCEPT = (
    "operation: Registered leadid: " + _payload_pill("leadid") + " email: " + _payload_pill("email")
)
BUTTON_PARAMS_REJECT = (
    "operation: Rejected leadid: " + _payload_pill("leadid") + " email: " + _payload_pill("email")
)
ATTACHMENT_FIELDS_EXPECTED: list[dict[str, str]] = [
    {"title": "Name", "value": _payload_pill("lastname") + " " + _payload_pill("firstname")},
    {"title": "Email", "value": _payload_pill("email")},
    {"title": "Company Name", "value": _reply_pill("Company", "company")},
    {"title": "Job Title", "value": _reply_pill("Lead", "job_title")},
    {"title": "Phone Number", "value": _reply_pill("Lead", "phone")},
    {"title": "Partner Referral", "value": _reply_pill("MKTO", "partner_referral")},
]
ERROR_MESSAGE_TEMPLATE = (
    "(" + _payload_pill("firstname") + " " + _payload_pill("lastname") + " - "
    + _payload_pill("email") + ")" + CATCH_MESSAGE_PILL
)
# The shared write mapping (update data / add columns): col_* -> pill.
_SHARED_WRITE_PILLS: dict[str, str] = {
    "col_City": _reply_pill("Company", "city"),
    "col_Collaboration Tool used": _reply_pill("Company", "tools"),
    "col_Company": _reply_pill("Company", "company"),
    "col_Company Size": _reply_pill("Company", "company_size"),
    "col_Country": _reply_pill("Company", "country"),
    "col_Email": _payload_pill("email"),
    "col_First Name": _payload_pill("firstname"),
    "col_Job Title": _reply_pill("Lead", "job_title"),
    "col_Last Name": _payload_pill("lastname"),
    "col_Partner Referral": _reply_pill("MKTO", "partner_referral"),
    "col_Phone": _reply_pill("Lead", "phone"),
    "col_Region": _reply_pill("Company", "region"),
    "col_Tech Stack": _reply_pill("Company", "tech_stack"),
    "col_UTM Campaign": _reply_pill("MKTO", "utm_campaign"),
    "col_UTM Content": _reply_pill("MKTO", "utm_content"),
    "col_UTM Medium": _reply_pill("MKTO", "utm_medium"),
    "col_UTM Source": _reply_pill("MKTO", "utm_source"),
    "col_UTM Term": _reply_pill("MKTO", "utm_term"),
}
UPDATE_DATA_EXPECTED = dict(_SHARED_WRITE_PILLS) | {"col_Status": FOUND_STATUS_PILL}
ADD_COLUMNS_EXPECTED = dict(_SHARED_WRITE_PILLS) | {
    "col_Status": "Waitlisted",
    "col_ID": _payload_pill("leadid"),
}
TRIGGER_FILTER_EXPECTED: dict[str, Any] = {
    "conditions": [
        {"lhs": _payload_pill("campaign_id"), "operand": "equals_to", "rhs": MARKETO_ID_PILL}
    ],
    "operand": "and",
    "type": "compound",
}


def validate_131392307(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str((raw.get("input") or {}).get("webhook_suffix") or "") != WEBHOOK_SUFFIX:
        raise RuntimeError(f"recipe {RECIPE_ID} webhook suffix changed")
    if raw.get("filter") != TRIGGER_FILTER_EXPECTED:
        raise RuntimeError(f"recipe {RECIPE_ID} runtime trigger filter changed: {raw.get('filter')}")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    by_as = {str(action.get("as") or ""): action for action in actions}

    search_input = (by_as.get(SEARCH_AS) or {}).get("input") or {}
    if (
        str(search_input.get("sheet_name") or "") != SHEET_NAME_LITERAL
        or str(search_input.get("count") or "") != "200"
        or search_input.get("data") != {"col_Email": _payload_pill("email")}
        or search_input.get("spreadsheet_id") != GSHEET_ID_PILL
        or str(search_input.get("column_headers") or "") != COLUMN_HEADERS
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} search step input changed")

    call_input = (by_as.get(CALL_AS) or {}).get("input") or {}
    if str(call_input.get("flow_id") or "") != MAIN_FLOW_ID or call_input.get("request") != {
        "lead_id": _payload_pill("leadid")
    }:
        raise RuntimeError(f"recipe {RECIPE_ID} call_service step input changed")

    update_input = (by_as.get(UPDATE_AS) or {}).get("input") or {}
    if (
        update_input.get("data") != UPDATE_DATA_EXPECTED
        or update_input.get("row_number") != ROW_NUMBER_PILL
        or update_input.get("sheet_name") != SHEET_PILL
        or update_input.get("spreadsheet_id") != SPREADSHEET_ID_PILL
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} update step input changed")

    add_input = (by_as.get(ADD_AS) or {}).get("input") or {}
    if (
        add_input.get("columns") != ADD_COLUMNS_EXPECTED
        or add_input.get("sheet_name") != SHEET_PILL
        or add_input.get("spreadsheet_id") != SPREADSHEET_ID_PILL
        or str(add_input.get("is_top_left") or "") != "false"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} add step input changed")

    if_node = _find_keyword(raw, "if", 5)
    conditions = (if_node.get("input") or {}).get("conditions") or []
    if (
        len(conditions) != 1
        or conditions[0].get("lhs") != _search_pill('"rows", {"path_element_type": "size"}')
        or conditions[0].get("operand") != "not_equals_to"
        or str(conditions[0].get("rhs") or "") != "0"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} IF#5 rows-size condition changed: {conditions}")

    slack_input = (by_as.get(SLACK_AS) or {}).get("input") or {}
    buttons = slack_input.get("attachment_buttons") or []
    message = slack_input.get("message") or {}
    if (
        str(slack_input.get("channel") or "") != SLACK_CHANNEL_LITERAL
        or len(buttons) != 2
        or buttons[0] != {"bot_command": BOT_COMMAND_ID, "params": BUTTON_PARAMS_ACCEPT, "title": "Accept"}
        or buttons[1] != {"bot_command": BOT_COMMAND_ID, "params": BUTTON_PARAMS_REJECT, "title": "Reject"}
        or slack_input.get("attachment_fields") != ATTACHMENT_FIELDS_EXPECTED
        or str(message.get("title") or "") != SLACK_TITLE
        or str(message.get("title_link") or "") != SLACK_TITLE_LINK
        or str(message.get("color") or "") != "good"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} slack post step input changed")

    error_input = (by_as.get(ERROR_CALL_AS) or {}).get("input") or {}
    if str(error_input.get("flow_id") or "") != ERROR_FLOW_ID or error_input.get("request") != {
        "error_message": ERROR_MESSAGE_TEMPLATE,
        "job_id": "#{_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_id\"]}')}",
        "job_url": "#{_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_url\"]}')}",
        "recipe_id": "#{_dp('{\"pill_type\":\"job_context\",\"path\":[\"recipe_id\"]}')}",
        "stop_recipe": "false",
    }:
        raise RuntimeError(f"recipe {RECIPE_ID} catch call_service step input changed")

    stop_node = _find_keyword(raw, "stop", 12)
    if (stop_node.get("input") or {}) != {"stop_reason": CATCH_MESSAGE_PILL, "stop_with_error": "true"}:
        raise RuntimeError(f"recipe {RECIPE_ID} stop step input changed")
    catch_node = _find_keyword(raw, "catch", 10)
    if (
        str(catch_node.get("as") or "") != CATCH_AS
        or str((catch_node.get("input") or {}).get("max_retry_count") or "") != CATCH_MAX_RETRY
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} catch block changed")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": [
            {
                "number": action.get("number"),
                "provider": action.get("provider"),
                "name": action.get("name"),
                "as": action.get("as"),
            }
            for action in actions
        ],
    }


def _validate_reply(reply: Any) -> None:
    if not isinstance(reply, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seeded call_service reply must be an object")
    for section, fields in REQUIRED_REPLY_SHAPE.items():
        block = reply.get(section)
        if not isinstance(block, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} seeded reply missing section {section!r}")
        for field in fields:
            if field not in block:
                raise RuntimeError(f"recipe {RECIPE_ID} seeded reply missing {section}.{field}")
    unknown = set(reply.keys()) - set(REQUIRED_REPLY_SHAPE.keys())
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} seeded reply carries unread sections (dead seed state): {sorted(unknown)}")


def seed_131392307(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_131392307(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    payload = trigger.get("payload")
    if not isinstance(payload, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input missing payload object")
    for key in REQUIRED_PAYLOAD_FIELDS:
        if key not in payload:
            raise RuntimeError(f"recipe {RECIPE_ID} trigger payload missing required field {key}")
    if "joinURL" not in payload:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger payload must declare joinURL explicitly ('' allowed)")
    job_context = data.get("job_context")
    if not isinstance(job_context, dict) or not isinstance(job_context.get("parameters"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing job_context.parameters")
    jc_parameters = job_context["parameters"]
    for key in ("marketo_id", "event_kit_gsheet_id", "event_date"):
        if not str(jc_parameters.get(key) or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} job_context.parameters.{key} is required")
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect block")
    filter_should_match = str(payload.get("campaign_id")) == str(jc_parameters.get("marketo_id"))
    if expect.get("trigger_filter_matched") is not filter_should_match:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.trigger_filter_matched must be {filter_should_match} "
            "(campaign_id vs job_context.parameters.marketo_id)"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or not isinstance(seed_in.get("sheets"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.sheets")
    headers = seed_in["sheets"].get("headers")
    if not isinstance(headers, list) or "col_Email" not in headers or "col_Status" not in headers:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets.headers must carry the literal searched/read "
            "columns 'col_Email' and 'col_Status'"
        )
    force = data.get("force_action_error")
    replies = seed_in.get("workato_service_replies")
    if isinstance(force, dict):
        if str(force.get("step_as") or "") != SEARCH_AS:
            raise RuntimeError(f"recipe {RECIPE_ID} force_action_error must target the search step {SEARCH_AS!r}")
        if not str(force.get("error") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} force_action_error requires an explicit error string")
        if not filter_should_match:
            raise RuntimeError(f"recipe {RECIPE_ID} a filter-skipped variant never reaches the forced step")
        if not isinstance(replies, dict) or sorted(replies.keys()) != [ERROR_CALL_AS]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} forced-error variants need seed.workato_service_replies keyed "
                f"exactly by the catch call step {ERROR_CALL_AS!r}"
            )
        for key in ("job_id", "job_url", "recipe_id"):
            if not str(job_context.get(key) or "").strip():
                raise RuntimeError(f"recipe {RECIPE_ID} catch variants must pin job_context.{key}")
    elif filter_should_match:
        if not isinstance(replies, dict) or sorted(replies.keys()) != [CALL_AS]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} requires seed.workato_service_replies keyed exactly by the "
                f"call_service step {CALL_AS!r}"
            )
        _validate_reply(replies[CALL_AS])
    elif replies is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} filter-skipped variants never call a service — "
            "remove seed.workato_service_replies (no dead seed state)"
        )
    sheets_seed_response = ctx.tools.call("harness.google_sheets.seed_rows", {"sheets": seed_in["sheets"]})
    if not sheets_seed_response.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Google Sheets seed failed: {sheets_seed_response}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(expect),
        "raw_validation": validation,
        "sheets": deepcopy(seed_in["sheets"]),
        "sheets_seed_response": sheets_seed_response,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if isinstance(replies, dict):
        out["workato_service_replies"] = deepcopy(replies)
    return attach_variant(out, ctx)


def run_131392307(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_131392307(raw)
    if not ctx.env.sheets_spreadsheet_id or not ctx.env.sheets_tab:
        raise RuntimeError("missing SHEETS_SPREADSHEET_ID or SHEETS_TAB for live Google Sheets upsert")
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
            "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_131392307(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _find_keyword(node: dict[str, Any], keyword: str, number: int) -> dict[str, Any]:
    if node.get("keyword") == keyword and node.get("number") == number:
        return node
    for child in node.get("block") or []:
        if isinstance(child, dict):
            found = _find_keyword(child, keyword, number)
            if found:
                return found
    return {}


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return {"google_sheets": ctx.tools.call("harness.google_sheets.snapshot", {})}


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
