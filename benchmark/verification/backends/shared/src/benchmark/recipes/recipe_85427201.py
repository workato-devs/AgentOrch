from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_85427201


RECIPE_ID = "85427201"
SEED_TYPE = "salesforce_scheduled_soql_oem_account_backfill_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "salesforce"
TRIGGER_NAME = "scheduled_sobject_soql_query"
TRIGGER_AS = "362d1833"
TRIGGER_SOBJECT = "Workato_User__c"
TRIGGER_CONDITIONS = "OEM_Account__c = null AND OEM_ID__c != null AND Data_Center__c != null"
TRIGGER_FIELD_LIST = "Id\nOEM_ID__c\nOEM_Account__c\nData_Center__c"
SEARCH_STEP_AS = "55b52d05"
COMPOSITE_STEP_AS = "31f0de91"
# Schema-in-seed contract: every variant must declare exactly these custom
# fields (ensure_custom_field provisions them once; they are schema, not
# data, so cleanup never removes them -- 128901328 precedent).
REQUIRED_SCHEMA = [
    {"sobject": "Workato_User__c", "field": "OEM_ID__c", "sf_type": "Text"},
    {"sobject": "Workato_User__c", "field": "OEM_Account__c", "sf_type": "Text"},
    {"sobject": "Workato_User__c", "field": "Data_Center__c", "sf_type": "Text"},
    {"sobject": "Workato_User__c", "field": "Account__c", "sf_type": "Text"},
    {"sobject": "Workato_User__c", "field": "Is_Admin__c", "sf_type": "Checkbox"},
]
TRIGGER_ROW_KEYS = {"Id", "OEM_ID__c", "OEM_Account__c", "Data_Center__c"}
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")

# salesforce.scheduled_sobject_soql_query (as 362d1833, daily 01:20 Pacific,
# batch_size 2000) on Workato_User__c WHERE "OEM_Account__c = null AND
# OEM_ID__c != null AND Data_Center__c != null", field_list Id/OEM_ID__c/
# OEM_Account__c/Data_Center__c. The scheduled trigger is replayed from the
# seeded payload carrying this run's live-created record ids (64106452
# precedent); the trigger conditions are pinned verbatim in the structure
# pins. Body:
#   2  workato_smart_list.create_list 9e56bd7f 'Workato Users' from the
#      trigger record list (primary_index Id; Workato-internal, in-process --
#      smart-list steps never appear in tool_calls, only in the trace)
#   3  workato_smart_list.query_list c8d5b12a:
#      SELECT DISTINCT OEM_ID__c,Data_Center__c FROM Workato Users
#      (output_schema_by=index -> rows {oem_id, data_center}; served by the
#      SQLite smart-list engine, spaced list name included -- probe-verified)
#   4  FOREACH ccb00bb1 over the distinct pairs (repeat_mode simple):
#      5  salesforce.search_sobjects_soql 55b52d05 (LIVE): Workato_User__c
#         WHERE OEM_ID__c = '<oem_id>' AND Data_Center__c = '<data_center>'
#         AND Account__c != null AND Is_Admin__c = true (limit 2000; needs
#         seed.salesforce.strict_soql_conditions -- != null / = true are
#         strict-only operators)
#      6  IF Workato_User__c size > 0 ->
#         7  workato_smart_list.query_list de43c6be:
#            UPDATE Workato Users SET OEM_Account__c = '<first admin
#            Account__c>' WHERE OEM_ID__c = '<oem_id>' AND Data_Center__c =
#            '<data_center>' (current_item outside the search loop = first
#            admin row; AND-compound UPDATE served by the SQLite engine --
#            probe-verified)
#   8  workato_smart_list.query_list 375699c0:
#      SELECT Id,OEM_Account__c FROM Workato Users WHERE OEM_Account__c IS
#      NOT NULL AND OEM_Account__c != '' (SQLite engine -- probe-verified)
#   9  FOREACH ee666d35 over the resolved rows (repeat_mode batch,
#      batch_size 2000; zero iterations on an empty source) ->
#      10 salesforce.composite_update_sobject 31f0de91 (LIVE): records
#         {Id, OEM_Account__c} per batch current_item, allOrNone=false,
#         batch_size 200 -> one salesforce.update_record call per record.
#         Nothing dereferences successRecords/failedRecords, so the
#         composite_update_extended_output seed flag stays OFF.
#
# Branch mapping (per benmark_rules):
# - variant_00 admin_found_updates_users: one (oem_id, dc) pair from two
#   trigger users; a live admin (Account__c set, Is_Admin__c true) matches ->
#   smart-list UPDATE -> final SELECT returns both users -> composite update
#   writes OEM_Account__c on both live records.
# - variant_01 no_admin_no_update: one pair, no admin -> IF-6 false, final
#   SELECT empty -> batch foreach runs ZERO iterations -> no Salesforce write.
# - variant_02 multi_pair_mixed: two distinct pairs -> foreach runs twice;
#   only the admin-backed pair is updated (loop > 1 and both IF outcomes in
#   one run).
#
# World-state consistency: seeded admin records carry OEM_Account__c already
# set (pre-linked), so they would NOT match the trigger conditions -- which
# is exactly why they are absent from the seeded trigger batch. Trigger-batch
# users are seeded with OEM_Account__c unset, faithfully satisfying
# "OEM_Account__c = null AND OEM_ID__c != null AND Data_Center__c != null".
#
# Backends: salesforce LIVE (benchmark-owned records; custom fields via
# schema-in-seed ensure_custom_field); workato_smart_list is Workato-internal
# (in-memory SQLite). Cleanup: harness.salesforce.cleanup in a finally block
# deletes every record this run's seed provisioned (required -- the run
# mutates live rows).

_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "362d1833",
  "provider": "salesforce",
  "name": "scheduled_sobject_soql_query",
  "skip": false,
  "input": {
   "Friday": "true",
   "Monday": "true",
   "Saturday": "true",
   "Sunday": "true",
   "Thursday": "true",
   "Tuesday": "true",
   "Wednesday": "true",
   "batch_size": "2000",
   "conditions": "OEM_Account__c = null AND OEM_ID__c != null AND Data_Center__c != null",
   "day_of_month": "1",
   "field_list": "Id\nOEM_ID__c\nOEM_Account__c\nData_Center__c",
   "hour": "01",
   "minute": "20",
   "schedule": "daily",
   "sobject_name": "Workato_User__c",
   "time_zone": "Pacific Time (US & Canada)"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "9e56bd7f",
  "provider": "workato_smart_list",
  "name": "create_list",
  "skip": false,
  "input": {
   "list_name": "Workato Users",
   "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"362d1833\",\"path\":[\"Workato_User__c\"]}')",
   "primary_index": "Id"
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "c8d5b12a",
  "provider": "workato_smart_list",
  "name": "query_list",
  "skip": false,
  "input": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "output_schema_by": "index",
   "result_schema_json": "[{\"name\":\"oem_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"data_center\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"}]",
   "sql": "SELECT DISTINCT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"9e56bd7f\",\"path\":[\"columns\", \"OEM_ID__c\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"9e56bd7f\",\"path\":[\"columns\", \"Data_Center__c\"]}')} FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"9e56bd7f\",\"path\":[\"list_name\"]}')}"
  }
 },
 {
  "keyword": "foreach",
  "number": 4,
  "as": "ccb00bb1",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"c8d5b12a\",\"path\":[\"rows\"]}')}"
  },
  "repeat_mode": "simple",
  "batch_size": null,
  "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"c8d5b12a\",\"path\":[\"rows\"]}')}"
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "55b52d05",
  "provider": "salesforce",
  "name": "search_sobjects_soql",
  "skip": false,
  "input": {
   "field_list": "Id\nAccount__c\nOEM_Account__c\nOEM_ID__c\nData_Center__c\nIs_Admin__c",
   "limit": "2000",
   "query": "OEM_ID__c = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"ccb00bb1\",\"path\":[\"oem_id\"]}')}' AND Data_Center__c = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"ccb00bb1\",\"path\":[\"data_center\"]}')}' AND Account__c != null AND Is_Admin__c = true",
   "sobject_name": "Workato_User__c"
  }
 },
 {
  "keyword": "if",
  "number": 6,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"55b52d05\",\"path\":[\"Workato_User__c\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "greater_than",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 7,
  "as": "de43c6be",
  "provider": "workato_smart_list",
  "name": "query_list",
  "skip": false,
  "input": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "output_schema_by": "index",
   "result_schema_json": "[{\"name\":\"success\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Success\"}]",
   "sql": "UPDATE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"9e56bd7f\",\"path\":[\"list_name\"]}')}\nSET\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"9e56bd7f\",\"path\":[\"columns\", \"OEM_Account__c\"]}')} = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"55b52d05\",\"path\":[\"Workato_User__c\", {\"path_element_type\": \"current_item\"}, \"Account__c\"]}')}'\nWHERE\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"9e56bd7f\",\"path\":[\"columns\", \"OEM_ID__c\"]}')} = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"ccb00bb1\",\"path\":[\"oem_id\"]}')}' AND #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"9e56bd7f\",\"path\":[\"columns\", \"Data_Center__c\"]}')} = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"ccb00bb1\",\"path\":[\"data_center\"]}')}'"
  }
 },
 {
  "keyword": "action",
  "number": 8,
  "as": "375699c0",
  "provider": "workato_smart_list",
  "name": "query_list",
  "skip": false,
  "input": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "output_schema_by": "index",
   "result_schema_json": "[{\"name\":\"Id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"OEM_Account__c\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"}]",
   "sql": "SELECT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"9e56bd7f\",\"path\":[\"columns\", \"Id\"]}')},#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"9e56bd7f\",\"path\":[\"columns\", \"OEM_Account__c\"]}')}\nFROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"9e56bd7f\",\"path\":[\"list_name\"]}')} WHERE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"9e56bd7f\",\"path\":[\"columns\", \"OEM_Account__c\"]}')} IS NOT NULL AND #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"9e56bd7f\",\"path\":[\"columns\", \"OEM_Account__c\"]}')} != ''"
  }
 },
 {
  "keyword": "foreach",
  "number": 9,
  "as": "ee666d35",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"375699c0\",\"path\":[\"rows\"]}')}"
  },
  "repeat_mode": "batch",
  "batch_size": "2000",
  "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"375699c0\",\"path\":[\"rows\"]}')}"
 },
 {
  "keyword": "action",
  "number": 10,
  "as": "31f0de91",
  "provider": "salesforce",
  "name": "composite_update_sobject",
  "skip": false,
  "input": {
   "advanced_configuration": {
    "allOrNone": "false"
   },
   "batch_size": "200",
   "records": {
    "Id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"ee666d35\",\"path\":[\"batch\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}",
    "OEM_Account__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"ee666d35\",\"path\":[\"batch\", {\"path_element_type\": \"current_item\"}, \"OEM_Account__c\"]}')}",
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"ee666d35\",\"path\":[\"batch\"]}')}",
    "attributes": {
     "Workato_User__c": "Workato_User__c"
    }
   },
   "sobject_name": "Workato_User__c"
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
    "salesforce.search_records",
    "salesforce.update_record",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "salesforce.update_record",
]
EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "smart_list_sqls",
    "final_fields_by_name",
)
OPTIONAL_EXPECT_KEYS = {"case"}


def _structure(node: dict[str, Any]) -> list[dict[str, Any]]:
    pin: dict[str, Any] = {
        "keyword": node.get("keyword"),
        "number": node.get("number"),
        "as": node.get("as"),
        "provider": node.get("provider"),
        "name": node.get("name"),
        "skip": bool(node.get("skip")),
        "input": node.get("input") or {},
    }
    if node.get("keyword") == "foreach":
        pin["repeat_mode"] = node.get("repeat_mode")
        pin["batch_size"] = node.get("batch_size")
        pin["source"] = node.get("source")
    if isinstance(node.get("filter"), dict):
        pin["filter"] = node["filter"]
    out = [pin]
    for child in node.get("block") or []:
        if isinstance(child, dict):
            out.extend(_structure(child))
    return out


def validate_85427201(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger 'as' changed: {raw.get('as')!r}")
    trigger_cfg = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    if str(trigger_cfg.get("sobject_name") or "") != TRIGGER_SOBJECT:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger sobject changed")
    if str(trigger_cfg.get("conditions") or "") != TRIGGER_CONDITIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger SOQL conditions changed")
    if str(trigger_cfg.get("field_list") or "") != TRIGGER_FIELD_LIST:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger field list changed")
    actual = _structure(raw)
    if len(actual) != len(STRUCTURE_PINS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} node count changed: {len(actual)} != {len(STRUCTURE_PINS)}"
        )
    for idx, (got, expected) in enumerate(zip(actual, STRUCTURE_PINS)):
        if got != expected:
            raise RuntimeError(
                f"recipe {RECIPE_ID} node {idx} (step {expected.get('number')}) changed:\n"
                f"expected: {json.dumps(expected, sort_keys=True)}\n"
                f"actual:   {json.dumps(got, sort_keys=True)}"
            )
    actions = [pin for pin in actual if pin["keyword"] == "action"]
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "actions": [
            {
                "number": pin["number"],
                "provider": pin["provider"],
                "name": pin["name"],
                "as": pin["as"],
            }
            for pin in actions
        ],
    }


def seed_85427201(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_85427201(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"salesforce"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    salesforce_section = seed_in.get("salesforce")
    _require_salesforce_section(salesforce_section)
    expect = data.get("expect")
    _require_expect_shape(expect)
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole "
            "run instead of exercising a recipe branch"
        )
    provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": salesforce_section})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    refs = _salesforce_ref_tokens(salesforce_section, provision)
    trigger = _replace_value(trigger, refs)
    _require_resolved_trigger(trigger)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        # Expected update targets / OEM_Account__c values are this run's live
        # seeded record ids, threaded via the same $REF_ID tokens as the
        # trigger (64106452 / 97967767 precedent).
        "expect": _replace_value(deepcopy(expect), refs),
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": refs,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_85427201(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_85427201(raw)
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    if not seed["salesforce_live"].get("strict_soql_conditions"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires strict_soql_conditions in the live state "
            "(the 55b52d05 SOQL uses != null / = true)"
        )
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
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
        # Required cleanup: the run mutates live benchmark-owned records.
        cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
        details["cleanup_response"] = cleanup_response
    if not cleanup_response.get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce cleanup failed: {cleanup_response}")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_85427201(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {TRIGGER_SOBJECT} or not isinstance(trigger.get(TRIGGER_SOBJECT), list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly "
            f"{{'{TRIGGER_SOBJECT}': [rows...]}} (the seeded scheduled-trigger batch)"
        )
    rows = trigger[TRIGGER_SOBJECT]
    if not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the seeded trigger batch must be non-empty (an empty "
            "scheduled poll never starts a job)"
        )
    for row in rows:
        if not isinstance(row, dict) or set(row) != TRIGGER_ROW_KEYS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} every trigger row must carry exactly "
                f"{sorted(TRIGGER_ROW_KEYS)} (the trigger field_list): {row!r}"
            )
        if row.get("OEM_Account__c") is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger rows must carry OEM_Account__c null "
                f"(the trigger conditions select unlinked users only): {row!r}"
            )
        for key in ("OEM_ID__c", "Data_Center__c"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} trigger row {key} must be a non-empty string "
                    f"(trigger conditions require {key} != null): {row!r}"
                )


def _require_salesforce_section(section: Any) -> None:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce")
    if section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true "
            "(the 55b52d05 SOQL uses != null / = true)"
        )
    schema = section.get("schema")
    if schema != REQUIRED_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare exactly the five "
            f"Workato_User__c custom fields: {json.dumps(REQUIRED_SCHEMA)}"
        )
    records = section.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records must be a non-empty list")
    for record in records:
        if not isinstance(record, dict) or not str(record.get("ref") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} every seeded Salesforce record needs a 'ref': {record}")
        if not isinstance(record.get("fields"), dict) or not record["fields"]:
            raise RuntimeError(f"recipe {RECIPE_ID} every seeded record needs explicit fields: {record}")
        sobject = str(record.get("sobject") or "")
        if sobject not in {"Account", TRIGGER_SOBJECT}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seeded records must be Account or {TRIGGER_SOBJECT}: {record}"
            )
        if sobject == TRIGGER_SOBJECT:
            fields = record["fields"]
            if not str(fields.get("Name") or "").strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} every seeded {TRIGGER_SOBJECT} needs a Name "
                    f"(expect.final_fields_by_name is keyed on it): {record}"
                )
            if fields.get("Is_Admin__c") is True:
                for key in ("Account__c", "OEM_Account__c"):
                    if not str(fields.get(key) or "").strip():
                        raise RuntimeError(
                            f"recipe {RECIPE_ID} admin rows must set {key} (Account__c feeds the "
                            f"UPDATE; a pre-linked OEM_Account__c keeps the admin out of the "
                            f"trigger conditions, matching the seeded batch): {record}"
                        )


def _require_expect_shape(expect: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(set(expect) - set(EXPECT_KEYS) - OPTIONAL_EXPECT_KEYS)
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has unexpected keys: {unknown}")
    tools = expect.get("tools")
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tools, list) or not isinstance(tool_expectations, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools/tool_expectations must be lists")
    if len(tools) != len(tool_expectations):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry")
    unknown_tools = sorted(set(tools) - set(ALLOWED_TOOLS))
    if unknown_tools:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools has unknown tools: {unknown_tools}")
    if not tools or tools[0] != "salesforce.search_records":
        raise RuntimeError(
            f"recipe {RECIPE_ID} every path reaches at least the first admin lookup "
            "(the trigger batch is never empty)"
        )
    sqls = expect.get("smart_list_sqls")
    if not isinstance(sqls, list) or len(sqls) < 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.smart_list_sqls must pin the resolved smart-list "
            "SQL sequence (at least the DISTINCT projection and the final SELECT)"
        )
    final_fields = expect.get("final_fields_by_name")
    if not isinstance(final_fields, dict) or not final_fields:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_fields_by_name must pin the final live "
            f"OEM_Account__c value of every seeded {TRIGGER_SOBJECT} record"
        )
    for name, fields in final_fields.items():
        if not isinstance(fields, dict) or "OEM_Account__c" not in fields:
            raise RuntimeError(
                f"recipe {RECIPE_ID} final_fields_by_name[{name!r}] must pin OEM_Account__c "
                "(null for untouched records)"
            )


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


def _require_resolved_trigger(trigger: dict[str, Any]) -> None:
    leftover = _TOKEN_RE.findall(json.dumps(trigger))
    if leftover:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger input has unresolved seed tokens: {leftover}")
    for row in trigger.get(TRIGGER_SOBJECT) or []:
        if not isinstance(row, dict) or not str(row.get("Id") or ""):
            raise RuntimeError(f"recipe {RECIPE_ID} trigger row is missing a live record Id: {row}")


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return ctx.tools.call("harness.salesforce.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
