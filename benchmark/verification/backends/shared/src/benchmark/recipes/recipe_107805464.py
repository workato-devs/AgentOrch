from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_107805464


RECIPE_ID = "107805464"
SEED_TYPE = "recipe_function_student_cert_grouping_variant"
TRACK = "live_salesforce_recipe_function_student_cert_pagination"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "898bfe38"
SF_LOGICAL_SOBJECT = "skilljar__Student__c"
SOQL_STEP_AS = "586b2c78"
CATCH_STEP_AS = "dec4c31c"
STOP_STEP_NUMBER = 9
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_SF_ID_RE = re.compile(r"^[a-zA-Z0-9]{15,18}$")


_STRUCTURE_PINS_JSON = r'''
[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "898bfe38",
  "provider": "workato_recipe_function",
  "name": "execute",
  "skip": false,
  "input": {
   "parameters_schema_json": "[{\"name\":\"AccountList\",\"type\":\"array\",\"optional\":false,\"properties\":[{\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account ID\"},{\"name\":\"AccountName\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account name\"}],\"of\":\"object\",\"label\":\"Account list\"}]",
   "result_schema_json": "[{\"name\":\"WorkatoStudents\",\"type\":\"array\",\"optional\":false,\"properties\":[{\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account ID\"},{\"name\":\"Students\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Students\"}],\"of\":\"object\",\"label\":\"Workato students\"}]"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "dcc1fecc",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "account_ids_string": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"898bfe38\",\"path\":[\"parameters\",\"AccountList\"]}')&.pluck(\"AccountID\").join(\"','\")"
    },
    "schema": "[{\"control_type\":\"text\",\"label\":\"account_ids_string\",\"name\":\"account_ids_string\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"account_ids_string\"}}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "05393b49",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "id": "000000000000000"
    },
    "schema": "[{\"name\":\"id\",\"type\":\"string\",\"optional\":true,\"label\":\"id\",\"details\":{\"real_name\":\"id\"},\"control_type\":\"text\"}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "2743d463",
  "provider": "workato_variable",
  "name": "declare_list",
  "skip": false,
  "input": {
   "list_item_schema_json": "[{\"name\":\"id\",\"type\":\"string\",\"optional\":false,\"label\":\"id\",\"control_type\":\"text\"},{\"name\":\"name\",\"type\":\"string\",\"optional\":false,\"label\":\"name\",\"control_type\":\"text\"},{\"name\":\"num_certs\",\"type\":\"integer\",\"optional\":false,\"label\":\"num_certs\",\"control_type\":\"integer\",\"parse_output\":\"integer_conversion\"},{\"name\":\"account_id\",\"type\":\"string\",\"optional\":false,\"label\":\"account_id\",\"control_type\":\"text\"}]",
   "name": "students"
  }
 },
 {
  "keyword": "repeat",
  "number": 5,
  "as": "c112b2bf",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {}
 },
 {
  "keyword": "try",
  "number": 6,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {}
 },
 {
  "keyword": "action",
  "number": 7,
  "as": "586b2c78",
  "provider": "salesforce",
  "name": "search_sobjects_soql_v2",
  "skip": false,
  "input": {
   "limit": "2000",
   "output_schema": "[{\"name\":\"Id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Id\"},{\"name\":\"Name\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Name\"},{\"name\":\"No_of_Certificates__c\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"No of certificates c\",\"parse_output\":\"integer_conversion\"},{\"name\":\"Account__c\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account c\"}]",
   "query": "SELECT Id, \n       Name, \n       No_of_Certificates__c, \n       Account__c\n  FROM skilljar__Student__c\n WHERE No_of_Certificates__c > 0\n   AND Account__c IN ('#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"dcc1fecc\",\"path\":[\"account_ids_string\"]}')}')\n   AND Id > '#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"05393b49\",\"path\":[\"id\"]}')}'\n ORDER BY Id   "
  }
 },
 {
  "keyword": "catch",
  "number": 8,
  "as": "dec4c31c",
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
  "number": 9,
  "as": "0f947348",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "stop_reason": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"dec4c31c\",\"path\":[\"type\"]}')} : #{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"dec4c31c\",\"path\":[\"message\"]}')}",
   "stop_with_error": "true"
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
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"586b2c78\",\"path\":[\"totalSize\"]}')}",
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
  "number": 11,
  "as": "96773734",
  "provider": "workato_variable",
  "name": "insert_to_list_batch",
  "skip": false,
  "input": {
   "list_items": {
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"586b2c78\",\"path\":[\"records\"]}')}",
    "account_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"586b2c78\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Account__c\"]}')}",
    "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"586b2c78\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Id\"]}')}",
    "name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"586b2c78\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Name\"]}')}",
    "num_certs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"586b2c78\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"No_of_Certificates__c\"]}')}"
   },
   "location": "end",
   "name": "e8c23ca5-a93d-4f3f-91a3-2f30870320a9:2743d463"
  }
 },
 {
  "keyword": "action",
  "number": 12,
  "as": "026e2c09",
  "provider": "workato_variable",
  "name": "update_variables",
  "skip": false,
  "input": {
   "id": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"586b2c78\",\"path\":[\"records\"]}')[-1][\"Id\"]",
   "name": "9cf606e1-4e9f-41b2-bb69-207093fa9dfa:05393b49:id"
  }
 },
 {
  "keyword": "while_condition",
  "number": 13,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"586b2c78\",\"path\":[\"totalSize\"]}')}",
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
  "number": 14,
  "as": "5c5a11d0",
  "provider": "workato_smart_list",
  "name": "create_list",
  "skip": false,
  "input": {
   "list_name": "Students",
   "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"2743d463\",\"path\":[\"list_items\"]}')",
   "primary_index": "account_id"
  }
 },
 {
  "keyword": "action",
  "number": 15,
  "as": "bb6d3c01",
  "provider": "workato_smart_list",
  "name": "query_list",
  "skip": false,
  "input": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "output_schema_by": "index",
   "result_schema_json": "[{\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account ID\"},{\"name\":\"Students\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Students\"}]",
   "sql": "SELECT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5c5a11d0\",\"path\":[\"columns\", \"account_id\"]}')}, \n       GROUP_CONCAT(#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5c5a11d0\",\"path\":[\"columns\", \"name\"]}')} || ' (' || #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5c5a11d0\",\"path\":[\"columns\", \"num_certs\"]}')} || ')', ';') as Students\n  FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5c5a11d0\",\"path\":[\"list_name\"]}')}\n GROUP BY #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"5c5a11d0\",\"path\":[\"columns\", \"account_id\"]}')}"
  }
 },
 {
  "keyword": "action",
  "number": 16,
  "as": "336cdc69",
  "provider": "workato_recipe_function",
  "name": "return_result",
  "skip": false,
  "input": {
   "result": {
    "WorkatoStudents": {
     "AccountID": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"bb6d3c01\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"AccountID\"]}')}",
     "Students": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"bb6d3c01\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"Students\"]}')}",
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"bb6d3c01\",\"path\":[\"rows\"]}')}"
    }
   }
  }
 }
]
'''

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "workato_runtime.declare_list",
    "salesforce.search_records",
    "workato_runtime.insert_to_list_batch",
    "workato_runtime.update_variables",
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_recipe_function.return_result",
]
REQUIRED_STUDENT_SCHEMA: dict[str, str] = {
    "No_of_Certificates__c": "Number",
    "Account__c": "Text",
}
SEED_SECTIONS = {"salesforce"}
EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "result",
    "search_queries",
    "students_rows",
    "stopped",
)
OPTIONAL_EXPECT_KEYS = {"case", "stop_step_number", "catch_type", "catch_message"}


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


def validate_107805464(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_107805464(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_107805464(raw)
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
    expect = data.get("expect")
    force = data.get("force_action_error")
    _require_force_shape(force)
    _require_expect_shape(expect, force)
    sf_section = seed_in.get("salesforce")
    if force is None:
        _require_salesforce_section(sf_section, trigger)
    elif sf_section is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} forced-error variants must not seed live Salesforce records "
            "(the SOQL step fails before any live read; nothing may read them)"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
    }
    refs: dict[str, str] = {}
    if isinstance(sf_section, dict):
        provision = ctx.tools.call(
            "harness.salesforce.seed_records", {"salesforce": deepcopy(sf_section)}
        )
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
        refs = _salesforce_ref_tokens(sf_section, provision)
        out["salesforce_live"] = deepcopy(provision["state"])
        out["salesforce_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
        out["salesforce_ref_tokens"] = refs
    resolved_trigger = _replace_value(deepcopy(trigger), refs)
    _require_no_tokens(resolved_trigger, "trigger_input")
    resolved_expect = _replace_value(deepcopy(expect), refs)
    _require_no_tokens(resolved_expect, "expect")
    _canonicalize_group_row_order(resolved_expect)
    out["trigger"] = resolved_trigger
    out["expect"] = resolved_expect
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_107805464(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_107805464(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing resolved expect block")
    if not isinstance(seed.get("force_action_error"), dict) and not isinstance(
        seed.get("salesforce_live"), dict
    ):
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
        details["initial_snapshot"] = _snapshot(ctx, seed)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx, seed)
    finally:
        if isinstance(seed.get("salesforce_live"), dict):
            cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
            details["cleanup_response"] = cleanup_response
    if isinstance(seed.get("salesforce_live"), dict) and not (cleanup_response or {}).get("ok"):
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
    result["verifier"] = verify_107805464(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {"parameters"} or not isinstance(trigger.get("parameters"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'parameters': {{...}}}}"
        )
    parameters = trigger["parameters"]
    if set(parameters) != {"AccountList"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must carry exactly AccountList: "
            f"{sorted(parameters)}"
        )
    rows = parameters.get("AccountList")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger AccountList must be a non-empty list "
            "(the schema marks it required; account_ids_string derives from it)"
        )
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {"AccountID", "AccountName"}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} AccountList[{idx}] must carry exactly "
                f"AccountID + AccountName: {row!r}"
            )
        for key, value in row.items():
            if not isinstance(value, str) or not value.strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} AccountList[{idx}].{key} must be a non-empty string"
                )


def _require_force_shape(force: Any) -> None:
    if force is None:
        return
    if not isinstance(force, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error must be an object")
    if str(force.get("step_as") or "") != SOQL_STEP_AS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error.step_as must be {SOQL_STEP_AS!r} "
            "(the only step wrapped by the try/catch)"
        )
    if not str(force.get("error") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error.error must be a non-empty message")


def _canonicalize_group_row_order(resolved_expect: dict[str, Any]) -> None:
    """Put the pinned WorkatoStudents group rows into the recipe's faithful
    emission order once the live Account ids are known.

    Step 12 is `SELECT account_id, GROUP_CONCAT(...) ... GROUP BY account_id`
    with no ORDER BY, executed on real SQLite: the group rows come out sorted
    ascending by the group key, i.e. by the LIVE Salesforce Account id string.
    Live Salesforce allocates record ids from per-app-server blocks, so two
    consecutively created Accounts are NOT guaranteed ascending ids (observed
    live: seed order ACC1->001..WBee1AAD, ACC2->001..WAjnqAAD). The variant
    pins each row's content byte-exact; only the relative row order is a
    function of the live-assigned ids, so it is canonicalized here after
    token resolution. Rows without a pinned AccountID are a malformed pin and
    fail fast."""

    def sort_rows(container: Any) -> None:
        if not isinstance(container, dict):
            return
        rows = container.get("WorkatoStudents")
        if not isinstance(rows, list) or len(rows) < 2:
            return
        for row in rows:
            if not isinstance(row, dict) or not row.get("AccountID"):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} expect WorkatoStudents rows must each pin AccountID"
                )
        rows.sort(key=lambda row: str(row["AccountID"]))

    sort_rows(resolved_expect.get("result"))
    for item in resolved_expect.get("tool_expectations") or []:
        if isinstance(item, dict) and isinstance(item.get("args_contains"), dict):
            sort_rows(item["args_contains"].get("result"))


def _require_expect_shape(expect: Any, force: Any) -> None:
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
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry"
        )
    unknown_tools = sorted(set(tools) - set(ALLOWED_TOOLS))
    if unknown_tools:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools has unknown tools: {unknown_tools}")
    if not isinstance(expect.get("search_queries"), list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.search_queries must be a list of exact SOQL texts")
    if not isinstance(expect.get("students_rows"), list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.students_rows must be a list")
    if not isinstance(expect.get("stopped"), bool):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.stopped must be a bool")
    search_count = sum(1 for tool in tools if tool == "salesforce.search_records")
    if search_count != len(expect["search_queries"]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.search_queries must pin every search call "
            f"({search_count} expected, {len(expect['search_queries'])} pinned)"
        )
    if force is not None:
        if expect["stopped"] is not True or str(expect.get("stop_step_number")) != str(STOP_STEP_NUMBER):
            raise RuntimeError(
                f"recipe {RECIPE_ID} forced-error variants stop at step {STOP_STEP_NUMBER} with error"
            )
        if str(expect.get("catch_message") or "") != str(force.get("error")):
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.catch_message must equal the forced error message"
            )
        if str(expect.get("catch_type") or "") != "RawRecipeExecutionError":
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.catch_type must pin RawRecipeExecutionError "
                "(the engine's forced-action failure type)"
            )
        if tools or expect["search_queries"] or expect["students_rows"] or expect.get("result") is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} forced-error variants fail before any allowed tool call "
                "and never return a result"
            )
        return
    if expect["stopped"]:
        raise RuntimeError(f"recipe {RECIPE_ID} only forced-error variants stop")
    if not tools or tools[-1] != "workato_recipe_function.return_result":
        raise RuntimeError(
            f"recipe {RECIPE_ID} non-forced variants always end with return_result"
        )
    result = expect.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("WorkatoStudents"), list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.result must pin the exact "
            "{'WorkatoStudents': [...]} return value"
        )


def _require_salesforce_section(sf_section: Any, trigger: dict[str, Any]) -> None:
    if not isinstance(sf_section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} non-forced variants require seed.salesforce")
    unexpected = sorted(set(sf_section) - {"strict_soql_conditions", "schema", "records"})
    if unexpected:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce has unexpected keys: {unexpected}"
        )
    if sf_section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true: the "
            "keyset SOQL (Id > '<cursor>' quoted-string compare, ORDER BY Id, totalSize) "
            "only evaluates faithfully under the strict flag"
        )
    schema = sf_section.get("schema")
    if not isinstance(schema, list) or not schema:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare the {SF_LOGICAL_SOBJECT} "
            "custom fields (schema-in-seed provisioning via ensure_custom_field)"
        )
    declared = {
        (str(entry.get("sobject") or ""), str(entry.get("field") or "")): str(entry.get("sf_type") or "")
        for entry in schema
        if isinstance(entry, dict)
    }
    for field, sf_type in REQUIRED_STUDENT_SCHEMA.items():
        if declared.get((SF_LOGICAL_SOBJECT, field)) != sf_type:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed.salesforce.schema must declare "
                f"{SF_LOGICAL_SOBJECT}.{field} as {sf_type}"
            )
    records = sf_section.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records must be a non-empty list")
    account_refs: set[str] = set()
    student_count = 0
    for record in records:
        if not isinstance(record, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records entries must be objects")
        sobject = str(record.get("sobject") or "")
        ref = str(record.get("ref") or "").strip()
        fields = record.get("fields")
        if sobject not in {"Account", SF_LOGICAL_SOBJECT}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed.salesforce.records only seeds Account/"
                f"{SF_LOGICAL_SOBJECT}; got {sobject!r}"
            )
        if not ref or not isinstance(fields, dict):
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded {sobject} record needs an explicit ref and fields"
            )
        if sobject == "Account":
            if not str(fields.get("Name") or "").strip():
                raise RuntimeError(f"recipe {RECIPE_ID} seeded Account requires an explicit Name")
            account_refs.add(ref)
            continue
        student_count += 1
        if not str(fields.get("Name") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} seeded {SF_LOGICAL_SOBJECT} requires an explicit Name"
            )
        certs = fields.get("No_of_Certificates__c")
        if not isinstance(certs, int) or isinstance(certs, bool) or certs < 0:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seeded {SF_LOGICAL_SOBJECT}.No_of_Certificates__c must be "
                f"an explicit non-negative integer; got {certs!r}"
            )
        token = str(fields.get("Account__c") or "")
        expected_tokens = {f"${account_ref.upper()}_ID" for account_ref in account_refs}
        if token not in expected_tokens:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seeded {SF_LOGICAL_SOBJECT}.Account__c must reference an "
                f"earlier seeded Account ref token; got {token!r}"
            )
    if not account_refs or not student_count:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed needs at least one Account and one {SF_LOGICAL_SOBJECT}"
        )
    account_tokens = {f"${ref.upper()}_ID" for ref in account_refs}
    for idx, row in enumerate(trigger["parameters"]["AccountList"]):
        if str(row.get("AccountID") or "") not in account_tokens:
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger AccountList[{idx}].AccountID must be a $<REF>_ID "
                "token of a seeded Account (live ids are only known after provisioning)"
            )


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


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
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
