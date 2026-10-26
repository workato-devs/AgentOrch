from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_88676076


RECIPE_ID = "88676076"
SEED_TYPE = "workato_service_master_registration_sheet_variant"
TRACK = "live_google_sheets_service_master_registration"
TRIGGER_PROVIDER = "workato_service"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "22b103c4"
SEARCH_STEP_AS = "4cd73a31"
ADD_STEP_AS = "fb8e9257"
UPDATE_STEP_AS = "69ebf583"
CATCH_STEP_AS = "36d3b7d0"
ERROR_STOP_STEP = 10
FORCEABLE_STEPS = {SEARCH_STEP_AS}
SHEET_HEADERS = [
    "ID",
    "Status",
    "Event Name",
    "First Name",
    "Last Name",
    "Company",
    "Email",
    "Job Title",
    "Phone",
    "Country",
    "City",
    "Company Size",
    "UTM Campaign",
    "UTM Source",
    "UTM Medium",
    "UTM Content",
    "UTM Term",
    "Partner Referral",
    "Attended?",
    "Region",
    "Who should follow up?",
    "Account Type",
]
REQUEST_SCALAR_KEYS = ("lead_id", "status", "event_name")
REQUEST_LEAD_KEYS = ("first_name", "last_name", "email", "phone", "job_title")
REQUEST_COMPANY_KEYS = (
    "company", "tools", "tech_stack", "city", "country", "company_size", "region", "account_type",
)
REQUEST_MKTO_KEYS = (
    "utm_campaign", "utm_source", "utm_medium", "utm_content", "utm_term", "partner_referral",
)


_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "22b103c4",
  "provider": "workato_service",
  "name": "receive_request",
  "skip": false,
  "input": {
   "request_schema_json": "[{\"name\":\"lead_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"status\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"event_name\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"properties\":[{\"control_type\":\"text\",\"label\":\"First name\",\"name\":\"first_name\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Last name\",\"name\":\"last_name\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Email\",\"name\":\"email\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Phone\",\"name\":\"phone\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Job title\",\"name\":\"job_title\",\"type\":\"string\",\"optional\":false}],\"label\":\"Lead\",\"name\":\"Lead\",\"type\":\"object\",\"optional\":false},{\"properties\":[{\"control_type\":\"text\",\"label\":\"Company\",\"name\":\"company\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Tools\",\"name\":\"tools\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Tech stack\",\"name\":\"tech_stack\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"City\",\"name\":\"city\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Country\",\"name\":\"country\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Company size\",\"name\":\"company_size\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Region\",\"name\":\"region\",\"type\":\"string\",\"optional\":false},{\"name\":\"account_type\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"}],\"label\":\"Company\",\"name\":\"Company\",\"type\":\"object\",\"optional\":false},{\"properties\":[{\"control_type\":\"text\",\"label\":\"Utm campaign\",\"name\":\"utm_campaign\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Utm source\",\"name\":\"utm_source\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Utm medium\",\"name\":\"utm_medium\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Utm content\",\"name\":\"utm_content\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Utm term\",\"name\":\"utm_term\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Partner referral\",\"name\":\"partner_referral\",\"type\":\"string\",\"optional\":false}],\"label\":\"MKTO\",\"name\":\"MKTO\",\"type\":\"object\",\"optional\":false}]",
   "service_name": "Update Master Registration Sheet"
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
  "as": "4cd73a31",
  "provider": "google_sheets",
  "name": "search_spreadsheet_rows_v4_new",
  "skip": false,
  "input": {
   "column_headers": "ID\nStatus\nEvent Name\nFirst Name\nLast Name\nCompany\nEmail\nJob Title\nPhone\nCountry\nCity\nCompany Size\nUTM Campaign\nUTM Source\nUTM Medium\nUTM Content\nUTM Term\nPartner Referral\nAttended?\nRegion\nWho should follow up?\nAccount Type",
   "count": "2000",
   "data": {
    "col_Event Name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"event_name\"]}')}",
    "col_ID": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"lead_id\"]}')}"
   },
   "sheet_name": "Main",
   "spreadsheet_id": "<anon>2PqR8StU9VwX0YzA1BcD2EfG3HiJ4KlM5NoPqRsT6Uv</anon>",
   "team_drives": "my_drive"
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
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"4cd73a31\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}",
     "operand": "less_than",
     "rhs": "1"
    }
   ],
   "operand": "and",
   "type": "compound"
  }
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "fb8e9257",
  "provider": "google_sheets",
  "name": "add_spreadsheet_row_v4",
  "skip": false,
  "input": {
   "column_headers": "ID\nStatus\nEvent Name\nFirst Name\nLast Name\nCompany\nEmail\nJob Title\nPhone\nCountry\nCity\nCompany Size\nUTM Campaign\nUTM Source\nUTM Medium\nUTM Content\nUTM Term\nPartner Referral\nAttended?\nRegion\nWho should follow up?\nAccount Type",
   "columns": {
    "col_Account Type": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"Company\", \"account_type\"]}')}",
    "col_City": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"Company\", \"city\"]}')}",
    "col_Company": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"Company\", \"company\"]}')}",
    "col_Company Size": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"Company\", \"company_size\"]}')}",
    "col_Country": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"Company\", \"country\"]}')}",
    "col_Email": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"Lead\", \"email\"]}')}",
    "col_Event Name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"event_name\"]}')}",
    "col_First Name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"Lead\", \"first_name\"]}')}",
    "col_ID": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"lead_id\"]}')}",
    "col_Job Title": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"Lead\", \"job_title\"]}')}",
    "col_Last Name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"Lead\", \"last_name\"]}')}",
    "col_Partner Referral": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"MKTO\", \"partner_referral\"]}')}",
    "col_Phone": "'#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"Lead\", \"phone\"]}')}",
    "col_Region": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"Company\", \"region\"]}')}",
    "col_Status": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"status\"]}')}",
    "col_UTM Campaign": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"MKTO\", \"utm_campaign\"]}')}",
    "col_UTM Content": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"MKTO\", \"utm_content\"]}')}",
    "col_UTM Medium": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"MKTO\", \"utm_medium\"]}')}",
    "col_UTM Source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"MKTO\", \"utm_source\"]}')}",
    "col_UTM Term": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"MKTO\", \"utm_term\"]}')}"
   },
   "sheet_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"4cd73a31\",\"path\":[\"sheet\"]}')}",
   "spreadsheet_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"4cd73a31\",\"path\":[\"spreadsheet_id\"]}')}",
   "team_drives": "my_drive"
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
     "lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"4cd73a31\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}",
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
  "as": "69ebf583",
  "provider": "google_sheets",
  "name": "update_row_v4_new",
  "skip": false,
  "input": {
   "column_headers": "ID\nStatus\nEvent Name\nFirst Name\nLast Name\nCompany\nEmail\nJob Title\nPhone\nCountry\nCity\nCompany Size\nUTM Campaign\nUTM Source\nUTM Medium\nUTM Content\nUTM Term\nPartner Referral\nAttended?\nRegion\nWho should follow up?\nAccount Type",
   "data": {
    "col_Account Type": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"Company\", \"account_type\"]}')}",
    "col_Status": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_service\",\"line\":\"22b103c4\",\"path\":[\"request\", \"status\"]}')}"
   },
   "row_number": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"4cd73a31\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"row_number\"]}')}",
   "sheet_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"4cd73a31\",\"path\":[\"sheet\"]}')}",
   "spreadsheet_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"google_sheets\",\"line\":\"4cd73a31\",\"path\":[\"spreadsheet_id\"]}')}",
   "team_drives": "my_drive"
  }
 },
 {
  "keyword": "catch",
  "number": 8,
  "as": "36d3b7d0",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "max_retry_count": "1",
   "retry_interval": "10"
  }
 },
 {
  "keyword": "action",
  "number": 9,
  "as": "50073cae",
  "provider": "workato_service",
  "name": "send_reply",
  "skip": false,
  "input": {
   "message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"36d3b7d0\",\"path\":[\"message\"]}')}",
   "reply_type": "error"
  }
 },
 {
  "keyword": "stop",
  "number": 10,
  "as": null,
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "stop_reason": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"36d3b7d0\",\"path\":[\"message\"]}')}",
   "stop_with_error": "true"
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "google_sheets.search_spreadsheet_rows_v4_new",
    "google_sheets.add_spreadsheet_row_v4",
    "google_sheets.update_row_v4_new",
    "workato_service.send_reply",
]
ALLOWED_TOOLS: list[str] = [
    "google_sheets.search_spreadsheet_rows_v4_new",
    "google_sheets.add_spreadsheet_row_v4",
    "google_sheets.update_row_v4_new",
    "workato_service.send_reply",
]
EXPECT_KEYS = ("executed_action_count", "tools", "tool_expectations", "stopped")
OPTIONAL_EXPECT_KEYS = {"case", "stop_step_number", "catch_message", "final_sheet_rows", "return_value"}


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


def validate_88676076(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_88676076(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88676076(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    unexpected = sorted(set(seed_in) - {"sheets"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed has unexpected sections: {unexpected}")
    expect = data.get("expect")
    force = data.get("force_action_error")
    _require_force_shape(force)
    _require_expect_shape(expect, force)
    tools_expected = expect.get("tools") or []
    needs_sheets = "google_sheets.search_spreadsheet_rows_v4_new" in tools_expected
    sheets_section = seed_in.get("sheets")
    if needs_sheets != isinstance(sheets_section, dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets must be present exactly when the variant "
            f"expects the sheets search to execute (needs_sheets={needs_sheets})"
        )
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": deepcopy(expect),
    }
    if isinstance(sheets_section, dict):
        _require_sheets_section(sheets_section, trigger, expect)
        if not ctx.env.sheets_spreadsheet_id or not ctx.env.sheets_tab:
            raise RuntimeError("missing SHEETS_SPREADSHEET_ID / SHEETS_TAB; refusing to guess")
        seed_response = ctx.tools.call("harness.google_sheets.seed_rows", {"sheets": sheets_section})
        if not seed_response.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Google Sheets seed failed: {seed_response}")
        out["sheets"] = deepcopy(sheets_section)
        out["sheets_seed_response"] = seed_response
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_88676076(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_88676076(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    sheets_expected = "google_sheets.search_spreadsheet_rows_v4_new" in (expect.get("tools") or [])
    if sheets_expected and not isinstance(seed.get("sheets"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing the sheets section")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    details["initial_snapshot"] = _snapshot(ctx, seed)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    details["raw_execution"] = raw_execution
    details["ground_truth"] = _ground_truth(raw_execution)
    details["final_snapshot"] = _snapshot(ctx, seed)
    # Cleanup per the cleanup principle: the seed fully overwrites the
    # benchmark tab on every run (harness.google_sheets.seed_rows clears the
    # tab first) and the service reply is Workato-internal state -- no
    # cleanup step is required for deterministic reruns.
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_88676076(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if set(trigger) != {"request"} or not isinstance(trigger.get("request"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input must be exactly {{'request': {{...}}}}")
    request = trigger["request"]
    expected_keys = set(REQUEST_SCALAR_KEYS) | {"Lead", "Company", "MKTO"}
    if set(request) != expected_keys:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger request must carry exactly {sorted(expected_keys)}; "
            f"got {sorted(request)}"
        )
    for key in REQUEST_SCALAR_KEYS:
        if not isinstance(request.get(key), str) or not request[key].strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger request.{key} must be a non-empty string "
                "(the request schema marks it required)"
            )
    for section, keys in (
        ("Lead", REQUEST_LEAD_KEYS),
        ("Company", REQUEST_COMPANY_KEYS),
        ("MKTO", REQUEST_MKTO_KEYS),
    ):
        value = request.get(section)
        if not isinstance(value, dict) or set(value) != set(keys):
            raise RuntimeError(
                f"recipe {RECIPE_ID} trigger request.{section} must carry exactly {sorted(keys)}; "
                f"got {sorted(value) if isinstance(value, dict) else value!r}"
            )
        for key in keys:
            if not isinstance(value.get(key), str):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} trigger request.{section}.{key} must be a string "
                    "(the request schema marks every field required; '' is an explicit blank)"
                )
    if "@" not in str(request["Lead"].get("email")):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger request.Lead.email must be a real address")


def _require_sheets_section(section: dict[str, Any], trigger: dict[str, Any], expect: dict[str, Any]) -> None:
    if section.get("headers") != SHEET_HEADERS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets.headers must pin the 22 raw column headers exactly"
        )
    rows = section.get("rows")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.sheets.rows must be a non-empty explicit list "
            "(the add variant seeds a non-matching decoy row, never an empty tab)"
        )
    request = trigger["request"]
    lead_id = str(request.get("lead_id"))
    event_name = str(request.get("event_name"))
    matches = 0
    for row in rows:
        if not isinstance(row, dict) or not set(row) <= set(SHEET_HEADERS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed.sheets rows must only use the declared headers: {row!r}"
            )
        if not str(row.get("ID") or "").strip() or not str(row.get("Event Name") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded sheet row needs explicit ID and Event Name "
                "(the search key columns)"
            )
        if str(row.get("ID")) == lead_id and str(row.get("Event Name")) == event_name:
            matches += 1
    update_expected = "google_sheets.update_row_v4_new" in (expect.get("tools") or [])
    if update_expected and matches != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} update variants must seed exactly one row matching "
            f"lead_id={lead_id!r} + event_name={event_name!r} (got {matches})"
        )
    if not update_expected and matches:
        raise RuntimeError(
            f"recipe {RECIPE_ID} add variants must not seed a row matching "
            f"lead_id={lead_id!r} + event_name={event_name!r}"
        )


def _require_force_shape(force: Any) -> None:
    if force is None:
        return
    if not isinstance(force, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error must be an object")
    if str(force.get("step_as") or "") not in FORCEABLE_STEPS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error.step_as must be one of {sorted(FORCEABLE_STEPS)}"
        )
    if not str(force.get("error") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error.error must be a non-empty message")


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
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry")
    unknown_tools = sorted(set(tools) - set(ALLOWED_TOOLS))
    if unknown_tools:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools has unknown tools: {unknown_tools}")
    if not isinstance(expect.get("stopped"), bool):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.stopped must be a bool")
    write_tools = {"google_sheets.add_spreadsheet_row_v4", "google_sheets.update_row_v4_new"}
    if force is not None:
        if tools != ["workato_service.send_reply"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} forced-error variants execute exactly the catch send_reply"
            )
        if not expect["stopped"] or str(expect.get("stop_step_number")) != str(ERROR_STOP_STEP):
            raise RuntimeError(
                f"recipe {RECIPE_ID} forced-error variants stop with error at step {ERROR_STOP_STEP}"
            )
        if str(expect.get("catch_message") or "") != str(force.get("error")):
            raise RuntimeError(f"recipe {RECIPE_ID} expect.catch_message must equal the forced error")
        return_value = expect.get("return_value")
        if not isinstance(return_value, dict) or return_value.get("reply_type") != "error":
            raise RuntimeError(
                f"recipe {RECIPE_ID} forced-error variants must pin expect.return_value "
                "(the error send_reply payload)"
            )
        if "final_sheet_rows" in expect:
            raise RuntimeError(
                f"recipe {RECIPE_ID} the forced search error never touches the tab: "
                "catch variants must not pin final_sheet_rows"
            )
    else:
        for key in ("catch_message", "stop_step_number"):
            if key in expect:
                raise RuntimeError(f"recipe {RECIPE_ID} only forced-error variants pin {key}")
        if expect["stopped"]:
            raise RuntimeError(f"recipe {RECIPE_ID} unforced paths run to completion")
        if expect.get("return_value") is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} the success path sends NO service reply: "
                "expect.return_value must be null/omitted"
            )
        if not tools or tools[0] != "google_sheets.search_spreadsheet_rows_v4_new":
            raise RuntimeError(f"recipe {RECIPE_ID} every unforced path starts with the step-3 search")
        chosen = [tool for tool in tools if tool in write_tools]
        if len(chosen) != 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} exactly one of add/update fires per run; got {chosen}"
            )
        if not isinstance(expect.get("final_sheet_rows"), list) or not expect["final_sheet_rows"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} sheet-writing variants must pin expect.final_sheet_rows "
                "(the exact FORMATTED read-back of the whole benchmark tab)"
            )


def _snapshot(ctx: RecipeContext, seed: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(seed.get("sheets"), dict):
        out["google_sheets"] = ctx.tools.call("harness.google_sheets.snapshot", {})
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
