from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_88676017


RECIPE_ID = "88676017"
SEED_TYPE = "recipe_function_contact_open_opportunity_lookup_variant"
TRACK = "live_salesforce_recipe_function_open_opportunity_lookup"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_PARAMETERS_SCHEMA_JSON = (
    '[{"name":"email","type":"string","optional":false,"control_type":"text","label":"Email"}]'
)
TRIGGER_RESULT_SCHEMA_JSON = (
    '[{"control_type":"text","label":"opportunity ID","name":"opportunity_id","type":"string","optional":false},'
    '{"control_type":"text","label":"opportunity name","name":"opportunity_name","type":"string","optional":false},'
    '{"name":"opportunity_stage","type":"string","optional":false,"control_type":"text","label":"Opportunity stage"}]'
)
EMAIL_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\","
    "\"line\":\"39ac7094\",\"path\":[\"parameters\", \"email\"]}')}"
)
CONTACT_LIST_SIZE_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"66389f6f\","
    "\"path\":[\"list_size\"]}')}"
)
CONTACT_ACCOUNT_ID_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"66389f6f\","
    "\"path\":[\"Contact\", {\"path_element_type\": \"current_item\"}, \"AccountId\"]}')}"
)
ACCOUNT_ID_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"0f27084d\","
    "\"path\":[\"Account\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}"
)
OPPORTUNITY_SOURCE_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"5da0fcde\","
    "\"path\":[\"Opportunity\"]}')}"
)


def _foreach_pill(field: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"f28ae75e\","
        "\"path\":[\"" + field + "\"]}')}"
    )


ACCUMULATE_DATA_TEMPLATE: dict[str, str] = {
    "Date": _foreach_pill("CloseDate"),
    "Stage": _foreach_pill("StageName"),
    "id": _foreach_pill("Id"),
    "opp_name": _foreach_pill("Name"),
}
ACCUMULATE_SCHEMA_JSON = (
    '[{"name":"Stage","type":"string","optional":true,"label":"Stage","control_type":"text"},'
    '{"name":"Date","type":"date","optional":true,"label":"Date","control_type":"date"},'
    '{"name":"opp_name","type":"string","optional":true,"label":"opp name","control_type":"text"},'
    '{"name":"id","type":"string","optional":true,"label":"id","control_type":"text"}]'
)
ACCUMULATE_LIST_NAME = "Opp stage and Date"
CREATE_LIST_NAME = "Opp Stage and Date"
CREATE_LIST_SOURCE_FORMULA = (
    "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\","
    "\"line\":\"2a425683\",\"path\":[\"list_items\"]}')"
)


def _stage_list_col(col: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\","
        "\"line\":\"6a7afb3a\",\"path\":[\"columns\", \"" + col + "\"]}')}"
    )


STAGE_LIST_NAME_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\","
    "\"line\":\"6a7afb3a\",\"path\":[\"list_name\"]}')}"
)
OPEN_STAGES_IN_LIST = (
    "('S0: Discovery', 'S1: Scoping', 'S2: Economic Buyer Meeting', "
    "'S3: Validation Event', 'S4: Business Case & Final Proposal', "
    "'S5: Negotiate & Close', 'Submitted for Booking')"
)
QUERY_SQL_TEMPLATE = (
    "SELECT " + _stage_list_col("Stage") + ", " + _stage_list_col("Date") + ", "
    + _stage_list_col("opp_name") + ", " + _stage_list_col("id")
    + " FROM " + STAGE_LIST_NAME_PILL
    + " WHERE " + _stage_list_col("Stage") + " IN " + OPEN_STAGES_IN_LIST
    + " ORDER BY " + _stage_list_col("Date") + " DESC LIMIT 1"
)
QUERY_RESULT_SCHEMA_JSON = (
    '[{"control_type":"text","label":"Stage","name":"Stage","type":"string","optional":true},'
    '{"control_type":"date","label":"Date","render_input":"date_conversion","parse_output":"date_conversion",'
    '"name":"Date","type":"date","optional":true},'
    '{"control_type":"text","label":"opp name","name":"opp_name","type":"string","optional":true},'
    '{"control_type":"text","label":"id","name":"id","type":"string","optional":true}]'
)
QUERY_ROWS_SIZE_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\","
    "\"line\":\"bfa6b004\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}"
)


def _query_row_pill(field: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\","
        "\"line\":\"bfa6b004\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"" + field + "\"]}')}"
    )


RETURN_NA_RESULT: dict[str, str] = {
    "opportunity_id": "N/A",
    "opportunity_name": "N/A",
    "opportunity_stage": "N/A",
}
RETURN_OPEN_RESULT_TEMPLATE: dict[str, str] = {
    "opportunity_id": _query_row_pill("id"),
    "opportunity_name": _query_row_pill("opp_name"),
    "opportunity_stage": _query_row_pill("Stage"),
}


def _disabled_list_col(col: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\","
        "\"line\":\"3724be65\",\"path\":[\"columns\", \"" + col + "\"]}')}"
    )


_DISABLED_LIST_NAME_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\","
    "\"line\":\"3724be65\",\"path\":[\"list_name\"]}')}"
)
DISABLED_NOT_LIKE_SQL = (
    "SELECT " + _disabled_list_col("opp_ID") + "," + _disabled_list_col("opp_name") + ","
    + _disabled_list_col("opp_stage")
    + " FROM " + _DISABLED_LIST_NAME_PILL
    + " WHERE " + _disabled_list_col("opp_stage") + ' NOT LIKE "Closed Lost" '
)
DISABLED_TRUNCATED_SQL = (
    "SELECT " + _disabled_list_col("opp_ID") + "," + _disabled_list_col("opp_name") + ","
    + _disabled_list_col("opp_stage")
    + " FROM " + _DISABLED_LIST_NAME_PILL
    + " WHERE (" + _disabled_list_col("opp_stage") + ' NOT LIKE "Closed Lost" AND '
)
DISABLED_CUSTOM_FIELD = "Opportunity_ID_18_Characters__c"
EXPECTED_DISABLED_NODES: list[tuple[int, str, str | None, str | None, str | None]] = [
    (15, "action", "salesforce", "search_sobjects", "081b79c6"),
    (16, "if", None, None, None),
    (17, "action", "workato_variable", "declare_list", "68a72444"),
    (18, "action", "workato_variable", "declare_list", "24ecc101"),
    (19, "foreach", None, None, "cb6ae160"),
    (20, "action", "workato_variable", "insert_to_list", "37514fd8"),
    (21, "foreach", None, None, "141db9bb"),
    (22, "action", "salesforce", "search_sobjects", "0ce1bf40"),
    (23, "action", "workato_variable", "insert_to_list", "71f36ffd"),
    (24, "action", "workato_smart_list", "create_list", "3724be65"),
    (25, "action", "workato_smart_list", "query_list", "127733dc"),
    (26, "if", None, None, None),
    (27, "action", "workato_smart_list", "query_list", "5596c9df"),
    (28, "action", "workato_recipe_function", "return_result", "ab880457"),
]
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("salesforce", "search_sobjects"),  # 66389f6f step 2 (Contact by Email)
    ("workato_recipe_function", "return_result"),  # 10bcec17 step 4 (N/A; terminal)
    ("salesforce", "search_sobjects"),  # 0f27084d step 7 (Account by Id)
    ("salesforce", "search_sobjects"),  # 5da0fcde step 8 (Opportunity by AccountId)
    ("workato_list", "accumulate_list_items"),  # 2a425683 step 10 (inside foreach 9)
    ("workato_smart_list", "create_list"),  # 6a7afb3a step 11
    ("workato_smart_list", "query_list"),  # bfa6b004 step 12
    ("workato_recipe_function", "return_result"),  # 6b9edda5 step 14 (terminal)
]
EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_runtime.accumulate_list_items",
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_recipe_function.return_result",
]


def validate_88676017(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != "39ac7094":
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step alias changed")
    trigger_in = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    if str(trigger_in.get("parameters_schema_json") or "") != TRIGGER_PARAMETERS_SCHEMA_JSON:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters schema changed")
    if str(trigger_in.get("result_schema_json") or "") != TRIGGER_RESULT_SCHEMA_JSON:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger result schema changed")

    actions = _collect_actions(raw)
    actual = [(action.get("provider"), action.get("name")) for action in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} executable action sequence changed: {actual}")
    (contact_search, return_na, account_search, opportunity_search,
     accumulate, create_list, query_list, return_open) = actions

    contact_in = _input(contact_search)
    if (
        str(contact_in.get("sobject_name") or "") != "Contact"
        or str(contact_in.get("Email") or "") != EMAIL_PILL
        or str(contact_in.get("field_list") or "") != "Id\nAccountId\nLastName\nFirstName\nName\nEmail"
        or str(contact_in.get("limit") or "") != "1"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} Contact search changed: {contact_in}")
    if _input(return_na).get("result") != RETURN_NA_RESULT:
        raise RuntimeError(f"recipe {RECIPE_ID} N/A return_result changed: {_input(return_na)}")
    account_in = _input(account_search)
    if (
        str(account_in.get("sobject_name") or "") != "Account"
        or str(account_in.get("Id") or "") != CONTACT_ACCOUNT_ID_PILL
        or str(account_in.get("field_list") or "") != "Id\nName"
        or str(account_in.get("limit") or "") != "150"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} Account search changed: {account_in}")
    opportunity_in = _input(opportunity_search)
    if (
        str(opportunity_in.get("sobject_name") or "") != "Opportunity"
        or str(opportunity_in.get("AccountId") or "") != ACCOUNT_ID_PILL
        or str(opportunity_in.get("field_list") or "") != "Id\nAccountId\nName\nStageName\nCloseDate\nIsClosed"
        or str(opportunity_in.get("limit") or "") != "150"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} Opportunity search changed: {opportunity_in}")
    accumulate_in = _input(accumulate)
    list_item = accumulate_in.get("list_item") if isinstance(accumulate_in.get("list_item"), dict) else {}
    if (
        str(accumulate_in.get("name") or "") != ACCUMULATE_LIST_NAME
        or list_item.get("data") != ACCUMULATE_DATA_TEMPLATE
        or str(list_item.get("schema") or "") != ACCUMULATE_SCHEMA_JSON
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} accumulate_list_items changed: {accumulate_in}")
    create_in = _input(create_list)
    if (
        str(create_in.get("list_name") or "") != CREATE_LIST_NAME
        or str(create_in.get("list_source") or "") != CREATE_LIST_SOURCE_FORMULA
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} smart list create_list changed: {create_in}")
    query_in = _input(query_list)
    if str(query_in.get("sql") or "") != QUERY_SQL_TEMPLATE:
        raise RuntimeError(f"recipe {RECIPE_ID} smart list query SQL changed: {query_in.get('sql')}")
    if str(query_in.get("result_schema_json") or "") != QUERY_RESULT_SCHEMA_JSON:
        raise RuntimeError(f"recipe {RECIPE_ID} smart list query result schema changed")
    if (
        str(query_in.get("output_schema_by") or "") != "index"
        or str(query_in.get("headers") or "") != "false"
        or str(query_in.get("csv") or "") != "false"
        or str(query_in.get("col_sep") or "") != "comma"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} smart list query options changed: {query_in}")
    if _input(return_open).get("result") != RETURN_OPEN_RESULT_TEMPLATE:
        raise RuntimeError(f"recipe {RECIPE_ID} open-opportunity return_result changed: {_input(return_open)}")

    ifs = _collect_ifs(raw)
    expected_ifs = [
        (3, CONTACT_LIST_SIZE_PILL, "equals_to", "0"),
        (6, CONTACT_ACCOUNT_ID_PILL, "present", "0"),
        (13, QUERY_ROWS_SIZE_PILL, "greater_than", "0"),
    ]
    if ifs != expected_ifs:
        raise RuntimeError(f"recipe {RECIPE_ID} executable IF conditions changed: {ifs}")

    foreach = _find_node(raw, lambda n: n.get("keyword") == "foreach" and not n.get("skip"))
    if (
        foreach is None
        or str(foreach.get("as") or "") != "f28ae75e"
        or str(_input(foreach).get("source") or "") != OPPORTUNITY_SOURCE_PILL
        or str(foreach.get("repeat_mode") or "") != "simple"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} opportunity foreach changed")
    stop = _find_node(raw, lambda n: n.get("keyword") == "stop")
    if stop is None or stop.get("skip") or str(_input(stop).get("stop_with_error") or "") != "false":
        raise RuntimeError(f"recipe {RECIPE_ID} graceful stop node changed")

    disabled = _collect_disabled(raw)
    actual_disabled = [
        (node.get("number"), node.get("keyword"), node.get("provider"), node.get("name"), node.get("as"))
        for node in disabled
    ]
    if actual_disabled != [tuple(item) for item in EXPECTED_DISABLED_NODES]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} author-disabled region changed (re-enabled steps need a "
            f"real OCR/custom-field build): {actual_disabled}"
        )
    by_as = {str(node.get("as") or ""): node for node in disabled}
    if str(_input(by_as["127733dc"]).get("sql") or "") != DISABLED_NOT_LIKE_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} disabled NOT LIKE SQL (step 25) changed")
    if str(_input(by_as["5596c9df"]).get("sql") or "") != DISABLED_TRUNCATED_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} disabled truncated SQL (step 27) changed")
    if DISABLED_CUSTOM_FIELD not in _input(by_as["0ce1bf40"]):
        raise RuntimeError(f"recipe {RECIPE_ID} disabled OCR opportunity search filter changed")

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
        "disabled_steps": [item[0] for item in EXPECTED_DISABLED_NODES],
    }


def seed_88676017(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88676017(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict) or sorted(parameters.keys()) != ["email"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must carry exactly ['email']; got "
            f"{sorted(parameters.keys()) if isinstance(parameters, dict) else parameters}"
        )
    if not str(parameters.get("email") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter 'email' must be a non-empty string")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or not isinstance(seed_in.get("salesforce"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce (live search targets)")
    records = seed_in["salesforce"].get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.records must be a non-empty list "
            "(every variant seeds at least one benchmark-owned record explicitly)"
        )
    for record in records:
        if not isinstance(record, dict) or not str(record.get("ref") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} every seeded Salesforce record needs a 'ref': {record}")
    if seed_in["salesforce"].get("schema") not in (None,):
        # The only custom field this recipe mentions lives in the author-disabled
        # region (steps 15-28); provisioning schema for dead code is forbidden.
        raise RuntimeError(
            f"recipe {RECIPE_ID} must not declare seed.salesforce.schema while steps 15-28 stay disabled"
        )
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": seed_in["salesforce"]})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    refs = _salesforce_ref_tokens(seed_in["salesforce"], provision)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "raw_validation": validation,
        # Expected opportunity ids/names are this run's live seeded records,
        # threaded into expect via the same $REF_ID tokens as 64106452/97967767.
        "expect": _replace_value(deepcopy(expect), refs),
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": refs,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    for key in ("force_action_error", "job_context"):
        if isinstance(data.get(key), dict):
            out[key] = deepcopy(data[key])
    return attach_variant(out, ctx)


def run_88676017(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88676017(raw)
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    cleanup_response: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = _snapshot(ctx)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx)
    finally:
        # Read-only recipe, but the SEED created live records: always delete
        # every benchmark-owned record, pass or fail.
        cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
        details["cleanup_response"] = cleanup_response
    if not cleanup_response.get("ok", True):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce cleanup failed: {cleanup_response}")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_88676017(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _input(node: dict[str, Any]) -> dict[str, Any]:
    raw = node.get("input")
    return raw if isinstance(raw, dict) else {}


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        if not child.get("skip"):
            found.extend(_collect_actions(child))
    return found


def _collect_ifs(node: dict[str, Any]) -> list[tuple[int, str, str, str]]:
    found: list[tuple[int, str, str, str]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict) or child.get("skip"):
            continue
        if child.get("keyword") == "if":
            for condition in (_input(child).get("conditions") or []):
                if isinstance(condition, dict):
                    found.append((
                        child.get("number"),
                        str(condition.get("lhs") or ""),
                        str(condition.get("operand") or ""),
                        str(condition.get("rhs") or ""),
                    ))
        found.extend(_collect_ifs(child))
    return found


def _collect_disabled(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("skip"):
            found.append(child)
        found.extend(_collect_disabled(child))
    return sorted(found, key=lambda n: int(n.get("number") or 0))


def _find_node(node: dict[str, Any], match: Any) -> dict[str, Any] | None:
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if match(child):
            return child
        nested = _find_node(child, match)
        if nested is not None:
            return nested
    return None


def _salesforce_ref_tokens(seed_section: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    live_ids = [
        str(record.get("id") or "")
        for record in salesforce_snapshot.get("records") or []
        if isinstance(record, dict) and record.get("id")
    ]
    seed_records = [record for record in seed_section.get("records") or [] if isinstance(record, dict)]
    if len(live_ids) != len(seed_records):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed/snapshot record count mismatch: "
            f"{len(seed_records)} seeded vs {len(live_ids)} provisioned"
        )
    refs: dict[str, str] = {}
    for idx, record in enumerate(seed_records):
        ref = str(record.get("ref") or "").strip()
        if ref:
            refs[f"${ref.upper()}_ID"] = live_ids[idx]
    return refs


def _replace_value(value: Any, refs: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_value(item, refs) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_value(item, refs) for item in value]
    if isinstance(value, str):
        out = value
        for token, replacement in refs.items():
            out = out.replace(token, replacement)
        return out
    return value


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return {"salesforce": ctx.tools.call("harness.salesforce.snapshot", {})}


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
