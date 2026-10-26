from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_109890664


RECIPE_ID = "109890664"
SEED_TYPE = "workspace_packages_api_variant"
TRACK = "workato_api_platform_packages"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "b28165b1"
OUTER_TABLE_ID = "8057"
INNER_TABLE_ID = "8054"
REQUIRED_TRIGGER_REQUEST_FIELDS = ("workspace_user_id",)
EXPECTED_ACTIONS: list[tuple[str, str]] = [   ('workato_db_table', 'get_records'),
    ('workato_api_platform', 'return_response'),
    ('workato_variable', 'declare_list'),
    ('workato_variable', 'declare_variable'),
    ('workato_db_table', 'get_records'),
    ('workato_variable', 'update_variables'),
    ('workato_variable', 'insert_to_list_batch'),
    ('workato_api_platform', 'return_response'),
    ('workato_api_platform', 'return_response')]
EXPECTED_ACTION_AS: list[str] = [   '1f36ef26',
    '0cb42b47',
    'd796a274',
    'ad997700',
    'd8235bcc',
    'a08c0bf9',
    'f7efec55',
    '1e9842ed',
    'e12dfb76']
EXPECTED_CONTROL_FLOW: list[dict[str, Any]] = [   {   'input': {   'conditions': [   {   'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"1f36ef26","path":["records", '
                                                  '{"path_element_type": "size"}]}\')}',
                                           'operand': 'equals_to',
                                           'rhs': '0'}],
                     'operand': 'and',
                     'type': 'compound'},
        'keyword': 'if',
        'number': 3},
    {'input': {}, 'keyword': 'try', 'number': 5},
    {'input': {}, 'keyword': 'repeat', 'number': 8},
    {   'input': {   'conditions': [   {   'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"d8235bcc","path":["records", '
                                                  '{"path_element_type": "size"}]}\')}',
                                           'operand': 'greater_than',
                                           'rhs': '0'}],
                     'operand': 'and',
                     'type': 'compound'},
        'keyword': 'if',
        'number': 11},
    {   'input': {   'conditions': [   {   'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"ad997700","path":["page_token"]}\')}',
                                           'operand': 'present',
                                           'rhs': ''}],
                     'operand': 'and',
                     'type': 'compound'},
        'keyword': 'while_condition',
        'number': 13},
    {'input': {'max_retry_count': '0', 'retry_interval': '2'}, 'keyword': 'catch', 'number': 15}]
PINNED_TRIGGER_INPUT: dict[str, Any] = {   'request': {   'content_type': 'json',
                   'schema': '[{"name":"workspace_user_id","type":"integer","optional":false,"control_type":"integer","label":"Workspace '
                             'user ID","parse_output":"integer_conversion"}]'},
    'response': {   'content_type': 'json',
                    'responses': [   {   'body_schema': '[{"name":"packages","type":"array","optional":false,"properties":[{"name":"id","type":"string","optional":false,"control_type":"text","label":"ID"},{"name":"description","type":"string","optional":false,"control_type":"text","label":"Description"},{"name":"name","type":"string","optional":false,"control_type":"text","label":"Name"}],"of":"object","label":"Packages"}]',
                                         'http_status_code': '200',
                                         'name': 'Success'},
                                     {   'body_schema': '[{"name":"error","type":"string","optional":false,"control_type":"text","label":"Error"}]',
                                         'http_status_code': '400',
                                         'name': 'Failed'},
                                     {'http_status_code': '401', 'name': 'Unauthorized'}]}}
PINNED_ACTION_INPUTS: list[dict[str, Any]] = [   {   '11fbe9a6-a16d-4d7e-86ea-afe42ec03005': 'id',
        '25f333bd-9f2c-483e-a4d3-d9ee9f7fca8e': 'string',
        '27bdf527-6657-412d-a106-293c28940a44': 'boolean',
        '61aae604-a95e-4519-9091-bb0bf754a67f': 'date_time',
        '73fd1e82-f4d2-48a9-8ff2-96713f5acd63': 'boolean',
        '9d00233f-dc89-4f40-b0f4-c2b6ee765ed2': 'string',
        'a5612739-5401-4ae7-bd07-782c1a6fb2d1': 'date_time',
        'e12c33da-6a37-4ecd-86e1-9cb2dafd0787': 'string',
        'e417aefa-9690-4edd-83c5-8e3f8749fc24': 'string',
        'filters': [   {   'field_id': 'e417aefa-9690-4edd-83c5-8e3f8749fc24',
                           'op_default': 'eq',
                           'value_default': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"b28165b1","path":["context", '
                                            '"access_profile", "id"]}\')}'},
                       {   'field_id': '9d00233f-dc89-4f40-b0f4-c2b6ee765ed2',
                           'op_default': 'eq',
                           'value_default': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"b28165b1","path":["request", '
                                            '"workspace_user_id"]}\')}'},
                       {   'field_id': '73fd1e82-f4d2-48a9-8ff2-96713f5acd63',
                           'op_boolean': 'istrue'}],
        'limit': '200',
        'order_direction': 'asc',
        'table_id': '8057'},
    {'http_status_code': '401'},
    {   'list_item_schema_json': '[{"control_type":"text","label":"ID","name":"id","type":"string","optional":false},{"control_type":"text","label":"Description","name":"description","type":"string","optional":false},{"control_type":"text","label":"Name","name":"name","type":"string","optional":false}]',
        'name': 'packages'},
    {   'variables': {   'schema': '[{"name":"page_token","type":"string","optional":true,"label":"page_token","details":{"real_name":"page_token"},"control_type":"text"}]'}},
    {   '11fbe9a6-a16d-4d7e-86ea-afe42ec03005': 'id',
        '1d79e1c5-1f18-4692-8e8f-37f5fd558263': 'string',
        '2304597f-d05e-42e9-a49b-cf7599cfb9a3': 'string',
        '23d307d8-98be-4370-b3e5-32c94998aaae': 'boolean',
        '254554f8-92ee-4136-8d3e-a3feef27048f': 'string',
        '61aae604-a95e-4519-9091-bb0bf754a67f': 'date_time',
        '70e1e7d7-558d-4557-bd90-0e34b5c2cef3': 'date_time',
        '775508d3-5890-4c28-86ac-27ae118d1ada': 'string',
        'a5612739-5401-4ae7-bd07-782c1a6fb2d1': 'date_time',
        'ba3cc272-0838-4c9f-9959-b6ecce82762d': 'string',
        'c67721ea-02de-47fe-9d83-9f2f042171fd': 'relation',
        'continuation_token': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"ad997700","path":["page_token"]}\')}',
        'd266a7d5-d157-4e50-8ec6-3f584414197b': 'relation',
        'd8f3f531-4791-4532-a891-807d2b21c901': 'relation',
        'fad0fcc9-3538-4d02-b38d-407bdfbf14a7': 'boolean',
        'filters': [{'field_id': 'fad0fcc9-3538-4d02-b38d-407bdfbf14a7', 'op_boolean': 'isfalse'}],
        'limit': '200',
        'order_direction': 'asc',
        'table_id': '8054'},
    {   'name': 'd5c7e83d-0b3d-41eb-9327-3f4199b9eec6:ad997700:page_token',
        'page_token': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"d8235bcc","path":["continuation_token"]}\')}'},
    {   'list_items': {   '____source': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"d8235bcc","path":["records"]}\')}',
                          'description': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"d8235bcc","path":["records", '
                                         '{"path_element_type": "current_item"}, '
                                         '"2304597f_d05e_42e9_a49b_cf7599cfb9a3"]}\')}',
                          'id': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"d8235bcc","path":["records", '
                                '{"path_element_type": "current_item"}, '
                                '"11fbe9a6_a16d_4d7e_86ea_afe42ec03005"]}\')}',
                          'name': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"d8235bcc","path":["records", '
                                  '{"path_element_type": "current_item"}, '
                                  '"775508d3_5890_4c28_86ac_27ae118d1ada"]}\')}'},
        'location': 'end',
        'name': '3b774789-06ba-4b12-bde1-1690c776b034:d796a274'},
    {   'http_status_code': '200',
        'response': {   'packages': {   '____source': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"d796a274","path":["list_items"]}\')}',
                                        'description': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"d796a274","path":["list_items", '
                                                       '{"path_element_type": "current_item"}, '
                                                       '"description"]}\')}',
                                        'id': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"d796a274","path":["list_items", '
                                              '{"path_element_type": "current_item"}, "id"]}\')}',
                                        'name': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"d796a274","path":["list_items", '
                                                '{"path_element_type": "current_item"}, '
                                                '"name"]}\')}'}}},
    {'http_status_code': '400', 'response': {'error': 'Unexpected Error'}}]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_api_platform.return_response",
    "workato_runtime.declare_list",
    "workato_runtime.declare_variable",
    "workato_runtime.update_variables",
    "workato_runtime.insert_to_list_batch",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_api_platform.return_response",
    "workato_runtime.declare_list",
    "workato_runtime.declare_variable",
    "workato_runtime.update_variables",
    "workato_runtime.insert_to_list_batch",
]


def validate_109890664(raw: dict[str, Any]) -> dict[str, Any]:
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
    if actions[0].get("input", {}).get("table_id") != OUTER_TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} outer workato_db_table changed")
    if actions[4].get("input", {}).get("table_id") != INNER_TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} inner workato_db_table changed")
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


def seed_109890664(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_109890664(raw)
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
    if OUTER_TABLE_ID not in tables_section["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must explicitly include auth table {OUTER_TABLE_ID}"
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


def run_109890664(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_109890664(raw)
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
    result["verifier"] = verify_109890664(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_fields(trigger: dict[str, Any]) -> None:
    context = trigger.get("context") if isinstance(trigger.get("context"), dict) else {}
    profile = context.get("access_profile") if isinstance(context.get("access_profile"), dict) else {}
    if profile.get("id") in (None, ""):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must pin context.access_profile.id "
            "(the auth-table filter dereferences it)"
        )
    request = trigger.get("request") if isinstance(trigger.get("request"), dict) else {}
    for field in REQUIRED_TRIGGER_REQUEST_FIELDS:
        if request.get(field) in (None, ""):
            raise RuntimeError(f"recipe {RECIPE_ID} trigger_input must pin request.{field}")


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
