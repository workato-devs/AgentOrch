from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_123864475


RECIPE_ID = "123864475"
SEED_TYPE = "api_platform_bluebirds_signal_lookup_variant"
TRACK = "live_salesforce_bluebirds_signal_api"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "7c9bdd0d"
GET_STEP_AS = "a495f9f5"
CATCH_STEP_AS = "86806634"
NOT_FOUND_STOP = {"number": 7, "as": "cf26d231"}
ACCOUNT_ID_TOKEN = "$ACCOUNT_ID"
RAW_SOURCE_SNIPPET = "BlueBirds Compelling Events"
RAW_SOURCE_TITLE = "BlueBirds"
RAW_SOURCE_TOOL = "bluebirds"
URL_PREFIX = "https://workato.salesforce.com/"
REQUIRED_SCHEMA = [
    {"sobject": "Account", "field": "Bluebirds_Signal_Summary__c", "sf_type": "LongTextArea"},
]
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")


_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "7c9bdd0d",
  "provider": "workato_api_platform",
  "name": "receive_request",
  "skip": false,
  "input": {
   "request": {
    "content_type": "json",
    "path_params": "[]",
    "schema": "[{\"name\":\"sfdcAccountId\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Sfdc account ID\"}]"
   },
   "response": {
    "content_type": "json",
    "responses": [
     {
      "body_schema": "[{\"name\":\"data\",\"type\":\"array\",\"of\":\"object\",\"label\":\"data\",\"properties\":[{\"name\":\"events\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Events\"}],\"optional\":true},{\"name\":\"rawSources\",\"type\":\"array\",\"of\":\"object\",\"label\":\"Raw sources\",\"properties\":[{\"control_type\":\"text\",\"label\":\"Title\",\"type\":\"string\",\"name\":\"title\"},{\"control_type\":\"text\",\"label\":\"Snippet\",\"type\":\"string\",\"name\":\"snippet\"},{\"control_type\":\"text\",\"label\":\"URL\",\"type\":\"string\",\"name\":\"url\"},{\"control_type\":\"text\",\"label\":\"Tool\",\"type\":\"string\",\"name\":\"tool\"}],\"optional\":true},{\"name\":\"error\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\",\"label\":\"Error\"},{\"name\":\"success\",\"type\":\"boolean\",\"optional\":false,\"control_type\":\"checkbox\",\"label\":\"Success\",\"render_input\":\"boolean_conversion\",\"parse_output\":\"boolean_conversion\",\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Success\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"success\",\"type\":\"boolean\",\"optional\":false}}]",
      "http_status_code": "200",
      "name": "Success"
     }
    ]
   }
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
  "as": "a495f9f5",
  "provider": "salesforce",
  "name": "get_custom_object",
  "skip": false,
  "input": {
   "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"7c9bdd0d\",\"path\":[\"request\", \"sfdcAccountId\"]}')}",
   "sobject_name": "Account"
  }
 },
 {
  "keyword": "if",
  "number": 4,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "conditions": [
    {
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a495f9f5\",\"path\":[\"Id\"]}')}",
     "operand": "present"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "252ace50",
  "provider": "workato_api_platform",
  "name": "return_response",
  "skip": false,
  "input": {
   "http_status_code": "200",
   "response": {
    "data": [
     {
      "events": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a495f9f5\",\"path\":[\"Bluebirds_Signal_Summary__c\"]}')}"
     }
    ],
    "rawSources": [
     {
      "snippet": "BlueBirds Compelling Events",
      "title": "BlueBirds",
      "tool": "bluebirds",
      "url": "https://workato.salesforce.com/#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"a495f9f5\",\"path\":[\"Id\"]}')}"
     }
    ],
    "success": "true"
   }
  }
 },
 {
  "keyword": "else",
  "number": 6,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {}
 },
 {
  "keyword": "stop",
  "number": 7,
  "as": "cf26d231",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "stop_reason": "No records found",
   "stop_with_error": "true"
  }
 },
 {
  "keyword": "catch",
  "number": 8,
  "as": "86806634",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "max_retry_count": "0",
   "retry_interval": "2"
  }
 },
 {
  "keyword": "action",
  "number": 9,
  "as": "edfa1c85",
  "provider": "workato_api_platform",
  "name": "return_response",
  "skip": false,
  "input": {
   "http_status_code": "200",
   "response": {
    "error": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"86806634\",\"path\":[\"message\"]}')}",
    "success": "false"
   }
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = [
    "salesforce.search_records",
    "workato_api_platform.return_response",
]
BASE_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "requested_account_id",
)
OPTIONAL_EXPECT_KEYS = {
    "case",
    "http_status_code",
    "response",
    "stopped",
    "stop_step_number",
    "stop_step_as",
    "catch_message",
    "get_record_fields",
}


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


def validate_123864475(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_123864475(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_123864475(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    requested_id = _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"salesforce"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    force = data.get("force_action_error")
    expect = data.get("expect")
    branch = _require_expect_shape(expect, requested_id, force, seed_in.get("salesforce"))
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "branch": branch,
    }
    refs: dict[str, str] = {}
    if isinstance(seed_in.get("salesforce"), dict):
        provision = ctx.tools.call(
            "harness.salesforce.seed_records", {"salesforce": seed_in["salesforce"]}
        )
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
        refs = _salesforce_ref_tokens(seed_in["salesforce"], provision)
        out["salesforce_live"] = deepcopy(provision["state"])
        out["salesforce_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
        out["salesforce_ref_tokens"] = dict(refs)
        if branch == "not_found_stop" and requested_id in refs.values():
            raise RuntimeError(
                f"recipe {RECIPE_ID} not-found variant requested a LIVE seeded id "
                f"({requested_id}); the requested id must not exist"
            )
    out["trigger"] = _replace_value(trigger, refs)
    _require_resolved(out["trigger"], "trigger")
    out["expect"] = _replace_value(deepcopy(expect), refs)
    _require_resolved(out["expect"], "expect")
    if isinstance(force, dict):
        out["force_action_error"] = deepcopy(force)
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_123864475(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_123864475(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if "salesforce.search_records" in (expect.get("tools") or []) and not isinstance(
        seed.get("salesforce_live"), dict
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} this variant executes the live Account get but the seed "
            "file has no salesforce_live state"
        )
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "branch": seed.get("branch"),
        "expect": expect,
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    cleanup_response: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = _snapshot(ctx, seed)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx, seed)
    finally:
        # Required cleanup whenever this run live-seeded benchmark records.
        if isinstance(seed.get("salesforce_live"), dict):
            cleanup_response = ctx.tools.call("harness.salesforce.cleanup", {})
            details["cleanup_response"] = cleanup_response
    if isinstance(seed.get("salesforce_live"), dict) and not (cleanup_response or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce cleanup failed: {cleanup_response}")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_123864475(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> str:
    if set(trigger) != {"request"} or not isinstance(trigger.get("request"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'request': {{...}}}}"
        )
    request = trigger["request"]
    if set(request) != {"sfdcAccountId"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} request must carry exactly the declared schema field "
            f"sfdcAccountId (required): {sorted(request)}"
        )
    requested = request.get("sfdcAccountId")
    if not isinstance(requested, str) or not requested.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} request.sfdcAccountId must be a non-empty string")
    return requested


def _require_salesforce_section(section: Any, *, want_summary_record: bool) -> None:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce for this variant")
    unexpected = sorted(set(section) - {"schema", "records"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce has unexpected keys: {unexpected}")
    if section.get("schema") != REQUIRED_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare exactly "
            f"{json.dumps(REQUIRED_SCHEMA)}"
        )
    records = section.get("records")
    if not isinstance(records, list) or len(records) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.records must contain exactly one Account "
            f"({'the requested record' if want_summary_record else 'the not-found decoy'})"
        )
    record = records[0]
    if not isinstance(record, dict) or record.get("sobject") != "Account":
        raise RuntimeError(f"recipe {RECIPE_ID} the seeded record must be an Account: {record}")
    if str(record.get("ref") or "") != "account":
        raise RuntimeError(f"recipe {RECIPE_ID} the seeded Account ref must be 'account': {record}")
    fields = record.get("fields")
    if not isinstance(fields, dict) or set(fields) != {"Name", "Bluebirds_Signal_Summary__c"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the seeded Account fields must be exactly "
            f"{{'Name', 'Bluebirds_Signal_Summary__c'}}: {record}"
        )
    if not str(fields.get("Name") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} the seeded Account needs a non-empty Name")
    if not str(fields.get("Bluebirds_Signal_Summary__c") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} the seeded Account needs a non-empty "
            f"Bluebirds_Signal_Summary__c (the recipe returns it as the events text)"
        )


def _require_expect_shape(
    expect: Any, requested_id: str, force: Any, salesforce_section: Any
) -> str:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect object")
    missing = [key for key in BASE_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(set(expect) - set(BASE_EXPECT_KEYS) - OPTIONAL_EXPECT_KEYS)
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has unexpected keys: {unknown}")
    if expect.get("requested_account_id") != requested_id:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.requested_account_id must equal "
            f"request.sfdcAccountId ({requested_id!r}): {expect.get('requested_account_id')!r}"
        )
    tools = expect.get("tools")
    items = expect.get("tool_expectations")
    if not isinstance(tools, list) or not isinstance(items, list) or len(tools) != len(items):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry"
        )
    if [item.get("tool") for item in items if isinstance(item, dict)] != tools:
        raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations order must match expect.tools")
    get_args = {
        "sobject": "Account",
        "query": "",
        "filters": [{"field": "Id", "value": requested_id}],
        "limit": 1,
    }

    if force is not None:
        # forced_catch_error branch.
        if not (
            isinstance(force, dict)
            and set(force) == {"step_as", "error"}
            and force.get("step_as") == GET_STEP_AS
            and str(force.get("error") or "").strip()
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} force_action_error must target exactly step "
                f"{GET_STEP_AS} with a pinned literal error: {force!r}"
            )
        if salesforce_section is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} the forced-catch variant must not seed Salesforce "
                "(the get raises before any live call)"
            )
        expected_response = {"error": str(force["error"]), "success": "false"}
        if expect.get("catch_message") != str(force["error"]):
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.catch_message must pin the forced error bytes"
            )
        if expect.get("http_status_code") != "200" or expect.get("response") != expected_response:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variant must expect 200 "
                f"{json.dumps(expected_response)}: {json.dumps(expect.get('response'))}"
            )
        if "stopped" in expect or "get_record_fields" in expect:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variant must not declare stop/get expectations"
            )
        if expect.get("executed_action_count") != 1 or tools != ["workato_api_platform.return_response"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variant executes exactly the edfa1c85 "
                "return_response (the forced get never reaches its tool call)"
            )
        item = items[0]
        if item.get("http_status_code") != "200" or item.get("args_contains") != {
            "http_status_code": "200",
            "response": expected_response,
        }:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch tool_expectations[0] must pin the exact "
                f"response body and status: {json.dumps(item)}"
            )
        return "forced_catch"

    if expect.get("stopped") is True:
        # account_not_found_stop branch (reachable since f01d3363: the get
        # returns EMPTY output on a missing record).
        if (
            expect.get("stop_step_number") != NOT_FOUND_STOP["number"]
            or expect.get("stop_step_as") != NOT_FOUND_STOP["as"]
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} the not-found path stops at step "
                f"{NOT_FOUND_STOP['number']} ({NOT_FOUND_STOP['as']})"
            )
        if "http_status_code" in expect or "response" in expect or "get_record_fields" in expect:
            raise RuntimeError(
                f"recipe {RECIPE_ID} the stop path returns NO response; expect must not "
                "declare response/get keys"
            )
        if requested_id.startswith("$"):
            raise RuntimeError(
                f"recipe {RECIPE_ID} not-found variant must request a literal nonexistent "
                f"id, not a seed token: {requested_id!r}"
            )
        _require_salesforce_section(salesforce_section, want_summary_record=False)
        if expect.get("executed_action_count") != 1 or tools != ["salesforce.search_records"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} the stop path executes exactly the one Account get"
            )
        item = items[0]
        if item.get("args_contains") != get_args or item.get("result_count") != 0:
            raise RuntimeError(
                f"recipe {RECIPE_ID} stop tool_expectations[0] must pin the get args "
                f"{json.dumps(get_args)} with result_count 0: {json.dumps(item)}"
            )
        return "not_found_stop"

    # account_found_success branch.
    if requested_id != ACCOUNT_ID_TOKEN:
        raise RuntimeError(
            f"recipe {RECIPE_ID} found variant must request the live seeded Account via "
            f"{ACCOUNT_ID_TOKEN}: {requested_id!r}"
        )
    _require_salesforce_section(salesforce_section, want_summary_record=True)
    summary = str(salesforce_section["records"][0]["fields"]["Bluebirds_Signal_Summary__c"])
    expected_response = {
        "data": [{"events": summary}],
        "rawSources": [
            {
                "snippet": RAW_SOURCE_SNIPPET,
                "title": RAW_SOURCE_TITLE,
                "tool": RAW_SOURCE_TOOL,
                "url": f"{URL_PREFIX}{ACCOUNT_ID_TOKEN}",
            }
        ],
        "success": "true",
    }
    if expect.get("http_status_code") != "200" or expect.get("response") != expected_response:
        raise RuntimeError(
            f"recipe {RECIPE_ID} found variant must expect 200 "
            f"{json.dumps(expected_response)}: {json.dumps(expect.get('response'))}"
        )
    if expect.get("get_record_fields") != {
        "Id": ACCOUNT_ID_TOKEN,
        "Bluebirds_Signal_Summary__c": summary,
    }:
        raise RuntimeError(
            f"recipe {RECIPE_ID} found variant must pin get_record_fields "
            "{Id: $ACCOUNT_ID, Bluebirds_Signal_Summary__c: <seeded summary>} so the "
            "response bytes are grounded in the live read-back"
        )
    if "stopped" in expect or "catch_message" in expect:
        raise RuntimeError(
            f"recipe {RECIPE_ID} found variant must not declare stop/catch expectations"
        )
    if expect.get("executed_action_count") != 2 or tools != [
        "salesforce.search_records",
        "workato_api_platform.return_response",
    ]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} found variant executes exactly the get then the 252ace50 "
            "return_response"
        )
    if items[0].get("args_contains") != get_args or items[0].get("result_count") != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} found tool_expectations[0] must pin the get args "
            f"{json.dumps(get_args)} with result_count 1: {json.dumps(items[0])}"
        )
    if items[1].get("http_status_code") != "200" or items[1].get("args_contains") != {
        "http_status_code": "200",
        "response": expected_response,
    }:
        raise RuntimeError(
            f"recipe {RECIPE_ID} found tool_expectations[1] must pin the exact response "
            f"body and status: {json.dumps(items[1])}"
        )
    return "found_success"


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


def _require_resolved(value: dict[str, Any], label: str) -> None:
    leftover = _TOKEN_RE.findall(json.dumps(value))
    if leftover:
        raise RuntimeError(f"recipe {RECIPE_ID} {label} has unresolved seed tokens: {leftover}")


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    if isinstance(seed.get("salesforce_live"), dict):
        return ctx.tools.call("harness.salesforce.snapshot", {})
    return {}


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
