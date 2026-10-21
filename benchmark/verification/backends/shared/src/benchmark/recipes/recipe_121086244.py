from __future__ import annotations

import datetime
import json
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_121086244


RECIPE_ID = "121086244"
SEED_TYPE = "netsuite_open_invoices_dbtable_sync_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "clock"
TRIGGER_NAME = "scheduled_event"
TRIGGER_AS = "4e415de5"
SEARCH_STEP_AS = "fe9c844d"
DECLARE_STEP_AS = "1ea22b2c"
FOREACH_STEP_AS = "833485bd"
UPSERT_STEP_AS = "33761e42"
UPDATE_VAR_STEP_AS = "e2b913ff"
DB_TABLE_ID = "1670"
PRIMARY_FIELD_DASH = "1e5fd270-2211-4c58-8dfa-95b6ee3b7b9c"
PRIMARY_FIELD = "1e5fd270_2211_4c58_8dfa_95b6ee3b7b9c"
PROJECT_PROPERTY = "Salesforce Environment"
# Registered snowflake_live keys. SALESFORCE."ACCOUNT" MUST keep its quotes:
# _rewrite_sql matches the literal SQL text and the unquoted key does NOT
# match the quoted reference (probe-verified on this tree).
INVOICE_TABLE = "NETSUITE.FLAT_INVOICE"
CUSTOMER_TABLE = "NETSUITE.FLAT_CUSTOMER"
CURRENCY_TABLE = "NETSUITE.CURRENCY"
ACCOUNT_TABLE = 'SALESFORCE."ACCOUNT"'
INVOICE_COLUMNS = {
    "internal_id": "string",
    "invoice_number": "string",
    "invoice_date": "date",
    "due_date": "date",
    "payment_term_name": "string",
    "subtotal": "float",
    "tax_total": "float",
    "status": "string",
    "amount_remaining": "float",
    "salesforce_record_id": "string",
    "customer_id": "string",
    "customer_name": "string",
    "currency_id": "string",
}
CUSTOMER_COLUMNS = {
    "internal_id": "string",
    "company_name": "string",
    "salesforce_account_id": "string",
}
CURRENCY_COLUMNS = {"internal_id": "string", "iso_code": "string"}
ACCOUNT_COLUMNS = {
    "id": "string",
    "ownerid": "string",
    "current_arr__c": "float",
    "active_subscription__c": "boolean",
}
# Upsert field map: live search row key (lowercase alias) -> record field id.
# 'ad862ef9_...' (Churn Oppty ID) is '=skip' in the raw recipe -> the SKIP
# sentinel drops it from resolved_parameters (never reaches args or table).
FIELD_MAP = {
    "past_due": "028d15b9_ac99_401c_b25f_c44a1ce7c5db",
    "current_arr": "0be8c260_33ba_4646_862c_ec74b765350a",
    "active": "12a1b031_46a2_493f_b19f_51afdab5dd11",
    "salesforce_invoice_id": "144af657_99db_483a_9ed8_a1324849d522",
    "invoice_id": PRIMARY_FIELD,
    "account_owner": "26fb5415_2534_4707_b26f_a0435b730382",
    "customer_id": "3faa69d3_6a7e_4d7c_aced_a1ba0b0442fe",
    "salesforce_account_id": "595fbc67_aef7_407b_813f_dd5b723d88cd",
    "payment_terms": "6044c826_e8b1_4524_b299_5d5d9c63a5a1",
    "amount": "634d81b9_6dfe_4fc8_a02c_78c49ca13b0f",
    "invoice_no": "665410c4_9b6f_46fe_93cd_8253dbcd3308",
    "balance": "6b5097f5_ac84_4c8d_8c21_654da728eafb",
    "invoice_date": "7d01c55a_176b_47dc_ad8c_b06899074107",
    "currency": "a1027508_c1d7_437b_9dd7_208f6dfa3ec3",
    "subtotal": "eef0c324_141b_46ad_a5aa_dd09b57e2ecd",
    "invoice_due_date": "f9a16194_15bd_4f03_a294_678f8c953df9",
}
MONEY_COLUMNS = ("subtotal", "tax_total", "amount_remaining")

# clock.scheduled_event (as 4e415de5, daily 06:00) -- payload-less trigger
# (trigger_input must be exactly {}); determinism comes from
# seed.snowflake_live.current_time (CURRENT_DATE() rewrite, fail-fast when
# missing). Body:
#   2  snowflake.search_rows_sql fe9c844d (LIVE, limit 50000): open-invoice
#      SQL -- DATEDIFF(DAYS, DUE_DATE, CURRENT_DATE()) PAST_DUE,
#      (SUBTOTAL+IFNULL(TAX_TOTAL,0))::FLOAT AMOUNT, CASE 'Paid In Full'
#      IS_PAID, two CONCAT urls rendering the 'Salesforce Environment'
#      project_property pill (seed.project_properties, fail-fast when
#      missing), JOIN FLAT_CUSTOMER (COMPANY_NAME NOT LIKE 'I/C%'), JOIN
#      CURRENCY, LEFT JOIN SALESFORCE."ACCOUNT"; WHERE AMOUNT_REMAINING > 0
#      AND IS_PAID = FALSE AND (ACTIVE = TRUE OR IS NULL) AND PAST_DUE IS
#      NOT NULL AND STATUS NOT IN ('Pending Approval')
#   3  workato_variable.declare_variable 1ea22b2c (mock): new_records
#      integer '0' -> coerced int 0 (schema integer_conversion)
#   FOREACH 833485bd over rows:
#     5  workato_db_table.upsert_record 33761e42 (mock table 1670, primary
#        NetSuite Invoice ID dash-form) -- 16 mapped foreach fields, Churn
#        Oppty ID '=skip' dropped
#     IF 6 (33761e42.created is_true):
#       7  workato_variable.update_variables e2b913ff: new_records =
#          =_dp(1ea22b2c.new_records) + 1 (declared-int coercion)
#
# Backends: Snowflake runs LIVE (create-or-replace seeds + drop in the
# runner's finally; READ-ONLY -- snapshot equality pinned). workato_db_table
# 1670 and workato_variable are Workato-internal mocks.
#
# GROUNDTRUTH DISCIPLINE:
# - money columns (subtotal/tax_total/amount_remaining/current_arr__c) are
#   FLOAT seeds on .25 quarters: NUMBER(38,0) would silently round
#   (triage-probed 100.5 -> 101) and quarter fractions keep Python-side
#   amount arithmetic binary-exact.
# - the SELECT has NO ORDER BY: live row order across >1 qualifying invoice
#   is unspecified. expect.upserts is keyed by invoice id (order-free), the
#   registry tool-name sequence is order-invariant by construction (variants
#   never mix created:true/false pinning at a trace index), and
#   final_table_rows are compared as a canonical multiset.
# - the seeder REPLICATES the WHERE clause over the seeded tables and
#   fail-fasts unless expect.sql_row_count/new_records_final/upserts match
#   the recomputation exactly.

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "clock", "name": "scheduled_event", "as": "4e415de5", "skip": false, "input": {"time_unit": "days", "trigger_at": "06:00:00", "trigger_every": "1"}, "block": [{"number": 2, "keyword": "action", "provider": "snowflake", "name": "search_rows_sql", "as": "fe9c844d", "skip": false, "input": {"limit": "50000", "output_schema": "[{\"control_type\":\"integer\",\"label\":\"PAST DUE\",\"parse_output\":\"integer_conversion\",\"name\":\"PAST_DUE\",\"type\":\"integer\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"INVOICE ID\",\"name\":\"INVOICE_ID\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"INVOICE NO\",\"name\":\"INVOICE_NO\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"date\",\"label\":\"INVOICE DATE\",\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\",\"name\":\"INVOICE_DATE\",\"type\":\"date\",\"optional\":false},{\"control_type\":\"date\",\"label\":\"INVOICE DUE DATE\",\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\",\"name\":\"INVOICE_DUE_DATE\",\"type\":\"date\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"PAYMENT TERMS\",\"name\":\"PAYMENT_TERMS\",\"type\":\"string\",\"optional\":false},{\"name\":\"CURRENCY\",\"type\":\"string\",\"optional\":false,\"label\":\"CURRENCY\",\"control_type\":\"text\"},{\"control_type\":\"number\",\"label\":\"SUBTOTAL\",\"parse_output\":\"float_conversion\",\"name\":\"SUBTOTAL\",\"type\":\"number\",\"optional\":false},{\"control_type\":\"number\",\"label\":\"AMOUNT\",\"parse_output\":\"float_conversion\",\"name\":\"AMOUNT\",\"type\":\"number\",\"optional\":false},{\"control_type\":\"checkbox\",\"label\":\"IS PAID\",\"render_input\":{},\"parse_output\":{},\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"IS PAID\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"IS_PAID\",\"type\":\"boolean\",\"optional\":false},\"name\":\"IS_PAID\",\"type\":\"boolean\",\"optional\":false},{\"control_type\":\"number\",\"label\":\"BALANCE\",\"parse_output\":\"float_conversion\",\"name\":\"BALANCE\",\"type\":\"number\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"SALESFORCE INVOICE ID\",\"name\":\"SALESFORCE_INVOICE_ID\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"SALESFORCE INVOICE URL\",\"name\":\"SALESFORCE_INVOICE_URL\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"text\",\"label\":\"CUSTOMER ID\",\"name\":\"CUSTOMER_ID\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"CUSTOMER NAME\",\"name\":\"CUSTOMER_NAME\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"SALESFORCE ACCOUNT ID\",\"name\":\"SALESFORCE_ACCOUNT_ID\",\"type\":\"string\",\"optional\":true},{\"name\":\"ACCOUNT_OWNER\",\"type\":\"string\",\"optional\":true,\"label\":\"ACCOUNT_OWNER\",\"control_type\":\"text\"},{\"control_type\":\"text\",\"label\":\"SALESFORCE ACCOUNT URL\",\"name\":\"SALESFORCE_ACCOUNT_URL\",\"type\":\"string\",\"optional\":true},{\"control_type\":\"number\",\"label\":\"CURRENT ARR\",\"parse_output\":\"float_conversion\",\"name\":\"CURRENT_ARR\",\"type\":\"number\",\"optional\":true},{\"name\":\"ACTIVE\",\"type\":\"boolean\",\"optional\":true,\"label\":\"ACTIVE\",\"control_type\":\"checkbox\",\"render_input\":{},\"parse_output\":{},\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"ACTIVE\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"ACTIVE\",\"type\":\"boolean\",\"optional\":true}}]", "sql": "SELECT\nDATEDIFF(DAYS, DUE_DATE, CURRENT_DATE()) AS PAST_DUE,\nI.INTERNAL_ID AS INVOICE_ID,\nI.INVOICE_NUMBER AS INVOICE_NO,\nI.INVOICE_DATE::DATE AS INVOICE_DATE,\nI.DUE_DATE::DATE AS INVOICE_DUE_DATE,\nI.PAYMENT_TERM_NAME AS PAYMENT_TERMS,\nCC.ISO_CODE AS CURRENCY,\nI.SUBTOTAL,\n(I.SUBTOTAL + IFNULL(I.TAX_TOTAL, 0))::FLOAT AS AMOUNT,\nCASE\nWHEN I.STATUS = 'Paid In Full'\nTHEN TRUE\nELSE FALSE\nEND AS IS_PAID,\nI.AMOUNT_REMAINING AS BALANCE,\nI.SALESFORCE_RECORD_ID AS SALESFORCE_INVOICE_ID,\nCONCAT('https://#{_dp('{\"pill_type\":\"project_property\",\"property_name\":\"Salesforce Environment\"}')}.lightning.force.com/lightning/r/NetSuite_Invoice__c/', I.SALESFORCE_RECORD_ID, '/view') AS SALESFORCE_INVOICE_URL,\nI.CUSTOMER_ID,\nI.CUSTOMER_NAME,\nC.SALESFORCE_ACCOUNT_ID,\nA.OwnerId as ACCOUNT_OWNER,\nCONCAT('https://#{_dp('{\"pill_type\":\"project_property\",\"property_name\":\"Salesforce Environment\"}')}.lightning.force.com/lightning/r/Account/', C.SALESFORCE_ACCOUNT_ID, '/view') AS SALESFORCE_ACCOUNT_URL,\nA.CURRENT_ARR__C AS CURRENT_ARR,\nA.ACTIVE_SUBSCRIPTION__C AS ACTIVE\n\nFROM NETSUITE.FLAT_INVOICE I\nJOIN NETSUITE.FLAT_CUSTOMER C\nON CUSTOMER_ID = C.INTERNAL_ID\nAND C.COMPANY_NAME NOT LIKE 'I/C%'\n\nJOIN NETSUITE.CURRENCY CC\nON I.CURRENCY_ID = CC.INTERNAL_ID\n\nLEFT JOIN SALESFORCE.\"ACCOUNT\" A\nON C.SALESFORCE_ACCOUNT_ID = A.ID\n\nWHERE I.AMOUNT_REMAINING > 0\nAND IS_PAID = FALSE\nAND (A.ACTIVE_SUBSCRIPTION__C = TRUE OR A.ACTIVE_SUBSCRIPTION__C IS NULL)\nAND PAST_DUE IS NOT NULL\nAND I.STATUS NOT IN ('Pending Approval')"}, "block": []}, {"number": 3, "keyword": "action", "provider": "workato_variable", "name": "declare_variable", "as": "1ea22b2c", "skip": false, "input": {"variables": {"data": {"new_records": "0"}, "schema": "[{\"control_type\":\"integer\",\"label\":\"New Records Count\",\"parse_output\":\"integer_conversion\",\"name\":\"new_records\",\"type\":\"integer\",\"optional\":true}]"}}, "block": []}, {"number": 4, "keyword": "foreach", "provider": "", "name": "", "as": "833485bd", "skip": false, "input": {"source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"fe9c844d\",\"path\":[\"rows\"]}')}"}, "repeat_mode": "simple", "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"fe9c844d\",\"path\":[\"rows\"]}')}", "block": [{"number": 5, "keyword": "action", "provider": "workato_db_table", "name": "upsert_record", "as": "33761e42", "skip": false, "input": {"parameters": {"028d15b9_ac99_401c_b25f_c44a1ce7c5db": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"833485bd\",\"path\":[\"past_due\"]}')}", "0be8c260_33ba_4646_862c_ec74b765350a": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"833485bd\",\"path\":[\"current_arr\"]}')}", "12a1b031_46a2_493f_b19f_51afdab5dd11": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"833485bd\",\"path\":[\"active\"]}')}", "144af657_99db_483a_9ed8_a1324849d522": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"833485bd\",\"path\":[\"salesforce_invoice_id\"]}')}", "1e5fd270_2211_4c58_8dfa_95b6ee3b7b9c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"833485bd\",\"path\":[\"invoice_id\"]}')}", "26fb5415_2534_4707_b26f_a0435b730382": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"833485bd\",\"path\":[\"account_owner\"]}')}", "3faa69d3_6a7e_4d7c_aced_a1ba0b0442fe": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"833485bd\",\"path\":[\"customer_id\"]}')}", "595fbc67_aef7_407b_813f_dd5b723d88cd": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"833485bd\",\"path\":[\"salesforce_account_id\"]}')}", "6044c826_e8b1_4524_b299_5d5d9c63a5a1": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"833485bd\",\"path\":[\"payment_terms\"]}')}", "634d81b9_6dfe_4fc8_a02c_78c49ca13b0f": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"833485bd\",\"path\":[\"amount\"]}')}", "665410c4_9b6f_46fe_93cd_8253dbcd3308": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"833485bd\",\"path\":[\"invoice_no\"]}')}", "6b5097f5_ac84_4c8d_8c21_654da728eafb": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"833485bd\",\"path\":[\"balance\"]}')}", "7d01c55a_176b_47dc_ad8c_b06899074107": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"833485bd\",\"path\":[\"invoice_date\"]}')}", "a1027508_c1d7_437b_9dd7_208f6dfa3ec3": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"833485bd\",\"path\":[\"currency\"]}')}", "ad862ef9_2e1e_462e_ab20_c149ce29997f": "=skip", "eef0c324_141b_46ad_a5aa_dd09b57e2ecd": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"833485bd\",\"path\":[\"subtotal\"]}')}", "f9a16194_15bd_4f03_a294_678f8c953df9": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"833485bd\",\"path\":[\"invoice_due_date\"]}')}"}, "primary_field_id": "1e5fd270-2211-4c58-8dfa-95b6ee3b7b9c", "table_id": "1670"}, "block": []}, {"number": 6, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_db_table\",\"line\":\"33761e42\",\"path\":[\"created\"]}')}", "operand": "is_true", "rhs": ""}], "operand": "and", "type": "compound"}, "block": [{"number": 7, "keyword": "action", "provider": "workato_variable", "name": "update_variables", "as": "e2b913ff", "skip": false, "input": {"name": "d6f8e401-810a-4ea7-9e29-2aa5e8a4758a:1ea22b2c:new_records", "new_records": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"1ea22b2c\",\"path\":[\"new_records\"]}') + 1"}, "block": []}]}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (SEARCH_STEP_AS, "snowflake", "search_rows_sql"),
    (DECLARE_STEP_AS, "workato_variable", "declare_variable"),
    (UPSERT_STEP_AS, "workato_db_table", "upsert_record"),
    (UPDATE_VAR_STEP_AS, "workato_variable", "update_variables"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_runtime.declare_variable",
    "workato_db_table.upsert_record",
    "workato_runtime.update_variables",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "workato_db_table.upsert_record",
]
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "sql_row_count",
    "new_records_final",
    "upserts",
    "final_table_rows",
    "final_row_ids",
)


def validate_121086244(raw: dict[str, Any]) -> dict[str, Any]:
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
    upsert = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == UPSERT_STEP_AS), None
    )
    if not isinstance(upsert, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} upsert step missing")
    upsert_input = upsert.get("input") or {}
    if str(upsert_input.get("table_id") or "") != DB_TABLE_ID:
        raise RuntimeError(f"recipe {RECIPE_ID} upsert table changed")
    if str(upsert_input.get("primary_field_id") or "") != PRIMARY_FIELD_DASH:
        raise RuntimeError(f"recipe {RECIPE_ID} upsert primary field changed")
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "db_table_id": DB_TABLE_ID,
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


def seed_121086244(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_121086244(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    if trigger != {}:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must be exactly {{}} (the scheduler payload is "
            f"never dereferenced): {trigger!r}"
        )
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no try/catch: force_action_error is not a reachable branch"
        )
    seed_in = data.get("seed")
    expected_sections = ["project_properties", "snowflake_live", "workato_db_table"]
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != expected_sections:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly {expected_sections}"
        )
    current_date = _require_snowflake_section(seed_in["snowflake_live"])
    _require_project_properties(seed_in["project_properties"])
    table_rows = _require_db_table_section(seed_in["workato_db_table"])
    expect = data.get("expect")
    _require_expect_shape(expect, seed_in, current_date, table_rows)
    provision = ctx.tools.call(
        "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "workato_db_table": deepcopy(seed_in["workato_db_table"]),
        "project_properties": deepcopy(seed_in["project_properties"]),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_121086244(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_121086244(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    if not isinstance(seed.get("workato_db_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing workato_db_table section")
    if not isinstance(seed.get("project_properties"), dict) or not str(
        seed["project_properties"].get(PROJECT_PROPERTY) or ""
    ).strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed file missing project_properties[{PROJECT_PROPERTY!r}]"
        )
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": seed.get("expect"),
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    raw_execution: dict[str, Any] | None = None
    snowflake_cleanup: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = _snapshot(ctx)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx)
    finally:
        # The four registered live tables are benchmark-owned: drop them even
        # on failure. The mock db table needs no live cleanup.
        snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    details["cleanup_response"] = {"snowflake_live": snowflake_cleanup}
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
    result["verifier"] = verify_121086244(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_snowflake_section(section: Any) -> datetime.date:
    if not isinstance(section, dict) or sorted(section.keys()) != ["current_time", "tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly "
            "{'current_time', 'tables'} (the SQL calls CURRENT_DATE())"
        )
    fixed = str(section.get("current_time") or "")
    parsed = datetime.datetime.fromisoformat(fixed.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} current_time must carry an explicit UTC offset: {fixed!r}"
        )
    tables = section["tables"]
    expected_keys = sorted([INVOICE_TABLE, CUSTOMER_TABLE, CURRENCY_TABLE, ACCOUNT_TABLE])
    if not isinstance(tables, dict) or sorted(tables.keys()) != expected_keys:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must register exactly {expected_keys} -- the "
            "SALESFORCE key keeps its quotes (unquoted does not match the quoted SQL)"
        )
    _require_typed_table(tables[INVOICE_TABLE], INVOICE_TABLE, INVOICE_COLUMNS)
    _require_typed_table(tables[CUSTOMER_TABLE], CUSTOMER_TABLE, CUSTOMER_COLUMNS)
    _require_typed_table(tables[CURRENCY_TABLE], CURRENCY_TABLE, CURRENCY_COLUMNS)
    _require_typed_table(tables[ACCOUNT_TABLE], ACCOUNT_TABLE, ACCOUNT_COLUMNS)
    for idx, row in enumerate(tables[INVOICE_TABLE]["rows"]):
        for column in MONEY_COLUMNS:
            _require_quarter(row.get(column), INVOICE_TABLE, idx, column)
    for idx, row in enumerate(tables[ACCOUNT_TABLE]["rows"]):
        _require_quarter(row.get("current_arr__c"), ACCOUNT_TABLE, idx, "current_arr__c")
    return parsed.astimezone(datetime.timezone.utc).date()


def _require_quarter(value: Any, table: str, idx: int, column: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"recipe {RECIPE_ID} {table} row {idx} {column} must be numeric")
    if float(value) * 4 != round(float(value) * 4):
        raise RuntimeError(
            f"recipe {RECIPE_ID} {table} row {idx} {column} must sit on a .25 quarter "
            f"(FLOAT column, binary-exact arithmetic): {value!r}"
        )


def _require_typed_table(spec: Any, table: str, columns: dict[str, str]) -> None:
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(f"recipe {RECIPE_ID} table {table} spec must be {{'columns','rows'}}")
    if spec["columns"] != columns:
        raise RuntimeError(f"recipe {RECIPE_ID} table {table} columns must be exactly {columns}")
    rows = spec["rows"]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {table} rows must be a list (may be empty)")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} table {table} row {idx} must be an object")
        extra = sorted(set(row.keys()) - set(columns.keys()))
        if extra:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {table} row {idx} uses undeclared columns: {extra}"
            )
        for column, value in row.items():
            kind = columns[column]
            if value is None:
                continue
            if kind == "boolean" and not isinstance(value, bool):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table} row {idx} {column} must be boolean"
                )
            if kind == "float" and (
                isinstance(value, bool) or not isinstance(value, (int, float))
            ):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table} row {idx} {column} must be numeric"
                )
            if kind == "string" and not isinstance(value, str):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {table} row {idx} {column} must be a string"
                )
            if kind == "date":
                try:
                    datetime.date.fromisoformat(str(value))
                except ValueError as exc:
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} table {table} row {idx} {column} must be "
                        f"YYYY-MM-DD: {value!r}"
                    ) from exc


def _require_project_properties(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != [PROJECT_PROPERTY]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.project_properties must pin exactly "
            f"{PROJECT_PROPERTY!r} (the SQL renders that pill twice; missing raises)"
        )
    if not str(section[PROJECT_PROPERTY] or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} project property value must be non-empty")


def _require_db_table_section(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table must be exactly {{'tables': ...}}"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [DB_TABLE_ID]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.workato_db_table.tables must declare exactly table "
            f"{DB_TABLE_ID!r}"
        )
    rows = tables[DB_TABLE_ID]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table {DB_TABLE_ID} rows must be a list")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or not str(row.get(PRIMARY_FIELD) or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} table {DB_TABLE_ID} seed row {idx} must carry the "
                f"underscore-form primary field {PRIMARY_FIELD!r}"
            )
        for key, value in row.items():
            if not isinstance(value, str):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} table {DB_TABLE_ID} seed row {idx} field {key} must "
                    "be a string (the mock stores stringified cells; typed seeds would break "
                    "byte-exact final-state pins)"
                )
    return rows


def _qualifying_rows(
    tables: dict[str, Any], current_date: datetime.date
) -> list[dict[str, Any]]:
    """Replicate the WHERE/JOIN semantics of the open-invoice SQL over the
    seeded rows (deterministic given the pinned current_time)."""
    customers = {
        str(row.get("internal_id")): row for row in tables[CUSTOMER_TABLE]["rows"]
    }
    currencies = {
        str(row.get("internal_id")): row for row in tables[CURRENCY_TABLE]["rows"]
    }
    accounts = {str(row.get("id")): row for row in tables[ACCOUNT_TABLE]["rows"]}
    out: list[dict[str, Any]] = []
    for invoice in tables[INVOICE_TABLE]["rows"]:
        customer = customers.get(str(invoice.get("customer_id")))
        if customer is None or str(customer.get("company_name") or "").startswith("I/C"):
            continue
        currency = currencies.get(str(invoice.get("currency_id")))
        if currency is None:
            continue
        account = accounts.get(str(customer.get("salesforce_account_id")))
        remaining = invoice.get("amount_remaining")
        if remaining is None or not float(remaining) > 0:
            continue
        status = str(invoice.get("status") or "")
        if status == "Paid In Full" or status == "Pending Approval":
            continue
        if account is not None and account.get("active_subscription__c") is False:
            continue
        due = invoice.get("due_date")
        if due is None:
            continue
        past_due = (current_date - datetime.date.fromisoformat(str(due))).days
        subtotal = float(invoice.get("subtotal"))
        amount = subtotal + float(invoice.get("tax_total") or 0)
        out.append(
            {
                "past_due": past_due,
                "invoice_id": str(invoice.get("internal_id")),
                "invoice_no": str(invoice.get("invoice_number")),
                "invoice_date": str(invoice.get("invoice_date")),
                "invoice_due_date": str(due),
                "payment_terms": invoice.get("payment_term_name"),
                "currency": str(currency.get("iso_code")),
                "subtotal": subtotal,
                "amount": amount,
                "balance": float(remaining),
                "salesforce_invoice_id": invoice.get("salesforce_record_id"),
                "customer_id": str(invoice.get("customer_id")),
                "customer_name": invoice.get("customer_name"),
                "salesforce_account_id": customer.get("salesforce_account_id"),
                "account_owner": None if account is None else account.get("ownerid"),
                "current_arr": None if account is None else account.get("current_arr__c"),
                "active": None if account is None else account.get("active_subscription__c"),
            }
        )
    return out


def _expected_record(row: dict[str, Any]) -> dict[str, Any]:
    return {field_id: row[key] for key, field_id in FIELD_MAP.items()}


def _require_expect_shape(
    expect: Any,
    seed_in: dict[str, Any],
    current_date: datetime.date,
    table_rows: list[dict[str, Any]],
) -> None:
    if not isinstance(expect, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    quals = _qualifying_rows(seed_in["snowflake_live"]["tables"], current_date)
    if expect.get("sql_row_count") != len(quals):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.sql_row_count must equal the recomputed number of "
            f"qualifying seeded invoices ({len(quals)}): {expect.get('sql_row_count')!r}"
        )
    seeded_ids = {str(row.get(PRIMARY_FIELD)) for row in table_rows}
    expected_upserts = {
        row["invoice_id"]: {
            "invoice_id": row["invoice_id"],
            "created": row["invoice_id"] not in seeded_ids,
            "record": _expected_record(row),
        }
        for row in quals
    }
    actual_upserts = expect.get("upserts")
    if not isinstance(actual_upserts, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.upserts must be a list")
    actual_by_id = {
        str(item.get("invoice_id")): item
        for item in actual_upserts
        if isinstance(item, dict)
    }
    if actual_by_id != expected_upserts:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.upserts diverges from the WHERE-clause "
            f"recomputation over the seeds: expected {expected_upserts!r}, "
            f"got {actual_by_id!r}"
        )
    created_count = sum(1 for item in expected_upserts.values() if item["created"])
    if expect.get("new_records_final") != created_count:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.new_records_final must be {created_count} "
            "(one increment per created:true upsert)"
        )
    expected_action_count = 2 + len(quals) + created_count
    if expect.get("executed_action_count") != expected_action_count:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.executed_action_count must be "
            f"{expected_action_count} (search + declare + {len(quals)} upserts + "
            f"{created_count} counter updates)"
        )
    expected_tools = ["snowflake.search_rows_sql"] + (
        ["workato_db_table.upsert_record"] * len(quals)
    )
    if expect.get("tools") != expected_tools:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools must be {expected_tools}: {expect.get('tools')!r}"
        )
    row_ids = expect.get("final_row_ids")
    if not isinstance(row_ids, list) or len(row_ids) != len(table_rows) + created_count:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_row_ids must list "
            f"{len(table_rows) + created_count} row ids (seeded + created)"
        )
    final_rows = expect.get("final_table_rows")
    if not isinstance(final_rows, list) or len(final_rows) != len(table_rows) + created_count:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_table_rows must pin exactly "
            f"{len(table_rows) + created_count} rows (no ghost writes)"
        )


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


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    snowflake = dict(ctx.tools.call("harness.snowflake.snapshot", {}))
    db_table = dict(ctx.tools.call("harness.workato_db_table.snapshot", {}))
    snowflake.pop("ok", None)
    return {**snowflake, **db_table}


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
