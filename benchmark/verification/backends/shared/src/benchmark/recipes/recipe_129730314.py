from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_129730314


RECIPE_ID = "129730314"
SEED_TYPE = "dynamic_client_store_api_variant"
TRACK = "workato_api_platform_client_store"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "11cb6620"
# API Platform "dynamic client store" endpoint (twin pair 129730314/129750406;
# raw bodies identical except table_id 53976 vs 54016). Request
# {action, client_name, client_id?}. TRY: get_records (table 53976,
# filter client_name eq request.client_name, limit 100, order desc) ->
# IF action=='register' [IF size>0 -> STOP 'Client name must be unique'
# (step 6); add_record client_name/client_id; return 200 {success:true}
# (terminal)] -> IF action=='fetch' [IF size==0 -> STOP 'Client not found'
# (step 11); return 200 {client_id: first record, success:true} (terminal)]
# -> STOP 'Unsupported action' (step 13; reachable ONLY via a third action
# value because both success returns are terminal). CATCH -> return 200
# {success:false}. Stop trace rows drop stop_reason/stop_with_error, so
# verification pins stops by step number/as, never by text (the reasons are
# still pinned at validate time via EXPECTED_CONTROL_FLOW).
TABLE_ID = "53976"
REQUIRED_TRIGGER_REQUEST_FIELDS = ("action", "client_name")
EXPECTED_ACTIONS: list[tuple[str, str]] = [   ('workato_db_table', 'get_records'),
    ('workato_db_table', 'add_record'),
    ('workato_api_platform', 'return_response'),
    ('workato_api_platform', 'return_response'),
    ('workato_api_platform', 'return_response')]
EXPECTED_ACTION_AS: list[str] = ['6cb62163', '75d18405', '0eeb331e', '26ba6eda', '5fa4b7cb']
EXPECTED_CONTROL_FLOW: list[dict[str, Any]] = [   {'input': {}, 'keyword': 'try', 'number': 2},
    {   'input': {   'conditions': [   {   'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"11cb6620","path":["request", '
                                                  '"action"]}\')}',
                                           'operand': 'equals_to',
                                           'rhs': 'register'}],
                     'operand': 'and',
                     'type': 'compound'},
        'keyword': 'if',
        'number': 4},
    {   'input': {   'conditions': [   {   'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"6cb62163","path":["records", '
                                                  '{"path_element_type": "size"}]}\')}',
                                           'operand': 'greater_than',
                                           'rhs': '0'}],
                     'operand': 'and',
                     'type': 'compound'},
        'keyword': 'if',
        'number': 5},
    {   'input': {'stop_reason': 'Client name must be unique', 'stop_with_error': 'true'},
        'keyword': 'stop',
        'number': 6},
    {   'input': {   'conditions': [   {   'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"11cb6620","path":["request", '
                                                  '"action"]}\')}',
                                           'operand': 'equals_to',
                                           'rhs': 'fetch'}],
                     'operand': 'and',
                     'type': 'compound'},
        'keyword': 'if',
        'number': 9},
    {   'input': {   'conditions': [   {   'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"6cb62163","path":["records", '
                                                  '{"path_element_type": "size"}]}\')}',
                                           'operand': 'equals_to',
                                           'rhs': '0'}],
                     'operand': 'and',
                     'type': 'compound'},
        'keyword': 'if',
        'number': 10},
    {   'input': {'stop_reason': 'Client not found', 'stop_with_error': 'true'},
        'keyword': 'stop',
        'number': 11},
    {   'input': {'stop_reason': 'Unsupported action', 'stop_with_error': 'true'},
        'keyword': 'stop',
        'number': 13},
    {'input': {'max_retry_count': '0', 'retry_interval': '2'}, 'keyword': 'catch', 'number': 14}]
# Raw trigger + per-action inputs pinned verbatim from
# dataset/input_recipes/129730314/raw_recipe.md (key formulas: the client_name eq filter
# pill, the add_record request pills, the fetch response current_item pill
# and the three return_response bodies). Any drift raises at validate time.
PINNED_TRIGGER_INPUT: dict[str, Any] = {   'request': {   'content_type': 'json',
                   'schema': '[{"control_type":"text","label":"Action","type":"string","name":"action"},{"control_type":"text","label":"Client '
                             'name","type":"string","name":"client_name"},{"control_type":"text","label":"Client '
                             'ID","type":"string","name":"client_id","optional":true}]'},
    'response': {   'content_type': 'json',
                    'responses': [   {   'body_schema': '[{"name":"success","type":"boolean","optional":false,"control_type":"checkbox","label":"Success","render_input":"boolean_conversion","parse_output":"boolean_conversion","toggle_hint":"Select '
                                                        'from option '
                                                        'list","toggle_field":{"label":"Success","control_type":"text","toggle_hint":"Use '
                                                        'custom '
                                                        'value","name":"success","type":"boolean","optional":false}},{"name":"client_id","type":"string","optional":true,"control_type":"text","label":"Client '
                                                        'ID"}]',
                                         'http_status_code': '200',
                                         'name': 'Success'}]}}
PINNED_ACTION_INPUTS: list[dict[str, Any]] = [   {   '11fbe9a6-a16d-4d7e-86ea-afe42ec03005': 'id',
        '1565526c-78e5-4dab-9699-390d2c0d185a': 'string',
        '61aae604-a95e-4519-9091-bb0bf754a67f': 'date_time',
        'a31f17ea-5e4f-4cc6-a471-6c316d52f301': 'string',
        'a5612739-5401-4ae7-bd07-782c1a6fb2d1': 'date_time',
        'filters': [   {   'field_id': '1565526c-78e5-4dab-9699-390d2c0d185a',
                           'op_default': 'eq',
                           'value_default': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"11cb6620","path":["request", '
                                            '"client_name"]}\')}'}],
        'limit': '100',
        'order_direction': 'desc',
        'table_id': '53976'},
    {   'parameters': {   '1565526c_78e5_4dab_9699_390d2c0d185a': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"11cb6620","path":["request", '
                                                                  '"client_name"]}\')}',
                          'a31f17ea_5e4f_4cc6_a471_6c316d52f301': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"11cb6620","path":["request", '
                                                                  '"client_id"]}\')}'},
        'table_id': '53976'},
    {'http_status_code': '200', 'response': {'success': 'true'}},
    {   'http_status_code': '200',
        'response': {   'client_id': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"6cb62163","path":["records", '
                                     '{"path_element_type": "current_item"}, '
                                     '"a31f17ea_5e4f_4cc6_a471_6c316d52f301"]}\')}',
                        'success': 'true'}},
    {'http_status_code': '200', 'response': {'success': 'false'}}]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.add_record",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.add_record",
    "workato_api_platform.return_response",
]


def validate_129730314(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger 'as' changed: {raw.get('as')!r}")
    if raw.get("input") != PINNED_TRIGGER_INPUT:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger request/response schema drifted")
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
    for idx in (0, 1):
        if actions[idx].get("input", {}).get("table_id") != TABLE_ID:
            raise RuntimeError(
                f"recipe {RECIPE_ID} workato_db_table id changed at action index {idx}"
            )
    control = _collect_control(raw)
    actual_control = [
        {"keyword": node.get("keyword"), "number": node.get("number"), "input": node.get("input")}
        for node in control
    ]
    if actual_control != EXPECTED_CONTROL_FLOW:
        raise RuntimeError(f"recipe {RECIPE_ID} control flow drifted: {actual_control}")
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


def seed_129730314(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_129730314(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_fields(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    tables_section = seed_in.get("workato_db_table")
    if not isinstance(tables_section, dict) or not isinstance(tables_section.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed.workato_db_table.tables")
    if TABLE_ID not in tables_section["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must explicitly include client-store table {TABLE_ID}"
        )
    if not isinstance(data.get("expect"), dict) or not data["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect block")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "raw_validation": validation,
        "harness_tool_calls": ctx.tools.call_log(),
        "expect": deepcopy(data["expect"]),
    }
    for key, value in seed_in.items():
        if isinstance(value, dict):
            out[str(key)] = deepcopy(value)
    if data.get("now") not in (None, ""):
        out["now"] = data["now"]
    for key in ("force_action_error", "job_context"):
        if isinstance(data.get(key), dict):
            out[key] = deepcopy(data[key])
    return attach_variant(out, ctx)


def run_129730314(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_129730314(raw)
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
    result["verifier"] = verify_129730314(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_fields(trigger: dict[str, Any]) -> None:
    request = trigger.get("request") if isinstance(trigger.get("request"), dict) else {}
    for field in REQUIRED_TRIGGER_REQUEST_FIELDS:
        if request.get(field) in (None, ""):
            raise RuntimeError(f"recipe {RECIPE_ID} trigger_input must pin request.{field}")
    if request.get("action") == "register" and request.get("client_id") in (None, ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} register variants must pin request.client_id "
            "(the add_record step dereferences it)"
        )


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
    keywords = {"if", "elsif", "else", "try", "repeat", "while_condition", "catch", "foreach", "stop"}
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") in keywords:
            found.append(child)
        found.extend(_collect_control(child))
    return found


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("workato_db_table"), dict):
        out.update(ctx.tools.call("harness.workato_db_table.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
