from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_96155393


RECIPE_ID = "96155393"
SEED_TYPE = "sfdc_event_attendee_menu_variant"
TRACK = "live_salesforce_slack_dynamic_menu"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "dynamic_menu"
TRIGGER_AS = "7114125c"
TABLE_ID = "9658"
RECORD_ID_FIELD = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
ATTENDEES_FIELD = "050f5687_3a9e_4505_a638_85faf3453709"
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_SF_ID_RE = re.compile(r"^[a-zA-Z0-9]{15,18}$")

# Slack dynamic_menu 'Select Contact' (trigger as 7114125c, dereferences
# parameters.record_id only):
#   2  workato_db_table.get_records 2ca3ebce (mock table 9658 '[GTM] [SMA]
#      SFDC Events', filter 'Record ID' 11fbe9a6 eq trigger record_id)
#   3  workato_list.create_list 492b3573, size = FIRST record's Attendees CSV
#      .split(",").length (records current_item OUTSIDE a foreach = first row)
#      -- the recipe's index-loop idiom: N placeholder items
#   4  FOREACH 8492abae over 492b3573.list
#      5 IF Attendees.split(",")[foreach index] not_contains '@workato.com'
#        6 workato_list.accumulate_list_items c699e72d 'Contact_list'
#          {email = Attendees.split(",")[index]}
#   7  logger.log_message 7554529f: Contact_list.pluck('email')
#      .format_map('\\'%s\\'').smart_join(",") -- the quoted IN-list. If NO
#      external attendee ever accumulated, the pluck on the never-run step
#      raises (real Workato: nil NoMethodError) -- every variant must keep at
#      least one external attendee.
#   8  salesforce.search_sobjects_soql 1965e65a Contact, bare condition
#      "Email IN (#{logger message})", limit 150 (LIVE; benchmark-owned
#      records only; seed pins strict_soql_conditions for fail-fast parity)
#   9  IF Contact list_size != '0'
#      10 slack_bot.generate_menu_options 25db2b53 (label 'First Last
#         (Email)', value Id)
#      ELSE 11
#      12 salesforce.search_sobjects_soql ca914d33 Lead, same Email IN query
#      13 slack_bot.generate_menu_options 7bac5ca7 over the Lead rows --
#         note: this action runs even when the Lead search returns 0 rows
#         (an empty options list is the faithful trace)
#   14 IF Contact list_size == '0' AND Lead list_size == '0'
#      15 slack_bot.generate_menu_options c502380f from the raw Contact_list
#         emails (label = value = email)
# Backends: db table 9658 is Workato-internal mock state; Salesforce runs
# LIVE against benchmark-owned Contacts/Leads (seeded per variant, cleaned up
# in finally); generate_menu_options is the controlled Workato menu payload
# (no live Slack post). The recipe never writes any backend: Salesforce and
# the db table must be unchanged after every run.
EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("2ca3ebce", "workato_db_table", "get_records"),
    ("492b3573", "workato_list", "create_list"),
    ("c699e72d", "workato_list", "accumulate_list_items"),
    ("7554529f", "logger", "log_message"),
    ("1965e65a", "salesforce", "search_sobjects_soql"),
    ("25db2b53", "slack_bot", "generate_menu_options"),
    ("ca914d33", "salesforce", "search_sobjects_soql"),
    ("7bac5ca7", "slack_bot", "generate_menu_options"),
    ("c502380f", "slack_bot", "generate_menu_options"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_runtime.create_list",
    "workato_runtime.accumulate_list_items",
    "workato_runtime.log_message",
    "salesforce.search_records",
    "slack_bot.generate_menu_options",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "salesforce.search_records",
    "slack_bot.generate_menu_options",
]
SEED_SECTIONS = {"workato_db_table", "salesforce"}
CONTACT_REQUIRED_FIELDS = ("FirstName", "LastName", "Email")
LEAD_REQUIRED_FIELDS = ("FirstName", "LastName", "Company", "Email")
EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "create_list_size",
    "accumulated_emails",
    "logger_message",
    "salesforce_unchanged",
)

# Verbatim raw-recipe pin: the full normalized node tree (number, keyword,
# provider, name, as, skip, input; foreach carries repeat_mode + source). Any
# drift in the indexed-split formulas, the pluck/format_map/smart_join logger
# chain, the Email IN queries or the three menu templates fails validation
# instead of silently changing groundtruth.
_RAW_PIN_JSON = r"""{"as": "7114125c", "block": [{"as": "2ca3ebce", "block": [], "input": {"02e29f0c-e865-430b-a04b-a9424d43622d": "string", "050f5687-3a9e-4505-a638-85faf3453709": "string", "0eb535d8-8d3a-4675-a817-6510757e8381": "string", "116a65b5-8b6a-456b-af87-a2fc66f857ad": "date_time", "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id", "19f82e28-438b-4da7-a3f4-be7178fb11c4": "string", "331490f8-417a-41ff-926b-842a44d8ff05": "string", "3d42ecd1-1801-4c0e-95b9-b2b9a799f9a2": "date_time", "4b0912f5-b3f7-4268-8581-13a8a1d514f1": "string", "4d4d7b84-57e5-448f-b3e2-940f007e0555": "string", "592f35a5-7e12-4e9f-a0b5-33c2b6782f48": "string", "5d39b548-51cc-4e74-bd1f-76f9d232e7ef": "string", "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time", "66a34cc1-bb95-4667-9727-23195b8b4266": "string", "711c8b93-84a0-4064-9252-a946d97b3ea1": "string", "7aae668d-69d6-4e5b-99ef-3cfed846c060": "string", "7b63fb60-4c64-46c2-8bfe-11b220147af9": "string", "7c6418c5-d62f-42b1-8505-bfc27fde7937": "string", "7e17ef77-d3c4-419c-92c5-be66945864b2": "string", "82dc0fa2-4404-4b80-962d-f81b165b2815": "string", "867ddc68-d351-4452-810e-de4db85c265d": "string", "a1c9c1df-527d-4009-97e5-da51c7e99404": "string", "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time", "a6f1bcd9-e7b0-4522-bea5-9e2e81352d3d": "string", "a9e25e4e-cf01-465a-a37c-e1b3f674ca0f": "string", "cea46df3-ee65-4ba5-b982-3ceb04e36446": "string", "ed47e0af-9345-41a2-b0ff-022727250a11": "string", "f0e39862-bbb6-4e3d-a82c-77aea0c82b01": "string", "f12b132d-ac21-4c1e-8dd5-9a3c46460e7e": "string", "f568cae6-30d4-4dfc-b8fd-ca01145b0666": "string", "ff882c1f-3fb8-48e3-8519-c008b438cd38": "string", "filters": [{"field_id": "11fbe9a6-a16d-4d7e-86ea-afe42ec03005", "op_id": "eq", "value_default": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"7114125c\",\"path\":[\"parameters\", \"record_id\"]}')}"}], "limit": "100", "order_direction": "asc", "table_id": "9658"}, "keyword": "action", "name": "get_records", "number": 2, "provider": "workato_db_table", "skip": false}, {"as": "492b3573", "block": [], "input": {"size": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"2ca3ebce\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"050f5687_3a9e_4505_a638_85faf3453709\"]}').split(\",\").length"}, "keyword": "action", "name": "create_list", "number": 3, "provider": "workato_list", "skip": false}, {"as": "8492abae", "block": [{"as": "", "block": [{"as": "c699e72d", "block": [], "input": {"list_item": {"data": {"email": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"2ca3ebce\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"050f5687_3a9e_4505_a638_85faf3453709\"]}').split(\",\")[_dp('{\"pill_type\":\"foreach_meta\",\"provider\":\"foreach\",\"line\":\"8492abae\",\"key\":\"index\"}')]"}, "schema": "[{\"name\":\"email\",\"type\":\"string\",\"optional\":true,\"label\":\"email\",\"details\":{\"real_name\":\"email\"},\"control_type\":\"text\"}]"}, "name": "Contact_list"}, "keyword": "action", "name": "accumulate_list_items", "number": 6, "provider": "workato_list", "skip": false}], "input": {"conditions": [{"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"2ca3ebce\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"050f5687_3a9e_4505_a638_85faf3453709\"]}').split(\",\")[_dp('{\"pill_type\":\"foreach_meta\",\"provider\":\"foreach\",\"line\":\"8492abae\",\"key\":\"index\"}')]", "operand": "not_contains", "rhs": "@workato.com"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 5, "provider": "", "skip": false}], "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"492b3573\",\"path\":[\"list\"]}')}"}, "keyword": "foreach", "name": "", "number": 4, "provider": "", "repeat_mode": "simple", "skip": false, "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"492b3573\",\"path\":[\"list\"]}')}"}, {"as": "7554529f", "block": [], "input": {"message": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"c699e72d\",\"path\":[\"list_items\"]}').pluck('email').format_map('\\'%s\\'').smart_join(\",\")", "user_logs_enabled": "false"}, "keyword": "action", "name": "log_message", "number": 7, "provider": "logger", "skip": false}, {"as": "1965e65a", "block": [], "input": {"field_list": "Id\nFirstName\nLastName\nEmail", "limit": "150", "query": "Email IN (#{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"7554529f\",\"path\":[\"message\"]}')})", "sobject_name": "Contact"}, "keyword": "action", "name": "search_sobjects_soql", "number": 8, "provider": "salesforce", "skip": false}, {"as": "", "block": [{"as": "25db2b53", "block": [], "input": {"options": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1965e65a\",\"path\":[\"Contact\"]}')}", "label": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1965e65a\",\"path\":[\"Contact\", {\"path_element_type\": \"current_item\"}, \"FirstName\"]}')} #{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1965e65a\",\"path\":[\"Contact\", {\"path_element_type\": \"current_item\"}, \"LastName\"]}')} (#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1965e65a\",\"path\":[\"Contact\", {\"path_element_type\": \"current_item\"}, \"Email\"]}')})", "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1965e65a\",\"path\":[\"Contact\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}"}, "use_option_groups": "false"}, "keyword": "action", "name": "generate_menu_options", "number": 10, "provider": "slack_bot", "skip": false}, {"as": "", "block": [{"as": "ca914d33", "block": [], "input": {"field_list": "Id\nFirstName\nLastName\nEmail", "limit": "150", "query": "Email IN (#{_dp('{\"pill_type\":\"output\",\"provider\":\"logger\",\"line\":\"7554529f\",\"path\":[\"message\"]}')})", "sobject_name": "Lead"}, "keyword": "action", "name": "search_sobjects_soql", "number": 12, "provider": "salesforce", "skip": false}, {"as": "7bac5ca7", "block": [], "input": {"options": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"ca914d33\",\"path\":[\"Lead\"]}')}", "label": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"ca914d33\",\"path\":[\"Lead\", {\"path_element_type\": \"current_item\"}, \"FirstName\"]}')} #{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"ca914d33\",\"path\":[\"Lead\", {\"path_element_type\": \"current_item\"}, \"LastName\"]}')} (#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"ca914d33\",\"path\":[\"Lead\", {\"path_element_type\": \"current_item\"}, \"Email\"]}')})", "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"ca914d33\",\"path\":[\"Lead\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}"}, "use_option_groups": "false"}, "keyword": "action", "name": "generate_menu_options", "number": 13, "provider": "slack_bot", "skip": false}], "input": {}, "keyword": "else", "name": "", "number": 11, "provider": "", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1965e65a\",\"path\":[\"list_size\"]}')}", "operand": "not_equals_to", "rhs": "0"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 9, "provider": "", "skip": false}, {"as": "", "block": [{"as": "c502380f", "block": [], "input": {"options": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"c699e72d\",\"path\":[\"list_items\"]}')}", "label": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"c699e72d\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"email\"]}')}", "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_list\",\"line\":\"c699e72d\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"email\"]}')}"}, "use_option_groups": "false"}, "keyword": "action", "name": "generate_menu_options", "number": 15, "provider": "slack_bot", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"1965e65a\",\"path\":[\"list_size\"]}')}", "operand": "equals_to", "rhs": "0"}, {"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"ca914d33\",\"path\":[\"list_size\"]}')}", "operand": "equals_to", "rhs": "0"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 14, "provider": "", "skip": false}], "input": {"dynamic_menu_name": "Select Contact", "parameters": "[\n  {\n    \"name\": \"record_id\",\n    \"type\": \"string\",\n    \"optional\": false,\n    \"control_type\": \"text\",\n    \"label\": \"Record ID\"\n  }\n]"}, "keyword": "trigger", "name": "dynamic_menu", "number": 1, "provider": "slack_bot", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)


def validate_96155393(raw: dict[str, Any]) -> dict[str, Any]:
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
    actions = _collect_actions(raw)
    actual = [(a.get("as"), a.get("provider"), a.get("name")) for a in actions]
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


def seed_96155393(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_96155393(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    record_id = _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - SEED_SECTIONS)
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    table_seed = seed_in.get("workato_db_table")
    _require_table_section(table_seed, record_id)
    sf_section = seed_in.get("salesforce")
    _require_salesforce_section(sf_section)
    expect = data.get("expect")
    _require_expect_shape(expect)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "workato_db_table": deepcopy(table_seed),
    }
    provision = ctx.tools.call(
        "harness.salesforce.seed_records", {"salesforce": deepcopy(sf_section)}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    refs = _salesforce_ref_tokens(sf_section, provision)
    out["salesforce_live"] = deepcopy(provision["state"])
    out["salesforce_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
    out["salesforce_ref_tokens"] = refs
    resolved_expect = _replace_value(deepcopy(expect), refs)
    _require_no_tokens(resolved_expect, "expect")
    out["expect"] = resolved_expect
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_96155393(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_96155393(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing resolved expect block")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    cleanup_response: dict[str, Any] | None = None
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect"),
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    try:
        details["initial_snapshot"] = _snapshot(ctx)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx)
    finally:
        cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
        details["cleanup_response"] = cleanup_response
    if not (cleanup_response or {}).get("ok"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} Salesforce cleanup left live records: {cleanup_response}"
        )
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_96155393(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> str:
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict) or sorted(trigger.keys()) != ["parameters"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'parameters': {{'record_id': ...}}}}"
        )
    if sorted(parameters.keys()) != ["record_id"]:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters must carry exactly record_id")
    record_id = parameters.get("record_id")
    if not isinstance(record_id, str) or not record_id.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} trigger record_id must be a non-empty string")
    return record_id


def _require_table_section(table_seed: Any, record_id: str) -> None:
    tables = table_seed.get("tables") if isinstance(table_seed, dict) else None
    if not isinstance(tables, dict) or sorted(tables.keys()) != [TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly workato_db_table.tables[{TABLE_ID!r}]"
        )
    rows = tables[TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"recipe {RECIPE_ID} table {TABLE_ID} seed must be a non-empty row list")
    matches: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table {TABLE_ID} rows must be objects")
        for field in (RECORD_ID_FIELD, ATTENDEES_FIELD):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {TABLE_ID} row {idx} needs a non-empty {field}"
                )
        if row[RECORD_ID_FIELD] == record_id:
            matches.append(row)
    if len(matches) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {TABLE_ID} must hold exactly ONE row matching the trigger "
            f"record_id {record_id!r} (create_list reads the FIRST filtered record); got {len(matches)}"
        )
    attendees = matches[0][ATTENDEES_FIELD].split(",")
    if any(not part.strip() for part in attendees):
        raise RuntimeError(
            f"recipe {RECIPE_ID} Attendees CSV must not contain blank entries: "
            f"{matches[0][ATTENDEES_FIELD]!r}"
        )
    if not any("@workato.com" not in part for part in attendees):
        raise RuntimeError(
            f"recipe {RECIPE_ID} every variant needs >=1 external attendee: with ALL attendees "
            "internal, Contact_list never accumulates and the logger pluck on the never-run step "
            "raises (real Workato: nil NoMethodError)"
        )


def _require_salesforce_section(sf_section: Any) -> None:
    if not isinstance(sf_section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} every variant requires seed.salesforce")
    if sf_section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true "
            "(the bare 'Email IN (...)' conditions must be evaluated fail-fast, never dropped)"
        )
    records = sf_section.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.records must be a non-empty list (every variant "
            "seeds at least a decoy so the live searches filter a real population)"
        )
    refs_seen: set[str] = set()
    # Email uniqueness is PER SOBJECT: the same address may deliberately exist
    # on both a Contact and a Lead (the contact-precedence variant proves the
    # ELSE Lead search is short-circuited), but duplicates within one sobject
    # would make the search result multiplicity ambiguous.
    emails_seen: set[tuple[str, str]] = set()
    for record in records:
        if not isinstance(record, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records entries must be objects")
        sobject = str(record.get("sobject") or "")
        ref = str(record.get("ref") or "").strip()
        fields = record.get("fields")
        if sobject not in {"Contact", "Lead"} or not ref or not isinstance(fields, dict):
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded record needs sobject Contact|Lead, ref and "
                f"fields; got {record}"
            )
        if ref in refs_seen:
            raise RuntimeError(f"recipe {RECIPE_ID} duplicate seed ref {ref!r}")
        refs_seen.add(ref)
        required = CONTACT_REQUIRED_FIELDS if sobject == "Contact" else LEAD_REQUIRED_FIELDS
        for key in required:
            if not str(fields.get(key) or "").strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} seeded {sobject} requires explicit {key} "
                    "(the menu label renders 'First Last (Email)')"
                )
        email = str(fields.get("Email") or "")
        if (sobject, email) in emails_seen:
            raise RuntimeError(f"recipe {RECIPE_ID} duplicate seeded {sobject} email {email!r}")
        emails_seen.add((sobject, email))


def _require_expect_shape(expect: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    if expect.get("salesforce_unchanged") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.salesforce_unchanged must be true (the recipe only reads "
            "Salesforce; the live snapshot must be identical before and after)"
        )
    tools = expect.get("tools")
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tools, list) or not isinstance(tool_expectations, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools/tool_expectations must be lists")
    if len(tools) != len(tool_expectations):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry")
    unknown_tools = sorted(set(tools) - set(ALLOWED_TOOLS))
    if unknown_tools:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools has unknown tools: {unknown_tools}")
    if not isinstance(expect.get("accumulated_emails"), list) or not expect["accumulated_emails"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.accumulated_emails must be a non-empty list "
            "(>=1 external attendee is a hard variant rule)"
        )
    if not isinstance(expect.get("logger_message"), str) or not expect["logger_message"]:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.logger_message must pin the quoted IN-list")


def _salesforce_ref_tokens(seed_section: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    live_records = [
        record
        for record in salesforce_snapshot.get("records") or []
        if isinstance(record, dict) and record.get("id") and not record.get("read_only")
    ]
    seed_records = [record for record in seed_section.get("records") or [] if isinstance(record, dict)]
    if len(live_records) != len(seed_records):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed/snapshot record count mismatch: "
            f"{len(seed_records)} seeded vs {len(live_records)} provisioned"
        )
    refs: dict[str, str] = {}
    for idx, record in enumerate(seed_records):
        ref = str(record.get("ref") or "").strip()
        live_id = str(live_records[idx].get("id") or "")
        if not _SF_ID_RE.fullmatch(live_id):
            raise RuntimeError(f"recipe {RECIPE_ID} provisioned record id looks invalid: {live_id!r}")
        if ref:
            refs[f"${ref.upper()}_ID"] = live_id
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


def _require_no_tokens(value: Any, label: str) -> None:
    leftover = sorted(set(_TOKEN_RE.findall(json.dumps(value))))
    if leftover:
        raise RuntimeError(f"recipe {RECIPE_ID} {label} has unresolved seed tokens: {leftover}")


def _normalize_tree(node: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "number": node.get("number"),
        "keyword": node.get("keyword"),
        "provider": node.get("provider") or "",
        "name": node.get("name") or "",
        "as": node.get("as") or "",
        "skip": bool(node.get("skip")),
    }
    if node.get("keyword") == "foreach":
        out["repeat_mode"] = node.get("repeat_mode")
        out["source"] = node.get("source")
    if not out["skip"]:
        out["input"] = node.get("input")
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


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    out: dict[str, Any] = {}
    out.update(ctx.tools.call("harness.workato_db_table.snapshot", {}))
    out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
