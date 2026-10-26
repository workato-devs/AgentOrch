from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_92629971


RECIPE_ID = "92629971"
SEED_TYPE = "recipe_function_slack_user_avatar_collector_variant"
TRACK = "live_slack_recipe_function_user_avatars"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "6f6ae674"
LOOKUP_EMAIL_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"b0c1c7a4\","
    "\"path\":[\"email\"]}')}"
)
IF4_LHS = (
    "=_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"b0c1c7a4\","
    "\"path\":[\"name\"]}').downcase"
)
IF7_LHS = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"891f2787\","
    "\"path\":[\"profile\", \"image_512\"]}')}"
)
FOREACH_SOURCE = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\","
    "\"line\":\"6f6ae674\",\"path\":[\"parameters\", \"Users\"]}')}"
)
ACCUMULATE_DATA = {
    "email": LOOKUP_EMAIL_PILL,
    "image_url": IF7_LHS,
    "placeholder_title": (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"b0c1c7a4\","
        "\"path\":[\"placeholder_title\"]}')}"
    ),
}


def _list_item_pill(field: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\","
        "\"line\":\"e7a6c22d\",\"path\":[\"list_items\", "
        "{\"path_element_type\": \"current_item\"}, \"" + field + "\"]}')}"
    )


RETURN_USERS_MAPPING = {
    "____source": (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\","
        "\"line\":\"e7a6c22d\",\"path\":[\"list_items\"]}')}"
    ),
    "email": _list_item_pill("email"),
    "image_url": _list_item_pill("image_url"),
    "placeholder_title": _list_item_pill("placeholder_title"),
}
EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("slack_bot", "get_user_by_email", "891f2787"),
    ("workato_list", "accumulate_list_items", "e7a6c22d"),
    ("workato_recipe_function", "return_result", "5a9e5dac"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "slack_bot.get_user_by_email",
    "workato_runtime.accumulate_list_items",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "slack_bot.get_user_by_email",
    "workato_recipe_function.return_result",
]


def validate_92629971(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed")
    schema_json = str((raw.get("input") or {}).get("parameters_schema_json") or "")
    for field in ('"name":"Users"', '"name":"placeholder_title"', '"name":"email"', '"name":"name"'):
        if field not in schema_json:
            raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter schema changed")
    actions = _collect_keyword(raw, "action")
    actual = [(a.get("provider"), a.get("name"), a.get("as")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    skipped = [
        (node.get("number"), node.get("provider"), node.get("name"))
        for node in _collect_skipped_actions(raw)
    ]
    if skipped != [(5, "slack", "get_user_by_email"), (10, None, None)]:
        raise RuntimeError(f"recipe {RECIPE_ID} skipped no-op nodes changed: {skipped}")
    lookup_input = _input(actions[0])
    if lookup_input.get("email") != LOOKUP_EMAIL_PILL:
        raise RuntimeError(f"recipe {RECIPE_ID} lookup email pill changed: {lookup_input}")
    accumulate_input = _input(actions[1])
    if str(accumulate_input.get("name") or "") != "Results":
        raise RuntimeError(f"recipe {RECIPE_ID} accumulate list name changed")
    data = (accumulate_input.get("list_item") or {}).get("data")
    if data != ACCUMULATE_DATA:
        raise RuntimeError(f"recipe {RECIPE_ID} accumulate mapping changed: {data}")
    return_input = _input(actions[2])
    if (return_input.get("result") or {}).get("Users") != RETURN_USERS_MAPPING:
        raise RuntimeError(f"recipe {RECIPE_ID} return_result Users mapping changed: {return_input}")
    foreachs = _collect_keyword(raw, "foreach")
    if (
        len(foreachs) != 1
        or foreachs[0].get("as") != "b0c1c7a4"
        or foreachs[0].get("repeat_mode") != "simple"
        or _input(foreachs[0]).get("source") != FOREACH_SOURCE
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} foreach changed")
    ifs = {node.get("number"): _single_condition(node) for node in _collect_keyword(raw, "if")}
    if sorted(ifs) != [4, 7]:
        raise RuntimeError(f"recipe {RECIPE_ID} IF steps changed: {sorted(ifs)}")
    if ifs[4] != (IF4_LHS, "not_contains", "scale"):
        raise RuntimeError(f"recipe {RECIPE_ID} IF4 changed: {ifs[4]}")
    if ifs[7] != (IF7_LHS, "present", ""):
        raise RuntimeError(f"recipe {RECIPE_ID} IF7 changed: {ifs[7]}")
    catches = _collect_keyword(raw, "catch")
    if (
        len(catches) != 1
        or catches[0].get("as") != "a4978a61"
        or str(_input(catches[0]).get("max_retry_count") or "") != "0"
        or str(_input(catches[0]).get("retry_interval") or "") != "2"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} catch block changed")
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


def seed_92629971(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_92629971(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger(trigger)
    expect = data.get("expect")
    if not isinstance(expect, dict) or not isinstance(expect.get("result"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must declare expect.result "
            "(the exact recipe-function return value)"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    seed_in = data.get("seed")
    if isinstance(seed_in, dict):
        for key, value in seed_in.items():
            if isinstance(value, dict):
                out[str(key)] = deepcopy(value)
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    return attach_variant(out, ctx)


def run_92629971(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_92629971(raw)
    trigger = seed.get("trigger")
    if not isinstance(trigger, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing trigger object")
    _require_trigger(trigger)
    expect = seed.get("expect") if isinstance(seed.get("expect"), dict) else {}
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": trigger,
            "track": seed.get("track"),
            "expect": expect,
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_92629971(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger(trigger: dict[str, Any]) -> None:
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input requires a parameters object")
    users = parameters.get("Users")
    if not isinstance(users, list) or not users:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters.Users must be a non-empty list")
    for user in users:
        if not isinstance(user, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} parameters.Users items must be objects")
        if not str(user.get("email") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} parameters.Users item requires a non-empty email")
        if not str(user.get("name") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} parameters.Users item requires a non-empty name "
                "(IF4 dereferences name.downcase)"
            )
        if not isinstance(user.get("placeholder_title"), str):
            raise RuntimeError(
                f"recipe {RECIPE_ID} parameters.Users item requires a string placeholder_title"
            )


def _collect_keyword(node: dict[str, Any], keyword: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == keyword and not child.get("skip"):
            found.append(child)
        found.extend(_collect_keyword(child, keyword))
    return found


def _collect_skipped_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and child.get("skip"):
            found.append(child)
        found.extend(_collect_skipped_actions(child))
    return found


def _input(node: dict[str, Any]) -> dict[str, Any]:
    value = node.get("input")
    return value if isinstance(value, dict) else {}


def _single_condition(node: dict[str, Any]) -> tuple[str, str, str]:
    conditions = _input(node).get("conditions")
    if not isinstance(conditions, list) or len(conditions) != 1 or not isinstance(conditions[0], dict):
        raise RuntimeError(f"recipe {RECIPE_ID} IF step {node.get('number')} is not a single condition")
    condition = conditions[0]
    return (
        str(condition.get("lhs") or ""),
        str(condition.get("operand") or ""),
        str(condition.get("rhs") or ""),
    )


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
