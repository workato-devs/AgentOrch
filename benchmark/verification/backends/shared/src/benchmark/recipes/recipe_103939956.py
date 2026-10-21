from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_103939956


RECIPE_ID = "103939956"
SEED_TYPE = "salesforce_recipe_function_open_feature_counts_variant"
TRACK = "live_salesforce_recipe_function_open_feature_counts"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "ea80dd69"
FR_SOBJECT = "Feature_Request__c"
SEARCH_AS = "596c386d"
TRIGGER_ROW_KEYS = {"AccountID", "AccountName"}
CLOSED_STATUSES = {"Done", "Rejected", "Released"}
# Schema-in-seed contract: Feature_Request__c was mdapi-deployed 2026-07-08
# (batch-07 provisioning) with Account__c Text(255) + Jira_Status__c
# Text(255). mdapi-deployed fields are describe-INVISIBLE until FLS is
# granted, so the seed schema section re-ensures FLS on both columns every
# run via ensure_custom_field (106603524/88707765 precedent).
REQUIRED_SCHEMA = [
    {"sobject": FR_SOBJECT, "field": "Account__c", "sf_type": "Text"},
    {"sobject": FR_SOBJECT, "field": "Jira_Status__c", "sf_type": "Text"},
]
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")

# workato_recipe_function.execute (as ea80dd69; parameters.AccountList[]
# {AccountID, AccountName}). Linear body, no if/foreach/try -- TWIN of
# 98802887 (same 5-step skeleton, payload deltas only):
#   2  workato_variable.declare_variable a826e077: account_ids_string =
#      AccountList&.pluck("AccountID").join("','")
#   3  salesforce.search_sobjects_soql_v2 596c386d (LIVE, limit 2000):
#      SELECT Account__c AccountID, COUNT(Id) TotalOpenFeatures
#      FROM Feature_Request__c WHERE IsDeleted = FALSE AND Jira_Status__c
#      NOT IN ('Done', 'Rejected', 'Released') AND Account__c IN ('<ids>')
#      GROUP BY Account__c -- aggregate COUNT + SELECT aliases evaluated by
#      the harness over live-read-back owned rows (_apply_aggregates); every
#      seeded FR declares read_fields ['IsDeleted'] so the strict boolean
#      leaf evaluates the LIVE read-back false (106603524/118905064
#      precedent -- WITHOUT it the row is silently rejected, probe-verified)
#   4  workato_smart_list.create_list 22b39266 'OpenFeatures' from the
#      aggregate records (primary AccountID; Workato-internal SQLite)
#   5  workato_smart_list.query_list f5816674 (output_schema_by index):
#      SELECT AccountID, TotalOpenFeatures FROM OpenFeatures (identifiers
#      via columns/list_name pills; plain projection, no window)
#   6  workato_recipe_function.return_result 004b17c4: result.FeatureRequests
#      ____source-mapped {AccountID, TotalOpenFeatureRequets} -- the key
#      'TotalOpenFeatureRequets' is a raw-recipe TYPO kept verbatim -- TERMINAL
#
# Branch mapping (linear recipe: coverage = SOQL predicate arms + group
# shapes; probe-verified end-to-end offline 2026-07-08):
# - variant_00 counts_per_account: A has 2 open FRs + 1 'Done' (NOT IN
#   excludes), B has 1 open -> [{A,2},{B,1}] with int counts.
# - variant_01 account_outside_list_excluded: an open FR on account C not in
#   AccountList is excluded by the IN pill -> only A's group returns.
# - variant_02 all_statuses_closed_empty: only Done/Rejected/Released FRs
#   (all three NOT-IN literals) -> 0 groups -> create_list registers the
#   EMPTY 2-column table from the node schema -> query [] ->
#   result.FeatureRequests [].
# - variant_03 not_in_exact_match_boundary: NOT IN is exact equality --
#   'Rejection Pending' is COUNTED beside excluded 'Rejected'/'Done'; B
#   carries only 'Released' so its group is ABSENT (group omission, not a
#   zero row).
#
# GROUP BY output order = owned-record iteration order in the harness
# (insertion-ordered dict, 106603524 precedent): seed FRs grouped by account
# in the order the expected rows are pinned. Backends: salesforce LIVE
# (benchmark-owned Account + Feature_Request__c records; cleanup deletes
# owned seeds in a finally block -- read-only recipe, but owned records must
# not leak); workato_smart_list / workato_variable / workato_recipe_function
# are Workato-internal in-process.

_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "ea80dd69",
  "provider": "workato_recipe_function",
  "name": "execute",
  "skip": false,
  "input": {
   "parameters_schema_json": "[{\"name\":\"AccountList\",\"type\":\"array\",\"optional\":false,\"label\":\"Account list\",\"properties\":[{\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account ID\"},{\"name\":\"AccountName\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account name\"}],\"of\":\"object\"}]",
   "result_schema_json": "[{\"name\":\"FeatureRequests\",\"type\":\"array\",\"optional\":false,\"properties\":[{\"control_type\":\"text\",\"label\":\"Account ID\",\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"integer\",\"label\":\"Total open feature requests\",\"name\":\"TotalOpenFeatureRequets\",\"type\":\"integer\",\"optional\":false,\"parse_output\":\"integer_conversion\"}],\"of\":\"object\",\"label\":\"Feature requests\"}]"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "a826e077",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "account_ids_string": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"ea80dd69\",\"path\":[\"parameters\",\"AccountList\"]}')&.pluck(\"AccountID\").join(\"','\")"
    },
    "schema": "[{\"control_type\":\"text\",\"label\":\"account_ids_string\",\"name\":\"account_ids_string\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"account_ids_string\"}}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "596c386d",
  "provider": "salesforce",
  "name": "search_sobjects_soql_v2",
  "skip": false,
  "input": {
   "limit": "2000",
   "output_schema": "[{\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"AccountID\"},{\"name\":\"TotalOpenFeatures\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"Total open features\",\"parse_output\":\"integer_conversion\"}]",
   "query": "SELECT Account__c AccountID, \n       COUNT(Id) TotalOpenFeatures\n  FROM Feature_Request__c\n WHERE IsDeleted = FALSE\n   AND Jira_Status__c NOT IN ('Done', 'Rejected', 'Released')\n   AND Account__c IN ('#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"a826e077\",\"path\":[\"account_ids_string\"]}')}')\n GROUP BY Account__c"
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "22b39266",
  "provider": "workato_smart_list",
  "name": "create_list",
  "skip": false,
  "input": {
   "list_name": "OpenFeatures",
   "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"596c386d\",\"path\":[\"records\"]}')",
   "primary_index": "AccountID"
  }
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "f5816674",
  "provider": "workato_smart_list",
  "name": "query_list",
  "skip": false,
  "input": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "output_schema_by": "index",
   "result_schema_json": "[{\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account ID\"},{\"name\":\"TotalOpenFeatures\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"Total open features\",\"parse_output\":\"integer_conversion\"}]",
   "sql": "SELECT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"22b39266\",\"path\":[\"columns\", \"AccountID\"]}')}, #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"22b39266\",\"path\":[\"columns\", \"TotalOpenFeatures\"]}')}\nFROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"22b39266\",\"path\":[\"list_name\"]}')}"
  }
 },
 {
  "keyword": "action",
  "number": 6,
  "as": "004b17c4",
  "provider": "workato_recipe_function",
  "name": "return_result",
  "skip": false,
  "input": {
   "result": {
    "FeatureRequests": {
     "AccountID": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"f5816674\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"AccountID\"]}')}",
     "TotalOpenFeatureRequets": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"f5816674\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"TotalOpenFeatures\"]}')}",
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"f5816674\",\"path\":[\"rows\"]}')}"
    }
   }
  }
 }
]"""

STRUCTURE_PINS: list[dict[str, Any]] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "salesforce.search_records",
    "workato_smart_list.create_list",
    "workato_smart_list.query_list",
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
    "smart_list_sqls",
    "create_lists",
    "query_rows",
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


def validate_103939956(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_103939956(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_103939956(raw)
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
        # (106603524 precedent).
        "expect": resolved_expect,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": refs,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_103939956(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_103939956(raw)
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    if not seed["salesforce_live"].get("strict_soql_conditions"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires strict_soql_conditions in the live state "
            "(IsDeleted = FALSE / NOT IN / IN are strict-only operators)"
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
        # Required cleanup: owned Feature_Request__c + Account seed records
        # must not leak into later runs (the recipe itself only reads).
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
    result["verifier"] = verify_103939956(result)
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
        if not isinstance(row, dict) or set(row) != TRIGGER_ROW_KEYS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} every AccountList row must carry exactly "
                f"{sorted(TRIGGER_ROW_KEYS)} (the trigger parameters schema): {row!r}"
            )
        for key in TRIGGER_ROW_KEYS:
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} AccountList row {key} must be a non-empty string: {row!r}"
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
            "(IsDeleted = FALSE / NOT IN / IN are strict-only operators)"
        )
    if section.get("schema") != REQUIRED_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare exactly "
            f"{json.dumps(REQUIRED_SCHEMA)} (mdapi fields are describe-invisible "
            "until FLS -- re-ensure every run)"
        )
    records = section.get("records")
    if not isinstance(records, list) or not records:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.salesforce.records must be a non-empty list")
    for record in records:
        if not isinstance(record, dict) or not str(record.get("ref") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded Salesforce record needs a 'ref': {record}"
            )
        fields = record.get("fields")
        if not isinstance(fields, dict) or not fields:
            raise RuntimeError(f"recipe {RECIPE_ID} every seeded record needs explicit fields: {record}")
        sobject = str(record.get("sobject") or "")
        if sobject not in {"Account", FR_SOBJECT}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seeded records must be Account or {FR_SOBJECT}: {record}"
            )
        if not str(fields.get("Name") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded record needs an explicit Name "
                f"(mdapi Text name field): {record}"
            )
        if sobject == FR_SOBJECT:
            if record.get("read_fields") != ["IsDeleted"]:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} every {FR_SOBJECT} seed must declare "
                    "read_fields ['IsDeleted'] (the strict 'IsDeleted = FALSE' leaf "
                    "evaluates the live read-back; without it the row is SILENTLY "
                    "rejected -- 106603524/118905064 precedent): "
                    f"{record}"
                )
            for key in ("Account__c", "Jira_Status__c"):
                if not str(fields.get(key) or "").strip():
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} {FR_SOBJECT} seed must set {key}: {record}"
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
    if expect.get("executed_action_count") != 5:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the linear body always executes all 5 actions"
        )
    tools = expect.get("tools")
    tool_expectations = expect.get("tool_expectations")
    if tools != ALLOWED_TOOLS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tools must be exactly {ALLOWED_TOOLS}: {tools!r}"
        )
    if not isinstance(tool_expectations, list) or len(tool_expectations) != len(tools):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry"
        )
    if not isinstance(expect.get("smart_list_sqls"), list) or not isinstance(
        expect.get("create_lists"), list
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.smart_list_sqls/create_lists must be lists")
    query_rows = expect.get("query_rows")
    if not isinstance(query_rows, list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.query_rows must pin the exact projected rows "
            "([] on the empty branch)"
        )
    final_result = expect.get("final_result")
    if not isinstance(final_result, dict) or not isinstance(
        final_result.get("FeatureRequests"), list
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_result.FeatureRequests must pin the exact "
            "return_result payload ([] on the empty branch)"
        )
    for row in final_result["FeatureRequests"]:
        if not isinstance(row, dict) or set(row) != {"AccountID", "TotalOpenFeatureRequets"}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} FeatureRequests rows carry exactly AccountID + the "
                f"raw-recipe TYPO key 'TotalOpenFeatureRequets' (schema-typo fidelity): {row!r}"
            )
        if not isinstance(row.get("TotalOpenFeatureRequets"), int) or isinstance(
            row.get("TotalOpenFeatureRequets"), bool
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} TotalOpenFeatureRequets must be a plain int "
                f"(COUNT stays integer through the list pipeline): {row!r}"
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
