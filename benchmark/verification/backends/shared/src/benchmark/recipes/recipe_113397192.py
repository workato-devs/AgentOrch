from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_113397192


RECIPE_ID = "113397192"
SEED_TYPE = "salesforce_recipe_function_workato_user_aggregates_variant"
TRACK = "live_salesforce_recipe_function_workato_user_aggregates"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "c70dbd3b"
WU_SOBJECT = "Workato_User__c"
SEARCH_SUM_AS = "568d7149"
SEARCH_MAX_AS = "8beef537"
SKIPPED_JOIN_AS = "e0c752d5"
CATCH_AS = "47d16f19"
STOP_AS = "3b83e78e"
STOP_NUMBER = 10
# Schema-in-seed contract (ensure_custom_field): Workato_User__c exists live
# (64106452 / 103986939 precedent; Account__c is a live Lookup(Account) and is
# NEVER re-created here -- lookups are deploy-time-only, 106603524 precedent).
# The five scalar columns the recipe reads are (re-)ensured + FLS-granted
# every run.
REQUIRED_SCHEMA = [
    {"sobject": WU_SOBJECT, "field": "Active_Recipes__c", "sf_type": "Number"},
    {"sobject": WU_SOBJECT, "field": "In_trial__c", "sf_type": "Checkbox"},
    {"sobject": WU_SOBJECT, "field": "Workato_Plan__c", "sf_type": "Text"},
    {"sobject": WU_SOBJECT, "field": "User_Account_Type__c", "sf_type": "Text"},
    {"sobject": WU_SOBJECT, "field": "Last_Login_Date__c", "sf_type": "Date"},
]
TRIGGER_ROW_KEYS = {"AccountID", "AccountName"}
_TOKEN_RE = re.compile(r"\$[A-Z][A-Z0-9_]*")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

# workato_recipe_function.execute (as c70dbd3b; parameters.AccountList[]
# {AccountID, AccountName}).
#   2  workato_variable.declare_variable a6142023:
#      account_ids_string = AccountList&.pluck("AccountID").join("','")
#      (probe-verified: 2 accounts -> "idA','idB"; [] -> ""; &. short-circuit)
#   TRY 3:
#     4  salesforce.search_sobjects_soql_v2 568d7149 (LIVE, limit 2000):
#        SELECT Account__c, SUM(Active_Recipes__c) active_recipes
#        FROM Workato_User__c WHERE IsDeleted = FALSE AND In_trial__c = FALSE
#        AND Workato_Plan__c != 'free' AND User_Account_Type__c LIKE
#        '%Production%' AND Account__c IN ('<ids>') GROUP BY Account__c
#        (strict SOQL: every seeded user declares read_fields ['IsDeleted'];
#        the Checkbox reads back a live boolean; LIKE '%Production%' is the
#        anchored engine's contains form)
#     5  workato_smart_list.create_list ed4a7726 'ActiveRecipes' from the
#        aggregate records (Workato-internal; trace-only observable -- the
#        list is created then never read because step 8 is skipped)
#     6  salesforce.search_sobjects_soql_v2 8beef537 (LIVE):
#        SELECT Account__c, MAX(Last_Login_Date__c) last_login_date ...
#        GROUP BY Account__c -- MAX over ISO dates compares lexicographically
#        (engine f9d83a51). SEMANTIC TRAP: this WHERE has NO
#        User_Account_Type__c leaf, so a non-Production user's later login
#        date CAN win MAX while the same user is excluded from the SUM.
#     7  workato_smart_list.create_list b5999f78 'LastLogin'
#     8  workato_smart_list.query_list e0c752d5 FULL OUTER JOIN -- skip:true,
#        traces as {skipped: true}, never executes
#     CATCH 9 (as 47d16f19, max_retry_count 3): the executor runs a SINGLE
#       attempt (no retry semantics -- execute_try catches once and runs the
#       catch block; documented engine behavior, trace is not tripled)
#       10 STOP 3b83e78e stop_with_error=true, stop_reason
#          '#{catch.type} : #{catch.message}' (engine-canonical type
#          'RawRecipeExecutionError'; trace stop rows carry no stop_reason --
#          the catch payload is pinned via step_outputs)
#   11 workato_recipe_function.return_result 61871b37:
#      result.WorkatoUsers ____source = 568d7149.records
#      {AccountID=Account__c, ProductionActiveRecipes=active_recipes};
#      LastLoginDate is declared in the result schema but NEVER mapped (the
#      MAX search feeds only the skipped join) -- rows carry exactly the two
#      mapped keys.
#
# Branch mapping (per benmark_rules -- control flow is try/catch + skip):
# - variant_00 two_accounts_summed_maxed: 2 on-list accounts; duplicate-
#   account users prove SUM; the Sandbox-type user proves the SUM/MAX WHERE
#   divergence (excluded from SUM, wins MAX); free-plan / in-trial /
#   off-list-account users prove each WHERE leaf.
# - variant_01 empty_account_list: AccountList [] -> IN ('') matches nothing
#   -> 0 aggregate rows -> row_count-0 lists -> WorkatoUsers [] (a seeded
#   decoy user proves the emptiness is the filter).
# - variant_02 catch_stop: sanctioned fault injection on 568d7149 -> catch ->
#   stop_with_error after 1 executed action.
#
# GROUP BY output order = owned-record iteration order (insertion-ordered).
# Backends: salesforce LIVE (cleanup deletes owned users + accounts in a
# finally block); workato_smart_list / workato_variable / recipe_function
# are Workato-internal in-process.

_STRUCTURE_PINS_JSON = r"""[{"as": "c70dbd3b", "input": {"parameters_schema_json": "[{\"name\":\"AccountList\",\"type\":\"array\",\"optional\":false,\"properties\":[{\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account ID\"},{\"name\":\"AccountName\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Account name\"}],\"of\":\"object\",\"label\":\"Account list\"}]", "result_schema_json": "[{\"name\":\"WorkatoUsers\",\"type\":\"array\",\"optional\":false,\"properties\":[{\"control_type\":\"text\",\"label\":\"Account ID\",\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"integer\",\"label\":\"Production active recipes\",\"parse_output\":\"integer_conversion\",\"name\":\"ProductionActiveRecipes\",\"type\":\"integer\",\"optional\":false},{\"name\":\"LastLoginDate\",\"type\":\"date_time\",\"optional\":true,\"label\":\"LastLoginDate\",\"control_type\":\"date\",\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\"}],\"of\":\"object\",\"label\":\"Workato users\"}]"}, "keyword": "trigger", "name": "execute", "number": 1, "provider": "workato_recipe_function", "skip": false}, {"as": "a6142023", "input": {"variables": {"data": {"account_ids_string": "=_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"c70dbd3b\",\"path\":[\"parameters\",\"AccountList\"]}')&.pluck(\"AccountID\").join(\"','\")"}, "schema": "[{\"control_type\":\"text\",\"label\":\"account_ids_string\",\"name\":\"account_ids_string\",\"type\":\"string\",\"optional\":true,\"details\":{\"real_name\":\"account_ids_string\"}}]"}}, "keyword": "action", "name": "declare_variable", "number": 2, "provider": "workato_variable", "skip": false}, {"as": null, "input": {}, "keyword": "try", "name": null, "number": 3, "provider": null, "skip": false}, {"as": "568d7149", "input": {"limit": "2000", "output_schema": "[{\"control_type\":\"text\",\"label\":\"Account ID\",\"name\":\"Account__c\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"integer\",\"label\":\"active_recipes\",\"parse_output\":\"integer_conversion\",\"name\":\"active_recipes\",\"type\":\"integer\",\"optional\":false}]", "query": "SELECT Account__c,\n       SUM(Active_Recipes__c) active_recipes\n  FROM Workato_User__c\n WHERE IsDeleted = FALSE\n   AND In_trial__c = FALSE \n   AND Workato_Plan__c != 'free'\n   AND User_Account_Type__c LIKE '%Production%'\n   AND Account__c IN ('#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"a6142023\",\"path\":[\"account_ids_string\"]}')}')\n GROUP BY Account__c   "}, "keyword": "action", "name": "search_sobjects_soql_v2", "number": 4, "provider": "salesforce", "skip": false}, {"as": "ed4a7726", "input": {"force": "true", "list_name": "ActiveRecipes", "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"568d7149\",\"path\":[\"records\"]}')", "primary_index": "Account__c"}, "keyword": "action", "name": "create_list", "number": 5, "provider": "workato_smart_list", "skip": false}, {"as": "8beef537", "input": {"limit": "2000", "output_schema": "[{\"control_type\":\"text\",\"label\":\"Account ID\",\"name\":\"Account__c\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"date\",\"label\":\"last_login_date\",\"name\":\"last_login_date\",\"type\":\"date_time\",\"optional\":false,\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\"}]", "query": "SELECT Account__c,\n\tMAX(Last_Login_Date__c) last_login_date\n  FROM Workato_User__c\n WHERE IsDeleted = FALSE\n   AND In_trial__c = FALSE \n   AND Workato_Plan__c != 'free'\n   AND Account__c IN ('#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"a6142023\",\"path\":[\"account_ids_string\"]}')}')\n GROUP BY Account__c"}, "keyword": "action", "name": "search_sobjects_soql_v2", "number": 6, "provider": "salesforce", "skip": false}, {"as": "b5999f78", "input": {"force": "true", "list_name": "LastLogin", "list_source": "=_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"8beef537\",\"path\":[\"records\"]}')", "primary_index": "Account__c"}, "keyword": "action", "name": "create_list", "number": 7, "provider": "workato_smart_list", "skip": false}, {"as": "e0c752d5", "input": {"col_sep": "comma", "csv": "false", "headers": "false", "output_schema_by": "index", "result_schema_json": "[{\"name\":\"AccountID\",\"type\":\"string\",\"optional\":false,\"label\":\"AccountID\",\"control_type\":\"text\"},{\"name\":\"ActiveRecipes\",\"type\":\"integer\",\"optional\":false,\"label\":\"ActiveRecipes\",\"control_type\":\"integer\",\"parse_output\":\"integer_conversion\"},{\"name\":\"LastLoginDate\",\"type\":\"date_time\",\"optional\":false,\"label\":\"LastLoginDate\",\"control_type\":\"date\",\"render_input\":\"date_conversion\",\"parse_output\":\"date_conversion\"}]", "sql": "SELECT #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"ed4a7726\",\"path\":[\"list_name\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"ed4a7726\",\"path\":[\"columns\", \"Account__c\"]}')},\n\t\t#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"ed4a7726\",\"path\":[\"list_name\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"ed4a7726\",\"path\":[\"columns\", \"active_recipes\"]}')},\n        #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b5999f78\",\"path\":[\"list_name\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b5999f78\",\"path\":[\"columns\", \"last_login_date\"]}')}\nFULL OUTER JOIN #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b5999f78\",\"path\":[\"list_name\"]}')}\n\t\tON #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"ed4a7726\",\"path\":[\"list_name\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"ed4a7726\",\"path\":[\"columns\", \"Account__c\"]}')} = #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b5999f78\",\"path\":[\"list_name\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\"b5999f78\",\"path\":[\"columns\", \"Account__c\"]}')}"}, "keyword": "action", "name": "query_list", "number": 8, "provider": "workato_smart_list", "skip": true}, {"as": "47d16f19", "input": {"max_retry_count": "3", "retry_interval": "10"}, "keyword": "catch", "name": null, "number": 9, "provider": null, "skip": false}, {"as": "3b83e78e", "input": {"stop_reason": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"47d16f19\",\"path\":[\"type\"]}')} : #{_dp('{\"pill_type\":\"output\",\"provider\":\"catch\",\"line\":\"47d16f19\",\"path\":[\"message\"]}')}", "stop_with_error": "true"}, "keyword": "stop", "name": null, "number": 10, "provider": null, "skip": false}, {"as": "61871b37", "input": {"result": {"WorkatoUsers": {"AccountID": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"568d7149\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"Account__c\"]}')}", "ProductionActiveRecipes": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"568d7149\",\"path\":[\"records\", {\"path_element_type\": \"current_item\"}, \"active_recipes\"]}')}", "____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"salesforce\",\"line\":\"568d7149\",\"path\":[\"records\"]}')}"}}}, "keyword": "action", "name": "return_result", "number": 11, "provider": "workato_recipe_function", "skip": false}]"""

STRUCTURE_PINS: list[dict] = json.loads(_STRUCTURE_PINS_JSON)

EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "salesforce.search_records",
    "workato_smart_list.create_list",
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
    "create_lists",
    "final_result",
    "stopped",
    "catch",
)
OPTIONAL_EXPECT_KEYS = {"stop_step_as", "stop_step_number"}


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
        pin["source"] = node.get("source")
    if isinstance(node.get("filter"), dict):
        pin["filter"] = node["filter"]
    out = [pin]
    for child in node.get("block") or []:
        if isinstance(child, dict):
            out.extend(_structure(child))
    return out


def validate_113397192(raw: dict[str, Any]) -> dict[str, Any]:
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
    actions = [pin for pin in actual if pin["keyword"] == "action" and not pin["skip"]]
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


def seed_113397192(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_113397192(raw)
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
    expect = data.get("expect")
    _require_expect_shape(expect)
    force = data.get("force_action_error")
    if force is not None:
        if not isinstance(force, dict) or str(force.get("step_as") or "") != SEARCH_SUM_AS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} fault injection is sanctioned only on step "
                f"{SEARCH_SUM_AS} (inside the try): {force!r}"
            )
        if expect.get("stopped") is not True:
            raise RuntimeError(
                f"recipe {RECIPE_ID} a forced error must pin expect.stopped true "
                "(catch -> stop_with_error)"
            )
    elif expect.get("stopped") is not False:
        raise RuntimeError(
            f"recipe {RECIPE_ID} the catch/stop is only reachable via sanctioned fault "
            "injection; happy variants must pin expect.stopped false"
        )
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
        # Account ids, threaded via $REF_ID tokens (106603524 precedent).
        "expect": resolved_expect,
        "salesforce_live": deepcopy(provision["state"]),
        "salesforce_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "salesforce_ref_tokens": refs,
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_113397192(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_113397192(raw)
    if not isinstance(seed.get("salesforce_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing salesforce_live state")
    if not seed["salesforce_live"].get("strict_soql_conditions"):
        raise RuntimeError(
            f"recipe {RECIPE_ID} requires strict_soql_conditions in the live state "
            "(IsDeleted = FALSE / boolean = FALSE / != / LIKE / IN are strict-only)"
        )
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    details: dict[str, Any] = {
        "seed_type": seed.get("seed_type"),
        "trigger": seed.get("trigger"),
        "track": seed.get("track"),
        "expect": expect,
        "force_action_error": deepcopy(seed.get("force_action_error"))
        if isinstance(seed.get("force_action_error"), dict)
        else None,
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
        # Required cleanup: owned Workato_User__c + Account seed records must
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
    result["verifier"] = verify_113397192(result)
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
    if section.get("strict_soql_conditions") is not True:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.strict_soql_conditions must be true "
            "(IsDeleted = FALSE / In_trial__c = FALSE / != / LIKE / IN are strict-only)"
        )
    if section.get("schema") != REQUIRED_SCHEMA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.salesforce.schema must declare exactly "
            f"{json.dumps(REQUIRED_SCHEMA)}"
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
        if sobject not in {"Account", WU_SOBJECT}:
            raise RuntimeError(
                f"recipe {RECIPE_ID} seeded records must be Account or {WU_SOBJECT}: {record}"
            )
        if not str(fields.get("Name") or "").strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} every seeded record needs an explicit Name: {record}"
            )
        if sobject == WU_SOBJECT:
            if record.get("read_fields") != ["IsDeleted"]:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} every {WU_SOBJECT} seed must declare read_fields "
                    "['IsDeleted'] (the strict 'IsDeleted = FALSE' leaf evaluates the "
                    "live read-back -- 118905064 precedent): "
                    f"{record}"
                )
            for key in ("Account__c", "Workato_Plan__c", "User_Account_Type__c"):
                if not str(fields.get(key) or "").strip():
                    raise RuntimeError(
                        f"recipe {RECIPE_ID} {WU_SOBJECT} seed must set {key}: {record}"
                    )
            if not isinstance(fields.get("In_trial__c"), bool):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {WU_SOBJECT} seed must set In_trial__c as an explicit "
                    f"boolean (the strict 'In_trial__c = FALSE' leaf): {record}"
                )
            if not isinstance(fields.get("Active_Recipes__c"), (int, float)) or isinstance(
                fields.get("Active_Recipes__c"), bool
            ):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {WU_SOBJECT} seed must set Active_Recipes__c as an "
                    f"explicit number (SUM input): {record}"
                )
            if not isinstance(fields.get("Last_Login_Date__c"), str) or not _DATE_RE.fullmatch(
                fields["Last_Login_Date__c"]
            ):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} {WU_SOBJECT} seed must set Last_Login_Date__c as an "
                    f"ISO date (MAX compares the read-back form lexicographically): {record}"
                )


def _require_expect_shape(expect: Any) -> None:
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
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must pin every expect.tools entry"
        )
    unknown_tools = sorted(set(tools) - set(ALLOWED_TOOLS))
    if unknown_tools:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.tools has unknown tools: {unknown_tools}")
    create_lists = expect.get("create_lists")
    if not isinstance(create_lists, list):
        raise RuntimeError(f"recipe {RECIPE_ID} expect.create_lists must be a list")
    if expect.get("stopped") is True:
        if expect.get("final_result") is not None or create_lists:
            raise RuntimeError(
                f"recipe {RECIPE_ID} the catch path never reaches the create/return steps: "
                "final_result must be null and create_lists []"
            )
        catch = expect.get("catch")
        if not isinstance(catch, dict) or set(catch) != {
            "type", "message", "adapter", "action", "line_number"
        }:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must pin the full connector catch payload"
            )
        if str(expect.get("stop_step_as") or "") != STOP_AS or expect.get("stop_step_number") != STOP_NUMBER:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must pin stop_step_as {STOP_AS!r} / "
                f"stop_step_number {STOP_NUMBER}"
            )
    elif expect.get("stopped") is False:
        if expect.get("catch") is not None:
            raise RuntimeError(f"recipe {RECIPE_ID} happy variants must pin expect.catch null")
        if len(create_lists) != 2:
            raise RuntimeError(
                f"recipe {RECIPE_ID} happy variants create exactly the ActiveRecipes and "
                "LastLogin lists (rows pinned; [] rows on the empty branch)"
            )
        for entry in create_lists:
            if (
                not isinstance(entry, dict)
                or set(entry) != {"list_name", "row_count", "rows"}
                or not isinstance(entry.get("rows"), list)
            ):
                raise RuntimeError(
                    f"recipe {RECIPE_ID} every create_lists entry must pin "
                    f"{{list_name, row_count, rows}}: {entry}"
                )
        if not isinstance(expect.get("final_result"), dict) or not isinstance(
            expect["final_result"].get("WorkatoUsers"), list
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} happy variants must pin expect.final_result.WorkatoUsers "
                "(the exact return_result payload; [] on the empty branch)"
            )
        for row in expect["final_result"]["WorkatoUsers"]:
            if not isinstance(row, dict) or set(row) != {"AccountID", "ProductionActiveRecipes"}:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} WorkatoUsers rows carry exactly AccountID + "
                    "ProductionActiveRecipes (LastLoginDate is declared in the result schema "
                    f"but never mapped): {row}"
                )
    else:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.stopped must be true or false")


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
        raise RuntimeError(
            f"recipe {RECIPE_ID} unresolved seed tokens remain: {sorted(set(leftover))}"
        )


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
