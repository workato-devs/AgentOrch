from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_86565537


RECIPE_ID = "86565537"
SEED_TYPE = "sdr_ae_routing_smart_list_variant"
TRACK = "sdr_ae_routing_smart_list"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "8546a8b1"
# SDR->AE routing recipe function (trigger as 8546a8b1, parameters {territory}):
# TRY {
#   3x lookup_table.get_entries -> 3x smart lists from CSV plucks:
#     'General/Group Territory to AE Mapping' (id, general_territory, group,
#     assignee_email), 'AE Status' (email, isActive), 'Detailed Territory to
#     Group Mapping' (id, detailed_territory, group)
#   query bbecc363 (step 9): general-territory JOIN AE Status; result schema
#     renames POSITIONALLY (no output_schema_by): ae_email <- assignee_email,
#     group <- group, ae_status <- isActive
#   IF 10 (rows.size == 0):
#     query 7837a714 (step 11): detailed-territory scalar subquery + NOT LIKE
#       'TBH' + IS NOT NULL + isActive='TRUE'; create 'AE Assignees' (force)
#   ELSE IF 14 (OR: first row ae_email=='TBH' / blank / ae_status is_not_true;
#              current_item outside foreach = FIRST row):
#     query 0f6b11d2 (step 15): group re-query keyed on the FIRST bbecc363
#       row's group VALUE ('#{rows.current_item.group}' inside single quotes);
#       create 'AE Assignees' (force)
#   ELSE:
#     declare territory_assigned=true (the ONLY path that declares it);
#     create 'AE Assignees' from bbecc363.rows.pluck('ae_email').to_csv (force)
#   query 3c6fecda (step 20): SELECT * FROM "AE Assignees"
#   IF 21 (territory contains 'Emerging'):
#     query f22deb44 (step 22): Emerging-wide JOIN (LIKE '%Emerging%' AND
#       '%workato.com%' AND '%TRUE%'); return step 23 over f22deb44.rows
#   ELSE: return step 25 over 3c6fecda.rows
# } CATCH (7e1b2a0f, max_retry 0): return step 27 {data:{email:nil},
#   territory_assigned:"false" (STRING — the other paths return booleans)}
#
# territory_assigned resolves via .is_true? on the variable: True only on the
# declare path, False (undeclared -> nil.is_true?) everywhere else.
# All backends are Workato-internal mocks (lookup tables + smart lists +
# variables + recipe-function return): no live seeding, no cleanup (per-run
# isolated state; 'AE Assignees' is force-overwritten inside the run).
LOOKUP_TABLES: list[tuple[str, str, str]] = [
    # (step as, lookup_table_id, display name)
    ("1a060163", "3204267", "[SDR-AE Routing] General Territory - Grouping - Email Mapping"),
    ("2aa56964", "3204265", "[SDR-AE Routing] - Enable AE Routing"),
    ("4b9a6b7b", "3204266", "[SDR-AE Routing] Detailed Territory - Group Mapping"),
]
LOOKUP_TABLE_IDS: list[str] = [table_id for _, table_id, _ in LOOKUP_TABLES]
TRIGGER_PARAMETERS_SCHEMA_JSON = (
    '[{"name":"territory","type":"string","optional":false,"control_type":"text"}]'
)
TRIGGER_RESULT_SCHEMA_JSON = (
    '[{"name":"data","type":"array","of":"object","label":"Data","optional":false,'
    '"properties":[{"control_type":"text","label":"Email","name":"email","type":"string","optional":false}]},'
    '{"name":"territory_assigned","type":"boolean","optional":false}]'
)


def _sl_col(line: str, col: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\""
        + line + "\",\"path\":[\"columns\", \"" + col + "\"]}')}"
    )


def _sl_list(line: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\""
        + line + "\",\"path\":[\"list_name\"]}')}"
    )


def _sl_rows(line: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\""
        + line + "\",\"path\":[\"rows\"]}')}"
    )


def _sl_rows_current(line: str, field: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\""
        + line + "\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"" + field + "\"]}')}"
    )


def _sl_rows_size(line: str) -> str:
    return (
        "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_smart_list\",\"line\":\""
        + line + "\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}"
    )


TERRITORY_PILL = (
    "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\","
    "\"line\":\"8546a8b1\",\"path\":[\"parameters\", \"territory\"]}')}"
)
_A = _sl_col("f190fcd5", "assignee_email")
_B = _sl_col("f190fcd5", "group")
_C = _sl_col("56715181", "isActive")
_D = _sl_list("f190fcd5")
_E = _sl_list("56715181")
_F = _sl_col("56715181", "email")
_G = _sl_col("f190fcd5", "general_territory")
_H = _sl_col("4d1dd4de", "group")
_I = _sl_list("4d1dd4de")
_J = _sl_col("4d1dd4de", "detailed_territory")

# The five query SQL templates VERBATIM (incl. the raw recipe's double spaces).
SQL_BBECC363 = (
    "SELECT " + _A + ", " + _B + ", aES." + _C
    + " FROM " + _D + " JOIN " + _E + " aES ON aES." + _F + " =  " + _A
    + " WHERE " + _G + " = '" + TERRITORY_PILL + "'"
)
SQL_7837A714 = (
    "SELECT gGTAEM." + _A + " FROM " + _D + " gGTAEM JOIN " + _E
    + " aES ON aES." + _F + " = gGTAEM." + _A
    + "  WHERE gGTAEM." + _B + " = (SELECT " + _H + " FROM " + _I
    + "  WHERE " + _J + " = '" + TERRITORY_PILL + "' LIMIT 1)"
    + " AND gGTAEM." + _A + " NOT LIKE 'TBH'"
    + " AND gGTAEM." + _A + " IS NOT NULL AND aES." + _C + " = 'TRUE'"
)
SQL_0F6B11D2 = (
    "SELECT gGTAEM." + _A + " FROM " + _D + " gGTAEM JOIN " + _E
    + " aES ON aES." + _F + " = gGTAEM." + _A
    + " WHERE gGTAEM." + _B + " = '" + _sl_rows_current("bbecc363", "group") + "'"
    + " AND gGTAEM." + _A + " NOT LIKE 'TBH'"
    + " AND gGTAEM." + _A + " IS NOT NULL AND aES." + _C + " = 'TRUE'"
)
SQL_3C6FECDA = 'SELECT * FROM "AE Assignees"'
SQL_F22DEB44 = (
    "SELECT m." + _A + ", m." + _B + ", aES." + _C
    + " FROM " + _D + " m JOIN " + _E + " aES ON aES." + _F + " =  m." + _A
    + " WHERE m." + _B + " LIKE '%Emerging%' AND m." + _A
    + " LIKE '%workato.com%' AND aES." + _C + " LIKE '%TRUE%'"
)

GENERAL_CSV_SCHEMA_JSON = (
    '[{"name":"id","type":"string","optional":false,"control_type":"text"},'
    '{"name":"general_territory","type":"string","optional":false,"control_type":"text"},'
    '{"name":"group","type":"string","optional":false,"control_type":"text"},'
    '{"name":"assignee_email","type":"string","optional":false,"control_type":"text"}]'
)
STATUS_CSV_SCHEMA_JSON = (
    '[{"name":"email","type":"string","optional":false,"control_type":"text"},'
    '{"name":"isActive","type":"string","optional":false,"control_type":"text"}]'
)
DETAILED_CSV_SCHEMA_JSON = (
    '[{"name":"id","type":"string","optional":false,"control_type":"text"},'
    '{"name":"detailed_territory","type":"string","optional":false,"control_type":"text"},'
    '{"name":"group","type":"string","optional":false,"control_type":"text"}]'
)
ASSIGNEES_CSV_SCHEMA_JSON = (
    '[{"name":"ae_email","type":"string","optional":false,"control_type":"text"}]'
)
QUERY_RESULT_SCHEMAS: dict[str, str] = {
    "bbecc363": (
        '[{"name":"ae_email","type":"string","optional":false,"control_type":"text"},'
        '{"name":"group","type":"string","optional":false,"control_type":"text"},'
        '{"name":"ae_status","type":"boolean","optional":false}]'
    ),
    "7837a714": ASSIGNEES_CSV_SCHEMA_JSON,
    "0f6b11d2": ASSIGNEES_CSV_SCHEMA_JSON,
    "3c6fecda": ASSIGNEES_CSV_SCHEMA_JSON,
    "f22deb44": (
        '[{"name":"ae_email","type":"string","optional":false,"control_type":"text"},'
        '{"name":"group","type":"string","optional":false,"control_type":"text"},'
        '{"name":"ae_status","type":"boolean","optional":false}]'
    ),
}
QUERY_SQLS: dict[str, str] = {
    "bbecc363": SQL_BBECC363,
    "7837a714": SQL_7837A714,
    "0f6b11d2": SQL_0F6B11D2,
    "3c6fecda": SQL_3C6FECDA,
    "f22deb44": SQL_F22DEB44,
}
# output_schema_by is set (to "index") ONLY on 0f6b11d2 and f22deb44 in the raw
# recipe; bbecc363's 3-column rename relies on Workato's positional mapping of
# headers=false query results, which the executor must honor without the flag.
QUERY_OUTPUT_SCHEMA_BY: dict[str, str] = {
    "bbecc363": "",
    "7837a714": "",
    "0f6b11d2": "index",
    "3c6fecda": "",
    "f22deb44": "index",
}
CSV_STEPS: dict[str, dict[str, str]] = {
    "f190fcd5": {
        "list_name": "General/Group Territory to AE Mapping",
        "csv_schema_json": GENERAL_CSV_SCHEMA_JSON,
        "list_source": "=_('data.lookup_table.1a060163.entries')"
                       ".pluck(['entry','col1'],['entry','col2'],['entry','col3'],['entry','col4']).to_csv",
        "force": "",
    },
    "56715181": {
        "list_name": "AE Status",
        "csv_schema_json": STATUS_CSV_SCHEMA_JSON,
        "list_source": "=_('data.lookup_table.2aa56964.entries').pluck(['entry','col1'],['entry','col2']).to_csv",
        "force": "",
    },
    "4d1dd4de": {
        "list_name": "Detailed Territory to Group Mapping",
        "csv_schema_json": DETAILED_CSV_SCHEMA_JSON,
        "list_source": "=_('data.lookup_table.4b9a6b7b.entries')"
                       ".pluck(['entry','col1'],['entry','col2'],['entry','col3']).to_csv",
        "force": "",
    },
    "20c6f659": {
        "list_name": "AE Assignees",
        "csv_schema_json": ASSIGNEES_CSV_SCHEMA_JSON,
        "list_source": "=_('data.workato_smart_list.bbecc363.rows').pluck('ae_email').to_csv",
        "force": "true",
    },
}
CREATE_LIST_STEPS: dict[str, str] = {
    "4172f000": "=_('data.workato_smart_list.7837a714.rows')",
    "513ba50a": "=_('data.workato_smart_list.0f6b11d2.rows')",
}
DECLARE_VARIABLES_INPUT: dict[str, Any] = {
    "data": {"territory_assigned": "true"},
    "schema": '[{"name":"territory_assigned","type":"boolean","optional":true,'
              '"label":"territory_assigned","control_type":"checkbox"}]',
}
TERRITORY_ASSIGNED_FORMULA = "=_('data.workato_variable.20e05498.territory_assigned').is_true?"
RETURN_EMERGING_RESULT: dict[str, Any] = {
    "data": {
        "____source": _sl_rows("f22deb44"),
        "email": _sl_rows_current("f22deb44", "ae_email"),
    },
    "territory_assigned": TERRITORY_ASSIGNED_FORMULA,
}
RETURN_ELSE_RESULT: dict[str, Any] = {
    "data": {
        "____source": _sl_rows("3c6fecda"),
        "email": _sl_rows_current("3c6fecda", "ae_email"),
    },
    "territory_assigned": TERRITORY_ASSIGNED_FORMULA,
}
RETURN_CATCH_RESULT: dict[str, Any] = {
    "data": {"email": "=nil"},
    "territory_assigned": "false",
}
EXPECTED_IFS: list[tuple[int, str, list[tuple[str, str, str]]]] = [
    (10, "and", [(_sl_rows_size("bbecc363"), "equals_to", "0")]),
    (14, "or", [
        (_sl_rows_current("bbecc363", "ae_email"), "equals_to", "TBH"),
        (_sl_rows_current("bbecc363", "ae_email"), "blank", ""),
        (_sl_rows_current("bbecc363", "ae_status"), "is_not_true", ""),
    ]),
    (21, "and", [(TERRITORY_PILL, "contains", "Emerging")]),
]
EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("lookup_table", "get_entries", "1a060163"),
    ("workato_smart_list", "create_list_from_csv", "f190fcd5"),
    ("lookup_table", "get_entries", "2aa56964"),
    ("workato_smart_list", "create_list_from_csv", "56715181"),
    ("lookup_table", "get_entries", "4b9a6b7b"),
    ("workato_smart_list", "create_list_from_csv", "4d1dd4de"),
    ("workato_smart_list", "query_list", "bbecc363"),
    ("workato_smart_list", "query_list", "7837a714"),
    ("workato_smart_list", "create_list", "4172f000"),
    ("workato_smart_list", "query_list", "0f6b11d2"),
    ("workato_smart_list", "create_list", "513ba50a"),
    ("workato_variable", "declare_variable", "20e05498"),
    ("workato_smart_list", "create_list_from_csv", "20c6f659"),
    ("workato_smart_list", "query_list", "3c6fecda"),
    ("workato_smart_list", "query_list", "f22deb44"),
    ("workato_recipe_function", "return_result", "9b2531e9"),
    ("workato_recipe_function", "return_result", "8f4b743a"),
    ("workato_recipe_function", "return_result", "c1ce9cf3"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "lookup_table.get_entries",
    "workato_smart_list.create_list_from_csv",
    "workato_smart_list.query_list",
    "workato_smart_list.create_list",
    "workato_runtime.declare_variable",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "lookup_table.get_entries",
    "workato_recipe_function.return_result",
]


def validate_86565537(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step alias changed")
    trigger_in = raw.get("input") if isinstance(raw.get("input"), dict) else {}
    if str(trigger_in.get("parameters_schema_json") or "") != TRIGGER_PARAMETERS_SCHEMA_JSON:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters schema changed")
    if str(trigger_in.get("result_schema_json") or "") != TRIGGER_RESULT_SCHEMA_JSON:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger result schema changed")

    actions = _collect_actions(raw)
    actual = [(a.get("provider"), a.get("name"), a.get("as")) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    by_as = {str(a.get("as") or ""): a for a in actions}

    for step_as, table_id, display_name in LOOKUP_TABLES:
        node = by_as[step_as]
        picked = node.get("dynamicPickListSelection") if isinstance(node.get("dynamicPickListSelection"), dict) else {}
        if str(_input(node).get("lookup_table_id") or "") != table_id:
            raise RuntimeError(f"recipe {RECIPE_ID} lookup table id changed on {step_as}: {_input(node)}")
        if str(picked.get("lookup_table_id") or "") != display_name:
            raise RuntimeError(f"recipe {RECIPE_ID} lookup table display name changed on {step_as}")

    for step_as, pins in CSV_STEPS.items():
        node_in = _input(by_as[step_as])
        if (
            str(node_in.get("list_name") or "") != pins["list_name"]
            or str(node_in.get("csv_schema_json") or "") != pins["csv_schema_json"]
            or str(node_in.get("list_source") or "") != pins["list_source"]
            or str(node_in.get("headers") or "") != "false"
            or str(node_in.get("col_sep") or "") != "comma"
            or str(node_in.get("force") or "") != pins["force"]
        ):
            raise RuntimeError(f"recipe {RECIPE_ID} create_list_from_csv {step_as} changed: {node_in}")
    if str(_input(by_as["20c6f659"]).get("primary_index") or "") != "ae_email":
        raise RuntimeError(f"recipe {RECIPE_ID} AE Assignees CSV primary index changed")

    for step_as, list_source in CREATE_LIST_STEPS.items():
        node_in = _input(by_as[step_as])
        if (
            str(node_in.get("list_name") or "") != "AE Assignees"
            or str(node_in.get("list_source") or "") != list_source
            or str(node_in.get("force") or "") != "true"
            or str(node_in.get("primary_index") or "") != "ae_email"
        ):
            raise RuntimeError(f"recipe {RECIPE_ID} create_list {step_as} changed: {node_in}")

    for step_as, sql in QUERY_SQLS.items():
        node_in = _input(by_as[step_as])
        if str(node_in.get("sql") or "") != sql:
            raise RuntimeError(f"recipe {RECIPE_ID} query {step_as} SQL changed: {node_in.get('sql')}")
        if str(node_in.get("result_schema_json") or "") != QUERY_RESULT_SCHEMAS[step_as]:
            raise RuntimeError(f"recipe {RECIPE_ID} query {step_as} result schema changed")
        if str(node_in.get("output_schema_by") or "") != QUERY_OUTPUT_SCHEMA_BY[step_as]:
            raise RuntimeError(f"recipe {RECIPE_ID} query {step_as} output_schema_by changed")
        if (
            str(node_in.get("csv") or "") != "false"
            or str(node_in.get("headers") or "") != "false"
            or str(node_in.get("col_sep") or "") != "comma"
        ):
            raise RuntimeError(f"recipe {RECIPE_ID} query {step_as} options changed: {node_in}")

    if _input(by_as["20e05498"]).get("variables") != DECLARE_VARIABLES_INPUT:
        raise RuntimeError(f"recipe {RECIPE_ID} territory_assigned declaration changed")
    if _input(by_as["9b2531e9"]).get("result") != RETURN_EMERGING_RESULT:
        raise RuntimeError(f"recipe {RECIPE_ID} Emerging return_result changed")
    if _input(by_as["8f4b743a"]).get("result") != RETURN_ELSE_RESULT:
        raise RuntimeError(f"recipe {RECIPE_ID} else-path return_result changed")
    if _input(by_as["c1ce9cf3"]).get("result") != RETURN_CATCH_RESULT:
        raise RuntimeError(f"recipe {RECIPE_ID} catch return_result changed")

    ifs = _collect_ifs(raw)
    if ifs != EXPECTED_IFS:
        raise RuntimeError(f"recipe {RECIPE_ID} IF conditions changed: {ifs}")

    catch = _find_catch(raw)
    if (
        catch is None
        or str(catch.get("as") or "") != "7e1b2a0f"
        or str(_input(catch).get("max_retry_count") or "") != "0"
        or str(_input(catch).get("retry_interval") or "") != "2"
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} try/catch structure changed")

    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
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


def seed_86565537(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_86565537(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict) or sorted(parameters.keys()) != ["territory"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must carry exactly ['territory']; got "
            f"{sorted(parameters.keys()) if isinstance(parameters, dict) else parameters}"
        )
    if not str(parameters.get("territory") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter 'territory' must be a non-empty string")
    seed_in = data.get("seed")
    lookup_seed = seed_in.get("lookup_table") if isinstance(seed_in, dict) else None
    tables = lookup_seed.get("tables") if isinstance(lookup_seed, dict) else None
    if not isinstance(tables, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed must define lookup_table.tables explicitly")
    if sorted(tables.keys()) != sorted(LOOKUP_TABLE_IDS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare ALL THREE routing lookup tables "
            f"{LOOKUP_TABLE_IDS} (empty tables still declare an explicit empty list); "
            f"got {sorted(tables.keys())}"
        )
    for table_id, rows in tables.items():
        if not isinstance(rows, list):
            raise RuntimeError(f"recipe {RECIPE_ID} lookup table {table_id} rows must be a list")
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track"),
        "raw_validation": validation,
        "expect": deepcopy(expect),
        "lookup_table": deepcopy(lookup_seed),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_86565537(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_86565537(raw)
    if not isinstance(seed.get("lookup_table"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing lookup_table section")
    initial_snapshot = _snapshot(ctx)
    raw_execution = execute_raw_recipe(raw, seed, ctx)
    final_snapshot = _snapshot(ctx)
    result = recipe_result(
        recipe_id=RECIPE_ID,
        ok=True,
        track=TRACK,
        ctx=ctx,
        details={
            "seed_type": seed.get("seed_type"),
            "trigger": seed.get("trigger"),
            "track": seed.get("track"),
            "expect": seed.get("expect") if isinstance(seed.get("expect"), dict) else {},
            "raw_validation": validation,
            "raw_execution": raw_execution,
            "expected_raw_tools": EXPECTED_RAW_TOOLS,
            "initial_snapshot": initial_snapshot,
            "final_snapshot": final_snapshot,
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_86565537(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _input(node: dict[str, Any]) -> dict[str, Any]:
    raw = node.get("input")
    return raw if isinstance(raw, dict) else {}


def _collect_actions(node: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "action" and not child.get("skip"):
            found.append(child)
        found.extend(_collect_actions(child))
    return found


def _collect_ifs(node: dict[str, Any]) -> list[tuple[int, str, list[tuple[str, str, str]]]]:
    found: list[tuple[int, str, list[tuple[str, str, str]]]] = []
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "if":
            conditions = [
                (str(c.get("lhs") or ""), str(c.get("operand") or ""), str(c.get("rhs") or ""))
                for c in (_input(child).get("conditions") or [])
                if isinstance(c, dict)
            ]
            found.append((child.get("number"), str(_input(child).get("operand") or ""), conditions))
        found.extend(_collect_ifs(child))
    return found


def _find_catch(node: dict[str, Any]) -> dict[str, Any] | None:
    for child in node.get("block") or []:
        if not isinstance(child, dict):
            continue
        if child.get("keyword") == "catch":
            return child
        nested = _find_catch(child)
        if nested is not None:
            return nested
    return None


def _snapshot(ctx: RecipeContext) -> dict[str, Any]:
    return ctx.tools.call("harness.lookup_table.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
