from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_117385101


RECIPE_ID = "117385101"
SEED_TYPE = "recipe_function_salesforce_quote_lines_workato_db_variant"
TRACK = "live_salesforce_workato_db_recipe_function"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "51664fed"
SF_LOGICAL_SOBJECT = "SBQQ__QuoteLine__c"
WORKSPACE_TABLE_ID = "13097"
PROVISIONING_TABLE_ID = "22982"

# workato_recipe_function.execute trigger (as 51664fed) with parameters
# {opportunity, workato_user_id, opportunity_owner_sales_team, data_center};
# returns {} (empty return_result). Body:
#   2  salesforce.search_sobjects_soql_v2 904320c5 (LIVE): SELECT
#      SBQQ__EffectiveStartDate__c FROM SBQQ__QuoteLine__c WHERE 6 parent
#      dotted-path conditions (= true x3, = '<opportunity>', (NOT ... LIKE
#      '%Services%'), != 'Bundle Feature') GROUP BY SBQQ__EffectiveStartDate__c
#      -- REQUIRES seed.salesforce.strict_soql_conditions true (the !=, = TRUE
#      and NOT LIKE arms only evaluate faithfully under the strict flag; the
#      strict evaluator strips the trailing GROUP BY before matching)
#   3  declare_variable f91eccae: sales_team_segment_conversion = multi-line
#      if/elsif include? chain over opportunity_owner_sales_team
#      (Enterprise/Embedded/BPO/Agentic, else "Commercial")
#   4  workato_db_table.get_records 18c862e0 (MOCK table 13097 '[AWP] Insights
#      Data - by Workspace and Result') by Secondary ID=opportunity + Workato
#      User Id
#   5  IF 18c862e0.records.size == 0:
#   6    workato_db_table.add_record 92522687 (13097): Secondary ID, Workato
#        User Id, Segment=step-3 variable, Status='Pending', Data Center
#   7  FOREACH b753a02a over 904320c5.records (repeat_mode simple):
#   8    declare_variable 65356e7c: pending_provisioning_status = 'Pending
#        Provisioning' (hardcoded)
#   9    workato_db_table.get_records d621b74b (MOCK table 22982 '[AWP]
#        Workspace Provisioning Request') by Opportunity Id + Workato User Id
#        + Provisioning Date=foreach SBQQ__EffectiveStartDate__c + Provisioning
#        Status=step-8 variable
#  10    IF d621b74b.records.size == 0:
#  11      workato_db_table.add_record ba7671ae (22982): Provisioning Date,
#          Opportunity Id, Workato User Id, Provisioning Status
#  12 workato_recipe_function.return_result f062edf8 (empty {})
#
# Live backend: Salesforce SBQQ__QuoteLine__c -> QuoteLine__c stand-in
# (SALESFORCE_SOBJECT_MAP; mdapi package /tmp/mdapi_117385101, manifest.md
# carries the exact SOBJECT_MAP/FIELD_MAP entries). The 6 parent dotted paths
# (SBQQ__Quote__r.SBQQ__Primary__c/Ordered__c/Opportunity2__c,
# SBQQ__Product__r.IsActive/Product_Sub_Family__c/Family) are FLATTENED
# columns on the stand-in; SALESFORCE_FIELD_MAP keys the DOTTED logical names
# and _logical_aliases re-exposes them flat on read-back, which is exactly
# where strict-SOQL _field_lookup resolves them. Quote_Opportunity2__c is Text
# (trigger passes foreign-org-shaped opportunity id strings), so seeds never
# need live Quote/Product/Opportunity records. Workato DB tables 13097/22982
# stay mocked (Workato-internal backend rule).
#
# Branch-mapping notes (recorded per benmark_rules):
# - variant_00 both IFs true (empty tables), segment Enterprise: 1 quote line
#   -> workspace add + one provisioning add; count 8.
# - variant_01 both IFs false (both rows pre-seeded), segment Embedded; count 6.
# - variant_02 IF5 false (workspace row pre-seeded), foreach x2 both IF10 true,
#   segment BPO; count 10.
# - variant_03 IF5 true, foreach x2 both IF10 false (provisioning rows
#   pre-seeded), segment Agentic; count 9.
# - variant_04 zero quote lines (SOQL matches nothing) -> zero-iteration
#   foreach, IF5 true, else-branch segment Commercial; count 5.
# - ENGINE GAP (probe-confirmed 2026-07-07, still open): eval_if_formula
#   handles an else clause only as a BARE `else` line; the raw formula's
#   inline form `else "Commercial"` (value on the same line) silently yields
#   "" instead of "Commercial". variant_04 pins the FAITHFUL value
#   ("Commercial") and FAILS until the shared engine supports the inline-else
#   form; do not weaken the expect.
# - GROUP-BY fidelity: the harness groups only when an aggregate is present,
#   so GROUP-BY-without-aggregate returns raw rows (no dedupe). All variants
#   seed DISTINCT SBQQ__EffectiveStartDate__c values per opportunity, where
#   raw rows == grouped rows; never seed duplicate dates for one opportunity.
#
# Cleanup: the recipe is READ-ONLY on Salesforce (no SF writes); every live
# record is benchmark-owned and run_117385101 calls harness.salesforce.cleanup
# in finally, failing on leftovers. Workato DB table state is mock-isolated
# per variant; variants are independently seedable.

_STRUCTURE_PINS_JSON = r'''
[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "51664fed",
  "provider": "workato_recipe_function",
  "name": "execute",
  "skip": false,
  "input": {
   "parameters_schema_json": "[{\"name\":\"opportunity\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Opportunity\"},{\"name\":\"workato_user_id\",\"type\":\"string\",\"optional\":false,\"hint\":\"Salesforce record Id\",\"control_type\":\"text\",\"label\":\"Workato user ID\"},{\"name\":\"opportunity_owner_sales_team\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Opportunity owner sales team\"},{\"name\":\"data_center\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Data center\"}]"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "904320c5",
  "provider": "salesforce",
  "name": "search_sobjects_soql_v2",
  "skip": false,
  "input": {
   "limit": "2000",
   "output_schema": "[{\"control_type\":\"text\",\"label\":\"SBQQ effective start date c\",\"type\":\"string\",\"name\":\"SBQQ__EffectiveStartDate__c\",\"optional\":false}]",
   "query": "SELECT SBQQ__EffectiveStartDate__c FROM SBQQ__QuoteLine__c WHERE SBQQ__Quote__r.SBQQ__Primary__c = true AND SBQQ__Quote__r.SBQQ__Ordered__c = true AND SBQQ__Quote__r.SBQQ__Opportunity2__c = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"51664fed\",\"path\":[\"parameters\", \"opportunity\"]}')}' AND SBQQ__Product__r.IsActive = true AND (NOT SBQQ__Product__r.Product_Sub_Family__c LIKE '%Services%') AND\nSBQQ__Product__r.Family != 'Bundle Feature'\nGROUP BY SBQQ__EffectiveStartDate__c"
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "f91eccae",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "sales_team_segment_conversion": "=if _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"51664fed\",\"path\":[\"parameters\",\"opportunity_owner_sales_team\"]}').include?(\"Enterprise\")\n\"Enterprise\"\nelsif _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"51664fed\",\"path\":[\"parameters\",\"opportunity_owner_sales_team\"]}').include?(\"Embedded\")\n\"Embedded\"\nelsif _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"51664fed\",\"path\":[\"parameters\",\"opportunity_owner_sales_team\"]}').include?(\"BPO\")\n\"BPO\"\nelsif _dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"51664fed\",\"path\":[\"parameters\",\"opportunity_owner_sales_team\"]}').include?(\"Agentic\")\n\"Agentic\"\nelse \"Commercial\"\nend"
    },
    "schema": "[{\"name\":\"sales_team_segment_conversion\",\"type\":\"string\",\"optional\":true,\"label\":\"Sales Team Segment Conversion\",\"details\":{\"real_name\":\"Sales Team Segment Conversion\"},\"control_type\":\"text\",\"parent\":[\"variables\",\"data\"]}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "18c862e0",
  "provider": "workato_db_table",
  "name": "get_records",
  "skip": false,
  "input": {
   "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id",
   "29c16206-c1a5-42f3-8aa4-87073dc21630": "integer",
   "546d5c07-6bf9-4f72-9c52-fb831715dc9f": "string",
   "56b997ec-0be7-409a-99f1-b0084dc3357a": "string",
   "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time",
   "65ea3d4a-de75-4abc-ae44-1b5a23e079eb": "string",
   "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time",
   "b86b8ce2-39f2-42e5-b616-4f03290ba87d": "string",
   "ccdf7aea-3336-4970-be67-c80260aca56f": "date",
   "de81e625-ef8b-476a-82be-0be68c2cdc37": "string",
   "f14ff161-7b25-4ff2-910f-1e5809596c9d": "string",
   "filters": [
    {
     "field_id": "546d5c07-6bf9-4f72-9c52-fb831715dc9f",
     "op_default": "eq",
     "value_default": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"51664fed\",\"path\":[\"parameters\", \"opportunity\"]}')}"
    },
    {
     "field_id": "56b997ec-0be7-409a-99f1-b0084dc3357a",
     "op_date": "eq",
     "op_default": "eq",
     "value_default": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"51664fed\",\"path\":[\"parameters\", \"workato_user_id\"]}')}"
    }
   ],
   "limit": "100",
   "order_direction": "asc",
   "table_id": "13097"
  }
 },
 {
  "keyword": "if",
  "number": 5,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"18c862e0\",\"path\":[\"records\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "equals_to",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 6,
  "as": "92522687",
  "provider": "workato_db_table",
  "name": "add_record",
  "skip": false,
  "input": {
   "parameters": {
    "546d5c07_6bf9_4f72_9c52_fb831715dc9f": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"51664fed\",\"path\":[\"parameters\", \"opportunity\"]}')}",
    "56b997ec_0be7_409a_99f1_b0084dc3357a": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"51664fed\",\"path\":[\"parameters\", \"workato_user_id\"]}')}",
    "65ea3d4a_de75_4abc_ae44_1b5a23e079eb": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"f91eccae\",\"path\":[\"sales_team_segment_conversion\"]}')}",
    "de81e625_ef8b_476a_82be_0be68c2cdc37": "Pending",
    "f14ff161_7b25_4ff2_910f_1e5809596c9d": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"51664fed\",\"path\":[\"parameters\", \"data_center\"]}')}"
   },
   "table_id": "13097"
  }
 },
 {
  "keyword": "foreach",
  "number": 7,
  "as": "b753a02a",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"904320c5\",\"path\":[\"records\"]}')}"
  },
  "repeat_mode": "simple",
  "batch_size": null,
  "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"904320c5\",\"path\":[\"records\"]}')}"
 },
 {
  "keyword": "action",
  "number": 8,
  "as": "65356e7c",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "pending_provisioning_status": "Pending Provisioning"
    },
    "schema": "[{\"name\":\"pending_provisioning_status\",\"type\":\"string\",\"optional\":true,\"label\":\"Pending Provisioning Status\",\"details\":{\"real_name\":\"Pending Provisioning Status\"},\"control_type\":\"text\",\"parent\":[\"variables\",\"data\"]}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 9,
  "as": "d621b74b",
  "provider": "workato_db_table",
  "name": "get_records",
  "skip": false,
  "input": {
   "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id",
   "1781f622-1e6e-47f7-809b-eec529aac3ec": "date",
   "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time",
   "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time",
   "d9b56e6b-2f16-4b5a-b579-477989353fee": "string",
   "e573174f-983a-4e33-b3fa-37a84c80c177": "string",
   "f24c2c0a-1b95-4811-8177-694bb8b106c6": "string",
   "filters": [
    {
     "field_id": "d9b56e6b-2f16-4b5a-b579-477989353fee",
     "op_default": "eq",
     "value_default": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"51664fed\",\"path\":[\"parameters\", \"opportunity\"]}')}"
    },
    {
     "field_id": "e573174f-983a-4e33-b3fa-37a84c80c177",
     "op_date": "eq",
     "op_default": "eq",
     "value_default": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"51664fed\",\"path\":[\"parameters\", \"workato_user_id\"]}')}"
    },
    {
     "field_id": "1781f622-1e6e-47f7-809b-eec529aac3ec",
     "op_date": "eq",
     "value_date": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"b753a02a\",\"path\":[\"SBQQ__EffectiveStartDate__c\"]}')}"
    },
    {
     "field_id": "f24c2c0a-1b95-4811-8177-694bb8b106c6",
     "op_default": "eq",
     "value_default": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"65356e7c\",\"path\":[\"pending_provisioning_status\"]}')}"
    }
   ],
   "limit": "100",
   "order_direction": "asc",
   "table_id": "22982"
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
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"d621b74b\",\"path\":[\"records\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "equals_to",
     "rhs": "0"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 11,
  "as": "ba7671ae",
  "provider": "workato_db_table",
  "name": "add_record",
  "skip": false,
  "input": {
   "parameters": {
    "1781f622_1e6e_47f7_809b_eec529aac3ec": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"b753a02a\",\"path\":[\"SBQQ__EffectiveStartDate__c\"]}')}",
    "d9b56e6b_2f16_4b5a_b579_477989353fee": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"51664fed\",\"path\":[\"parameters\", \"opportunity\"]}')}",
    "e573174f_983a_4e33_b3fa_37a84c80c177": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"51664fed\",\"path\":[\"parameters\", \"workato_user_id\"]}')}",
    "f24c2c0a_1b95_4811_8177_694bb8b106c6": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"65356e7c\",\"path\":[\"pending_provisioning_status\"]}')}"
   },
   "table_id": "22982"
  }
 },
 {
  "keyword": "action",
  "number": 12,
  "as": "f062edf8",
  "provider": "workato_recipe_function",
  "name": "return_result",
  "skip": false,
  "input": {}
 }
]
'''

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_runtime.declare_variable",
    "workato_db_table.get_records",
    "workato_db_table.add_record",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_db_table.get_records",
    "workato_db_table.add_record",
    "workato_recipe_function.return_result",
]
TRIGGER_PARAM_KEYS = (
    "opportunity",
    "workato_user_id",
    "opportunity_owner_sales_team",
    "data_center",
)
QUOTE_LINE_FIELD_KEYS = {
    "Name",
    "SBQQ__EffectiveStartDate__c",
    "SBQQ__Quote__r.SBQQ__Primary__c",
    "SBQQ__Quote__r.SBQQ__Ordered__c",
    "SBQQ__Quote__r.SBQQ__Opportunity2__c",
    "SBQQ__Product__r.IsActive",
    "SBQQ__Product__r.Product_Sub_Family__c",
    "SBQQ__Product__r.Family",
}
QUOTE_LINE_BOOL_FIELDS = (
    "SBQQ__Quote__r.SBQQ__Primary__c",
    "SBQQ__Quote__r.SBQQ__Ordered__c",
    "SBQQ__Product__r.IsActive",
)
SEED_SECTIONS = {"salesforce", "workato_db_table"}
SALESFORCE_SECTION_KEYS = {"strict_soql_conditions", "records"}
TABLE_IDS = {WORKSPACE_TABLE_ID, PROVISIONING_TABLE_ID}
EXPECT_KEYS = (
    "executed_action_count",
    "sales_team_segment_conversion",
    "final_table_counts",
    "final_table_contains",
    "tools",
    "tool_expectations",
)
# Corpus lint: recognized tool_expectations keys, and the subset that count as
# value keys (every item must carry at least one).
EXPECTATION_KEYS = {
    "tool", "table_id", "lookup_table_id", "match_fields", "channel",
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
}
EXPECTATION_VALUE_KEYS = {
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
}
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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


def validate_117385101(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_117385101(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_117385101(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - SEED_SECTIONS)
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    sf_section = seed_in.get("salesforce")
    _require_salesforce_section(sf_section)
    db_section = seed_in.get("workato_db_table")
    _require_db_section(db_section)
    _require_expect_shape(data.get("expect"))
    provision = ctx.tools.call(
        "harness.salesforce.seed_records", {"salesforce": deepcopy(sf_section)}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "trigger": trigger,
        "expect": deepcopy(data["expect"]),
        "raw_validation": validation,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "workato_db_table": deepcopy(db_section),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_117385101(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_117385101(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing explicit expect block")
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
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
    if not cleanup_response.get("ok"):
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
    result["verifier"] = verify_117385101(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {"parameters"} or not isinstance(trigger.get("parameters"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'parameters': {{...}}}}"
        )
    parameters = trigger["parameters"]
    if set(parameters) != set(TRIGGER_PARAM_KEYS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must carry exactly "
            f"{sorted(TRIGGER_PARAM_KEYS)}: {sorted(parameters)}"
        )
    for key in TRIGGER_PARAM_KEYS:
        value = parameters.get(key)
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger parameters.{key} must be a non-empty string"
            )


def _require_salesforce_section(sf_section: Any) -> None:
    if not isinstance(sf_section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce")
    unexpected = sorted(set(sf_section) - SALESFORCE_SECTION_KEYS)
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce has unexpected keys: {unexpected}")
    if sf_section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true: the "
            "quote-line SOQL's = TRUE / != / (NOT ... LIKE) arms and the trailing GROUP BY "
            "strip only evaluate faithfully under the strict flag"
        )
    records = sf_section.get("records")
    if not isinstance(records, list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.records must be a list "
            "(explicitly empty for the zero-quote-line branch)"
        )
    for idx, record in enumerate(records):
        if not isinstance(record, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records[{idx}] must be an object")
        if str(record.get("sobject") or "") != SF_LOGICAL_SOBJECT:
            raise RuntimeError(
                f"recipe {RECIPE_ID} only seeds {SF_LOGICAL_SOBJECT}; "
                f"got {record.get('sobject')!r}"
            )
        if not str(record.get("ref") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} seeded quote line [{idx}] needs an explicit ref")
        fields = record.get("fields")
        if not isinstance(fields, dict) or set(fields) != QUOTE_LINE_FIELD_KEYS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seeded quote line [{idx}] fields must be exactly "
                f"{sorted(QUOTE_LINE_FIELD_KEYS)}: {sorted(fields) if isinstance(fields, dict) else fields!r}"
            )
        if not _DATE_RE.fullmatch(str(fields.get("SBQQ__EffectiveStartDate__c") or "")):
            raise RuntimeError(
                f"recipe {RECIPE_ID} seeded quote line [{idx}] SBQQ__EffectiveStartDate__c "
                f"must be an explicit YYYY-MM-DD date: {fields.get('SBQQ__EffectiveStartDate__c')!r}"
            )
        for key in QUOTE_LINE_BOOL_FIELDS:
            if not isinstance(fields.get(key), bool):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} seeded quote line [{idx}] {key} must be a boolean"
                )
        for key in ("Name", "SBQQ__Quote__r.SBQQ__Opportunity2__c",
                    "SBQQ__Product__r.Product_Sub_Family__c", "SBQQ__Product__r.Family"):
            if not isinstance(fields.get(key), str) or not fields[key].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} seeded quote line [{idx}] {key} must be a non-empty string"
                )
    dates_by_opportunity: dict[str, set[str]] = {}
    for record in records:
        fields = record["fields"]
        opportunity = str(fields["SBQQ__Quote__r.SBQQ__Opportunity2__c"])
        date = str(fields["SBQQ__EffectiveStartDate__c"])
        if date in dates_by_opportunity.setdefault(opportunity, set()):
            raise RuntimeError(
                f"recipe {RECIPE_ID} duplicate SBQQ__EffectiveStartDate__c {date!r} for "
                f"opportunity {opportunity!r}: the harness does not dedupe "
                "GROUP-BY-without-aggregate, so duplicate dates would diverge from Workato"
            )
        dates_by_opportunity[opportunity].add(date)


def _require_db_section(db_section: Any) -> None:
    if not isinstance(db_section, dict) or set(db_section) != {"tables"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table must be exactly {{'tables': {{...}}}}"
        )
    tables = db_section.get("tables")
    if not isinstance(tables, dict) or set(tables) != TABLE_IDS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table.tables must declare exactly "
            f"tables {sorted(TABLE_IDS)} (explicitly empty lists included)"
        )
    for table_id, rows in tables.items():
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed.workato_db_table.tables[{table_id}] must be a "
                "list of row objects"
            )


def _require_expect_shape(expect: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(set(expect) - set(EXPECT_KEYS))
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has unexpected keys: {unknown}")
    if not isinstance(expect.get("executed_action_count"), int):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.executed_action_count must be an integer")
    segment = expect.get("sales_team_segment_conversion")
    if not isinstance(segment, str) or not segment.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.sales_team_segment_conversion must be a non-empty string"
        )
    counts = expect.get("final_table_counts")
    if not isinstance(counts, dict) or set(counts) != TABLE_IDS or not all(
        isinstance(value, int) for value in counts.values()
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_table_counts must pin integer row counts for "
            f"exactly tables {sorted(TABLE_IDS)}"
        )
    contains = expect.get("final_table_contains")
    if not isinstance(contains, list) or not contains:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.final_table_contains must be a non-empty list")
    for idx, item in enumerate(contains):
        if (
            not isinstance(item, dict)
            or str(item.get("table_id") or "") not in TABLE_IDS
            or not isinstance(item.get("fields"), dict)
            or not item["fields"]
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.final_table_contains[{idx}] must carry a known "
                "table_id and a non-empty fields object"
            )
    tools = expect.get("tools")
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tools, list) or not isinstance(tool_expectations, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools/tool_expectations must be lists")
    if len(tools) != len(tool_expectations):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry"
        )
    unknown_tools = sorted(set(tools) - set(ALLOWED_TOOLS))
    if unknown_tools:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools has unknown tools: {unknown_tools}")
    if not tools or tools[-1] != "workato_recipe_function.return_result":
        raise RuntimeError(f"recipe {RECIPE_ID} every variant ends with return_result")
    for idx, item in enumerate(tool_expectations):
        if not isinstance(item, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations[{idx}] must be an object")
        if str(item.get("tool") or "") != tools[idx]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.tool_expectations[{idx}].tool must match "
                f"expect.tools[{idx}]"
            )
        unknown_keys = sorted(set(item) - EXPECTATION_KEYS)
        if unknown_keys:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.tool_expectations[{idx}] has unrecognized keys: "
                f"{unknown_keys}"
            )
        if not (set(item) & EXPECTATION_VALUE_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.tool_expectations[{idx}] must carry at least one "
                f"value key ({sorted(EXPECTATION_VALUE_KEYS)})"
            )


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    out: dict[str, Any] = {}
    out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
    out.update(ctx.tools.call("harness.workato_db_table.snapshot", {}))
    out.pop("ok", None)
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
