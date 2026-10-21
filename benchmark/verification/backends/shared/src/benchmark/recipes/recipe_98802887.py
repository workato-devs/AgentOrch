from __future__ import annotations

import json
import re
import time
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_98802887


RECIPE_ID = "98802887"
SEED_TYPE = "salesforce_recipe_function_fv_status_variant"
TRACK = "live_salesforce_recipe_function_fv_status"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "cf447f1d"
TASK_SOBJECT = "Workato_Task__c"
SEARCH_AS = "fcec7f45"
TRIGGER_ROW_KEYS = {"AccountID", "AccountName"}
# The verbatim SOQL LIKE literal: the seed guard uses it to keep the DESC
# partition deterministic (at most one MATCHING task per account per phase).
LIKE_LITERAL = "First Value - Direct"
# Workato_Task__c.CreatedDate is org-assigned with whole-second precision;
# audit-field create is disabled in the benchmark org, so a real pause
# between phases is the only faithful spacing (88704851/123859779 precedent
# -- a tie would make ROW_NUMBER ... ORDER BY CreatedDate DESC
# nondeterministic).
CREATED_DATE_SPACING_SECONDS = 1.2
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")

# workato_recipe_function.execute (as cf447f1d; parameters.AccountList[]
# {AccountID, AccountName}; [] is the in-contract empty input). Linear body,
# no if/foreach/try:
#   2  workato_variable.declare_variable c6a252e3: account_ids_string =
#      AccountList&.pluck("AccountID").join("','")
#      (probe-verified: 2 accounts -> "id1','id2"; [] -> "")
#   3  salesforce.search_sobjects_soql_v2 fcec7f45 (LIVE, limit 2000):
#      SELECT Account__c, Status__c, CreatedDate FROM Workato_Task__c
#      WHERE Activity_Type__c LIKE '%First Value - Direct%'
#      AND Account__c IN ('<ids>') -- Workato_Task__c EXISTS in the
#      benchmark org (17 fields incl all queried; FLS pre-granted --
#      91361562 uses Activity_Type__c with no schema section); infix LIKE +
#      IN are strict-only conditions
#   4  workato_smart_list.create_list af71d26b 'FVStatus' from the records
#      (primary Account__c, secondary CreatedDate; Workato-internal SQLite)
#   5  workato_smart_list.query_list 65d5b389 (output_schema_by index):
#      WITH all_fv_tasks AS (SELECT Account__c, Status__c, ROW_NUMBER()
#      OVER (PARTITION BY Account__c ORDER BY CreatedDate DESC) AS rn FROM
#      FVStatus) SELECT ... WHERE rn = 1 -- latest task per account; all
#      identifiers resolve through list_name/columns pills; the projected
#      rows carry BOTH source columns and the positional index aliases
#      ({Account__c, Status__c, AccountID, Status} -- probe-verified)
#   6  workato_recipe_function.return_result 656337a0:
#      result.FVStatus ____source-mapped over the rows -- TERMINAL
#
# Branch mapping (linear recipe: coverage = SOQL predicate arms + rn dedup +
# empty shapes; probe-verified end-to-end offline 2026-07-08):
# - variant_00 dedup_latest_per_account: acct A has 2 matching tasks in
#   separate phases (Open older, Completed newer) -> rn=1 keeps Completed;
#   acct B has 1 -> {A,Completed},{B,Open}; a non-matching decoy on A proves
#   the LIKE filter inside the partition.
# - variant_01 like_filter_boundary: infix match 'CS First Value - Direct
#   followup' flows through; 'Renewal Check' and 'First Value - Emb' (the
#   Emb arm named in the recipe comment) are excluded.
# - variant_02 account_not_in_list: a matching task on an account OUTSIDE
#   AccountList is excluded by the IN pill.
# - variant_03 zero_matches_empty_result: only a non-matching task exists ->
#   records [] -> create_list registers the EMPTY table from the node schema
#   -> query [] -> FVStatus [].
# - variant_04 empty_account_list: AccountList [] -> ids string '' ->
#   IN ('') matches nothing (a seeded matching decoy proves the emptiness is
#   the filter, not missing data).
#
# ROW-ORDER NOTE (LIVE-FALSIFIED assumption, re-pinned 2026-07-08): the
# final SELECT has NO ORDER BY -- the emitted order is SQLite's window sort
# by Account__c BYTE order, and live-assigned SF id suffixes are NOT
# lexicographically monotonic with creation order (live run: second-created
# ...Ve6hb... sorted before first-created ...VeAWg..., flipping the rows).
# expect.query_rows / expect.final_result.FVStatus are therefore compared as
# exact MULTISETS by the verifier (120183307/121086244 no-ORDER-BY
# precedent) with the order-preserving ____source row->result mapping still
# pinned positionally against the ACTUAL query rows; the variant_00
# return_result tool_expectation pins result_contains {FVStatus: "__ANY__"}
# (presence only) because _contains_subset list compare is positional.
#
# Backends: salesforce LIVE (benchmark-owned Account + Workato_Task__c
# records; cleanup deletes owned seeds in a finally block -- read-only
# recipe, but owned records must not leak); workato_smart_list /
# workato_variable / workato_recipe_function are Workato-internal
# in-process. TWIN of 103939956 (same 5-step skeleton, payload deltas only).

_STRUCTURE_PINS_JSON = r"""[
 {
  "keyword": "trigger",
  "number": 1,
  "as": "cf447f1d",
  "provider": "workato_recipe_function",
  "name": "execute",
  "skip": false,
  "input": {
   "parameters_schema_json": "[{\"name\":\"AccountList\",\"type\":\"array\",\"optional\":false,\"label\":\"Account list\",\"properties\":[{\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account ID\"},{\"name\":\"AccountName\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account name\"}],\"of\":\"object\"}]",
   "result_schema_json": "[{\"name\":\"FVStatus\",\"type\":\"array\",\"optional\":false,\"label\":\"FV status\",\"properties\":[{\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account ID\"},{\"name\":\"Status\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Status\"}],\"of\":\"object\"}]"
  }
 },
 {
  "keyword": "action",
  "number": 2,
  "as": "c6a252e3",
  "provider": "workato_variable",
  "name": "declare_variable",
  "skip": false,
  "input": {
   "variables": {
    "data": {
     "account_ids_string": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"cf447f1d\",\"path\":[\"parameters\",\"AccountList\"]}')&.pluck(\"AccountID\").join(\"','\")"
    },
    "schema": "[{\"control_type\":\"text\",\"label\":\"account_ids_string\",\"name\":\"account_ids_string\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"account_ids_string\"}}]"
   }
  }
 },
 {
  "keyword": "action",
  "number": 3,
  "as": "fcec7f45",
  "provider": "salesforce",
  "name": "search_sobjects_soql_v2",
  "skip": false,
  "input": {
   "limit": "2000",
   "output_schema": "[{\"name\":\"Account__c\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account ID\"},{\"name\":\"Status__c\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Status\"},{\"name\":\"CreatedDate\",\"type\":\"date_time\",\"optional\":false,\"label\":\"CreatedDate\",\"control_type\":\"date_time\",\"render_input\":\"date_time_conversion\",\"parse_output\":\"date_time_conversion\"}]",
   "query": "SELECT Account__c,\n       Status__c,\n       CreatedDate\n  FROM Workato_Task__c\n WHERE Activity_Type__c LIKE '%First Value - Direct%'\n   AND Account__c IN ('#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"c6a252e3\",\"path\":[\"account_ids_string\"]}')}')"
  }
 },
 {
  "keyword": "action",
  "number": 4,
  "as": "af71d26b",
  "provider": "workato_smart_list",
  "name": "create_list",
  "skip": false,
  "input": {
   "list_name": "FVStatus",
   "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"fcec7f45\",\"path\":[\"records\"]}')",
   "primary_index": "Account__c",
   "secondary_index": "CreatedDate"
  }
 },
 {
  "keyword": "action",
  "number": 5,
  "as": "65d5b389",
  "provider": "workato_smart_list",
  "name": "query_list",
  "skip": false,
  "input": {
   "col_sep": "comma",
   "csv": "false",
   "headers": "false",
   "output_schema_by": "index",
   "result_schema_json": "[{\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account ID\"},{\"name\":\"Status\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Status\"}]",
   "sql": "WITH all_fv_tasks AS (\nSELECT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"af71d26b\",\"path\":[\"columns\", \"Account__c\"]}')},\n       #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"af71d26b\",\"path\":[\"columns\", \"Status__c\"]}')},\n       ROW_NUMBER() OVER (PARTITION BY #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"af71d26b\",\"path\":[\"columns\", \"Account__c\"]}')} ORDER BY #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"af71d26b\",\"path\":[\"columns\", \"CreatedDate\"]}')} DESC) AS rn\n  FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"af71d26b\",\"path\":[\"list_name\"]}')}\n)   \n\nSELECT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"af71d26b\",\"path\":[\"columns\", \"Account__c\"]}')},\n       #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"af71d26b\",\"path\":[\"columns\", \"Status__c\"]}')}\n  FROM all_fv_tasks\n WHERE rn = 1"
  }
 },
 {
  "keyword": "action",
  "number": 6,
  "as": "656337a0",
  "provider": "workato_recipe_function",
  "name": "return_result",
  "skip": false,
  "input": {
   "result": {
    "FVStatus": {
     "AccountID": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"65d5b389\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"AccountID\"]}')}",
     "Status": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"65d5b389\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"Status\"]}')}",
     "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"65d5b389\",\"path\":[\"rows\"]}')}"
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


def validate_98802887(raw: dict[str, Any]) -> dict[str, Any]:
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


def seed_98802887(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_98802887(raw)
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
    state, seed_snapshot, refs = _provision_salesforce_phases(ctx, seed_in["salesforce"])
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
        "salesforce_live": state,
        "salesforce_seed_snapshot": seed_snapshot,
        "salesforce_ref_tokens": refs,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_98802887(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_98802887(raw)
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    if not seed["salesforce_live"].get("strict_soql_conditions"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires strict_soql_conditions in the live state "
            "(the infix LIKE and IN filters are strict-only operators)"
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
        # Required cleanup: owned Workato_Task__c + Account seed records must
        # not leak into later runs (the recipe itself only reads).
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
    result["verifier"] = verify_98802887(result)
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
    if not isinstance(section, dict) or sorted(section) != ["phases", "strict_soql_conditions"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce must be exactly "
            "{'strict_soql_conditions': true, 'phases': [...]}"
        )
    if section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true "
            "(infix LIKE / IN are strict-only operators)"
        )
    phases = section.get("phases")
    if not isinstance(phases, list) or not phases:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.phases must be a non-empty list of "
            "{'records': [...]} sections (phase order = CreatedDate order)"
        )
    for phase_index, phase in enumerate(phases):
        if not isinstance(phase, dict) or sorted(phase) != ["records"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} each salesforce phase must be exactly {{'records': [...]}}"
            )
        records = phase.get("records")
        if not isinstance(records, list) or not records:
            raise RuntimeError(f"recipe {RECIPE_ID} salesforce phase {phase_index} has no records")
        matching_accounts: set[str] = set()
        for record in records:
            if not isinstance(record, dict) or not str(record.get("ref") or "").strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} every seeded Salesforce record needs a 'ref': {record}"
                )
            fields = record.get("fields")
            if not isinstance(fields, dict) or not fields:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} every seeded record needs explicit fields: {record}"
                )
            sobject = str(record.get("sobject") or "")
            if sobject not in {"Account", TASK_SOBJECT}:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} seeded records must be Account or {TASK_SOBJECT}: {record}"
                )
            if not str(fields.get("Name") or "").strip():
                raise RuntimeError(
                    f"recipe {RECIPE_ID} every seeded record needs an explicit Name: {record}"
                )
            if sobject == TASK_SOBJECT:
                for key in ("Account__c", "Activity_Type__c", "Status__c"):
                    if not str(fields.get(key) or "").strip():
                        raise RuntimeError(
                            f"recipe {RECIPE_ID} {TASK_SOBJECT} seed must set {key}: {record}"
                        )
                if LIKE_LITERAL in str(fields.get("Activity_Type__c") or ""):
                    account = str(fields.get("Account__c") or "")
                    if account in matching_accounts:
                        raise RuntimeError(
                            f"recipe {RECIPE_ID} phase {phase_index} seeds two LIKE-matching "
                            f"tasks for account {account!r}: each matching task needs its OWN "
                            "phase (1s SF CreatedDate granularity; a tie would make the "
                            "ROW_NUMBER DESC partition nondeterministic)"
                        )
                    matching_accounts.add(account)


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
    if not isinstance(expect.get("query_rows"), list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.query_rows must pin the exact rn=1 output rows "
            "([] on the empty branch)"
        )
    final_result = expect.get("final_result")
    if not isinstance(final_result, dict) or not isinstance(final_result.get("FVStatus"), list):
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.final_result.FVStatus must pin the exact "
            "return_result payload ([] on the empty branch)"
        )


def _provision_salesforce_phases(
    ctx: RecipeContext, section: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    phases = section["phases"]
    state: dict[str, Any] | None = None
    merged_records: list[dict[str, Any]] = []
    refs: dict[str, str] = {}
    for phase_index, phase in enumerate(phases):
        if phase_index:
            time.sleep(CREATED_DATE_SPACING_SECONDS)
        phase_section: dict[str, Any] = {
            "strict_soql_conditions": True,
            "records": _replace_value(deepcopy(phase["records"]), refs),
        }
        try:
            provision = ctx.tools.call(
                "harness.salesforce.seed_records", {"salesforce": phase_section}
            )
            if not provision.get("ok"):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} Salesforce phase-{phase_index} seed failed: {provision}"
                )
        except Exception:
            if state is not None:
                # A later phase failed after earlier phases committed live
                # records: remove them before failing so a rerun never sees
                # stale benchmark state (123859779 precedent).
                from ..salesforce_live_harness import OwnedSalesforce

                OwnedSalesforce(state).delete_owned()
            raise
        refs.update(_phase_ref_tokens(phase["records"], provision))
        phase_state = deepcopy(provision["state"])
        merged_records.extend(
            deepcopy(list(((provision.get("snapshot") or {}).get("salesforce") or {}).get("records") or []))
        )
        if state is None:
            state = phase_state
        else:
            state["owned_records"] = list(state.get("owned_records") or []) + list(
                phase_state.get("owned_records") or []
            )
            state["read_only_records"] = list(state.get("read_only_records") or []) + list(
                phase_state.get("read_only_records") or []
            )
            state["strict_soql_conditions"] = bool(
                state.get("strict_soql_conditions") or phase_state.get("strict_soql_conditions")
            )
            state["expand_relationships"] = bool(
                state.get("expand_relationships") or phase_state.get("expand_relationships")
            )
    assert state is not None  # phases is validated non-empty
    return state, {"salesforce": {"records": merged_records}}, refs


def _phase_ref_tokens(
    phase_records: list[dict[str, Any]], provision: dict[str, Any]
) -> dict[str, str]:
    snapshot = provision.get("snapshot") if isinstance(provision.get("snapshot"), dict) else {}
    salesforce_snapshot = snapshot.get("salesforce") if isinstance(snapshot.get("salesforce"), dict) else {}
    live_ids = [
        str(record.get("id") or "")
        for record in salesforce_snapshot.get("records") or []
        if isinstance(record, dict) and record.get("id")
    ]
    seed_records = [record for record in phase_records if isinstance(record, dict)]
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
