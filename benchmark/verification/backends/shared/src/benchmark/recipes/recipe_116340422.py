from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_116340422


RECIPE_ID = "116340422"
SEED_TYPE = "api_platform_demoinfra_workspaces_listing_variant"
TRACK = "workato_api_platform_snowflake_demoinfra_workspaces"
TRIGGER_AS = "c9054fed"
DECLARE_AS = "c05d07c2"
SEARCH_AS = "4a921ec5"
COUNT_AS = "ac48f6d0"
RETURN_AS = "58bc5c59"
TABLE_KEY = "DEMOINFRA_WORKSPACES"

# workato_api_platform.receive_request (as c9054fed; request schema [] — the
# five OPTIONAL path_params name/sort/page/pagesize/order are the only
# trigger derefs). Linear body, terminal return:
#   2  workato_variable.declare_variable c05d07c2 (MOCK Workato-internal):
#      limit  = path_params.page || 10       (integer_conversion -> int)
#      offset = path_params.pagesize || 0    (leading-space '= _dp' form,
#                                             integer_conversion -> int)
#      order  = path_params.order || 'ASC'
#      sort   = path_params.sort || 'PRIORITY'
#      query  = name.present? ? "lower(name) like '%<name>%'" : '1=1'
#               (escaped-quote ternary; the input is NOT lowered — LIKE
#               matches the literal against lower(name), the faithful quirk)
#      NOTE the page->LIMIT / pagesize->OFFSET naming swap is the recipe's
#      own quirk, replayed verbatim.
#   3  snowflake.search_rows_sql 4a921ec5 (LIVE): SELECT id, name,
#      environment, description, priority FROM DEMOINFRA_WORKSPACES WHERE
#      #{query}; the connector's separate orderby input '#{sort} #{order}'
#      is APPENDED as ORDER BY (no top-level ORDER BY in the SQL); limit/
#      offset pills applied. Output pills are hash-suffixed
#      (id_b497e547/name_77b1dd6c/…) and resolve via the _<8hex>-suffix
#      stripping in lookup_path (re-probed 2026-07-08).
#   4  snowflake.search_rows_sql ac48f6d0 (LIVE): SELECT count(1) row_count
#      FROM DEMOINFRA_WORKSPACES WHERE #{query} — no orderby/limit/offset;
#      total row count is UNAFFECTED by pagination.
#   5  workato_api_platform.return_response 58bc5c59 (MOCK, TERMINAL): 200,
#      result = ____source over the search rows {id,name,environment,
#      description} (priority selected but not returned), total = count-rows
#      current_item row_count_8c45cb0e — current_item OUTSIDE a ____source =
#      FIRST row; the aggregate always returns exactly one row, and a
#      zero-match count resolves natively to int 0 (full-pill, no
#      falsy-render exposure; re-probed).
#
# Branch mapping: no block-level branches; the formula-level branch in query
# (name.present? LIKE vs 1=1) and the || defaults each get a variant:
# - v0 name_filter_sorted: all params -> LIKE + ORDER BY NAME DESC + params
# - v1 defaults_all: path_params {} -> 1=1 + ORDER BY PRIORITY ASC + 10/0
# - v2 zero_match: LIKE matches nothing -> result [] + total 0
# - v3 pagination_slice: page=1&pagesize=1 -> LIMIT 1 OFFSET 1 second row
# - v4 case_sensitivity_like: 'ACME' uppercase never matches lower(name) —
#   total 0 while the table is non-empty (proves the recipe does NOT lower
#   the input)
#
# Backends: snowflake LIVE (bare 1-part DEMOINFRA_WORKSPACES -> BENCH_DB.
# <env schema>; create-or-replace seed, dropped in the runner's finally,
# fail-fast; READ-ONLY during the run — snapshot equality pinned). API
# platform trigger + return_response are mocks (Workato-internal). The
# %-literals in LIKE survive the bind-less path (_bind_sql doubles,
# _executable_sql un-doubles; triage live probe + offline re-probe).
TABLE_COLUMNS = {
    "id": "number",
    "name": "string",
    "environment": "string",
    "description": "string",
    "priority": "string",
}
SELECT_SQL = (
    "SELECT id, name, environment, description, priority\n"
    "FROM DEMOINFRA_WORKSPACES\nWHERE {query}"
)
COUNT_SQL = "SELECT count(1) row_count\nFROM DEMOINFRA_WORKSPACES\nWHERE {query}"
PATH_PARAM_KEYS = ("name", "sort", "page", "pagesize", "order")
SORT_COLUMNS = ("ID", "NAME", "ENVIRONMENT", "DESCRIPTION", "PRIORITY")
ORDERS = ("ASC", "DESC")
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "snowflake.search_rows_sql",
    "workato_api_platform.return_response",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_api_platform.return_response",
]
EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "trace_tools",
    "declared",
    "http_status_code",
    "response",
)
MAX_ROWS = 20
_SAFE_TEXT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 _.-]*")

_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "c9054fed",
  "provider": "workato_api_platform",
  "name": "receive_request",
  "skip": false,
  "input": {
   "request": {
    "content_type": "json",
    "path_params": "[{\"control_type\":\"text\",\"label\":\"Name\",\"name\":\"name\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Sort\",\"name\":\"sort\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"integer\",\"label\":\"Page\",\"parse_output\":\"integer_conversion\",\"name\":\"page\",\"type\":\"integer\",\"optional\":true},{\"control_type\":\"integer\",\"label\":\"Offset\",\"parse_output\":\"integer_conversion\",\"name\":\"pagesize\",\"type\":\"integer\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"Order\",\"name\":\"order\",\"type\":\"string\",\"optional\":true}]",
    "schema": "[]"
   },
   "response": {
    "content_type": "json",
    "headers": "[]",
    "responses": [
     {
      "body_schema": "[{\"name\":\"result\",\"type\":\"array\",\"of\":\"object\",\"label\":\"Data\",\"properties\":[{\"control_type\":\"integer\",\"label\":\"ID\",\"parse_output\":\"integer_conversion\",\"type\":\"integer\",\"name\":\"id\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Name\",\"type\":\"string\",\"name\":\"name\"},{\"control_type\":\"text\",\"label\":\"Environment\",\"type\":\"string\",\"name\":\"environment\"},{\"control_type\":\"text\",\"label\":\"Description\",\"type\":\"string\",\"name\":\"description\",\"optional\":true}]},{\"control_type\":\"integer\",\"label\":\"Total\",\"parse_output\":\"integer_conversion\",\"name\":\"total\",\"type\":\"integer\",\"optional\":false}]",
      "http_status_code": "200",
      "name": "Ok - List of Workspaces "
     }
    ]
   }
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "c05d07c2",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "limit": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"c9054fed\",\"path\":[\"path_params\",\"page\"]}') || 10",
     "offset": "= _dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"c9054fed\",\"path\":[\"path_params\",\"pagesize\"]}') || 0",
     "order": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"c9054fed\",\"path\":[\"path_params\",\"order\"]}') || \"ASC\"",
     "query": "=(_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"c9054fed\",\"path\":[\"path_params\",\"name\"]}').present? ? 'lower(name) like \\'%' + _dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"c9054fed\",\"path\":[\"path_params\",\"name\"]}') + '%\\'' : '1=1')",
     "sort": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_api_platform\",\"line\":\"c9054fed\",\"path\":[\"path_params\",\"sort\"]}') || \"PRIORITY\""
    },
    "schema": "[{\"control_type\":\"text\",\"label\":\"query\",\"name\":\"query\",\"type\":\"string\",\"optional\":true,\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"integer\",\"label\":\"limit\",\"parse_output\":\"integer_conversion\",\"name\":\"limit\",\"type\":\"integer\",\"optional\":true,\"details\":{\"real_name\":\"limit\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"text\",\"label\":\"offset\",\"parse_output\":\"integer_conversion\",\"name\":\"offset\",\"type\":\"integer\",\"optional\":true,\"details\":{\"real_name\":\"offset\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"text\",\"label\":\"sort\",\"name\":\"sort\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"sort\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]},{\"control_type\":\"text\",\"label\":\"order\",\"name\":\"order\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"order\"},\"hint\":\"Defaults to nil if not supplied.\",\"sticky\":true,\"parent\":[\"variables\",\"data\"]}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "4a921ec5",
  "provider": "snowflake",
  "name": "search_rows_sql",
  "skip": false,
  "input": {
   "limit": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c05d07c2\",\"path\":[\"limit\"]}')}",
   "offset": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c05d07c2\",\"path\":[\"offset\"]}')}",
   "orderby": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c05d07c2\",\"path\":[\"sort\"]}')} #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c05d07c2\",\"path\":[\"order\"]}')}",
   "output_schema": "[{\"name\":\"id\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\"},{\"name\":\"name\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"environment\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\"},{\"name\":\"description\",\"type\":\"string\",\"optional\":true,\"control_type\":\"text\"},{\"name\":\"priority\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Priority\"}]",
   "sql": "SELECT id, name, environment, description, priority\nFROM DEMOINFRA_WORKSPACES\nWHERE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c05d07c2\",\"path\":[\"query\"]}')}"
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "ac48f6d0",
  "provider": "snowflake",
  "name": "search_rows_sql",
  "skip": false,
  "input": {
   "output_schema": "[{\"name\":\"row_count\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\"}]",
   "sql": "SELECT count(1) row_count\nFROM DEMOINFRA_WORKSPACES\nWHERE #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c05d07c2\",\"path\":[\"query\"]}')}"
  }
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "58bc5c59",
  "provider": "workato_api_platform",
  "name": "return_response",
  "skip": false,
  "input": {
   "http_status_code": "200",
   "response": {
    "result": {
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"4a921ec5\",\"path\":[\"rows\"]}')}",
     "description": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"4a921ec5\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"description_58741ffa\"]}')}",
     "environment": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"4a921ec5\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"environment_3882715b\"]}')}",
     "id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"4a921ec5\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"id_b497e547\"]}')}",
     "name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"4a921ec5\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"name_77b1dd6c\"]}')}"
    },
    "total": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"ac48f6d0\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"row_count_8c45cb0e\"]}')}"
   }
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)


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


def validate_116340422(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
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
        "trigger_provider": "workato_api_platform",
        "trigger_name": "receive_request",
        "snowflake_table": TABLE_KEY,
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


def _require_path_params(trigger: dict[str, Any]) -> dict[str, str]:
    if sorted(trigger.keys()) != ["path_params"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{'path_params': ...}} "
            f"(request schema is [] — nothing else is dereferenced): {trigger!r}"
        )
    path_params = trigger["path_params"]
    if not isinstance(path_params, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} path_params must be an object")
    unexpected = sorted(set(path_params) - set(PATH_PARAM_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} path_params has undeclared keys: {unexpected}")
    out: dict[str, str] = {}
    for key, value in path_params.items():
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} path_params.{key} must be a non-empty string "
                "(URL path params arrive as strings; omit absent params entirely — "
                "the || defaults are a reachable branch, not an empty-string branch)"
            )
        out[key] = value
    if "page" in out and not out["page"].isdigit():
        raise RuntimeError(f"recipe {RECIPE_ID} path_params.page must be digits: {out['page']!r}")
    if "pagesize" in out and not out["pagesize"].isdigit():
        raise RuntimeError(f"recipe {RECIPE_ID} path_params.pagesize must be digits: {out['pagesize']!r}")
    if "sort" in out and out["sort"] not in SORT_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} path_params.sort must be a physical column of "
            f"{SORT_COLUMNS}: {out['sort']!r}"
        )
    if "order" in out and out["order"] not in ORDERS:
        raise RuntimeError(f"recipe {RECIPE_ID} path_params.order must be ASC or DESC: {out['order']!r}")
    if "name" in out and not _SAFE_TEXT_RE.fullmatch(out["name"]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} path_params.name must stay in the plain-text alphabet "
            f"(it is spliced into a quoted LIKE literal): {out['name']!r}"
        )
    return out


def _require_snowflake_seed(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}}"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [TABLE_KEY]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} snowflake_live.tables must declare exactly "
            f"{TABLE_KEY!r} (the recipe's bare 1-part name)"
        )
    spec = tables[TABLE_KEY]
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table spec must be exactly {{'columns': ..., 'rows': ...}}"
        )
    if spec["columns"] != TABLE_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table must declare exactly the columns {TABLE_COLUMNS!r}"
        )
    rows = spec["rows"]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires a NON-EMPTY table (zero-result branches are "
            "driven by non-matching filters, never by an empty table)"
        )
    if len(rows) > MAX_ROWS:
        raise RuntimeError(f"recipe {RECIPE_ID} at most {MAX_ROWS} table rows")
    ids: set[int] = set()
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(TABLE_COLUMNS.keys()):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} must fill exactly "
                f"{sorted(TABLE_COLUMNS.keys())}"
            )
        if isinstance(row["id"], bool) or not isinstance(row["id"], int):
            raise RuntimeError(f"recipe {RECIPE_ID} row {idx} id must be an integer")
        ids.add(row["id"])
        for key in ("name", "environment", "description", "priority"):
            value = row[key]
            if not isinstance(value, str) or not value.strip() or not _SAFE_TEXT_RE.fullmatch(value):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} row {idx} {key} must be a non-empty plain-text "
                    f"string (deterministic ASCII ordering): {value!r}"
                )
    if len(ids) != len(rows):
        raise RuntimeError(f"recipe {RECIPE_ID} id values must be distinct")
    return rows


def derive_116340422(
    path_params: dict[str, str],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Mirror the declare-step defaulting + the live SQL over the seeded
    table with exact parity (re-probed offline 2026-07-08; v0/v1 branches
    additionally live-verified by triage)."""
    name = path_params.get("name")
    declared: dict[str, Any] = {
        "limit": int(path_params["page"]) if "page" in path_params else 10,
        "offset": int(path_params["pagesize"]) if "pagesize" in path_params else 0,
        "order": path_params.get("order") or "ASC",
        "sort": path_params.get("sort") or "PRIORITY",
        "query": f"lower(name) like '%{name}%'" if name else "1=1",
    }
    if re.search(r"\b(limit|offset)\b|\border\s+by\b", declared["query"], flags=re.I):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the WHERE interpolation must not contain limit/offset/"
            f"order-by words (they would confuse the connector's append guards): "
            f"{declared['query']!r}"
        )
    matched = [
        row for row in rows
        if name is None or name in str(row["name"]).lower()
    ]
    sort_field = declared["sort"].lower()
    sort_values = [row[sort_field] for row in matched]
    if len(set(sort_values)) != len(sort_values):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the effective sort column {declared['sort']!r} must be "
            f"distinct across matched rows (ORDER BY must be a total order): {sort_values!r}"
        )
    ordered = sorted(matched, key=lambda row: row[sort_field], reverse=declared["order"] == "DESC")
    sliced = ordered[declared["offset"]:declared["offset"] + declared["limit"]]
    return {
        "declared": declared,
        "select_sql": SELECT_SQL.format(query=declared["query"])
        + f" ORDER BY {declared['sort']} {declared['order']}",
        "count_sql": COUNT_SQL.format(query=declared["query"]),
        "result": [
            {
                "id": row["id"],
                "name": row["name"],
                "environment": row["environment"],
                "description": row["description"],
            }
            for row in sliced
        ],
        "total": len(matched),
    }


def _require_expect(expect: Any, derived: dict[str, Any]) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    response = {"result": derived["result"], "total": derived["total"]}
    checks = (
        expect.get("executed_action_count") == 4,
        expect.get("trace_tools")
        == [
            "workato_runtime.declare_variable",
            "snowflake.search_rows_sql",
            "snowflake.search_rows_sql",
            "workato_api_platform.return_response",
        ],
        expect.get("tools")
        == [
            "snowflake.search_rows_sql",
            "snowflake.search_rows_sql",
            "workato_api_platform.return_response",
        ],
        expect.get("declared") == derived["declared"],
        expect.get("http_status_code") == "200",
        expect.get("response") == response,
        expect.get("tool_expectations")
        == [
            {
                "tool": "snowflake.search_rows_sql",
                "args_contains": {
                    "sql": derived["select_sql"],
                    "limit": derived["declared"]["limit"],
                    "offset": derived["declared"]["offset"],
                },
                "result_count": len(derived["result"]),
            },
            {
                "tool": "snowflake.search_rows_sql",
                "args_contains": {"sql": derived["count_sql"]},
                "result_count": 1,
            },
            {
                "tool": "workato_api_platform.return_response",
                "http_status_code": "200",
                "response_contains": response,
            },
        ],
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect block is inconsistent with the derived ground "
            f"truth {derived!r}: {expect!r}"
        )


def seed_116340422(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_116340422(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    path_params = _require_path_params(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must carry exactly the snowflake_live section; "
            f"got {sorted(seed_in.keys()) if isinstance(seed_in, dict) else seed_in!r}"
        )
    rows = _require_snowflake_seed(seed_in["snowflake_live"])
    derived = derive_116340422(path_params, rows)
    _require_expect(data.get("expect"), derived)
    provision = ctx.tools.call(
        "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "expect": deepcopy(data["expect"]),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_116340422(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_116340422(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
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
        details["initial_snapshot"] = dict(ctx.tools.call("harness.snowflake.snapshot", {}))
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = dict(ctx.tools.call("harness.snowflake.snapshot", {}))
    finally:
        # Required cleanup: DEMOINFRA_WORKSPACES is benchmark-owned
        # create-or-replace state — drop it whether or not the run completed.
        snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    details["cleanup_response"] = {"snowflake_live": snowflake_cleanup}
    if not (snowflake_cleanup or {}).get("ok", False):
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
    result["verifier"] = verify_116340422(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
