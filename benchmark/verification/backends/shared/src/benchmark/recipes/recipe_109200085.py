from __future__ import annotations

import json
import unicodedata
from typing import Any

from ..context import RecipeContext
from ..variant_input import trigger_input, variant_data
from ..verifier import verify_109200085
from .snowflake_live_recipe_utils import (
    run_live_snowflake_recipe,
    seed_live_snowflake,
    snowflake_seed_base,
)


RECIPE_ID = "109200085"
SEED_TYPE = "slack_dynamic_menu_snowflake_instance_search_variant"
TRACK = "live_snowflake_slack_dynamic_menu_instance_search"
TRIGGER_PROVIDER = "slack_bot"
TRIGGER_NAME = "dynamic_menu"
TRIGGER_AS = "af9da3a9"
DYNAMIC_MENU_NAME = "getinstances"
SQL_STEP_AS = "1a519773"
MENU_STEP_AS = "a1b9af44"
TABLE_KEY = "PUBLIC.DEMOINFRA_INSTANCES"
TABLE_COLUMNS = {"ID": "integer", "NAME": "string"}
SQL = "SELECT ID, NAME FROM PUBLIC.DEMOINFRA_INSTANCES WHERE LOWER(NAME) LIKE :value"
BIND_FORMULA = (
    "='%'+_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"af9da3a9\","
    "\"path\":[\"typeahead\",\"value\"]}').unicode_normalize.downcase+'%'"
)

# slack_bot.dynamic_menu 'getinstances' (trigger payload seeded; the declared
# 'query' parameter is NEVER dereferenced by any step -- seeded for faith,
# provably inert):
#   2  snowflake.run_custom_sql 1a519773 (LIVE): SELECT ID, NAME FROM
#      PUBLIC.DEMOINFRA_INSTANCES WHERE LOWER(NAME) LIKE :value with the
#      named bind parameters.data.value =
#      '%'+typeahead.value.unicode_normalize.downcase+'%' (Ruby NFC default;
#      apply_dp_methods probe: 'Café' -> 'café' composed, while
#      .downcase alone leaves the combining mark). The 2-part table key maps
#      to <SNOWFLAKE_DATABASE>.PUBLIC.DEMOINFRA_INSTANCES and the literal
#      table name in the SQL is rewritten inside the live adapter only -- the
#      trace keeps the recipe's verbatim SQL; :value binds via pyformat.
#   3  slack_bot.generate_menu_options a1b9af44: flat ____source = step-2
#      rows, label = current_item.name, value = current_item.id (int -- the
#      output_schema declares integer with integer_conversion and Snowflake
#      NUMBER round-trips to int). Deterministic validation-only Workbot
#      echo, no Slack API call.
# Linear, no block branches: the only boundary is the LIKE match count
# (0/1/N). The SELECT has no ORDER BY: multi-row menus are pinned as a
# MULTISET (menu_options_ordered false), single/empty pin exact order.
# IN-BATCH SHAPE-TWINS: 108871514 (DEMOINFRA_APPLICATIONS) and 108564927
# (DEMOINFRA_PROVIDERS) share the same select-bind-menu shape with string id
# columns; this recipe keys off registered 102760065 ('[CB] Search by User',
# same run_custom_sql-with-:bind + downcased typeahead + menu tail), plus the
# .unicode_normalize link that landed in raw_executor apply_dp_methods.

_RAW_PIN_JSON = r"""{"number": 1, "keyword": "trigger", "provider": "slack_bot", "name": "dynamic_menu", "as": "af9da3a9", "skip": false, "input": {"dynamic_menu_name": "getinstances", "parameters": "[{\"name\":\"query\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Query\"}]"}, "block": [{"number": 2, "keyword": "action", "provider": "snowflake", "name": "run_custom_sql", "as": "1a519773", "skip": false, "input": {"output_schema": "[{\"name\":\"id\",\"type\":\"integer\",\"optional\":false,\"control_type\":\"integer\",\"label\":\"ID\",\"parse_output\":\"integer_conversion\"},{\"name\":\"name\",\"type\":\"string\",\"optional\":false,\"control_type\":\"text\",\"label\":\"Name\"}]", "parameters": {"data": {"value": "='%'+_dp('{\"pill_type\":\"output\",\"provider\":\"slack_bot\",\"line\":\"af9da3a9\",\"path\":[\"typeahead\",\"value\"]}').unicode_normalize.downcase+'%'"}, "schema": "[{\"name\":\"value\",\"type\":\"string\",\"optional\":true,\"label\":\"value\",\"details\":{\"real_name\":\"value\"},\"control_type\":\"text\"}]"}, "sql": "SELECT ID, NAME FROM PUBLIC.DEMOINFRA_INSTANCES WHERE LOWER(NAME) LIKE :value", "update_only": "false"}, "block": []}, {"number": 3, "keyword": "action", "provider": "slack_bot", "name": "generate_menu_options", "as": "a1b9af44", "skip": false, "input": {"options": {"____source": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"1a519773\",\"path\":[\"rows\"]}')}", "label": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"1a519773\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"name\"]}')}", "value": "#{_dp('{\"pill_type\":\"output\",\"provider\":\"snowflake\",\"line\":\"1a519773\",\"path\":[\"rows\", {\"path_element_type\": \"current_item\"}, \"id\"]}')}"}}, "block": []}]}"""
_EXPECTED_TREE = json.loads(_RAW_PIN_JSON)

EXPECTED_ACTIONS: list[tuple[int, str, str, str]] = [
    (2, SQL_STEP_AS, "snowflake", "run_custom_sql"),
    (3, MENU_STEP_AS, "slack_bot", "generate_menu_options"),
]
EXPECTED_RAW_TOOLS: list[str] = [
    "snowflake.run_custom_sql",
    "slack_bot.generate_menu_options",
]
ALLOWED_TOOLS: list[str] = list(EXPECTED_RAW_TOOLS)
REQUIRED_EXPECT_KEYS = (
    "branch",
    "executed_action_count",
    "tools",
    "tool_expectations",
    "bind_value",
    "menu_options",
    "menu_options_ordered",
)
BRANCHES = (
    "multi_match",
    "case_fold",
    "unicode_nfc",
    "zero_match",
)
# The typeahead feeds the LIKE bind as '%'+value.unicode_normalize.downcase+'%':
# LIKE metacharacters and quoting characters are rejected so groundtruth stays
# a plain (binary, post-NFC) substring match. Combining marks are the point of
# this recipe and stay allowed.
_FORBIDDEN_TYPEAHEAD_CHARS = "%_'\"\\"


def validate_109200085(raw: dict[str, Any]) -> dict[str, Any]:
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
    actions = _collect_actions(raw)
    actual = [
        (a.get("number"), str(a.get("as")), str(a.get("provider")), str(a.get("name")))
        for a in actions
    ]
    if actual != EXPECTED_ACTIONS:
        raise RuntimeError(f"recipe {RECIPE_ID} action sequence changed: {actual}")
    # Semantic pins over the drift-prone bits (all inside the tree pin too;
    # re-derived here so a drift diagnoses precisely).
    sql_input = actions[0].get("input") or {}
    if sql_input.get("sql") != SQL:
        raise RuntimeError(f"recipe {RECIPE_ID} SQL text changed: {sql_input.get('sql')!r}")
    parameters = sql_input.get("parameters") or {}
    data = parameters.get("data") if isinstance(parameters.get("data"), dict) else {}
    if sorted(data.keys()) != ["value"] or data.get("value") != BIND_FORMULA:
        raise RuntimeError(
            f"recipe {RECIPE_ID} bind data must be exactly the unicode_normalize.downcase "
            f"typeahead formula on 'value'; got {data!r}"
        )
    schema_names = [item.get("name") for item in json.loads(parameters.get("schema") or "[]")]
    if schema_names != ["value"]:
        raise RuntimeError(f"recipe {RECIPE_ID} bind schema changed: {schema_names!r}")
    menu_input = actions[1].get("input") or {}
    options = menu_input.get("options") if isinstance(menu_input.get("options"), dict) else {}
    if sorted(options.keys()) != ["____source", "label", "value"]:
        raise RuntimeError(f"recipe {RECIPE_ID} menu options shape changed: {sorted(options.keys())}")
    source = str(options.get("____source") or "")
    if f'"line":"{SQL_STEP_AS}"' not in source or '"path":["rows"]' not in source:
        raise RuntimeError(f"recipe {RECIPE_ID} menu source no longer targets step-2 rows: {source!r}")
    for field, column in (("label", "name"), ("value", "id")):
        pill = str(options.get(field) or "")
        if f'"line":"{SQL_STEP_AS}"' not in pill or "current_item" not in pill or f'"{column}"' not in pill:
            raise RuntimeError(
                f"recipe {RECIPE_ID} menu {field} pill no longer reads current_item.{column}: {pill!r}"
            )
    return {
        "trigger_provider": TRIGGER_PROVIDER,
        "trigger_name": TRIGGER_NAME,
        "dynamic_menu_name": DYNAMIC_MENU_NAME,
        "snowflake_tables": [TABLE_KEY],
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


def seed_109200085(raw: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    validation = validate_109200085(raw)
    data = variant_data(ctx)
    if not data:
        raise RuntimeError(f"recipe {RECIPE_ID} requires explicit benchmark-local variant input")
    trigger = trigger_input(ctx)
    typeahead = _require_trigger_shape(trigger)
    seed_in = data.get("seed")
    if not isinstance(seed_in, dict) or sorted(seed_in.keys()) != ["snowflake_live"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the snowflake_live section; "
            f"got {sorted(seed_in.keys()) if isinstance(seed_in, dict) else seed_in!r}"
        )
    rows = _require_snowflake_section(seed_in["snowflake_live"])
    if data.get("force_action_error") is not None:
        raise RuntimeError(f"recipe {RECIPE_ID} has no catch: forcing an action error is invalid")
    _require_expect(data.get("expect"), typeahead, rows)
    provision = seed_live_snowflake(RECIPE_ID, data, ctx)
    return snowflake_seed_base(
        recipe_id=RECIPE_ID,
        seed_type=SEED_TYPE,
        track=TRACK,
        validation=validation,
        ctx=ctx,
        snowflake_state=provision["state"],
        extra={"trigger": trigger},
    )


def run_109200085(raw: dict[str, Any], seed: dict[str, Any], ctx: RecipeContext) -> dict[str, Any]:
    if not isinstance(seed.get("expect"), dict) or not seed["expect"]:
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing expect block")
    if not isinstance(seed.get("snowflake_live"), dict):
        raise RuntimeError(f"recipe {RECIPE_ID} seed file missing snowflake_live state")
    return run_live_snowflake_recipe(
        recipe_id=RECIPE_ID,
        track=TRACK,
        raw=raw,
        seed=seed,
        ctx=ctx,
        validation=validate_109200085(raw),
        expected_raw_tools=EXPECTED_RAW_TOOLS,
        allowed_tools=ALLOWED_TOOLS,
        verifier=verify_109200085,
    )


def _require_trigger_shape(trigger: dict[str, Any]) -> str:
    if sorted(trigger.keys()) != ["parameters", "typeahead"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} trigger_input must carry exactly parameters + typeahead; "
            f"got {sorted(trigger.keys())}"
        )
    parameters = trigger.get("parameters")
    if (
        not isinstance(parameters, dict)
        or sorted(parameters.keys()) != ["query"]
        or not isinstance(parameters.get("query"), str)
        or not parameters["query"].strip()
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} parameters must be exactly {{'query': <non-empty str>}} -- "
            f"the declared menu parameter is seeded for faith even though no step derefs it"
        )
    typeahead = trigger.get("typeahead")
    if (
        not isinstance(typeahead, dict)
        or sorted(typeahead.keys()) != ["value"]
        or not isinstance(typeahead.get("value"), str)
        or not typeahead["value"]
    ):
        raise RuntimeError(f"recipe {RECIPE_ID} typeahead must be {{'value': <non-empty str>}}")
    value = typeahead["value"]
    if any(ch in value for ch in _FORBIDDEN_TYPEAHEAD_CHARS):
        raise RuntimeError(
            f"recipe {RECIPE_ID} typeahead.value feeds the LIKE bind as "
            f"'%'+value.unicode_normalize.downcase+'%': LIKE wildcards (%/_), quotes and "
            f"backslashes are rejected so groundtruth stays a plain substring match; got {value!r}"
        )
    return value


def _require_snowflake_section(section: Any) -> list[dict[str, Any]]:
    if not isinstance(section, dict) or sorted(section.keys()) != ["tables"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed.snowflake_live must be exactly {{'tables': ...}} "
            "(the SQL uses no CURRENT_DATE/TIMESTAMP, so current_time is not allowed)"
        )
    tables = section["tables"]
    if not isinstance(tables, dict) or sorted(tables.keys()) != [TABLE_KEY]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} seed must declare exactly the 2-part table {TABLE_KEY!r}"
        )
    spec = tables[TABLE_KEY]
    if not isinstance(spec, dict) or sorted(spec.keys()) != ["columns", "rows"]:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {TABLE_KEY} spec must be exactly {{'columns', 'rows'}}"
        )
    if spec["columns"] != TABLE_COLUMNS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {TABLE_KEY} must declare exactly the columns "
            f"{TABLE_COLUMNS}; got {spec['columns']!r}"
        )
    rows = spec["rows"]
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            f"recipe {RECIPE_ID} table {TABLE_KEY} rows must be a non-empty list "
            "(the zero-match branch is expressed via a non-matching typeahead)"
        )
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or sorted(row.keys()) != sorted(TABLE_COLUMNS):
            raise RuntimeError(
                f"recipe {RECIPE_ID} table row {idx} must carry exactly "
                f"{sorted(TABLE_COLUMNS)}; got {row!r}"
            )
        if not isinstance(row["ID"], int) or isinstance(row["ID"], bool):
            raise RuntimeError(
                f"recipe {RECIPE_ID} row {idx} ID must be an int (the menu value pill "
                f"preserves the Snowflake NUMBER as int); got {row['ID']!r}"
            )
        if not isinstance(row["NAME"], str) or not row["NAME"].strip():
            raise RuntimeError(
                f"recipe {RECIPE_ID} row {idx} NAME must be a non-empty string; got {row['NAME']!r}"
            )
    ids = [row["ID"] for row in rows]
    if len(set(ids)) != len(ids):
        raise RuntimeError(f"recipe {RECIPE_ID} seeded IDs must be unique: {ids}")
    return rows


def _require_expect(expect: Any, typeahead: str, rows: list[dict[str, Any]]) -> None:
    if not isinstance(expect, dict) or not expect:
        raise RuntimeError(f"recipe {RECIPE_ID} variant input missing expect object")
    missing = [key for key in REQUIRED_EXPECT_KEYS if key not in expect]
    if missing:
        raise RuntimeError(f"recipe {RECIPE_ID} expect block is missing required keys: {missing}")
    unexpected = sorted(set(expect) - set(REQUIRED_EXPECT_KEYS))
    if unexpected:
        raise RuntimeError(f"recipe {RECIPE_ID} expect has undeclared keys: {unexpected}")
    branch = expect.get("branch")
    if branch not in BRANCHES:
        raise RuntimeError(f"recipe {RECIPE_ID} expect.branch must be one of {BRANCHES}")
    # Derive the bind and match set exactly like the engine + live Snowflake:
    # NFC-normalize, downcase, %-wrap; LIKE '%core%' is a binary substring
    # match against LOWER(NAME).
    bind = "%" + unicodedata.normalize("NFC", typeahead).lower() + "%"
    if expect.get("bind_value") != bind:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.bind_value must be the NFC-downcased %-wrapped "
            f"typeahead {bind!r}; got {expect.get('bind_value')!r}"
        )
    core = bind[1:-1]
    options = [
        {"label": row["NAME"], "value": row["ID"]}
        for row in rows
        if core in row["NAME"].lower()
    ]
    ordered = expect.get("menu_options_ordered")
    if len(options) > 1:
        if ordered is not False:
            raise RuntimeError(
                f"recipe {RECIPE_ID} the SQL has no ORDER BY: multi-row menus must set "
                "menu_options_ordered false (multiset compare)"
            )
        expected_sorted = sorted(options, key=_option_key)
        actual = expect.get("menu_options")
        if not isinstance(actual, list) or sorted(actual, key=_option_key) != expected_sorted:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.menu_options must be the multiset {expected_sorted}; "
                f"got {actual!r}"
            )
    else:
        if ordered is not True:
            raise RuntimeError(
                f"recipe {RECIPE_ID} single/empty menus pin exact order "
                "(menu_options_ordered true)"
            )
        if expect.get("menu_options") != options:
            raise RuntimeError(
                f"recipe {RECIPE_ID} expect.menu_options must be {options}; "
                f"got {expect.get('menu_options')!r}"
            )
    _require_branch(branch, typeahead, options, rows)
    if expect.get("executed_action_count") != 2 or expect.get("tools") != ALLOWED_TOOLS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect must pin executed_action_count 2 and tools "
            f"{ALLOWED_TOOLS}; got {expect!r}"
        )
    items = expect.get("tool_expectations")
    if not isinstance(items, list) or [item.get("tool") for item in items] != ALLOWED_TOOLS:
        raise RuntimeError(
            f"recipe {RECIPE_ID} expect.tool_expectations must align 1:1 with expect.tools"
        )
    sql_item, menu_item = items
    sql_contains = sql_item.get("args_contains")
    if (
        not isinstance(sql_contains, dict)
        or sql_contains.get("sql") != SQL
        or sql_contains.get("parameters") != {"value": bind}
        or sql_item.get("result_count") != len(options)
    ):
        raise RuntimeError(
            f"recipe {RECIPE_ID} run_custom_sql expectation must pin the verbatim SQL, "
            f"the resolved bind {{'value': {bind!r}}} and result_count {len(options)}"
        )
    if menu_item.get("result_count") != len(options):
        raise RuntimeError(
            f"recipe {RECIPE_ID} generate_menu_options expectation must pin result_count "
            f"{len(options)}"
        )
    if len(options) > 1:
        # No ORDER BY: positional option pins are forbidden on multi-row menus.
        if "options_contains" in menu_item or (
            isinstance(menu_item.get("args_contains"), dict)
            and "options" in menu_item["args_contains"]
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} multi-row variants must not pin options positionally "
                "(no ORDER BY); the verifier multiset-compares expect.menu_options"
            )
    else:
        if (
            menu_item.get("args_contains") != {"options": options}
            or menu_item.get("options_contains") != options
        ):
            raise RuntimeError(
                f"recipe {RECIPE_ID} single/empty variants must pin the exact options "
                f"{options} via args_contains + options_contains"
            )


def _require_branch(
    branch: str,
    typeahead: str,
    options: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> None:
    nfc = unicodedata.normalize("NFC", typeahead)
    if branch == "multi_match":
        if len(options) < 2 or len(options) >= len(rows):
            raise RuntimeError(
                f"recipe {RECIPE_ID} multi_match must match >=2 rows while leaving at "
                f"least one row unmatched; matched {len(options)} of {len(rows)}"
            )
    elif branch == "case_fold":
        if typeahead == typeahead.lower() or nfc != typeahead or not options:
            raise RuntimeError(
                f"recipe {RECIPE_ID} case_fold needs an already-NFC typeahead with "
                f"uppercase letters that still matches (proves .downcase in the bind); "
                f"got {typeahead!r} -> {len(options)} options"
            )
    elif branch == "unicode_nfc":
        if nfc == typeahead:
            raise RuntimeError(
                f"recipe {RECIPE_ID} unicode_nfc requires a DECOMPOSED typeahead "
                f"(combining marks) so .unicode_normalize is load-bearing; got {typeahead!r}"
            )
        if not options or len(options) >= len(rows):
            raise RuntimeError(
                f"recipe {RECIPE_ID} unicode_nfc must match the composed-NFC row while an "
                f"accent-free decoy stays unmatched; matched {len(options)} of {len(rows)}"
            )
    elif branch == "zero_match":
        if options:
            raise RuntimeError(
                f"recipe {RECIPE_ID} zero_match must match no seeded row; got {options!r}"
            )


def _option_key(option: Any) -> tuple[str, str]:
    if not isinstance(option, dict):
        return ("", "")
    return (str(option.get("label")), str(option.get("value")))


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
