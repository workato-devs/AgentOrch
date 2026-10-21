from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data, variant_index
from ..verifier import verify_121365920
from .salesforce_recipe_utils import replace_tokens


RECIPE_ID = "121365920"
SEED_TYPE = "sf_churn_stage_slack_edit_db_tracking_variant"
TRACK = "live_slack_workato_db_churn_tracking"
TRIGGER_PROVIDER = "salesforce"
TRIGGER_NAME = "new_custom_object"
SOBJECT_NAME = "OpportunityFieldHistory"
# Salesforce OpportunityFieldHistory event (trigger payload only, no live SF
# action; trigger filter: Field == 'StageName' AND OldValue not_contains
# 'Closed' AND NewValue contains 'Closed') -> workato_db_table.get_records
# table 29282 '[FCA] Non Payment Churn Tracking' filtered by Opp ID ->
# IF(records size > 0) { IF(Message ID col present) { IF(Stage contains
# 'Closed Won') try { slack EDIT the previously-posted message via advanced.ts
# ('Churned Recorded, Stage: ...') } catch(0c7240de) { IF(catch message ==
# 'Cant update message') slack threaded post via advanced.thread_ts };
# IF(Stage contains 'Closed Lost') try { slack EDIT 'Resolved' } catch
# (9571f26e) { IF(catch message == 'Cant update message') slack threaded
# 'Resolved' } } ; workato_db_table.update_record stage col = trigger
# Opportunity.StageName }.
#
# Slack runs LIVE. Message-edit variants use a two-phase seed: the seeder
# posts a real message ($SEED_MESSAGE_TS token) and writes its live ts into
# the table-29282 seed row, so chat.update / threaded replies target a real
# ts. The Slack channel is the project_property 'Slack Channel: Non-Payments'
# (seeded explicitly; the executor redirects non-user channels to
# SLACK_CHANNEL_OVERRIDE, so the live post lands in the benchmark channel).
# The account_property 'Salesforce Environment' (title_link URL) is also
# seeded explicitly. Catch branches are reached via seed.force_action_error
# with the recipe's exact 'Cant update message' comparison string (or a
# different string for the swallowed-error path).
TABLE_ID = "29282"
COL_OPP = "7282605a_5019_4d32_9bca_ad22eee221a6"
COL_STAGE = "ce590e2a_eec4_4dc2_bde2_321f102f3b1d"
COL_TS = "6b92357c_3529_4d85_be67_0b6a76b54ab2"
COL_RECORD_ID = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
FILTER_FIELD_ID = "7282605a-5019-4d32-9bca-ad22eee221a6"
PROJECT_PROPERTY = "Slack Channel: Non-Payments"
ACCOUNT_PROPERTY = "Salesforce Environment"
WON_TRY_STEP_AS = "8b29964f"
WON_CATCH_AS = "0c7240de"
LOST_TRY_STEP_AS = "19f51e0d"
LOST_CATCH_AS = "9571f26e"
CATCH_MESSAGE = "Cant update message"
SEED_TS_TOKEN = "$SEED_MESSAGE_TS"


def _trigger_pill(*path: str) -> str:
    rendered = ", ".join('"%s"' % part for part in path)
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\","
        "\"line\":\"2fb5fd5a\",\"path\":[" + rendered + "]}')}"
    )


def _records_pill(field: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\","
        "\"line\":\"866522ca\",\"path\":[\"records\", {\"path_element_type\": "
        "\"current_item\"}, \"" + field + "\"]}')}"
    )


def _catch_pill(line: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\","
        "\"line\":\"" + line + "\",\"path\":[\"message\"]}')}"
    )


CHANNEL_PILL = "#{_dp('{\"pill_type\":\"project_property\",\"property_name\":\"Slack Channel: Non-Payments\"}')}"
TITLE_LINK = (
    "https://#{_dp('{\"pill_type\":\"account_property\",\"property_name\":\"Salesforce Environment\"}')}"
    ".lightning.force.com/lightning/r/Opportunity/"
    + _trigger_pill("OpportunityId")
    + "/view"
)
CHURN_TEXT = "Churned Recorded, Stage: " + _trigger_pill("Opportunity", "StageName")
RESOLVED_TEXT = "Resolved"
RECORDS_SIZE_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\","
    "\"line\":\"866522ca\",\"path\":[\"records\", {\"path_element_type\": \"size\"}]}')}"
)
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_db_table", "get_records"),
    ("slack_bot", "post_bot_message"),
    ("slack_bot", "post_bot_message"),
    ("slack_bot", "post_bot_message"),
    ("slack_bot", "post_bot_message"),
    ("workato_db_table", "update_record"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "slack.post_message",
    "workato_db_table.update_record",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "slack.post_message",
    "workato_db_table.update_record",
]


def validate_121365920(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str((raw.get("input") or {}).get("sobject_name") or "") != SOBJECT_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger sobject changed")
    trigger_filter = raw.get("filter") if isinstance(raw.get("filter"), dict) else {}
    filter_conditions = [
        (str(c.get("lhs") or ""), str(c.get("operand") or ""), str(c.get("rhs") or ""))
        for c in trigger_filter.get("conditions") or []
        if isinstance(c, dict)
    ]
    expected_filter = [
        (_trigger_pill("Field"), "equals_to", "StageName"),
        (_trigger_pill("OldValue"), "not_contains", "Closed"),
        (_trigger_pill("NewValue"), "contains", "Closed"),
    ]
    if filter_conditions != expected_filter or str(trigger_filter.get("operand") or "") != "and":
        raise RuntimeError(f"recipe {RECIPE_ID} trigger filter changed: {filter_conditions}")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    get_input = actions[0].get("input") or {}
    filters = get_input.get("filters") or []
    if (
        str(get_input.get("table_id") or "") != TABLE_ID
        or str(get_input.get("limit") or "") != "1"
        or len(filters) != 1
        or filters[0].get("field_id") != FILTER_FIELD_ID
        or filters[0].get("op_default") != "eq"
        or filters[0].get("value_default") != _trigger_pill("OpportunityId")
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} tracking-row lookup changed: {get_input}")
    posts = {
        1: (WON_TRY_STEP_AS, "ts", CHURN_TEXT),
        2: ("329a3be7", "thread_ts", CHURN_TEXT),
        3: (LOST_TRY_STEP_AS, "ts", RESOLVED_TEXT),
        4: ("5d1ec783", "thread_ts", RESOLVED_TEXT),
    }
    for index, (step_as, advanced_key, text) in posts.items():
        node = actions[index]
        inp = node.get("input") or {}
        advanced = inp.get("advanced") or {}
        if str(node.get("as") or "") != step_as:
            raise RuntimeError(f"recipe {RECIPE_ID} slack step id changed at action {index}")
        if set(advanced) != {advanced_key} or advanced.get(advanced_key) != _records_pill(COL_TS):
            raise RuntimeError(f"recipe {RECIPE_ID} slack advanced.{advanced_key} changed at action {index}")
        if inp.get("channel") != CHANNEL_PILL:
            raise RuntimeError(f"recipe {RECIPE_ID} slack channel pill changed at action {index}")
        if inp.get("text") != text:
            raise RuntimeError(f"recipe {RECIPE_ID} slack text changed at action {index}")
        message = inp.get("message") or {}
        if (
            message.get("color") != "good"
            or message.get("title") != _trigger_pill("Opportunity", "Name")
            or message.get("title_link") != TITLE_LINK
        ):
            raise RuntimeError(f"recipe {RECIPE_ID} slack attachment changed at action {index}")
    update_input = actions[5].get("input") or {}
    if (
        str(update_input.get("table_id") or "") != TABLE_ID
        or update_input.get("record_id") != _records_pill(COL_RECORD_ID)
        or update_input.get("parameters") != {COL_STAGE: _trigger_pill("Opportunity", "StageName")}
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} stage update changed: {update_input}")
    if_conditions = _collect_if_conditions(raw)
    expected_ifs = [
        (RECORDS_SIZE_PILL, "greater_than", "0"),
        (_records_pill(COL_TS), "present", ""),
        (_trigger_pill("Opportunity", "StageName"), "contains", "Closed Won"),
        (_catch_pill(WON_CATCH_AS), "equals_to", CATCH_MESSAGE),
        (_trigger_pill("Opportunity", "StageName"), "contains", "Closed Lost"),
        (_catch_pill(LOST_CATCH_AS), "equals_to", CATCH_MESSAGE),
    ]
    if if_conditions != expected_ifs:
        raise RuntimeError(f"recipe {RECIPE_ID} IF conditions changed: {if_conditions}")
    catches = _collect_catches(raw)
    if [(c.get("as"), str((c.get("input") or {}).get("max_retry_count") or "")) for c in catches] != [
        (WON_CATCH_AS, "0"),
        (LOST_CATCH_AS, "0"),
    ]:
        raise RuntimeError(f"recipe {RECIPE_ID} try/catch structure changed")
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


def seed_121365920(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_121365920(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    for field in ("Field", "OldValue", "NewValue", "OpportunityId"):
        if str(trigger.get(field) or "") == "":
            raise RuntimeError(f"recipe {RECIPE_ID} trigger_input requires {field}")
    opportunity = trigger.get("Opportunity")
    if (
        not isinstance(opportunity, dict)
        or not str(opportunity.get("Name") or "")
        or not str(opportunity.get("StageName") or "")
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input requires Opportunity.Name and Opportunity.StageName")
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    if expect.get("slack_interaction") not in {"edit", "thread", "none"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} every variant must pin expect.slack_interaction (edit|thread|none)"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    project_properties = seed_in.get("project_properties")
    if not isinstance(project_properties, dict) or PROJECT_PROPERTY not in project_properties:
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must seed project_properties[{PROJECT_PROPERTY!r}] "
            "explicitly (project_property pills have no auto channel override)"
        )
    account_properties = seed_in.get("account_properties")
    if not isinstance(account_properties, dict) or ACCOUNT_PROPERTY not in account_properties:
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must seed account_properties[{ACCOUNT_PROPERTY!r}]"
        )
    db_section = seed_in.get("workato_db_table")
    if not isinstance(db_section, dict) or TABLE_ID not in (db_section.get("tables") or {}):
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must seed workato_db_table.tables[{TABLE_ID!r}]"
        )
    db_section = deepcopy(db_section)
    message: dict[str, Any] | None = None
    if _contains_token(db_section, SEED_TS_TOKEN):
        channel = ctx.env.slack_channel_override
        if not channel:
            raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
        idx = variant_index(ctx)
        seed_text = (
            f"benchmark seed for recipe {RECIPE_ID} variant {idx:02d}: "
            "non-payment churn notification pending stage change"
        )
        posted = ctx.tools.call("harness.slack.seed_message", {"channel": channel, "text": seed_text})
        ts = str(posted.get("ts") or "")
        if not ts:
            raise RuntimeError(f"Slack chat.postMessage returned no ts: {posted}")
        actual_channel = str(posted.get("channel") or channel)
        db_section = replace_tokens(db_section, {SEED_TS_TOKEN: ts})
        message = {"channel": actual_channel, "ts": ts, "text": seed_text}
    elif _contains_token(data, SEED_TS_TOKEN):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the {SEED_TS_TOKEN!r} token is only valid inside "
            "seed.workato_db_table (the table row feeds advanced.ts/thread_ts)"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(expect),
        "raw_validation": validation,
        "workato_db_table": db_section,
        "project_properties": deepcopy(project_properties),
        "account_properties": deepcopy(account_properties),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if message is not None:
        out["message"] = message
    return attach_variant(out, ctx)


def run_121365920(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_121365920(raw)
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
    if not isinstance(seed.get("project_properties"), dict) or PROJECT_PROPERTY not in seed["project_properties"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing project_properties[{PROJECT_PROPERTY!r}]")
    if not isinstance(seed.get("account_properties"), dict) or ACCOUNT_PROPERTY not in seed["account_properties"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing account_properties[{ACCOUNT_PROPERTY!r}]")
    expect = seed.get("expect") if isinstance(seed.get("expect"), dict) else {}
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    message = seed.get("message")
    if expect.get("slack_interaction") in {"edit", "thread"}:
        if not isinstance(message, dict) or not str(message.get("ts") or "") or not str(message.get("channel") or ""):
            raise RuntimeError(
                f"recipe {RECIPE_ID} {expect.get('slack_interaction')} variants require a live "
                "seeded Slack message (never fabricate a ts)"
            )
    if isinstance(message, dict):
        details["seed_message"] = {
            "channel": message.get("channel"),
            "ts": message.get("ts"),
            "text": message.get("text"),
        }
    initial_snapshot = ctx.tools.call("harness.workato_db_table.snapshot", {})
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = ctx.tools.call("harness.workato_db_table.snapshot", {})
    details["raw_execution"] = raw_execution
    details["initial_snapshot"] = initial_snapshot
    details["final_snapshot"] = final_snapshot
    details["ground_truth"] = _ground_truth(raw_execution)
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_121365920(result)
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


def _collect_if_conditions(node: dict[str, Any]) -> list[tuple[str, str, str]]:
    found: list[tuple[str, str, str]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "if":
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


def _collect_catches(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "catch":
            found.append(child)
        found.extend(_collect_catches(child))
    return found


def _contains_token(value: Any, token: str) -> bool:
    if isinstance(value, dict):
        return any(_contains_token(item, token) for item in value.values())
    if isinstance(value, list):
        return any(_contains_token(item, token) for item in value)
    return isinstance(value, str) and token in value


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
