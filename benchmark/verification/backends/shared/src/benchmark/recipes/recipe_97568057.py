from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_97568057


RECIPE_ID = "97568057"
SEED_TYPE = "clock_intt_exempted_enrolment_publish_variant"
TRACK = "clock_trigger_expired_exemptions_pub_sub"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRACKER_TABLE_ID = "531"
TOPIC_ID = "35836"
# Daily clock trigger (12:30 America/Los_Angeles; payload-less) ->
#   declare_list 'Tracker' (fb73fd30)
#   declare_variable 871e147c {page_token_exempted: nil, limit: 200}
#   REPEAT 1c636317 (do-while pagination):
#     get_records 81da35e7 on table 531 '[INTT] Training Enrolment Tracker'
#       filters [Status eq 'Exempted', Exempted-To-Date lte =today],
#       continuation_token = page_token.presence or SKIP (omitted on page 1),
#       limit = the 871e147c limit pill
#     IF records.size > 0: insert_to_list_batch 870089a3 into Tracker
#       (____source mapping ONLY email/record_id/course_id)
#     update_variables d8fabc64 page_token = continuation_token.presence or
#       clear ('' once the mock serves no token)
#     WHILE continuation_token present -> false on the single mock page
#   FOREACH fa218202 over Tracker.list_items:
#     workato_pub_sub.publish_to_topic f2e91ae8 (topic 35836) message
#       {type 'Exempted', email, record_id, course_id,
#        number_of_reminders: null, last_reminder_sent: null} -- the last two
#       are NEVER inserted into the Tracker list, so the pills resolve null.
# HARD RULE (mock pagination reality): the datatable mock re-serves the FULL
# seeded row set on every get_records call, so ONLY single-page variants are
# faithful -- variants must never seed continuation_tokens (a seeded token
# would re-insert the same rows on iteration 2 and double-publish).
# All backends are Workato-internal (datatable / pub-sub / variables) ->
# fully mockable per the backend policy; per-variant isolated state.
EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("workato_variable", "declare_list", "fb73fd30"),
    ("workato_variable", "declare_variable", "871e147c"),
    ("workato_db_table", "get_records", "81da35e7"),
    ("workato_variable", "insert_to_list_batch", "870089a3"),
    ("workato_variable", "update_variables", "d8fabc64"),
    ("workato_pub_sub", "publish_to_topic", "f2e91ae8"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_list",
    "workato_runtime.declare_variable",
    "workato_db_table.get_records",
    "workato_runtime.insert_to_list_batch",
    "workato_runtime.update_variables",
    "workato_pub_sub.publish_to_topic",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_pub_sub.publish_to_topic",
]
STATUS_FILTER = {
    "field_id": "bc4dccae-9c53-472e-a321-491a9982ddbb",
    "op_default": "eq",
    "value_default": "Exempted",
}
DATE_FILTER = {
    "field_id": "50e36191-795d-4265-bd93-d9dc2a7842e4",
    "op_date": "lte",
    "value_date": "=today",
}
CONTINUATION_FORMULA = (
    "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"871e147c\","
    "\"path\":[\"page_token_exempted\"]}').presence or skip"
)
LIMIT_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"871e147c\","
    "\"path\":[\"limit\"]}')}"
)
PAGE_TOKEN_UPDATE_FORMULA = (
    "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"81da35e7\","
    "\"path\":[\"continuation_token\"]}').presence or clear"
)
INSERT_MAPPING = {
    "____source": (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"81da35e7\","
        "\"path\":[\"records\"]}')}"
    ),
    "course_id": (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"81da35e7\","
        "\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"0687d8fc_75c3_402e_bfb5_8343057213de\"]}')}"
    ),
    "email": (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"81da35e7\","
        "\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"724ce614_876b_4775_b110_ca6cc4a252ea\"]}')}"
    ),
    "record_id": (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"81da35e7\","
        "\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\"]}')}"
    ),
}
PUBLISH_MESSAGE = {
    "course_id": (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"fa218202\","
        "\"path\":[\"course_id\"]}')}"
    ),
    "email": (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"fa218202\","
        "\"path\":[\"email\"]}')}"
    ),
    "last_reminder_sent": (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"fa218202\","
        "\"path\":[\"last_reminder_sent\"]}')}"
    ),
    "number_of_reminders": (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"fa218202\","
        "\"path\":[\"number_of_reminders\"]}')}"
    ),
    "record_id": (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"fa218202\","
        "\"path\":[\"record_id\"]}')}"
    ),
    "type": "Exempted",
}
FOREACH_SOURCE = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"fb73fd30\","
    "\"path\":[\"list_items\"]}')}"
)
WHILE_TOKEN_LHS = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"81da35e7\","
    "\"path\":[\"continuation_token\"]}')}"
)
SIZE_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"81da35e7\","
    "\"path\":[\"records\", {\"path_element_type\": \"size\"}]}')}"
)


def validate_97568057(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    trigger_in = raw.get("input") or {}
    if (
        str(trigger_in.get("trigger_at") or "") != "12:30:00"
        or str(trigger_in.get("timezone") or "") != "America/Los_Angeles"
        or str(trigger_in.get("trigger_every") or "") != "1"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger schedule changed: {trigger_in}")
    actions = _collect_keyword(raw, "action")
    actual = [(a.get("provider"), a.get("name"), a.get("as")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    declare_variable = _input(actions[1])
    if ((declare_variable.get("variables") or {}).get("data") or {}) != {"limit": "200"}:
        raise RuntimeError(f"recipe {RECIPE_ID} pagination variable defaults changed")
    get_input = _input(actions[2])
    if (
        str(get_input.get("table_id") or "") != TRACKER_TABLE_ID
        or get_input.get("filters") != [STATUS_FILTER, DATE_FILTER]
        or get_input.get("continuation_token") != CONTINUATION_FORMULA
        or get_input.get("limit") != LIMIT_PILL
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} get_records changed: {get_input}")
    insert_input = _input(actions[3])
    if insert_input.get("list_items") != INSERT_MAPPING or not str(
        insert_input.get("name") or ""
    ).endswith(":fb73fd30"):
        raise RuntimeError(f"recipe {RECIPE_ID} insert_to_list_batch changed: {insert_input}")
    update_input = _input(actions[4])
    if update_input.get("page_token_exempted") != PAGE_TOKEN_UPDATE_FORMULA or not str(
        update_input.get("name") or ""
    ).endswith(":871e147c:page_token_exempted"):
        raise RuntimeError(f"recipe {RECIPE_ID} page-token update changed: {update_input}")
    publish_input = _input(actions[5])
    if str(publish_input.get("topic_id") or "") != TOPIC_ID or publish_input.get("message") != PUBLISH_MESSAGE:
        raise RuntimeError(f"recipe {RECIPE_ID} publish_to_topic changed: {publish_input}")
    ifs = _collect_keyword(raw, "if")
    if len(ifs) != 1 or ifs[0].get("number") != 6:
        raise RuntimeError(f"recipe {RECIPE_ID} IF steps changed")
    conditions = _input(ifs[0]).get("conditions")
    if (
        not isinstance(conditions, list)
        or len(conditions) != 1
        or conditions[0].get("lhs") != SIZE_PILL
        or conditions[0].get("operand") != "greater_than"
        or conditions[0].get("rhs") != "0"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} IF condition changed: {conditions}")
    repeats = _collect_keyword(raw, "repeat")
    if len(repeats) != 1 or repeats[0].get("as") != "1c636317":
        raise RuntimeError(f"recipe {RECIPE_ID} repeat block changed")
    whiles = _collect_keyword(raw, "while_condition")
    if len(whiles) != 1:
        raise RuntimeError(f"recipe {RECIPE_ID} while_condition changed")
    while_conditions = _input(whiles[0]).get("conditions")
    if (
        not isinstance(while_conditions, list)
        or len(while_conditions) != 1
        or while_conditions[0].get("lhs") != WHILE_TOKEN_LHS
        or while_conditions[0].get("operand") != "present"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} while condition changed: {while_conditions}")
    foreachs = _collect_keyword(raw, "foreach")
    if (
        len(foreachs) != 1
        or foreachs[0].get("as") != "fa218202"
        or foreachs[0].get("repeat_mode") != "simple"
        or _input(foreachs[0]).get("source") != FOREACH_SOURCE
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} foreach changed")
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


def seed_97568057(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_97568057(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} clock trigger is payload-less; trigger_input must be exactly {{}}"
        )
    if data.get("now") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} requires fixed variant now for the '=today' filter")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or not isinstance(seed_in.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.workato_db_table")
    tables = seed_in["workato_db_table"].get("tables")
    if not isinstance(tables, dict) or not isinstance(tables.get(TRACKER_TABLE_ID), list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must define workato_db_table.tables[{TRACKER_TABLE_ID!r}] explicitly"
        )
    if seed_in["workato_db_table"].get("continuation_tokens"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} must stay single-page: the mock re-serves the full row set per "
            "page, so seeded continuation_tokens would double-insert (see recipe module note)"
        )
    expect = data.get("expect")
    if not isinstance(expect, dict) or not isinstance(expect.get("published_messages"), list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} every variant must declare expect.published_messages (may be empty)"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "expect": deepcopy(expect),
        "raw_validation": validation,
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "now": data["now"],
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_97568057(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_97568057(raw)
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = _snapshot(ctx, seed)
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
    result["verifier"] = verify_97568057(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _collect_keyword(node: dict[str, Any], keyword: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == keyword and not child.get("skip"):
            found.append(child)
        found.extend(_collect_keyword(child, keyword))
    return found


def _input(node: dict[str, Any]) -> dict[str, Any]:
    value = node.get("input")
    return value if isinstance(value, dict) else {}


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("workato_db_table"), dict):
        out.update(ctx.tools.call("harness.workato_db_table.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
