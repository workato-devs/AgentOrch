from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_123154292


RECIPE_ID = "123154292"
SEED_TYPE = "api_platform_walnutiq_company_output_poll_variant"
TRACK = "workato_api_platform_walnutiq_company_output_poll"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "7caed8cf"
OUTPUTS_TABLE = "walnutiq.outputs"
SQL_STEP_AS = "32de9a12"
SUCCESS_RETURN_AS = "9fd5b1dd"
CATCH_RETURN_AS = "f87b9db6"
CATCH_AS = "1a33231f"
RAW_SQL = (
    "SELECT id, content, created_at, output_file_id FROM walnutiq.outputs "
    "WHERE company_id = :id ORDER BY created_at DESC LIMIT 1"
)

# workato_api_platform.receive_request (as 7caed8cf; path_params.company_id
# is the ONLY dereferenced trigger field; responses declared 200/500).
# Registered precedent: 122809739 (batch 04) -- same walnutiq schema family,
# same TRY/return/catch skeleton -- but THIS recipe has NO rows-size IF: the
# 200 body always renders. Body = one TRY:
#   3  snowflake.run_custom_sql 32de9a12 (LIVE Snowflake): RAW_SQL with the
#      FORMULA-MODE bind parameters.data.id =
#      `=_dp(path_params.company_id).to_i` -> INT (re-probed: '512' -> 512);
#      :id binds via pyformat, ORDER BY created_at DESC LIMIT 1 is carried by
#      the SQL itself (the connector appends nothing).
#   4  return_response 9fd5b1dd http 200 {content / created_at / id <-
#      rows current_item <col>, file_link <- rows current_item
#      output_file_id} -- current_item OUTSIDE any foreach = FIRST row;
#      TERMINAL (stops the run).
#   5  CATCH 1a33231f (max_retry_count 0) -> 6 return_response f87b9db6
#      http 500 {message: #{catch.1a33231f.message}}
#
# Branch mapping (per benmark_rules):
# - latest-row 200: rows exist for the bound company -> the newest one (ORDER
#   BY created_at DESC LIMIT 1) fills all four fields. 2 actions.
# - zero-row 200: no row for the company -> rows [] -> current_item MISSING.
#   ENGINE FACT (re-probed, CORRECTING the triage note): the response dict
#   resolves through resolve_value, which renders MISSING pills as JSON
#   null -- NOT '' (resolve_text's rendering never runs here). The 200 body
#   is {content: null, created_at: null, file_link: null, id: null}; expects
#   pin the nulls explicitly. (Real Workato also renders nulls, so this is
#   the faithful shape.) 2 actions.
# - catch 500: seed.force_action_error on 32de9a12 raises BEFORE the live
#   adapter -> catch -> 500 {message}. 1 action; the variant owns NO live
#   state (empty seed, no snapshots, no cleanup call).
#
# ENGINE FIDELITY NOTES:
# - created_at renders as snowflake_live._json_value isoformat of the live
#   TIMESTAMP_NTZ read-back (naive, e.g. '2026-07-02T09:30:00'); seeds use
#   'YYYY-MM-DD HH:MM:SS' literals so the rendered form is stable and the
#   expects pin it exactly.
# - the ID/CONTENT/OUTPUT_FILE_ID columns are seeded as strings (the recipe
#   output_schema types them text); COMPANY_ID is NUMBER so the int bind
#   compares natively.
# - the ORDER BY needs a UNIQUE newest row: the seeder requires distinct
#   created_at values among the bound company's rows.
# Backends: Snowflake runs LIVE (create-or-replace, dropped in the runner's
# finally); the API platform trigger/responses are deterministic
# Workato-internal mocks (terminal). READ-ONLY on Snowflake.

_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "7caed8cf",
  "provider": "workato_api_platform",
  "name": "receive_request",
  "skip": false,
  "input": {
   "request": {
    "content_type": "json",
    "path_params": "[{\"control_type\":\"text\",\"label\":\"Company ID\",\"name\":\"company_id\",\"type\":\"string\",\"optional\":false}]"
   },
   "response": {
    "content_type": "json",
    "responses": [
     {
      "body_schema": "[{\"control_type\":\"text\",\"label\":\"ID\",\"type\":\"string\",\"name\":\"id\"},{\"control_type\":\"text\",\"label\":\"Content\",\"type\":\"string\",\"name\":\"content\"},{\"control_type\":\"text\",\"label\":\"Created at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"type\":\"date_time\",\"name\":\"created_at\"},{\"name\":\"file_link\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"File link\"}]",
      "http_status_code": "200",
      "name": "Success"
     },
     {
      "body_schema": "[{\"name\":\"message\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Message\"}]",
      "http_status_code": "500",
      "name": "Error"
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
  "as": "32de9a12",
  "provider": "snowflake",
  "name": "run_custom_sql",
  "skip": false,
  "input": {
   "output_schema": "[{\"control_type\":\"text\",\"label\":\"ID\",\"type\":\"string\",\"name\":\"id\"},{\"control_type\":\"text\",\"label\":\"Content\",\"type\":\"string\",\"name\":\"content\"},{\"control_type\":\"text\",\"label\":\"Created at\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\",\"type\":\"date_time\",\"name\":\"created_at\"},{\"control_type\":\"text\",\"label\":\"Output file ID\",\"type\":\"string\",\"name\":\"output_file_id\"}]",
   "parameters": {
    "data": {
     "id": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"7caed8cf\",\"path\":[\"path_params\",\"company_id\"]}').to_i"
    },
    "schema": "[{\"name\":\"id\",\"type\":\"integer\",\"optional\":true,\"label\":\"id\",\"details\":{\"real_name\":\"id\"},\"control_type\":\"integer\"}]"
   },
   "sql": "SELECT id, content, created_at, output_file_id FROM walnutiq.outputs WHERE company_id = :id ORDER BY created_at DESC LIMIT 1",
   "update_only": "false"
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "9fd5b1dd",
  "provider": "workato_api_platform",
  "name": "return_response",
  "skip": false,
  "input": {
   "http_status_code": "200",
   "response": {
    "content": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"32de9a12\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"content\"]}')}",
    "created_at": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"32de9a12\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"created_at\"]}')}",
    "file_link": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"32de9a12\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"output_file_id\"]}')}",
    "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"32de9a12\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}"
   }
  }
 },
 {
  "keyword": "catch",
  "number": 5,
  "as": "1a33231f",
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
  "number": 6,
  "as": "f87b9db6",
  "provider": "workato_api_platform",
  "name": "return_response",
  "skip": false,
  "input": {
   "http_status_code": "500",
   "response": {
    "message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"1a33231f\",\"path\":[\"message\"]}')}"
   }
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = list(EXPECTED_RAW_TOOLS)
EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "http_status_code",
    "response",
    "return_step_as",
)
OPTIONAL_EXPECT_KEYS = {"catch_message"}
RETURN_STEP_AS = (SUCCESS_RETURN_AS, CATCH_RETURN_AS)
OUTPUTS_COLUMNS = {
    "ID": "string",
    "CONTENT": "string",
    "CREATED_AT": "timestamp",
    "OUTPUT_FILE_ID": "string",
    "COMPANY_ID": "number",
}
_CREATED_AT_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


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


def validate_123154292(raw: dict[str, Any]) -> dict[str, Any]:
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
    sql_pin = next(pin for pin in actual if pin["as"] == SQL_STEP_AS)
    if sql_pin["input"].get("sql") != RAW_SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} custom SQL changed: {sql_pin['input'].get('sql')!r}")
    bind = ((sql_pin["input"].get("parameters") or {}).get("data") or {}).get("id")
    if not (isinstance(bind, str) and bind.startswith("=_dp(") and bind.endswith(".to_i")):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the formula-mode integer bind changed: {bind!r} -- the "
            "int-vs-NUMBER column analysis no longer holds"
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


def seed_123154292(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_123154292(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    company_id = _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    expect = data.get("expect")
    force = data.get("force_action_error")
    _require_force_shape(force)
    _require_expect_shape(expect, force)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": deepcopy(expect),
    }
    if force is not None:
        # CATCH branch: the forced error fires BEFORE the snowflake adapter
        # runs, so this variant owns no live resources and must not seed any.
        if sorted(seed_in.keys()) != []:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must not seed live sections "
                f"(nothing runs against Snowflake); got {sorted(seed_in.keys())}"
            )
    else:
        if sorted(seed_in.keys()) != ["snowflake_live"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} non-catch variants must seed exactly the "
                f"snowflake_live section; got {sorted(seed_in.keys())}"
            )
        rows = _require_snowflake_section(seed_in["snowflake_live"], company_id)
        derived = _derive_response(rows, company_id)
        if expect.get("response") != derived:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.response contradicts the seeded rows for "
                f"company {company_id}: expected {derived!r}, got {expect.get('response')!r}"
            )
        provision = ctx.tools.call(
            "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
        )
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
        out["snowflake_live"] = deepcopy(provision["state"])
        out["snowflake_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_123154292(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_123154292(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    live = isinstance(seed.get("snowflake_live"), dict)
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    raw_execution: dict[str, Any] | None = None
    snowflake_cleanup: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = _snapshot(ctx, live)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx, live)
    finally:
        if live:
            # walnutiq.outputs is benchmark-owned create-or-replace live state:
            # drop it even when execution fails (cleanup principle). The API
            # responses are not persistent. Catch variants own no live state.
            snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    details["cleanup_response"] = {"snowflake_live": snowflake_cleanup}
    if live and not (snowflake_cleanup or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake cleanup failed: {snowflake_cleanup}")
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_123154292(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> str:
    if set(trigger) != {"path_params"} or not isinstance(trigger.get("path_params"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'path_params': {{...}}}}"
        )
    path_params = trigger["path_params"]
    if set(path_params) != {"company_id"}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} path_params must declare exactly company_id"
        )
    company_id = path_params["company_id"]
    if not isinstance(company_id, str) or not company_id.isdigit():
        raise RuntimeError(
            f"recipe {RECIPE_ID} company_id must be a numeric string (the bind is "
            f"`=_dp(...).to_i` against the NUMBER company_id column): {company_id!r}"
        )
    return company_id


def _require_force_shape(force: Any) -> None:
    if force is None:
        return
    if not isinstance(force, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error must be an object")
    if str(force.get("step_as") or "") != SQL_STEP_AS or not str(force.get("error") or "").strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} force_action_error must target step_as {SQL_STEP_AS!r} "
            "with an explicit error message (the only fallible step inside the TRY)"
        )


def _require_expect_shape(expect: Any, force: Any) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(EXPECT_KEYS) - OPTIONAL_EXPECT_KEYS)
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if expect.get("return_step_as") not in RETURN_STEP_AS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.return_step_as must be one of {RETURN_STEP_AS}"
        )
    catch = force is not None
    if (expect.get("return_step_as") == CATCH_RETURN_AS) != catch:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the catch return step and force_action_error must be "
            "declared together (the static SQL has no other deterministic failure)"
        )
    if str(expect.get("http_status_code")) != ("500" if catch else "200"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} http_status_code must be 500 on catch, 200 otherwise; "
            f"got {expect.get('http_status_code')!r}"
        )
    if expect.get("executed_action_count") != (1 if catch else 2):
        raise RuntimeError(
            f"recipe {RECIPE_ID} executed_action_count must be 1 on catch (the forced "
            f"error raises before the tool call), 2 otherwise; got "
            f"{expect.get('executed_action_count')!r}"
        )
    if catch:
        if "catch_message" not in expect or expect["catch_message"] != force.get("error"):
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must pin expect.catch_message equal "
                "to the forced error text"
            )
        if expect.get("response") != {"message": force.get("error")}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must pin response "
                f"{{'message': <forced error>}}; got {expect.get('response')!r}"
            )
    elif "catch_message" in expect:
        raise RuntimeError(f"recipe {RECIPE_ID} only catch variants may pin catch_message")


def _require_snowflake_section(section: Any, company_id: str) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(no CURRENT_* in the SQL -> current_time must NOT be declared)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [OUTPUTS_TABLE]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly {OUTPUTS_TABLE!r}"
        )
    spec = tables[OUTPUTS_TABLE]
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table spec must be exactly {{'columns': ..., 'rows': ...}}"
        )
    if spec["columns"] != OUTPUTS_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} walnutiq.outputs columns must be exactly {OUTPUTS_COLUMNS} "
            "(TIMESTAMP -> TIMESTAMP_NTZ keeps the created_at isoformat rendering stable)"
        )
    rows = spec["rows"]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} walnutiq.outputs must declare a non-empty rows list "
            "(the zero-row variant seeds rows for OTHER companies, never an empty table)"
        )
    matched_created: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != set(OUTPUTS_COLUMNS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} every walnutiq.outputs row must fill all declared "
                f"columns: {row!r}"
            )
        if not isinstance(row["COMPANY_ID"], int):
            raise RuntimeError(
                f"recipe {RECIPE_ID} COMPANY_ID must be an integer (NUMBER column): {row!r}"
            )
        for key in ("ID", "CONTENT", "OUTPUT_FILE_ID"):
            if not isinstance(row[key], str) or not row[key].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} row {key} must be a non-empty string: {row!r}"
                )
        if not isinstance(row["CREATED_AT"], str) or not _CREATED_AT_RE.fullmatch(row["CREATED_AT"]):
            raise RuntimeError(
                f"recipe {RECIPE_ID} CREATED_AT must be 'YYYY-MM-DD HH:MM:SS' (stable "
                f"TIMESTAMP_NTZ isoformat read-back): {row!r}"
            )
        if row["COMPANY_ID"] == int(company_id):
            matched_created.append(row["CREATED_AT"])
    if len(set(matched_created)) != len(matched_created):
        raise RuntimeError(
            f"recipe {RECIPE_ID} rows for the bound company must carry DISTINCT "
            "created_at values (ORDER BY created_at DESC LIMIT 1 needs a unique newest row)"
        )
    return [dict(row) for row in rows]


def _derive_response(rows: list[dict[str, Any]], company_id: str) -> dict[str, Any]:
    """Groundtruth of the live SELECT: the newest row for the bound company
    ('YYYY-MM-DD HH:MM:SS' strings sort chronologically), or the all-null 200
    body when no row matches (MISSING pills render null via resolve_value)."""
    matched = [row for row in rows if row["COMPANY_ID"] == int(company_id)]
    if not matched:
        return {"content": None, "created_at": None, "file_link": None, "id": None}
    top = max(matched, key=lambda row: row["CREATED_AT"])
    return {
        "content": top["CONTENT"],
        "created_at": top["CREATED_AT"].replace(" ", "T"),
        "file_link": top["OUTPUT_FILE_ID"],
        "id": top["ID"],
    }


def _snapshot(ctx: RecipeContext, live: bool) -> dict[str, Any]:
    if not live:
        return {}
    return dict(ctx.tools.call("harness.snowflake.snapshot", {}))


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
