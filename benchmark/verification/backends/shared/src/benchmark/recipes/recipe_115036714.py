from __future__ import annotations

import datetime
import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_115036714


RECIPE_ID = "115036714"
SEED_TYPE = "salesteam_hist_scd_maintenance_variant"
TRACK = "final_state"
TRIGGER_PROVIDER = "workato_recipe_function"
TRIGGER_NAME = "execute"
TRIGGER_AS = "f42a341c"
HIST_TABLE = "product.salesforce.salesteam_hist"
ROSTER_TABLE = "product.salesforce.user_roster"
HIST_COLUMNS = {"USER_ID": "string", "TEAM_NAME": "string", "DATE_FROM": "date", "DATE_TO": "date"}
ROSTER_COLUMNS = {"ID": "string", "SALES_TEAM__C": "string", "START_DATE__C": "date", "ISACTIVE": "boolean"}


_RAW_PIN_JSON = r"""{"as": "f42a341c", "block": [{"as": "", "block": [{"as": "9ce3bca8", "block": [], "input": {"variables": {"data": {"Database": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"f42a341c\",\"path\":[\"parameters\", \"database\"]}')}", "Schema": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"f42a341c\",\"path\":[\"parameters\", \"schema\"]}')}", "Table": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"f42a341c\",\"path\":[\"parameters\", \"table\"]}')}", "date_path": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"f42a341c\",\"path\":[\"parameters\", \"date_path\"]}')}"}, "schema": "[{\"name\":\"Database\",\"type\":\"string\",\"optional\":true,\"label\":\"Database\",\"details\":{\"real_name\":\"Database\"},\"control_type\":\"text\"},{\"name\":\"Schema\",\"type\":\"string\",\"optional\":true,\"label\":\"Schema\",\"details\":{\"real_name\":\"Schema\"},\"control_type\":\"text\"},{\"name\":\"Table\",\"type\":\"string\",\"optional\":true,\"label\":\"Table\",\"details\":{\"real_name\":\"Table\"},\"control_type\":\"text\"},{\"name\":\"date_path\",\"type\":\"string\",\"optional\":true,\"label\":\"Date Path\",\"details\":{\"real_name\":\"Date Path\"},\"control_type\":\"text\"}]"}}, "keyword": "action", "name": "declare_variable", "number": 3, "provider": "workato_variable", "skip": false}, {"as": "f9ade6bb", "block": [], "input": {"sql": "MERGE INTO #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"9ce3bca8\",\"path\":[\"Database\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"9ce3bca8\",\"path\":[\"Schema\"]}')}.SALESTEAM_HIST ST\nUSING (\n    SELECT U.ID, U.SALES_TEAM__C, U.START_DATE__C, U.ISACTIVE\n    FROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"9ce3bca8\",\"path\":[\"Database\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"9ce3bca8\",\"path\":[\"Schema\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"9ce3bca8\",\"path\":[\"Table\"]}')} U\n    WHERE U.SALES_TEAM__C IS NOT NULL\n) AS USERS\nON ST.USER_ID = USERS.ID AND ST.TEAM_NAME = USERS.SALES_TEAM__C\n\n-- HANDLES REPS WHO LEFT THE COMPANY\nWHEN MATCHED AND USERS.ISACTIVE = FALSE AND ST.DATE_TO IS NULL THEN\n    UPDATE SET DATE_TO = (CURRENT_DATE() - 1)\n\n-- HANDLES NEW USER\nWHEN NOT MATCHED THEN\n    INSERT (USER_ID, TEAM_NAME, DATE_FROM)\n    VALUES (USERS.ID, USERS.SALES_TEAM__C, IFF(USERS.START_DATE__C < CURRENT_DATE(), CURRENT_DATE(), USERS.START_DATE__C));", "update_only": "false"}, "keyword": "action", "name": "run_custom_sql", "number": 4, "provider": "snowflake", "skip": false}, {"as": "5515bc7a", "block": [], "input": {"output_schema": "[{\"name\":\"team_name\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Team name\"},{\"name\":\"user_id\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"User ID\"}]", "sql": "SELECT \nTEAM_NAME,\nUSER_ID\n\nFROM #{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"9ce3bca8\",\"path\":[\"Database\"]}')}.#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_variable\",\"line\":\"9ce3bca8\",\"path\":[\"Schema\"]}')}.SALESTEAM_HIST\nWHERE DATE_TO IS NULL\nQUALIFY ROW_NUMBER() OVER (PARTITION BY USER_ID ORDER BY DATE_FROM DESC) = 2", "update_only": "false"}, "keyword": "action", "name": "run_custom_sql", "number": 5, "provider": "snowflake", "skip": false}, {"as": "", "block": [{"as": "b7af4070", "block": [], "input": {"key_columns": "USER_ID\nTEAM_NAME", "rows": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5515bc7a\",\"path\":[\"rows\"]}')}", "date_to": "=today - 1.days", "team_name": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5515bc7a\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"team_name\"]}')}", "user_id": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5515bc7a\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"user_id\"]}')}"}, "table": "SALESFORCE.SALESTEAM_HIST"}, "keyword": "action", "name": "upsert_rows_batch", "number": 7, "provider": "snowflake", "skip": false}], "input": {"conditions": [{"lhs": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"5515bc7a\",\"path\":[\"rows\", {\"path_element_type\": \"size\"}]}')}", "operand": "greater_than", "rhs": "0"}], "operand": "and", "type": "compound"}, "keyword": "if", "name": "", "number": 6, "provider": "", "skip": false}, {"as": "4d75939b", "block": [], "input": {"result": {"successful": "true"}}, "keyword": "action", "name": "return_result", "number": 8, "provider": "workato_recipe_function", "skip": false}, {"as": "8db103e6", "block": [{"as": "e00bdfe3", "block": [], "input": {"result": {"error_message": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"workato_recipe_function\",\"line\":\"4d75939b\",\"path\":[\"result\", \"error_message\"]}')}", "successful": "false"}}, "keyword": "action", "name": "return_result", "number": 10, "provider": "workato_recipe_function", "skip": false}], "input": {"max_retry_count": "0", "retry_interval": "2"}, "keyword": "catch", "name": "", "number": 9, "provider": "", "skip": false}], "input": {}, "keyword": "try", "name": "", "number": 2, "provider": "", "skip": false}], "input": {"parameters_schema_json": "[{\"control_type\":\"text\",\"label\":\"Database\",\"name\":\"database\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Schema\",\"name\":\"schema\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Table\",\"name\":\"table\",\"type\":\"string\",\"optional\":false},{\"control_type\":\"text\",\"label\":\"Date path\",\"name\":\"date_path\",\"type\":\"string\",\"optional\":false}]", "result_schema_json": "[{\"control_type\":\"checkbox\",\"label\":\"Successful\",\"render_input\":{},\"parse_output\":{},\"name\":\"successful\",\"type\":\"boolean\",\"optional\":false,\"toggle_hint\":\"Select from option list\",\"toggle_field\":{\"label\":\"Successful\",\"control_type\":\"text\",\"toggle_hint\":\"Use custom value\",\"name\":\"successful\",\"type\":\"boolean\",\"optional\":false}},{\"control_type\":\"text\",\"label\":\"Error message\",\"name\":\"error_message\",\"type\":\"string\",\"optional\":true}]"}, "keyword": "trigger", "name": "execute", "number": 1, "provider": "workato_recipe_function", "skip": false}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    ("9ce3bca8", "workato_variable", "declare_variable"),
    ("f9ade6bb", "snowflake", "run_custom_sql"),
    ("5515bc7a", "snowflake", "run_custom_sql"),
    ("b7af4070", "snowflake", "upsert_rows_batch"),
    ("4d75939b", "workato_recipe_function", "return_result"),
    ("e00bdfe3", "workato_recipe_function", "return_result"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "snowflake.run_custom_sql",
    "snowflake.upsert_rows_batch",
    "workato_recipe_function.return_result",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "snowflake.upsert_rows_batch",
    "workato_recipe_function.return_result",
]
EXPECTED_PARAMETERS_SCHEMA_JSON = (
    '[{"control_type":"text","label":"Database","name":"database","type":"string","optional":false},'
    '{"control_type":"text","label":"Schema","name":"schema","type":"string","optional":false},'
    '{"control_type":"text","label":"Table","name":"table","type":"string","optional":false},'
    '{"control_type":"text","label":"Date path","name":"date_path","type":"string","optional":false}]'
)
_IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_115036714(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    schema_json = str((raw.get("input") or {}).get("parameters_schema_json") or "")
    if schema_json != EXPECTED_PARAMETERS_SCHEMA_JSON:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter schema changed")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
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


def seed_115036714(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_115036714(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    now = data.get("now")
    if not isinstance(now, str) or not now.strip():
        raise RuntimeError(f"recipe {RECIPE_ID} variant input must pin now ('=today - 1.days')")
    parsed_now = datetime.datetime.fromisoformat(now.replace("Z", "+00:00"))
    if parsed_now.tzinfo is None:
        raise RuntimeError(f"recipe {RECIPE_ID} now must carry an explicit UTC offset: {now!r}")
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    if sorted(seed_in.keys()) != ["snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the snowflake_live section; "
            f"got {sorted(seed_in.keys())}"
        )
    snowflake_seed = seed_in["snowflake_live"]
    _require_snowflake_section(snowflake_seed, parsed_now)
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    provision = ctx.tools.call("harness.snowflake_live.seed_tables", {"snowflake": snowflake_seed})
    if not provision.get("ok"):
        raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "now": now,
        "expect": deepcopy(expect),
        "snowflake_live": deepcopy(provision["state"]),
        "snowflake_seed_snapshot": deepcopy(provision.get("snapshot") or {}),
        "harness_tool_calls": ctx.tools.call_log(),
    }
    return attach_variant(out, ctx)


def run_115036714(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_115036714(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    if not str(seed.get("now") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing pinned now")
    initial_snapshot = _snapshot(ctx)
    raw_execution: dict[str, Any] | None = None
    final_snapshot: dict[str, Any] = {}
    snowflake_cleanup: dict[str, Any] | None = None
    try:
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx)
    finally:
        snowflake_cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
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
            "cleanup_response": {"snowflake_live": snowflake_cleanup},
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_115036714(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != ["parameters"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly the parameters object; "
            f"got {sorted(trigger.keys())}"
        )
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict) or sorted(parameters.keys()) != [
        "database",
        "date_path",
        "schema",
        "table",
    ]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters must carry exactly "
            "database/schema/table/date_path"
        )
    for key, value in parameters.items():
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"recipe {RECIPE_ID} trigger parameter {key} must be a non-empty string")
    if parameters["database"] != "product" or parameters["schema"] != "salesforce":
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters database/schema must be the literal "
            "'product'/'salesforce' (they interpolate into the registered 3-part seed keys)"
        )
    if not _IDENTIFIER_RE.fullmatch(parameters["table"]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameter table must be a lowercase identifier; "
            f"got {parameters['table']!r}"
        )


def _require_snowflake_section(section: Any, parsed_now: datetime.datetime) -> None:
    if not isinstance(section, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed.snowflake_live must be an object")
    unknown = sorted(set(section.keys()) - {"tables", "current_time"})
    if unknown:
        raise RuntimeError(f"recipe {RECIPE_ID} seed.snowflake_live has unknown keys: {unknown}")
    today_utc = parsed_now.astimezone(datetime.timezone.utc).date().isoformat()
    current_time = str(section.get("current_time") or "")
    if not current_time.startswith(today_utc):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.current_time must fall on the UTC date of "
            f"now ({today_utc}) so CURRENT_DATE()-1 == '=today - 1.days'; got {current_time!r}"
        )
    tables = section.get("tables")
    if not isinstance(tables, dict) or sorted(tables.keys()) != sorted([HIST_TABLE, ROSTER_TABLE]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{HIST_TABLE!r} and {ROSTER_TABLE!r} (the literal interpolated 3-part names)"
        )
    for table, expected_columns in ((HIST_TABLE, HIST_COLUMNS), (ROSTER_TABLE, ROSTER_COLUMNS)):
        spec = tables[table]
        if not isinstance(spec, dict):
            raise RuntimeError(f"recipe {RECIPE_ID} snowflake table {table} spec must be an object")
        if spec.get("columns") != expected_columns:
            raise RuntimeError(
                f"recipe {RECIPE_ID} snowflake table {table} must declare exactly the columns "
                f"{expected_columns}"
            )
        rows = spec.get("rows")
        if not isinstance(rows, list):
            raise RuntimeError(
                f"recipe {RECIPE_ID} snowflake table {table} must declare rows (may be empty)"
            )
        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                raise RuntimeError(f"recipe {RECIPE_ID} snowflake table {table} row {idx} must be an object")
            extra = set(row.keys()) - set(expected_columns.keys())
            if extra:
                raise RuntimeError(
                    f"recipe {RECIPE_ID} snowflake table {table} row {idx} uses undeclared "
                    f"columns: {sorted(extra)}"
                )
            for column, value in row.items():
                kind = expected_columns[column]
                if kind == "date":
                    if value is not None and not (
                        isinstance(value, str) and _DATE_RE.fullmatch(value)
                    ):
                        raise RuntimeError(
                            f"recipe {RECIPE_ID} snowflake table {table} row {idx} {column} "
                            f"must be YYYY-MM-DD or null; got {value!r}"
                        )
                elif kind == "boolean":
                    if not isinstance(value, bool):
                        raise RuntimeError(
                            f"recipe {RECIPE_ID} snowflake table {table} row {idx} {column} "
                            f"must be a boolean; got {value!r}"
                        )
                elif column == "SALES_TEAM__C":
                    # Nullable on purpose: the MERGE's USING filter
                    # (WHERE SALES_TEAM__C IS NOT NULL) is a reachable branch.
                    if value is not None and (not isinstance(value, str) or not value.strip()):
                        raise RuntimeError(
                            f"recipe {RECIPE_ID} snowflake table {table} row {idx} {column} "
                            f"must be a non-empty string or null; got {value!r}"
                        )
                else:
                    if not isinstance(value, str) or not value.strip():
                        raise RuntimeError(
                            f"recipe {RECIPE_ID} snowflake table {table} row {idx} {column} "
                            f"must be a non-empty string; got {value!r}"
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
    return ctx.tools.call("harness.snowflake.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
