from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_109892683


RECIPE_ID = "109892683"
SEED_TYPE = "workspace_package_versions_api_variant"
TRACK = "workato_api_platform_package_versions"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "b28165b1"
AUTH_TABLE_ID = "9009"
PACKAGES_TABLE_ID = "9006"
INSTALLS_TABLE_ID = "9008"
VERSIONS_TABLE_ID = "9005"
REQUIRED_TRIGGER_REQUEST_FIELDS = ("workspace_user_id", "package_id",)
EXPECTED_ACTIONS: list[tuple[str, str]] = [   ('workato_db_table', 'get_records'),
    ('workato_api_platform', 'return_response'),
    ('workato_db_table', 'get_records'),
    ('workato_api_platform', 'return_response'),
    ('workato_db_table', 'get_records'),
    ('workato_variable', 'declare_list'),
    ('workato_variable', 'declare_variable'),
    ('workato_db_table', 'get_records'),
    ('workato_variable', 'update_variables'),
    ('workato_variable', 'insert_to_list_batch'),
    ('workato_api_platform', 'return_response'),
    ('workato_api_platform', 'return_response')]
EXPECTED_ACTION_AS: list[str] = [   'da3cfd40',
    '287c4d0c',
    '7b377962',
    'b0c92c3a',
    '81d4b97f',
    '0b2120cf',
    '67b62be6',
    '17e72b35',
    'ba7fec45',
    '51dbe38d',
    '0725ea23',
    '13d04040']
EXPECTED_CONTROL_FLOW: list[dict[str, Any]] = [   {   'input': {   'conditions': [   {   'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"da3cfd40","path":["records", '
                                                  '{"path_element_type": "size"}]}\')}',
                                           'operand': 'equals_to',
                                           'rhs': '0'}],
                     'operand': 'and',
                     'type': 'compound'},
        'keyword': 'if',
        'number': 3},
    {'input': {}, 'keyword': 'try', 'number': 5},
    {   'input': {   'conditions': [   {   'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"7b377962","path":["records", '
                                                  '{"path_element_type": "current_item"}, '
                                                  '"fad0fcc9_3538_4d02_b38d_407bdfbf14a7"]}\')}',
                                           'operand': 'is_true',
                                           'rhs': ''}],
                     'operand': 'and',
                     'type': 'compound'},
        'keyword': 'if',
        'number': 7},
    {'input': {}, 'keyword': 'repeat', 'number': 12},
    {   'input': {   'conditions': [   {   'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"17e72b35","path":["records", '
                                                  '{"path_element_type": "size"}]}\')}',
                                           'operand': 'greater_than',
                                           'rhs': '0'}],
                     'operand': 'and',
                     'type': 'compound'},
        'keyword': 'if',
        'number': 15},
    {   'input': {   'conditions': [   {   'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"67b62be6","path":["page_token"]}\')}',
                                           'operand': 'present',
                                           'rhs': ''}],
                     'operand': 'and',
                     'type': 'compound'},
        'keyword': 'while_condition',
        'number': 17},
    {'input': {'max_retry_count': '0', 'retry_interval': '2'}, 'keyword': 'catch', 'number': 19}]
PINNED_TRIGGER_INPUT: dict[str, Any] = {   'request': {   'content_type': 'json',
                   'schema': '[{"name":"workspace_user_id","type":"integer","optional":false,"control_type":"integer","label":"Workspace '
                             'user '
                             'ID","parse_output":"integer_conversion"},{"name":"package_id","type":"string","optional":false,"control_type":"text","label":"Package '
                             'ID"}]'},
    'response': {   'content_type': 'json',
                    'responses': [   {   'body_schema': '[{"name":"versions","type":"array","of":"object","label":"Versions","optional":false,"properties":[{"control_type":"text","label":"Version '
                                                        'ID","name":"id","type":"string","optional":false},{"control_type":"text","label":"Description","name":"description","type":"string","optional":false},{"control_type":"text","label":"Name","name":"name","type":"string","optional":false}]}]',
                                         'http_status_code': '200',
                                         'name': 'Success'},
                                     {   'body_schema': '[{"name":"error","type":"string","optional":false,"control_type":"text","label":"Error"}]',
                                         'http_status_code': '400',
                                         'name': 'Failed'},
                                     {'http_status_code': '401', 'name': 'Unauthorized'}]}}
PINNED_ACTION_INPUTS: list[dict[str, Any]] = [   {   '11fbe9a6-a16d-4d7e-86ea-afe42ec03005': 'id',
        '25f333bd-9f2c-483e-a4d3-d9ee9f7fca8e': 'string',
        '61aae604-a95e-4519-9091-bb0bf754a67f': 'date_time',
        '73fd1e82-f4d2-48a9-8ff2-96713f5acd63': 'boolean',
        '9d00233f-dc89-4f40-b0f4-c2b6ee765ed2': 'string',
        'a5612739-5401-4ae7-bd07-782c1a6fb2d1': 'date_time',
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
        'limit': '100',
        'order_direction': 'asc',
        'table_id': '9009'},
    {'http_status_code': '401'},
    {   '11fbe9a6-a16d-4d7e-86ea-afe42ec03005': 'id',
        '2304597f-d05e-42e9-a49b-cf7599cfb9a3': 'string',
        '23d307d8-98be-4370-b3e5-32c94998aaae': 'boolean',
        '254554f8-92ee-4136-8d3e-a3feef27048f': 'string',
        '61aae604-a95e-4519-9091-bb0bf754a67f': 'date_time',
        '775508d3-5890-4c28-86ac-27ae118d1ada': 'string',
        'a5612739-5401-4ae7-bd07-782c1a6fb2d1': 'date_time',
        'ba3cc272-0838-4c9f-9959-b6ecce82762d': 'string',
        'c67721ea-02de-47fe-9d83-9f2f042171fd': 'relation',
        'd266a7d5-d157-4e50-8ec6-3f584414197b': 'relation',
        'd8f3f531-4791-4532-a891-807d2b21c901': 'relation',
        'fad0fcc9-3538-4d02-b38d-407bdfbf14a7': 'boolean',
        'filters': [   {   'field_id': '11fbe9a6-a16d-4d7e-86ea-afe42ec03005',
                           'op_id': 'eq',
                           'value_default': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"b28165b1","path":["request", '
                                            '"package_id"]}\')}'}],
        'limit': '100',
        'order_direction': 'asc',
        'table_id': '9006'},
    {   'http_status_code': '400',
        'response': {   'error': 'The '
                                 '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"7b377962","path":["records", '
                                 '{"path_element_type": "current_item"}, '
                                 '"775508d3_5890_4c28_86ac_27ae118d1ada"]}\')} package has been '
                                 'deprecated and is no longer available for use.'}},
    {   '0f34f995-2a34-4fcf-b5c3-0270f8f718d0': 'relation',
        '11fbe9a6-a16d-4d7e-86ea-afe42ec03005': 'id',
        '61aae604-a95e-4519-9091-bb0bf754a67f': 'date_time',
        'a5612739-5401-4ae7-bd07-782c1a6fb2d1': 'date_time',
        'db77c09c-5f9c-4681-8135-50f0c39af67a': 'relation',
        'fc952b5a-bf20-4985-a1bd-5cfa657e8c74': 'relation',
        'filters': [   {   'field_id': 'db77c09c-5f9c-4681-8135-50f0c39af67a',
                           'op_relation': 'eq',
                           'value_relation': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"da3cfd40","path":["records", '
                                             '{"path_element_type": "current_item"}, '
                                             '"11fbe9a6_a16d_4d7e_86ea_afe42ec03005"]}\')}'},
                       {   'field_id': '0f34f995-2a34-4fcf-b5c3-0270f8f718d0',
                           'op_relation': 'eq',
                           'value_relation': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"b28165b1","path":["request", '
                                             '"package_id"]}\')}'}],
        'limit': '100',
        'order_direction': 'asc',
        'table_id': '9008'},
    {   'list_item_schema_json': '[{"control_type":"text","label":"ID","name":"id","type":"string","optional":false},{"control_type":"text","label":"Description","name":"description","type":"string","optional":false},{"control_type":"text","label":"Name","name":"name","type":"string","optional":false}]',
        'name': 'package_versions'},
    {   'variables': {   'schema': '[{"name":"page_token","type":"string","optional":true,"label":"page_token","details":{"real_name":"page_token"},"control_type":"text"}]'}},
    {   '11fbe9a6-a16d-4d7e-86ea-afe42ec03005': 'id',
        '1398de92-647f-4c1a-b1b3-77c53af0ed78': 'string',
        '13f19e63-dd47-4682-81c0-47c4bcaeeae3': 'date_time',
        '205f0633-0893-447e-a24f-146797dd3dfe': 'string',
        '2069a23e-4fcc-4674-9f81-094ac5e8c95d': 'relation',
        '225a1c1a-9719-4d19-bb71-8d5762009d49': 'date_time',
        '3c0b720b-bbe8-47de-a88d-96d759af819e': 'date_time',
        '4612b15c-300f-4120-870b-1884489c3736': 'integer',
        '61aae604-a95e-4519-9091-bb0bf754a67f': 'date_time',
        '622152c7-a09f-4d54-80f7-add539bee209': 'relation',
        '6e0f65d3-4376-4264-a472-c705bd4d41b4': 'string',
        '7b0540a6-7322-42dd-b6cf-89cf8759fb73': 'string',
        '891c88dd-6aa1-46a3-80ef-92fbb6c21f53': 'relation',
        'a5612739-5401-4ae7-bd07-782c1a6fb2d1': 'date_time',
        'cc31f2eb-b841-498c-bced-247d9dd78edb': 'string',
        'continuation_token': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"67b62be6","path":["page_token"]}\')}',
        'd1a07df5-2696-436d-930b-9a3ba82e0f26': 'string',
        'dfdac2d4-7384-4916-8416-0bc42c29d36f': 'string',
        'e2bf4aa4-a19c-4cbe-92b3-0ff50bcbbfbc': 'string',
        'e3bdb7a7-3561-48c0-b600-c210f5d64bb7': 'boolean',
        'e6395bdd-5e77-4ce7-8dbc-256c798486f9': 'string',
        'fc7aac95-0564-472c-a07f-9b20ba8e5a7b': 'boolean',
        'filters': [   {   'field_id': '622152c7-a09f-4d54-80f7-add539bee209',
                           'op_boolean': 'isfalse',
                           'op_relation': 'eq',
                           'value_relation': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"b28165b1","path":["request", '
                                             '"package_id"]}\')}'},
                       {'field_id': 'fc7aac95-0564-472c-a07f-9b20ba8e5a7b', 'op_boolean': 'istrue'},
                       {   'field_id': 'e3bdb7a7-3561-48c0-b600-c210f5d64bb7',
                           'op_boolean': 'isfalse'}],
        'limit': '200',
        'order_direction': 'asc',
        'table_id': '9005'},
    {   'name': 'f5731ceb-38aa-447f-b4db-a40866cd671a:67b62be6:page_token',
        'page_token': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"17e72b35","path":["continuation_token"]}\')}'},
    {   'list_items': {   '____source': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"17e72b35","path":["records"]}\')}',
                          'description': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"17e72b35","path":["records", '
                                         '{"path_element_type": "current_item"}, '
                                         '"205f0633_0893_447e_a24f_146797dd3dfe"]}\')}',
                          'id': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"17e72b35","path":["records", '
                                '{"path_element_type": "current_item"}, '
                                '"11fbe9a6_a16d_4d7e_86ea_afe42ec03005"]}\')}',
                          'name': '="v#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"17e72b35","path":["records",{"path_element_type":"current_item"},"4612b15c_300f_4120_870b_1884489c3736"]}\')}#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"17e72b35","path":["records",{"path_element_type":"current_item"},"11fbe9a6_a16d_4d7e_86ea_afe42ec03005"]}\') '
                                  '== '
                                  '_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"81d4b97f","path":["records",{"path_element_type":"current_item"},"fc952b5a_bf20_4985_a1bd_5cfa657e8c74","record_id"]}\') '
                                  '? \' - currently installed\' : \'\'}"'},
        'location': 'end',
        'name': '42626445-42c7-4919-b6eb-74f369cc61b1:0b2120cf'},
    {   'http_status_code': '200',
        'response': {   'versions': {   '____source': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"0b2120cf","path":["list_items"]}\')}',
                                        'description': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"0b2120cf","path":["list_items", '
                                                       '{"path_element_type": "current_item"}, '
                                                       '"description"]}\')}',
                                        'id': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"0b2120cf","path":["list_items", '
                                              '{"path_element_type": "current_item"}, "id"]}\')}',
                                        'name': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"0b2120cf","path":["list_items", '
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
]


def validate_109892683(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_109892683(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_109892683(raw)
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
    if AUTH_TABLE_ID not in tables_section["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must explicitly include auth table {AUTH_TABLE_ID}"
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


def run_109892683(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_109892683(raw)
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
    result["verifier"] = verify_109892683(result)
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
