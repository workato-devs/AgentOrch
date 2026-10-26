from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_91193728


RECIPE_ID = "91193728"
SEED_TYPE = "slack_firefighter_rerun_command_variant"
TRACK = "live_slack_workato_firefighter_rerun_chat_update"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "bot_command_v2"
TRIGGER_AS = "80a598fe"
POST_STEP_AS = "096e3f40"
RERUN_STEP_AS = "4d356cc8"
CATCH_STEP_AS = "9ee228f3"
STOP_STEP_AS = "027c7dde"
TS_TOKEN = "$SLACK_MESSAGE_TS"
TRIGGER_PARAM_KEYS = ("recipe_id", "job_id", "opportunity_id", "opportunity_name")
FIREFIGHTER_LINE = ":firefighter_8: We will attempt to check this particular opportunity again."
_TS_RE = re.compile(r"^\d+\.\d+$")
_LINK_SAFE_RE = re.compile(r"^[^<>|\n]+$")


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "slack_bot", "name": "bot_command_v2", "as": "80a598fe", "skip": false, "input": {"allow_dialog": "false", "domain": "firefighter", "hide_from_help": "true", "name": "rerun", "parameters": "[\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Recipe ID\",\n    \"name\": \"recipe_id\",\n    \"type\": \"string\",\n    \"optional\": false\n  },\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Job ID\",\n    \"name\": \"job_id\",\n    \"type\": \"string\",\n    \"optional\": false\n  },\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Opportunity ID\",\n    \"name\": \"opportunity_id\",\n    \"type\": \"string\",\n    \"optional\": false\n  },\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Opportunity Name\",\n    \"name\": \"opportunity_name\",\n    \"type\": \"string\",\n    \"optional\": false\n  }\n]", "scope": "evaluate_deal"}, "block": [{"number": 2, "keyword": "try", "provider": "", "name": "", "as": "", "skip": false, "input": {}, "block": [{"number": 3, "keyword": "action", "provider": "slack_bot", "name": "post_bot_message", "as": "096e3f40", "skip": false, "input": {"advanced": {"ts": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"80a598fe\",\"path\":[\"ts\"]}')}"}, "blocks": [{"block_type": "section_with_text", "button_type": "continue_flow", "section_text": ":salesforce: *<https://workato.lightning.force.com/lightning/r/Opportunity/#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"80a598fe\",\"path\":[\"parameters\", \"opportunity_id\"]}')}/view|#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"80a598fe\",\"path\":[\"parameters\", \"opportunity_name\"]}')}>* :salesforce:"}, {"block_type": "divider", "button_type": "continue_flow"}, {"block_type": "section_with_text", "button_type": "continue_flow", "section_text": ":firefighter_8: We will attempt to check this particular opportunity again."}], "channel": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"80a598fe\",\"path\":[\"context\", \"channel\"]}')}"}, "block": []}, {"number": 4, "keyword": "action", "provider": "workato_app", "name": "rerun_jobs", "as": "4d356cc8", "skip": false, "input": {"jobs": {"job_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"80a598fe\",\"path\":[\"parameters\", \"job_id\"]}')}"}, "recipe_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"80a598fe\",\"path\":[\"parameters\", \"recipe_id\"]}')}"}, "block": []}, {"number": 5, "keyword": "catch", "provider": "", "name": "", "as": "9ee228f3", "skip": false, "input": {"max_retry_count": "0", "retry_interval": "2"}, "block": [{"number": 6, "keyword": "stop", "provider": "", "name": "", "as": "027c7dde", "skip": false, "input": {"stop_reason": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"9ee228f3\",\"path\":[\"message\"]}')}", "stop_with_error": "true"}, "block": []}]}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (POST_STEP_AS, "slack_bot", "post_bot_message"),
    (RERUN_STEP_AS, "workato_app", "rerun_jobs"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "slack.post_message",
    "workato_app.rerun_jobs",
]
ALLOWED_TOOLS: list[str] = list(EXPECTED_RAW_TOOLS)
CASES = ("update_and_rerun", "catch_stop_error")
REQUIRED_EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "stopped",
    "slack_text",
    "rerun_args",
    "catch_message",
)
_EXPECT_ITEM_KEYS = {
    "tool", "table_id", "lookup_table_id", "match_fields", "channel",
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
}
_EXPECT_VALUE_KEYS = {
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
}


def _opportunity_line(opportunity_id: str, opportunity_name: str) -> str:
    return (
        ":salesforce: *<https://workato.lightning.force.com/lightning/r/Opportunity/"
        f"{opportunity_id}/view|{opportunity_name}>* :salesforce:"
    )


def validate_91193728(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    # Semantic pins on the drift-prone bits (the tree pin holds the exact
    # bytes; these name the trap when one changes).
    post = _node_by_as(raw, POST_STEP_AS)
    post_input = post.get("input") or {}
    advanced = post_input.get("advanced") if isinstance(post_input.get("advanced"), dict) else {}
    if TRIGGER_AS not in str(advanced.get("ts") or "") or '"ts"' not in str(advanced.get("ts") or ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} advanced.ts no longer threads the trigger ts "
            f"(the chat.update lane): {advanced.get('ts')!r}"
        )
    blocks = post_input.get("blocks") or []
    block_types = [str((block or {}).get("block_type") or "") for block in blocks]
    if block_types != ["section_with_text", "divider", "section_with_text"]:
        raise RuntimeError(f"recipe {RECIPE_ID} message blocks changed: {block_types}")
    if str(blocks[2].get("section_text") or "") != FIREFIGHTER_LINE:
        raise RuntimeError(f"recipe {RECIPE_ID} firefighter line changed")
    if "context\", \"channel" not in str(post_input.get("channel") or "").replace("'", "\""):
        raise RuntimeError(f"recipe {RECIPE_ID} channel pill changed: {post_input.get('channel')!r}")
    rerun = _node_by_as(raw, RERUN_STEP_AS)
    rerun_input = rerun.get("input") or {}
    jobs = rerun_input.get("jobs") if isinstance(rerun_input.get("jobs"), dict) else {}
    if "job_id" not in jobs or "recipe_id" not in rerun_input:
        raise RuntimeError(f"recipe {RECIPE_ID} rerun_jobs jobs.job_id/recipe_id bindings changed")
    stop = _node_by_as(raw, STOP_STEP_AS)
    if stop.get("keyword") != "stop" or str((stop.get("input") or {}).get("stop_with_error")) != "true":
        raise RuntimeError(f"recipe {RECIPE_ID} catch stop step changed")
    if CATCH_STEP_AS not in str((stop.get("input") or {}).get("stop_reason") or ""):
        raise RuntimeError(f"recipe {RECIPE_ID} stop_reason no longer reads the catch message")
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


def seed_91193728(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_91193728(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = _require_trigger_shape(trigger)
    force = data.get("force_action_error")
    expect = data.get("expect")
    _require_expect_shape(expect, parameters, force)
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
    }
    slack_seed = data.get("slack_seed_message")
    if force is not None:
        # CATCH branch: the forced error fires on the FIRST action, so no
        # live Slack call ever happens and the variant must not seed one.
        if slack_seed is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must not seed a Slack message "
                "(the chat.update step never runs)"
            )
        if trigger.get("ts") == TS_TOKEN or not _TS_RE.fullmatch(str(trigger.get("ts") or "")):
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must pin trigger.ts as a literal "
                f"epoch.micros string (nothing is seeded): {trigger.get('ts')!r}"
            )
    else:
        if not isinstance(slack_seed, dict) or not str(slack_seed.get("text") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} happy variants must declare slack_seed_message.text "
                "(chat.update needs a live bot-owned seeded ts)"
            )
        if trigger.get("ts") != TS_TOKEN:
            raise RuntimeError(
                f"recipe {RECIPE_ID} happy variants must pin trigger.ts as the "
                f"{TS_TOKEN!r} token: step 3 chat.updates the trigger ts, which only "
                "works on the live seed-posted bot message"
            )
        posted = ctx.tools.call(
            "harness.slack.seed_message",
            {"channel": ctx.env.slack_channel_override, "text": str(slack_seed["text"])},
        )
        channel = str(posted.get("channel") or ctx.env.slack_channel_override)
        ts = str(posted.get("ts") or "")
        if not ts:
            raise RuntimeError(f"recipe {RECIPE_ID} Slack seed message returned no ts: {posted}")
        trigger = deepcopy(trigger)
        trigger["ts"] = ts
        out["seed_slack_message"] = {"channel": channel, "ts": ts, "text": str(slack_seed["text"])}
    out["trigger"] = trigger
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_91193728(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_91193728(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not ctx.env.slack_channel_override:
        raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    catch_branch = isinstance(seed.get("force_action_error"), dict)
    message = seed.get("seed_slack_message") if isinstance(seed.get("seed_slack_message"), dict) else {}
    if not catch_branch and not (message.get("channel") and message.get("ts")):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing the live seed_slack_message ts")
    if catch_branch and message:
        raise RuntimeError(f"recipe {RECIPE_ID} catch seed must not carry a live Slack message")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_slack_message": deepcopy(message) if message else None,
        "expected_channel": ctx.env.slack_channel_override,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
        "cleanup_response": None,
    }
    cleanup_response: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
    finally:
        if message:
            # Required cleanup (rerun determinism): the run chat.updates the
            # bot-owned seeded placeholder in place; delete it so reruns never
            # see (or double-update) a stale message. Catch variants own no
            # live Slack state.
            cleanup_response = ctx.tools.call(
                "slack.delete_message",
                {"channel": message["channel"], "ts": message["ts"]},
            )
            details["cleanup_response"] = cleanup_response
    if message and not (cleanup_response or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Slack cleanup failed: {cleanup_response}")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_91193728(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> dict[str, str]:
    if sorted(trigger.keys()) != ["context", "parameters", "ts"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly "
            "{'ts': ..., 'context': {'channel': ...}, 'parameters': {...}}; "
            f"got keys {sorted(trigger.keys())}"
        )
    context = trigger.get("context")
    if not isinstance(context, dict) or sorted(context.keys()) != ["channel"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger context must carry exactly ['channel']: {context!r}"
        )
    channel = str(context.get("channel") or "")
    if not channel.startswith("C"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger context.channel must be a C-prefixed channel "
            f"literal (non-U channels route to the override by design; a U-prefixed "
            f"value would target a live user): {channel!r}"
        )
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict) or sorted(parameters.keys()) != sorted(TRIGGER_PARAM_KEYS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must carry exactly the declared "
            f"{sorted(TRIGGER_PARAM_KEYS)}; got {sorted(parameters or {})}"
        )
    out: dict[str, str] = {}
    for key in TRIGGER_PARAM_KEYS:
        value = parameters.get(key)
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger parameters.{key} must be a non-empty string "
                f"(all four are required by the declared command schema): {value!r}"
            )
        out[key] = value
    for key in ("opportunity_id", "opportunity_name"):
        if not _LINK_SAFE_RE.fullmatch(out[key]):
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger parameters.{key} interpolates into Slack "
                f"link markup <url|label>; got unsafe value {out[key]!r}"
            )
    if not str(trigger.get("ts") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} trigger ts must be non-empty")
    return out


def _require_expect_shape(
    expect: Any,
    parameters: dict[str, str],
    force: Any,
) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has unexpected keys: {unknown}")
    case = expect.get("case")
    if case not in CASES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.case must be one of {CASES}")
    if force is not None:
        if case != "catch_stop_error":
            raise RuntimeError(
                f"recipe {RECIPE_ID} force_action_error variants must pin case "
                f"'catch_stop_error'; got {case!r}"
            )
        if not isinstance(force, dict) or str(force.get("step_as") or "") != POST_STEP_AS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} force_action_error must target the FIRST action "
                f"{POST_STEP_AS!r} (forcing the second would live-update the seeded "
                f"message before stopping); got {force!r}"
            )
        if not str(force.get("error") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} force_action_error.error must be non-empty")
        checks = (
            expect.get("executed_action_count") == 0,
            expect.get("tools") == [],
            expect.get("tool_expectations") == [],
            expect.get("stopped") is True,
            expect.get("slack_text") is None,
            expect.get("rerun_args") is None,
            expect.get("catch_message") == str(force.get("error")),
        )
        if not all(checks):
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants stop before any action executes: "
                "expect {executed_action_count 0, tools [], tool_expectations [], "
                "stopped true, slack_text null, rerun_args null, catch_message == the "
                f"forced error}}; got {expect!r}"
            )
        return
    if case != "update_and_rerun":
        raise RuntimeError(
            f"recipe {RECIPE_ID} happy variants must pin case 'update_and_rerun'; got {case!r}"
        )
    expected_text = (
        _opportunity_line(parameters["opportunity_id"], parameters["opportunity_name"])
        + "\n"
        + FIREFIGHTER_LINE
    )
    expected_rerun_args = {
        "recipe_id": parameters["recipe_id"],
        "job_ids": [parameters["job_id"]],
    }
    checks = (
        expect.get("executed_action_count") == 2,
        expect.get("tools") == ALLOWED_TOOLS,
        expect.get("stopped") is False,
        expect.get("catch_message") is None,
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} happy variants must pin executed_action_count 2, "
            f"tools {ALLOWED_TOOLS}, stopped false, catch_message null: {expect!r}"
        )
    if expect.get("slack_text") != expected_text:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.slack_text must be the exact 2-line render "
            f"(divider dropped) {expected_text!r}; got {expect.get('slack_text')!r}"
        )
    if expect.get("rerun_args") != expected_rerun_args:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.rerun_args must be {expected_rerun_args!r}; "
            f"got {expect.get('rerun_args')!r}"
        )
    _require_tool_expectations(expect, expected_text, expected_rerun_args)


def _require_tool_expectations(
    expect: dict[str, Any],
    expected_text: str,
    expected_rerun_args: dict[str, Any],
) -> None:
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or len(items) != len(ALLOWED_TOOLS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin both expect.tools entries"
        )
    for idx, item in enumerate(items):
        if not isinstance(item, dict) or item.get("tool") != ALLOWED_TOOLS[idx]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] must pin tool "
                f"{ALLOWED_TOOLS[idx]!r}: {item!r}"
            )
        unknown = sorted(set(item.keys()) - _EXPECT_ITEM_KEYS)
        if unknown:
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] has unsupported keys: {unknown}"
            )
        if not (set(item.keys()) & _EXPECT_VALUE_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] must pin at least one VALUE key "
                f"({sorted(_EXPECT_VALUE_KEYS)})"
            )
    slack_item, rerun_item = items
    lines = expected_text.split("\n")
    if (
        slack_item.get("channel") != "override"
        or slack_item.get("args_contains") != {"ts": "__ANY__", "thread_ts": ""}
        or slack_item.get("text_fragments") != lines
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0] must pin channel 'override', "
            "args_contains {'ts': '__ANY__', 'thread_ts': ''} (a fresh post would carry "
            "no ts) and text_fragments == the exact 2 rendered lines: "
            f"{slack_item!r}"
        )
    if rerun_item.get("args_contains") != expected_rerun_args:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[1].args_contains must pin "
            f"{expected_rerun_args!r}: {rerun_item!r}"
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


def _node_by_as(raw: dict[str, Any], step_as: str) -> dict[str, Any]:
    node = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == step_as),
        None,
    )
    if not isinstance(node, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} step {step_as} missing")
    return node


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
