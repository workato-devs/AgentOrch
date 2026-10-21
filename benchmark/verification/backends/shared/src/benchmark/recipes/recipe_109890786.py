from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_109890786


RECIPE_ID = "109890786"
SEED_TYPE = "workspace_packages_by_type_api_variant"
TRACK = "workato_api_platform_packages_by_type"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "b28165b1"
# API Platform endpoint: list packages of a package type. Step map:
#   auth get_records (Workspaces, access_profile.id + workspace_user_id +
#   enabled istrue) -> IF size==0 return 401 (terminal). TRY: package-type
#   get_records by request.package_type_id, declare_list packages,
#   declare_variable page_token, REPEAT [packages get_records (type relation
#   eq first type-record id + deleted isfalse, limit 200,
#   continuation_token=page_token), update page_token, IF size>0
#   insert_to_list_batch (id/description/name), WHILE page_token present]
#   -> return 200 {packages}. CATCH -> 400 {error: "Unexpected Error"}.
#   An unknown package_type_id nil-PROPAGATES the relation-filter pill
#   (first record of the EMPTY type result -> nil, faithful Workato datapill
#   semantics since the 2026-07-14 engine nil-propagation pass): the packages
#   read runs with a null filter that matches only null/empty relation cells,
#   so the natural outcome is 200 with an empty packages array (variant_04).
#   The catch 400 arm is entered via force_action_error on the packages read
#   (variant_05).
AUTH_TABLE_ID = "7201"
TYPES_TABLE_ID = "7205"
PACKAGES_TABLE_ID = "7184"
REQUIRED_TRIGGER_REQUEST_FIELDS = ("workspace_user_id", "package_type_id",)
EXPECTED_ACTIONS: list[tuple[str, str]] = [   ('workato_db_table', 'get_records'),
    ('workato_api_platform', 'return_response'),
    ('workato_db_table', 'get_records'),
    ('workato_variable', 'declare_list'),
    ('workato_variable', 'declare_variable'),
    ('workato_db_table', 'get_records'),
    ('workato_variable', 'update_variables'),
    ('workato_variable', 'insert_to_list_batch'),
    ('workato_api_platform', 'return_response'),
    ('workato_api_platform', 'return_response')]
EXPECTED_ACTION_AS: list[str] = [   '8b12c2d4',
    '43ae7274',
    '3a15792d',
    '1b5253fe',
    '272c4f6f',
    '6f83804e',
    '10973da8',
    '4100fdb8',
    '1a4372b6',
    '2cea7793']
EXPECTED_CONTROL_FLOW: list[dict[str, Any]] = [   {   'input': {   'conditions': [   {   'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"8b12c2d4","path":["records", '
                                                  '{"path_element_type": "size"}]}\')}',
                                           'operand': 'equals_to',
                                           'rhs': '0'}],
                     'operand': 'and',
                     'type': 'compound'},
        'keyword': 'if',
        'number': 3},
    {'input': {}, 'keyword': 'try', 'number': 5},
    {'input': {}, 'keyword': 'repeat', 'number': 9},
    {   'input': {   'conditions': [   {   'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"6f83804e","path":["records", '
                                                  '{"path_element_type": "size"}]}\')}',
                                           'operand': 'greater_than',
                                           'rhs': '0'}],
                     'operand': 'and',
                     'type': 'compound'},
        'keyword': 'if',
        'number': 12},
    {   'input': {   'conditions': [   {   'lhs': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"272c4f6f","path":["page_token"]}\')}',
                                           'operand': 'present',
                                           'rhs': ''}],
                     'operand': 'and',
                     'type': 'compound'},
        'keyword': 'while_condition',
        'number': 14},
    {'input': {'max_retry_count': '0', 'retry_interval': '2'}, 'keyword': 'catch', 'number': 16}]
# Raw trigger + per-action inputs pinned verbatim from
# dataset/input_recipes/109890786/raw_recipe.md (key formulas: db-table filter pills,
# the pagination continuation_token / page_token pills, the list mappings
# and the return_response bodies). Any drift raises at validate time.
PINNED_TRIGGER_INPUT: dict[str, Any] = {   'request': {   'content_type': 'json',
                   'schema': '[{"name":"workspace_user_id","type":"integer","optional":false,"control_type":"integer","label":"Workspace '
                             'user '
                             'ID","parse_output":"integer_conversion"},{"name":"package_type_id","type":"string","optional":false,"control_type":"text","label":"Package '
                             'type ID"}]'},
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
        'table_id': '7201'},
    {'http_status_code': '401'},
    {   '11fbe9a6-a16d-4d7e-86ea-afe42ec03005': 'id',
        '553544e4-187e-4b4f-b246-f14fdf5d3521': 'string',
        '61aae604-a95e-4519-9091-bb0bf754a67f': 'date_time',
        'a5612739-5401-4ae7-bd07-782c1a6fb2d1': 'date_time',
        'filters': [   {   'field_id': '11fbe9a6-a16d-4d7e-86ea-afe42ec03005',
                           'op_id': 'eq',
                           'value_default': '#{_dp(\'{"pill_type":"output","provider":"workato_api_platform","line":"b28165b1","path":["request", '
                                            '"package_type_id"]}\')}'}],
        'limit': '100',
        'order_direction': 'asc',
        'table_id': '7205'},
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
        'continuation_token': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"272c4f6f","path":["page_token"]}\')}',
        'd266a7d5-d157-4e50-8ec6-3f584414197b': 'relation',
        'd8f3f531-4791-4532-a891-807d2b21c901': 'relation',
        'fad0fcc9-3538-4d02-b38d-407bdfbf14a7': 'boolean',
        'filters': [   {   'field_id': 'd8f3f531-4791-4532-a891-807d2b21c901',
                           'op_relation': 'eq',
                           'value_relation': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"3a15792d","path":["records", '
                                             '{"path_element_type": "current_item"}, '
                                             '"11fbe9a6_a16d_4d7e_86ea_afe42ec03005"]}\')}'},
                       {   'field_id': 'fad0fcc9-3538-4d02-b38d-407bdfbf14a7',
                           'op_boolean': 'isfalse'}],
        'limit': '200',
        'order_direction': 'asc',
        'table_id': '7184'},
    {   'name': '60de4ea3-a614-4936-8de8-0145c6b0eb1e:272c4f6f:page_token',
        'page_token': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"6f83804e","path":["continuation_token"]}\')}'},
    {   'list_items': {   '____source': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"6f83804e","path":["records"]}\')}',
                          'description': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"6f83804e","path":["records", '
                                         '{"path_element_type": "current_item"}, '
                                         '"2304597f_d05e_42e9_a49b_cf7599cfb9a3"]}\')}',
                          'id': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"6f83804e","path":["records", '
                                '{"path_element_type": "current_item"}, '
                                '"11fbe9a6_a16d_4d7e_86ea_afe42ec03005"]}\')}',
                          'name': '#{_dp(\'{"pill_type":"output","provider":"workato_db_table","line":"6f83804e","path":["records", '
                                  '{"path_element_type": "current_item"}, '
                                  '"775508d3_5890_4c28_86ac_27ae118d1ada"]}\')}'},
        'location': 'end',
        'name': '214161ab-ff01-419c-8080-8e90b65032e5:1b5253fe'},
    {   'http_status_code': '200',
        'response': {   'packages': {   '____source': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"1b5253fe","path":["list_items"]}\')}',
                                        'description': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"1b5253fe","path":["list_items", '
                                                       '{"path_element_type": "current_item"}, '
                                                       '"description"]}\')}',
                                        'id': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"1b5253fe","path":["list_items", '
                                              '{"path_element_type": "current_item"}, "id"]}\')}',
                                        'name': '#{_dp(\'{"pill_type":"output","provider":"workato_variable","line":"1b5253fe","path":["list_items", '
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


def validate_109890786(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_109890786(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_109890786(raw)
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


def run_109890786(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_109890786(raw)
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
    result["verifier"] = verify_109890786(result)
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
