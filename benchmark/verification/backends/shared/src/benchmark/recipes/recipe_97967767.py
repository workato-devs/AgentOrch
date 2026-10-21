from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_97967767


RECIPE_ID = "97967767"
SEED_TYPE = "salesforce_product_update_lookup_sync_slack_bot_variant"
TRACK = "live_salesforce_lookup_table_slack_product_sync"
TRIGGER_PROVIDER = "salesforce"
TRIGGER_NAME = "updated_custom_object"
LOOKUP_TABLE_ID = "2257714"
PRODUCT_REF_TOKEN = "$PRODUCT_ID"
EXPECTED_ACTIONS: list[tuple[str, str]] = [
    ("salesforce", "get_custom_object"),
    ("lookup_table", "search_entries"),
    ("lookup_table", "add_entry"),
    ("lookup_table", "update_entry"),
    ("slack_bot", "post_bot_message"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.search_records",
    "lookup_table.search_entries",
    "lookup_table.add_entry",
    "lookup_table.update_entry",
    "slack.post_message",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "lookup_table.search_entries",
    "lookup_table.add_entry",
    "lookup_table.update_entry",
    "slack.post_message",
]
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_SF_ID_RE = re.compile(r"^[a-zA-Z0-9]{15,18}$")

# --- Verbatim raw-recipe pins. The trigger is replayed from the seeded payload
# and the lookup table is a Workato-internal mock, so these literals never
# reach a live Workato runtime; they are pinned verbatim so any upstream change
# to the raw recipe fails validation instead of silently drifting. ---
_TRIGGER_ID_PILL = '''#{_dp('{"pill_type":"output","provider":"salesforce","line":"f2178d9f","path":["Id"]}')}'''
_TRIGGER_NAME_PILL = '''#{_dp('{"pill_type":"output","provider":"salesforce","line":"f2178d9f","path":["Name"]}')}'''
_TRIGGER_FAMILY_PILL = '''#{_dp('{"pill_type":"output","provider":"salesforce","line":"f2178d9f","path":["Family"]}')}'''
_TRIGGER_ISACTIVE_PILL = '''#{_dp('{"pill_type":"output","provider":"salesforce","line":"f2178d9f","path":["IsActive"]}')}'''
_GET_SUB_FAMILY_PILL = '''#{_dp('{"pill_type":"output","provider":"salesforce","line":"2cf3b068","path":["Product_Sub_Family__c"]}')}'''
_ENTRIES_SIZE_PILL = '''#{_dp('{"pill_type":"output","provider":"lookup_table","line":"a93857df","path":["entries", {"path_element_type": "size"}]}')}'''
_ENTRIES_CURRENT_ID_PILL = '''#{_dp('{"pill_type":"output","provider":"lookup_table","line":"a93857df","path":["entries", {"path_element_type": "current_item"}, "id"]}')}'''
_ENTRIES_CURRENT_COL1_PILL = '''#{_dp('{"pill_type":"output","provider":"lookup_table","line":"a93857df","path":["entries", {"path_element_type": "current_item"}, "entry", "col1"]}')}'''
_ENTRIES_CURRENT_COL3_PILL = '''#{_dp('{"pill_type":"output","provider":"lookup_table","line":"a93857df","path":["entries", {"path_element_type": "current_item"}, "entry", "col3"]}')}'''
_ENTRIES_CURRENT_COL6_PILL = '''#{_dp('{"pill_type":"output","provider":"lookup_table","line":"a93857df","path":["entries", {"path_element_type": "current_item"}, "entry", "col6"]}')}'''
_ADD_ID_PILL = '''#{_dp('{"pill_type":"output","provider":"lookup_table","line":"4e4f89c8","path":["id"]}')}'''
_UPDATE_ID_PILL = '''#{_dp('{"pill_type":"output","provider":"lookup_table","line":"1ea6cba9","path":["id"]}')}'''
_CATCH_MESSAGE_PILL = '''#{_dp('{"pill_type":"output","provider":"catch","line":"747dd863","path":["message"]}')}'''
_ISACTIVE_TO_S_FORMULA = '''=_dp('{"pill_type":"output","provider":"salesforce","line":"f2178d9f","path":["IsActive"]}').to_s'''
_CATEGORY_FORMULA = (
    '''=_dp('{"pill_type":"output","provider":"lookup_table","line":"1ea6cba9","path":["entry","col2"]}').present? '''
    '''? "`#{_dp('{"pill_type":"output","provider":"lookup_table","line":"1ea6cba9","path":["entry","col2"]}')}`" : "~NIL~"'''
)
_TRUE_QUANTITY_FORMULA = (
    '''=_dp('{"pill_type":"output","provider":"lookup_table","line":"1ea6cba9","path":["entry","col5"]}').present? '''
    '''? "`#{_dp('{"pill_type":"output","provider":"lookup_table","line":"1ea6cba9","path":["entry","col5"]}')}`" : "~NIL~"'''
)
_ACTIVE_FORMULA = (
    '''=_dp('{"pill_type":"output","provider":"salesforce","line":"f2178d9f","path":["IsActive"]}').is_true? '''
    '''? ":firefighter_check:" : ":firefighter_cross:"'''
)
_PRODUCT_LINK = (
    "https://workato.lightning.force.com/lightning/r/Product2/" + _TRIGGER_ID_PILL + "/view"
)

TRIGGER_INPUT_PIN: dict[str, Any] = {
    "field_list": "Id\nProductCode\nName\nDescription\nIsActive\nFamily\nStockKeepingUnit\nPlan_Description__c\nSBQQ__DefaultQuantity__c\nSBCF_IsCPQProduct__c",
    "since_offset": "no_limit",
    "sobject_name": "Product2",
}
GET_INPUT_PIN: dict[str, Any] = {
    "id": _TRIGGER_ID_PILL,
    "sobject_name": "Product2",
}
IF4_INPUT_PIN: dict[str, Any] = {
    "conditions": [
        {"lhs": _GET_SUB_FAMILY_PILL, "operand": "contains", "rhs": "Bundle Component"},
    ],
    "operand": "and",
    "type": "compound",
}
STOP5_INPUT_PIN: dict[str, Any] = {"stop_with_error": "false"}
SEARCH_INPUT_PIN: dict[str, Any] = {
    "lookup_table_id": LOOKUP_TABLE_ID,
    "parameters": {"col4": _TRIGGER_ID_PILL},
}
IF7_INPUT_PIN: dict[str, Any] = {
    "conditions": [
        {"lhs": _ENTRIES_SIZE_PILL, "operand": "equals_to", "rhs": "0"},
    ],
    "operand": "and",
    "type": "compound",
}
ADD_INPUT_PIN: dict[str, Any] = {
    "lookup_table_id": LOOKUP_TABLE_ID,
    "parameters": {
        "col1": _TRIGGER_NAME_PILL,
        "col3": _TRIGGER_FAMILY_PILL,
        "col4": _TRIGGER_ID_PILL,
        "col6": _TRIGGER_ISACTIVE_PILL,
    },
}
IF9_INPUT_PIN: dict[str, Any] = {
    "conditions": [
        {"lhs": _ENTRIES_SIZE_PILL, "operand": "equals_to", "rhs": "1"},
    ],
    "operand": "and",
    "type": "compound",
}
IF10_INPUT_PIN: dict[str, Any] = {
    "conditions": [
        {"lhs": _TRIGGER_NAME_PILL, "operand": "not_equals_to", "rhs": _ENTRIES_CURRENT_COL1_PILL},
        {"lhs": _TRIGGER_FAMILY_PILL, "operand": "not_equals_to", "rhs": _ENTRIES_CURRENT_COL3_PILL},
        {"lhs": _ISACTIVE_TO_S_FORMULA, "operand": "not_equals_to", "rhs": _ENTRIES_CURRENT_COL6_PILL},
    ],
    "operand": "and",
    "type": "compound",
}
UPDATE_INPUT_PIN: dict[str, Any] = {
    "id": _ENTRIES_CURRENT_ID_PILL,
    "ignore_not_found": "false",
    "lookup_table_id": LOOKUP_TABLE_ID,
    "parameters": {
        "col1": _TRIGGER_NAME_PILL,
        "col3": _TRIGGER_FAMILY_PILL,
        "col4": _TRIGGER_ID_PILL,
        "col6": _TRIGGER_ISACTIVE_PILL,
    },
}
IF12_INPUT_PIN: dict[str, Any] = {
    "conditions": [
        {"lhs": _ENTRIES_SIZE_PILL, "operand": "greater_than", "rhs": "1"},
    ],
    "operand": "and",
    "type": "compound",
}
STOP13_INPUT_PIN: dict[str, Any] = {
    "stop_reason": "Duplicated entries found in Lookup Table",
    "stop_with_error": "true",
}
IF14_INPUT_PIN: dict[str, Any] = {
    "conditions": [
        {"lhs": _ADD_ID_PILL, "operand": "present", "rhs": ""},
        {"lhs": _UPDATE_ID_PILL, "operand": "present", "rhs": ""},
    ],
    "operand": "or",
    "type": "compound",
}
SLACK_INPUT_PIN: dict[str, Any] = {
    "attachment_buttons": [{}],
    "attachment_fields": [
        {"title": "Name", "value": "`" + _TRIGGER_NAME_PILL + "`"},
        {"title": "Category", "value": _CATEGORY_FORMULA},
        {"title": "Family", "value": "`" + _TRIGGER_FAMILY_PILL + "`"},
        {"title": "True Quantity", "value": _TRUE_QUANTITY_FORMULA},
        {"title": "Active", "value": _ACTIVE_FORMULA},
    ],
    "blocks": [
        {
            "block_type": "section_with_text",
            "button_type": "continue_flow",
            "section_text": ":salesforce: *Updated <" + _PRODUCT_LINK + "|Product>!*",
        },
        {
            "block_type": "section_with_button_with_long_action",
            "bot_command": "23112894",
            "button_title": "Update",
            "button_type": "bot_command",
            "params": "product_id: " + _TRIGGER_ID_PILL,
            "section_text": (
                "Do check if we need to update the *True Quantity* and *Category* of this "
                "product in the <https://app.workato.com/lookup_tables/2257714|Lookup Table>!"
            ),
            "style": "primary",
        },
        {"block_type": "divider", "button_type": "continue_flow"},
    ],
    "channel": "#salesforce-feed",
    "message": {
        "color": "warning",
        "footer": "<" + _PRODUCT_LINK + "|Product ID: " + _TRIGGER_ID_PILL + ">",
    },
}
CATCH_INPUT_PIN: dict[str, Any] = {"max_retry_count": "0", "retry_interval": "2"}
STOP17_INPUT_PIN: dict[str, Any] = {
    "stop_reason": _CATCH_MESSAGE_PILL,
    "stop_with_error": "true",
}


def validate_97967767(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != "f2178d9f":
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed")
    _require_input(raw, TRIGGER_INPUT_PIN, "trigger")
    root_children = [child for child in raw.get("block") or [] if isinstance(child, dict)]
    if len(root_children) != 1 or root_children[0].get("keyword") != "try" or root_children[0].get("number") != 2:
        raise RuntimeError(f"recipe {RECIPE_ID} root block is not a single try (step 2)")
    try_node = root_children[0]
    children = [child for child in try_node.get("block") or [] if isinstance(child, dict)]
    shape = [(child.get("keyword"), child.get("number")) for child in children]
    expected_shape = [
        ("action", 3), ("if", 4), ("action", 6), ("if", 7),
        ("if", 9), ("if", 12), ("if", 14), ("catch", 16),
    ]
    if shape != expected_shape:
        raise RuntimeError(f"recipe {RECIPE_ID} try-body shape changed: {shape}")
    get3, if4, search6, if7, if9, if12, if14, catch16 = children
    _require_action(get3, "salesforce", "get_custom_object", "2cf3b068", GET_INPUT_PIN)
    _require_input(if4, IF4_INPUT_PIN, "if 4")
    stop5 = _only_child(if4, "stop", 5)
    _require_input(stop5, STOP5_INPUT_PIN, "stop 5")
    _require_action(search6, "lookup_table", "search_entries", "a93857df", SEARCH_INPUT_PIN)
    _require_input(if7, IF7_INPUT_PIN, "if 7")
    add8 = _only_child(if7, "action", 8)
    _require_action(add8, "lookup_table", "add_entry", "4e4f89c8", ADD_INPUT_PIN)
    _require_input(if9, IF9_INPUT_PIN, "if 9")
    if10 = _only_child(if9, "if", 10)
    _require_input(if10, IF10_INPUT_PIN, "if 10")
    update11 = _only_child(if10, "action", 11)
    _require_action(update11, "lookup_table", "update_entry", "1ea6cba9", UPDATE_INPUT_PIN)
    _require_input(if12, IF12_INPUT_PIN, "if 12")
    stop13 = _only_child(if12, "stop", 13)
    _require_input(stop13, STOP13_INPUT_PIN, "stop 13")
    _require_input(if14, IF14_INPUT_PIN, "if 14")
    slack15 = _only_child(if14, "action", 15)
    _require_action(slack15, "slack_bot", "post_bot_message", "7e1bf032", SLACK_INPUT_PIN)
    if catch16.get("as") != "747dd863":
        raise RuntimeError(f"recipe {RECIPE_ID} catch step id changed: {catch16.get('as')}")
    _require_input(catch16, CATCH_INPUT_PIN, "catch 16")
    stop17 = _only_child(catch16, "stop", 17)
    _require_input(stop17, STOP17_INPUT_PIN, "stop 17")
    actions = _collect_actions(raw)
    actual_actions = [(action.get("provider"), action.get("name")) for action in actions]
    if actual_actions != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual_actions}")
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


def seed_97967767(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_97967767(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"salesforce", "lookup_table"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    sf_section = seed_in.get("salesforce")
    if not isinstance(sf_section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce (live Product2 seed)")
    _require_product_schema(sf_section)
    product_fields = _require_product_record(sf_section)
    lookup_section = seed_in.get("lookup_table")
    if not isinstance(lookup_section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.lookup_table (Workato-internal mock)")
    tables = lookup_section.get("tables")
    if not isinstance(tables, dict) or not isinstance(tables.get(LOOKUP_TABLE_ID), list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must declare table {LOOKUP_TABLE_ID} explicitly"
        )
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    for key in ("tools", "stopped", "slack_posted", "final_lookup_row_count"):
        if key not in expect:
            raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required key {key!r}")
    _require_trigger_shape(trigger, product_fields)
    provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": sf_section})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    live_id = _live_product_id(provision)
    refs = {PRODUCT_REF_TOKEN: live_id}
    trigger = _replace_value(trigger, refs)
    _require_no_tokens(trigger, "trigger")
    if str(trigger.get("Id") or "") != live_id:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger Id did not resolve to the live Product2 id")
    resolved_lookup = _replace_value(deepcopy(lookup_section), refs)
    _require_no_tokens(resolved_lookup, "seed.lookup_table")
    resolved_expect = _replace_value(deepcopy(expect), refs)
    _require_no_tokens(resolved_expect, "expect")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "expect": resolved_expect,
        "raw_validation": validation,
        "lookup_table": resolved_lookup,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": refs,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    for key in ("force_action_error", "job_context"):
        if isinstance(data.get(key), dict):
            out[key] = deepcopy(data[key])
    return attach_variant(out, ctx)


def run_97967767(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_97967767(raw)
    if any(tool.startswith("slack.") for tool in ALLOWED_TOOLS):
        if not ctx.env.slack_channel_override:
            raise RuntimeError("missing SLACK_CHANNEL_OVERRIDE; refusing to guess live Slack channel")
    initial_snapshot = _snapshot(ctx, seed)
    cleanup_response: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, seed)
    finally:
        if isinstance(seed.get("salesforce_live"), dict):
            cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
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
            "cleanup_response": cleanup_response,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_97967767(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_input(node: dict[str, Any], expected: dict[str, Any], label: str) -> None:
    actual = node.get("input")
    if actual != expected:
        raise RuntimeError(
            f"recipe {RECIPE_ID} {label} input changed:\n"
            f"expected: {json.dumps(expected, sort_keys=True)}\n"
            f"actual:   {json.dumps(actual, sort_keys=True)}"
        )


def _require_action(
    node: dict[str, Any],
    provider: str,
    name: str,
    step_as: str,
    expected_input: dict[str, Any],
) -> None:
    if node.get("provider") != provider or node.get("name") != name or node.get("as") != step_as:
        raise RuntimeError(
            f"recipe {RECIPE_ID} action changed: expected {provider}.{name} as {step_as}, "
            f"got {node.get('provider')}.{node.get('name')} as {node.get('as')}"
        )
    if node.get("skip"):
        raise RuntimeError(f"recipe {RECIPE_ID} action {provider}.{name} is skipped in the raw recipe")
    _require_input(node, expected_input, f"{provider}.{name}")


def _only_child(node: dict[str, Any], keyword: str, number: int) -> dict[str, Any]:
    children = [child for child in node.get("block") or [] if isinstance(child, dict)]
    if len(children) != 1 or children[0].get("keyword") != keyword or children[0].get("number") != number:
        raise RuntimeError(
            f"recipe {RECIPE_ID} step {node.get('number')} block changed: expected a single "
            f"{keyword} (step {number}), got {[(c.get('keyword'), c.get('number')) for c in children]}"
        )
    return children[0]


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _require_product_schema(sf_section: dict[str, Any]) -> None:
    schema = sf_section.get("schema")
    if not isinstance(schema, list) or not schema:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare the Product2 custom field "
            "(schema-in-seed provisioning via ensure_custom_field)"
        )
    if not any(
        isinstance(entry, dict)
        and str(entry.get("sobject") or "") == "Product2"
        and str(entry.get("field") or "") == "Product_Sub_Family__c"
        for entry in schema
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must include Product2.Product_Sub_Family__c"
        )


def _require_product_record(sf_section: dict[str, Any]) -> dict[str, Any]:
    records = [record for record in sf_section.get("records") or [] if isinstance(record, dict)]
    products = [record for record in records if str(record.get("sobject") or "") == "Product2"]
    if len(records) != 1 or len(products) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.records must contain exactly one Product2 record"
        )
    product = products[0]
    if str(product.get("ref") or "") != "product":
        raise RuntimeError(f"recipe {RECIPE_ID} Product2 seed record must carry ref 'product'")
    fields = product.get("fields")
    if not isinstance(fields, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} Product2 seed record is missing fields")
    for key in ("Name", "Family", "Product_Sub_Family__c"):
        if not str(fields.get(key) or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} Product2 seed record requires explicit {key}")
    if not isinstance(fields.get("IsActive"), bool):
        raise RuntimeError(f"recipe {RECIPE_ID} Product2 seed record requires an explicit boolean IsActive")
    return fields


def _require_trigger_shape(trigger: dict[str, Any], product_fields: dict[str, Any]) -> None:
    for key in ("Id", "Name", "Family", "IsActive"):
        if key not in trigger:
            raise RuntimeError(f"recipe {RECIPE_ID} trigger_input is missing dereferenced field {key}")
    if str(trigger.get("Id") or "") != PRODUCT_REF_TOKEN:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.Id must be the {PRODUCT_REF_TOKEN} seed token "
            "(live record ids are assigned at seed time)"
        )
    if not isinstance(trigger.get("IsActive"), bool):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input.IsActive must be an explicit boolean")
    # The trigger event carries the just-updated Product2 state; the recipe then
    # re-reads the same record live. Pin the two views to each other so a
    # variant cannot drift into an unfaithful trigger/record split.
    for key in ("Name", "Family", "IsActive"):
        if trigger.get(key) != product_fields.get(key):
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger_input.{key} must match the seeded Product2 field "
                f"({trigger.get(key)!r} != {product_fields.get(key)!r})"
            )


def _live_product_id(provision: dict[str, Any]) -> str:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    products = [
        record for record in salesforce.get("records") or []
        if isinstance(record, dict) and str(record.get("sobject") or "") == "Product2"
    ]
    if len(products) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expected exactly one provisioned Product2 record, got {len(products)}"
        )
    live_id = str(products[0].get("id") or "")
    if not _SF_ID_RE.fullmatch(live_id):
        raise RuntimeError(f"recipe {RECIPE_ID} provisioned Product2 id looks invalid: {live_id!r}")
    return live_id


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


def _require_no_tokens(value: Any, label: str) -> None:
    leftover = sorted(set(_TOKEN_RE.findall(json.dumps(value))))
    if leftover:
        raise RuntimeError(f"recipe {RECIPE_ID} {label} has unresolved seed tokens: {leftover}")


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("lookup_table"), dict):
        out.update(ctx.tools.call("harness.lookup_table.snapshot", {}))
    if isinstance(seed.get("salesforce_live"), dict):
        out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
