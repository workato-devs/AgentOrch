from __future__ import annotations

import datetime as _dt
import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_125342694


RECIPE_ID = "125342694"
SEED_TYPE = "slack_app_home_proserv_menu_variant"
TRACK = "live_slack_app_home_publish"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "new_event"
TRIGGER_AS = "fc4e7116"
HOME_AS = "fd296d51"
DEAD_HOME_AS = "8aa4ae07"   # skip:true older 17-block home (editor leftover)
CATCH_AS = "7c0db11c"
DM_AS = "8bc6eb0f"
LIVE_MEMBER_ID = "U0B91BSRGF8"
PLACEHOLDER_IMAGE_URL = "https://a.slack-edge.com/80588/img/plugins/app/service_72.png"


_RAW_PIN_JSON = r"""{"as": "fc4e7116", "block": [{"as": "", "block": [{"as": "fd296d51", "block": [], "input": {"blocks": [{"alt_text": "ProServ Bot", "block_type": "section_with_image", "image_url": "https://avatars.slack-edge.com/<anon>2024-01-01</anon>/1458338400595_e4c75069b7735e32d871_88.png", "section_text": "=today.wday == 5 ? \"Hey <@\"+_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"fc4e7116\",\"path\":[\"app_home_opened\",\"user\"]}')+\">, it's good to have you here. What would you like to do today? \\n :yay: Happy Fridayyy!!! Don't forget to fill the timesheets in Certinia. Enjoy your weekend\" : \"Hey <@\"+_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"fc4e7116\",\"path\":[\"app_home_opened\",\"user\"]}')+\">, it's good to have you here. What would you like to do today?\""}, {"block_type": "divider"}, {"block_type": "section_with_text", "section_text": "> :envelope_with_arrow: *Sales / Customer Success Requests* "}, {"actions": [{"bot_command": "61748545", "button_title": "Professional Services Opp", "params": "action: request_form", "style": "primary", "type": "button"}], "block_type": "actions"}, {"block_type": "context", "elements": [{"text": "Create a professional services opportunity and request a Practice Manager for scoping.  Use this for enterprise onboardings, implementation services, and/or advisory services (SOWs)", "type": "text"}]}, {"actions": [{"bot_command": "61748548", "button_title": "Investment Service Request", "style": "primary", "type": "button", "url": "https://docs.google.com/forms/d/e/1FAIpQLSe4ZEWWCtcyXwXb3_SnzpbmURS5GbHeJwwuTC81J-4xk7ZGIQ/viewform"}], "block_type": "actions"}, {"block_type": "context", "elements": [{"text": "Place a request for investment services approval.  Utilize the ScaleX program for new logo acquisition or the Accelerate360 program for at-risk accounts.", "type": "text"}]}, {"actions": [{"bot_command": "45586144", "button_title": "Technical Assistance Request", "style": "primary", "type": "button"}], "block_type": "actions"}, {"block_type": "context", "elements": [{"text": "Place a request for ad-hoc technical assistance for existing customers.  Requests may include recipe reviews, task optimization guidance or security reviews.  Should require less than 4 hours of effort.", "type": "text"}]}, {"block_type": "divider"}, {"block_type": "section_with_text", "section_text": "> :wrench: *Professional Services Utilities* "}, {"actions": [{"bot_command": "43286104", "button_title": "Add Project Contact", "params": "operation_name: addprojectcontact", "style": "primary", "type": "button"}], "block_type": "actions"}, {"block_type": "context", "elements": [{"text": "Add contact for CSAT survey", "type": "text"}]}, {"actions": [{"bot_command": "45586053", "button_title": "Enrich Introduction Deck", "style": "primary", "type": "button"}], "block_type": "actions"}, {"block_type": "context", "elements": [{"text": "Automate deck enrichment for Direct Customer Packaged Onboardings (will not work for Non-Enterprise Onboardings)", "type": "text"}]}, {"block_type": "divider"}, {"block_type": "section_with_text", "section_text": "> :stopwatch: *Time Tracking Tools* "}, {"actions": [{"bot_command": "62706588", "button_title": "Initialize Timesheet", "style": "default", "type": "button"}], "block_type": "actions"}, {"block_type": "context", "elements": [{"text": "Initial setup required for automated certinia timesheet creation. (To be run only ONCE)", "type": "text"}]}, {"actions": [{"bot_command": "62706589", "button_title": "Certinia Create Timesheet", "style": "primary", "type": "button"}], "block_type": "actions"}, {"block_type": "context", "elements": [{"text": "Automatically generates the weekly timesheet report for Certinia.", "type": "text"}]}, {"actions": [{"bot_command": "62706583", "button_title": "Select Projects", "style": "default", "type": "button"}], "block_type": "actions"}, {"block_type": "context", "elements": [{"text": "Allows you to select and manage non-billable projects within Certinia.", "type": "text"}]}, {"actions": [{"bot_command": "63559694", "button_title": "Manage Calendars", "style": "default", "type": "button"}], "block_type": "actions"}, {"block_type": "context", "elements": [{"text": "Allows you to select and manage the calendars to be included in the timesheet generation process for Certinia.", "type": "text"}]}], "user_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"fc4e7116\",\"path\":[\"app_home_opened\", \"user\"]}')}"}, "keyword": "action", "name": "open_bot_app_home", "number": 3, "provider": "slack_bot", "skip": false}, {"as": "8aa4ae07", "block": [], "keyword": "action", "name": "open_bot_app_home", "number": 4, "provider": "slack_bot", "skip": true}, {"as": "7c0db11c", "block": [{"as": "8bc6eb0f", "block": [], "input": {"blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": "<@#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"fc4e7116\",\"path\":[\"app_home_opened\", \"user\"]}')}>, it seems something went wrong with Bot homepage! \nPlease contact bot admin <@U025CTFAX6K>"}], "channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"fc4e7116\",\"path\":[\"app_home_opened\", \"user\"]}')}"}, "keyword": "action", "name": "post_bot_message", "number": 6, "provider": "slack_bot", "skip": false}], "input": {"max_retry_count": "0", "retry_interval": "2"}, "keyword": "catch", "name": "", "number": 5, "provider": "", "skip": false}], "input": {}, "keyword": "try", "name": "", "number": 2, "provider": "", "skip": false}], "input": {"event_name": "app_home_opened"}, "keyword": "trigger", "name": "new_event", "number": 1, "provider": "slack_bot", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

HOME_BLOCKS_RAW: list[dict[str, Any]] = json.loads(r"""[{"alt_text": "ProServ Bot", "block_type": "section_with_image", "image_url": "https://avatars.slack-edge.com/<anon>2024-01-01</anon>/1458338400595_e4c75069b7735e32d871_88.png", "section_text": "=today.wday == 5 ? \"Hey <@\"+_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"fc4e7116\",\"path\":[\"app_home_opened\",\"user\"]}')+\">, it's good to have you here. What would you like to do today? \\n :yay: Happy Fridayyy!!! Don't forget to fill the timesheets in Certinia. Enjoy your weekend\" : \"Hey <@\"+_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"fc4e7116\",\"path\":[\"app_home_opened\",\"user\"]}')+\">, it's good to have you here. What would you like to do today?\""}, {"block_type": "divider"}, {"block_type": "section_with_text", "section_text": "> :envelope_with_arrow: *Sales / Customer Success Requests* "}, {"actions": [{"bot_command": "61748545", "button_title": "Professional Services Opp", "params": "action: request_form", "style": "primary", "type": "button"}], "block_type": "actions"}, {"block_type": "context", "elements": [{"text": "Create a professional services opportunity and request a Practice Manager for scoping.  Use this for enterprise onboardings, implementation services, and/or advisory services (SOWs)", "type": "text"}]}, {"actions": [{"bot_command": "61748548", "button_title": "Investment Service Request", "style": "primary", "type": "button", "url": "https://docs.google.com/forms/d/e/1FAIpQLSe4ZEWWCtcyXwXb3_SnzpbmURS5GbHeJwwuTC81J-4xk7ZGIQ/viewform"}], "block_type": "actions"}, {"block_type": "context", "elements": [{"text": "Place a request for investment services approval.  Utilize the ScaleX program for new logo acquisition or the Accelerate360 program for at-risk accounts.", "type": "text"}]}, {"actions": [{"bot_command": "45586144", "button_title": "Technical Assistance Request", "style": "primary", "type": "button"}], "block_type": "actions"}, {"block_type": "context", "elements": [{"text": "Place a request for ad-hoc technical assistance for existing customers.  Requests may include recipe reviews, task optimization guidance or security reviews.  Should require less than 4 hours of effort.", "type": "text"}]}, {"block_type": "divider"}, {"block_type": "section_with_text", "section_text": "> :wrench: *Professional Services Utilities* "}, {"actions": [{"bot_command": "43286104", "button_title": "Add Project Contact", "params": "operation_name: addprojectcontact", "style": "primary", "type": "button"}], "block_type": "actions"}, {"block_type": "context", "elements": [{"text": "Add contact for CSAT survey", "type": "text"}]}, {"actions": [{"bot_command": "45586053", "button_title": "Enrich Introduction Deck", "style": "primary", "type": "button"}], "block_type": "actions"}, {"block_type": "context", "elements": [{"text": "Automate deck enrichment for Direct Customer Packaged Onboardings (will not work for Non-Enterprise Onboardings)", "type": "text"}]}, {"block_type": "divider"}, {"block_type": "section_with_text", "section_text": "> :stopwatch: *Time Tracking Tools* "}, {"actions": [{"bot_command": "62706588", "button_title": "Initialize Timesheet", "style": "default", "type": "button"}], "block_type": "actions"}, {"block_type": "context", "elements": [{"text": "Initial setup required for automated certinia timesheet creation. (To be run only ONCE)", "type": "text"}]}, {"actions": [{"bot_command": "62706589", "button_title": "Certinia Create Timesheet", "style": "primary", "type": "button"}], "block_type": "actions"}, {"block_type": "context", "elements": [{"text": "Automatically generates the weekly timesheet report for Certinia.", "type": "text"}]}, {"actions": [{"bot_command": "62706583", "button_title": "Select Projects", "style": "default", "type": "button"}], "block_type": "actions"}, {"block_type": "context", "elements": [{"text": "Allows you to select and manage non-billable projects within Certinia.", "type": "text"}]}, {"actions": [{"bot_command": "63559694", "button_title": "Manage Calendars", "style": "default", "type": "button"}], "block_type": "actions"}, {"block_type": "context", "elements": [{"text": "Allows you to select and manage the calendars to be included in the timesheet generation process for Certinia.", "type": "text"}]}]""")
GREETING_FORMULA_PREFIX = "=today.wday == 5 ?"
PUBLISHED_COUNTS = {"blocks": 25, "section": 4, "divider": 3, "actions": 9, "context": 9}

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (HOME_AS, "slack_bot", "open_bot_app_home"),
    (DM_AS, "slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "slack_bot.open_bot_app_home",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = list(EXPECTED_RAW_TOOLS)
BRANCHES = ("friday_home", "weekday_home", "catch_dm")
REQUIRED_EXPECT_KEYS = (
    "case",
    "branch",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "greeting_text",
    "home_blocks",
    "published_image_url",
    "published_counts",
    "dm",
    "dead_step_traced",
    "catch",
)
_EXPECTATION_TARGET_KEYS = {"tool", "table_id", "lookup_table_id", "match_fields", "channel"}
_EXPECTATION_VALUE_KEYS = {
    "args_contains",
    "result_count",
    "response_contains",
    "result_contains",
    "created",
    "http_status_code",
    "text_fragments",
    "options_contains",
}
_USER_RE = re.compile(r"^U[A-Z0-9]{5,12}$")


def _greeting_friday(user: str) -> str:
    return (
        "Hey <@%s>, it's good to have you here. What would you like to do today? \n"
        " :yay: Happy Fridayyy!!! Don't forget to fill the timesheets in Certinia. "
        "Enjoy your weekend" % user
    )


def _greeting_weekday(user: str) -> str:
    return "Hey <@%s>, it's good to have you here. What would you like to do today?" % user


def _dm_text(user: str) -> str:
    return (
        "<@%s>, it seems something went wrong with Bot homepage! \n"
        "Please contact bot admin <@U025CTFAX6K>" % user
    )


def validate_125342694(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    if str((raw.get("input") or {}).get("event_name") or "") != "app_home_opened":
        raise RuntimeError(f"recipe {RECIPE_ID} trigger event changed")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    # Semantic pins on the drift-prone pieces.
    nodes = {str(node.get("as") or ""): node for node in _walk_nodes(raw)}
    home = nodes.get(HOME_AS) or {}
    blocks = (home.get("input") or {}).get("blocks")
    if blocks != HOME_BLOCKS_RAW:
        raise RuntimeError(f"recipe {RECIPE_ID} home blocks changed")
    greeting = str((blocks or [{}])[0].get("section_text") or "")
    if not greeting.startswith(GREETING_FORMULA_PREFIX):
        raise RuntimeError(
            f"recipe {RECIPE_ID} greeting lost the today.wday == 5 ternary: {greeting!r}"
        )
    if "<anon>" not in str((blocks or [{}])[0].get("image_url") or ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} greeting image_url lost its embedded anon tag -- the "
            f"live placeholder substitution premise no longer holds; re-triage"
        )
    dead = nodes.get(DEAD_HOME_AS) or {}
    if dead.get("skip") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} step {DEAD_HOME_AS} is no longer skip:true -- the "
            f"dead-branch proof does not hold; re-triage before building"
        )
    dm = nodes.get(DM_AS) or {}
    dm_input = dm.get("input") or {}
    dm_blocks = dm_input.get("blocks") or []
    if (
        TRIGGER_AS not in str(dm_input.get("channel") or "")
        or len(dm_blocks) != 1
        or "bot admin <@U025CTFAX6K>" not in str(dm_blocks[0].get("section_text") or "")
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} catch DM node changed")
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
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


def seed_125342694(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_125342694(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    user = _require_trigger_shape(trigger)
    now = data.get("now")
    wday = _derive_wday(now)
    force = data.get("force_action_error")
    if force is not None and (
        not isinstance(force, dict)
        or str(force.get("step_as") or "") != HOME_AS
        or not str(force.get("error") or "").strip()
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error must be exactly "
            f"{{'step_as': {HOME_AS!r}, 'error': <non-empty text>}} (the catch is "
            f"reachable ONLY through the home publish): {force!r}"
        )
    if "seed" in data and data.get("seed") != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no seedable backend state (slack-only, live): "
            f"seed must be absent or {{}}"
        )
    derived = _derive_ground_truth(user, wday, force)
    _require_expect_shape(data.get("expect"), derived)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "now": now,
        "trigger": trigger,
        "expect": deepcopy(data["expect"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_125342694(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_125342694(raw)
    if seed.get("now") in (None, ""):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing the fixed 'now'")
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("trigger"), dict) or not seed["trigger"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing the trigger payload")
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    # No snapshots and no cleanup: slack is the only backend; the App Home
    # publish overwrites the same member's tab on every run (idempotent live
    # surface) and the catch DM is an ordinary post never re-read.
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "now": seed.get("now"),
            "expect": seed.get("expect"),
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_125342694(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> str:
    if sorted(trigger.keys()) != ["app_home_opened"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly app_home_opened; "
            f"got {sorted(trigger.keys())}"
        )
    payload = trigger.get("app_home_opened")
    if not isinstance(payload, dict) or sorted(payload.keys()) != ["user"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.app_home_opened must be exactly "
            f"{{'user': <workspace member id>}} (the only field the recipe dereferences)"
        )
    user = payload.get("user")
    if not isinstance(user, str) or not _USER_RE.fullmatch(user):
        raise RuntimeError(
            f"recipe {RECIPE_ID} app_home_opened.user must be a Slack user id: {user!r}"
        )
    if user != LIVE_MEMBER_ID:
        raise RuntimeError(
            f"recipe {RECIPE_ID} app_home_opened.user must be the proven live member "
            f"{LIVE_MEMBER_ID}: views.publish AND the catch DM run LIVE fail-fast "
            f"against this user id; got {user!r}"
        )
    return user


def _derive_wday(now: Any) -> int:
    if not isinstance(now, str) or not now.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input requires a fixed 'now' (the greeting "
            f"pivots on today.wday)"
        )
    try:
        dt = _dt.datetime.fromisoformat(now.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeError(f"recipe {RECIPE_ID} 'now' must be an ISO timestamp: {now!r}") from exc
    if dt.tzinfo is None:
        raise RuntimeError(f"recipe {RECIPE_ID} 'now' must carry timezone information: {now!r}")
    # Engine 'today' is the UTC date of seed.now; Ruby wday is Sunday=0.
    return dt.astimezone(_dt.timezone.utc).date().isoweekday() % 7


def _derive_ground_truth(user: str, wday: int, force: Any) -> dict[str, Any]:
    if force is not None:
        return {
            "branch": "catch_dm",
            "greeting_text": None,
            "home_blocks": None,
            "dm": {"channel": user, "text": _dm_text(user)},
            "dead_step_traced": False,
            "catch": {
                "type": "RawRecipeExecutionError",
                "message": str(force.get("error") or ""),
                "adapter": "slack_bot",
                "action": "open_bot_app_home",
                "line_number": 3,
            },
        }
    branch = "friday_home" if wday == 5 else "weekday_home"
    greeting = _greeting_friday(user) if branch == "friday_home" else _greeting_weekday(user)
    home_blocks = deepcopy(HOME_BLOCKS_RAW)
    home_blocks[0]["section_text"] = greeting
    return {
        "branch": branch,
        "greeting_text": greeting,
        "home_blocks": home_blocks,
        "dm": None,
        "dead_step_traced": True,
        "catch": None,
    }


def _require_expect_shape(expect: Any, derived: dict[str, Any]) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    branch = expect.get("branch")
    if branch not in BRANCHES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch must be one of {BRANCHES}")
    if branch != derived["branch"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.branch {branch!r} contradicts the variant "
            f"input (derived {derived['branch']!r} from now/force_action_error)"
        )
    common = (
        expect.get("executed_action_count") == 1,
        expect.get("greeting_text") == derived["greeting_text"],
        expect.get("home_blocks") == derived["home_blocks"],
        expect.get("dm") == derived["dm"],
        expect.get("dead_step_traced") == derived["dead_step_traced"],
        expect.get("catch") == derived["catch"],
    )
    if branch == "catch_dm":
        branch_checks = (
            expect.get("tools") == ["slack.post_message"],
            expect.get("published_image_url") is None,
            expect.get("published_counts") is None,
        )
    else:
        branch_checks = (
            expect.get("tools") == ["slack_bot.open_bot_app_home"],
            expect.get("published_image_url") == PLACEHOLDER_IMAGE_URL,
            expect.get("published_counts") == PUBLISHED_COUNTS,
        )
    if not all(common) or not all(branch_checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with the derived ground "
            f"truth (branch {derived['branch']!r}): {expect!r}"
        )
    _require_tool_expectations(expect, derived)


def _require_tool_expectations(expect: dict[str, Any], derived: dict[str, Any]) -> None:
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or len(items) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin exactly the one "
            f"external call of this branch"
        )
    item = items[0]
    if not isinstance(item, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[0] must be an object")
    unknown = sorted(set(item) - _EXPECTATION_TARGET_KEYS - _EXPECTATION_VALUE_KEYS)
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[0] has non-corpus keys: {unknown}")
    if not any(key in item for key in _EXPECTATION_VALUE_KEYS):
        raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[0] pins no ground-truth value")
    if derived["branch"] == "catch_dm":
        checks = (
            item.get("tool") == "slack.post_message",
            item.get("args_contains") == {"channel": LIVE_MEMBER_ID},
            item.get("text_fragments") == [derived["dm"]["text"]],
        )
        reason = "catch DM must pin the raw user-id channel and the full admin-contact text"
    else:
        checks = (
            item.get("tool") == "slack_bot.open_bot_app_home",
            item.get("args_contains")
            == {"user_id": LIVE_MEMBER_ID, "view": {"blocks": derived["home_blocks"]}},
        )
        reason = (
            "home publish must pin the trigger user and the VERBATIM 25-block raw "
            "payload with only the greeting resolved"
        )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0] does not pin the derived ground "
            f"truth ({reason}): {item!r}"
        )


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
