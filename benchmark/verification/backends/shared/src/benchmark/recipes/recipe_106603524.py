from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_106603524


RECIPE_ID = "106603524"
SEED_TYPE = "salesforce_recipe_function_support_ticket_counts_variant"
TRACK = "live_salesforce_recipe_function_support_ticket_counts"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "ea80dd69"
TICKET_SOBJECT = "Support_Ticket__c"
SEARCH_ALL_AS = "596c386d"
SEARCH_20D_AS = "68e6796b"
CATCH_AS = "baa77910"
STOP_AS = "db452987"
REQUIRED_SCHEMA = [
    {"sobject": "Support_Ticket__c", "field": "Status__c", "sf_type": "Text"},
    {"sobject": "Support_Ticket__c", "field": "Days_Open__c", "sf_type": "Number"},
]
TRIGGER_ROW_KEYS = {"AccountID", "AccountName"}
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")


_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "ea80dd69",
  "provider": "workato_recipe_function",
  "name": "execute",
  "skip": false,
  "input": {
   "parameters_schema_json": "[{\"name\":\"AccountList\",\"type\":\"array\",\"optional\":false,\"label\":\"Account list\",\"properties\":[{\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account ID\"},{\"name\":\"AccountName\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account name\"}],\"of\":\"object\"}]",
   "result_schema_json": "[{\"name\":\"SupportTickets\",\"type\":\"array\",\"optional\":false,\"properties\":[{\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account ID\"},{\"name\":\"TotalOpenTickets\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"Total open tickets\",\"parse_output\":\"integer_conversion\"},{\"name\":\"OpenTicketsMore20days\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"Open tickets more 20 days\",\"parse_output\":\"integer_conversion\"}],\"of\":\"object\",\"label\":\"Support tickets\"}]"
  }
 },
 {
  "keyword": "try",
  "number": 2,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {}
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "a826e077",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "account_ids_string": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"ea80dd69\",\"path\":[\"parameters\",\"AccountList\"]}')&.pluck(\"AccountID\").join(\"','\")"
    },
    "schema": "[{\"control_type\":\"text\",\"label\":\"account_ids_string\",\"name\":\"account_ids_string\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"account_ids_string\"}}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "596c386d",
  "provider": "salesforce",
  "name": "search_sobjects_soql_v2",
  "skip": false,
  "input": {
   "limit": "2000",
   "output_schema": "[{\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"AccountID\"},{\"name\":\"TotalOpenTickets\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"Total open tickets\",\"parse_output\":\"integer_conversion\"}]",
   "query": "SELECT Account__c AccountID, COUNT(Id) TotalOpenTickets\nFROM Support_Ticket__c\nWHERE IsDeleted = FALSE\n\tAND Status__c NOT IN ('Closed', 'Resolved')\n\tAND Account__c IN ('#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"a826e077\",\"path\":[\"account_ids_string\"]}')}')\nGROUP BY Account__c"
  }
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "22b39266",
  "provider": "workato_smart_list",
  "name": "create_list",
  "skip": false,
  "input": {
   "list_name": "OpenTickets",
   "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"596c386d\",\"path\":[\"records\"]}')",
   "primary_index": "AccountID"
  }
 },
 {
  "keyword": "action",
  "number": 6,
  "as": "68e6796b",
  "provider": "salesforce",
  "name": "search_sobjects_soql_v2",
  "skip": false,
  "input": {
   "limit": "2000",
   "output_schema": "[{\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"AccountID\"},{\"name\":\"OpenTicketsMore20days\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"Open tickets more 20 days\",\"parse_output\":\"integer_conversion\"}]",
   "query": "SELECT Account__c AccountID, COUNT(Id) OpenTicketsMore20days\nFROM Support_Ticket__c\nWHERE IsDeleted = FALSE\n\tAND Status__c NOT IN ('Closed', 'Resolved')\n\tAND Account__c IN ('#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"a826e077\",\"path\":[\"account_ids_string\"]}')}')\n\tAND Days_Open__c > 20\nGROUP BY Account__c"
  }
 },
 {
  "keyword": "action",
  "number": 7,
  "as": "fe0596ef",
  "provider": "workato_smart_list",
  "name": "create_list",
  "skip": false,
  "input": {
   "list_name": "OpenTicketsMore20days",
   "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"68e6796b\",\"path\":[\"records\"]}')",
   "primary_index": "AccountID"
  }
 },
 {
  "keyword": "action",
  "number": 8,
  "as": "96f06bfe",
  "provider": "workato_smart_list",
  "name": "query_list",
  "skip": false,
  "input": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "output_schema_by": "index",
   "result_schema_json": "[{\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account ID\"},{\"name\":\"TotalOpenTickets\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"Total open tickets\",\"parse_output\":\"integer_conversion\"},{\"name\":\"OpenTicketsMore20days\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"Open tickets more 20 days\",\"parse_output\":\"integer_conversion\"}]",
   "sql": "SELECT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"22b39266\",\"path\":[\"list_name\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"22b39266\",\"path\":[\"columns\", \"AccountID\"]}')}, #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"22b39266\",\"path\":[\"list_name\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"22b39266\",\"path\":[\"columns\", \"TotalOpenTickets\"]}')}, #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"fe0596ef\",\"path\":[\"list_name\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"fe0596ef\",\"path\":[\"columns\", \"OpenTicketsMore20days\"]}')}\nFROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"22b39266\",\"path\":[\"list_name\"]}')}\nLEFT JOIN #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"fe0596ef\",\"path\":[\"list_name\"]}')}\n\tON #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"22b39266\",\"path\":[\"list_name\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"22b39266\",\"path\":[\"columns\", \"AccountID\"]}')} = #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"fe0596ef\",\"path\":[\"list_name\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"fe0596ef\",\"path\":[\"columns\", \"AccountID\"]}')}"
  }
 },
 {
  "keyword": "action",
  "number": 9,
  "as": "004b17c4",
  "provider": "workato_recipe_function",
  "name": "return_result",
  "skip": false,
  "input": {
   "result": {
    "SupportTickets": {
     "AccountID": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"96f06bfe\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"AccountID\"]}')}",
     "OpenTicketsMore20days": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"96f06bfe\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"OpenTicketsMore20days\"]}')}",
     "TotalOpenTickets": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"96f06bfe\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"TotalOpenTickets\"]}')}",
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"96f06bfe\",\"path\":[\"rows\"]}')}"
    }
   }
  }
 },
 {
  "keyword": "catch",
  "number": 10,
  "as": "baa77910",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "max_retry_count": "3",
   "retry_interval": "10"
  }
 },
 {
  "keyword": "stop",
  "number": 11,
  "as": "db452987",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "stop_reason": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"baa77910\",\"path\":[\"type\"]}')} : #{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"baa77910\",\"path\":[\"message\"]}')}",
   "stop_with_error": "true"
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "salesforce.search_records",
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_recipe_function.return_result",
]
EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "smart_list_sqls",
    "create_lists",
    "query_rows",
    "final_result",
    "stopped",
    "catch",
)
OPTIONAL_EXPECT_KEYS = {"stop_step_as", "stop_step_number"}


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


def validate_106603524(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_106603524(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_106603524(raw)
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
    _require_salesforce_section(seed_in.get("salesforce"))
    expect = data.get("expect")
    _require_expect_shape(expect)
    force = data.get("force_action_error")
    if force is not None:
        if not isinstance(force, dict) or str(force.get("step_as") or "") != SEARCH_ALL_AS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} fault injection is sanctioned only on step "
                f"{SEARCH_ALL_AS} (inside the try): {force!r}"
            )
        if expect.get("stopped") is not True:
            raise RuntimeError(
                f"recipe {RECIPE_ID} a forced error must pin expect.stopped true "
                "(catch -> stop_with_error)"
            )
    elif expect.get("stopped") is not False:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the catch/stop is only reachable via sanctioned fault "
            "injection; happy variants must pin expect.stopped false"
        )
    provision = ctx.tools.call(
        "harness.salesforce.seed_records", {"salesforce": deepcopy(seed_in["salesforce"])}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    refs = _salesforce_ref_tokens(seed_in["salesforce"], provision)
    trigger = _replace_value(trigger, refs)
    _require_resolved(trigger)
    resolved_expect = _replace_value(deepcopy(expect), refs)
    _require_resolved(resolved_expect)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        # Expected SOQL text / result AccountIDs are this run's live seeded
        # Account ids, threaded via the same $REF_ID tokens as the trigger
        # (64106452 / 85427201 precedent).
        "expect": resolved_expect,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": refs,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_106603524(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_106603524(raw)
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    if not seed["salesforce_live"].get("strict_soql_conditions"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires strict_soql_conditions in the live state "
            "(IsDeleted = FALSE / NOT IN / IN / Days_Open__c > 20 are strict-only)"
        )
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
        "force_action_error": deepcopy(seed.get("force_action_error"))
        if isinstance(seed.get("force_action_error"), dict)
        else None,
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
        # Required cleanup: owned Support_Ticket__c + Account seed records must
        # not leak into later runs (the recipe itself only reads).
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
    result["verifier"] = verify_106603524(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {"parameters"} or not isinstance(trigger.get("parameters"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'parameters': {{...}}}}"
        )
    parameters = trigger["parameters"]
    if set(parameters) != {"AccountList"} or not isinstance(parameters.get("AccountList"), list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must carry exactly AccountList "
            "(a list; [] is the empty-input branch)"
        )
    for row in parameters["AccountList"]:
        if not isinstance(row, dict) or set(row) != TRIGGER_ROW_KEYS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} every AccountList row must carry exactly "
                f"{sorted(TRIGGER_ROW_KEYS)} (the trigger parameters schema): {row!r}"
            )
        for key in TRIGGER_ROW_KEYS:
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} AccountList row {key} must be a non-empty string: {row!r}"
                )


def _require_salesforce_section(section: Any) -> None:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce")
    if section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true "
            "(IsDeleted = FALSE / NOT IN / IN / numeric > are strict-only operators)"
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
        if sobject not in {"Account", TICKET_SOBJECT}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seeded records must be Account or {TICKET_SOBJECT}: {record}"
            )
        if not str(fields.get("Name") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded record needs an explicit Name "
                f"(mdapi Text name field): {record}"
            )
        if sobject == TICKET_SOBJECT:
            if record.get("read_fields") != ["IsDeleted"]:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} every {TICKET_SOBJECT} seed must declare "
                    "read_fields ['IsDeleted'] (the strict 'IsDeleted = FALSE' leaf "
                    "evaluates the live read-back -- 118905064 precedent): "
                    f"{record}"
                )
            for key in ("Account__c", "Status__c"):
                if not str(fields.get(key) or "").strip():
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} {TICKET_SOBJECT} seed must set {key}: {record}"
                    )
            if not isinstance(fields.get("Days_Open__c"), (int, float)) or isinstance(
                fields.get("Days_Open__c"), bool
            ):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {TICKET_SOBJECT} seed must set Days_Open__c as an "
                    f"explicit number (a plain Number column, never a live formula): {record}"
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
    if not isinstance(expect.get("smart_list_sqls"), list) or not isinstance(
        expect.get("create_lists"), list
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.smart_list_sqls/create_lists must be lists")
    if expect.get("stopped") is True:
        if expect.get("final_result") is not None or expect.get("query_rows") is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} the catch path never reaches the query/return steps: "
                "final_result/query_rows must be null"
            )
        catch = expect.get("catch")
        if not isinstance(catch, dict) or set(catch) != {
            "type", "message", "adapter", "action", "line_number"
        }:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must pin the full connector catch payload"
            )
        if str(expect.get("stop_step_as") or "") != STOP_AS or expect.get("stop_step_number") != 11:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must pin stop_step_as {STOP_AS!r} / "
                "stop_step_number 11"
            )
    elif expect.get("stopped") is False:
        if expect.get("catch") is not None:
            raise RuntimeError(f"recipe {RECIPE_ID} happy variants must pin expect.catch null")
        if not isinstance(expect.get("final_result"), dict) or not isinstance(
            expect["final_result"].get("SupportTickets"), list
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} happy variants must pin expect.final_result.SupportTickets "
                "(the exact return_result payload; [] on the empty branch)"
            )
        if not isinstance(expect.get("query_rows"), list):
            raise RuntimeError(
                f"recipe {RECIPE_ID} happy variants must pin expect.query_rows "
                "(the exact LEFT-JOIN output rows)"
            )
    else:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.stopped must be true or false")


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


def _require_resolved(value: Any) -> None:
    leftover = _TOKEN_RE.findall(json.dumps(value))
    if leftover:
        raise RuntimeError(f"recipe {RECIPE_ID} unresolved seed tokens remain: {sorted(set(leftover))}")


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
