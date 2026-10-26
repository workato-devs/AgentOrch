from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import RawWorkatoRuntime, RuntimeState, input_obj, resolve_text, resolve_value
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_83147854
from .snowflake_live_recipe_utils import ground_truth, seed_live_snowflake


RECIPE_ID = "83147854"
SEED_TYPE = "slack_app_home_department_gated_variant"
TRACK = "live_slack_app_home_snowflake_department_gate"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "new_event"
TRIGGER_EVENT = "app_home_opened"
EMPLOYEE_TABLE = "workato_business_systems.public.employee"
DEPARTMENT_TABLE = "PUBLIC.DEPARTMENT"
ADMIN_DEPARTMENT = "Business Technology"
ADMIN_BOT_COMMAND = "36925586"
REQUEST_BOT_COMMANDS = ("36925598", "36925589", "36925599")
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("slack", "get_user_by_email"),
    ("snowflake", "run_custom_sql"),
    ("slack_bot", "open_bot_app_home"),
    ("slack_bot", "open_bot_app_home"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "slack_bot.get_user_by_email",
    "snowflake.run_custom_sql",
    "slack_bot.open_bot_app_home",
]
ALLOWED_TOOLS: list[str] = [
    "slack_bot.get_user_by_email",
    "snowflake.run_custom_sql",
    "slack_bot.open_bot_app_home",
]


class _Runtime83147854(RawWorkatoRuntime):
    """Module-local runtime extensions (harness files are frozen for this
    batch; fold both into the shared engine when it is next extended).

    1. Workato's Slack "Get user by email/ID" action outputs the Slack user
       object directly (top-level profile.*) — this recipe dereferences the
       ["profile", "email"] pill. The live tool result nests the user object
       under "user", so the shared adapter's step output leaves that pill
       unresolvable (verified: lookup_path -> MISSING). Mirror the connector
       schema by lifting user.profile to the top level of the recorded step
       output. The ctx.tools call log (verifier ground truth) keeps the
       unmodified live result; fail-fast when the live lookup has no profile.
    The shared Slack live adapter now supports Workato's
    ``section_with_button`` discriminator directly, so App Home arguments are
    preserved exactly as authored.
    """

    def slack_bot_get_user_by_email(
        self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState
    ) -> tuple[str, dict[str, Any], dict[str, Any]]:
        tool, args, result = super().slack_bot_get_user_by_email(node, _ctx, state)
        user = result.get("user") if isinstance(result.get("user"), dict) else {}
        profile = user.get("profile") if isinstance(user.get("profile"), dict) else None
        if profile is None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} requires a resolvable live Slack user with a profile; "
                f"lookup result: {result}"
            )
        return tool, args, {**result, "profile": deepcopy(profile)}

    def slack_bot_open_bot_app_home(
        self, node: dict[str, Any], _ctx: RecipeContext, state: RuntimeState
    ) -> tuple[str, dict[str, Any], dict[str, Any]]:
        return super().slack_bot_open_bot_app_home(node, _ctx, state)


def validate_83147854(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if (raw.get("input") or {}).get("event_name") != TRIGGER_EVENT:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger is not the app_home_opened event")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    lookup_input = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if "1f66aace" not in str(lookup_input.get("id") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} user lookup no longer maps the trigger user id")
    sql_input = actions[1].get("input") if isinstance(actions[1].get("input"), dict) else {}
    sql = str(sql_input.get("sql") or "")
    for fragment in (
        "FROM workato_business_systems.public.employee e",
        "join department d on d.id = e.department_id",
        "e.email = :email",
    ):
        if fragment not in sql:
            raise RuntimeError(f"recipe {RECIPE_ID} employee/department SQL changed: missing {fragment!r}")
    email_bind = str(((sql_input.get("parameters") or {}).get("data") or {}).get("email") or "")
    if "2456d6be" not in email_bind or "profile" not in email_bind:
        raise RuntimeError(f"recipe {RECIPE_ID} :email bind no longer maps the looked-up profile email")
    admin_blocks = str((actions[2].get("input") or {}).get("blocks") or "")
    for fragment in (ADMIN_BOT_COMMAND, "Approve", ":lock: Admin use only", *REQUEST_BOT_COMMANDS):
        if fragment not in admin_blocks:
            raise RuntimeError(f"recipe {RECIPE_ID} admin App Home content changed: missing {fragment!r}")
    standard_blocks = str((actions[3].get("input") or {}).get("blocks") or "")
    if ADMIN_BOT_COMMAND in standard_blocks:
        raise RuntimeError(f"recipe {RECIPE_ID} standard App Home unexpectedly carries the admin command")
    for fragment in REQUEST_BOT_COMMANDS:
        if fragment not in standard_blocks:
            raise RuntimeError(f"recipe {RECIPE_ID} standard App Home content changed: missing {fragment!r}")
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


def seed_83147854(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_83147854(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    event = trigger.get("app_home_opened")
    if not isinstance(event, dict) or not str(event.get("user") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry app_home_opened.user (live Slack user id)"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    snowflake_seed = seed_in.get("snowflake_live")
    tables = snowflake_seed.get("tables") if isinstance(snowflake_seed, dict) else None
    if not isinstance(tables, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.snowflake_live.tables")
    for table in (EMPLOYEE_TABLE, DEPARTMENT_TABLE):
        if table not in tables:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed must define snowflake_live.tables[{table!r}] explicitly "
                "(explicit columns; empty tables still declare columns)"
            )
    provision = seed_live_snowflake(RECIPE_ID, data, ctx)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "expect": deepcopy(data.get("expect") if isinstance(data.get("expect"), dict) else {}),
        "raw_validation": validation,
        "snowflake_live": deepcopy(provision["state"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    for key in ("force_action_error", "job_context"):
        if isinstance(data.get(key), dict):
            out[key] = deepcopy(data[key])
    return attach_variant(out, ctx)


def run_83147854(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_83147854(raw)
    initial_snapshot = _snapshot(ctx, seed)
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    snowflake_cleanup: dict[str, Any] | None = None
    try:
        raw_execution = _Runtime83147854(ctx, seed).execute(raw)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        if isinstance(seed.get("snowflake_live"), dict):
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
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "cleanup_response": {"snowflake_live": snowflake_cleanup},
            "ground_truth": ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_83147854(result)
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
    if isinstance(seed.get("snowflake_live"), dict):
        out.update(ctx.tools.call("harness.snowflake.snapshot", {}))
    return out
