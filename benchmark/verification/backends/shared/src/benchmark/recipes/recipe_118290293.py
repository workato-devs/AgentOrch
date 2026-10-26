from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_118290293


RECIPE_ID = "118290293"
SEED_TYPE = "salesforce_recipe_function_last_sfdc_activity_variant"
TRACK = "live_salesforce_recipe_function_last_sfdc_activity"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "35a0e063"
SEARCH_AS = "2fc09276"
TASK_TYPES_IN = ("Email", "Call")
TRIGGER_ROW_KEYS = {"AccountID", "AccountName"}
BANNED_TRIGGER_ROW_KEYS = {"SuccessOwner_UserID"}
TASK_SEED_FIELD_KEYS = {"Subject", "Type", "WhatId", "Closed_Date__c"}
REQUIRED_SCHEMA = [
    {"sobject": "Activity", "field": "Closed_Date__c", "sf_type": "Date"},
]
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "35a0e063",
  "provider": "workato_recipe_function",
  "name": "execute",
  "skip": false,
  "input": {
   "parameters_schema_json": "[{\"name\":\"AccountList\",\"type\":\"array\",\"optional\":false,\"properties\":[{\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account ID\"},{\"name\":\"AccountName\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account name\"}],\"of\":\"object\",\"label\":\"Account list\"}]",
   "result_schema_json": "[{\"name\":\"LastSFDCActivity\",\"type\":\"array\",\"optional\":false,\"label\":\"Last SFDC Activity\",\"properties\":[{\"control_type\":\"text\",\"label\":\"Account ID\",\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"date\",\"label\":\"Last Activity\",\"name\":\"LastActivity\",\"type\":\"date_time\",\"optional\":false,\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\"}],\"of\":\"object\"}]"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "64a4fa81",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "account_ids_string": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"35a0e063\",\"path\":[\"parameters\",\"AccountList\"]}')&.pluck(\"AccountID\").join(\"','\")",
     "owner_ids_string": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"35a0e063\",\"path\":[\"parameters\",\"AccountList\"]}')&.pluck('SuccessOwner_UserID').uniq.join(\"','\")"
    },
    "schema": "[{\"control_type\":\"text\",\"label\":\"account_ids_string\",\"name\":\"account_ids_string\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"account_ids_string\"}},{\"name\":\"owner_ids_string\",\"type\":\"string\",\"optional\":true,\"label\":\"owner_ids_string\",\"details\":{\"real_name\":\"owner_ids_string\"},\"control_type\":\"text\"}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "2fc09276",
  "provider": "salesforce",
  "name": "search_sobjects_soql_v2",
  "skip": false,
  "input": {
   "limit": "2000",
   "output_schema": "[{\"control_type\":\"text\",\"label\":\"Account ID\",\"name\":\"AccountId\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"date\",\"label\":\"last_activity\",\"name\":\"last_activity\",\"type\":\"date_time\",\"optional\":false,\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\"}]",
   "query": "SELECT AccountId,\n       MAX(Closed_Date__c) last_activity\n  FROM Task\n WHERE Type IN ('Email', 'Call')\n   AND AccountId IN ('#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"64a4fa81\",\"path\":[\"account_ids_string\"]}')}')\n GROUP BY AccountId"
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "0d2e8b10",
  "provider": "workato_recipe_function",
  "name": "return_result",
  "skip": false,
  "input": {
   "result": {
    "LastSFDCActivity": {
     "AccountID": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2fc09276\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"AccountId\"]}')}",
     "LastActivity": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2fc09276\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"last_activity\"]}')}",
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"2fc09276\",\"path\":[\"records\"]}')}"
    }
   }
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "salesforce.search_records",
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


def validate_118290293(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_118290293(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118290293(raw)
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
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: forced action errors would fail the whole "
            "run instead of exercising a recipe branch"
        )
    expect = data.get("expect")
    _require_expect_shape(expect)
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
        # (103939956 precedent).
        "expect": resolved_expect,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": refs,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_118290293(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118290293(raw)
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    if not seed["salesforce_live"].get("strict_soql_conditions"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires strict_soql_conditions in the live state "
            "(Type IN / AccountId IN are strict-only operators)"
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
        # Required cleanup: owned Account + Task seed records must not leak
        # into later runs (the recipe itself only reads).
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
    result["verifier"] = verify_118290293(result)
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
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} AccountList rows must be objects: {row!r}")
        if set(row) & BANNED_TRIGGER_ROW_KEYS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} AccountList rows must NOT carry SuccessOwner_UserID: "
                "the trigger schema does not declare it, and seeding it would mask the "
                f"documented owner_ids_string falsy-render family: {row!r}"
            )
        if set(row) != TRIGGER_ROW_KEYS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} every AccountList row must carry exactly "
                f"{sorted(TRIGGER_ROW_KEYS)} (the trigger parameters schema): {row!r}"
            )
        for key in TRIGGER_ROW_KEYS:
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} AccountList row {key} must be a non-empty string: {row!r}"
                )
        if not row["AccountID"].startswith("$"):
            raise RuntimeError(
                f"recipe {RECIPE_ID} AccountID must be a $<REF>_ID token for a seeded "
                f"Account (live ids are run-generated): {row!r}"
            )


def _require_salesforce_section(section: Any) -> None:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce")
    if sorted(section) != ["records", "schema", "strict_soql_conditions"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce must be exactly "
            "{'strict_soql_conditions': true, 'schema': [...], 'records': [...]}"
        )
    if section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true "
            "(Type IN / AccountId IN are strict-only operators)"
        )
    if section.get("schema") != REQUIRED_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare exactly "
            f"{json.dumps(REQUIRED_SCHEMA)} (Task custom fields live on Activity; "
            "FLS is re-ensured every run)"
        )
    records = section.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records must be a non-empty list")
    account_refs_seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} seeded record must be an object: {record}")
        ref = str(record.get("ref") or "").strip()
        if not ref:
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded Salesforce record needs a 'ref': {record}"
            )
        fields = record.get("fields")
        if not isinstance(fields, dict) or not fields:
            raise RuntimeError(f"recipe {RECIPE_ID} every seeded record needs explicit fields: {record}")
        sobject = str(record.get("sobject") or "")
        if sobject == "Account":
            if set(fields) != {"Name"} or not str(fields.get("Name") or "").strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} Account seeds carry exactly a non-empty Name: {record}"
                )
            if record.get("read_fields") is not None:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} Account seeds need no read_fields: {record}"
                )
            account_refs_seen.add(ref.lower())
            continue
        if sobject != "Task":
            raise RuntimeError(
                f"recipe {RECIPE_ID} seeded records must be Account or Task: {record}"
            )
        if set(fields) != TASK_SEED_FIELD_KEYS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} Task seeds carry exactly "
                f"{sorted(TASK_SEED_FIELD_KEYS)}: {record}"
            )
        if record.get("read_fields") != ["AccountId"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} every Task seed must declare read_fields "
                "['AccountId'] (AccountId is DERIVED live from WhatId; without the "
                "read-back the strict AccountId IN leaf silently rejects the row): "
                f"{record}"
            )
        what_id = str(fields.get("WhatId") or "")
        what_ref = what_id[1:-3].lower() if what_id.startswith("$") and what_id.endswith("_ID") else ""
        if not what_ref or what_ref not in account_refs_seen:
            raise RuntimeError(
                f"recipe {RECIPE_ID} Task WhatId must be the $<REF>_ID token of an "
                f"Account seeded EARLIER in the records list (refs resolve in order): {record}"
            )
        if not str(fields.get("Subject") or "").strip() or not str(fields.get("Type") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} Task seeds need non-empty Subject and Type: {record}"
            )
        if not _DATE_RE.fullmatch(str(fields.get("Closed_Date__c") or "")):
            raise RuntimeError(
                f"recipe {RECIPE_ID} Task Closed_Date__c must be a YYYY-MM-DD date "
                f"(the recipe has no date-window arm, so static dates are rerun-safe): {record}"
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
    if expect.get("executed_action_count") != 3:
        raise RuntimeError(f"recipe {RECIPE_ID} the linear body always executes all 3 actions")
    if expect.get("tools") != ALLOWED_TOOLS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools must be exactly {ALLOWED_TOOLS}: "
            f"{expect.get('tools')!r}"
        )
    tool_expectations = expect.get("tool_expectations")
    if not isinstance(tool_expectations, list) or len(tool_expectations) != len(ALLOWED_TOOLS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry"
        )
    search_item = tool_expectations[0]
    if not isinstance(search_item, dict) or search_item.get("tool") != "salesforce.search_records":
        raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[0] must pin the SOQL search")
    args = search_item.get("args_contains")
    if not isinstance(args, dict) or args.get("sobject") != "Task" or args.get("limit") != "2000":
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0].args_contains must pin sobject "
            f"'Task' and limit '2000': {args!r}"
        )
    query = str(args.get("query") or "")
    if "MAX(Closed_Date__c) last_activity" not in query or "Type IN ('Email', 'Call')" not in query:
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0] must pin the resolved SOQL verbatim "
            f"(MAX alias + Type IN arms): {query!r}"
        )
    if not isinstance(search_item.get("result_count"), int):
        raise RuntimeError(
            f"recipe {RECIPE_ID} tool_expectations[0].result_count must pin the aggregate "
            "row count (0 on the empty branches)"
        )
    final_result = expect.get("final_result")
    if not isinstance(final_result, dict) or set(final_result) != {"LastSFDCActivity"} or not isinstance(
        final_result.get("LastSFDCActivity"), list
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_result must pin exactly "
            "{'LastSFDCActivity': [...]} ([] on the empty branches)"
        )
    for row in final_result["LastSFDCActivity"]:
        if not isinstance(row, dict) or set(row) != {"AccountID", "LastActivity"}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} LastSFDCActivity rows carry exactly "
                f"AccountID + LastActivity: {row!r}"
            )
        if not _DATE_RE.fullmatch(str(row.get("LastActivity") or "")):
            raise RuntimeError(
                f"recipe {RECIPE_ID} LastActivity must be the YYYY-MM-DD read-back of the "
                f"per-account MAX(Closed_Date__c): {row!r}"
            )
    if search_item["result_count"] != len(final_result["LastSFDCActivity"]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the ____source mapping is 1:1 -- result_count must equal "
            "the pinned LastSFDCActivity row count"
        )


def _salesforce_ref_tokens(seed_section: dict[str, Any], provision: dict[str, Any]) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    live_ids = [
        str(record.get("id") or "")
        for record in salesforce_snapshot.get("records") or []
        if isinstance(record, dict) and record.get("id") and not record.get("read_only")
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
