from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_101954510


RECIPE_ID = "101954510"
SEED_TYPE = "sf_history_snowflake_oem_relink_variant"
TRACK = "final_state"
TRIGGER_AS = "364d5c88"
SEARCH_AS = "57ccff6f"
SQL_AS = "73109306"
FOREACH_AS = "d4ab6d55"
COMPOSITE_AS = "a9df1a62"
USER_SOBJECT = "Workato_User__c"
TABLE_KEY = "EDW_DB.SALESFORCE.WORKATO_USER"

# TRUE TWIN of 115850922 (scale batch 07, batch_D) — recipe 101954510 is the
# 2024-08-28 original (flow 43771832 v5); 115850922 is the 2025-03-07 re-issue
# (flow 43592055 v15). The raw diff is 106 lines of CSV metadata + extended-
# schema noise ONLY (Domain__c / Is_AHQ_Admin__c / Last_Login_Date__c /
# Logins_Last_30_Days__c schema entries and parse_output/render_input
# null-vs-{} formatting); every executable input is BYTE-IDENTICAL across all
# 5 nodes, including the as-ids 364d5c88/57ccff6f/73109306/d4ab6d55/a9df1a62
# (re-proved 2026-07-08 on the working tree via key-by-key node comparison).
# This module is derived mechanically from the registered head module and
# validates the SAME STRUCTURE_PINS; verify_101954510 delegates to
# verify_115850922 (twin precedent verify_117564458 -> verify_118162473).
# Twin-specific groundtruth lives in this recipe's OWN variant inputs
# (own Account/user names, OEM ids 313/528/664, own timestamps — nothing
# byte-shared with the head's 777/812/941 variants) and its OWN live lanes.
#
# See recipe_115850922.py for the full shape/backends/branch documentation;
# everything there applies verbatim (seeded __History event, live SF search
# alias, NULL-EXCLUDING plain '!=' Snowflake WHERE — live-probed on the head,
# evidence transfers because the executable inputs are byte-identical —
# single-batch foreach, constant-value composite update). The physical
# Snowflake table EDW_DB.SALESFORCE.WORKATO_USER is SHARED by the trio:
# never run family variants concurrently.
#
# Branch mapping (per benmark_rules):
# - variant_00 relink_admin_children: old-OEM child relinked; NULL-OEM child
#   EXCLUDED by the plain '!=' and pinned untouched; already-new + wrong-DC
#   decoys excluded -> 1 row -> composite single-record arm.
# - variant_01 no_children_noop: already-new + NULL-OEM + wrong-OEM decoys ->
#   0 rows -> foreach zero iterations -> composite never traces.
# - variant_02 multi_child_batch: two old-OEM children -> one batch -> 2 live
#   updates with the SAME constant Account id (id SET compare, no ORDER BY).
TABLE_COLUMNS = {
    "id": "string",
    "account__c": "string",
    "oem_id__c": "string",
    "oem_account__c": "string",
    "data_center__c": "string",
}
REQUIRED_SCHEMA = [
    {"sobject": USER_SOBJECT, "field": "OEM_ID__c", "sf_type": "Text"},
    {"sobject": USER_SOBJECT, "field": "Data_Center__c", "sf_type": "Text"},
    {"sobject": USER_SOBJECT, "field": "Is_Admin__c", "sf_type": "Checkbox"},
]
RESOLVED_SQL_TEMPLATE = (
    "SELECT \nId, \nAccount__c\nFROM EDW_DB.SALESFORCE.WORKATO_USER\nWHERE\n"
    "OEM_ID__c = '{oem_id}' AND OEM_Account__c != '{account}' "
    "AND Data_Center__c = '{data_center}'"
)
TRIGGER_KEYS = ("ParentId", "CreatedDate", "Field", "OldValue", "NewValue")
TRIGGER_FIELD = "Account__c"
PARENT_TOKEN = "$WU_PARENT_ID"
ACC_OLD_TOKEN = "$ACC_OLD_ID"
ACC_NEW_TOKEN = "$ACC_NEW_ID"
EXPECT_KEYS = (
    "case",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "updated_children",
    "new_oem_account",
    "final_oem_accounts",
)
EXPECTED_RAW_TOOLS: list[str] = [
    "salesforce.search_records",
    "snowflake.search_rows_sql",
    "salesforce.update_record",
]
ALLOWED_TOOLS: list[str] = list(EXPECTED_RAW_TOOLS)
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")

_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "364d5c88",
  "provider": "salesforce",
  "name": "new_custom_object",
  "skip": false,
  "input": {
   "field_list": "ParentId\nCreatedDate\nField\nOldValue\nNewValue",
   "query": "Field = 'Account__c' AND Parent.OEM_ID__c != null AND Parent.Is_Admin__c = true",
   "since_offset": "0",
   "sobject_name": "Workato_User__History"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "57ccff6f",
  "provider": "salesforce",
  "name": "search_sobjects",
  "skip": false,
  "input": {
   "Id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"364d5c88\",\"path\":[\"ParentId\"]}')}",
   "field_list": "Id\nAccount__c\nOEM_ID__c\nData_Center__c",
   "limit": "150",
   "sobject_name": "Workato_User__c"
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "73109306",
  "provider": "snowflake",
  "name": "search_rows_sql",
  "skip": false,
  "input": {
   "limit": "50000",
   "sql": "SELECT \nId, \nAccount__c\nFROM EDW_DB.SALESFORCE.WORKATO_USER\nWHERE\nOEM_ID__c = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"57ccff6f\",\"path\":[\"Workato_User__c\", {\"path_element_type\": \"current_item\"}, \"OEM_ID__c\"]}')}' AND OEM_Account__c != '#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"57ccff6f\",\"path\":[\"Workato_User__c\", {\"path_element_type\": \"current_item\"}, \"Account__c\"]}')}' AND Data_Center__c = '#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"57ccff6f\",\"path\":[\"Workato_User__c\", {\"path_element_type\": \"current_item\"}, \"Data_Center__c\"]}')}'"
  }
 },
 {
  "keyword": "foreach",
  "number": 4,
  "as": "d4ab6d55",
  "provider": null,
  "name": null,
  "skip": false,
  "input": {
   "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"73109306\",\"path\":[\"rows\"]}')}"
  },
  "repeat_mode": "batch",
  "batch_size": "2000",
  "source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"73109306\",\"path\":[\"rows\"]}')}"
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "a9df1a62",
  "provider": "salesforce",
  "name": "composite_update_sobject",
  "skip": false,
  "input": {
   "advanced_configuration": {
    "allOrNone": "false"
   },
   "batch_size": "200",
   "records": {
    "Id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"d4ab6d55\",\"path\":[\"batch\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}",
    "OEM_Account__c": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"57ccff6f\",\"path\":[\"Workato_User__c\", {\"path_element_type\": \"current_item\"}, \"Account__c\"]}')}",
    "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"foreach\",\"line\":\"d4ab6d55\",\"path\":[\"batch\"]}')}",
    "attributes": {
     "Workato_User__c": "Workato_User__c"
    }
   },
   "sobject_name": "Workato_User__c"
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
    out = [pin]
    for child in node.get("block") or []:
        if isinstance(child, dict):
            out.extend(_structure(child))
    return out


def validate_101954510(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
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
        "trigger_provider": "salesforce",
        "trigger_name": "new_custom_object",
        "snowflake_tables": [TABLE_KEY],
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


def seed_101954510(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_101954510(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    if data.get("force_action_error") is not None:
        raise RuntimeError(
            f"recipe {RECIPE_ID} has no catch: a forced action error fails the whole run "
            "instead of exercising a recipe branch"
        )
    trigger = trigger_input(ctx)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["salesforce", "snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must carry exactly salesforce + snowflake_live; "
            f"got {sorted(seed_in.keys())}"
        )
    parent, children = _require_salesforce_section(seed_in["salesforce"])
    _require_trigger_shape(trigger, parent)
    rows = _require_snowflake_section(seed_in["snowflake_live"], parent, children)
    predicted = _predicted_updates(parent, rows)
    _require_expect_shape(data.get("expect"), trigger, parent, children, rows, predicted)

    provision = ctx.tools.call(
        "harness.salesforce.seed_records", {"salesforce": deepcopy(seed_in["salesforce"])}
    )
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce seed failed: {provision}")
    refs = _salesforce_ref_tokens(seed_in["salesforce"], provision)

    snowflake_seed = _replace_value(deepcopy(seed_in["snowflake_live"]), refs)
    _require_resolved(snowflake_seed)
    snowflake_provision = ctx.tools.call(
        "harness.snowflake_live.seed_tables", {"snowflake": snowflake_seed}
    )
    if not snowflake_provision.get("ok"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} live Snowflake seed failed: {snowflake_provision}"
        )

    resolved_trigger = _replace_value(trigger, refs)
    _require_resolved(resolved_trigger)
    resolved_expect = _replace_value(deepcopy(data["expect"]), refs)
    _require_resolved(resolved_expect)
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "trigger": resolved_trigger,
        "expect": resolved_expect,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": refs,
        "snowflake_live": deepcopy(snowflake_provision["state"]),
        "snowflake_seed_snapshot": deepcopy(snowflake_provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_101954510(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_101954510(raw)
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    trigger = seed.get("trigger")
    if not isinstance(trigger, dict) or not trigger:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing trigger object")
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": trigger,
        "track": seed.get("track"),
        "expect": expect,
        "raw_validation": validation,
        "expected_raw_tools": EXPECTED_RAW_TOOLS,
        "seed_harness_tool_calls": seed.get("harness_tool_calls") or [],
    }
    snowflake_cleanup: dict[str, Any] | None = None
    salesforce_cleanup: dict[str, Any] | None = None
    try:
        details["initial_snapshot"] = _snapshot(ctx)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        details["raw_execution"] = raw_execution
        details["ground_truth"] = _ground_truth(raw_execution)
        details["final_snapshot"] = _snapshot(ctx)
    finally:
        # Required cleanup on BOTH live backends: the run mutates owned
        # Salesforce records and the seeder created the live Snowflake table.
        try:
            snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
        finally:
            salesforce_cleanup = ctx.tools.call("harness.salesforce.cleanup", {})
        details["cleanup_response"] = {
            "snowflake_live": snowflake_cleanup,
            "salesforce": salesforce_cleanup,
        }
    if not (snowflake_cleanup or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake cleanup failed: {snowflake_cleanup}")
    if not (salesforce_cleanup or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Salesforce cleanup failed: {salesforce_cleanup}")
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details=details,
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_101954510(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any], parent: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != sorted(TRIGGER_KEYS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the trigger field_list "
            f"{sorted(TRIGGER_KEYS)}; got {sorted(trigger.keys())}"
        )
    if trigger.get("Field") != TRIGGER_FIELD:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger Field must be {TRIGGER_FIELD!r} "
            f"(trigger query coherence); got {trigger.get('Field')!r}"
        )
    if trigger.get("ParentId") != PARENT_TOKEN:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger ParentId must be the {PARENT_TOKEN} token "
            "(a live benchmark-owned Workato_User__c id after seeding)"
        )
    if trigger.get("OldValue") != ACC_OLD_TOKEN or trigger.get("NewValue") != ACC_NEW_TOKEN:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger Old/NewValue must be the {ACC_OLD_TOKEN}/"
            f"{ACC_NEW_TOKEN} live Account tokens (the Account__c change the event records)"
        )
    created = str(trigger.get("CreatedDate") or "")
    if "T" not in created or not created.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger CreatedDate must be a fixed ISO timestamp; "
            f"got {created!r}"
        )
    fields = parent.get("fields") or {}
    if fields.get("Account__c") != trigger.get("NewValue"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} the parent's CURRENT Account__c must equal the event "
            "NewValue (the recipe reads the post-change parent)"
        )


def _require_salesforce_section(section: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} requires seed.salesforce")
    if sorted(section.keys()) != ["records", "schema"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce must be exactly {{schema, records}} "
            "(no SOQL evaluates in the SF matcher, so strict_soql_conditions / "
            f"relationship_expansion are not allowed); got {sorted(section.keys())}"
        )
    if section.get("schema") != REQUIRED_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare exactly "
            f"{json.dumps(REQUIRED_SCHEMA)}"
        )
    records = section.get("records")
    if not isinstance(records, list) or len(records) < 5:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.records needs 2 Accounts + parent + "
            "at least 2 children (decoys prove the WHERE bites)"
        )
    refs = [str(record.get("ref") or "").strip() for record in records if isinstance(record, dict)]
    if len(refs) != len(records) or "" in refs or len(set(refs)) != len(refs):
        raise RuntimeError(
            f"recipe {RECIPE_ID} every seeded Salesforce record needs a unique 'ref'"
        )
    if [record.get("ref") for record in records[:2]] != ["acc_old", "acc_new"] or any(
        record.get("sobject") != "Account" for record in records[:2]
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} records[0]/[1] must be the acc_old/acc_new live Accounts "
            "(Lookup targets must exist before any Workato_User__c references them)"
        )
    for record in records[:2]:
        if not str((record.get("fields") or {}).get("Name") or "").strip():
            raise RuntimeError(f"recipe {RECIPE_ID} Account seeds need an explicit Name")
    users = records[2:]
    if any(record.get("sobject") != USER_SOBJECT for record in users):
        raise RuntimeError(
            f"recipe {RECIPE_ID} records[2:] must all be {USER_SOBJECT} seeds"
        )
    if users[0].get("ref") != "wu_parent":
        raise RuntimeError(f"recipe {RECIPE_ID} records[2] must be the wu_parent record")
    parent = users[0]
    parent_fields = parent.get("fields") or {}
    if parent_fields.get("Account__c") != ACC_NEW_TOKEN:
        raise RuntimeError(
            f"recipe {RECIPE_ID} wu_parent.Account__c must be the {ACC_NEW_TOKEN} token "
            "(live Lookup(Account) — a Text value fails fast live)"
        )
    if parent_fields.get("Is_Admin__c") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} wu_parent.Is_Admin__c must be true "
            "(trigger query: Parent.Is_Admin__c = true)"
        )
    for key in ("Name", "OEM_ID__c", "Data_Center__c"):
        if not str(parent_fields.get(key) or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} wu_parent must set {key} explicitly "
                "(trigger query / SQL pill coherence)"
            )
    children = users[1:]
    if len(children) < 2:
        raise RuntimeError(
            f"recipe {RECIPE_ID} needs at least 2 child {USER_SOBJECT} seeds "
            "(the no-match proof uses decoys, not an empty table)"
        )
    for child in children:
        fields = child.get("fields") or {}
        if not str(child.get("ref") or "").startswith("wu_"):
            raise RuntimeError(f"recipe {RECIPE_ID} child refs must start with wu_: {child}")
        for key in ("Name", "OEM_ID__c", "Data_Center__c"):
            if not str(fields.get(key) or "").strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} child {child.get('ref')} must set {key} explicitly"
                )
        oem_account = fields.get("OEM_Account__c")
        if oem_account is not None and oem_account not in (ACC_OLD_TOKEN, ACC_NEW_TOKEN):
            raise RuntimeError(
                f"recipe {RECIPE_ID} child OEM_Account__c must be a live Account token "
                f"({ACC_OLD_TOKEN}/{ACC_NEW_TOKEN}) or absent (NULL); got {oem_account!r}"
            )
    return parent, children


def _require_snowflake_section(
    section: Any,
    parent: dict[str, Any],
    children: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the SQL uses no CURRENT_DATE/TIMESTAMP, so current_time is not allowed)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [TABLE_KEY]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{[TABLE_KEY]}"
        )
    spec = tables[TABLE_KEY]
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {TABLE_KEY} spec must be exactly "
            "{'columns': ..., 'rows': ...}"
        )
    if spec["columns"] != TABLE_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {TABLE_KEY} must declare exactly the columns "
            f"{TABLE_COLUMNS} (the recipe SELECTs Id/Account__c and filters "
            "OEM_ID__c/OEM_Account__c/Data_Center__c)"
        )
    rows = spec["rows"]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} {TABLE_KEY} rows must be NON-EMPTY — the no-match "
            "branch proves the WHERE bites via decoy rows, not an empty table"
        )
    by_ref = {f"${str(child.get('ref')).upper()}_ID": child for child in children}
    seen: set[str] = set()
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(TABLE_COLUMNS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} {TABLE_KEY} row {idx} must carry exactly the "
                f"declared columns; got {sorted(row.keys()) if isinstance(row, dict) else row!r}"
            )
        token = str(row.get("id") or "")
        child = by_ref.get(token)
        if child is None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} {TABLE_KEY} row {idx} id must be a seeded child's "
                f"$REF token (owned-records-only updates); got {token!r}"
            )
        if token in seen:
            raise RuntimeError(f"recipe {RECIPE_ID} duplicate {TABLE_KEY} row id {token!r}")
        seen.add(token)
        fields = child.get("fields") or {}
        # EDW mirror coherence: the warehouse row must mirror the live child.
        mirror = {
            "oem_id__c": fields.get("OEM_ID__c"),
            "data_center__c": fields.get("Data_Center__c"),
            "oem_account__c": fields.get("OEM_Account__c"),
            "account__c": fields.get("Account__c"),
        }
        for column, expected in mirror.items():
            if row.get(column) != expected:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {TABLE_KEY} row {idx} column {column} must "
                    f"mirror the live child seed ({expected!r}); got {row.get(column)!r}"
                )
    return rows


def _predicted_updates(parent: dict[str, Any], rows: list[dict[str, Any]]) -> list[str]:
    """Authoring-time coherence: apply the LIVE-probed WHERE semantics (plain
    '!=' is NULL-EXCLUDING) to the seeded rows. Run-time truth still comes from
    live Snowflake; a variant whose expect disagrees fails at seed time."""
    fields = parent.get("fields") or {}
    out: list[str] = []
    for row in rows:
        if row.get("oem_id__c") != fields.get("OEM_ID__c"):
            continue
        if row.get("data_center__c") != fields.get("Data_Center__c"):
            continue
        oem_account = row.get("oem_account__c")
        if oem_account is None:
            continue  # NULL-OEM rows are EXCLUDED by the plain '!=' (live-probed)
        if oem_account == fields.get("Account__c"):
            continue
        out.append(str(row.get("id")))
    return out


def _expected_sql(parent: dict[str, Any]) -> str:
    fields = parent.get("fields") or {}
    return RESOLVED_SQL_TEMPLATE.format(
        oem_id=fields.get("OEM_ID__c"),
        account=fields.get("Account__c"),
        data_center=fields.get("Data_Center__c"),
    )


def _require_expect_shape(
    expect: Any,
    trigger: dict[str, Any],
    parent: dict[str, Any],
    children: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    predicted: list[str],
) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} every variant must declare an explicit expect")
    missing = [key for key in EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect is missing required keys: {missing}")
    unknown = sorted(set(expect) - set(EXPECT_KEYS))
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unknown}")
    if not str(expect.get("case") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} expect.case must describe the branch")
    updated = expect.get("updated_children")
    if updated != predicted:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.updated_children must equal the rows the "
            f"live-probed WHERE selects, in row order ({predicted}); got {updated!r}"
        )
    if len(rows) <= len(predicted):
        raise RuntimeError(
            f"recipe {RECIPE_ID} every variant needs at least one EXCLUDED decoy row "
            "(proof that the WHERE bites)"
        )
    if expect.get("new_oem_account") != ACC_NEW_TOKEN:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.new_oem_account must be {ACC_NEW_TOKEN} "
            "(the composite writes the parent search's CONSTANT Account__c)"
        )
    expected_count = 2 + (1 if predicted else 0)
    if expect.get("executed_action_count") != expected_count:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.executed_action_count must be {expected_count} "
            "(trace actions: search + SQL + one composite row only when rows match)"
        )
    expected_tools = [
        "salesforce.search_records",
        "snowflake.search_rows_sql",
        *(["salesforce.update_record"] if predicted else []),
    ]
    if expect.get("tools") != expected_tools:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools must be {expected_tools} "
            "(one stable registry batch call for the composite action)"
        )
    expected_items: list[dict[str, Any]] = [
        {
            "tool": "salesforce.search_records",
            "args_contains": {
                "sobject": USER_SOBJECT,
                "query": "",
                "filters": [{"field": "Id", "value": trigger.get("ParentId")}],
                "limit": "150",
            },
            "result_count": 1,
        },
        {
            "tool": "snowflake.search_rows_sql",
            "args_contains": {"sql": _expected_sql(parent), "limit": "50000"},
            "result_count": len(predicted),
        },
    ]
    if predicted:
        expected_items.append(
            {
                "tool": "salesforce.update_record",
                "args_contains": {
                    "sobject": USER_SOBJECT,
                    "records": [
                        {
                            "sobject": USER_SOBJECT,
                            "id": token,
                            "fields": {"OEM_Account__c": ACC_NEW_TOKEN},
                        }
                        for token in predicted
                    ],
                },
            }
        )
    if expect.get("tool_expectations") != expected_items:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must equal\n"
            f"{json.dumps(expected_items, indent=1)}\n"
            f"got\n{json.dumps(expect.get('tool_expectations'), indent=1)}"
        )
    expected_final: dict[str, Any] = {
        PARENT_TOKEN: (parent.get("fields") or {}).get("OEM_Account__c"),
    }
    for child in children:
        token = f"${str(child.get('ref')).upper()}_ID"
        seeded = (child.get("fields") or {}).get("OEM_Account__c")
        expected_final[token] = ACC_NEW_TOKEN if token in predicted else seeded
    if expect.get("final_oem_accounts") != expected_final:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_oem_accounts must pin every seeded "
            f"{USER_SOBJECT} record's post-run OEM_Account__c exactly "
            f"({json.dumps(expected_final, sort_keys=True)}); got "
            f"{json.dumps(expect.get('final_oem_accounts'), sort_keys=True)}"
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
        ref = str(record.get("ref") or "").strip()
        if ref:
            refs[f"${ref.upper()}_ID"] = live_ids[idx]
    return refs


def _replace_value(value: Any, refs: dict[str, str]) -> Any:
    if isinstance(value, dict):
        # Keys are replaced too: expect.final_oem_accounts is keyed by tokens.
        return {
            _replace_value(key, refs): _replace_value(item, refs)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_replace_value(item, refs) for item in value]
    if isinstance(value, str):
        out = value
        # Longest-first so a token never rewrites inside a longer sibling.
        for token in sorted(refs, key=len, reverse=True):
            out = out.replace(token, refs[token])
        return out
    return value


def _require_resolved(value: Any) -> None:
    leftover = _TOKEN_RE.findall(json.dumps(value))
    if leftover:
        raise RuntimeError(
            f"recipe {RECIPE_ID} unresolved seed tokens remain: {sorted(set(leftover))}"
        )


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    out: dict[str, Any] = {}
    out.update(ctx.tools.call("harness.salesforce.snapshot", {}))
    out.update(ctx.tools.call("harness.snowflake.snapshot", {}))
    return out


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if not tool:
            continue
        by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
