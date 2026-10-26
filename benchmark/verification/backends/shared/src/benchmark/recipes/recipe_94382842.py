from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_94382842


RECIPE_ID = "94382842"
SEED_TYPE = "slack_dynamic_menu_freshdesk_company_names_variant"
TRACK = "live_snowflake_slack_dynamic_menu"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "dynamic_menu"
TRIGGER_AS = "bd069835"
DYNAMIC_MENU_NAME = "List of Freshdesk Company Names"
DECLARE_STEP_AS = "36bf1d17"
SEARCH_STEP_AS = "85f2b107"
MENU_STEP_AS = "aab14ffe"
UPDATE_STEP_AS = "d719ef1b"
SNOWFLAKE_TABLE = "WORKATO_BUSINESS_SYSTEMS.FRESHDESK.product_support_ticket_export"
TABLE_COLUMNS = {"COMPANY_NAME": "string"}


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "slack_bot", "name": "dynamic_menu", "as": "bd069835", "skip": false, "input": {"dynamic_menu_name": "List of Freshdesk Company Names", "parameters": "[\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Company\",\n    \"name\": \"company_name\",\n    \"type\": \"string\",\n    \"optional\": true\n  },\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Report\",\n    \"name\": \"report\",\n    \"type\": \"string\",\n    \"optional\": true\n  }\n]"}, "block": [{"number": 2, "keyword": "action", "provider": "workato_variable", "name": "declare_variable", "as": "36bf1d17", "skip": false, "input": {"variables": {"data": {"job_report": "OK"}, "schema": "[{\"name\":\"job_report\",\"type\":\"string\",\"optional\":true,\"label\":\"Job Report\",\"details\":{\"real_name\":\"Job Report\"},\"control_type\":\"text\"}]"}}, "block": []}, {"number": 3, "keyword": "try", "provider": "", "name": "", "as": "", "skip": false, "input": {}, "block": [{"number": 4, "keyword": "action", "provider": "snowflake", "name": "search_rows_sql", "as": "85f2b107", "skip": false, "input": {"limit": "2000", "parameters": {"schema": "[]"}, "sql": "SELECT DISTINCT COMPANY_NAME FROM WORKATO_BUSINESS_SYSTEMS.FRESHDESK.product_support_ticket_export WHERE LOWER(COMPANY_NAME) LIKE LOWER('%#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"bd069835\",\"path\":[\"typeahead\", \"value\"]}')}%')"}, "block": []}, {"number": 5, "keyword": "action", "provider": "slack_bot", "name": "generate_menu_options", "as": "aab14ffe", "skip": false, "input": {"option_groups": [{}], "options": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"85f2b107\",\"path\":[\"rows\"]}')}", "label": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"85f2b107\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"company_name\"]}')}", "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"85f2b107\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"company_name\"]}')}"}, "use_option_groups": "false"}, "block": []}, {"number": 6, "keyword": "catch", "provider": "", "name": "", "as": "31cbad55", "skip": false, "input": {"max_retry_count": "0", "retry_interval": "2"}, "block": [{"number": 7, "keyword": "action", "provider": "workato_variable", "name": "update_variables", "as": "d719ef1b", "skip": false, "input": {"job_report": "Failed", "name": "a6523e8a-1564-4e9f-8a97-759562eee67b:36bf1d17:job_report"}, "block": []}]}]}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[str, str, str]] = [
    (DECLARE_STEP_AS, "workato_variable", "declare_variable"),
    (SEARCH_STEP_AS, "snowflake", "search_rows_sql"),
    (MENU_STEP_AS, "slack_bot", "generate_menu_options"),
    (UPDATE_STEP_AS, "workato_variable", "update_variables"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "workato_runtime.declare_variable",
    "snowflake.search_rows_sql",
    "slack_bot.generate_menu_options",
    "workato_runtime.update_variables",
]
ALLOWED_TOOLS: list[str] = [
    "snowflake.search_rows_sql",
    "slack_bot.generate_menu_options",
]
TRIGGER_PARAMETER_KEYS = ("company_name", "report")
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "resolved_sql",
    "menu_options",
    "menu_options_ordered",
    "final_job_report",
)
_TYPEAHEAD_RE = re.compile(r"^[A-Za-z0-9 .\-]*$")


def validate_94382842(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("keyword") != "trigger":
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe root is not a trigger")
    if raw.get("provider") != TRIGGER_PROVIDER or raw.get("name") != TRIGGER_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} has unexpected trigger")
    if str(raw.get("as") or "") != TRIGGER_AS:
        raise RuntimeError(f"recipe {RECIPE_ID} trigger step id changed: {raw.get('as')!r}")
    if str((raw.get("input") or {}).get("dynamic_menu_name") or "") != DYNAMIC_MENU_NAME:
        raise RuntimeError(f"recipe {RECIPE_ID} dynamic menu name changed")
    normalized = _normalize_tree(raw)
    if normalized != _EXPECTED_TREE:
        mismatch = _first_tree_mismatch(normalized, _EXPECTED_TREE)
        raise RuntimeError(f"recipe {RECIPE_ID} raw recipe drifted from pin: {mismatch}")
    # Semantic pins on the drift-prone bits (the tree pin holds the exact
    # bytes; these name the trap when one changes).
    search = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == SEARCH_STEP_AS),
        None,
    )
    if not isinstance(search, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} search step {SEARCH_STEP_AS} missing")
    sql = str((search.get("input") or {}).get("sql") or "")
    if SNOWFLAKE_TABLE not in sql or "SELECT DISTINCT COMPANY_NAME" not in sql:
        raise RuntimeError(f"recipe {RECIPE_ID} search SQL table/projection changed: {sql!r}")
    if "LOWER(COMPANY_NAME) LIKE LOWER('%" not in sql:
        raise RuntimeError(f"recipe {RECIPE_ID} case-insensitive LIKE filter changed: {sql!r}")
    if str((search.get("input") or {}).get("limit") or "") != "2000":
        raise RuntimeError(f"recipe {RECIPE_ID} search limit changed")
    menu = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == MENU_STEP_AS),
        None,
    )
    if not isinstance(menu, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} menu step {MENU_STEP_AS} missing")
    menu_input = menu.get("input") or {}
    if menu_input.get("option_groups") != [{}] or menu_input.get("use_option_groups") != "false":
        raise RuntimeError(
            f"recipe {RECIPE_ID} menu step no longer carries the vestigial "
            "option_groups [{}] + use_option_groups 'false' shape"
        )
    update = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == UPDATE_STEP_AS),
        None,
    )
    if not isinstance(update, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} catch update step {UPDATE_STEP_AS} missing")
    target = str((update.get("input") or {}).get("name") or "")
    if target.split(":")[1:] != [DECLARE_STEP_AS, "job_report"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch update no longer targets the declared "
            f"{DECLARE_STEP_AS}:job_report variable: {target!r}"
        )
    actions = _collect_actions(raw)
    actual = [(str(a.get("as")), str(a.get("provider")), str(a.get("name"))) for a in actions]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "dynamic_menu_name": DYNAMIC_MENU_NAME,
        "snowflake_table": SNOWFLAKE_TABLE,
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


def seed_94382842(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_94382842(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    expect = data.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    force = data.get("force_action_error")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
    }
    if force is not None:
        # CATCH branch: the forced error fires BEFORE the snowflake adapter
        # runs, so this variant owns no live resources and must not seed any.
        if not isinstance(force, dict) or str(force.get("step_as") or "") != SEARCH_STEP_AS:
            raise RuntimeError(
                f"recipe {RECIPE_ID} force_action_error must target the snowflake "
                f"step {SEARCH_STEP_AS!r}; got {force!r}"
            )
        if sorted(seed_in.keys()) != []:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must not seed live sections "
                f"(nothing runs against Snowflake); got {sorted(seed_in.keys())}"
            )
        if expect.get("final_job_report") != "Failed":
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must expect final_job_report "
                f"'Failed'; got {expect.get('final_job_report')!r}"
            )
        if expect.get("menu_options") is not None or expect.get("resolved_sql") is not None:
            raise RuntimeError(
                f"recipe {RECIPE_ID} catch variants must pin menu_options and "
                "resolved_sql as null (the TRY branch never completes)"
            )
    else:
        if sorted(seed_in.keys()) != ["snowflake_live"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} TRY variants must seed exactly the snowflake_live "
                f"section; got {sorted(seed_in.keys())}"
            )
        _require_snowflake_section(seed_in["snowflake_live"])
        if expect.get("final_job_report") != "OK":
            raise RuntimeError(
                f"recipe {RECIPE_ID} TRY variants must expect final_job_report 'OK'; "
                f"got {expect.get('final_job_report')!r}"
            )
        if not isinstance(expect.get("menu_options"), list) or not isinstance(
            expect.get("resolved_sql"), str
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} TRY variants must pin expect.menu_options (list) "
                "and expect.resolved_sql (str)"
            )
        provision = ctx.tools.call(
            "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
        )
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
        out["snowflake_live"] = deepcopy(provision["state"])
        out["snowflake_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_94382842(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_94382842(raw)
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    live = isinstance(seed.get("snowflake_live"), dict)
    if not live and not isinstance(seed.get("force_action_error"), dict):
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed carries neither snowflake_live state nor a "
            "forced catch error — nothing to run"
        )
    raw_execution: dict[str, Any] | None = None
    initial_snapshot: dict[str, Any] = {}
    final_snapshot: dict[str, Any] = {}
    cleanup: dict[str, Any] | None = None
    try:
        initial_snapshot = _snapshot(ctx, live)
        raw_execution = execute_raw_recipe(raw, seed, ctx)
        final_snapshot = _snapshot(ctx, live)
    finally:
        if live:
            # Required cleanup: the seeder create-or-replaced the registered
            # live table; drop it whether or not the run completed.
            cleanup = ctx.tools.call("harness.snowflake_live.cleanup", {})
    if live and not (cleanup or {}).get("ok", False):
        raise RuntimeError(f"recipe {RECIPE_ID} Snowflake cleanup failed: {cleanup}")
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
            "cleanup_response": {"snowflake_live": cleanup},
            "ground_truth": _ground_truth(raw_execution),
        },
        allowed_tools=ALLOWED_TOOLS,
    )
    result["verifier"] = verify_94382842(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> None:
    if sorted(trigger.keys()) != ["parameters", "typeahead"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly typeahead + parameters; "
            f"got {sorted(trigger.keys())}"
        )
    typeahead = trigger.get("typeahead")
    if (
        not isinstance(typeahead, dict)
        or sorted(typeahead.keys()) != ["value"]
        or not isinstance(typeahead.get("value"), str)
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input.typeahead must be {{'value': <str>}} "
            "(explicitly blank '' exercises the LIKE-'%%'-match-all branch)"
        )
    if not _TYPEAHEAD_RE.fullmatch(typeahead["value"]):
        raise RuntimeError(
            f"recipe {RECIPE_ID} typeahead.value interpolates into a single-quoted SQL "
            f"LIKE literal; quotes, backslashes and LIKE wildcards (%/_) are rejected: "
            f"{typeahead['value']!r}"
        )
    parameters = trigger.get("parameters")
    if not isinstance(parameters, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} trigger_input.parameters must be an object")
    unknown = sorted(set(parameters.keys()) - set(TRIGGER_PARAMETER_KEYS))
    if unknown:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger parameters may only carry the declared optional "
            f"{list(TRIGGER_PARAMETER_KEYS)} (both unused by the recipe); got {unknown}"
        )
    for key, value in parameters.items():
        if not isinstance(value, str):
            raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters.{key} must be a string")


def _require_snowflake_section(section: Any) -> None:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the SQL uses no CURRENT_DATE/TIMESTAMP, so current_time is not allowed)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [SNOWFLAKE_TABLE]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live.tables must declare exactly "
            f"{SNOWFLAKE_TABLE!r} (the literal 3-part name the SQL interpolates)"
        )
    spec = tables[SNOWFLAKE_TABLE]
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table spec must be exactly {{'columns': ..., 'rows': ...}}"
        )
    if spec["columns"] != TABLE_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table must declare exactly the columns {TABLE_COLUMNS}"
        )
    rows = spec["rows"]
    if not isinstance(rows, list):
        raise RuntimeError(f"recipe {RECIPE_ID} table rows must be a list (may be empty)")
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != ["COMPANY_NAME"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} must be exactly "
                f"{{'COMPANY_NAME': <str or null>}}; got {row!r}"
            )
        value = row["COMPANY_NAME"]
        # Null is allowed on purpose: LOWER(NULL) LIKE ... is NULL, so the SQL
        # itself drops null names — a reachable live semantic worth seeding.
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} COMPANY_NAME must be a non-empty "
                f"string or null; got {value!r}"
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


def _snapshot(ctx: RecipeContext, live: bool) -> dict[str, Any]:
    if not live:
        return {}
    return ctx.tools.call("harness.snowflake.snapshot", {})


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
