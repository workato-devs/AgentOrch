from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data, variant_index
from ..verifier import verify_99910943


RECIPE_ID = "99910943"
SEED_TYPE = "slack_bt_submit_request_update_variant"
TRACK = "live_slack_snowflake_bt_submit"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"
TRIGGER_AS = "efd719ec"
LIVE_MEMBER_EMAIL = "jamie.lee@corp.example"
LIVE_MEMBER_USER_ID = "U0B91BSRGF8"
SEED_TS_TOKEN = "$SEED_MESSAGE_TS"
APP_REQ_LOG_TABLE = "PUBLIC.APP_REQ_LOG"
ACCESS_LOG_TABLE = "PUBLIC.APP_ACCESS_LEVEL_REQ_LOG"
REQUIRED_TABLE_COLUMNS: dict[str, set[str]] = {
    APP_REQ_LOG_TABLE: {
        "id", "beneficiary_id", "requester_id", "app_id",
        "requested_prov_date", "approval_stage", "comments", "last_updated",
    },
    ACCESS_LOG_TABLE: {"id", "app_req_log_id", "comments", "modified_at"},
    "PUBLIC.EMPLOYEE": {"id", "email", "first_name"},
    "PUBLIC.APP": {"id", "name"},
    "PUBLIC.APP_APPROVAL": {"app_id", "approval_stage", "approver_slack_id", "approver_slack_name"},
}
REQUIRED_COLUMN_TYPES: dict[str, dict[str, str]] = {
    APP_REQ_LOG_TABLE: {"comments": "string", "last_updated": "string", "requested_prov_date": "date"},
    ACCESS_LOG_TABLE: {"comments": "string", "modified_at": "string"},
}
REQUIRED_TRIGGER_PARAMETERS = ("request_id", "comments", "orig_conv_id", "orig_message_id")
REQUIRED_TRIGGER_CONTEXT_FIELDS = ("user", "user_name", "channel")
EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("eabdb649", "workato_variable", "declare_variable"),
    ("bbea8657", "slack_bot", "post_bot_message"),
    ("872d3f37", "snowflake", "search_rows_sql"),
    ("831a1bb5", "snowflake", "update_rows"),
    ("0eb21140", "snowflake", "update_rows"),
    ("60e56820", "slack_bot", "get_user_by_email"),
    ("5e0c2427", "slack_bot", "get_user_by_email"),
    ("ba9d7e2b", "workato_variable", "declare_variable"),
    ("5ba5555c", "slack_bot", "post_bot_message"),
    ("191083e2", "slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "slack.post_message",
    "snowflake.search_rows_sql",
    "snowflake.update_rows",
    "slack_bot.get_user_by_email",
]
ALLOWED_TOOLS: list[str] = [
    "slack.post_message",
    "snowflake.search_rows_sql",
    "snowflake.update_rows",
    "slack_bot.get_user_by_email",
]

_RAW_PIN_JSON = r"""{"as": "efd719ec", "block": [{"as": "", "block": [{"as": "eabdb649", "block": [], "input": {"variables": {"data": {"comments_formatted": "=_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"efd719ec\",\"path\":[\"parameters\",\"comments\"]}').strip.gsub(\"\\n\", \"\").gsub(/[\"']/, '\"'=>'', '\\''=>'').gsub(/[\\\\]/, \"\")\n#Remove newlines, backslash, double quotes and single quotes", "conversation_id": "=_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"efd719ec\",\"path\":[\"parameters\",\"orig_conv_id\"]}').presence or _dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"efd719ec\",\"path\":[\"context\",\"channel\"]}')", "message_id": "=_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"efd719ec\",\"path\":[\"parameters\",\"orig_message_id\"]}').presence or _dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"efd719ec\",\"path\":[\"ts\"]}')"}, "schema": "[{\"name\":\"comments_formatted\",\"type\":\"string\",\"optional\":true,\"label\":\"Comments (Formatted)\",\"control_type\":\"text\"},{\"name\":\"conversation_id\",\"type\":\"string\",\"optional\":true,\"label\":\"Conversation ID\",\"control_type\":\"text\"},{\"name\":\"message_id\",\"type\":\"string\",\"optional\":true,\"label\":\"Message ID\",\"control_type\":\"text\"}]"}}, "keyword": "action", "name": "declare_variable", "number": 3, "provider": "workato_variable", "skip": false}, {"as": "bbea8657", "block": [], "input": {"advanced": {"thread_ts": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"eabdb649\",\"path\":[\"message_id\"]}')}"}, "blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": "Processing your message... :firefighter_loading:"}], "channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"eabdb649\",\"path\":[\"conversation_id\"]}')}"}, "keyword": "action", "name": "post_bot_message", "number": 4, "provider": "slack_bot", "skip": false}, {"as": "872d3f37", "block": [], "input": {"limit": "1", "output_schema": "[{\"control_type\":\"text\",\"label\":\"REQUEST ID\",\"name\":\"REQUEST_ID\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"BENE EMAIL\",\"name\":\"BENE_EMAIL\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"REQ EMAIL\",\"name\":\"REQ_EMAIL\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"REQ FIRSTNAME\",\"name\":\"REQ_FIRSTNAME\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"APP\",\"name\":\"APP\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"date\",\"label\":\"REQUESTED PROV DATE\",\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\",\"name\":\"REQUESTED_PROV_DATE\",\"type\":\"date\",\"optional\":false},{\"name\":\"APPROVAL_STAGE\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"APPROVAL STAGE\",\"parse_output\":\"integer_conversion\"},{\"name\":\"APPROVER_SLACK_ID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"APPROVER SLACK ID\"},{\"name\":\"APPROVER_SLACK_NAME\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"APPROVER SLACK NAME\"},{\"name\":\"COMMENTS\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"COMMENTS\"}]", "parameters": {"data": {"request_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"efd719ec\",\"path\":[\"parameters\", \"request_id\"]}')}"}, "schema": "[{\"name\":\"request_id\",\"type\":\"string\",\"optional\":true,\"label\":\"Request ID\",\"control_type\":\"text\"}]"}, "sql": "SELECT\nPR.ID AS REQUEST_ID,\nB.EMAIL AS BENE_EMAIL,\nR.EMAIL AS REQ_EMAIL,\nR.FIRST_NAME AS REQ_FIRSTNAME,\nA.NAME AS APP,\nPR.REQUESTED_PROV_DATE::DATE AS REQUESTED_PROV_DATE,\nPR.APPROVAL_STAGE,\nAA.APPROVER_SLACK_ID,\nAA.APPROVER_SLACK_NAME,\nPR.COMMENTS\n\nFROM APP_REQ_LOG PR\nJOIN EMPLOYEE B\nON PR.BENEFICIARY_ID = B.ID\n\nJOIN EMPLOYEE R\nON PR.REQUESTER_ID = R.ID\n\nJOIN APP A\nON PR.APP_ID = A.ID\n\nLEFT JOIN APP_APPROVAL AA\nON PR.APPROVAL_STAGE = AA.APPROVAL_STAGE\nAND PR.APP_ID = AA.APP_ID\nAND A.ID = AA.APP_ID\n\nWHERE PR.ID = :request_id"}, "keyword": "action", "name": "search_rows_sql", "number": 5, "provider": "snowflake", "skip": false}, {"as": "831a1bb5", "block": [], "input": {"columns": {"comments": "=\"#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"872d3f37\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"comments\"]}')} | #{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"efd719ec\",\"path\":[\"context\",\"user\"]}')}: \" + _dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"efd719ec\",\"path\":[\"parameters\",\"comments\"]}').strip.gsub(/[\"']/, '\"'=>'', '\\''=>\"''\").gsub(/[\\\\]/, \"\")\n#Remove backslash, double quotes and replace single quotes with double single quotes", "last_updated": "=_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_created_at\"]}').in_time_zone(\"Asia/Singapore\").strftime(\"%Y-%m-%d\")"}, "table": "PUBLIC.APP_REQ_LOG", "where": "ID = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"efd719ec\",\"path\":[\"parameters\", \"request_id\"]}')}'"}, "keyword": "action", "name": "update_rows", "number": 6, "provider": "snowflake", "skip": false}, {"as": "0eb21140", "block": [], "input": {"columns": {"comments": "=\"#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"872d3f37\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"comments\"]}')} | #{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"efd719ec\",\"path\":[\"context\",\"user\"]}')}: \" + _dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"efd719ec\",\"path\":[\"parameters\",\"comments\"]}').strip.gsub(/[\"']/, '\"'=>'', '\\''=>\"''\").gsub(/[\\\\]/, \"\")\n#Remove backslash, double quotes and replace single quotes with double single quotes", "modified_at": "=now.in_time_zone(\"Etc/UTC\")"}, "table": "PUBLIC.APP_ACCESS_LEVEL_REQ_LOG", "where": "APP_REQ_LOG_ID = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"efd719ec\",\"path\":[\"parameters\", \"request_id\"]}')}'"}, "keyword": "action", "name": "update_rows", "number": 7, "provider": "snowflake", "skip": false}, {"as": "60e56820", "block": [], "input": {"email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"872d3f37\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"req_email\"]}')}"}, "keyword": "action", "name": "get_user_by_email", "number": 8, "provider": "slack_bot", "skip": false}, {"as": "5e0c2427", "block": [], "input": {"id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"efd719ec\",\"path\":[\"context\", \"user\"]}')}"}, "keyword": "action", "name": "get_user_by_email", "number": 9, "provider": "slack_bot", "skip": false}, {"as": "ba9d7e2b", "block": [], "input": {"variables": {"data": {"request_justification": "=_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"872d3f37\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"comments\"]}').present? ? _dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"872d3f37\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"comments\"]}').split(\" | \").first.gsub(\"Justification: \", \"\") : \"N.A.\""}, "schema": "[{\"name\":\"request_justification\",\"type\":\"string\",\"optional\":true,\"label\":\"Request Justification\",\"control_type\":\"text\"}]"}}, "keyword": "action", "name": "declare_variable", "number": 10, "provider": "workato_variable", "skip": false}, {"as": "5ba5555c", "block": [], "input": {"advanced": {"ts": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"bbea8657\",\"path\":[\"ts\"]}')}"}, "blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": "_#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"eabdb649\",\"path\":[\"comments_formatted\"]}')}_"}], "channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"eabdb649\",\"path\":[\"conversation_id\"]}')}", "message": {"color": "#38e5f5", "footer": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"5e0c2427\",\"path\":[\"real_name\"]}')}", "footer_icon": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"5e0c2427\",\"path\":[\"profile\", \"image_512\"]}')}"}}, "keyword": "action", "name": "post_bot_message", "number": 11, "provider": "slack_bot", "skip": false}, {"as": "191083e2", "block": [], "input": {"attachment_fields": [{"title": "App Beneficiary", "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"872d3f37\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"bene_email\"]}')}"}, {"title": "Requested Provision Date", "value": "=\"`\" + _dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"872d3f37\",\"path\":[\"rows\",{\"path_element_type\":\"current_item\"},\"requested_prov_date\"]}').strftime(\"%A, %d %B %Y\") + \"`\""}, {"title": "Approver", "value": "<slack://channel?team=T02MRTQUB&id=C25BE01TM|BT Team>"}, {"title": "App Name", "value": "`#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"872d3f37\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"app\"]}')}`"}, {"title": "Status", "value": "_Pending Approval_"}, {"title": "Reason for Request", "value": "```#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"ba9d7e2b\",\"path\":[\"request_justification\"]}')}```"}], "blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": "Bringing an update! :firefighter_13:\n<https://workato.slack.com/team/#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"efd719ec\",\"path\":[\"context\", \"user\"]}')}|#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"efd719ec\",\"path\":[\"context\", \"user_name\"]}')}> has a message for you on your recent App Request:"}, {"block_type": "divider", "button_type": "continue_flow"}, {"block_type": "context", "button_type": "continue_flow", "elements": [{"text": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"eabdb649\",\"path\":[\"comments_formatted\"]}')}", "type": "text"}]}, {"block_type": "divider", "button_type": "continue_flow"}], "channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"60e56820\",\"path\":[\"id\"]}')}", "message": {"color": "#B97DF5"}}, "keyword": "action", "name": "post_bot_message", "number": 12, "provider": "slack_bot", "skip": false}, {"as": "077736db", "block": [{"as": "", "block": [], "input": {"stop_reason": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"077736db\",\"path\":[\"message\"]}')}", "stop_with_error": "true"}, "keyword": "stop", "name": "", "number": 14, "provider": "", "skip": false}], "input": {"max_retry_count": "0", "retry_interval": "2"}, "keyword": "catch", "name": "", "number": 13, "provider": "", "skip": false}], "input": {}, "keyword": "try", "name": "", "number": 2, "provider": "", "skip": false}], "input": {"allow_dialog": "false", "description": "Nil", "domain": "firefighter", "hide_from_help": "true", "name": "bt_submit", "parameters": "[\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Request ID\",\n    \"name\": \"request_id\",\n    \"type\": \"string\",\n    \"optional\": false\n  },\n  {\n    \"control_type\": \"text-area\",\n    \"label\": \"Comments\",\n    \"name\": \"comments\",\n    \"type\": \"string\",\n    \"optional\": false,\n    \"hint\": \"Any status updates you wish to inform the requester on this request\"\n  },\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Original Conversation ID\",\n    \"name\": \"orig_conv_id\",\n    \"type\": \"string\",\n    \"optional\": true,\n    \"prompt\": false\n  },\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Original Message ID\",\n    \"name\": \"orig_message_id\",\n    \"type\": \"string\",\n    \"optional\": true,\n    \"prompt\": false\n  }\n]", "scope": "updates"}, "keyword": "trigger", "name": "bot_command_v2", "number": 1, "provider": "slack_bot", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)


def validate_99910943(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    trigger_cfg = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    if (
        str(trigger_cfg.get("domain") or "") != "firefighter"
        or str(trigger_cfg.get("name") or "") != "bt_submit"
        or str(trigger_cfg.get("scope") or "") != "updates"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} bot command identity changed: {trigger_cfg}")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
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


def seed_99910943(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_99910943(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict) or sorted(parameters.keys()) != sorted(REQUIRED_TRIGGER_PARAMETERS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must carry exactly "
            f"{sorted(REQUIRED_TRIGGER_PARAMETERS)}; got "
            f"{sorted(parameters.keys()) if isinstance(parameters, dict) else parameters}"
        )
    for field in ("request_id", "comments"):
        if not isinstance(parameters.get(field), str) or not parameters[field].strip():
            raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter {field!r} must be a non-empty string")
    for field in ("orig_conv_id", "orig_message_id"):
        if not isinstance(parameters.get(field), str):
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger parameter {field!r} must be an explicit string "
                "(seed optional fields as '' when the presence-or fallback branch is intended)"
            )
    context = trigger.get("context")
    if not isinstance(context, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input missing context object")
    for field in REQUIRED_TRIGGER_CONTEXT_FIELDS:
        if not str(context.get(field) or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} trigger context field {field!r} must be a non-empty string")
    if str(context.get("user") or "") != LIVE_MEMBER_USER_ID:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger context.user must be the proven live workspace user id "
            f"{LIVE_MEMBER_USER_ID!r} (step 5e0c2427 calls live users.info on it)"
        )
    if not str(trigger.get("ts") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input requires ts")
    token_slots = [
        field for field in ("orig_message_id", "ts")
        if (parameters.get("orig_message_id") if field == "orig_message_id" else trigger.get("ts")) == SEED_TS_TOKEN
    ]
    if len(token_slots) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} exactly one of trigger parameters.orig_message_id / trigger.ts "
            f"must be the {SEED_TS_TOKEN!r} token: step 4 live-threads via thread_ts = "
            "(orig_message_id.presence or ts), so the anchor must be a real seeded message ts "
            "(never fabricate the ts that gets used)"
        )
    if str(data.get("now") or "").strip() == "":
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must pin top-level now "
            "(modified_at uses now.in_time_zone; never use wall-clock time)"
        )
    job_context = data.get("job_context")
    if not isinstance(job_context, dict) or not str(job_context.get("job_created_at") or ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must pin job_context.job_created_at "
            "(last_updated reads it; never use wall-clock time)"
        )
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    snowflake_seed = seed_in.get("snowflake_live")
    _require_snowflake_tables(snowflake_seed)
    _require_live_requester_email(snowflake_seed, str(parameters.get("request_id")))
    channel = ctx.env.slack_channel_override
    if not channel:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    idx = variant_index(ctx)
    seed_text = (
        f"benchmark seed for recipe {RECIPE_ID} variant {idx:02d}: "
        f"app request {parameters.get('request_id')} conversation anchor"
    )
    posted = ctx.tools.call("harness.slack.seed_message", {"channel": channel, "text": seed_text})
    ts = str(posted.get("ts") or "")
    if not ts:
        raise RuntimeError(f"Slack chat.postMessage returned no ts: {posted}")
    trigger = _replace_token(trigger, SEED_TS_TOKEN, ts)
    expect = _replace_token(deepcopy(expect), SEED_TS_TOKEN, ts)
    message = {"channel": str(posted.get("channel") or channel), "ts": ts, "text": seed_text}
    provision = ctx.tools.call("harness.snowflake_live.seed_tables", {"snowflake": snowflake_seed})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "expect": expect,
        "raw_validation": validation,
        "now": data["now"],
        "job_context": deepcopy(job_context),
        "message": message,
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_99910943(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_99910943(raw)
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live section")
    if str(seed.get("now") or "").strip() == "" or not isinstance(seed.get("job_context"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file must carry pinned now and job_context")
    message = seed.get("message")
    if not isinstance(message, dict) or not str(message.get("ts") or "") or not str(message.get("channel") or ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires a live seeded Slack parent message (seed['message'] with "
            "channel + ts); never fabricate a ts"
        )
    trigger = seed.get("trigger") if isinstance(seed.get("trigger"), dict) else {}
    parameters = trigger.get("parameters") if isinstance(trigger.get("parameters"), dict) else {}
    thread_anchor = str(parameters.get("orig_message_id") or "") or str(trigger.get("ts") or "")
    if thread_anchor != str(message.get("ts") or ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed thread anchor (orig_message_id.presence or ts) does not "
            "match the seeded live message ts"
        )
    initial_snapshot = ctx.tools.call("harness.snowflake.snapshot", {})
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    snowflake_cleanup: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = ctx.tools.call("harness.snowflake.snapshot", {})
    finally:
        snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
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
            "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "seed_message": {
                "channel": message.get("channel"),
                "ts": message.get("ts"),
                "text": message.get("text"),
            },
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "cleanup_response": {"snowflake_live": snowflake_cleanup},
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_99910943(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_snowflake_tables(snowflake_seed: Any) -> None:
    if not isinstance(snowflake_seed, dict) or not isinstance(snowflake_seed.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.snowflake_live.tables")
    tables = snowflake_seed["tables"]
    if sorted(tables.keys()) != sorted(REQUIRED_TABLE_COLUMNS.keys()):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the snowflake tables "
            f"{sorted(REQUIRED_TABLE_COLUMNS)} (exact keys); got {sorted(tables.keys())}"
        )
    for table, required_columns in REQUIRED_TABLE_COLUMNS.items():
        spec = tables.get(table)
        if not isinstance(spec, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} snowflake_live.tables[{table!r}] must be an object")
        columns = spec.get("columns")
        if not isinstance(columns, dict) or not all(
            isinstance(kind, str) and kind.strip() for kind in columns.values()
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} snowflake_live table {table} must declare explicit column types"
            )
        declared = {str(name).strip().lower(): str(kind).strip().lower() for name, kind in columns.items()}
        if set(declared) != required_columns:
            raise RuntimeError(
                f"recipe {RECIPE_ID} snowflake_live table {table} must declare exactly the "
                f"columns {sorted(required_columns)}; got {sorted(declared)}"
            )
        for column, kind in (REQUIRED_COLUMN_TYPES.get(table) or {}).items():
            if declared.get(column) != kind:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} snowflake_live table {table} column {column} must be "
                    f"declared {kind!r} (write/read round-trip fidelity); got {declared.get(column)!r}"
                )
        rows = spec.get("rows")
        if not isinstance(rows, list):
            raise RuntimeError(
                f"recipe {RECIPE_ID} snowflake_live table {table} must declare rows (may be empty)"
            )
        for row in rows:
            if not isinstance(row, dict):
                raise RuntimeError(f"recipe {RECIPE_ID} snowflake_live table {table} rows must be objects")
            extra = {str(key).strip().lower() for key in row} - required_columns
            if extra:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} snowflake_live table {table} row uses undeclared columns: {sorted(extra)}"
                )


def _require_live_requester_email(snowflake_seed: dict[str, Any], request_id: str) -> None:
    """The requester EMPLOYEE row joined for the triggering request feeds a LIVE
    users.lookupByEmail; it must carry the proven benchmark-workspace member
    email or the run would resolve not_found and post to an empty channel."""
    tables = snowflake_seed["tables"]
    request_rows = [
        row for row in (tables[APP_REQ_LOG_TABLE].get("rows") or [])
        if str(_row_field(row, "id")) == request_id
    ]
    if len(request_rows) > 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must not carry duplicate {APP_REQ_LOG_TABLE} rows for {request_id!r}"
        )
    if not request_rows:
        return  # branch without a matching request row (e.g. forced-error variants may omit it)
    requester_id = _row_field(request_rows[0], "requester_id")
    employee_rows = [
        row for row in (tables["PUBLIC.EMPLOYEE"].get("rows") or [])
        if str(_row_field(row, "id")) == str(requester_id)
    ]
    if len(employee_rows) != 1 or str(_row_field(employee_rows[0], "email")) != LIVE_MEMBER_EMAIL:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the requester EMPLOYEE row (id {requester_id!r}) must exist exactly "
            f"once and carry the live workspace member email {LIVE_MEMBER_EMAIL!r}; got {employee_rows}"
        )


def _row_field(row: dict[str, Any], field: str) -> Any:
    for key, value in row.items():
        if str(key).strip().lower() == field:
            return value
    return None


def _replace_token(value: Any, token: str, replacement: str) -> Any:
    if isinstance(value, dict):
        return {key: _replace_token(item, token, replacement) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_token(item, token, replacement) for item in value]
    if isinstance(value, str) and token in value:
        return value.replace(token, replacement)
    return value


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
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
