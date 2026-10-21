from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_110075264


RECIPE_ID = "110075264"
SEED_TYPE = "salesforce_wuo_partial_deprovision_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "1d428569"
WUO_SOBJECT = "Workato_User_Opportunity__c"
USER_SOBJECT = "Workato_User__c"
TABLE_ID = "15307"
RECORD_ID_COL = "11fbe9a6_a16d_4d7e_86ea_afe42ec03005"
WORKATO_USER_ID_COL = "a114ddce_f923_477e_94d2_eb7e09e0170a"
OPPORTUNITY_ID_COL = "a5161116_c154_499f_a7f8_9e4ee8795fc9"
USER_ID_COL = "0c99706e_34ab_4977_ab2f_9d4c1234339f"
DATA_CENTER_COL = "a9fa1ae2_1ede_423d_9a33_27a7c023b316"
OPERATION_COL = "77c98de8_9e62_4af9_b670_ad3140082c93"
EXECUTION_DATE_COL = "8e541e8d_9c3b_4c19_bb58_9800a06656c6"
SEARCH_PRIMARY_AS = "074b5f04"
PRIMARY_UPSERT_AS = "305d7b23"
SIBLING_SEARCH_AS = "e580f7d9"
COMPOSITE_AS = "b623d730"
STOP_AS = "58a5baa4"
# Schema-in-seed contract: mdapi Workato_User_Opportunity__c deployed
# 2026-07-07 (Opportunity__c Text, Workato_User__c Lookup(Workato_User__c),
# Provisioning_Status__c Text, Text name field) with FLS; the seed schema
# section (ensure_custom_field) re-ensures the three Workato_User__c columns
# the relationship pills dereference.
REQUIRED_SCHEMA = [
    {"sobject": "Workato_User__c", "field": "User_ID__c", "sf_type": "Text"},
    {"sobject": "Workato_User__c", "field": "Workspace_ID__c", "sf_type": "Text"},
    {"sobject": "Workato_User__c", "field": "Data_Center__c", "sf_type": "Text"},
]
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")

# workato_recipe_function.execute (as 1d428569; the only dereferenced
# parameter is workato_user_opportunity_id):
#   2  salesforce.search_sobjects 074b5f04 (LIVE): Workato_User_Opportunity__c
#      by Id = param (limit 2000; the Workato_User__r$ field_list entries are
#      UI metadata -- the nested Workato_User__r pills are served by
#      seed.salesforce.relationship_expansion over the owned Workato_User__c
#      lookup)
#   3  workato_db_table.upsert_record 305d7b23 (table 15307 '[AWP] Workspace
#      Deprovisioning Operation Log', primary field workato_user_id
#      a114ddce...): workato_user_id = current.Workato_User__c, opportunity_id
#      = current.Opportunity__c, user_id = Workato_User__r.User_ID__c,
#      data_center = Workato_User__r.Data_Center__c, operation_executed
#      'Downgrade', execution_date = job_created_at.to_date (probe-verified
#      -> '2026-07-07' string; every variant pins seed.job_context).
#      DESIGN: every variant seeds table 15307 with the primary user's
#      existing log row (record-id column set) so this upsert takes the
#      UPDATE arm and the step-12 record-id pill resolves deterministically;
#      the mock only carries the Workato record-id column on seeded rows
#      (created rows expose _row_id, not the 11fbe9a6 column), so the
#      create-arm return value is not faithfully representable -- the INSERT
#      arm is still exercised by the sibling loop upserts, whose record ids
#      are never read.
#   4  salesforce.update_sobject b9b06b94 (LIVE): id = trigger param,
#      Provisioning_Status__c = 'Partially Deprovisioned'
#   5  salesforce.search_sobjects_soql e580f7d9 (LIVE, limit 150):
#      Opportunity__c = current.Opportunity__c AND
#      Workato_User__r.Workspace_ID__c = current.Workato_User__r.User_ID__c
#      AND Workato_User__r.Data_Center__c = current...Data_Center__c AND
#      Id != current.Id -- the recipe quirk (sibling WORKSPACE id compared to
#      the primary's USER id) is deliberately encoded in every seed; the
#      4-term compound WHERE with dotted relationship paths needs
#      seed.salesforce.strict_soql_conditions.
#   IF 6 (e580f7d9 list_size > 0):
#     7  salesforce.composite_update_sobject b623d730 (LIVE): ____source =
#        sibling records, {Id, Provisioning_Status__c 'Partially
#        Deprovisioned'}, allOrNone=false, batch_size 200 -> one
#        salesforce.update_record call per sibling;
#        seed.composite_update_extended_output (set unconditionally by the
#        seeder) exposes the successRecords/failedRecords shape steps 8/10
#        dereference.
#     FOREACH 8 (0a06a593 over successRecords, repeat_mode simple):
#       9  workato_db_table.upsert_record 5219854f (same table/primary key):
#          sibling fields via e580f7d9.where(Id: foreach.Id).pluck(...).first
#          (probe-verified) -> INSERTs one log row per sibling user
#     IF 10 (failedRecords.current_item.errors.size > 0):
#       11 STOP 58a5baa4 stop_with_error=true.  The failure path is exercised
#          with a post-resolution simulated connector fault on a benchmark-
#          owned sibling update.  Because allOrNone=false catches that child
#          failure, it faithfully appears in failedRecords without turning
#          the composite action itself into an unhandled recipe error.
#   12 workato_recipe_function.return_result 8bc5206e:
#      result.data_table_record_id = 305d7b23.record.<record-id column>
#
# Branch mapping (per benmark_rules):
# - variant_00 related_workspaces_updated: 2 matching siblings (+ wrong-DC
#   and wrong-Opportunity decoys) -> IF 6 true -> composite updates both ->
#   2 loop upserts -> return the primary log record id.
# - variant_01 no_related_workspaces: only a wrong-DC decoy -> e580f7d9
#   returns 0 -> IF 6 false -> steps 2-5 + return only.
# - variant_02 single_sibling_id_exclusion: the primary user's OWN
#   Workspace_ID__c equals its User_ID__c, so the primary WUO matches all
#   three field terms and is excluded ONLY by Id != -> exactly 1 sibling ->
#   1-iteration loop (loop-size variation + Id-term proof).
#
# Backends: salesforce LIVE (owned Workato_User__c / Workato_User_Opportunity
# __c records; cleanup deletes them in a finally block -- the run MUTATES
# live rows). workato_db_table 15307 is the Workato-internal per-variant mock
# (the seed fully overwrites it each run -> deterministic reruns).

_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "1d428569",
  "provider": "workato_recipe_function",
  "name": "execute",
  "skip": false,
  "input": {
   "parameters_schema_json": "[{\"name\":\"workato_user_opportunity_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Workato user opportunity ID\"}]",
   "result_schema_json": "[{\"name\":\"data_table_record_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Data table record ID\"}]"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "074b5f04",
  "provider": "salesforce",
  "name": "search_sobjects",
  "skip": false,
  "input": {
   "Id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"1d428569\",\"path\":[\"parameters\", \"workato_user_opportunity_id\"]}')}",
   "field_list": "Id\nOpportunity__c\nWorkato_User__c\nWorkato_User__r$Workato User.User_ID__c\nWorkato_User__r$Workato User.Data_Center__c\nProvisioning_Status__c\nWorkato_User__r$Workato User.Workspace_ID__c\nWorkato_User__r$Workato User.Federated_Account_ID__c\nWorkato_User__r$Workato User.OEM_ID__c\nWorkato_User__r$Workato User.Is_Admin__c",
   "limit": "2000",
   "sobject_name": "Workato_User_Opportunity__c",
   "table_list": "Workato_User__c\nOpportunity"
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "305d7b23",
  "provider": "workato_db_table",
  "name": "upsert_record",
  "skip": false,
  "input": {
   "parameters": {
    "0c99706e_34ab_4977_ab2f_9d4c1234339f": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"074b5f04\",\"path\":[\"Workato_User_Opportunity__c\", {\"path_element_type\": \"current_item\"}, \"Workato_User__r\", \"User_ID__c\"]}')}",
    "77c98de8_9e62_4af9_b670_ad3140082c93": "Downgrade",
    "8e541e8d_9c3b_4c19_bb58_9800a06656c6": "=_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_created_at\"]}').to_date",
    "a114ddce_f923_477e_94d2_eb7e09e0170a": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"074b5f04\",\"path\":[\"Workato_User_Opportunity__c\", {\"path_element_type\": \"current_item\"}, \"Workato_User__c\"]}')}",
    "a5161116_c154_499f_a7f8_9e4ee8795fc9": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"074b5f04\",\"path\":[\"Workato_User_Opportunity__c\", {\"path_element_type\": \"current_item\"}, \"Opportunity__c\"]}')}",
    "a9fa1ae2_1ede_423d_9a33_27a7c023b316": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"074b5f04\",\"path\":[\"Workato_User_Opportunity__c\", {\"path_element_type\": \"current_item\"}, \"Workato_User__r\", \"Data_Center__c\"]}')}"
   },
   "primary_field_id": "a114ddce-f923-477e-94d2-eb7e09e0170a",
   "table_id": "15307"
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "b9b06b94",
  "provider": "salesforce",
  "name": "update_sobject",
  "skip": false,
  "input": {
   "Provisioning_Status__c": "Partially Deprovisioned",
   "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"1d428569\",\"path\":[\"parameters\", \"workato_user_opportunity_id\"]}')}",
   "sobject_name": "Workato_User_Opportunity__c"
  }
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "e580f7d9",
  "provider": "salesforce",
  "name": "search_sobjects_soql",
  "skip": false,
  "input": {
   "field_list": "Id\nOpportunity__c\nWorkato_User__c\nWorkato_User__r$Workato User.User_ID__c\nWorkato_User__r$Workato User.Workspace_ID__c\nWorkato_User__r$Workato User.Data_Center__c",
   "limit": "150",
   "query": "Opportunity__c = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"074b5f04\",\"path\":[\"Workato_User_Opportunity__c\", {\"path_element_type\": \"current_item\"}, \"Opportunity__c\"]}')}' AND Workato_User__r.Workspace_ID__c = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"074b5f04\",\"path\":[\"Workato_User_Opportunity__c\", {\"path_element_type\": \"current_item\"}, \"Workato_User__r\", \"User_ID__c\"]}')}' AND Workato_User__r.Data_Center__c = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"074b5f04\",\"path\":[\"Workato_User_Opportunity__c\", {\"path_element_type\": \"current_item\"}, \"Workato_User__r\", \"Data_Center__c\"]}')}' AND Id != '#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"074b5f04\",\"path\":[\"Workato_User_Opportunity__c\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}'",
   "sobject_name": "Workato_User_Opportunity__c",
   "table_list": "Workato_User__c"
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
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"e580f7d9\",\"path\":[\"list_size\"]}')}",
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
  "as": "b623d730",
  "provider": "salesforce",
  "name": "composite_update_sobject",
  "skip": false,
  "input": {
   "advanced_configuration": {
    "allOrNone": "false"
   },
   "batch_size": "200",
   "records": {
    "Id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"e580f7d9\",\"path\":[\"Workato_User_Opportunity__c\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}",
    "Provisioning_Status__c": "Partially Deprovisioned",
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"e580f7d9\",\"path\":[\"Workato_User_Opportunity__c\"]}')}",
    "attributes": {
     "Workato_User_Opportunity__c": "Workato_User_Opportunity__c"
    }
   },
   "sobject_name": "Workato_User_Opportunity__c"
  }
 },
 {
  "keyword": "foreach",
  "number": 8,
  "as": "0a06a593",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"b623d730\",\"path\":[\"successRecords\"]}')}"
  },
  "repeat_mode": "simple",
  "batch_size": null,
  "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"b623d730\",\"path\":[\"successRecords\"]}')}"
 },
 {
  "keyword": "action",
  "number": 9,
  "as": "5219854f",
  "provider": "workato_db_table",
  "name": "upsert_record",
  "skip": false,
  "input": {
   "parameters": {
    "0c99706e_34ab_4977_ab2f_9d4c1234339f": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"e580f7d9\",\"path\":[\"Workato_User_Opportunity__c\"]}').where(Id: _dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"0a06a593\",\"path\":[\"Id\"]}')).pluck(['Workato_User__r', 'User_ID__c']).first",
    "77c98de8_9e62_4af9_b670_ad3140082c93": "Downgrade",
    "8e541e8d_9c3b_4c19_bb58_9800a06656c6": "=_dp('{\"pill_type\":\"job_context\",\"path\":[\"job_created_at\"]}').to_date",
    "a114ddce_f923_477e_94d2_eb7e09e0170a": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"e580f7d9\",\"path\":[\"Workato_User_Opportunity__c\"]}').where(Id: _dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"0a06a593\",\"path\":[\"Id\"]}')).pluck('Workato_User__c').first",
    "a5161116_c154_499f_a7f8_9e4ee8795fc9": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"074b5f04\",\"path\":[\"Workato_User_Opportunity__c\", {\"path_element_type\": \"current_item\"}, \"Opportunity__c\"]}')}",
    "a9fa1ae2_1ede_423d_9a33_27a7c023b316": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"e580f7d9\",\"path\":[\"Workato_User_Opportunity__c\"]}').where(Id: _dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"0a06a593\",\"path\":[\"Id\"]}')).pluck(['Workato_User__r','Data_Center__c']).first"
   },
   "primary_field_id": "a114ddce-f923-477e-94d2-eb7e09e0170a",
   "table_id": "15307"
  }
 },
 {
  "keyword": "if",
  "number": 10,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"b623d730\",\"path\":[\"failedRecords\", {\"path_element_type\": \"current_item\"}, \"errors\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "greater_than",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "stop",
  "number": 11,
  "as": "58a5baa4",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "stop_reason": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"b623d730\",\"path\":[\"failedRecords\",{\"path_element_type\":\"current_item\"},\"errors\"]}').pluck('message').join(\"; \")",
   "stop_with_error": "true"
  }
 },
 {
  "keyword": "action",
  "number": 12,
  "as": "8bc5206e",
  "provider": "workato_recipe_function",
  "name": "return_result",
  "skip": false,
  "input": {
   "result": {
    "data_table_record_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"305d7b23\",\"path\":[\"record\", \"11fbe9a6_a16d_4d7e_86ea_afe42ec03005\"]}')}"
   }
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_db_table.upsert_record",
    "salesforce.update_record",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_db_table.upsert_record",
    "salesforce.update_record",
    "workato_recipe_function.return_result",
]
EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "final_table_15307",
    "final_provisioning_status",
    "final_result",
)


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


def validate_110075264(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if raw.get("as") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger 'as' changed: {raw.get('as')!r}")
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


def seed_110075264(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_110075264(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"salesforce", "workato_db_table"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    _require_salesforce_section(seed_in.get("salesforce"))
    _require_db_table_section(seed_in.get("workato_db_table"))
    job_context = data.get("job_context")
    if not isinstance(job_context, dict) or not str(job_context.get("job_created_at") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} every variant must pin job_context.job_created_at "
            "(execution_date = job_created_at.to_date)"
        )
    expect = data.get("expect")
    _require_expect_shape(expect)
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole "
            "run instead of exercising a recipe branch; use the narrowly "
            "validated simulated_action_faults child-update mechanism instead)"
        )
    action_faults = data.get("simulated_action_faults")
    if action_faults is not None:
        if not isinstance(action_faults, list) or not action_faults:
            raise RuntimeError(
                f"recipe {RECIPE_ID} simulated_action_faults must be a non-empty list"
            )
        for fault in action_faults:
            if (
                not isinstance(fault, dict)
                or fault.get("tool") != "salesforce.update_record"
                or not isinstance(fault.get("args"), dict)
                or not str(fault.get("error") or "")
            ):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} only permits explicit Salesforce update faults"
                )
    provision = ctx.tools.call(
        "harness.salesforce.seed_records", {"salesforce": deepcopy(seed_in["salesforce"])}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    refs = _salesforce_ref_tokens(seed_in["salesforce"], provision)
    trigger = _replace_value(trigger, refs)
    _require_resolved(trigger)
    # The seeded operation-log row is keyed on the LIVE Workato_User__c record
    # id created this run: thread it through the same $REF tokens.
    db_table = _replace_value(deepcopy(seed_in["workato_db_table"]), refs)
    _require_resolved(db_table)
    resolved_expect = _replace_value(deepcopy(expect), refs)
    _require_resolved(resolved_expect)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": resolved_expect,
        "workato_db_table": db_table,
        # Workato's composite update always exposes successRecords/
        # failedRecords; steps 8 and 10 dereference them, so the faithful
        # executor shape is opted in for every variant (88707765 precedent).
        "composite_update_extended_output": True,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": refs,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    if action_faults is not None:
        out["_simulated_action_faults"] = _replace_value(
            deepcopy(action_faults), refs
        )
    return attach_variant(out, ctx)


def run_110075264(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_110075264(raw)
    live_state = seed.get("salesforce_live")
    if not isinstance(live_state, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    if not live_state.get("strict_soql_conditions") or not live_state.get("expand_relationships"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires strict_soql_conditions AND relationship_expansion "
            "in the live state (4-term dotted WHERE + Workato_User__r pills)"
        )
    if seed.get("composite_update_extended_output") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must carry composite_update_extended_output: true "
            "(faithful successRecords/failedRecords shape)"
        )
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
    if not isinstance(seed.get("job_context"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing job_context")
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
        "job_context": deepcopy(seed.get("job_context")),
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
    result["verifier"] = verify_110075264(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {"parameters"} or not isinstance(trigger.get("parameters"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'parameters': {{...}}}}"
        )
    parameters = trigger["parameters"]
    if set(parameters) != {"workato_user_opportunity_id"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must carry exactly "
            "workato_user_opportunity_id"
        )
    value = parameters.get("workato_user_opportunity_id")
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} workato_user_opportunity_id must be a non-empty string "
            "(the seeded primary WUO's live id token)"
        )


def _require_salesforce_section(section: Any) -> None:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce")
    if section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true "
            "(the e580f7d9 4-term compound WHERE is strict-only)"
        )
    if section.get("relationship_expansion") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.relationship_expansion must be true "
            "(Workato_User__c lookup -> nested Workato_User__r pills)"
        )
    if section.get("schema") != REQUIRED_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare exactly "
            f"{json.dumps(REQUIRED_SCHEMA)}"
        )
    records = section.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records must be a non-empty list")
    for record in records:
        if not isinstance(record, dict) or not str(record.get("ref") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded Salesforce record needs a 'ref': {record}"
            )
        fields = record.get("fields")
        if not isinstance(fields, dict) or not fields:
            raise RuntimeError(f"recipe {RECIPE_ID} every seeded record needs explicit fields: {record}")
        sobject = str(record.get("sobject") or "")
        if sobject not in {USER_SOBJECT, WUO_SOBJECT}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seeded records must be {USER_SOBJECT} or {WUO_SOBJECT}: {record}"
            )
        if not str(fields.get("Name") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded record needs an explicit Name "
                f"(mdapi Text name field): {record}"
            )
        required = (
            ("User_ID__c", "Workspace_ID__c", "Data_Center__c")
            if sobject == USER_SOBJECT
            else ("Opportunity__c", "Workato_User__c", "Provisioning_Status__c")
        )
        for key in required:
            if not str(fields.get(key) or "").strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {sobject} seed must set {key} explicitly: {record}"
                )


def _require_db_table_section(section: Any) -> None:
    if not isinstance(section, dict) or set(section) != {"tables"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table must be exactly {{'tables': {{...}}}}"
        )
    tables = section.get("tables")
    if not isinstance(tables, dict) or set(tables) != {TABLE_ID}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly workato_db_table table {TABLE_ID}"
        )
    rows = tables.get(TABLE_ID)
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {TABLE_ID} must be seeded with the primary user's "
            "existing operation-log row (the step-12 record-id pill reads the Workato "
            "record-id column, which the mock only carries on seeded rows)"
        )
    primary_rows = [
        row
        for row in rows
        if isinstance(row, dict)
        and str(row.get(RECORD_ID_COL) or "").strip()
        and str(row.get(WORKATO_USER_ID_COL) or "").strip()
    ]
    if len(primary_rows) != len(rows):
        raise RuntimeError(
            f"recipe {RECIPE_ID} every seeded {TABLE_ID} row must set both the record-id "
            f"column ({RECORD_ID_COL}) and workato_user_id ({WORKATO_USER_ID_COL})"
        )


def _require_expect_shape(expect: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(
        set(expect)
        - (
            set(EXPECT_KEYS)
            | {"raw_executed_action_count", "stopped", "stop_reason"}
        )
    )
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
    stopped = expect.get("stopped") is True
    if not tools or tools[0] != "salesforce.search_records" or (
        not stopped and tools[-1] != "workato_recipe_function.return_result"
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} every path starts with the primary WUO search and "
            "non-stopped paths end with return_result"
        )
    if not isinstance(expect.get("final_table_15307"), list) or not expect["final_table_15307"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_table_15307 must pin the exact final mock "
            "table rows"
        )
    status = expect.get("final_provisioning_status")
    if not isinstance(status, dict) or not status:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_provisioning_status must pin the LIVE post-run "
            "Provisioning_Status__c of every seeded WUO record (decoys included)"
        )
    final_result = expect.get("final_result")
    if not stopped and (
        not isinstance(final_result, dict)
        or not str(final_result.get("data_table_record_id") or "").strip()
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_result.data_table_record_id must pin the "
            "seeded primary log row's record id"
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
        # Keys are replaced too: expect.final_provisioning_status is keyed by
        # the seeded WUO records' $REF tokens.
        return {
            _replace_value(key, refs): _replace_value(item, refs)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_replace_value(item, refs) for item in value]
    if isinstance(value, str):
        out = value
        for token, replacement in refs.items():
            out = out.replace(token, replacement)
        return out
    return value


def _require_resolved(value: Any) -> None:
    leftover = _TOKEN_RE.findall(json.dumps(value))
    if leftover:
        raise RuntimeError(f"recipe {RECIPE_ID} unresolved seed tokens remain: {sorted(set(leftover))}")


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    out: dict[str, Any] = {}
    out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
    out.update(ctx.tools.call("harness.workato_db_table.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
