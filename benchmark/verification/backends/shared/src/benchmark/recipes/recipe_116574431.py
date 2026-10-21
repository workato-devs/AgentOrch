from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_116574431


RECIPE_ID = "116574431"
SEED_TYPE = "clock_itgenie_process_metrics_rollup_variant"
TRACK = "workato_db_table_itgenie_process_metrics_rollup"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "01defda5"
USAGE_TABLE_ID = "10546"
METRICS_TABLE_ID = "10828"
CREATED_AT_FIELD = "a5612739_5401_4ae7_bd07_782c1a6fb2d1"
USAGE_ROW_FIELDS = {
    "211810bd_e2db_4feb_b058_41337cb362a1",  # Process ID
    "921f48e9_6692_4c1f_93ae_19d2c3a2237b",  # Category
    "351b4fb5_864b_47da_89e6_30433d1ecc70",  # Ticket Resolution Time (int/null)
    "7a290ed0_4881_4521_b5cb_e17c7894b11f",  # Process Execution Time (int)
    CREATED_AT_FIELD,                          # Created at (ISO datetime)
}
DECLARE_PERIOD_AS = "dda3ad96"
DECLARE_LIST_AS = "d8e2644f"
GET_RECORDS_AS = "e9a69756"
INSERT_BATCH_AS = "4e440342"
UPDATE_TOKEN_AS = "58e05796"
DECLARE_AGG_AS = "2286b831"
DECLARE_NON_AS = "cc1734de"
DECLARE_DEFLECTION_AS = "48f84dd7"
ADD_RECORD_AS = "1cbc5c22"
EXECUTED_ACTION_COUNT = 9

# clock.scheduled_event (as 01defda5, monthly day-1 00:00; payload-less
# trigger -- the recipe reads time ONLY via =1.months.ago / =1.days.ago, so
# every variant pins seed.now). Body:
#   2  declare_variable dda3ad96 {period_start = 1.months.ago,
#      period_end = 1.days.ago, next_token (schema-only, stays absent)}
#   3  declare_list d8e2644f 'usage_metrics_list' {process_id,
#      action_category, ticket_resolution_time int, process_execution_time int}
#   4  REPEAT (do-while, as 15d1c62b):
#      5  workato_db_table.get_records e9a69756 table 10546 'ITGenie | Usage
#         Metrics' filter Created-at gte period_start (limit 200, asc),
#         continuation_token = next_token.presence ('' on the first page)
#      6  insert_to_list_batch 4e440342 (____source = records; maps
#         process_id / action_category / ticket_resolution_time /
#         process_execution_time)
#      7  update_variables 58e05796 next_token = continuation_token.presence
#      8  WHILE e9a69756.continuation_token present
#   9  declare_variable 2286b831 {total_processes_count =
#      list.pluck(:process_id).uniq.length, ticketing_processes_count =
#      list.where(action_category: 'ticketing').pluck(:process_id).uniq
#      .length, average_ticket_resolution_time = list.where(
#      "ticket_resolution_time !=": null).pluck(...).length > 0 ?
#      sum/length : skip}
#   10 declare_variable cc1734de non_ticketing = total - ticketing
#   11 declare_variable 48f84dd7 ticket_deflection_rate = total != 0 ?
#      (non*100/total).to_i : skip
#   12 workato_db_table.add_record 1cbc5c22 table 10828 'ITGenie | Process
#      Metrics' {counts, Hours Saved = avg.present? ? (avg*non)/3600000 :
#      skip, Ticket Deflection Rate, Period Start/End}
#
# Branch mapping (per benmark_rules): the step path is LINEAR (always 9
# actions); the branches live in the gte date filter, the while loop, and
# the three formula-level ternaries:
# - variant_00 mixed_metrics_full_record: ticketing rows with resolution
#   times (duplicate process_id P1), non-ticketing rows with null times, one
#   row EXACTLY on period_start (gte includes it) and one 1s older (excluded)
#   -> all ternaries take their value arms; the 10828 record carries all 7
#   fields ('3'/'1'/'2'/'3'/'66' + periods).
# - variant_01 zero_records_all_skip: every row is older than period_start
#   -> 0 records; counts 0/0/0; avg SKIP (no resolved times), deflection
#   SKIP (total == 0 -> the ternary's skip arm), hours SKIP (avg absent ->
#   .present? false). Hours Saved is OMITTED from the add_record args
#   entirely (SKIP), Ticket Deflection Rate resolves MISSING -> null arg ->
#   dropped by the mock's _clean; the stored row carries only counts+periods.
# - variant_02 ticketing_only_no_restimes (different seed.now, Feb period):
#   all rows ticketing with null resolution times -> avg SKIP and hours SKIP,
#   BUT non_ticketing = 0 with total != 0 -> deflection takes its VALUE arm
#   ((0*100/2).to_i = 0 -> '0' in the record).
#
# ENGINE-DEFINED GROUND TRUTH (probed on the current engine):
# - 1.months.ago / 1.days.ago render '%Y-%m-%dT%H:%M:%S+00:00' from seed.now;
#   seeded 10546 created-at values use the SAME ISO form so the gte compare
#   (datetime-parsed by _compare_workato_values) is exact.
# - the while loop is ENGINE-BOUNDED to one iteration: the mock get_records
#   emits no continuation_token (none seeded -- seeding one is FORBIDDEN
#   here because the mock re-serves the full record list per page, which
#   would unfaithfully duplicate list items in insert_to_list_batch);
#   next_token.presence renders '' both in the get args and the update.
# - avg is a STRING ('5400000', integer floor division), non_ticketing is
#   coerced to int by the declare schema's integer_conversion, deflection is
#   an INT (.to_i), hours is a STRING ('3'); single-pill '#{...}' add_record
#   inputs preserve the raw pill type (dry-replay-verified: the count/
#   deflection args are INTS while the hours-saved formula arg stays the
#   string '3'), and the MOCK stringifies values when storing the row -- the
#   expects pin both forms exactly (typed args, string table cells).
#
# Backends: both tables are Workato-internal deterministic mocks (backend
# rule); the per-variant seed fully overwrites state, so reruns are
# deterministic without cleanup. The add_record write to 10828 is the final
# observable and is pinned via the table snapshot.

_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "01defda5",
  "provider": "clock",
  "name": "scheduled_event",
  "skip": false,
  "input": {
   "days_of_month": "1",
   "time_unit": "months",
   "trigger_at": "00:00:00",
   "trigger_every": "1"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "dda3ad96",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "period_end": "=1.days.ago",
     "period_start": "=1.months.ago"
    },
    "schema": "[{\"control_type\":\"text\",\"label\":\"period_start\",\"name\":\"period_start\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"period_start\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"text\",\"label\":\"period_end\",\"name\":\"period_end\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"period_end\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"name\":\"next_token\",\"type\":\"string\",\"optional\":true,\"label\":\"next_token\",\"details\":{\"real_name\":\"next_token\"},\"control_type\":\"text\",\"parent\":[\"variables\",\"data\"]}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "d8e2644f",
  "provider": "workato_variable",
  "name": "declare_list",
  "skip": false,
  "input": {
   "list_item_schema_json": "[{\"name\":\"process_id\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Process ID\"},{\"name\":\"action_category\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Action category\"},{\"name\":\"ticket_resolution_time\",\"type\":\"integer\",\"optional\":true,\"control_type\":\"integer\",\"label\":\"Ticket resolution time\",\"parse_output\":\"integer_conversion\"},{\"name\":\"process_execution_time\",\"type\":\"integer\",\"optional\":true,\"control_type\":\"integer\",\"label\":\"Process execution time\",\"parse_output\":\"integer_conversion\"}]",
   "name": "usage_metrics_list"
  }
 },
 {
  "keyword": "repeat",
  "number": 4,
  "as": "15d1c62b",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {}
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "e9a69756",
  "provider": "workato_db_table",
  "name": "get_records",
  "skip": false,
  "input": {
   "0104b7ef-de3c-4a5f-ba6b-c1ddc4bc6f17": "string",
   "045d2afd-0012-4bbc-a53d-b4008c51179b": "string",
   "11fbe9a6-a16d-4d7e-86ea-afe42ec03005": "id",
   "211810bd-e2db-4feb-b058-41337cb362a1": "string",
   "21ea8e76-5bd7-4fa1-b70b-0fef13c05193": "string",
   "265ff871-ab3e-4c7d-9e1a-31c20636a96c": "string",
   "3323868d-d1f3-4ff1-8b8e-35aed4265162": "boolean",
   "351b4fb5-864b-47da-89e6-30433d1ecc70": "integer",
   "4c816268-1553-4ec9-a667-6322dd4cbc9e": "string",
   "61aae604-a95e-4519-9091-bb0bf754a67f": "date_time",
   "69527934-bfb0-4080-a583-b2c931c8c6f4": "boolean",
   "7469ad3d-9dd3-48cc-b2dd-4c3b5c4afa10": "string",
   "77394afc-f172-4058-86ed-5a786c86d4bb": "string",
   "7a290ed0-4881-4521-b5cb-e17c7894b11f": "integer",
   "921f48e9-6692-4c1f-93ae-19d2c3a2237b": "string",
   "a5612739-5401-4ae7-bd07-782c1a6fb2d1": "date_time",
   "c0d9f3e8-f181-429f-858e-53b43d3a9d39": "string",
   "continuation_token": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"dda3ad96\",\"path\":[\"next_token\"]}').presence",
   "dcca5c9e-25f1-46c6-ae80-ec07f872e9a6": "string",
   "filters": [
    {
     "field_id": "a5612739-5401-4ae7-bd07-782c1a6fb2d1",
     "op_date_time": "gte",
     "value_date_time": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"dda3ad96\",\"path\":[\"period_start\"]}')"
    }
   ],
   "limit": "200",
   "order_direction": "asc",
   "table_id": "10546"
  }
 },
 {
  "keyword": "action",
  "number": 6,
  "as": "4e440342",
  "provider": "workato_variable",
  "name": "insert_to_list_batch",
  "skip": false,
  "input": {
   "list_items": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"e9a69756\",\"path\":[\"records\"]}')}",
    "action_category": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"e9a69756\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"921f48e9_6692_4c1f_93ae_19d2c3a2237b\"]}')}",
    "process_execution_time": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"e9a69756\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"7a290ed0_4881_4521_b5cb_e17c7894b11f\"]}')",
    "process_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"e9a69756\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"211810bd_e2db_4feb_b058_41337cb362a1\"]}')}",
    "ticket_resolution_time": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"e9a69756\",\"path\":[\"records\",{\"path_element_type\":\"current_item\"},\"351b4fb5_864b_47da_89e6_30433d1ecc70\"]}')"
   },
   "location": "end",
   "name": "da12955a-a570-4b7d-a402-090a03f38e12:d8e2644f"
  }
 },
 {
  "keyword": "action",
  "number": 7,
  "as": "58e05796",
  "provider": "workato_variable",
  "name": "update_variables",
  "skip": false,
  "input": {
   "name": "3d84fc22-12da-448e-8313-54473d672c2e:dda3ad96:next_token",
   "next_token": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"e9a69756\",\"path\":[\"continuation_token\"]}').presence"
  }
 },
 {
  "keyword": "while_condition",
  "number": 8,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"e9a69756\",\"path\":[\"continuation_token\"]}')}",
     "operand": "present",
     "rhs": ""
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 9,
  "as": "2286b831",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "average_ticket_resolution_time": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"d8e2644f\",\"path\":[\"list_items\"]}').where(\"ticket_resolution_time !=\": null).pluck(:ticket_resolution_time).length > 0 ? _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"d8e2644f\",\"path\":[\"list_items\"]}').where(\"ticket_resolution_time !=\": null).pluck(:ticket_resolution_time).sum/_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"d8e2644f\",\"path\":[\"list_items\"]}').where(\"ticket_resolution_time !=\": null).pluck(:ticket_resolution_time).length : skip",
     "ticketing_processes_count": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"d8e2644f\",\"path\":[\"list_items\"]}').where(action_category: \"ticketing\").pluck(:process_id).uniq.length",
     "total_processes_count": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"d8e2644f\",\"path\":[\"list_items\"]}').pluck(:process_id).uniq.length"
    },
    "schema": "[{\"control_type\":\"integer\",\"label\":\"total_processes_count\",\"parse_output\":\"integer_conversion\",\"name\":\"total_processes_count\",\"type\":\"integer\",\"optional\":true,\"details\":{\"real_name\":\"total_processes_count\"}},{\"control_type\":\"integer\",\"label\":\"ticketing_processes_count\",\"parse_output\":\"integer_conversion\",\"name\":\"ticketing_processes_count\",\"type\":\"integer\",\"optional\":true,\"details\":{\"real_name\":\"ticketing_processes_count\"}},{\"name\":\"average_ticket_resolution_time\",\"type\":\"string\",\"optional\":true,\"label\":\"average_ticket_resolution_time\",\"details\":{\"real_name\":\"average_ticket_resolution_time\"},\"control_type\":\"text\"}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 10,
  "as": "cc1734de",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "non_ticketing_processes_count": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"total_processes_count\"]}') - _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"ticketing_processes_count\"]}')"
    },
    "schema": "[{\"name\":\"non_ticketing_processes_count\",\"type\":\"integer\",\"optional\":true,\"label\":\"non_ticketing_processes_count\",\"details\":{\"real_name\":\"non_ticketing_processes_count\"},\"control_type\":\"integer\"}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 11,
  "as": "48f84dd7",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "ticket_deflection_rate": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"total_processes_count\"]}') != 0 ? (_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"cc1734de\",\"path\":[\"non_ticketing_processes_count\"]}')*100/_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"total_processes_count\"]}')).to_i : skip"
    },
    "schema": "[{\"name\":\"ticket_deflection_rate\",\"type\":\"string\",\"optional\":true,\"label\":\"ticket_deflection_rate\",\"details\":{\"real_name\":\"ticket_deflection_rate\"},\"control_type\":\"text\"}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 12,
  "as": "1cbc5c22",
  "provider": "workato_db_table",
  "name": "add_record",
  "skip": false,
  "input": {
   "parameters": {
    "41d1a848_0abd_47b4_9ff3_457bce148aa9": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"total_processes_count\"]}')}",
    "522be3c0_cd38_4168_9076_5583ffeea86c": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"average_ticket_resolution_time\"]}').present? ? (_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"average_ticket_resolution_time\"]}') * _dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"cc1734de\",\"path\":[\"non_ticketing_processes_count\"]}')) / 3600000 : skip",
    "6a482238_5023_41fb_9b9d_687c23e2c5ca": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"cc1734de\",\"path\":[\"non_ticketing_processes_count\"]}')}",
    "7bf0cddb_eb7f_463f_9cff_046f3f2aa754": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2286b831\",\"path\":[\"ticketing_processes_count\"]}')}",
    "7f9d71ad_4816_4554_87d6_8b0a1d3cada8": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"48f84dd7\",\"path\":[\"ticket_deflection_rate\"]}')}",
    "b650960e_fab7_433e_a684_9f093f8820a9": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"dda3ad96\",\"path\":[\"period_start\"]}')}",
    "ff6aefdb_b233_47a1_9896_7092bacef527": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"dda3ad96\",\"path\":[\"period_end\"]}')}"
   },
   "table_id": "10828"
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "workato_runtime.declare_list",
    "workato_db_table.get_records",
    "workato_runtime.insert_to_list_batch",
    "workato_runtime.update_variables",
    "workato_db_table.add_record",
]
ALLOWED_TOOLS: list[str] = [
    "workato_db_table.get_records",
    "workato_db_table.add_record",
]
EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "raw_executed_action_count",
    "tools",
    "tool_expectations",
    "period_start",
    "period_end",
    "list_items",
    "variables",
    "final_metrics_rows",
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


def validate_116574431(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_116574431(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_116574431(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (payload-less scheduler tick; "
            "period bounds come from seed.now)"
        )
    now = data.get("now")
    if not isinstance(now, str) or not now.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} variant input must pin 'now' (1.months.ago / 1.days.ago "
            "derive the period bounds from it; wall-clock time is forbidden)"
        )
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"workato_db_table"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    expect = data.get("expect")
    _require_expect_shape(expect)
    _require_db_section(seed_in.get("workato_db_table"))
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "now": now,
        "expect": deepcopy(expect),
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_116574431(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_116574431(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
    if not str(seed.get("now") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing pinned 'now'")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "now": seed.get("now"),
        "expect": expect,
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    details["initial_snapshot"] = _snapshot(ctx)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    details["raw_execution"] = raw_execution
    details["ground_truth"] = _ground_truth(raw_execution)
    details["final_snapshot"] = _snapshot(ctx)
    # Cleanup per the cleanup principle: both tables are per-variant mocks
    # whose state the seed fully overwrites on every run; the 10828 write is
    # snapshot-verified above -- no cleanup step is required for
    # deterministic reruns.
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_116574431(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_expect_shape(expect: Any) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if expect.get("executed_action_count") != len(ALLOWED_TOOLS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} exposes exactly {len(ALLOWED_TOOLS)} benchmark "
            f"tool actions on every variant"
        )
    if expect.get("raw_executed_action_count") != EXECUTED_ACTION_COUNT:
        raise RuntimeError(
            f"recipe {RECIPE_ID} runs a LINEAR 9-action path on every variant "
            "(branches are formula-level ternaries, not step skips)"
        )
    variables = expect.get("variables")
    if not isinstance(variables, dict) or sorted(variables) != [
        DECLARE_AGG_AS,
        DECLARE_DEFLECTION_AS,
        DECLARE_NON_AS,
        DECLARE_PERIOD_AS,
    ]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.variables must pin the four declare steps "
            f"({DECLARE_PERIOD_AS}/{DECLARE_AGG_AS}/{DECLARE_NON_AS}/{DECLARE_DEFLECTION_AS})"
        )


def _require_db_section(section: Any) -> None:
    if not isinstance(section, dict) or not isinstance(section.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.workato_db_table.tables")
    if sorted(section["tables"]) != [USAGE_TABLE_ID, METRICS_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table.tables must declare exactly "
            f"tables {USAGE_TABLE_ID} and {METRICS_TABLE_ID}"
        )
    if "continuation_tokens" in section:
        raise RuntimeError(
            f"recipe {RECIPE_ID} must NOT seed continuation_tokens: the mock re-serves the "
            "full record list per page, which would unfaithfully duplicate list items in "
            "insert_to_list_batch (the while loop is engine-bounded to one iteration)"
        )
    usage_rows = section["tables"][USAGE_TABLE_ID]
    if not isinstance(usage_rows, list) or not usage_rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {USAGE_TABLE_ID} must be a non-empty explicit list "
            "(the zero-records variant seeds rows OLDER than period_start, never an empty table)"
        )
    for row in usage_rows:
        if not isinstance(row, dict) or set(row) != USAGE_ROW_FIELDS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} every 10546 row must declare exactly the five mapped "
                f"columns {sorted(USAGE_ROW_FIELDS)}: {row!r}"
            )
        if not str(row.get(CREATED_AT_FIELD) or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} every 10546 row needs a non-empty Created-at "
                f"({CREATED_AT_FIELD}) for the gte filter: {row!r}"
            )
    metrics_rows = section["tables"][METRICS_TABLE_ID]
    if metrics_rows != []:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {METRICS_TABLE_ID} must be seeded EMPTY (the add_record "
            "write is the observable; pre-seeded rows would blur the snapshot pin)"
        )


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return dict(ctx.tools.call("harness.workato_db_table.snapshot", {}))


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
