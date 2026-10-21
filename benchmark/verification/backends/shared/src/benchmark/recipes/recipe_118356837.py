from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_118356837


RECIPE_ID = "118356837"
SEED_TYPE = "recipe_function_comma_split_typed_reply_variant"
TRACK = "workato_recipe_function_comma_split_typed_reply"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "0dc619ef"
FOREACH_AS = "140b9c9f"
FOREACH_REPEAT_MODE = "simple"
BLANK_STOP_STEP_NUMBER = 5
# Callable recipe function (trigger as 0dc619ef; parameters.String, a
# comma-separated string). The recipe replies through
# workato_service.send_reply (it never calls return_result):
#   declare_list 'Output List' (step 2, as 9e860062)
#   IF3 parameters.String blank:
#     send_reply success (step 4, as f6e6ea72; List ____source-mapped from the
#       still-empty Output List -> reply {"List": []})
#     STOP 5 (graceful, stop_with_error=false)
#   declare_variable (step 6, as e4f0eb26): Array = String.strip.split(","),
#     is_array_of_strings = "false"
#   workato_list.create_list (step 7, as 78454755) size = Array.length
#     (iteration scaffold)
#   FOREACH (step 8, as 140b9c9f, repeat_mode=simple) over the created list:
#     IF9 (Array[foreach index]).to_i not_equals_to Array[foreach index]:
#       update is_array_of_strings = "true" (step 10, as b88c6a70)
#       [harness equals_to/not_equals_to is str(lhs)==str(rhs), so per item:
#        '1'.to_i=1 vs '1' -> '1'=='1' equal (stays integer classification);
#        'abc'.to_i=0 vs 'abc' -> differ (string); ' 3'.to_i=3 vs ' 3' ->
#        '3' != ' 3' differ (string). Deterministic and pinned per variant.]
#     insert_to_list Output List Value = Array[foreach index].strip
#       (step 11, as 5c761018)
#   IF12 is_array_of_strings is_true:
#     send_reply success (step 13, as 19475c1e; string Values)
#     logger.log_message list_items.to_json (step 14, as 74a60038)
#   ELSE (step 15):
#     send_reply success (step 16, as 13747cc2; Value = .to_i integers)
#     logger.log_message '[{"Value": ' + pluck join (step 17, as 928c42be)
# No external backend at all: workato_service replies, workato variables/lists
# and the loggers are deterministic Workato-internal mocks (mock-only recipe
# per the backend policy). The captured send_reply is the observable output.
PINNED_TRIGGER_INPUT = {   'parameters_schema_json': '[{"control_type":"text","label":"String","name":"String","type":"string","optional":false,"hint":"Comma '
                              'Separated String"}]',
    'result_schema_json': '[{"name":"List","type":"array","of":"object","label":"List","optional":false,"properties":[{"control_type":"text","label":"Value","name":"Value","type":"string","optional":false}]}]'}
EXPECTED_ACTIONS: list = [   ('workato_variable', 'declare_list'),
    ('workato_service', 'send_reply'),
    ('workato_variable', 'declare_variable'),
    ('workato_list', 'create_list'),
    ('workato_variable', 'update_variables'),
    ('workato_variable', 'insert_to_list'),
    ('workato_service', 'send_reply'),
    ('logger', 'log_message'),
    ('workato_service', 'send_reply'),
    ('logger', 'log_message')]
EXPECTED_ACTION_AS: list = [   '9e860062',
    'f6e6ea72',
    'e4f0eb26',
    '78454755',
    'b88c6a70',
    '5c761018',
    '19475c1e',
    '74a60038',
    '13747cc2',
    '928c42be']
PINNED_ACTION_INPUTS: list = [   {   'list_item_schema_json': '[{"name":"Value","type":"string","optional":false,"control_type":"text"}]',
        'name': 'Output List'},
    {   'reply': {   'List': {   'Value': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"9e860062","path":["list_items", '
                                          '{"path_element_type": '
                                          '"current_item"}, "Value"]}\')}',
                                 '____source': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"9e860062","path":["list_items"]}\')}'}},
        'reply_type': 'success'},
    {   'variables': {   'data': {   'Array': '=_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"0dc619ef","path":["parameters","String"]}\').strip.split(",")',
                                     'is_array_of_strings': 'false'},
                         'schema': '[{"control_type":"text","label":"Array","name":"Array","type":"string","optional":true,"details":{"real_name":"Array"},"parent":["variables","data"],"hint":"Defaults '
                                   'to nil if not '
                                   'supplied.","sticky":true},{"name":"is_array_of_strings","type":"boolean","optional":true,"label":"Is '
                                   'Array of '
                                   'Strings?","details":{"real_name":"Is Array '
                                   'of '
                                   'Strings?"},"control_type":"checkbox","parent":["variables","data"]}]'}},
    {   'size': '=_dp(\'{"pill_type":"output","provider":"workato_variable","line":"e4f0eb26","path":["Array"]}\').length'},
    {   'is_array_of_strings': 'true',
        'name': '5ff4cbbd-d784-45f9-83bd-3ce68f49a6fd:e4f0eb26:is_array_of_strings'},
    {   'list_item': {   'Value': '=_dp(\'{"pill_type":"output","provider":"workato_variable","line":"e4f0eb26","path":["Array"]}\')[_dp(\'{"pill_type":"foreach_meta","provider":"foreach","line":"140b9c9f","key":"index"}\')].strip'},
        'location': 'end',
        'name': '623cf12e-35b7-4c8c-af32-34a5b84892ac:9e860062'},
    {   'reply': {   'List': {   'Value': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"9e860062","path":["list_items", '
                                          '{"path_element_type": '
                                          '"current_item"}, "Value"]}\')}',
                                 '____source': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"9e860062","path":["list_items"]}\')}'}},
        'reply_type': 'success'},
    {   'message': '=_dp(\'{"pill_type":"output","provider":"workato_variable","line":"9e860062","path":["list_items"]}\').to_json',
        'user_logs_enabled': 'false'},
    {   'reply': {   'List': {   'Value': '=_dp(\'{"pill_type":"output","provider":"workato_variable","line":"9e860062","path":["list_items",{"path_element_type":"current_item"},"Value"]}\').to_i',
                                 '____source': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"9e860062","path":["list_items"]}\')}'}},
        'reply_type': 'success'},
    {   'message': '=\'[{"Value": \' + '
                   '_dp(\'{"pill_type":"output","provider":"workato_variable","line":"9e860062","path":["list_items"]}\').pluck(\'Value\').join(\'}, '
                   '{"Value": \') + \'}]\'',
        'user_logs_enabled': 'false'}]
EXPECTED_CONTROL_FLOW: list = [   {   'input': {   'conditions': [   {   'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_recipe_function","line":"0dc619ef","path":["parameters", '
                                                  '"String"]}\')}',
                                           'operand': 'blank'}],
                     'operand': 'and',
                     'type': 'compound'},
        'keyword': 'if',
        'number': 3},
    {'input': {'stop_with_error': 'false'}, 'keyword': 'stop', 'number': 5},
    {   'input': {   'source': '#{_dp(\'{"pill_type":"output","provider":"workato_list","line":"78454755","path":["list"]}\')}'},
        'keyword': 'foreach',
        'number': 8},
    {   'input': {   'conditions': [   {   'lhs': '=(_dp(\'{"pill_type":"output","provider":"workato_variable","line":"e4f0eb26","path":["Array"]}\')[_dp(\'{"pill_type":"foreach_meta","provider":"foreach","line":"140b9c9f","key":"index"}\')]).to_i',
                                           'operand': 'not_equals_to',
                                           'rhs': '=_dp(\'{"pill_type":"output","provider":"workato_variable","line":"e4f0eb26","path":["Array"]}\')[_dp(\'{"pill_type":"foreach_meta","provider":"foreach","line":"140b9c9f","key":"index"}\')]'}],
                     'operand': 'and',
                     'type': 'compound'},
        'keyword': 'if',
        'number': 9},
    {   'input': {   'conditions': [   {   'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"e4f0eb26","path":["is_array_of_strings"]}\')}',
                                           'operand': 'is_true'}],
                     'operand': 'and',
                     'type': 'compound'},
        'keyword': 'if',
        'number': 12},
    {'input': {}, 'keyword': 'else', 'number': 15}]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_list",
    "workato_service.send_reply",
    "workato_runtime.declare_variable",
    "workato_runtime.create_list",
    "workato_runtime.update_variables",
    "workato_runtime.insert_to_list",
    "workato_runtime.log_message",
]
ALLOWED_TOOLS: list[str] = [
    "workato_service.send_reply",
]
CONTROL_KEYWORDS = {"if", "elsif", "else", "try", "repeat", "while_condition", "catch", "foreach", "stop"}


def validate_118356837(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger 'as' changed: {raw.get('as')!r}")
    if raw.get("input") != PINNED_TRIGGER_INPUT:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter/result schema drifted")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
    actual_as = [action.get("as") for action in actions]
    if actual_as != EXPECTED_ACTION_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} action step ids changed: {actual_as}")
    for idx, action in enumerate(actions):
        if action.get("input") != PINNED_ACTION_INPUTS[idx]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} raw formula drift at action index {idx} "
                f"(step {action.get('number')}, as {action.get('as')!r})"
            )
    control = _collect_control(raw)
    actual_control = [
        {"keyword": node.get("keyword"), "number": node.get("number"), "input": node.get("input")}
        for node in control
    ]
    if actual_control != EXPECTED_CONTROL_FLOW:
        raise RuntimeError(f"recipe {RECIPE_ID} control flow drifted: {actual_control}")
    foreachs = [node for node in control if node.get("keyword") == "foreach"]
    if len(foreachs) != 1 or foreachs[0].get("as") != FOREACH_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} foreach step changed")
    if foreachs[0].get("repeat_mode") != FOREACH_REPEAT_MODE:
        raise RuntimeError(
            f"recipe {RECIPE_ID} foreach repeat_mode changed: {foreachs[0].get('repeat_mode')!r}"
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


def seed_118356837(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118356837(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input requires a parameters object")
    if "String" not in parameters or not isinstance(parameters.get("String"), str):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger input requires an explicit string parameters.String "
            "(the empty string is a valid blank-branch input)"
        )
    if not isinstance(data.get("expect"), dict) or not data["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect block")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "harness_tool_calls": ctx.tools.call_log(),
        "expect": deepcopy(data["expect"]),
    }
    seed_in = data.get("seed")
    if isinstance(seed_in, dict):
        for key, value in seed_in.items():
            if isinstance(value, dict):
                out[str(key)] = deepcopy(value)
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    for key in ("force_action_error", "job_context"):
        if isinstance(data.get(key), dict):
            out[key] = deepcopy(data[key])
    return attach_variant(out, ctx)


def run_118356837(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118356837(raw)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
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
            "initial_snapshot": {},
            "final_snapshot": {},
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_118356837(result)
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


def _collect_control(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") in CONTROL_KEYWORDS:
            found.append(child)
        found.extend(_collect_control(child))
    return found


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
