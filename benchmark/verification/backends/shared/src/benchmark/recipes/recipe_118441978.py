from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_118441978


RECIPE_ID = "118441978"
SEED_TYPE = "clock_snowflake_relink_composite_update_variant"
TRACK = "live_snowflake_salesforce_free_workspace_relink"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "7f8a4207"
SQL_STEP_AS = "f07d9d06"
LOGGER_STEP_AS = "586bdf86"
FOREACH_AS = "15e7f8fc"
COMPOSITE_AS = "d30ad505"
SF_SOBJECT = "Workato_User__c"
MUG_TABLE = "BI_DB.MASTER_DATA.MANAGED_USER_GRANTS_COMB_D"
WORKATO_USER_TABLE = "BI_DB.SALESFORCE.WORKATO_USER"
ACCOUNT_TABLE = "BI_DB.SALESFORCE.ACCOUNT"
FEDERATED_TABLE = "BI_DB.MASTER_DATA.FEDERATED_ACCOUNTS_COMB_D"
ACCOUNTS_COMB_TABLE = "BI_DB.MASTER_DATA.ACCOUNTS_COMB_D"
CPQ_TABLE = "BI_DB.SALESFORCE.CPQ_CONTRACT"
SNOWFLAKE_TABLES = (
    MUG_TABLE,
    WORKATO_USER_TABLE,
    ACCOUNT_TABLE,
    FEDERATED_TABLE,
    ACCOUNTS_COMB_TABLE,
    CPQ_TABLE,
)
REQUIRED_COLUMNS = {
    MUG_TABLE: (
        "USER_ID", "MANAGED_USER_ID", "DATA_CENTER", "CREATED_AT",
        "GRANT_TYPE", "FEDERATED_ACCOUNT_ID", "ACCOUNT_ID",
    ),
    WORKATO_USER_TABLE: (
        "ID", "NAME", "WORKATO_USER_ID", "WORKSPACE_ID", "DATA_CENTER",
        "ACCOUNT_ID", "ACCOUNT", "EMBED_SALESFORCE_ACCOUNT_ID",
        "WORKATO_EMBED_ID", "WORKATO_PLAN", "WORKATO_USER_EMAIL",
    ),
    ACCOUNT_TABLE: ("ID", "NAME", "ACTIVE_SUBSCRIPTION", "ACCOUNT_RECORD_TYPE"),
    FEDERATED_TABLE: ("ID", "ADMIN_ID", "DATA_CENTER"),
    ACCOUNTS_COMB_TABLE: ("ID", "ADMIN_ID", "DATA_CENTER"),
    CPQ_TABLE: ("ACCOUNTID", "STATUS", "STARTDATE"),
}


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "clock", "name": "scheduled_event", "as": "7f8a4207", "skip": false, "input": {"days_of_week": "0,1,2,3,4,5,6", "time_unit": "weeks", "timezone": "America/Los_Angeles", "trigger_at": "08:42:00", "trigger_every": "1"}, "block": [{"number": 2, "keyword": "action", "provider": "snowflake", "name": "search_rows_sql", "as": "f07d9d06", "skip": false, "input": {"limit": "10000", "orderby": "account2", "sql": "WITH mug AS (\nSELECT * FROM\n(\nSELECT mug.user_id,\n       mug.managed_user_id::int AS managed_user_id,\n       mug.data_center,\n       mug.created_at,\n       a.active_subscription\n  FROM BI_DB.MASTER_DATA.MANAGED_USER_GRANTS_COMB_D mug\n INNER JOIN BI_DB.SALESFORCE.WORKATO_USER wu\n    ON mug.managed_user_id = try_to_decimal(wu.workato_user_id)\n   AND mug.data_center = wu.data_center\n INNER JOIN BI_DB.SALESFORCE.ACCOUNT a\n    ON COALESCE(wu.account_id,wu.embed_salesforce_account_id) = a.id -- Embedded empoloyees often add just as collaborators to child workspaces (and not to OEM Admin)\n   AND IFNULL(a.name,'') NOT IN ('TESTING ONLY','TESTING ONLY - Embedded','Workato') -- Exclude where customer User workspaces were granted access to workato workspaces (e.g. contests)\n WHERE mug.grant_type = 'team'\nUNION ALL\nSELECT mug.user_id,\n        fa.admin_id AS managed_user_id,\n        mug.data_center,\n        mug.created_at,\n        a.active_subscription\n  FROM BI_DB.MASTER_DATA.MANAGED_USER_GRANTS_COMB_D mug\n INNER JOIN BI_DB.MASTER_DATA.FEDERATED_ACCOUNTS_COMB_D fa\n    ON mug.federated_account_id = fa.id\n   AND mug.data_center = fa.data_center\n INNER JOIN BI_DB.SALESFORCE.WORKATO_USER wu\n    ON fa.admin_id = try_to_decimal(wu.workato_user_id)\n   AND fa.data_center = wu.data_center\n INNER JOIN BI_DB.SALESFORCE.ACCOUNT a\n    ON COALESCE(wu.account_id,wu.embed_salesforce_account_id) = a.id -- Embedded empoloyees often add just as collaborators to child workspaces (and not to OEM Admin)\n   AND IFNULL(a.name,'') NOT IN ('TESTING ONLY','TESTING ONLY - Embedded','Workato')\n WHERE mug.grant_type = 'federation_manager'\nUNION ALL\nSELECT mug.user_id,\n       oem.admin_id AS managed_user_id,\n       mug.data_center,\n       mug.created_at,\n       a.active_subscription\n  FROM BI_DB.MASTER_DATA.MANAGED_USER_GRANTS_COMB_D mug\n INNER JOIN BI_DB.MASTER_DATA.ACCOUNTS_COMB_D oem\n    ON mug.account_id = oem.id\n   AND mug.data_center = oem.data_center\n INNER JOIN BI_DB.SALESFORCE.WORKATO_USER wu\n    ON oem.admin_id = try_to_decimal(wu.workato_user_id)\n   AND oem.data_center = wu.data_center\n INNER JOIN BI_DB.SALESFORCE.ACCOUNT a\n    ON COALESCE(wu.account_id,wu.embed_salesforce_account_id) = a.id -- Embedded empoloyees often add just as collaborators to child workspaces (and not to OEM Admin)\n   AND IFNULL(a.name,'') NOT IN ('TESTING ONLY','TESTING ONLY - Embedded','Workato') \n WHERE mug.grant_type = 'customer_manager'\n)\nQUALIFY ROW_NUMBER() OVER (PARTITION BY user_id,data_center ORDER BY IFNULL(active_subscription,FALSE) DESC,created_at) = 1\n),\n\nfuture_contracts AS (\nSELECT accountid AS account_id\n  FROM BI_DB.SALESFORCE.CPQ_CONTRACT\n WHERE status = 'Inactive'\n   AND startdate > current_date\n)\n   \nSELECT mug.user_id || '-' || mug.data_center as user_id_dc,\n       mug.managed_user_id,\n       wu1.id,\n       wu1.name,\n       wu1.workato_user_email,\n       wu1.workato_plan,\n       wu1.account_id,\n       wu1.account,\n       a1.active_subscription,\n       wu2.id AS id2,\n       wu2.name AS name2,\n       wu2.workato_user_email AS workato_user_email2,\n       wu2.workato_plan AS workato_plan2,\n       COALESCE(wu2.account_id,wu2.embed_salesforce_account_id) AS account_id2, -- Embedded empoloyees often add just as collaborators to child workspaces (and not to OEM Admin)\n       a2.name AS account2,\n       wu2.workato_embed_id AS workato_embed_id2,\n       wu2.embed_salesforce_account_id AS embed_salesforce_account_id2,\n       a2.active_subscription AS active_subscription2\n  FROM mug\n INNER JOIN BI_DB.SALESFORCE.WORKATO_USER wu1\n    ON mug.user_id = try_to_decimal(wu1.workspace_id) -- Link to workspace_id so that all child environments get relinked as well\n   AND mug.data_center = wu1.data_center\n   AND wu1.workato_embed_id IS NULL  -- workspaces with and OEM Id are not \"User\" workspaces so they should be excluded\n   AND IFNULL(wu1.workato_plan,'') = 'free' -- Only consider \"free\" workspaces\n   AND IFNULL(wu1.workato_user_email,'') NOT ILIKE '%==%' -- Exclude embed child user workspaces\n   AND IFNULL(wu1.workato_user_email,'') NOT ILIKE '%workato.com%' -- Do not re-link Workato User workspaces for Workato employees\n INNER JOIN BI_DB.SALESFORCE.WORKATO_USER wu2\n    ON mug.managed_user_id = try_to_decimal(wu2.workato_user_id)\n   AND mug.data_center = wu2.data_center\n   AND IFNULL(wu1.account_id,'') != IFNULL(wu2.account_id,'') -- User Account doesn't match the first active subscription Account\n INNER JOIN BI_DB.SALESFORCE.ACCOUNT a1\n    ON wu1.account_id = a1.id\n   AND IFNULL(a1.account_record_type,'') != '012o0000000tYvxAAE' -- Exclude Partners\n   AND IFNULL(a1.active_subscription,false) != true  -- Only re-link Account if current Account link is not and active subscription\n INNER JOIN BI_DB.SALESFORCE.ACCOUNT a2\n    ON COALESCE(wu2.account_id,wu2.embed_salesforce_account_id) = a2.id -- Embedded empoloyees often add just as collaborators to child workspaces (and not to OEM Admin)\n   AND a2.active_subscription = true -- Only re-link Account if the User has access to an Account with an active subscription\n WHERE wu1.account_id NOT IN (SELECT account_id FROM future_contracts)"}, "block": []}, {"number": 3, "keyword": "action", "provider": "logger", "name": "log_message", "as": "586bdf86", "skip": false, "input": {"message": "=_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"f07d9d06\",\"path\":[\"rows\"]}').pluck(\"user_id_dc\").join(\",\")", "user_logs_enabled": "false"}, "block": []}, {"number": 4, "keyword": "foreach", "provider": "", "name": "", "as": "15e7f8fc", "skip": false, "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"f07d9d06\",\"path\":[\"rows\"]}')}"}, "repeat_mode": "batch", "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"f07d9d06\",\"path\":[\"rows\"]}')}", "block": [{"number": 5, "keyword": "action", "provider": "salesforce", "name": "composite_update_sobject", "as": "d30ad505", "skip": false, "input": {"advanced_configuration": {"allOrNone": "false"}, "batch_size": "#{_dp('{\"pill_type\":\"project_property\",\"property_name\":\"Batch Size - Salesforce Update\"}')}", "records": {"Account__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"15e7f8fc\",\"path\":[\"batch\", {\"path_element_type\": \"current_item\"}, \"account_id2\"]}')}", "Id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"15e7f8fc\",\"path\":[\"batch\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}", "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"15e7f8fc\",\"path\":[\"batch\"]}')}", "attributes": {"Workato_User__c": "Workato_User__c"}}, "sobject_name": "Workato_User__c"}, "block": []}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[int, str, str, str]] = [
    (2, SQL_STEP_AS, "snowflake", "search_rows_sql"),
    (3, LOGGER_STEP_AS, "logger", "log_message"),
    (5, COMPOSITE_AS, "salesforce", "composite_update_sobject"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_runtime.log_message",
    "salesforce.update_record",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "salesforce.update_record",
]
REQUIRED_EXPECT_KEYS = (
    "branch",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "log_message",
    "rows_meta",
)
BRANCHES = (
    "two_relinks_ordered_log",
    "zero_rows",
    "qualify_dedupe_active_wins",
    "exclusion_battery",
)
_EXPECT_ITEM_KEYS = {
    "tool", "table_id", "lookup_table_id", "match_fields", "channel",
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
}
_EXPECT_VALUE_KEYS = {
    "args_contains", "result_count", "response_contains", "result_contains",
    "created", "http_status_code", "text_fragments", "options_contains",
}
ROWS_META_KEYS = {"user_id_dc", "id", "account_id2", "account2"}
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_SF_ID_RE = re.compile(r"^[a-zA-Z0-9]{15,18}$")
_USER_ID_DC_RE = re.compile(r"^([0-9]+)-([a-z]+)$")
_ASCII_RE = re.compile(r"^[\x20-\x7e]*$")
_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:?\d{2})?$")


def validate_118441978(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    # Semantic pins over the drift-prone bits (the tree pin holds the bytes;
    # these name the trap when one changes).
    sql_node = next(node for node in _walk_nodes(raw) if str(node.get("as") or "") == SQL_STEP_AS)
    sql_input = sql_node.get("input") or {}
    sql = str(sql_input.get("sql") or "")
    if str(sql_input.get("orderby") or "") != "account2":
        raise RuntimeError(f"recipe {RECIPE_ID} connector orderby changed: {sql_input.get('orderby')!r}")
    if str(sql_input.get("limit") or "") != "10000":
        raise RuntimeError(f"recipe {RECIPE_ID} connector limit changed")
    if _has_top_level_order_by(sql):
        raise RuntimeError(
            f"recipe {RECIPE_ID} raw SQL grew a TOP-LEVEL ORDER BY -- the connector "
            "orderby-append analysis (and the ordering groundtruth) no longer holds"
        )
    if "QUALIFY ROW_NUMBER() OVER (PARTITION BY user_id,data_center ORDER BY" not in sql:
        raise RuntimeError(
            f"recipe {RECIPE_ID} QUALIFY dedupe window changed -- the "
            "active-subscription-wins groundtruth no longer holds"
        )
    if "startdate > current_date" not in sql:
        raise RuntimeError(
            f"recipe {RECIPE_ID} future_contracts arm changed -- the pinned "
            "current_time requirement must be revisited"
        )
    for table in SNOWFLAKE_TABLES:
        if table not in sql:
            raise RuntimeError(f"recipe {RECIPE_ID} SQL no longer reads {table}")
    logger_node = next(node for node in _walk_nodes(raw) if str(node.get("as") or "") == LOGGER_STEP_AS)
    message = str((logger_node.get("input") or {}).get("message") or "")
    if '.pluck("user_id_dc").join(",")' not in message:
        raise RuntimeError(f"recipe {RECIPE_ID} logger formula changed: {message!r}")
    foreach = next(node for node in _walk_nodes(raw) if str(node.get("as") or "") == FOREACH_AS)
    if foreach.get("repeat_mode") != "batch":
        raise RuntimeError(f"recipe {RECIPE_ID} foreach repeat_mode changed")
    composite = next(node for node in _walk_nodes(raw) if str(node.get("as") or "") == COMPOSITE_AS)
    records = (composite.get("input") or {}).get("records") or {}
    if sorted(records.keys()) != ["Account__c", "Id", "____source", "attributes"]:
        raise RuntimeError(f"recipe {RECIPE_ID} composite record mapping changed: {sorted(records.keys())}")
    if '"account_id2"' not in str(records.get("Account__c")) or '"id"' not in str(records.get("Id")):
        raise RuntimeError(f"recipe {RECIPE_ID} composite per-row pills changed: {records!r}")
    actions = _collect_actions(raw)
    actual = [
        (a.get("number"), str(a.get("as")), str(a.get("provider")), str(a.get("name")))
        for a in actions
    ]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        # The verbatim raw SQL rides in the validation payload so the verifier
        # can derive the exact expected args.sql (raw + connector append)
        # without duplicating 4KB of SQL in every variant input.
        "sql": sql,
        "orderby": "account2",
        "limit": "10000",
        "actions": [
            {
                "number": a.get("number"),
                "provider": a.get("provider"),
                "name": a.get("name"),
                "as": a.get("as"),
            }
            for a in actions
        ],
    }


def seed_118441978(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118441978(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (payload-less "
            f"scheduler tick; no trigger field is ever dereferenced): {trigger!r}"
        )
    expect = data.get("expect")
    _require_expect_common(expect)
    rows_meta = expect["rows_meta"]
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    needs_salesforce = bool(rows_meta)
    expected_sections = ["salesforce", "snowflake_live"] if needs_salesforce else ["snowflake_live"]
    if sorted(seed_in.keys()) != expected_sections:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must carry exactly {expected_sections} (salesforce "
            f"exactly when updates run); got {sorted(seed_in.keys())}"
        )
    _require_snowflake_section(seed_in["snowflake_live"], rows_meta)
    _require_expect_groundtruth(expect)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": trigger,
        "harness_tool_calls": [],
    }
    refs: dict[str, str] = {}
    if needs_salesforce:
        _require_salesforce_section(seed_in["salesforce"], rows_meta)
        provision = ctx.tools.call("harness.salesforce.seed_records", {"salesforce": seed_in["salesforce"]})
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
        refs = _salesforce_ref_tokens(seed_in["salesforce"], provision)
        out["salesforce_live"] = deepcopy(provision["state"])
        out["salesforce_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
        out["salesforce_ref_tokens"] = refs
    resolved_snowflake = _replace_value(deepcopy(seed_in["snowflake_live"]), refs)
    resolved_expect = _replace_value(deepcopy(expect), refs)
    _require_no_tokens(resolved_snowflake, "seed.snowflake_live")
    _require_no_tokens(resolved_expect, "expect")
    snow_provision = ctx.tools.call("harness.snowflake_live.seed_tables", {"snowflake": resolved_snowflake})
    if not snow_provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {snow_provision}")
    out["expect"] = resolved_expect
    out["snowflake_live"] = deepcopy(snow_provision["state"])
    out["snowflake_seed_snapshot"] = deepcopy(snow_provision.get("snapshot") or {})
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_118441978(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_118441978(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed carries no snowflake_live state")
    has_salesforce = isinstance(seed.get("salesforce_live"), dict)
    if bool(expect.get("rows_meta")) != has_salesforce:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed salesforce_live state must exist exactly when "
            f"rows_meta expects updates"
        )
    raw_execution: dict[str, Any] | None = None
    initial_snapshot: dict[str, Any] = {}
    final_snapshot: dict[str, Any] = {}
    snowflake_cleanup: dict[str, Any] | None = None
    salesforce_cleanup: dict[str, Any] | None = None
    try:
        initial_snapshot = _snapshot(ctx, has_salesforce)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, has_salesforce)
    finally:
        # Benchmark-owned live state is dropped even when execution fails
        # (cleanup principle): the 6 BI_DB.* tables and the seeded Salesforce
        # Account/Workato_User__c records.
        snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
        if has_salesforce:
            salesforce_cleanup = ctx.tools.call("harness.salesforce.cleanup", {})
    if not (snowflake_cleanup or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake cleanup failed: {snowflake_cleanup}")
    if has_salesforce and not (salesforce_cleanup or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce cleanup failed: {salesforce_cleanup}")
    if raw_execution is None:
        raise RuntimeError(f"recipe {RECIPE_ID} raw execution did not complete")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "expect": seed.get("expect"),
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "cleanup_response": {
                "snowflake_live": snowflake_cleanup,
                "salesforce": salesforce_cleanup,
            },
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_118441978(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_expect_common(expect: Any) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    if expect.get("branch") not in BRANCHES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch must be one of {BRANCHES}")
    rows_meta = expect.get("rows_meta")
    if not isinstance(rows_meta, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.rows_meta must be a list")
    for row in rows_meta:
        if not isinstance(row, dict) or set(row) != ROWS_META_KEYS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} rows_meta entries must carry exactly "
                f"{sorted(ROWS_META_KEYS)}: {row!r}"
            )
        if not _USER_ID_DC_RE.fullmatch(str(row["user_id_dc"])):
            raise RuntimeError(
                f"recipe {RECIPE_ID} rows_meta user_id_dc must be '<digits>-<dc>': {row!r}"
            )
    account2_values = [str(row["account2"]) for row in rows_meta]
    if account2_values != sorted(account2_values) or len(set(account2_values)) != len(account2_values):
        raise RuntimeError(
            f"recipe {RECIPE_ID} rows_meta must be sorted by DISTINCT ASCII account2 "
            f"(the appended ORDER BY account2 pins exact row order; ties would be "
            f"nondeterministic): {account2_values}"
        )
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or not items:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tool_expectations must be a non-empty list")
    for item in items:
        if not isinstance(item, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} tool expectation must be an object: {item!r}")
        unknown = sorted(set(item) - _EXPECT_ITEM_KEYS)
        if unknown:
            raise RuntimeError(f"recipe {RECIPE_ID} tool expectation has undeclared keys: {unknown}")
        if not (set(item) & _EXPECT_VALUE_KEYS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} every tool expectation must carry at least one "
                f"value-asserting key ({sorted(_EXPECT_VALUE_KEYS)}): {item!r}"
            )


def _require_expect_groundtruth(expect: dict[str, Any]) -> None:
    rows_meta = expect["rows_meta"]
    branch = expect["branch"]
    if branch == "two_relinks_ordered_log" and len(rows_meta) < 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} {branch} needs >=2 rows (the appended ORDER BY is the "
            f"observable); got {rows_meta!r}"
        )
    if branch == "zero_rows" and rows_meta:
        raise RuntimeError(f"recipe {RECIPE_ID} zero_rows must expect no rows: {rows_meta!r}")
    if branch in ("qualify_dedupe_active_wins", "exclusion_battery") and len(rows_meta) != 1:
        raise RuntimeError(
            f"recipe {RECIPE_ID} {branch} must derive exactly 1 surviving row; "
            f"got {rows_meta!r}"
        )
    log_message = ",".join(str(row["user_id_dc"]) for row in rows_meta)
    expected_tools = ["snowflake.search_rows_sql"] + (
        ["salesforce.update_record"] if rows_meta else []
    )
    expected_count = 2 + (1 if rows_meta else 0)
    checks = (
        expect.get("log_message") == log_message,
        expect.get("tools") == expected_tools,
        expect.get("executed_action_count") == expected_count,
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} {branch} expect block contradicts rows_meta "
            f"(log_message {log_message!r}, tools {expected_tools!r}, "
            f"executed_action_count {expected_count}): {expect!r}"
        )
    expected_items: list[dict[str, Any]] = [
        {
            "tool": "snowflake.search_rows_sql",
            "args_contains": {"limit": "10000"},
            "result_count": len(rows_meta),
        },
    ]
    if rows_meta:
        expected_items.append(
            {
                "tool": "salesforce.update_record",
                "args_contains": {
                    "sobject": SF_SOBJECT,
                    "records": [
                        {
                            "sobject": SF_SOBJECT,
                            "id": row["id"],
                            "fields": {"Account__c": row["account_id2"]},
                        }
                        for row in rows_meta
                    ],
                },
            }
        )
    if expect.get("tool_expectations") != expected_items:
        raise RuntimeError(
            f"recipe {RECIPE_ID} {branch} tool_expectations must pin exactly the derived "
            f"sql + one stable batch update item; expected {expected_items!r}, got "
            f"{expect.get('tool_expectations')!r}"
        )


def _require_salesforce_section(section: Any, rows_meta: list[dict[str, Any]]) -> None:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce must be an object")
    unexpected = sorted(set(section) - {"schema", "records"})
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce has unexpected keys: {unexpected}")
    schema = section.get("schema")
    if not isinstance(schema, list) or not schema:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare the {SF_SOBJECT} "
            "Account__c custom field (schema-in-seed provisioning)"
        )
    declared = {
        (str(entry.get("sobject") or ""), str(entry.get("field") or ""))
        for entry in schema
        if isinstance(entry, dict)
    }
    if (SF_SOBJECT, "Account__c") not in declared:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must include {SF_SOBJECT}.Account__c"
        )
    records = [record for record in section.get("records") or [] if isinstance(record, dict)]
    if not records:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records must not be empty")
    refs: set[str] = set()
    for record in records:
        ref = str(record.get("ref") or "").strip()
        if not ref:
            raise RuntimeError(f"recipe {RECIPE_ID} every seed.salesforce record needs a ref: {record!r}")
        if str(record.get("sobject") or "") not in {"Account", SF_SOBJECT}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seed.salesforce records must be Account or "
                f"{SF_SOBJECT}: {record!r}"
            )
        if not isinstance(record.get("fields"), dict) or not record["fields"]:
            raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce record {ref!r} is missing fields")
        refs.add(f"${ref.upper()}_ID")
    for row in rows_meta:
        for key in ("id", "account_id2"):
            if str(row[key]) not in refs:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} rows_meta.{key} {row[key]!r} must be a $REF_ID "
                    f"token of a seeded Salesforce record (live Lookup(Account) / owned "
                    f"update target); seeded refs: {sorted(refs)}"
                )


def _require_snowflake_section(section: Any, rows_meta: list[dict[str, Any]]) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["current_time", "tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'current_time', "
            f"'tables'}} (the SQL uses current_date -> a pinned time is REQUIRED)"
        )
    if not _TIME_RE.fullmatch(str(section.get("current_time") or "")):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.current_time must be an explicit "
            f"ISO timestamp; got {section.get('current_time')!r}"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted(SNOWFLAKE_TABLES):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{sorted(SNOWFLAKE_TABLES)}; got "
            f"{sorted(tables.keys()) if isinstance(tables, dict) else tables!r}"
        )
    specs: dict[str, dict[str, Any]] = {}
    for table in SNOWFLAKE_TABLES:
        spec = tables[table]
        if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {table} spec must be exactly {{'columns': ..., 'rows': ...}}"
            )
        columns = spec["columns"]
        rows = spec["rows"]
        if not isinstance(columns, dict) or not isinstance(rows, list):
            raise RuntimeError(f"recipe {RECIPE_ID} {table} columns/rows malformed")
        for required in REQUIRED_COLUMNS[table]:
            if required not in columns:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {table} must declare column {required} (the CTE "
                    f"references it; WORKATO_USER.ACCOUNT especially -- probed live "
                    f"'invalid identifier WU1.ACCOUNT' without it); got {sorted(columns)}"
                )
        for row in rows:
            if not isinstance(row, dict) or set(row) - set(columns):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {table} row carries undeclared columns: {row!r}"
                )
            for value in row.values():
                if value is None or isinstance(value, bool):
                    continue
                if isinstance(value, (int, float)):
                    continue
                if not isinstance(value, str) or not _ASCII_RE.fullmatch(value):
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} {table} values must be printable-ASCII "
                        f"strings, numbers, booleans or null: {row!r}"
                    )
        specs[table] = spec
    # NOT IN (SELECT account_id FROM future_contracts) is NULL-poisonous: a
    # NULL accountid in a matching CPQ row would empty the whole result set.
    for row in specs[CPQ_TABLE]["rows"]:
        if row.get("ACCOUNTID") in (None, ""):
            raise RuntimeError(
                f"recipe {RECIPE_ID} CPQ_CONTRACT rows must carry a non-null ACCOUNTID "
                f"(NOT IN over a NULL empties every result -- never author it): {row!r}"
            )
    # Structural consistency net between rows_meta and the seeds (the CTE
    # itself is verified LIVE; these checks catch authoring drift offline).
    wu_rows = specs[WORKATO_USER_TABLE]["rows"]
    account_rows = {str(row.get("ID")): row for row in specs[ACCOUNT_TABLE]["rows"]}
    for meta in rows_meta:
        digits, data_center = _USER_ID_DC_RE.fullmatch(str(meta["user_id_dc"])).groups()
        workspace = [
            row for row in wu_rows
            if str(row.get("WORKSPACE_ID") or "") == digits
            and str(row.get("DATA_CENTER") or "") == data_center
            and str(row.get("ID") or "") == str(meta["id"])
        ]
        if len(workspace) != 1:
            raise RuntimeError(
                f"recipe {RECIPE_ID} rows_meta {meta['user_id_dc']!r} needs exactly one "
                f"WORKATO_USER workspace row (WORKSPACE_ID={digits}, DATA_CENTER="
                f"{data_center}, ID={meta['id']}); found {len(workspace)}"
            )
        if str(workspace[0].get("WORKATO_PLAN") or "") != "free":
            raise RuntimeError(
                f"recipe {RECIPE_ID} surviving workspace {meta['user_id_dc']!r} must be "
                f"on the 'free' plan: {workspace[0]!r}"
            )
        target = account_rows.get(str(meta["account_id2"]))
        if not isinstance(target, dict) or target.get("ACTIVE_SUBSCRIPTION") is not True:
            raise RuntimeError(
                f"recipe {RECIPE_ID} rows_meta account_id2 {meta['account_id2']!r} must "
                f"be a seeded ACCOUNT row with ACTIVE_SUBSCRIPTION true (the a2 join)"
            )
        if str(target.get("NAME") or "") != str(meta["account2"]):
            raise RuntimeError(
                f"recipe {RECIPE_ID} rows_meta account2 {meta['account2']!r} must equal "
                f"the target ACCOUNT row's NAME {target.get('NAME')!r}"
            )


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
        live_id = live_ids[idx]
        if not _SF_ID_RE.fullmatch(live_id):
            raise RuntimeError(f"recipe {RECIPE_ID} provisioned record id looks invalid: {live_id!r}")
        refs[f"${str(record.get('ref')).strip().upper()}_ID"] = live_id
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


def _has_top_level_order_by(sql: str) -> bool:
    """True only for a paren-depth-0 ORDER BY, honoring single-quoted strings
    (same semantics the engine's connector-append suppression uses)."""
    text = str(sql)
    depth = 0
    quote = False
    idx = 0
    while idx < len(text):
        char = text[idx]
        if quote:
            if char == "'":
                quote = False
            idx += 1
            continue
        if char == "'":
            quote = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        elif (
            depth == 0
            and re.match(r"ORDER\s+BY\b", text[idx:], flags=re.I)
            and (idx == 0 or not (text[idx - 1].isalnum() or text[idx - 1] == "_"))
        ):
            return True
        idx += 1
    return False


def _snapshot(ctx: RecipeContext, has_salesforce: bool) -> dict[str, Any]:
    out: dict[str, Any] = {}
    out.update(ctx.tools.call("harness.snowflake.snapshot", {}))
    if has_salesforce:
        out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
    return out


def _normalize_tree(node: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "number": node.get("number"),
        "keyword": node.get("keyword"),
        "provider": node.get("provider") or "",
        "name": node.get("name") or "",
        "as": node.get("as") or "",
        "skip": bool(node.get("skip")),
    }
    if not out["skip"]:
        out["input"] = node.get("input")
    if node.get("keyword") == "foreach":
        out["repeat_mode"] = node.get("repeat_mode")
        out["source"] = node.get("source")
    if isinstance(node.get("filter"), dict):
        out["filter"] = node["filter"]
    out["block"] = [
        _normalize_tree(child) for child in node.get("block") or [] if isinstance(child, dict)
    ]
    return out


def _first_tree_mismatch(actual: Any, expected: Any, path: str = "root") -> str:
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(set(expected) | set(actual)):
            if key not in actual:
                return f"{path}.{key}: missing in raw recipe"
            if key not in expected:
                return f"{path}.{key}: unexpected in raw recipe"
            found = _first_tree_mismatch(actual[key], expected[key], f"{path}.{key}")
            if found:
                return found
        return ""
    if isinstance(expected, list) and isinstance(actual, list):
        if len(actual) != len(expected):
            return f"{path}: length {len(actual)} != {len(expected)}"
        for idx, (act, exp) in enumerate(zip(actual, expected)):
            found = _first_tree_mismatch(act, exp, f"{path}[{idx}]")
            if found:
                return found
        return ""
    if actual != expected:
        return f"{path}: {json.dumps(actual, default=str)[:200]} != {json.dumps(expected, default=str)[:200]}"
    return ""


def _walk_nodes(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        found.append(child)
        found.extend(_walk_nodes(child))
    return found


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
