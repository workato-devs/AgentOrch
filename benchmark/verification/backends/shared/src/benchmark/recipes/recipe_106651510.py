from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from ..context import RecipeContext
from ..raw_executor import execute_raw_recipe
from ..result import recipe_result
from ..variant_input import attach_variant, trigger_input, variant_data
from ..verifier import verify_106651510


RECIPE_ID = "106651510"
SEED_TYPE = "slack_dynamic_menu_freshdesk_success_owners_variant"
TRACK = "live_snowflake_slack_dynamic_menu"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "dynamic_menu"
TRIGGER_AS = "144cca42"
DYNAMIC_MENU_NAME = "List of Success Owner"
DECLARE_STEP_AS = "e0710040"
SEARCH_STEP_AS = "a07a5b6b"
MENU_STEP_AS = "bce0615a"
CATCH_AS = "e534d68c"
UPDATE_STEP_AS = "d81aaa3b"
SNOWFLAKE_TABLE = "FRESHDESK.PRODUCT_SUPPORT_TICKET_EXPORT"
TABLE_COLUMNS = {"SUCCESS_OWNER_AUTO_POPULATED": "string"}
IF_FORMULA_SUFFIX = '.split("_") [0].capitalize'


_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "slack_bot", "name": "dynamic_menu", "as": "144cca42", "skip": false, "input": {"dynamic_menu_name": "List of Success Owner", "parameters": "[\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Success Owner\",\n    \"name\": \"success_owner\",\n    \"type\": \"string\",\n    \"optional\": true\n  },\n  {\n    \"control_type\": \"text\",\n    \"label\": \"Request Type\",\n    \"name\": \"request_type\",\n    \"type\": \"string\",\n    \"optional\": true\n  }\n]"}, "block": [{"number": 2, "keyword": "action", "provider": "workato_variable", "name": "declare_variable", "as": "e0710040", "skip": false, "input": {"variables": {"data": {"job_report": "OK"}, "schema": "[{\"name\":\"job_report\",\"type\":\"string\",\"optional\":true,\"label\":\"Job Report\",\"details\":{\"real_name\":\"Job Report\"},\"control_type\":\"text\"}]"}}, "block": []}, {"number": 3, "keyword": "try", "provider": "", "name": "", "as": "", "skip": false, "input": {}, "block": [{"number": 4, "keyword": "if", "provider": "", "name": "", "as": "", "skip": false, "input": {"conditions": [{"lhs": "=_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"144cca42\",\"path\":[\"parameters\",\"request_type\"]}').split(\"_\") [0].capitalize", "operand": "equals_to", "rhs": "Freshdesk"}], "operand": "and", "type": "compound"}, "block": [{"number": 5, "keyword": "action", "provider": "snowflake", "name": "search_rows_sql", "as": "a07a5b6b", "skip": false, "input": {"limit": "2000", "parameters": {"schema": "[]"}, "sql": "SELECT DISTINCT SUCCESS_OWNER_AUTO_POPULATED FROM FRESHDESK.PRODUCT_SUPPORT_TICKET_EXPORT WHERE LOWER(SUCCESS_OWNER_AUTO_POPULATED) LIKE LOWER('%#{_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"144cca42\",\"path\":[\"typeahead\", \"value\"]}')}%')"}, "block": []}, {"number": 6, "keyword": "action", "provider": "slack_bot", "name": "generate_menu_options", "as": "bce0615a", "skip": false, "input": {"option_groups": [{}], "options": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"a07a5b6b\",\"path\":[\"rows\"]}')}", "label": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"a07a5b6b\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"success_owner_auto_populated\"]}')}", "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"a07a5b6b\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"success_owner_auto_populated\"]}')}"}, "use_option_groups": "false"}, "block": []}]}, {"number": 7, "keyword": "catch", "provider": "", "name": "", "as": "e534d68c", "skip": false, "input": {"max_retry_count": "0", "retry_interval": "2"}, "block": [{"number": 8, "keyword": "action", "provider": "workato_variable", "name": "update_variables", "as": "d81aaa3b", "skip": false, "input": {"job_report": "Failed", "name": "81c8f4ce-f798-4fd4-96dd-c0bcb03c3128:e0710040:job_report"}, "block": []}]}]}]}"""
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
TRIGGER_PARAMETER_KEYS = ("success_owner", "request_type")
REQUIRED_EXPECT_KEYS = (
    "executed_action_count",
    "tools",
    "tool_expectations",
    "branch",
    "resolved_sql",
    "menu_options",
    "menu_options_ordered",
    "final_job_report",
)
BRANCHES = ("freshdesk_menu", "skip_non_freshdesk", "catch_failed")
_TYPEAHEAD_RE = re.compile(r"^[A-Za-z0-9 .\-]*$")


def _request_type_transform(value: str) -> str:
    # Ruby `.split("_") [0].capitalize` parity for the seeded values the guard
    # admits (Python capitalize also lowercases the tail).
    return value.split("_")[0].capitalize()


def validate_106651510(raw: dict[str, Any]) -> dict[str, Any]:
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
    if_nodes = [node for node in _walk_nodes(raw) if node.get("keyword") == "if"]
    if len(if_nodes) != 1:
        raise RuntimeError(f"recipe {RECIPE_ID} expected exactly one IF gate")
    condition = ((if_nodes[0].get("input") or {}).get("conditions") or [{}])[0]
    lhs = str(condition.get("lhs") or "")
    if not lhs.endswith(IF_FORMULA_SUFFIX) or condition.get("rhs") != "Freshdesk":
        raise RuntimeError(
            f"recipe {RECIPE_ID} the quirky space-before-[0] IF formula changed: {lhs!r}"
        )
    search = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == SEARCH_STEP_AS), None
    )
    if not isinstance(search, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} search step {SEARCH_STEP_AS} missing")
    sql = str((search.get("input") or {}).get("sql") or "")
    if SNOWFLAKE_TABLE not in sql or "SELECT DISTINCT SUCCESS_OWNER_AUTO_POPULATED" not in sql:
        raise RuntimeError(f"recipe {RECIPE_ID} search SQL table/projection changed: {sql!r}")
    if "LOWER(SUCCESS_OWNER_AUTO_POPULATED) LIKE LOWER('%" not in sql:
        raise RuntimeError(f"recipe {RECIPE_ID} case-insensitive LIKE filter changed: {sql!r}")
    if str((search.get("input") or {}).get("limit") or "") != "2000":
        raise RuntimeError(f"recipe {RECIPE_ID} search limit changed")
    menu = next(
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == MENU_STEP_AS), None
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
        (node for node in _walk_nodes(raw) if str(node.get("as") or "") == UPDATE_STEP_AS), None
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


def seed_106651510(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_106651510(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    request_transform = _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict):
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing seed object")
    expect = data.get("expect")
    _require_expect_common(expect)
    branch = expect["branch"]
    force = data.get("force_action_error")
    out: dict[str, Any] = {
        "recipe_id": RECIPE_ID,
        "seed_type": SEED_TYPE,
        "trigger": trigger,
        "track": data.get("track") or TRACK,
        "raw_validation": validation,
        "expect": deepcopy(expect),
    }
    if branch == "freshdesk_menu":
        _require_menu_variant(seed_in, expect, force, request_transform)
        provision = ctx.tools.call(
            "harness.snowflake_live.seed_tables", {"snowflake": seed_in["snowflake_live"]}
        )
        if not provision.get("ok"):
            raise RuntimeError(f"recipe {RECIPE_ID} live Snowflake seed failed: {provision}")
        out["snowflake_live"] = deepcopy(provision["state"])
        out["snowflake_seed_snapshot"] = deepcopy(provision.get("snapshot") or {})
    elif branch == "skip_non_freshdesk":
        _require_skip_variant(seed_in, expect, force, request_transform)
    else:  # catch_failed
        _require_catch_variant(seed_in, expect, force, request_transform)
    out["harness_tool_calls"] = ctx.tools.call_log()
    return attach_variant(out, ctx)


def run_106651510(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_106651510(raw)
    expect = seed.get("expect")
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    live = isinstance(seed.get("snowflake_live"), dict)
    if expect.get("branch") == "freshdesk_menu" and not live:
        raise RuntimeError(
            f"recipe {RECIPE_ID} freshdesk_menu seed carries no snowflake_live state"
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
    result["verifier"] = verify_106651510(result)
    result["ok"] = bool(result["ok"] and result["verifier"]["ok"])
    return result


def _require_trigger_shape(trigger: dict[str, Any]) -> str:
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
            f"recipe {RECIPE_ID} trigger parameters may only carry the declared "
            f"{list(TRIGGER_PARAMETER_KEYS)}; got {unknown}"
        )
    for key, value in parameters.items():
        if not isinstance(value, str):
            raise RuntimeError(f"recipe {RECIPE_ID} trigger parameters.{key} must be a string")
    request_type = str(parameters.get("request_type") or "")
    if not request_type.strip():
        raise RuntimeError(
            f"recipe {RECIPE_ID} parameters.request_type must be non-blank in EVERY "
            "variant: the IF formula calls .split on it and a blank pill raises "
            "(diverting into the catch instead of the intended branch)"
        )
    if not re.fullmatch(r"[A-Za-z]+(_[A-Za-z]+)*", request_type):
        raise RuntimeError(
            f"recipe {RECIPE_ID} parameters.request_type must be a plain "
            f"underscore-separated word so the Ruby capitalize parity holds: "
            f"{request_type!r}"
        )
    return _request_type_transform(request_type)


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


def _require_menu_variant(
    seed_in: dict[str, Any],
    expect: dict[str, Any],
    force: Any,
    request_transform: str,
) -> None:
    if force is not None:
        raise RuntimeError(f"recipe {RECIPE_ID} menu variants must not force an action error")
    if request_transform != "Freshdesk":
        raise RuntimeError(
            f"recipe {RECIPE_ID} freshdesk_menu variants need request_type that "
            f"capitalizes to 'Freshdesk'; got {request_transform!r}"
        )
    if sorted(seed_in.keys()) != ["snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} freshdesk_menu variants must seed exactly the "
            f"snowflake_live section; got {sorted(seed_in.keys())}"
        )
    _require_snowflake_section(seed_in["snowflake_live"])
    checks = (
        expect.get("final_job_report") == "OK",
        isinstance(expect.get("resolved_sql"), str),
        isinstance(expect.get("menu_options"), list),
        expect.get("executed_action_count") == 3,
        expect.get("tools")
        == ["snowflake.search_rows_sql", "slack_bot.generate_menu_options"],
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} freshdesk_menu expect block is inconsistent (3 actions, "
            f"both registry tools, resolved_sql str, menu_options list, job_report OK): "
            f"{expect!r}"
        )


def _require_skip_variant(
    seed_in: dict[str, Any],
    expect: dict[str, Any],
    force: Any,
    request_transform: str,
) -> None:
    if force is not None:
        raise RuntimeError(f"recipe {RECIPE_ID} skip variants must not force an action error")
    if request_transform == "Freshdesk":
        raise RuntimeError(
            f"recipe {RECIPE_ID} skip variants need request_type that does NOT "
            "capitalize to 'Freshdesk'"
        )
    if sorted(seed_in.keys()) != []:
        raise RuntimeError(
            f"recipe {RECIPE_ID} skip variants must not seed live sections (the IF "
            f"gate skips the snowflake step); got {sorted(seed_in.keys())}"
        )
    checks = (
        expect.get("final_job_report") == "OK",
        expect.get("resolved_sql") is None,
        expect.get("menu_options") is None,
        expect.get("menu_options_ordered") is False,
        expect.get("executed_action_count") == 1,
        expect.get("tools") == [],
        expect.get("tool_expectations") == [],
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} skip expect block is inconsistent (1 action, zero "
            f"registry tools, null resolved_sql/menu_options, job_report OK): {expect!r}"
        )


def _require_catch_variant(
    seed_in: dict[str, Any],
    expect: dict[str, Any],
    force: Any,
    request_transform: str,
) -> None:
    if not isinstance(force, dict) or str(force.get("step_as") or "") != SEARCH_STEP_AS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch variants must declare force_action_error."
            f"step_as == {SEARCH_STEP_AS!r} (the only fallible step inside the TRY)"
        )
    if not str(force.get("error") or "").strip():
        raise RuntimeError(f"recipe {RECIPE_ID} force_action_error.error must be explicit")
    if request_transform != "Freshdesk":
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch variants need request_type that capitalizes to "
            "'Freshdesk' (the IF gate must admit the failing snowflake step)"
        )
    if sorted(seed_in.keys()) != []:
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch variants must not seed live sections (the "
            f"forced error fires before the adapter); got {sorted(seed_in.keys())}"
        )
    checks = (
        expect.get("final_job_report") == "Failed",
        expect.get("resolved_sql") is None,
        expect.get("menu_options") is None,
        expect.get("menu_options_ordered") is False,
        expect.get("executed_action_count") == 2,
        expect.get("tools") == [],
        expect.get("tool_expectations") == [],
    )
    if not all(checks):
        raise RuntimeError(
            f"recipe {RECIPE_ID} catch expect block is inconsistent (2 actions, zero "
            f"registry tools, null resolved_sql/menu_options, job_report Failed): "
            f"{expect!r}"
        )


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
            f"{SNOWFLAKE_TABLE!r} (the literal 2-part name the SQL references)"
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
        if not isinstance(row, dict) or sorted(row.keys()) != ["SUCCESS_OWNER_AUTO_POPULATED"]:
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} must be exactly "
                f"{{'SUCCESS_OWNER_AUTO_POPULATED': <str or null>}}; got {row!r}"
            )
        value = row["SUCCESS_OWNER_AUTO_POPULATED"]
        # Null is allowed on purpose: LOWER(NULL) LIKE ... is NULL, so the SQL
        # itself drops null owners — a reachable live semantic worth seeding.
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} SUCCESS_OWNER_AUTO_POPULATED must "
                f"be a non-empty string or null; got {value!r}"
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
    return dict(ctx.tools.call("harness.snowflake.snapshot", {}))


def _ground_truth(raw_execution: dict[str, Any]) -> dict[str, Any]:
    by_tool: dict[str, list[dict[str, Any]]] = {}
    for row in raw_execution.get("trace") or []:
        tool = row.get("tool")
        if tool:
            by_tool.setdefault(str(tool), []).append(row if isinstance(row, dict) else {})
    return {"by_tool": by_tool, "return_value": raw_execution.get("return_value")}
