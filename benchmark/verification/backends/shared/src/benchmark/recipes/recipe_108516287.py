from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_108516287


RECIPE_ID = "108516287"
SEED_TYPE = "api_platform_workato_usage_workspace_rollup_variant"
TRACK = "workato_api_platform_snowflake_workato_usage"
TRIGGER_PROVIDER = "workato_api_platform"
TRIGGER_NAME = "receive_request"
TRIGGER_AS = "458af9a1"
SEARCH_STEP_AS = "5a86b1ad"
SUCCESS_RETURN_AS = "426432f0"
CATCH_AS = "c96801ed"
CATCH_RETURN_AS = "1c0a9f98"
# The literal 3-part names the SQL references; MUST be the registered
# snowflake_live table keys so _rewrite_sql maps them onto the benchmark
# database (<SNOWFLAKE_DATABASE>.WORKATO_USAGE.RECIPE_DIM / .WORKSPACE_DIM).
RECIPE_DIM_TABLE = "product.workato_usage.recipe_dim"
WORKSPACE_DIM_TABLE = "product.workato_usage.workspace_dim"
SEED_TABLE_KEYS = sorted([RECIPE_DIM_TABLE, WORKSPACE_DIM_TABLE])
WORKSPACE_IDS_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\","
    "\"line\":\"" + TRIGGER_AS + "\",\"path\":[\"request\", \"workspace_ids\"]}')}"
)
ACCOUNT_ID_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\","
    "\"line\":\"" + TRIGGER_AS + "\",\"path\":[\"request\", \"account_id\"]}')}"
)
# Verbatim recipe SQL: BOTH request pills interpolate into the SQL TEXT
# (parameters.schema is [] — no bind parameters). workspace_ids lands RAW
# inside the IN () list; account_id lands inside single quotes.
RAW_SQL_TEMPLATE = (
    "select \nLISTAGG(distinct wd.workspace_name, ', ') workspaces,\n"
    "count_if(rd.running) running,\n"
    "count_if(rd.is_callable or rd.is_function) function_recipe,\n"
    "count_if(rd.HAS_WORKBOT) HAS_WORKBOT,\n"
    "count_if(rd.is_billable) is_billable,\n"
    "count_if(rd.uses_custom_connector) uses_custom_connector,\n"
    "count_if(rd.USES_OPA) USES_OPA,\n"
    "count_if(rd.is_workbot) is_workbot,\n"
    "count_if(rd.is_etl) is_etl,\n"
    "count_if(rd.IS_REVERSE_ETL) IS_REVERSE_ETL,\n"
    "count_if(rd.is_ai) is_ai\n"
    "from product.workato_usage.recipe_dim rd\n"
    "left join product.workato_usage.workspace_dim wd on wd.workspace_id = rd.user_id\n"
    "where rd.is_latest\nand rd.running\nand wd.is_latest\nand not wd.is_deleted\n"
    "and wd.is_paid_workspace\nand not wd.is_internal\n"
    "and wd.workspace_id in (" + WORKSPACE_IDS_PILL + ")\n"
    "and wd.sales_account_id = '" + ACCOUNT_ID_PILL + "'"
)
RAW_LIMIT = "1"
RAW_OFFSET = "0"
RECIPE_DIM_COLUMNS = {
    "recipe_id": "string",
    "user_id": "number",
    "is_latest": "boolean",
    "running": "boolean",
    "is_callable": "boolean",
    "is_function": "boolean",
    "has_workbot": "boolean",
    "is_billable": "boolean",
    "uses_custom_connector": "boolean",
    "uses_opa": "boolean",
    "is_workbot": "boolean",
    "is_etl": "boolean",
    "is_reverse_etl": "boolean",
    "is_ai": "boolean",
}
WORKSPACE_DIM_COLUMNS = {
    "workspace_id": "number",
    "workspace_name": "string",
    "is_latest": "boolean",
    "is_deleted": "boolean",
    "is_paid_workspace": "boolean",
    "is_internal": "boolean",
    "sales_account_id": "string",
}
# response key -> count_if flag, in the recipe's mapping (function_recipe is
# the only OR-composite). workspaces is handled separately (LISTAGG).
COUNT_KEYS = (
    "running",
    "function_recipe",
    "has_workbot",
    "is_billable",
    "uses_custom_connector",
    "uses_opa",
    "is_workbot",
    "is_etl",
    "is_reverse_etl",
    "is_ai",
)
WORKSPACE_IDS_RE = re.compile(r"\d+(?:\s*,\s*\d+)*")
SQL_SAFE_TEXT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._-]*")

# workato_api_platform.receive_request (as 458af9a1, request schema pins TWO
# required strings account_id + workspace_ids; BOTH are dereferenced INSIDE
# the SQL text of step 3 — parameters.schema is [], so there are NO bind
# parameters and the resolved SQL itself is variant groundtruth). Head of the
# 108516287/108333874 near-twin pair (108333874 = same as-ids, SQL minus the
# LISTAGG column + IN predicate); 108332331 shares the as-id skeleton only.
# Body = one TRY (step 2):
#   3  snowflake.search_rows_sql 5a86b1ad (LIVE): RAW_SQL_TEMPLATE with the
#      pills interpolated, limit '1' offset '0' (offset 0 is NOT appended;
#      ' limit 1' IS appended by _append_limit_offset — harmless on the
#      single aggregate row). LISTAGG(distinct wd.workspace_name, ', ')
#      + 10x count_if over recipe_dim LEFT JOIN workspace_dim (the wd.*
#      WHERE arms make the left join effectively inner). An aggregate
#      SELECT always returns EXACTLY ONE row.
#   4  workato_api_platform.return_response 426432f0 (mock, TERMINAL): 200,
#      response = OBJECT of 11 fields via rows[current_item].<col_hash>
#      pills (workspaces_4f336350, running_5dc1ba5c, ...). Full-pill fields
#      resolve NATIVELY: on matched rows count_if Decimals -> int
#      (_json_value), so the 10 counts are INTS in the response despite the
#      schema's float_conversion, and workspaces is the single matched name.
#      ZERO-MATCH SHAPE IS LIVE-PROBED (output/108516287/variant_01,
#      2026-07-08): the aggregate still returns ONE row but every count_if
#      column is NULL (NOT int 0) and LISTAGG renders '' (NOT null); the
#      typed None/'' row values pass through the single-pill template as
#      JSON null / "".
#   CATCH c96801ed (max_retry_count 0):
#   6  return_response 1c0a9f98 (TERMINAL): 500 with NO response input —
#      the adapter renders response {} (bodyless 500). No trailing stop
#      exists in this recipe (unlike the AUTOMATION_COMPASS family).
#
# Branch mapping:
# - aggregates_200: matched workspaces/recipes -> every count pinned from
#   the seed derivation below; decoys prove each WHERE arm (non-latest
#   recipe, not-running recipe, internal workspace, other-account workspace
#   inside the IN list, in-account workspace OUTSIDE the IN list, stale
#   workspace, recipe whose user_id has no workspace row).
# - zero_counts_200: near-miss decoys only -> 1 aggregate row where every
#   count_if is NULL and workspaces is '' (live-probed shape); still 2
#   actions (data-independent 200 path).
# - catch_500: seed.force_action_error on 5a86b1ad (the pill-in-SQL text has
#   no other deterministic failure) -> bodyless 500 after 1 action.
#
# DETERMINISM (triage rule): LISTAGG(distinct ...) carries NO WITHIN GROUP
# ORDER BY — a 2-name workspaces value is order-non-deterministic. The
# seeder REQUIRES all matched workspaces to share ONE workspace_name (which
# simultaneously proves DISTINCT collapses duplicates). Workspace ids must
# be unique across workspace_dim rows so the join can never fan out.
#
# Backends: Snowflake runs LIVE (harness.snowflake_live.seed_tables
# create-or-replace; dropped in the runner's finally). The API platform
# trigger/responses are deterministic Workato-internal mocks. READ-ONLY on
# Snowflake. The physical WORKATO_USAGE.RECIPE_DIM / WORKSPACE_DIM tables
# are SHARED with twin 108333874 — never run the pair's lanes concurrently.
# The SQL uses no CURRENT_DATE/TIMESTAMP: seed.snowflake_live.current_time
# is rejected.

_STRUCTURE_PINS_JSON = r"""[
 {
  "as": "458af9a1",
  "input": {
   "request": {
    "content_type": "json",
    "schema": "[{\"name\":\"account_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account ID\"},{\"name\":\"workspace_ids\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Workspace ids\"}]"
   },
   "response": {
    "content_type": "json",
    "responses": [
     {
      "body_schema": "[{\"control_type\":\"number\",\"label\":\"Running\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"running\"},{\"control_type\":\"number\",\"label\":\"Function recipe\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"function_recipe\"},{\"control_type\":\"number\",\"label\":\"Has workbot\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"has_workbot\"},{\"control_type\":\"number\",\"label\":\"Is billable\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"is_billable\"},{\"control_type\":\"number\",\"label\":\"Uses custom connector\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"uses_custom_connector\"},{\"control_type\":\"number\",\"label\":\"Uses opa\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"uses_opa\"},{\"control_type\":\"number\",\"label\":\"Is workbot\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"is_workbot\"},{\"control_type\":\"number\",\"label\":\"Is etl\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"is_etl\"},{\"control_type\":\"number\",\"label\":\"Is reverse etl\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"is_reverse_etl\"},{\"control_type\":\"number\",\"label\":\"Is ai\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"is_ai\"},{\"name\":\"workspaces\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Workspaces\"}]",
      "http_status_code": "200",
      "name": "Success"
     },
     {
      "http_status_code": "500",
      "name": "failure"
     }
    ]
   }
  },
  "keyword": "trigger",
  "name": "receive_request",
  "number": 1,
  "provider": "workato_api_platform",
  "skip": false
 },
 {
  "as": null,
  "input": {},
  "keyword": "try",
  "name": null,
  "number": 2,
  "provider": null,
  "skip": false
 },
 {
  "as": "5a86b1ad",
  "input": {
   "limit": "1",
   "offset": "0",
   "output_schema": "[{\"control_type\":\"number\",\"label\":\"Running\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"running\"},{\"control_type\":\"number\",\"label\":\"Function recipe\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"function_recipe\"},{\"control_type\":\"number\",\"label\":\"Has workbot\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"has_workbot\"},{\"control_type\":\"number\",\"label\":\"Is billable\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"is_billable\"},{\"control_type\":\"number\",\"label\":\"Uses custom connector\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"uses_custom_connector\"},{\"control_type\":\"number\",\"label\":\"Uses opa\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"uses_opa\"},{\"control_type\":\"number\",\"label\":\"Is workbot\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"is_workbot\"},{\"control_type\":\"number\",\"label\":\"Is etl\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"is_etl\"},{\"control_type\":\"number\",\"label\":\"Is reverse etl\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"is_reverse_etl\"},{\"control_type\":\"number\",\"label\":\"Is ai\",\"parse_output\":\"float_conversion\",\"type\":\"number\",\"name\":\"is_ai\"},{\"name\":\"workspaces\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Workspaces\"}]",
   "parameters": {
    "schema": "[]"
   },
   "sql": "select \nLISTAGG(distinct wd.workspace_name, ', ') workspaces,\ncount_if(rd.running) running,\ncount_if(rd.is_callable or rd.is_function) function_recipe,\ncount_if(rd.HAS_WORKBOT) HAS_WORKBOT,\ncount_if(rd.is_billable) is_billable,\ncount_if(rd.uses_custom_connector) uses_custom_connector,\ncount_if(rd.USES_OPA) USES_OPA,\ncount_if(rd.is_workbot) is_workbot,\ncount_if(rd.is_etl) is_etl,\ncount_if(rd.IS_REVERSE_ETL) IS_REVERSE_ETL,\ncount_if(rd.is_ai) is_ai\nfrom product.workato_usage.recipe_dim rd\nleft join product.workato_usage.workspace_dim wd on wd.workspace_id = rd.user_id\nwhere rd.is_latest\nand rd.running\nand wd.is_latest\nand not wd.is_deleted\nand wd.is_paid_workspace\nand not wd.is_internal\nand wd.workspace_id in (#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"458af9a1\",\"path\":[\"request\", \"workspace_ids\"]}')})\nand wd.sales_account_id = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"458af9a1\",\"path\":[\"request\", \"account_id\"]}')}'"
  },
  "keyword": "action",
  "name": "search_rows_sql",
  "number": 3,
  "provider": "snowflake",
  "skip": false
 },
 {
  "as": "426432f0",
  "input": {
   "http_status_code": "200",
   "response": {
    "function_recipe": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"function_recipe_f4c506b9\"]}')}",
    "has_workbot": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"has_workbot_ab0aa5ea\"]}')}",
    "is_ai": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"is_ai_fdb3f010\"]}')}",
    "is_billable": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"is_billable_694e1eb3\"]}')}",
    "is_etl": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"is_etl_000a6cd0\"]}')}",
    "is_reverse_etl": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"is_reverse_etl_42bef564\"]}')}",
    "is_workbot": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"is_workbot_74190b83\"]}')}",
    "running": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"running_5dc1ba5c\"]}')}",
    "uses_custom_connector": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"uses_custom_connector_59f60cba\"]}')}",
    "uses_opa": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"uses_opa_13b4c8bd\"]}')}",
    "workspaces": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5a86b1ad\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"workspaces_4f336350\"]}')}"
   }
  },
  "keyword": "action",
  "name": "return_response",
  "number": 4,
  "provider": "workato_api_platform",
  "skip": false
 },
 {
  "as": "c96801ed",
  "input": {
   "max_retry_count": "0",
   "retry_interval": "2"
  },
  "keyword": "catch",
  "name": null,
  "number": 5,
  "provider": null,
  "skip": false
 },
 {
  "as": "1c0a9f98",
  "input": {
   "http_status_code": "500"
  },
  "keyword": "action",
  "name": "return_response",
  "number": 6,
  "provider": "workato_api_platform",
  "skip": false
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = list(EXPECTED_RAW_TOOLS)
SUCCESS_TOOLS = ["snowflake.search_rows_sql", "workato_api_platform.return_response"]
CATCH_TOOLS = ["workato_api_platform.return_response"]
EXPECT_KEYS = (
    "case",
    "outcome",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "http_status_code",
    "response",
    "sql_row_count",
)
OPTIONAL_EXPECT_KEYS = {"catch_message"}
OUTCOMES = ("aggregates_200", "zero_counts_200", "catch_500")
VALUE_KEYS = (
    "args_contains",
    "result_count",
    "response_contains",
    "result_contains",
    "created",
    "http_status_code",
    "text_fragments",
    "options_contains",
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


def validate_108516287(raw: dict[str, Any]) -> dict[str, Any]:
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
    sql_pin = next(pin for pin in actual if pin["as"] == SEARCH_STEP_AS)
    if sql_pin["input"].get("sql") != RAW_SQL_TEMPLATE:
        raise RuntimeError(f"recipe {RECIPE_ID} search SQL changed: {sql_pin['input'].get('sql')!r}")
    if sql_pin["input"].get("limit") != RAW_LIMIT or sql_pin["input"].get("offset") != RAW_OFFSET:
        raise RuntimeError(f"recipe {RECIPE_ID} search limit/offset changed")
    actions = [pin for pin in actual if pin["keyword"] == "action"]
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "snowflake_tables": SEED_TABLE_KEYS,
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


def resolved_sql(trigger: dict[str, Any]) -> str:
    request = trigger.get("request") or {}
    return RAW_SQL_TEMPLATE.replace(
        WORKSPACE_IDS_PILL, str(request.get("workspace_ids"))
    ).replace(ACCOUNT_ID_PILL, str(request.get("account_id")))


def _require_trigger(trigger: Any) -> tuple[str, set[int]]:
    request = (trigger or {}).get("request") if isinstance(trigger, dict) else None
    if (
        not isinstance(trigger, dict)
        or sorted(trigger.keys()) != ["request"]
        or not isinstance(request, dict)
        or sorted(request.keys()) != ["account_id", "workspace_ids"]
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger must be exactly {{'request': {{'account_id',"
            f" 'workspace_ids'}}}} (both required by the request schema): {trigger!r}"
        )
    account_id = request["account_id"]
    workspace_ids = request["workspace_ids"]
    if not isinstance(account_id, str) or not SQL_SAFE_TEXT_RE.fullmatch(account_id):
        raise RuntimeError(
            f"recipe {RECIPE_ID} request.account_id must be a SQL-quote-safe string "
            f"(it interpolates inside single quotes in the SQL text): {account_id!r}"
        )
    if not isinstance(workspace_ids, str) or not WORKSPACE_IDS_RE.fullmatch(workspace_ids):
        raise RuntimeError(
            f"recipe {RECIPE_ID} request.workspace_ids must be a comma-separated "
            f"integer list string (it interpolates RAW into the IN () list): "
            f"{workspace_ids!r}"
        )
    return account_id, {int(part) for part in workspace_ids.split(",")}


def _require_table(name: str, spec: Any, columns: dict[str, str]) -> list[dict[str, Any]]:
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {name} spec must be exactly {{'columns': ..., 'rows': ...}}"
        )
    if spec["columns"] != columns:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {name} must declare exactly the columns {columns}"
        )
    rows = spec["rows"]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {name} rows must be NON-EMPTY — the zero branch "
            "proves the WHERE arms via near-miss decoys, never via empty tables"
        )
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(columns.keys()):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {name} row {idx} must fill exactly "
                f"{sorted(columns.keys())} (NULL booleans would silently drop join "
                f"rows); got {row!r}"
            )
        for key, kind in columns.items():
            value = row[key]
            if kind == "boolean":
                if not isinstance(value, bool):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} table {name} row {idx} column {key} must be "
                        f"a strict boolean: {value!r}"
                    )
            elif kind == "number":
                if isinstance(value, bool) or not isinstance(value, int):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} table {name} row {idx} column {key} must be "
                        f"an integer: {value!r}"
                    )
            else:
                if not isinstance(value, str) or not value.strip():
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} table {name} row {idx} column {key} must be "
                        f"a non-empty string: {value!r}"
                    )
    return rows


def _require_snowflake_section(section: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the SQL uses no CURRENT_DATE/TIMESTAMP, so current_time is not allowed)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != SEED_TABLE_KEYS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{SEED_TABLE_KEYS} (the literal 3-part SQL names)"
        )
    recipe_rows = _require_table(RECIPE_DIM_TABLE, tables[RECIPE_DIM_TABLE], RECIPE_DIM_COLUMNS)
    workspace_rows = _require_table(
        WORKSPACE_DIM_TABLE, tables[WORKSPACE_DIM_TABLE], WORKSPACE_DIM_COLUMNS
    )
    if len({row["recipe_id"] for row in recipe_rows}) != len(recipe_rows):
        raise RuntimeError(f"recipe {RECIPE_ID} recipe_dim recipe_id values must be distinct")
    if len({row["workspace_id"] for row in workspace_rows}) != len(workspace_rows):
        raise RuntimeError(
            f"recipe {RECIPE_ID} workspace_dim workspace_id values must be distinct "
            "(duplicate ids would fan out the join non-deterministically)"
        )
    return recipe_rows, workspace_rows


def _derived_response(
    recipe_rows: list[dict[str, Any]],
    workspace_rows: list[dict[str, Any]],
    account_id: str,
    workspace_ids: set[int],
) -> dict[str, Any]:
    """Derive the single live aggregate row from seed rows with exact parity:
    join on workspace_id == user_id (ids are unique, so no fan-out), apply
    every WHERE arm, then count_if per flag (Decimal -> int lands as native
    ints) and LISTAGG(distinct name) constrained to ONE distinct name."""
    by_id = {row["workspace_id"]: row for row in workspace_rows}
    matched: list[dict[str, Any]] = []
    names: set[str] = set()
    for rd in recipe_rows:
        if not (rd["is_latest"] and rd["running"]):
            continue
        wd = by_id.get(rd["user_id"])
        if wd is None:
            # LEFT JOIN miss: the wd.* WHERE arms are NULL -> row filtered.
            continue
        if not (
            wd["is_latest"]
            and not wd["is_deleted"]
            and wd["is_paid_workspace"]
            and not wd["is_internal"]
            and wd["workspace_id"] in workspace_ids
            and wd["sales_account_id"] == account_id
        ):
            continue
        matched.append(rd)
        names.add(str(wd["workspace_name"]))
    if len(names) > 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} matched workspaces must share ONE workspace_name — "
            f"LISTAGG(distinct ...) has no WITHIN GROUP ORDER BY, so a multi-name "
            f"value is not deterministic groundtruth: {sorted(names)}"
        )
    out: dict[str, Any] = {}
    if not matched:
        # LIVE-probed zero-match shape (output/108516287/variant_01,
        # 2026-07-08): every count_if over the empty aggregate input is NULL
        # (NOT int 0) and LISTAGG(distinct ...) renders '' (NOT null).
        for key in COUNT_KEYS:
            out[key] = None
        out["workspaces"] = ""
        return out
    for key in COUNT_KEYS:
        if key == "function_recipe":
            out[key] = sum(1 for rd in matched if rd["is_callable"] or rd["is_function"])
        else:
            out[key] = sum(1 for rd in matched if rd[key])
    out["workspaces"] = next(iter(names))
    return out


def _require_expect(
    expect: Any,
    force: Any,
    derived: dict[str, Any] | None,
    trigger: dict[str, Any],
) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(EXPECT_KEYS) - OPTIONAL_EXPECT_KEYS)
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    outcome = expect.get("outcome")
    if outcome not in OUTCOMES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.outcome must be one of {OUTCOMES}")
    if (outcome == "catch_500") != (force is not None):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the catch outcome and force_action_error must be "
            "declared together (the pill-in-SQL text has no other deterministic failure)"
        )
    tools = expect.get("tools")
    items = expect.get("tool_expectations")
    if not isinstance(tools, list) or not isinstance(items, list) or len(items) != len(tools):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin every expected call"
        )
    for idx, item in enumerate(items):
        if not isinstance(item, dict) or item.get("tool") != tools[idx]:
            raise RuntimeError(f"recipe {RECIPE_ID} tool_expectations[{idx}] does not match tools")
        if not any(key in item for key in VALUE_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} tool_expectations[{idx}] carries no value-asserting key"
            )
    if outcome == "catch_500":
        checks = (
            derived is None,
            expect.get("http_status_code") == "500",
            expect.get("response") == {},
            expect.get("catch_message") == (force or {}).get("error"),
            expect.get("sql_row_count") is None,
            expect.get("executed_action_count") == 1,
            tools == CATCH_TOOLS,
            items[0].get("http_status_code") == "500",
        )
        reason = (
            "catch variants pin the BODYLESS 500 (response {}), catch_message, "
            "1 action and no snowflake seed"
        )
    else:
        if derived is None:
            raise RuntimeError(f"recipe {RECIPE_ID} data variants require a snowflake_live seed")
        matched = int(derived.get("running") or 0)
        if outcome == "aggregates_200":
            if matched < 1:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} aggregates_200 requires at least one matched recipe row"
                )
            zero_keys = sorted(key for key in COUNT_KEYS if not derived[key])
            if zero_keys:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} aggregates_200 must pin every count >= 1 — only "
                    f"the all-positive and the zero-match (all-NULL counts + '' "
                    f"workspaces) shapes are live-proven; int-0 pins on a non-empty "
                    f"group are not admitted until probed: {zero_keys}"
                )
        if outcome == "zero_counts_200" and (
            any(derived[key] is not None for key in COUNT_KEYS) or derived["workspaces"] != ""
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} zero_counts_200 requires ZERO matched rows — the "
                f"LIVE zero-match shape is every count NULL and workspaces '' "
                f"(output/108516287/variant_01, 2026-07-08), NOT int 0s; derived {derived!r}"
            )
        checks = (
            expect.get("http_status_code") == "200",
            expect.get("response") == derived,
            expect.get("sql_row_count") == 1,
            expect.get("executed_action_count") == 2,
            tools == SUCCESS_TOOLS,
            "catch_message" not in expect,
            items[0].get("args_contains")
            == {
                "sql": resolved_sql(trigger),
                "limit": RAW_LIMIT,
                "offset": RAW_OFFSET,
                "parameters": {},
            },
            items[0].get("result_count") == 1,
            items[1].get("http_status_code") == "200",
            items[1].get("response_contains") == derived,
        )
        reason = (
            "data variants must pin sql_row_count 1 (the aggregate always returns one "
            "row), the EXACT pill-resolved SQL text with limit '1'/offset '0'/no bind "
            f"parameters, and the EXACT derived 11-field object (ints + single name "
            f"when matched; live NULLs + '' workspaces on zero-match) {derived!r}"
        )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with outcome "
            f"{outcome!r} ({reason}): {expect!r}"
        )


def seed_108516287(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_108516287(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    account_id, workspace_ids = _require_trigger(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    force = data.get("force_action_error")
    if force is not None:
        if not isinstance(force, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} force_action_error must be an object")
        if str(force.get("step_as") or "") != SEARCH_STEP_AS or not str(force.get("error") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} force_action_error must target step_as "
                f"{SEARCH_STEP_AS!r} with an explicit error message"
            )
        if seed_in != {}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must seed NOTHING (the forced error "
                f"fires before the snowflake adapter): {sorted(seed_in)}"
            )
        derived = None
    else:
        if sorted(seed_in.keys()) != ["snowflake_live"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} data variants must seed exactly the snowflake_live "
                f"section; got {sorted(seed_in.keys())}"
            )
        recipe_rows, workspace_rows = _require_snowflake_section(seed_in["snowflake_live"])
        derived = _derived_response(recipe_rows, workspace_rows, account_id, workspace_ids)
    _require_expect(data.get("expect"), force, derived, trigger)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": deepcopy(data["expect"]),
    }
    if force is None:
        provision = ctx.tools.call(
            "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
        )
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
        out["snowflake_live"] = deepcopy(provision["state"])
        out["snowflake_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_108516287(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_108516287(raw)
    trigger = seed.get("trigger")
    if not isinstance(trigger, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing trigger object")
    _require_trigger(trigger)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    live = isinstance(seed.get("snowflake_live"), dict)
    if not live and not isinstance(seed.get("force_action_error"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed carries neither snowflake_live state nor a "
            "forced catch error — nothing to run"
        )
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": trigger,
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
            # Required cleanup: the WORKATO_USAGE dim tables are benchmark-owned
            # create-or-replace state shared with twin 108333874 — drop them
            # whether or not the run completed. Catch variants own NO live state.
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
    result["verifier"] = verify_108516287(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


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
