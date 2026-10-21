from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data, variant_index
from ..verifier import verify_50815491


RECIPE_ID = "50815491"
SEED_TYPE = "hrbot_admin_error_status_variant"
TRACK = "live_slack_workato_service_admin_error"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"
# 'hrbot handle admin_error' bot command (required parameters status + ru_id):
# try { workato_service.call_service RUSlackLog Read-noClear -> json_parser
# parse_json x2 (attachment fields + buttons) -> workato_list
# accumulate_list_items (Attachment_title.upcase) -> IF status==in_progress
# { slack post_bot_message (warning, updates Message_to_update ts) +
# call_service Update } -> IF status==resolved { slack post_bot_message (good)
# + call_service Read } -> UNCONDITIONAL stop (stop_with_error=false), making
# step 14 parse_json dead code } catch { declare_variable Status
# (status.gsub("_","").titleize) + slack post_bot_message (danger, threaded
# under Message_to_update.presence or trigger ts) }.
# RUSlackLog replies are deterministic Workato-internal seed state
# (seed.workato_service_replies keyed by step as-id). Slack runs live: when a
# variant carries $SEED_MESSAGE_TS tokens, the seeder posts a real message and
# threads its ts into the trigger/replies so chat.update targets a live ts.
SERVICE_FLOW_ID = "18452539"
READ_STEP_AS = "8d9e8b75"
SEED_TS_TOKEN = "$SEED_MESSAGE_TS"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("workato_service", "call_service"),
    ("json_parser", "parse_json"),
    ("json_parser", "parse_json"),
    ("workato_list", "accumulate_list_items"),
    ("slack_bot", "post_bot_message"),
    ("workato_service", "call_service"),
    ("slack_bot", "post_bot_message"),
    ("workato_service", "call_service"),
    ("json_parser", "parse_json"),
    ("workato_variable", "declare_variable"),
    ("slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_service.call_service",
    "workato_runtime.parse_json",
    "workato_runtime.accumulate_list_items",
    "slack.post_message",
    "workato_runtime.declare_variable",
]
ALLOWED_TOOLS: list[str] = [
    "workato_service.call_service",
    "slack.post_message",
]


def validate_50815491(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    trigger_in = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    if (
        trigger_in.get("domain") != "hrbot"
        or trigger_in.get("name") != "handle"
        or trigger_in.get("scope") != "admin_error"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} is not the expected 'hrbot handle admin_error' command")
    actions = _collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    first_call = actions[0].get("input") if isinstance(actions[0].get("input"), dict) else {}
    if str(first_call.get("flow_id") or "") != SERVICE_FLOW_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} RUSlackLog flow id changed")
    if_conditions = _collect_if_rhs(raw)
    if if_conditions != ["in_progress", "resolved"]:
        raise RuntimeError(f"recipe {RECIPE_ID} IF status conditions changed: {if_conditions}")
    stop_node = _find_stop(raw)
    if stop_node is None or str((stop_node.get("input") or {}).get("stop_with_error")) != "false":
        raise RuntimeError(f"recipe {RECIPE_ID} unconditional graceful stop (step 13) changed")
    catch_node = _find_catch(raw)
    if catch_node is None:
        raise RuntimeError(f"recipe {RECIPE_ID} try/catch structure changed: no catch block")
    catch_actions = [
        (child.get("provider"), child.get("name"))
        for child in catch_node.get("block") or []
        if isinstance(child, dict) and child.get("keyword") == "action"
    ]
    if catch_actions != [("workato_variable", "declare_variable"), ("slack_bot", "post_bot_message")]:
        raise RuntimeError(f"recipe {RECIPE_ID} catch block actions changed: {catch_actions}")
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


def seed_50815491(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_50815491(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters")
    if (
        not isinstance(parameters, dict)
        or not str(parameters.get("status") or "")
        or not str(parameters.get("ru_id") or "")
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} bot command requires parameters.status and parameters.ru_id")
    context = trigger.get("context")
    if not isinstance(context, dict) or not str(context.get("user_name") or "") or not str(context.get("channel") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger requires context.user_name and context.channel")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    replies = seed_in.get("workato_service_replies")
    if not isinstance(replies, dict) or READ_STEP_AS not in replies:
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires seed.workato_service_replies keyed by the "
            f"call_service step as-ids (missing {READ_STEP_AS!r})"
        )
    read_reply = replies.get(READ_STEP_AS)
    if (
        not isinstance(read_reply, dict)
        or not isinstance(read_reply.get("Message"), list)
        or not read_reply["Message"]
        or not isinstance(read_reply["Message"][0], dict)
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} Read-noClear reply must carry a non-empty reply.Message array "
            "(steps 4-6 dereference its first item)"
        )
    job_context = data.get("job_context")
    if not isinstance(job_context, dict) or job_context.get("job_id") in (None, ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires a pinned job_context.job_id "
            "(the Update request's Buttons literal interpolates it)"
        )
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    replies = deepcopy(replies)
    message: dict[str, Any] | None = None
    if _contains_token(trigger, SEED_TS_TOKEN) or _contains_token(replies, SEED_TS_TOKEN):
        channel = ctx.env.slack_channel_override
        if not channel:
            raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
        idx = variant_index(ctx)
        seed_text = (
            f"benchmark seed for recipe {RECIPE_ID} variant {idx:02d}: "
            "hrbot admin_error message pending status update"
        )
        posted = ctx.tools.call("harness.slack.seed_message", {"channel": channel, "text": seed_text})
        ts = str(posted.get("ts") or "")
        if not ts:
            raise RuntimeError(f"Slack chat.postMessage returned no ts: {posted}")
        actual_channel = str(posted.get("channel") or channel)
        trigger = _replace_token(trigger, SEED_TS_TOKEN, ts)
        replies = _replace_token(replies, SEED_TS_TOKEN, ts)
        message = {"channel": actual_channel, "ts": ts, "text": seed_text}
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": deepcopy(expect),
        "raw_validation": validation,
        "workato_service_replies": replies,
        "job_context": deepcopy(job_context),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if message is not None:
        out["message"] = message
    if isinstance(data.get("force_action_error"), dict):
        out["force_action_error"] = deepcopy(data["force_action_error"])
    return attach_variant(out, ctx)


def run_50815491(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_50815491(raw)
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    if not isinstance(seed.get("workato_service_replies"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_service_replies")
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
    if isinstance(message, dict):
        if not str(message.get("channel") or "") or not str(message.get("ts") or ""):
            raise RuntimeError(f"recipe {RECIPE_ID} seed message is missing its live Slack channel or ts")
        details["seed_message"] = {
            "channel": message.get("channel"),
            "ts": message.get("ts"),
            "text": message.get("text"),
        }
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    details["raw_execution"] = raw_execution
    details["ground_truth"] = _ground_truth(raw_execution)
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_50815491(result)
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


def _collect_if_rhs(node: dict[str, Any]) -> list[str]:
    found: list[str] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "if":
            for condition in ((child.get("input") or {}).get("conditions") or []):
                if isinstance(condition, dict):
                    found.append(str(condition.get("rhs") or ""))
        found.extend(_collect_if_rhs(child))
    return found


def _find_stop(node: dict[str, Any]) -> dict[str, Any] | None:
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "stop":
            return child
        nested = _find_stop(child)
        if nested is not None:
            return nested
    return None


def _find_catch(node: dict[str, Any]) -> dict[str, Any] | None:
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "catch":
            return child
        nested = _find_catch(child)
        if nested is not None:
            return nested
    return None


def _contains_token(value: Any, token: str) -> bool:
    if isinstance(value, dict):
        return any(_contains_token(item, token) for item in value.values())
    if isinstance(value, list):
        return any(_contains_token(item, token) for item in value)
    return isinstance(value, str) and token in value


def _replace_token(value: Any, token: str, replacement: str) -> Any:
    if isinstance(value, dict):
        return {key: _replace_token(item, token, replacement) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_token(item, token, replacement) for item in value]
    if isinstance(value, str):
        return value.replace(token, replacement)
    return value


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
