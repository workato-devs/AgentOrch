from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_120762631


RECIPE_ID = "120762631"
SEED_TYPE = "api_platform_deepresearch_job_publish_variant"
TRACK = "workato_api_platform_deepresearch_job_publish"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "4c34d26c"
DECLARE_AS = "7c6eff74"
PUBLISH_AS = "fa742e11"
SUCCESS_RETURN_AS = "0a351f84"
CATCH_AS = "dbd9e528"
CATCH_RETURN_AS = "bccfccc1"
TOPIC_ID = "47402"

# workato_api_platform.receive_request (as 4c34d26c) -- dereferences
# request.user_objectives (publish message) and request.zoominfo_id (via
# =_dp(...).to_i). Body = one TRY (step 2):
#   3  workato_variable.declare_variable 7c6eff74: workflow_run_id =
#      =workato.uuid -- resolved from seed.workato_uuids (deterministic list,
#      consumed in call order; the engine evaluates the declare node's data
#      TWICE -- once while resolving the args `variables` object and once for
#      the step result -- so ONE run consumes EXACTLY TWO seeded uuids. The
#      seeder therefore requires seed.workato_uuids == [u, u] with both
#      entries identical, keeping args and step output consistent.)
#   4  workato_pub_sub.publish_to_topic fa742e11 (topic 47402 '[RIQ] New
#      DeepResearch Job', Workato-internal mock): message {conversation_id
#      'NA', force_generate 'true' (custom-value string), user_email
#      'api_user', user_objectives = request pill (typed passthrough),
#      workflow_run_id = declare pill, zoom_info_id = request.zoominfo_id
#      .to_i (INTEGER -- '00421' -> 421)}
#   5  workato_api_platform.return_response 0a351f84: 201 {success 'true'
#      (literal string), workflow_run_id pill} -- ENGINE-TERMINAL
#   6  CATCH dbd9e528 (max_retry_count 0) -> 7 return_response bccfccc1:
#      500 {message: catch.dbd9e528.message, success 'false'} -- TERMINAL
#
# Branch mapping (all reachable paths covered):
# - variant_00 publish_201: happy path; 3 executed actions (declare +
#   publish + 201). The trailing catch never fires.
# - variant_01 catch_500: seed.force_action_error on fa742e11 (the publish
#   is a pure Workato-internal mock -- no trigger-controllable failure
#   exists, the forced error is the deterministic catch path). The error
#   raises BEFORE the tool call, so the trace has NO publish row; declare
#   still ran (both uuids consumed). 2 executed actions.
# - variant_02 zoominfo_string_to_i: request.zoominfo_id seeded as the
#   STRING '00421' -> .to_i coerces to integer 421 in the published message
#   (Ruby to_i, leading zeros dropped). 201 path again; pins the coercion.
#
# Backends: ALL Workato-internal mocks (api_platform trigger/responses,
# pub_sub topic, workato_variable) -- no live backend, no cleanup, no
# persistent state. Both return_response steps are engine-terminal
# (TERMINAL_TOOLS), so exactly one response fires per run.

_RAW_PIN_JSON = r"""{"as": "4c34d26c", "block": [{"as": "", "block": [{"as": "7c6eff74", "block": [], "input": {"variables": {"data": {"workflow_run_id": "=workato.uuid"}, "schema": "[{\"name\":\"workflow_run_id\",\"type\":\"string\",\"optional\":true,\"label\":\"workflow_run_id\",\"details\":{\"real_name\":\"workflow_run_id\"},\"control_type\":\"text\",\"parent\":[\"variables\",\"data\"]}]"}}, "keyword": "action", "name": "declare_variable", "number": 3, "provider": "workato_variable", "skip": false}, {"as": "fa742e11", "block": [], "input": {"message": {"conversation_id": "NA", "force_generate": "true", "user_email": "api_user", "user_objectives": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"4c34d26c\",\"path\":[\"request\", \"user_objectives\"]}')}", "workflow_run_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"7c6eff74\",\"path\":[\"workflow_run_id\"]}')}", "zoom_info_id": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"4c34d26c\",\"path\":[\"request\",\"zoominfo_id\"]}').to_i"}, "topic_id": "47402"}, "keyword": "action", "name": "publish_to_topic", "number": 4, "provider": "workato_pub_sub", "skip": false}, {"as": "0a351f84", "block": [], "input": {"http_status_code": "201", "response": {"success": "true", "workflow_run_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"7c6eff74\",\"path\":[\"workflow_run_id\"]}')}"}}, "keyword": "action", "name": "return_response", "number": 5, "provider": "workato_api_platform", "skip": false}, {"as": "dbd9e528", "block": [{"as": "bccfccc1", "block": [], "input": {"http_status_code": "500", "response": {"message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"dbd9e528\",\"path\":[\"message\"]}')}", "success": "false"}}, "keyword": "action", "name": "return_response", "number": 7, "provider": "workato_api_platform", "skip": false}], "input": {"max_retry_count": "0", "retry_interval": "2"}, "keyword": "catch", "name": "", "number": 6, "provider": "", "skip": false}], "input": {}, "keyword": "try", "name": "", "number": 2, "provider": "", "skip": false}], "input": {"request": {"content_type": "json", "schema": "[{\"name\":\"zoominfo_id\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"Zoominfo ID\",\"parse_output\":\"integer_conversion\"},{\"name\":\"user_objectives\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"User objectives\"}]"}, "response": {"content_type": "json", "responses": [{"body_schema": "[{\"name\":\"workflow_run_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Workflow run ID\"},{\"name\":\"success\",\"type\":\"boolean\",\"optional\":false,\"control_type\":\"checkbox\",\"label\":\"Success\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Success\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"success\",\"type\":\"boolean\",\"optional\":false}}]", "http_status_code": "201", "name": "Success"}, {"body_schema": "[{\"name\":\"message\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Message\"},{\"name\":\"success\",\"type\":\"boolean\",\"optional\":false,\"control_type\":\"checkbox\",\"label\":\"Success\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Success\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"success\",\"type\":\"boolean\",\"optional\":false}}]", "http_status_code": "500", "name": "Error"}]}}, "keyword": "trigger", "name": "receive_request", "number": 1, "provider": "workato_api_platform", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (DECLARE_AS, "workato_variable", "declare_variable"),
    (PUBLISH_AS, "workato_pub_sub", "publish_to_topic"),
    (SUCCESS_RETURN_AS, "workato_api_platform", "return_response"),
    (CATCH_RETURN_AS, "workato_api_platform", "return_response"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "workato_pub_sub.publish_to_topic",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = [
    "workato_pub_sub.publish_to_topic",
    "workato_api_platform.return_response",
]
REQUIRED_EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "outcome",
    "http_status_code",
    "response",
    "return_step_as",
    "workflow_run_id",
    "published_message",
)
OPTIONAL_EXPECT_KEYS = {"catch_message"}
OUTCOMES = ("publish_201", "catch_500")
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_ZOOMINFO_RE = re.compile(r"^\s*\d+\s*$")


def validate_120762631(raw: dict[str, Any]) -> dict[str, Any]:
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
    nodes = {str(node.get("as") or ""): node for node in _walk_nodes(raw)}
    # Semantic pins (the tree pin holds the bytes; these name the traps):
    # 1. the =workato.uuid declaration (the whole reason this recipe needed
    #    an engine gap fix),
    declare_data = (
        ((nodes[DECLARE_AS].get("input") or {}).get("variables") or {}).get("data") or {}
    )
    if declare_data.get("workflow_run_id") != "=workato.uuid":
        raise RuntimeError(
            f"recipe {RECIPE_ID} workflow_run_id declaration changed: {declare_data!r}"
        )
    # 2. the .to_i coercion on the zoominfo_id request pill,
    publish_message = (nodes[PUBLISH_AS].get("input") or {}).get("message") or {}
    zoom_formula = str(publish_message.get("zoom_info_id") or "")
    if not zoom_formula.startswith("=") or not zoom_formula.endswith(".to_i"):
        raise RuntimeError(f"recipe {RECIPE_ID} zoom_info_id formula changed: {zoom_formula!r}")
    if str((nodes[PUBLISH_AS].get("input") or {}).get("topic_id")) != TOPIC_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} publish topic changed")
    # 3. both responses (201 with the workflow_run_id pill; catch 500 with
    #    the catch.message pill).
    if str((nodes[SUCCESS_RETURN_AS].get("input") or {}).get("http_status_code")) != "201":
        raise RuntimeError(f"recipe {RECIPE_ID} success status changed")
    if str((nodes[CATCH_RETURN_AS].get("input") or {}).get("http_status_code")) != "500":
        raise RuntimeError(f"recipe {RECIPE_ID} catch status changed")
    catch_body = (nodes[CATCH_RETURN_AS].get("input") or {}).get("response") or {}
    if '"line\\":\\"dbd9e528\\"' not in json.dumps(catch_body.get("message") or "") and (
        "dbd9e528" not in str(catch_body.get("message") or "")
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} catch message pill changed: {catch_body!r}")
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


def seed_120762631(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_120762631(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["workato_uuids"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the workato_uuids section "
            f"(the =workato.uuid engine contract): got "
            f"{sorted(seed_in.keys()) if isinstance(seed_in, dict) else seed_in!r}"
        )
    uuid = _require_workato_uuids(seed_in["workato_uuids"])
    force = data.get("force_action_error")
    _require_force_shape(force)
    _require_expect_shape(data.get("expect"), force, trigger, uuid)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "workato_uuids": list(seed_in["workato_uuids"]),
        "expect": deepcopy(data["expect"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_120762631(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_120762631(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    _require_trigger_shape(seed.get("trigger") or {})
    _require_workato_uuids(seed.get("workato_uuids"))
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    # Pure Workato-internal mock recipe: no live backend, no persistent state,
    # no cleanup (API responses and pub/sub publishes are not persistent).
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "expect": expect,
            "raw_validation": validation,
            "workato_uuids": seed.get("workato_uuids"),
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_120762631(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != ["request"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'request': ...}}; "
            f"got {sorted(trigger.keys())}"
        )
    request = trigger["request"]
    if not isinstance(request, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger request must be an object")
    unknown = sorted(set(request.keys()) - {"zoominfo_id", "user_objectives"})
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger request has unknown keys: {unknown}")
    zoominfo = request.get("zoominfo_id")
    if isinstance(zoominfo, bool) or not (
        isinstance(zoominfo, int) or (isinstance(zoominfo, str) and _ZOOMINFO_RE.match(zoominfo))
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} request.zoominfo_id must be an integer or a digit string "
            f"(the recipe applies .to_i; non-numeric strings would silently become 0): "
            f"{zoominfo!r}"
        )
    if not isinstance(request.get("user_objectives"), str) or not request["user_objectives"].strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} request.user_objectives must be a non-empty string "
            f"(the publish message dereferences it)"
        )


def _require_workato_uuids(uuids: Any) -> str:
    # ENGINE CONTRACT (pinned by probe): the verbatim declare node evaluates
    # =workato.uuid TWICE per run (args resolution + result resolution), so
    # the deterministic seed list must hold EXACTLY TWO IDENTICAL uuids --
    # anything else either fail-fasts mid-run or splits args/result values.
    if (
        not isinstance(uuids, list)
        or len(uuids) != 2
        or uuids[0] != uuids[1]
        or not isinstance(uuids[0], str)
        or not _UUID_RE.match(uuids[0])
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_uuids must be exactly [u, u] with two "
            f"IDENTICAL lowercase uuid strings (the declare node consumes one per "
            f"formula evaluation and evaluates twice): {uuids!r}"
        )
    return uuids[0]


def _require_force_shape(force: Any) -> None:
    if force is None:
        return
    if not isinstance(force, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error must be an object")
    if str(force.get("step_as") or "") != PUBLISH_AS or not str(force.get("error") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error must target step_as {PUBLISH_AS!r} with "
            f"an explicit error message (the publish is the only fallible step inside the "
            f"TRY -- declare and the terminal 201 have no failure mode)"
        )


def _require_expect_shape(
    expect: Any, force: Any, trigger: dict[str, Any], uuid: str
) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS) - OPTIONAL_EXPECT_KEYS)
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    outcome = expect.get("outcome")
    if outcome not in OUTCOMES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.outcome must be one of {OUTCOMES}")
    if (outcome == "catch_500") != (force is not None):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the catch outcome and force_action_error must be declared "
            f"together (no other deterministic failure exists)"
        )
    if expect.get("workflow_run_id") != uuid:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.workflow_run_id must pin the seeded uuid: "
            f"{expect.get('workflow_run_id')!r} != {uuid!r}"
        )
    request = trigger["request"]
    zoom_int = int(str(request["zoominfo_id"]).strip())
    if outcome == "publish_201":
        expected_message = {
            "conversation_id": "NA",
            "force_generate": "true",
            "user_email": "api_user",
            "user_objectives": request["user_objectives"],
            "workflow_run_id": uuid,
            "zoom_info_id": zoom_int,
        }
        checks = (
            expect.get("executed_action_count") == 3,
            expect.get("tools") == ALLOWED_TOOLS,
            expect.get("http_status_code") == "201",
            expect.get("return_step_as") == SUCCESS_RETURN_AS,
            expect.get("response") == {"success": "true", "workflow_run_id": uuid},
            expect.get("published_message") == expected_message,
            "catch_message" not in expect,
        )
    else:  # catch_500
        checks = (
            expect.get("executed_action_count") == 2,
            expect.get("tools") == ["workato_api_platform.return_response"],
            expect.get("http_status_code") == "500",
            expect.get("return_step_as") == CATCH_RETURN_AS,
            expect.get("response") == {"message": force.get("error"), "success": "false"},
            expect.get("published_message") is None,
            expect.get("catch_message") == force.get("error"),
        )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with outcome {outcome!r}: {expect!r}"
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
