from __future__ import annotations

from typing import Any

from ..context import RecipeContext
from ..variant_input import trigger_input, variant_data
from ..verifier import verify_90817361
from .snowflake_live_recipe_utils import (
    run_live_snowflake_recipe,
    seed_live_snowflake,
    snowflake_seed_base,
)


RECIPE_ID = "90817361"
SEED_TYPE = "rpa_error_api_snowflake_slack_variant"
TRACK = "live_snowflake_slack_api_rpa_error"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
# API endpoint 'record an RPA job error': receive_request (request.job_id
# required; message/type/value/traceback optional) -> snowflake.search_rows
# RPA.QUEUE where job_id = :job_id (bind parameter) -> IF(rows size == 1)
# { IF(message present) { update QUEUE status='Error: RPA'/status_info=message
# + slack post to #bt-rpa-errors } IF(type present AND message blank) { update QUEUE
# status_info=type\nvalue\ntraceback + slack post } return_response 200 } ->
# snowflake.search_rows RPA.NETSUITE_QUEUE where job_id = :job_id ->
# IF(netsuite size == 1) { same message/type branches against NETSUITE_QUEUE }
# -> return_response 404.
#
# Each branch dereferences the search that guards it. The NETSUITE branch
# therefore updates and reports the matching NETSUITE row instead of reading
# an empty current-item from the earlier QUEUE search.
#
# return_response is TERMINAL in the executor (TERMINAL_TOOLS): the first
# return_response ends the run, so queue-match variants stop at the 200 and
# never reach the NETSUITE search or the trailing 404. Ground truth pins the
# FIRST response (expect.first_response_status), matching Workato
# first-response-wins semantics.
QUEUE_TABLE = "RPA.QUEUE"
NETSUITE_TABLE = "RPA.NETSUITE_QUEUE"
SEARCH_WHERE = "job_id = :job_id"
QUEUE_SEARCH_AS = "86d97b7a"
NETSUITE_SEARCH_AS = "e4806798"


def _request_pill(field: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\","
        "\"line\":\"7076f362\",\"path\":[\"request\", \"" + field + "\"]}')}"
    )


def _row_pill(line: str, field: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\","
        "\"line\":\"" + line + "\",\"path\":[\"rows\", {\"path_element_type\": "
        "\"current_item\"}, \"" + field + "\"]}')}"
    )


def _queue_row_pill(field: str) -> str:
    return _row_pill(QUEUE_SEARCH_AS, field)


def _netsuite_row_pill(field: str) -> str:
    return _row_pill(NETSUITE_SEARCH_AS, field)


def _size_pill(line: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\","
        "\"line\":\"" + line + "\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}"
    )


QUEUE_UPDATE_WHERE = "job_id = '" + _queue_row_pill("job_id") + "'"
NETSUITE_UPDATE_WHERE = "job_id = '" + _netsuite_row_pill("job_id") + "'"
MESSAGE_INFO = _request_pill("message")
TYPE_INFO = _request_pill("type") + "\n" + _request_pill("value") + "\n" + _request_pill("traceback")
SECTION_TEXT = (
    "*RPA ERROR*\n\nAn error occured in an RPA Job.\n*Job ID:* `"
    + _request_pill("job_id")
    + "`"
)
SLACK_CHANNEL = "#bt-rpa-errors"
QUEUE_ATTACHMENT_FIELDS = [
    {"title": "App ID", "value": _queue_row_pill("app_id")},
    {"title": "Action", "value": _queue_row_pill("action")},
    {"title": "User", "value": _queue_row_pill("user_email")},
    {"title": "Ran At", "value": _queue_row_pill("ran_at")},
]
NETSUITE_ATTACHMENT_FIELDS = [
    {"title": "App ID", "value": _netsuite_row_pill("app_id")},
    {"title": "Action", "value": _netsuite_row_pill("action")},
    {"title": "User", "value": _netsuite_row_pill("user_email")},
    {"title": "Ran At", "value": _netsuite_row_pill("ran_at")},
]
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("snowflake", "search_rows"),
    ("snowflake", "update_rows"),
    ("slack_bot", "post_bot_message"),
    ("snowflake", "update_rows"),
    ("slack_bot", "post_bot_message"),
    ("workato_api_platform", "return_response"),
    ("snowflake", "search_rows"),
    ("snowflake", "update_rows"),
    ("slack_bot", "post_bot_message"),
    ("snowflake", "update_rows"),
    ("slack_bot", "post_bot_message"),
    ("workato_api_platform", "return_response"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows",
    "snowflake.update_rows",
    "slack.post_message",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows",
    "snowflake.update_rows",
    "slack.post_message",
    "workato_api_platform.return_response",
]


def validate_90817361(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    request_schema = str(((raw.get("input") or {}).get("request") or {}).get("schema") or "")
    if '"name":"job_id"' not in request_schema or '"optional":false' not in request_schema:
        raise RuntimeError(f"recipe {RECIPE_ID} request schema no longer requires job_id")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    searches = {
        0: (QUEUE_TABLE, QUEUE_SEARCH_AS),
        6: (NETSUITE_TABLE, NETSUITE_SEARCH_AS),
    }
    for index, (table, step_as) in searches.items():
        node = actions[index]
        inp = node.get("input") or {}
        if str(node.get("as") or "") != step_as:
            raise RuntimeError(f"recipe {RECIPE_ID} search step id changed at action {index}")
        if inp.get("table") != table or inp.get("where") != SEARCH_WHERE:
            raise RuntimeError(f"recipe {RECIPE_ID} search {table} table/where changed: {inp}")
        parameters = ((inp.get("parameters") or {}).get("data") or {})
        if parameters.get("job_id") != _request_pill("job_id"):
            raise RuntimeError(f"recipe {RECIPE_ID} search {table} bind parameter changed")
    updates = {
        1: (QUEUE_TABLE, MESSAGE_INFO, QUEUE_UPDATE_WHERE),
        3: (QUEUE_TABLE, TYPE_INFO, QUEUE_UPDATE_WHERE),
        7: (NETSUITE_TABLE, MESSAGE_INFO, NETSUITE_UPDATE_WHERE),
        9: (NETSUITE_TABLE, TYPE_INFO, NETSUITE_UPDATE_WHERE),
    }
    for index, (table, status_info, expected_where) in updates.items():
        inp = actions[index].get("input") or {}
        columns = inp.get("columns") or {}
        if inp.get("table") != table:
            raise RuntimeError(f"recipe {RECIPE_ID} update table changed at action {index}")
        if inp.get("where") != expected_where:
            raise RuntimeError(f"recipe {RECIPE_ID} update where formula changed at action {index}")
        if columns.get("status") != "Error: RPA" or columns.get("status_info") != status_info:
            raise RuntimeError(f"recipe {RECIPE_ID} update columns changed at action {index}")
    posts = {
        2: (MESSAGE_INFO, QUEUE_ATTACHMENT_FIELDS),
        4: (TYPE_INFO, QUEUE_ATTACHMENT_FIELDS),
        8: (MESSAGE_INFO, NETSUITE_ATTACHMENT_FIELDS),
        10: (TYPE_INFO, NETSUITE_ATTACHMENT_FIELDS),
    }
    for index, (attachment_text, expected_fields) in posts.items():
        inp = actions[index].get("input") or {}
        if inp.get("channel") != SLACK_CHANNEL:
            raise RuntimeError(f"recipe {RECIPE_ID} slack channel changed at action {index}")
        blocks = inp.get("blocks") or []
        if (
            len(blocks) != 2
            or blocks[0].get("block_type") != "section_with_text"
            or blocks[0].get("section_text") != SECTION_TEXT
            or blocks[1].get("block_type") != "divider"
        ):
            raise RuntimeError(f"recipe {RECIPE_ID} slack blocks changed at action {index}")
        message = inp.get("message") or {}
        if (
            message.get("title") != "Error Message"
            or message.get("color") != "danger"
            or message.get("attachment_text") != attachment_text
        ):
            raise RuntimeError(f"recipe {RECIPE_ID} slack attachment message changed at action {index}")
        fields = inp.get("attachment_fields") or []
        if fields != expected_fields:
            raise RuntimeError(f"recipe {RECIPE_ID} slack attachment_fields changed at action {index}")
    responses = {5: "200", 11: "404"}
    for index, status in responses.items():
        inp = actions[index].get("input") or {}
        if str(inp.get("http_status_code") or "") != status:
            raise RuntimeError(f"recipe {RECIPE_ID} return_response status changed at action {index}")
    if_conditions = _collect_if_conditions(raw)
    expected_ifs = [
        (_size_pill(QUEUE_SEARCH_AS), "equals_to", "1"),
        (_request_pill("message"), "present", ""),
        (_request_pill("type"), "present", ""),
        (_request_pill("message"), "blank", ""),
        (_size_pill(NETSUITE_SEARCH_AS), "equals_to", "1"),
        (_request_pill("message"), "present", ""),
        (_request_pill("type"), "present", ""),
        (_request_pill("message"), "blank", ""),
    ]
    if if_conditions != expected_ifs:
        raise RuntimeError(f"recipe {RECIPE_ID} IF conditions changed: {if_conditions}")
    keyword_by_number = {
        int(node.get("number")): str(node.get("keyword") or "")
        for node in _walk_nodes(raw)
        if node.get("number") in {4, 7, 13, 16}
    }
    if keyword_by_number != {4: "if", 7: "if", 13: "if", 16: "if"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} message/type branch precedence changed: {keyword_by_number}"
        )
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


def seed_90817361(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_90817361(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    request = trigger.get("request")
    if not isinstance(request, dict) or not str(request.get("job_id") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input requires request.job_id")
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    if str(expect.get("first_response_status") or "") not in {"200", "404"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} every variant must pin expect.first_response_status (200 or 404)"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or not isinstance(seed_in.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.snowflake_live")
    tables = (seed_in["snowflake_live"] or {}).get("tables")
    if not isinstance(tables, dict) or set(tables) != {QUEUE_TABLE, NETSUITE_TABLE}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must define exactly "
            f"{QUEUE_TABLE} and {NETSUITE_TABLE}"
        )
    provision = seed_live_snowflake(RECIPE_ID, data, ctx)
    return snowflake_seed_base(
        recipe_id=RECIPE_ID,
        seed_type=SEED_TYPE,
        track=TRACK,
        validation=validation,
        ctx=ctx,
        snowflake_state=provision["state"],
    )


def run_90817361(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_90817361(raw)
    expect = seed.get("expect") if isinstance(seed.get("expect"), dict) else {}
    if "slack.post_message" in (expect.get("tools") or []) and not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    return run_live_snowflake_recipe(
        recipe_id=RECIPE_ID,
        track=TRACK,
        raw=raw,
        seed=seed,
        ctx=ctx,
        validation=validation,
        expected_raw_tools=EXPECTED_RAW_TOOLS,
        allowed_tools=ALLOWED_TOOLS,
        verifier=verify_90817361,
    )


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _walk_nodes(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        found.append(child)
        found.extend(_walk_nodes(child))
    return found


def _collect_if_conditions(node: dict[str, Any]) -> list[tuple[str, str, str]]:
    found: list[tuple[str, str, str]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") in {"if", "elsif"}:
            for condition in ((child.get("input") or {}).get("conditions") or []):
                if isinstance(condition, dict):
                    found.append(
                        (
                            str(condition.get("lhs") or ""),
                            str(condition.get("operand") or ""),
                            str(condition.get("rhs") or ""),
                        )
                    )
        found.extend(_collect_if_conditions(child))
    return found
