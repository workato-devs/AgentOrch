from __future__ import annotations

import json
import re
import time
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_89731033


RECIPE_ID = "89731033"
SEED_TYPE = "api_platform_open_opportunities_deal_type_variant"
TRACK = "live_salesforce_api_platform_open_opportunities"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "d3598ac7"
LOOKUP_TABLE_ID = "3304617"
SOQL_STEP_AS = "aef0ef3e"
PAGINATION_SOQL_STEP_AS = "63a33a39"
FILTER_DECLARE_STEP_AS = "83dfe49e"
BATCH_SIZE_DECLARE_STEP_AS = "27d909cb"
MAX_BATCH_SIZE = 2000
# Benchmark-owned live fixtures intentionally stay far below the connector's
# pagination boundary.  This is a safety/cost cap on seeded test data, not a
# claim that the production branch is logically unreachable.
MAX_SEED_OPPORTUNITIES = 100
OPPORTUNITY_SEED_FIELDS = {"Name", "StageName", "CloseDate", "Type"}
# Org-assigned LastModifiedDate must strictly decrease across the recipe's
# ORDER BY LastModifiedDate DESC ground truth; audit-field writes are disabled
# in the benchmark org, so a real pause between seed phases is the only
# faithful spacing (precedent recipe_88704851 CREATED_DATE_SPACING_SECONDS).
LMD_SPACING_SECONDS = 1.2
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_SF_ID_RE = re.compile(r"^[a-zA-Z0-9]{15,18}$")

# workato_api_platform.receive_request (as d3598ac7; request {deal_type
# optional ('Renew, Expand or Land'), account_type optional-unused};
# response 200 {opportunities: [{id, name}]}). Body (linear, no try/catch,
# no stop):
#   2  lookup_table.search_entries 839fdf7a (table 3304617 '[CSCON] Deal
#      Types': col1 Name, col2 SOQL Filter) by col1 = request.deal_type
#   3  declare_variable 83dfe49e deal_type_filter =
#        if entries.first.entry.col2.present?
#          "AND (" + col2 + ")"  else  ""  end
#      (probe-verified: EMPTY entries -> entries.first resolves MISSING ->
#      .present? false -> "" — the no-lookup-match path and the blank-col2
#      path both inject nothing)
#   4  declare_variable 27d909cb max_batch_size = 2000 (schema parse_output
#      integer_conversion -> the engine stores int 2000; the SOQL limit arg
#      resolves to int 2000)
#   5  declare_list d2c4c0f3 'records' {id, name}
#   6  salesforce.search_sobjects_soql_v2 aef0ef3e (LIVE):
#        SELECT Id, Name, Type, LastModifiedDate FROM Opportunity
#        WHERE IsClosed = false #{deal_type_filter}
#        ORDER BY LastModifiedDate DESC        (limit = max_batch_size pill)
#      — REQUIRES seed.salesforce.strict_soql_conditions true ('IsClosed =
#      false' keyword leaf + injected 'AND (Type = ...)' + ORDER BY applied)
#   7  insert_to_list_batch 4a5c5db8 records <- ____source aef0ef3e.records
#      {id: Id, name: Name}, location end
#   8  IF aef0ef3e.records.{size} equals_to max_batch_size:
#      9  search_sobjects_soql_v2 63a33a39 (same SOQL, offset 2000) +
#      10 insert_to_list_batch 9df0d960
#      — DEAD-IN-BENCHMARK: reachable only with exactly 2000 open owned
#      opportunities; seeding 2000 live records is prohibitive. The branch is
#      recorded as proven-unreachable; the verifier pins that exactly ONE
#      SOQL search (as aef0ef3e) executes.
#   11 workato_api_platform.return_response 86b1eaac (200, opportunities
#      ____source = d2c4c0f3.list_items {id, name}) — terminal.
#
# Branch-mapping notes (recorded per benmark_rules):
# - variant_00 renew_filtered: deal_type 'Renew' -> col2 "Type = 'Renewal'"
#   appended -> only OPEN Renewal owned opps returned, LastModifiedDate DESC
#   (2 matches seeded in phases 1 and 3 -> response order [phase3, phase1];
#   an open New Business opp and a Closed-Won Renewal opp are live decoys).
# - variant_01 blank_filter_all_open: deal_type 'Land' matches an entry with
#   BLANK col2 -> present? false -> filter '' -> ALL open owned opps
#   regardless of Type ([phase3, phase2, phase1]); a closed decoy excluded.
# - variant_02 no_lookup_match: deal_type 'Expand' absent from the table ->
#   entries [] -> entries.first MISSING -> filter '' (distinct proof of the
#   empty-entries arm; result_count 0 on the lookup) -> all open owned opps.
# - variant_03 zero_open_opps: deal_type 'Renew' with matching lookup row,
#   but only closed opps + an open New Business decoy are seeded -> the
#   filtered query returns [] -> batch insert of an empty source -> response
#   opportunities [].
#
# LastModifiedDate DESC determinism: SF timestamps have 1s granularity, so
# every response-order-sensitive record is seeded in its OWN phase and phases
# are provisioned LMD_SPACING_SECONDS apart (later phase = newer timestamp =
# earlier in the DESC response). The seeder enforces one response ref per
# phase + reverse-phase response order; the verifier asserts the live
# read-back LastModifiedDate values are strictly descending (ties fail).
#
# Backends: salesforce LIVE (owned-record scan keeps the unscoped
# 'IsClosed = false' query deterministic; the recipe is READ-ONLY on
# Salesforce — snapshot equality is pinned — and cleanup deletes every owned
# record in finally, failing on leftovers); lookup_table + workato_variable +
# workato_api_platform are Workato-internal deterministic mocks.

_STRUCTURE_PINS_JSON = r'''
[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "d3598ac7",
  "provider": "workato_api_platform",
  "name": "receive_request",
  "skip": false,
  "input": {
   "request": {
    "content_type": "json",
    "schema": "[{\"name\":\"deal_type\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Deal type\",\"hint\":\"Renew, Expand or Land\"},{\"name\":\"account_type\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Account type\"}]"
   },
   "response": {
    "content_type": "json",
    "responses": [
     {
      "body_schema": "[{\"name\":\"opportunities\",\"type\":\"array\",\"of\":\"object\",\"label\":\"Opportunities\",\"optional\":false,\"properties\":[{\"control_type\":\"text\",\"label\":\"ID\",\"name\":\"id\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Name\",\"name\":\"name\",\"type\":\"string\",\"optional\":false}]}]",
      "http_status_code": "200"
     }
    ]
   }
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "839fdf7a",
  "provider": "lookup_table",
  "name": "search_entries",
  "skip": false,
  "input": {
   "lookup_table_id": "3304617",
   "parameters": {
    "col1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"d3598ac7\",\"path\":[\"request\", \"deal_type\"]}')}"
   }
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "83dfe49e",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "deal_type_filter": "=if _('data.lookup_table.839fdf7a.entries.first.entry.col2').present?\n  \"AND (\" + _('data.lookup_table.839fdf7a.entries.first.entry.col2') + \")\"\nelse\n  \"\"\nend"
    },
    "schema": "[{\"name\":\"deal_type_filter\",\"type\":\"string\",\"optional\":true,\"label\":\"deal type filter\",\"details\":{\"real_name\":\"deal type filter\"},\"control_type\":\"text\"}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "27d909cb",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "max_batch_size": "2000"
    },
    "schema": "[{\"name\":\"max_batch_size\",\"type\":\"integer\",\"optional\":true,\"label\":\"max batch size\",\"details\":{\"real_name\":\"max batch size\"},\"control_type\":\"integer\"}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "d2c4c0f3",
  "provider": "workato_variable",
  "name": "declare_list",
  "skip": false,
  "input": {
   "list_item_schema_json": "[{\"name\":\"id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"ID\"},{\"name\":\"name\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Name\"}]",
   "name": "records"
  }
 },
 {
  "keyword": "action",
  "number": 6,
  "as": "aef0ef3e",
  "provider": "salesforce",
  "name": "search_sobjects_soql_v2",
  "skip": false,
  "input": {
   "limit": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"27d909cb\",\"path\":[\"max_batch_size\"]}')}",
   "output_schema": "[{\"control_type\":\"text\",\"label\":\"Name\",\"type\":\"string\",\"name\":\"Name\"},{\"control_type\":\"text\",\"label\":\"ID\",\"type\":\"string\",\"name\":\"Id\"},{\"name\":\"LastModifiedDate\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Last modified date\"}]",
   "query": "SELECT\nId,\nName,\nType,\nLastModifiedDate\nFROM\nOpportunity\nWHERE\nIsClosed = false\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"83dfe49e\",\"path\":[\"deal_type_filter\"]}')}\nORDER BY LastModifiedDate DESC"
  }
 },
 {
  "keyword": "action",
  "number": 7,
  "as": "4a5c5db8",
  "provider": "workato_variable",
  "name": "insert_to_list_batch",
  "skip": false,
  "input": {
   "list_items": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"aef0ef3e\",\"path\":[\"records\"]}')}",
    "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"aef0ef3e\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}",
    "name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"aef0ef3e\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Name\"]}')}"
   },
   "location": "end",
   "name": "4f29ecc3-07c9-47ba-b25f-136bb58b0633:d2c4c0f3"
  }
 },
 {
  "keyword": "if",
  "number": 8,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"aef0ef3e\",\"path\":[\"records\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "equals_to",
     "rhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"27d909cb\",\"path\":[\"max_batch_size\"]}')}"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 9,
  "as": "63a33a39",
  "provider": "salesforce",
  "name": "search_sobjects_soql_v2",
  "skip": false,
  "input": {
   "limit": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"27d909cb\",\"path\":[\"max_batch_size\"]}')}",
   "offset": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"27d909cb\",\"path\":[\"max_batch_size\"]}')}",
   "output_schema": "[{\"control_type\":\"text\",\"label\":\"Name\",\"type\":\"string\",\"name\":\"Name\"},{\"control_type\":\"text\",\"label\":\"ID\",\"type\":\"string\",\"name\":\"Id\"},{\"name\":\"LastModifiedDate\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Last modified date\"}]",
   "query": "SELECT\nId,\nName,\nType,\nLastModifiedDate\nFROM\nOpportunity\nWHERE\nIsClosed = false\n#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"83dfe49e\",\"path\":[\"deal_type_filter\"]}')}\nORDER BY LastModifiedDate DESC"
  }
 },
 {
  "keyword": "action",
  "number": 10,
  "as": "9df0d960",
  "provider": "workato_variable",
  "name": "insert_to_list_batch",
  "skip": false,
  "input": {
   "list_items": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"63a33a39\",\"path\":[\"records\"]}')}",
    "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"63a33a39\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}",
    "name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"63a33a39\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Name\"]}')}"
   },
   "location": "end",
   "name": "4f29ecc3-07c9-47ba-b25f-136bb58b0633:d2c4c0f3"
  }
 },
 {
  "keyword": "action",
  "number": 11,
  "as": "86b1eaac",
  "provider": "workato_api_platform",
  "name": "return_response",
  "skip": false,
  "input": {
   "http_status_code": "200",
   "response": {
    "opportunities": {
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"d2c4c0f3\",\"path\":[\"list_items\"]}')}",
     "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"d2c4c0f3\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}",
     "name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"d2c4c0f3\",\"path\":[\"list_items\", {\"path_element_type\": \"current_item\"}, \"name\"]}')}"
    }
   }
  }
 }
]
'''

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "workato_runtime.declare_variable",
    "workato_runtime.declare_list",
    "salesforce.search_records",
    "workato_runtime.insert_to_list_batch",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.search_entries",
    "salesforce.search_records",
    "workato_api_platform.return_response",
]
SEED_SECTIONS = {"lookup_table", "salesforce"}
EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "stopped",
    "deal_type_filter",
    "opportunities",
)
OPTIONAL_EXPECT_KEYS = {"case"}
SOQL_TEMPLATE = (
    "SELECT\nId,\nName,\nType,\nLastModifiedDate\nFROM\nOpportunity\nWHERE\n"
    "IsClosed = false\n{deal_type_filter}\nORDER BY LastModifiedDate DESC"
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


def validate_89731033(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_89731033(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_89731033(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    if _TOKEN_RE.search(json.dumps(trigger)):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input must not carry seed ref tokens")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - SEED_SECTIONS)
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no try/catch — a forced action error would abort the job, "
            "which is not an observable branch of this recipe"
        )
    expect = data.get("expect")
    _require_expect_shape(expect, trigger)
    _require_lookup_section(seed_in.get("lookup_table"), trigger, expect)
    salesforce_section = seed_in.get("salesforce")
    _require_salesforce_section(salesforce_section, expect)
    state, seed_snapshot, refs = _provision_salesforce_phases(ctx, salesforce_section)
    resolved_expect = _replace_value(deepcopy(expect), refs)
    _require_no_tokens(resolved_expect, "expect")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": resolved_expect,
        "lookup_table": deepcopy(seed_in["lookup_table"]),
        "salesforce_live": state,
        "salesforce_seed_snapshot": seed_snapshot,
        "salesforce_ref_tokens": refs,
    }
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_89731033(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_89731033(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing resolved expect block")
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    if not seed["salesforce_live"].get("strict_soql_conditions"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires salesforce_live.strict_soql_conditions "
            "(the 'IsClosed = false' leaf and ORDER BY apply only under the strict flag)"
        )
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
    result["verifier"] = verify_89731033(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {"request"} or not isinstance(trigger.get("request"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input must be exactly {{'request': {{...}}}}")
    request = trigger["request"]
    extra = sorted(set(request) - {"deal_type", "account_type"})
    if extra:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger request has undeclared fields: {extra}")
    deal_type = request.get("deal_type")
    if not isinstance(deal_type, str) or not deal_type.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger request.deal_type must be a non-empty string "
            "(the lookup keys off it; an absent deal_type would degenerate to a match-any "
            "lookup search, which is not one of the benchmarked branches)"
        )


def _require_expect_shape(expect: Any, trigger: dict[str, Any]) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(set(expect) - set(EXPECT_KEYS) - OPTIONAL_EXPECT_KEYS)
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has unexpected keys: {unknown}")
    if expect.get("stopped") is not False:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no stop steps — expect.stopped must be exactly false "
            "(return_response is terminal but not a stop)"
        )
    if int(expect.get("executed_action_count") or 0) != 7:
        raise RuntimeError(
            f"recipe {RECIPE_ID} every reachable path executes exactly 7 actions (the "
            "size==2000 pagination branch is proven-unreachable in the benchmark)"
        )
    tools = expect.get("tools")
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tools, list) or not isinstance(tool_expectations, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools/tool_expectations must be lists")
    if tools != ALLOWED_TOOLS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools must be exactly {ALLOWED_TOOLS} "
            "(one lookup search, ONE SOQL search, one terminal response)"
        )
    if len(tool_expectations) != len(tools):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry"
        )
    deal_type_filter = expect.get("deal_type_filter")
    if not isinstance(deal_type_filter, str):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.deal_type_filter must be a string "
            "('' for the blank-col2 and no-lookup-match arms)"
        )
    if deal_type_filter and not (
        deal_type_filter.startswith("AND (") and deal_type_filter.endswith(")")
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} a non-empty expect.deal_type_filter must be the formula's "
            "verbatim 'AND (<col2>)' rendering"
        )
    opportunities = expect.get("opportunities")
    if not isinstance(opportunities, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.opportunities must be a list")
    for item in opportunities:
        if not isinstance(item, dict) or sorted(item) != ["id", "name"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.opportunities items must be exactly {{id, name}}: {item!r}"
            )
        if not _TOKEN_RE.fullmatch(str(item.get("id") or "")):
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.opportunities ids must be $<REF>_ID seed tokens "
                f"(live ids are only known after provisioning): {item!r}"
            )
    expected_query = SOQL_TEMPLATE.format(deal_type_filter=deal_type_filter)
    soql_item = tool_expectations[1] if len(tool_expectations) > 1 else None
    if not isinstance(soql_item, dict) or str(soql_item.get("tool")) != "salesforce.search_records":
        raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[1] must pin the SOQL search")
    args_contains = soql_item.get("args_contains")
    if not isinstance(args_contains, dict) or args_contains.get("query") != expected_query:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[1].args_contains.query must pin the resolved "
            f"SOQL verbatim (from expect.deal_type_filter): {expected_query!r}"
        )
    if args_contains.get("limit") != MAX_BATCH_SIZE:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[1].args_contains.limit must be the int "
            f"{MAX_BATCH_SIZE} (declare_variable integer_conversion applies)"
        )
    if soql_item.get("result_count") != len(opportunities):
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[1].result_count must equal "
            "len(expect.opportunities) (the pagination branch is unreachable, so the single "
            "search feeds the whole response)"
        )
    response_item = tool_expectations[2] if len(tool_expectations) > 2 else None
    if not isinstance(response_item, dict) or str(response_item.get("tool")) != "workato_api_platform.return_response":
        raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[2] must pin the terminal response")
    response_args = response_item.get("args_contains")
    if not isinstance(response_args, dict) or response_args.get("response") != {
        "opportunities": opportunities
    }:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[2].args_contains.response must equal "
            "{'opportunities': expect.opportunities} exactly (args_contains lists are "
            "exact-length, pinning order and count)"
        )
    if str(response_item.get("http_status_code") or "") != "200":
        raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[2] must pin http_status_code '200'")


def _require_lookup_section(section: Any, trigger: dict[str, Any], expect: dict[str, Any]) -> None:
    if not isinstance(section, dict) or not isinstance(section.get("tables"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.lookup_table.tables")
    if sorted(section["tables"]) != [LOOKUP_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.lookup_table.tables must declare exactly table {LOOKUP_TABLE_ID}"
        )
    rows = section["tables"][LOOKUP_TABLE_ID]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the deal-types table {LOOKUP_TABLE_ID} must be a non-empty "
            "explicit list (a no-match variant seeds non-matching rows, never an implicit "
            "empty table)"
        )
    deal_type = str(trigger["request"].get("deal_type"))
    matches: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} lookup rows must be objects")
        if not str(row.get("col1") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} lookup rows need a non-empty col1 (deal type name)")
        if not isinstance(row.get("col2"), str):
            raise RuntimeError(
                f"recipe {RECIPE_ID} lookup rows need an explicit string col2 (SOQL filter; '' "
                "exercises the blank-filter arm)"
            )
        col2 = str(row.get("col2"))
        if col2 and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*\s*=\s*'[^']*'", col2):
            raise RuntimeError(
                f"recipe {RECIPE_ID} lookup col2 is INJECTED VERBATIM into the live SOQL — keep "
                f"it to a strict-supported \"Field = 'value'\" leaf: {col2!r}"
            )
        if str(row.get("col1")) == deal_type:
            matches.append(row)
    expected_filter = str(expect.get("deal_type_filter"))
    if not matches:
        if expected_filter != "":
            raise RuntimeError(
                f"recipe {RECIPE_ID} no lookup row matches deal_type {deal_type!r} — "
                "expect.deal_type_filter must be '' (the entries.first MISSING arm)"
            )
        return
    if len(matches) > 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} multiple lookup rows match deal_type {deal_type!r}; seed exactly "
            "one (entries.first must be deterministic)"
        )
    col2 = str(matches[0].get("col2"))
    derived = f"AND ({col2})" if col2 else ""
    if expected_filter != derived:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.deal_type_filter {expected_filter!r} disagrees with the "
            f"matched lookup row's col2 rendering {derived!r}"
        )


def _require_salesforce_section(section: Any, expect: dict[str, Any]) -> None:
    if not isinstance(section, dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires seed.salesforce (the SOQL search always executes)"
        )
    unexpected = sorted(set(section) - {"strict_soql_conditions", "phases"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce has unexpected keys: {unexpected}")
    if section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true "
            "('IsClosed = false' + injected filter + ORDER BY are strict-only semantics)"
        )
    phases = section.get("phases")
    if not isinstance(phases, list) or not phases:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.phases must be a non-empty list of "
            "{'records': [...]} sections (phase order = LastModifiedDate order)"
        )
    seeded_count = sum(
        len(phase.get("records") or [])
        for phase in phases
        if isinstance(phase, dict)
    )
    if seeded_count > MAX_SEED_OPPORTUNITIES:
        raise RuntimeError(
            f"recipe {RECIPE_ID} benchmark fixtures cap owned Opportunity seeds "
            f"at {MAX_SEED_OPPORTUNITIES}; got {seeded_count}"
        )
    refs_seen: set[str] = set()
    ref_meta: dict[str, dict[str, Any]] = {}
    for phase_index, phase in enumerate(phases):
        if not isinstance(phase, dict) or sorted(phase) != ["records"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} each salesforce phase must be exactly {{'records': [...]}}"
            )
        records = phase.get("records")
        if not isinstance(records, list) or not records:
            raise RuntimeError(f"recipe {RECIPE_ID} salesforce phase {phase_index} has no records")
        for record in records:
            if not isinstance(record, dict) or str(record.get("sobject") or "") != "Opportunity":
                raise RuntimeError(
                    f"recipe {RECIPE_ID} every seeded record must be an Opportunity: {record!r}"
                )
            ref = str(record.get("ref") or "").strip()
            if not ref:
                raise RuntimeError(f"recipe {RECIPE_ID} every seeded Opportunity needs a ref")
            token = f"${ref.upper()}_ID"
            if token in refs_seen:
                raise RuntimeError(f"recipe {RECIPE_ID} duplicate seed ref {ref!r}")
            refs_seen.add(token)
            fields = record.get("fields")
            if not isinstance(fields, dict):
                raise RuntimeError(f"recipe {RECIPE_ID} seeded Opportunity needs a fields object")
            extra_fields = sorted(set(fields) - OPPORTUNITY_SEED_FIELDS)
            if extra_fields:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} seeded Opportunity carries fields the recipe never "
                    f"reads: {extra_fields}"
                )
            for key in ("Name", "StageName", "CloseDate"):
                if not str(fields.get(key) or "").strip():
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} seeded Opportunity needs a non-empty {key}"
                    )
            ref_meta[token] = {
                "phase": phase_index,
                "name": str(fields.get("Name")),
                "closed": str(fields.get("StageName")).startswith("Closed"),
            }
    # Response-order determinism: each phase may contribute at most ONE record
    # to the response, and the DESC response order must be exactly the reverse
    # phase order (later phase = newer LastModifiedDate = earlier in response).
    response_phases: list[int] = []
    phases_used: set[int] = set()
    for item in expect.get("opportunities") or []:
        token = str(item.get("id"))
        meta = ref_meta.get(token)
        if meta is None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.opportunities id {token!r} is not a seeded ref token"
            )
        if meta["closed"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.opportunities includes {token!r} but its StageName "
                "is a Closed stage (IsClosed = false excludes it)"
            )
        if str(item.get("name")) != meta["name"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.opportunities name for {token!r} must equal the "
                f"seeded Name {meta['name']!r}"
            )
        if meta["phase"] in phases_used:
            raise RuntimeError(
                f"recipe {RECIPE_ID} two response records share seed phase {meta['phase']} — "
                "same-second LastModifiedDate ties make the DESC order nondeterministic; give "
                "each response record its own phase"
            )
        phases_used.add(meta["phase"])
        response_phases.append(meta["phase"])
    if response_phases != sorted(response_phases, reverse=True):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.opportunities must be in strictly DESCENDING seed-phase "
            f"order (LastModifiedDate DESC = reverse provisioning order); got phases {response_phases}"
        )


def _provision_salesforce_phases(
    ctx: RecipeContext, section: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    phases = section["phases"]
    state: dict[str, Any] | None = None
    merged_records: list[dict[str, Any]] = []
    refs: dict[str, str] = {}
    for phase_index, phase in enumerate(phases):
        if phase_index:
            time.sleep(LMD_SPACING_SECONDS)
        phase_section: dict[str, Any] = {
            "strict_soql_conditions": True,
            "records": deepcopy(phase["records"]),
        }
        try:
            provision = ctx.tools.call(
                "harness.salesforce.seed_records", {"salesforce": phase_section}
            )
            if not provision.get("ok"):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} Salesforce phase-{phase_index} seed failed: {provision}"
                )
        except Exception:
            if state is not None:
                # A later phase failed after earlier phases committed live
                # records: remove them before failing so a rerun never sees
                # stale benchmark state (precedent recipe_88704851).
                from ..salesforce_live_harness import OwnedSalesforce

                OwnedSalesforce(state).delete_owned()
            raise
        refs.update(_phase_ref_tokens(phase_section, provision))
        phase_state = deepcopy(provision["state"])
        phase_snapshot_records = list(
            ((provision.get("snapshot") or {}).get("salesforce") or {}).get("records") or []
        )
        merged_records.extend(deepcopy(phase_snapshot_records))
        if state is None:
            state = phase_state
        else:
            state["owned_records"] = list(state.get("owned_records") or []) + list(
                phase_state.get("owned_records") or []
            )
            state["read_only_records"] = list(state.get("read_only_records") or []) + list(
                phase_state.get("read_only_records") or []
            )
            state["strict_soql_conditions"] = bool(
                state.get("strict_soql_conditions") or phase_state.get("strict_soql_conditions")
            )
            state["expand_relationships"] = bool(
                state.get("expand_relationships") or phase_state.get("expand_relationships")
            )
    assert state is not None  # phases is validated non-empty
    return state, {"salesforce": {"records": merged_records}}, refs


def _phase_ref_tokens(phase_section: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    live_records = [
        record
        for record in salesforce_snapshot.get("records") or []
        if isinstance(record, dict) and record.get("id") and not record.get("read_only")
    ]
    seed_records = [record for record in phase_section.get("records") or [] if isinstance(record, dict)]
    if len(live_records) != len(seed_records):
        raise RuntimeError(
            f"recipe {RECIPE_ID} phase seed/snapshot record count mismatch: "
            f"{len(seed_records)} seeded vs {len(live_records)} provisioned"
        )
    refs: dict[str, str] = {}
    for record, live in zip(seed_records, live_records):
        ref = str(record.get("ref") or "").strip()
        live_id = str(live.get("id") or "")
        if not _SF_ID_RE.fullmatch(live_id):
            raise RuntimeError(f"recipe {RECIPE_ID} provisioned record id looks invalid: {live_id!r}")
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


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    out: dict[str, Any] = {
        "lookup_table": (ctx.tools.call("harness.lookup_table.snapshot", {}) or {}).get("lookup_table"),
    }
    salesforce_snapshot = ctx.tools.call("harness.salesforce.snapshot", {})
    out["salesforce"] = salesforce_snapshot.get("salesforce")
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
