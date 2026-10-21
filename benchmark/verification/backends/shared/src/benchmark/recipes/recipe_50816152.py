from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_50816152


RECIPE_ID = "50816152"
SEED_TYPE = "officebot_locker_extend_variant"
TRACK = "lookup_table_slack_locker_extend"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"
# 'officebot extend locker_booking' bot command (required parameter entry_id):
# linear flow — lookup_table.update_entry marks booking entry_id as
# col8='Renewed' (LT 1889452 'Lockers Booking', ignore_not_found=false) ->
# lookup_table.search_entries on LT 1889451 'Lockers Database' by
# col1=<booking office col3> to read the office timezone (col8) ->
# logger.log_message used as a date compute: (job_created_at + 1.months)
# .in_time_zone(<timezone pill>).strftime("%B %Y") -> lookup_table.add_entry
# books the next month (col5=<logger message>, col6='Approved',
# col9=job_created_at.strftime("%d/%m/%Y")) -> slack_bot.post_bot_reply_v2
# (replace_original=true, live Slack) confirming the extension.
# Lookup tables are Workato-internal deterministic seeded state; job_context
# must be pinned per variant (both date formulas read job_created_at).
BOOKING_TABLE_ID = "1889452"
DATABASE_TABLE_ID = "1889451"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("lookup_table", "update_entry"),
    ("lookup_table", "search_entries"),
    ("logger", "log_message"),
    ("lookup_table", "add_entry"),
    ("slack_bot", "post_bot_reply_v2"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.update_entry",
    "lookup_table.search_entries",
    "workato_runtime.log_message",
    "lookup_table.add_entry",
    "slack.post_reply",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.update_entry",
    "lookup_table.search_entries",
    "lookup_table.add_entry",
    "slack.post_reply",
]


def validate_50816152(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    trigger_in = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    if (
        trigger_in.get("domain") != "officebot"
        or trigger_in.get("name") != "extend"
        or trigger_in.get("scope") != "locker_booking"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} is not the expected 'officebot extend locker_booking' command")
    actions = _collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    update_in = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if str(update_in.get("lookup_table_id") or "") != BOOKING_TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} update_entry lookup table changed")
    if str(update_in.get("ignore_not_found")) != "false":
        raise RuntimeError(f"recipe {RECIPE_ID} update_entry ignore_not_found changed")
    if (update_in.get("parameters") or {}).get("col8") != "Renewed":
        raise RuntimeError(f"recipe {RECIPE_ID} update_entry no longer marks col8='Renewed'")
    search_in = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    if str(search_in.get("lookup_table_id") or "") != DATABASE_TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} search_entries lookup table changed")
    add_in = actions[3].get("input") if isinstance(actions[3].get("input"), dict) else {}
    if str(add_in.get("lookup_table_id") or "") != BOOKING_TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} add_entry lookup table changed")
    if (add_in.get("parameters") or {}).get("col6") != "Approved":
        raise RuntimeError(f"recipe {RECIPE_ID} add_entry no longer books col6='Approved'")
    reply_in = actions[4].get("input") if isinstance(actions[4].get("input"), dict) else {}
    if str(reply_in.get("replace_original")) != "true":
        raise RuntimeError(f"recipe {RECIPE_ID} bot reply is no longer replace_original=true")
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


def seed_50816152(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_50816152(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict) or not str(parameters.get("entry_id") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} bot command requires parameters.entry_id")
    context = trigger.get("context")
    if not isinstance(context, dict) or not str(context.get("user") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger requires context.user (the reply mentions it)")
    job_context = data.get("job_context")
    if not isinstance(job_context, dict) or job_context.get("job_created_at") in (None, ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires a pinned job_context.job_created_at "
            "(both the +1.months month label and the col9 request date read it)"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    lookup_seed = seed_in.get("lookup_table")
    tables = lookup_seed.get("tables") if isinstance(lookup_seed, dict) else None
    if not isinstance(tables, dict) or BOOKING_TABLE_ID not in tables or DATABASE_TABLE_ID not in tables:
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires seed.lookup_table.tables for both "
            f"{BOOKING_TABLE_ID!r} (Lockers Booking) and {DATABASE_TABLE_ID!r} (Lockers Database)"
        )
    entry_id = str(parameters.get("entry_id"))
    booking_row = next(
        (
            row
            for row in tables.get(BOOKING_TABLE_ID) or []
            if isinstance(row, dict) and str(row.get("id")) == entry_id
        ),
        None,
    )
    if booking_row is None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seeded Lockers Booking table has no entry with id {entry_id!r}; "
            "update_entry (ignore_not_found=false) requires the booking row"
        )
    office = str(booking_row.get("col3") or "")
    timezone_row = next(
        (
            row
            for row in tables.get(DATABASE_TABLE_ID) or []
            if isinstance(row, dict) and str(row.get("col1")) == office and str(row.get("col8") or "")
        ),
        None,
    )
    if timezone_row is None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seeded Lockers Database has no timezone row for office {office!r}; "
            "in_time_zone reads the first matching entry's col8"
        )
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(expect),
        "raw_validation": validation,
        "lookup_table": deepcopy(lookup_seed),
        "job_context": deepcopy(job_context),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if isinstance(data.get("force_action_error"), dict):
        out["force_action_error"] = deepcopy(data["force_action_error"])
    return attach_variant(out, ctx)


def run_50816152(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_50816152(raw)
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table state")
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
    result["verifier"] = verify_50816152(result)
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


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("lookup_table"), dict):
        out.update(ctx.tools.call("harness.lookup_table.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
